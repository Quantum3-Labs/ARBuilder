// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import { BN254 } from "solidity-bn254/BN254.sol";
import { Vm } from "forge-std/Vm.sol";
import { IDarkpool } from "darkpoolv1-interfaces/IDarkpool.sol";
import { NullifierLib as NullifierSetLib } from "renegade-lib/NullifierSet.sol";
import { WalletOperations } from "darkpoolv1-lib/WalletOperations.sol";
import { PlonkProof } from "renegade-lib/verifier/Types.sol";
import { ExternalTransfer, TransferType, TransferAuthorization } from "darkpoolv1-types/Transfers.sol";
import { PublicRootKey } from "darkpoolv1-types/Keychain.sol";
import { DarkpoolTestBase } from "./DarkpoolTestBase.sol";
import { ValidWalletCreateStatement, ValidWalletUpdateStatement } from "darkpoolv1-lib/PublicInputs.sol";

contract UpdateWalletTest is DarkpoolTestBase {
    // --- Update Wallet --- //

    /// @notice Test updating a wallet
    function test_updateWallet_validUpdate() public {
        // Setup calldata
        (bytes memory newSharesCommitmentSig, ValidWalletUpdateStatement memory statement, PlonkProof memory proof) =
            updateWalletCalldata();
        TransferAuthorization memory transferAuthorization = emptyTransferAuthorization();

        // Modify the merkle root to be valid
        BN254.ScalarField currRoot = darkpool.getMerkleRoot();
        statement.merkleRoot = currRoot;

        // Update the wallet
        darkpool.updateWallet(newSharesCommitmentSig, transferAuthorization, statement, proof);

        // Check that the nullifier is used
        BN254.ScalarField nullifier = statement.previousNullifier;
        assertEq(darkpool.nullifierSpent(nullifier), true);
    }

    /// @notice Test updating a wallet with a deposit
    function test_updateWallet_deposit() public {
        uint256 depositAmount = 100;

        // Generate keys for the on-chain wallet and the user wallet
        Vm.Wallet memory userWallet = randomEthereumWallet();
        Vm.Wallet memory rootKeyWallet = randomEthereumWallet();
        quoteToken.mint(userWallet.addr, depositAmount);

        uint256 darkpoolBalanceBefore = quoteToken.balanceOf(address(darkpool));
        uint256 userBalanceBefore = quoteToken.balanceOf(userWallet.addr);

        // Setup calldata
        ExternalTransfer memory transfer = ExternalTransfer({
            account: userWallet.addr,
            mint: address(quoteToken),
            amount: depositAmount,
            transferType: TransferType.Deposit
        });
        (bytes memory newSharesCommitmentSig, ValidWalletUpdateStatement memory statement, PlonkProof memory proof) =
            generateUpdateWalletCalldata(transfer, rootKeyWallet);
        statement.merkleRoot = darkpool.getMerkleRoot();

        // Authorize the deposit
        PublicRootKey memory oldPkRoot = forgeWalletToRootKey(rootKeyWallet);
        TransferAuthorization memory transferAuthorization =
            authorizeDeposit(transfer, oldPkRoot, address(darkpool), permit2, userWallet);

        // Update the wallet
        darkpool.updateWallet(newSharesCommitmentSig, transferAuthorization, statement, proof);

        // Check that the user token balance has decreased
        uint256 darkpoolBalanceAfter = quoteToken.balanceOf(address(darkpool));
        uint256 userBalanceAfter = quoteToken.balanceOf(userWallet.addr);
        assertEq(darkpoolBalanceAfter, darkpoolBalanceBefore + depositAmount);
        assertEq(userBalanceAfter, userBalanceBefore - depositAmount);
    }

    /// @notice Test updating a wallet with a withdrawal
    function test_updateWallet_withdrawal() public {
        uint256 withdrawalAmount = 100;

        // Generate keys for the on-chain wallet and the Renegade wallet
        Vm.Wallet memory userWallet = randomEthereumWallet();
        Vm.Wallet memory rootKeyWallet = randomEthereumWallet();
        quoteToken.mint(address(darkpool), withdrawalAmount);
        uint256 darkpoolBalanceBefore = quoteToken.balanceOf(address(darkpool));
        uint256 userBalanceBefore = quoteToken.balanceOf(userWallet.addr);

        // Setup calldata
        ExternalTransfer memory transfer = ExternalTransfer({
            account: userWallet.addr,
            mint: address(quoteToken),
            amount: withdrawalAmount,
            transferType: TransferType.Withdrawal
        });
        (bytes memory newSharesCommitmentSig, ValidWalletUpdateStatement memory statement, PlonkProof memory proof) =
            generateUpdateWalletCalldata(transfer, rootKeyWallet);
        statement.merkleRoot = darkpool.getMerkleRoot();

        // Authorize the withdrawal
        TransferAuthorization memory transferAuthorization = authorizeWithdrawal(transfer, rootKeyWallet);

        // Update the wallet
        darkpool.updateWallet(newSharesCommitmentSig, transferAuthorization, statement, proof);

        // Check that the user token balance has increased
        uint256 darkpoolBalanceAfter = quoteToken.balanceOf(address(darkpool));
        uint256 userBalanceAfter = quoteToken.balanceOf(userWallet.addr);
        assertEq(darkpoolBalanceAfter, darkpoolBalanceBefore - withdrawalAmount);
        assertEq(userBalanceAfter, userBalanceBefore + withdrawalAmount);
    }

    // --- Invalid Test Cases --- //

    /// @notice Test updating a wallet with an invalid proof
    function test_updateWallet_invalidProof() public {
        (bytes memory newSharesCommitmentSig, ValidWalletUpdateStatement memory statement, PlonkProof memory proof) =
            updateWalletCalldata();
        TransferAuthorization memory transferAuthorization = emptyTransferAuthorization();

        vm.expectRevert(IDarkpool.VerificationFailed.selector);
        darkpoolRealVerifier.updateWallet(newSharesCommitmentSig, transferAuthorization, statement, proof);
    }

    /// @notice Test updating a wallet with a duplicate public blinder share
    function test_updateWallet_duplicateBlinder() public {
        // Create a wallet using the public blinder
        (ValidWalletCreateStatement memory createStatement, PlonkProof memory createProof) = createWalletCalldata();
        darkpool.createWallet(createStatement, createProof);
        BN254.ScalarField publicBlinder = createStatement.publicShares[createStatement.publicShares.length - 1];

        // Update the wallet with the same public blinder share
        (bytes memory newSharesCommitmentSig, ValidWalletUpdateStatement memory statement, PlonkProof memory proof) =
            updateWalletCalldata();
        TransferAuthorization memory transferAuthorization = emptyTransferAuthorization();
        statement.merkleRoot = darkpool.getMerkleRoot();
        statement.newPublicShares[statement.newPublicShares.length - 1] = publicBlinder;

        // Should fail
        vm.expectRevert(NullifierSetLib.NullifierAlreadySpent.selector);
        darkpool.updateWallet(newSharesCommitmentSig, transferAuthorization, statement, proof);
    }

    /// @notice Test updating a wallet with an invalid Merkle root
    function test_updateWallet_invalidMerkleRoot() public {
        // Setup calldata
        (bytes memory newSharesCommitmentSig, ValidWalletUpdateStatement memory statement, PlonkProof memory proof) =
            updateWalletCalldata();
        TransferAuthorization memory transferAuthorization = emptyTransferAuthorization();

        // Modify the merkle root to be invalid
        statement.merkleRoot = randomScalar();

        // Should fail
        vm.expectRevert(WalletOperations.MerkleRootNotInHistory.selector);
        darkpool.updateWallet(newSharesCommitmentSig, transferAuthorization, statement, proof);
    }

    /// @notice Test updating a wallet with a spent nullifier
    function test_updateWallet_spentNullifier() public {
        // Setup calldata
        (bytes memory newSharesCommitmentSig, ValidWalletUpdateStatement memory statement, PlonkProof memory proof) =
            updateWalletCalldata();
        TransferAuthorization memory transferAuthorization = emptyTransferAuthorization();

        // Modify the merkle root to be valid
        BN254.ScalarField currRoot = darkpool.getMerkleRoot();
        statement.merkleRoot = currRoot;

        // First update should succeed
        darkpool.updateWallet(newSharesCommitmentSig, transferAuthorization, statement, proof);

        // Second update with same nullifier should fail
        vm.expectRevert(NullifierSetLib.NullifierAlreadySpent.selector);
        darkpool.updateWallet(newSharesCommitmentSig, transferAuthorization, statement, proof);
    }

    /// @notice Test updating a wallet with an invalid signature
    function test_updateWallet_invalidSignature() public {
        // Setup calldata
        (bytes memory newSharesCommitmentSig, ValidWalletUpdateStatement memory statement, PlonkProof memory proof) =
            updateWalletCalldata();
        TransferAuthorization memory transferAuthorization = emptyTransferAuthorization();

        // Use the current Merkle root to isolate the signature check directly
        BN254.ScalarField currRoot = darkpool.getMerkleRoot();
        statement.merkleRoot = currRoot;

        // Modify a random byte of the signature
        uint256 randIdx = randomUint(newSharesCommitmentSig.length);
        newSharesCommitmentSig[randIdx] = randomByte();

        // Should fail
        vm.expectRevert();
        darkpool.updateWallet(newSharesCommitmentSig, transferAuthorization, statement, proof);
    }
}

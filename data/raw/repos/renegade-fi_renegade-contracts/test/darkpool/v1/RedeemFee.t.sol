// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import { Vm } from "forge-std/Vm.sol";
import { BN254 } from "solidity-bn254/BN254.sol";

import { DarkpoolTestBase } from "./DarkpoolTestBase.sol";
import { IDarkpool } from "darkpoolv1-interfaces/IDarkpool.sol";
import { NullifierLib as NullifierSetLib } from "renegade-lib/NullifierSet.sol";
import { WalletOperations } from "darkpoolv1-lib/WalletOperations.sol";
import { TransferAuthorization } from "darkpoolv1-types/Transfers.sol";
import { PlonkProof } from "renegade-lib/verifier/Types.sol";
import {
    ValidWalletCreateStatement,
    ValidWalletUpdateStatement,
    ValidFeeRedemptionStatement
} from "darkpoolv1-lib/PublicInputs.sol";

contract RedeemFeeTest is DarkpoolTestBase {
    // --- Redeem Fee --- //

    /// @notice Test redeeming a fee correctly
    function test_redeemFee() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        Vm.Wallet memory receiverWallet = randomEthereumWallet();

        // Generate the calldata and redeem the fee
        (bytes memory newSharesCommitmentSig, ValidFeeRedemptionStatement memory statement, PlonkProof memory proof) =
            redeemFeeCalldata(merkleRoot, receiverWallet);
        darkpool.redeemFee(newSharesCommitmentSig, statement, proof);

        // Check that the nullifiers are spent
        assertEq(darkpool.nullifierSpent(statement.walletNullifier), true);
        assertEq(darkpool.nullifierSpent(statement.noteNullifier), true);
    }

    // --- Invalid Cases --- //

    /// @notice Test redeeming a fee with an invalid proof
    function test_redeemFee_invalidProof() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        Vm.Wallet memory receiverWallet = randomEthereumWallet();

        // Generate the calldata and redeem the fee
        (bytes memory newSharesCommitmentSig, ValidFeeRedemptionStatement memory statement, PlonkProof memory proof) =
            redeemFeeCalldata(merkleRoot, receiverWallet);

        // Should fail
        vm.expectRevert(IDarkpool.VerificationFailed.selector);
        darkpoolRealVerifier.redeemFee(newSharesCommitmentSig, statement, proof);
    }

    /// @notice Test redeeming a fee with a duplicate public blinder share
    function test_redeemFee_duplicateBlinder() public {
        // Create a wallet using the public blinder
        (ValidWalletCreateStatement memory createStatement, PlonkProof memory createProof) = createWalletCalldata();
        darkpool.createWallet(createStatement, createProof);
        BN254.ScalarField publicBlinder = createStatement.publicShares[createStatement.publicShares.length - 1];

        // Redeem the fee with the same public blinder share
        Vm.Wallet memory receiverWallet = randomEthereumWallet();
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (bytes memory redeemSig, ValidFeeRedemptionStatement memory statement, PlonkProof memory proof) =
            redeemFeeCalldata(merkleRoot, receiverWallet);
        statement.newWalletPublicShares[statement.newWalletPublicShares.length - 1] = publicBlinder;

        // Should fail
        vm.expectRevert(NullifierSetLib.NullifierAlreadySpent.selector);
        darkpool.redeemFee(redeemSig, statement, proof);
    }

    /// @notice Test redeeming a fee with an invalid wallet merkle root
    function test_redeemFee_invalidWalletMerkleRoot() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        Vm.Wallet memory receiverWallet = randomEthereumWallet();

        // Generate the calldata and redeem the fee
        (bytes memory newSharesCommitmentSig, ValidFeeRedemptionStatement memory statement, PlonkProof memory proof) =
            redeemFeeCalldata(merkleRoot, receiverWallet);
        statement.walletRoot = randomScalar();
        vm.expectRevert(WalletOperations.MerkleRootNotInHistory.selector);
        darkpool.redeemFee(newSharesCommitmentSig, statement, proof);
    }

    /// @notice Test redeeming a fee with an invalid note merkle root
    function test_redeemFee_invalidNoteMerkleRoot() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        Vm.Wallet memory receiverWallet = randomEthereumWallet();

        // Generate the calldata and redeem the fee
        (bytes memory newSharesCommitmentSig, ValidFeeRedemptionStatement memory statement, PlonkProof memory proof) =
            redeemFeeCalldata(merkleRoot, receiverWallet);
        statement.noteRoot = randomScalar();
        vm.expectRevert(WalletOperations.NoteNotInMerkleHistory.selector);
        darkpool.redeemFee(newSharesCommitmentSig, statement, proof);
    }

    /// @notice Test redeeming a fee with a spent wallet nullifier
    function test_redeemFee_spentWalletNullifier() public {
        BN254.ScalarField nullifier = randomScalar();
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();

        // Update a wallet using the nullifier
        (bytes memory updateSig, ValidWalletUpdateStatement memory updateStatement, PlonkProof memory updateProof) =
            updateWalletCalldata();
        TransferAuthorization memory transferAuthorization = emptyTransferAuthorization();
        updateStatement.previousNullifier = nullifier;
        updateStatement.merkleRoot = merkleRoot;
        darkpool.updateWallet(updateSig, transferAuthorization, updateStatement, updateProof);

        // Setup calldata
        BN254.ScalarField merkleRoot2 = darkpool.getMerkleRoot();
        Vm.Wallet memory receiverWallet = randomEthereumWallet();

        // Generate the calldata and redeem the fee
        (bytes memory redeemSig, ValidFeeRedemptionStatement memory statement, PlonkProof memory proof) =
            redeemFeeCalldata(merkleRoot2, receiverWallet);
        statement.walletNullifier = nullifier;
        vm.expectRevert(NullifierSetLib.NullifierAlreadySpent.selector);
        darkpool.redeemFee(redeemSig, statement, proof);
    }

    /// @notice Test redeeming a fee with a spent note nullifier
    function test_redeemFee_spentNoteNullifier() public {
        BN254.ScalarField nullifier = randomScalar();
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();

        // Update a wallet using the nullifier
        (bytes memory updateSig, ValidWalletUpdateStatement memory updateStatement, PlonkProof memory updateProof) =
            updateWalletCalldata();
        TransferAuthorization memory transferAuthorization = emptyTransferAuthorization();
        updateStatement.previousNullifier = nullifier;
        updateStatement.merkleRoot = merkleRoot;
        darkpool.updateWallet(updateSig, transferAuthorization, updateStatement, updateProof);

        // Setup calldata
        BN254.ScalarField merkleRoot2 = darkpool.getMerkleRoot();
        Vm.Wallet memory receiverWallet = randomEthereumWallet();

        // Generate the calldata and redeem the fee
        (bytes memory redeemSig, ValidFeeRedemptionStatement memory statement, PlonkProof memory proof) =
            redeemFeeCalldata(merkleRoot2, receiverWallet);
        statement.noteNullifier = nullifier;
        vm.expectRevert(NullifierSetLib.NullifierAlreadySpent.selector);
        darkpool.redeemFee(redeemSig, statement, proof);
    }

    /// @notice Test redeeming a fee with an invalid signature
    function test_redeemFee_invalidSignature() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        Vm.Wallet memory receiverWallet = randomEthereumWallet();

        // Generate the calldata and redeem the fee
        (bytes memory redeemSig, ValidFeeRedemptionStatement memory statement, PlonkProof memory proof) =
            redeemFeeCalldata(merkleRoot, receiverWallet);
        statement.newSharesCommitment = randomScalar();
        statement.walletRootKey = forgeWalletToRootKey(receiverWallet);
        vm.expectRevert(IDarkpool.InvalidSignature.selector);
        darkpool.redeemFee(redeemSig, statement, proof);
    }
}

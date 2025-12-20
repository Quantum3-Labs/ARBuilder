// SPDX-License-Identifier: MIT
/* solhint-disable gas-small-strings */
/* solhint-disable func-name-mixedcase */
pragma solidity ^0.8.24;

import { ERC20Mock } from "oz-contracts/mocks/token/ERC20Mock.sol";
import { BN254 } from "solidity-bn254/BN254.sol";

import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import { DarkpoolV2TestUtils } from "../DarkpoolV2TestUtils.sol";
import { PublicRelayerFeePaymentProofBundle } from "darkpoolv2-types/ProofBundles.sol";
import { ValidPublicRelayerFeePaymentStatement } from "darkpoolv2-lib/public_inputs/Fees.sol";
import { MerkleMountainLib } from "renegade-lib/merkle/MerkleMountain.sol";
import { Note } from "darkpoolv2-types/Note.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";

/// @title PublicRelayerFeeTest
/// @author Renegade Eng
/// @notice Tests for the public relayer fee payment functionality in DarkpoolV2
contract PublicRelayerFeeTest is DarkpoolV2TestUtils {
    using MerkleMountainLib for MerkleMountainLib.MerkleMountainRange;

    // Test state
    MerkleMountainLib.MerkleMountainRange private testMountain;
    ERC20Mock internal feeToken;
    address internal feeReceiver;

    /// @notice Set up the test environment
    function setUp() public override {
        super.setUp();
        feeToken = baseToken;
        feeReceiver = vm.randomAddress();
    }

    // -----------
    // | Helpers |
    // -----------

    /// @notice Create a Note for the fee payment
    /// @param receiver The receiver of the fee
    /// @param token The token to pay the fee in
    /// @param amount The amount of the fee
    /// @return note The created note
    function createNote(address receiver, address token, uint256 amount) internal returns (Note memory note) {
        note = Note({ mint: token, amount: amount, receiver: receiver, blinder: randomScalar() });
    }

    /// @notice Create a public relayer fee payment proof bundle
    /// @param note The note representing the fee payment
    /// @param merkleRoot The Merkle root for the balance
    /// @return proofBundle The created proof bundle
    function createPublicRelayerFeeProofBundle(
        Note memory note,
        BN254.ScalarField merkleRoot
    )
        internal
        returns (PublicRelayerFeePaymentProofBundle memory proofBundle)
    {
        BN254.ScalarField oldBalanceNullifier = randomScalar();
        BN254.ScalarField newBalanceCommitment = randomScalar();
        BN254.ScalarField recoveryId = randomScalar();
        BN254.ScalarField newRelayerFeeBalanceShare = randomScalar();
        uint256 merkleDepth = DarkpoolConstants.DEFAULT_MERKLE_DEPTH;

        ValidPublicRelayerFeePaymentStatement memory statement = ValidPublicRelayerFeePaymentStatement({
            merkleRoot: merkleRoot,
            oldBalanceNullifier: oldBalanceNullifier,
            newBalanceCommitment: newBalanceCommitment,
            recoveryId: recoveryId,
            newRelayerFeeBalanceShare: newRelayerFeeBalanceShare,
            note: note
        });

        proofBundle = PublicRelayerFeePaymentProofBundle({
            merkleDepth: merkleDepth,
            statement: statement,
            proof: createDummyProof()
        });
    }

    /// @notice Generate random public relayer fee payment calldata
    /// @return proofBundle The proof bundle for the fee payment
    function generateRandomFeePaymentCalldata()
        internal
        returns (PublicRelayerFeePaymentProofBundle memory proofBundle)
    {
        uint256 feeAmount = randomAmount();
        Note memory note = createNote(feeReceiver, address(feeToken), feeAmount);
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot(DarkpoolConstants.DEFAULT_MERKLE_DEPTH);
        proofBundle = createPublicRelayerFeeProofBundle(note, merkleRoot);

        // Capitalize the darkpool to have enough tokens for the fee payment (withdrawal)
        feeToken.mint(address(darkpool), feeAmount);
    }

    /// @notice Generate random public relayer fee payment calldata with a specific amount
    /// @param amount The amount of the fee
    /// @return proofBundle The proof bundle for the fee payment
    function generateFeePaymentCalldataWithAmount(uint256 amount)
        internal
        returns (PublicRelayerFeePaymentProofBundle memory proofBundle)
    {
        Note memory note = createNote(feeReceiver, address(feeToken), amount);
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot(DarkpoolConstants.DEFAULT_MERKLE_DEPTH);
        proofBundle = createPublicRelayerFeeProofBundle(note, merkleRoot);

        // Capitalize the darkpool for the fee payment
        feeToken.mint(address(darkpool), amount);
    }

    // ---------
    // | Tests |
    // ---------

    /// @notice Test a successful public relayer fee payment
    function test_payPublicRelayerFee_success() public {
        // Generate test data
        PublicRelayerFeePaymentProofBundle memory proofBundle = generateRandomFeePaymentCalldata();
        uint256 feeAmount = proofBundle.statement.note.amount;

        // Record balances before
        uint256 darkpoolBalanceBefore = feeToken.balanceOf(address(darkpool));
        uint256 receiverBalanceBefore = feeToken.balanceOf(feeReceiver);

        // Execute the fee payment
        darkpool.payPublicRelayerFee(proofBundle);

        // Check balances after
        uint256 darkpoolBalanceAfter = feeToken.balanceOf(address(darkpool));
        uint256 receiverBalanceAfter = feeToken.balanceOf(feeReceiver);
        assertEq(
            darkpoolBalanceAfter, darkpoolBalanceBefore - feeAmount, "Darkpool balance should decrease by fee amount"
        );
        assertEq(receiverBalanceAfter, receiverBalanceBefore + feeAmount, "Receiver balance should increase by fee");
    }

    /// @notice Test the Merkle root after a fee payment
    function test_payPublicRelayerFee_merkleRoot() public {
        // Generate test data
        PublicRelayerFeePaymentProofBundle memory proofBundle = generateRandomFeePaymentCalldata();

        // Execute the fee payment
        darkpool.payPublicRelayerFee(proofBundle);

        // Build a parallel merkle tree with the same operation
        uint256 depth = proofBundle.merkleDepth;
        testMountain.insertLeaf(depth, proofBundle.statement.newBalanceCommitment, hasher);
        BN254.ScalarField root = testMountain.getRoot(depth);

        // The root should be in the darkpool's history
        bool rootInHistory = darkpool.rootInHistory(root);
        assertTrue(rootInHistory, "Merkle root should be in history");
    }

    /// @notice Test fee payment with invalid Merkle root (not in history)
    function test_payPublicRelayerFee_invalidMerkleRoot_reverts() public {
        // Create a proof bundle with a random (invalid) Merkle root
        uint256 feeAmount = randomAmount();
        Note memory note = createNote(feeReceiver, address(feeToken), feeAmount);

        // Use a random Merkle root that is NOT in history
        BN254.ScalarField invalidMerkleRoot = randomScalar();
        PublicRelayerFeePaymentProofBundle memory proofBundle =
            createPublicRelayerFeeProofBundle(note, invalidMerkleRoot);

        // Capitalize the darkpool
        feeToken.mint(address(darkpool), feeAmount);

        // Should revert due to invalid Merkle root
        vm.expectRevert(IDarkpoolV2.InvalidMerkleRoot.selector);
        darkpool.payPublicRelayerFee(proofBundle);
    }

    /// @notice Test that double spending the same nullifier fails
    function test_payPublicRelayerFee_doubleSpendNullifier_reverts() public {
        // Generate test data
        PublicRelayerFeePaymentProofBundle memory proofBundle = generateRandomFeePaymentCalldata();

        // Execute the first fee payment
        darkpool.payPublicRelayerFee(proofBundle);

        // Second attempt with the same nullifier should fail
        vm.expectRevert(IDarkpoolV2.NullifierAlreadySpent.selector);
        darkpool.payPublicRelayerFee(proofBundle);
    }
}

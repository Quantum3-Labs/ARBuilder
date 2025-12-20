// SPDX-License-Identifier: MIT
/* solhint-disable gas-small-strings */
/* solhint-disable func-name-mixedcase */
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";

import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import { DarkpoolV2TestUtils } from "../DarkpoolV2TestUtils.sol";
import { PrivateProtocolFeePaymentProofBundle } from "darkpoolv2-types/ProofBundles.sol";
import { ValidPrivateProtocolFeePaymentStatement } from "darkpoolv2-lib/public_inputs/Fees.sol";
import { MerkleMountainLib } from "renegade-lib/merkle/MerkleMountain.sol";
import { ElGamalCiphertext, EncryptionKey, BabyJubJubPoint } from "renegade-lib/Ciphertext.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";

/// @title PrivateProtocolFeeTest
/// @author Renegade Eng
/// @notice Tests for the private protocol fee payment functionality in DarkpoolV2
contract PrivateProtocolFeeTest is DarkpoolV2TestUtils {
    using MerkleMountainLib for MerkleMountainLib.MerkleMountainRange;

    // Test state
    MerkleMountainLib.MerkleMountainRange private testMountain;

    /// @notice Set up the test environment
    function setUp() public override {
        super.setUp();
    }

    // -----------
    // | Helpers |
    // -----------

    /// @notice Create a dummy ElGamalCiphertext
    /// @return ciphertext The created ciphertext
    function createDummyCiphertext() internal returns (ElGamalCiphertext memory ciphertext) {
        BN254.ScalarField[] memory ciphertextData = new BN254.ScalarField[](3);
        ciphertextData[0] = randomScalar();
        ciphertextData[1] = randomScalar();
        ciphertextData[2] = randomScalar();

        ciphertext = ElGamalCiphertext({
            ephemeralKey: BabyJubJubPoint({ x: randomScalar(), y: randomScalar() }),
            ciphertext: ciphertextData
        });
    }

    /// @notice Create a private protocol fee payment proof bundle
    /// @param merkleRoot The Merkle root for the balance
    /// @param receiver The protocol fee receiver address
    /// @param encryptionKey The protocol encryption key
    /// @return proofBundle The created proof bundle
    function createPrivateProtocolFeeProofBundle(
        BN254.ScalarField merkleRoot,
        address receiver,
        EncryptionKey memory encryptionKey
    )
        internal
        returns (PrivateProtocolFeePaymentProofBundle memory proofBundle)
    {
        BN254.ScalarField oldBalanceNullifier = randomScalar();
        BN254.ScalarField newBalanceCommitment = randomScalar();
        BN254.ScalarField recoveryId = randomScalar();
        BN254.ScalarField newProtocolFeeBalanceShare = randomScalar();
        BN254.ScalarField noteCommitment = randomScalar();
        uint256 merkleDepth = DarkpoolConstants.DEFAULT_MERKLE_DEPTH;

        ValidPrivateProtocolFeePaymentStatement memory statement = ValidPrivateProtocolFeePaymentStatement({
            merkleRoot: merkleRoot,
            oldBalanceNullifier: oldBalanceNullifier,
            newBalanceCommitment: newBalanceCommitment,
            recoveryId: recoveryId,
            newProtocolFeeBalanceShare: newProtocolFeeBalanceShare,
            protocolFeeReceiver: receiver,
            noteCommitment: noteCommitment,
            noteCiphertext: createDummyCiphertext(),
            protocolEncryptionKey: encryptionKey
        });

        proofBundle = PrivateProtocolFeePaymentProofBundle({
            merkleDepth: merkleDepth,
            statement: statement,
            proof: createDummyProof()
        });
    }

    /// @notice Generate random private protocol fee payment calldata with valid protocol config
    /// @return proofBundle The proof bundle for the fee payment
    function generateRandomFeePaymentCalldata()
        internal
        returns (PrivateProtocolFeePaymentProofBundle memory proofBundle)
    {
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot(DarkpoolConstants.DEFAULT_MERKLE_DEPTH);
        address receiver = protocolFeeAddr;
        EncryptionKey memory encryptionKey = darkpool.protocolFeeKey();
        proofBundle = createPrivateProtocolFeeProofBundle(merkleRoot, receiver, encryptionKey);
    }

    // ---------
    // | Tests |
    // ---------

    /// @notice Test a successful private protocol fee payment
    function test_payPrivateProtocolFee_success() public {
        // Generate test data
        PrivateProtocolFeePaymentProofBundle memory proofBundle = generateRandomFeePaymentCalldata();

        // Execute the fee payment (should not revert)
        darkpool.payPrivateProtocolFee(proofBundle);
    }

    /// @notice Test the Merkle root after a private fee payment
    /// @dev Both the new balance commitment and note commitment should be inserted
    function test_payPrivateProtocolFee_merkleRoot() public {
        // Generate test data
        PrivateProtocolFeePaymentProofBundle memory proofBundle = generateRandomFeePaymentCalldata();

        // Execute the fee payment
        darkpool.payPrivateProtocolFee(proofBundle);

        // Build a parallel merkle tree with the same operations
        uint256 depth = proofBundle.merkleDepth;
        testMountain.insertLeaf(depth, proofBundle.statement.newBalanceCommitment, hasher);
        testMountain.insertLeaf(depth, proofBundle.statement.noteCommitment, hasher);
        BN254.ScalarField root = testMountain.getRoot(depth);

        // The root should be in the darkpool's history
        bool rootInHistory = darkpool.rootInHistory(root);
        assertTrue(rootInHistory, "Merkle root should be in history after both insertions");
    }

    /// @notice Test fee payment with invalid Merkle root (not in history)
    function test_payPrivateProtocolFee_invalidMerkleRoot_reverts() public {
        // Use a random Merkle root that is NOT in history
        BN254.ScalarField invalidMerkleRoot = randomScalar();
        address receiver = protocolFeeAddr;
        EncryptionKey memory encryptionKey = darkpool.protocolFeeKey();
        PrivateProtocolFeePaymentProofBundle memory proofBundle =
            createPrivateProtocolFeeProofBundle(invalidMerkleRoot, receiver, encryptionKey);

        // Should revert due to invalid Merkle root
        vm.expectRevert(IDarkpoolV2.InvalidMerkleRoot.selector);
        darkpool.payPrivateProtocolFee(proofBundle);
    }

    /// @notice Test that double spending the same nullifier fails
    function test_payPrivateProtocolFee_doubleSpendNullifier_reverts() public {
        // Generate test data
        PrivateProtocolFeePaymentProofBundle memory proofBundle = generateRandomFeePaymentCalldata();

        // Execute the first fee payment
        darkpool.payPrivateProtocolFee(proofBundle);

        // Second attempt with the same nullifier should fail
        vm.expectRevert(IDarkpoolV2.NullifierAlreadySpent.selector);
        darkpool.payPrivateProtocolFee(proofBundle);
    }

    /// @notice Test fee payment with wrong protocol fee receiver
    function test_payPrivateProtocolFee_wrongReceiver_reverts() public {
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot(DarkpoolConstants.DEFAULT_MERKLE_DEPTH);
        address wrongReceiver = vm.randomAddress();
        EncryptionKey memory encryptionKey = darkpool.protocolFeeKey();

        PrivateProtocolFeePaymentProofBundle memory proofBundle =
            createPrivateProtocolFeeProofBundle(merkleRoot, wrongReceiver, encryptionKey);

        // Should revert due to invalid protocol fee receiver
        vm.expectRevert(IDarkpoolV2.InvalidProtocolFeeReceiver.selector);
        darkpool.payPrivateProtocolFee(proofBundle);
    }

    /// @notice Test fee payment with wrong encryption key
    function test_payPrivateProtocolFee_wrongEncryptionKey_reverts() public {
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot(DarkpoolConstants.DEFAULT_MERKLE_DEPTH);
        address receiver = protocolFeeAddr;
        EncryptionKey memory wrongEncryptionKey = randomEncryptionKey();

        PrivateProtocolFeePaymentProofBundle memory proofBundle =
            createPrivateProtocolFeeProofBundle(merkleRoot, receiver, wrongEncryptionKey);

        // Should revert due to invalid protocol encryption key
        vm.expectRevert(IDarkpoolV2.InvalidProtocolFeeEncryptionKey.selector);
        darkpool.payPrivateProtocolFee(proofBundle);
    }
}

// SPDX-License-Identifier: MIT
/* solhint-disable gas-small-strings */
/* solhint-disable func-name-mixedcase */
pragma solidity ^0.8.24;

import { Vm } from "forge-std/Vm.sol";
import { BN254 } from "solidity-bn254/BN254.sol";

import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import { DarkpoolV2TestUtils } from "../DarkpoolV2TestUtils.sol";
import { PrivateRelayerFeePaymentProofBundle } from "darkpoolv2-types/ProofBundles.sol";
import { ValidPrivateRelayerFeePaymentStatement } from "darkpoolv2-lib/public_inputs/Fees.sol";
import { MerkleMountainLib } from "renegade-lib/merkle/MerkleMountain.sol";
import { ElGamalCiphertext, BabyJubJubPoint } from "renegade-lib/Ciphertext.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";
import { SignatureWithNonce } from "darkpoolv2-types/settlement/SignatureWithNonce.sol";
import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";

/// @title PrivateRelayerFeeTest
/// @author Renegade Eng
/// @notice Tests for the private relayer fee payment functionality in DarkpoolV2
contract PrivateRelayerFeeTest is DarkpoolV2TestUtils {
    using MerkleMountainLib for MerkleMountainLib.MerkleMountainRange;

    // Test state
    MerkleMountainLib.MerkleMountainRange private testMountain;
    Vm.Wallet private relayerWallet;

    /// @notice Set up the test environment
    function setUp() public override {
        super.setUp();
        // Create a wallet for the relayer to sign ciphertexts
        relayerWallet = vm.createWallet("relayer");
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

    /// @notice Create a signature with nonce for the ciphertext
    /// @param ciphertext The ciphertext to sign
    /// @param signerPrivateKey The private key of the signer
    /// @return signature The signature with nonce
    function signCiphertext(
        ElGamalCiphertext memory ciphertext,
        uint256 signerPrivateKey
    )
        internal
        returns (SignatureWithNonce memory signature)
    {
        // Hash the ciphertext bytes
        bytes memory ciphertextBytes = abi.encode(ciphertext);
        bytes32 ciphertextHash = EfficientHashLib.hash(ciphertextBytes);

        // Hash the ciphertext hash with a nonce
        uint256 nonce = randomUint();
        bytes32 signatureDigest = EfficientHashLib.hash(ciphertextHash, bytes32(nonce));

        // Create the signature
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(signerPrivateKey, signatureDigest);
        signature = SignatureWithNonce({ nonce: nonce, signature: abi.encodePacked(r, s, v) });
    }

    /// @notice Create a private relayer fee payment proof bundle
    /// @param merkleRoot The Merkle root for the balance
    /// @param receiver The relayer fee receiver address
    /// @param signerPrivateKey The private key to sign the ciphertext
    /// @return proofBundle The created proof bundle
    function createPrivateRelayerFeeProofBundle(
        BN254.ScalarField merkleRoot,
        address receiver,
        uint256 signerPrivateKey
    )
        internal
        returns (PrivateRelayerFeePaymentProofBundle memory proofBundle)
    {
        BN254.ScalarField oldBalanceNullifier = randomScalar();
        BN254.ScalarField newBalanceCommitment = randomScalar();
        BN254.ScalarField recoveryId = randomScalar();
        BN254.ScalarField newRelayerFeeBalanceShare = randomScalar();
        BN254.ScalarField noteCommitment = randomScalar();
        uint256 merkleDepth = DarkpoolConstants.DEFAULT_MERKLE_DEPTH;

        ElGamalCiphertext memory noteCiphertext = createDummyCiphertext();
        SignatureWithNonce memory relayerSignature = signCiphertext(noteCiphertext, signerPrivateKey);

        ValidPrivateRelayerFeePaymentStatement memory statement = ValidPrivateRelayerFeePaymentStatement({
            merkleRoot: merkleRoot,
            oldBalanceNullifier: oldBalanceNullifier,
            newBalanceCommitment: newBalanceCommitment,
            recoveryId: recoveryId,
            newRelayerFeeBalanceShare: newRelayerFeeBalanceShare,
            relayerFeeReceiver: receiver,
            noteCommitment: noteCommitment
        });

        proofBundle = PrivateRelayerFeePaymentProofBundle({
            merkleDepth: merkleDepth,
            noteCiphertext: noteCiphertext,
            relayerCiphertextSignature: relayerSignature,
            statement: statement,
            proof: createDummyProof()
        });
    }

    /// @notice Generate random private relayer fee payment calldata with valid relayer config
    /// @return proofBundle The proof bundle for the fee payment
    function generateRandomFeePaymentCalldata()
        internal
        returns (PrivateRelayerFeePaymentProofBundle memory proofBundle)
    {
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot(DarkpoolConstants.DEFAULT_MERKLE_DEPTH);
        proofBundle = createPrivateRelayerFeeProofBundle(merkleRoot, relayerWallet.addr, relayerWallet.privateKey);
    }

    // ---------
    // | Tests |
    // ---------

    /// @notice Test a successful private relayer fee payment
    function test_payPrivateRelayerFee_success() public {
        // Generate test data
        PrivateRelayerFeePaymentProofBundle memory proofBundle = generateRandomFeePaymentCalldata();

        // Execute the fee payment (should not revert)
        darkpool.payPrivateRelayerFee(proofBundle);
    }

    /// @notice Test the Merkle root after a private fee payment
    /// @dev Both the new balance commitment and note commitment should be inserted
    function test_payPrivateRelayerFee_merkleRoot() public {
        // Generate test data
        PrivateRelayerFeePaymentProofBundle memory proofBundle = generateRandomFeePaymentCalldata();

        // Execute the fee payment
        darkpool.payPrivateRelayerFee(proofBundle);

        // Build a parallel merkle tree with the same operations
        uint256 depth = proofBundle.merkleDepth;
        testMountain.insertLeaf(depth, proofBundle.statement.newBalanceCommitment, hasher);
        testMountain.insertLeaf(depth, proofBundle.statement.noteCommitment, hasher);
        BN254.ScalarField root = testMountain.getRoot(depth);

        // The root should be in the darkpool's history
        bool rootInHistory = darkpool.rootInHistory(root);
        assertTrue(rootInHistory, "Merkle root should be in history after both insertions");
    }

    /// @notice Test fee payment with invalid Merkle root
    function test_payPrivateRelayerFee_invalidMerkleRoot_reverts() public {
        // Use a random Merkle root that is NOT in history
        BN254.ScalarField invalidMerkleRoot = randomScalar();
        address receiver = relayerWallet.addr;
        PrivateRelayerFeePaymentProofBundle memory proofBundle =
            createPrivateRelayerFeeProofBundle(invalidMerkleRoot, receiver, relayerWallet.privateKey);

        // Should revert due to invalid Merkle root
        vm.expectRevert(IDarkpoolV2.InvalidMerkleRoot.selector);
        darkpool.payPrivateRelayerFee(proofBundle);
    }

    /// @notice Test that double spending the same signature nonce + nullifier fails
    function test_payPrivateRelayerFee_doubleSpend_reverts() public {
        // Generate test data
        PrivateRelayerFeePaymentProofBundle memory proofBundle = generateRandomFeePaymentCalldata();

        // Execute the first fee payment
        darkpool.payPrivateRelayerFee(proofBundle);

        // Second attempt with the same signature nonce + nullifier should fail
        vm.expectRevert(IDarkpoolV2.NonceAlreadySpent.selector);
        darkpool.payPrivateRelayerFee(proofBundle);
    }

    /// @notice Test fee payment with wrong relayer fee receiver
    function test_payPrivateRelayerFee_wrongReceiver_reverts() public {
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot(DarkpoolConstants.DEFAULT_MERKLE_DEPTH);
        address wrongReceiver = vm.randomAddress();
        PrivateRelayerFeePaymentProofBundle memory proofBundle =
            createPrivateRelayerFeeProofBundle(merkleRoot, wrongReceiver, relayerWallet.privateKey);

        // Should revert due to invalid relayer ciphertext signature (receiver doesn't match signer)
        vm.expectRevert(IDarkpoolV2.InvalidRelayerCiphertextSignature.selector);
        darkpool.payPrivateRelayerFee(proofBundle);
    }

    /// @notice Test fee payment with invalid signature (wrong signer)
    function test_payPrivateRelayerFee_invalidSignature_reverts() public {
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot(DarkpoolConstants.DEFAULT_MERKLE_DEPTH);
        address receiver = relayerWallet.addr;
        // Use wrong signer's private key (signature won't match receiver)
        PrivateRelayerFeePaymentProofBundle memory proofBundle =
            createPrivateRelayerFeeProofBundle(merkleRoot, receiver, wrongSigner.privateKey);

        // Should revert due to invalid relayer ciphertext signature
        vm.expectRevert(IDarkpoolV2.InvalidRelayerCiphertextSignature.selector);
        darkpool.payPrivateRelayerFee(proofBundle);
    }
}

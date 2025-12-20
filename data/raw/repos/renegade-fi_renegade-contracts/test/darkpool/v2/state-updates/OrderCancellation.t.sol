// SPDX-License-Identifier: MIT
/* solhint-disable gas-small-strings */
/* solhint-disable func-name-mixedcase */
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";

import { DarkpoolV2TestUtils } from "../DarkpoolV2TestUtils.sol";
import { OrderCancellationProofBundle } from "darkpoolv2-types/ProofBundles.sol";
import { OrderCancellationAuth } from "darkpoolv2-types/OrderCancellation.sol";
import { SignatureWithNonce } from "darkpoolv2-types/settlement/SignatureWithNonce.sol";
import { ValidOrderCancellationStatement } from "darkpoolv2-lib/public_inputs/OrderCancellation.sol";
import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";
import { NullifierLib } from "renegade-lib/NullifierSet.sol";

/// @title OrderCancellationTest
/// @author Renegade Eng
/// @notice Tests for the order cancellation functionality in DarkpoolV2
contract OrderCancellationTest is DarkpoolV2TestUtils {
    /// @notice Set up the test environment
    function setUp() public override {
        super.setUp();
    }

    // -----------
    // | Helpers |
    // -----------

    /// @notice Generate random order cancellation calldata (auth + proof bundle)
    /// @return auth The order cancellation authorization
    /// @return proofBundle The order cancellation proof bundle
    function generateRandomOrderCancellationCalldata()
        internal
        returns (OrderCancellationAuth memory auth, OrderCancellationProofBundle memory proofBundle)
    {
        proofBundle = createOrderCancellationProofBundle();
        auth = createOrderCancellationAuth(proofBundle.statement.oldIntentNullifier);
    }

    /// @notice Create an order cancellation auth for testing
    /// @param intentNullifier The intent nullifier to sign
    /// @return The order cancellation authorization
    function createOrderCancellationAuth(BN254.ScalarField intentNullifier)
        internal
        returns (OrderCancellationAuth memory)
    {
        // Generate a random nonce for replay protection
        uint256 nonce = vm.randomUint();

        // Sign H(nullifierHash || nonce)
        bytes32 nullifierHash = EfficientHashLib.hash(BN254.ScalarField.unwrap(intentNullifier));
        bytes32 signatureHash = EfficientHashLib.hash(nullifierHash, bytes32(nonce));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(intentOwner.privateKey, signatureHash);
        bytes memory signature = abi.encodePacked(r, s, v);

        return OrderCancellationAuth({ signature: SignatureWithNonce({ nonce: nonce, signature: signature }) });
    }

    /// @notice Create an order cancellation proof bundle for testing
    /// @return The order cancellation proof bundle
    function createOrderCancellationProofBundle() internal returns (OrderCancellationProofBundle memory) {
        BN254.ScalarField merkleRoot = randomScalar();
        BN254.ScalarField oldIntentNullifier = randomScalar();
        address owner = intentOwner.addr;

        ValidOrderCancellationStatement memory statement = ValidOrderCancellationStatement({
            merkleRoot: merkleRoot,
            oldIntentNullifier: oldIntentNullifier,
            owner: owner
        });

        return OrderCancellationProofBundle({ statement: statement, proof: createDummyProof() });
    }

    /// @notice Create an order cancellation auth with wrong signer
    /// @param intentNullifier The intent nullifier to sign
    /// @return The order cancellation authorization with wrong signer
    function createOrderCancellationAuthWrongSigner(BN254.ScalarField intentNullifier)
        internal
        returns (OrderCancellationAuth memory)
    {
        // Generate a random nonce for replay protection
        uint256 nonce = vm.randomUint();

        // Sign H(nullifierHash || nonce) with wrong signer
        bytes32 nullifierHash = EfficientHashLib.hash(BN254.ScalarField.unwrap(intentNullifier));
        bytes32 signatureHash = EfficientHashLib.hash(nullifierHash, bytes32(nonce));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(wrongSigner.privateKey, signatureHash);
        bytes memory signature = abi.encodePacked(r, s, v);

        return OrderCancellationAuth({ signature: SignatureWithNonce({ nonce: nonce, signature: signature }) });
    }

    // ---------
    // | Tests |
    // ---------

    /// @notice Test a successful order cancellation
    function test_orderCancellation_success() public {
        // Generate test data
        (OrderCancellationAuth memory auth, OrderCancellationProofBundle memory proofBundle) =
            generateRandomOrderCancellationCalldata();
        BN254.ScalarField intentNullifier = proofBundle.statement.oldIntentNullifier;

        // Check that the nullifier is spent only in the cancellation
        assertFalse(darkpool.nullifierSpent(intentNullifier), "Nullifier should not be spent before cancellation");
        darkpool.cancelOrder(auth, proofBundle);
        assertTrue(darkpool.nullifierSpent(intentNullifier), "Nullifier should be spent after cancellation");
    }

    /// @notice Test that a nullifier cannot be reused
    function test_orderCancellation_duplicateNullifier() public {
        // Generate test data
        OrderCancellationProofBundle memory proofBundle = createOrderCancellationProofBundle();
        OrderCancellationAuth memory auth = createOrderCancellationAuth(proofBundle.statement.oldIntentNullifier);

        // Execute the cancellation once
        darkpool.cancelOrder(auth, proofBundle);

        // Try to execute the same cancellation again with the same nullifier but a fresh nonce
        // Should revert because the nullifier is already spent
        OrderCancellationAuth memory auth2 = createOrderCancellationAuth(proofBundle.statement.oldIntentNullifier);
        vm.expectRevert(NullifierLib.NullifierAlreadySpent.selector);
        darkpool.cancelOrder(auth2, proofBundle);
    }

    /// @notice Test order cancellation with invalid signature
    function test_orderCancellation_invalidSignature() public {
        // Generate test data
        OrderCancellationProofBundle memory proofBundle = createOrderCancellationProofBundle();
        BN254.ScalarField intentNullifier = proofBundle.statement.oldIntentNullifier;

        // Create auth with wrong signer
        OrderCancellationAuth memory auth = createOrderCancellationAuthWrongSigner(intentNullifier);

        // Should revert due to invalid signature
        vm.expectRevert(IDarkpoolV2.InvalidOrderCancellationSignature.selector);
        darkpool.cancelOrder(auth, proofBundle);
    }
}

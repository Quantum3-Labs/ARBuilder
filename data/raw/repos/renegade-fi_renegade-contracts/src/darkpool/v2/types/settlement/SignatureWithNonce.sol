// SPDX-License-Identifier: Apache
pragma solidity ^0.8.24;

import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";
import { ECDSALib } from "renegade-lib/ECDSA.sol";
import { DarkpoolState, DarkpoolStateLib } from "darkpoolv2-lib/DarkpoolState.sol";

/// @notice A signature with a nonce
/// @dev We assume the signature is encoded in the format:
/// - r in the first 32 bytes
/// - s in the next 32 bytes
/// - v in the last byte
/// @dev We further assume that the signature is over the following:
/// H(H(message) || nonce)
struct SignatureWithNonce {
    /// @dev The nonce of the signature
    uint256 nonce;
    /// @dev The signature
    bytes signature;
}

/// @title Signature With Nonce Library
/// @author Renegade Eng
/// @notice Library for computing the hash of a signature with a nonce
library SignatureWithNonceLib {
    using DarkpoolStateLib for DarkpoolState;

    /// @notice Verify a signature with a nonce and spend the nonce
    /// @param signature The signature to verify
    /// @param expectedSigner The expected signer of the signature
    /// @param digest The bytes32 digest of the message to verify
    /// @param state The darkpool state to spend the nonce in
    /// @return Whether the signature is valid
    /// @dev Verifies the signature over H(digest || nonce) and always spends the nonce to prevent replay
    function verifyPrehashedAndSpendNonce(
        SignatureWithNonce memory signature,
        address expectedSigner,
        bytes32 digest,
        DarkpoolState storage state
    )
        internal
        returns (bool)
    {
        // Spend the nonce to prevent replay
        state.spendNonce(signature.nonce);

        // Verify the signature
        bytes32 signatureHash = EfficientHashLib.hash(digest, bytes32(signature.nonce));
        return ECDSALib.verify(signatureHash, signature.signature, expectedSigner);
    }
}

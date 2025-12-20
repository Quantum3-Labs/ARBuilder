// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { ECDSA } from "oz-contracts/utils/cryptography/ECDSA.sol";

/// @title ECDSALib
/// @author Renegade Eng
/// @notice Library for ECDSA operations
/// @dev This library is a thin wrapper around the ECDSA library from OpenZeppelin
library ECDSALib {
    /// @notice Error thrown when the signature length is invalid
    error InvalidSignatureLength();

    /// @notice The expected size of a serialized signature
    uint256 internal constant SIGNATURE_LENGTH = 65;

    /// @notice Verify a signature by recovering the signer address and comparing against an expected address
    /// @param digest The hash of the message to verify
    /// @param signature The signature to verify
    /// @param expectedSigner The expected signer address
    /// @return Whether the signature is valid
    function verify(bytes32 digest, bytes memory signature, address expectedSigner) internal pure returns (bool) {
        // Split the signature into r, s and v
        if (signature.length != SIGNATURE_LENGTH) revert InvalidSignatureLength();

        bytes32 r;
        bytes32 s;
        uint8 v;

        // Extract r, s, v from signature using assembly
        assembly {
            r := mload(add(signature, 0x20))
            s := mload(add(signature, 0x40))
            v := byte(0, mload(add(signature, 0x60)))
        }

        // Clients (notably ethers) sometimes use v = 0 or 1, the ecrecover precompile expects 27 or 28
        if (v == 0 || v == 1) {
            v += 27;
        }

        address recovered = ECDSA.recover(digest, v, r, s);
        return recovered == expectedSigner;
    }
}

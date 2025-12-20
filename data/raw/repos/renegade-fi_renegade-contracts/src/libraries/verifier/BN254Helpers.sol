// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import { BN254, Utils as BN254Util } from "solidity-bn254/BN254.sol";
import { Math } from "oz-contracts/utils/math/Math.sol";

/// @title Helper functions for BN254 curve operations
/// @author Renegade Eng
/// @notice This library contains utility functions for working with the BN254 curve
library BN254Helpers {
    /// @notice Zero in the scalar field
    BN254.ScalarField public constant ZERO = BN254.ScalarField.wrap(0);
    /// @notice One in the scalar field
    BN254.ScalarField public constant ONE = BN254.ScalarField.wrap(1);
    /// @notice Negative one in the scalar field
    BN254.ScalarField public constant NEG_ONE = BN254.ScalarField.wrap(BN254.R_MOD - 1);

    /// @dev The 2-adicity of the BN254 scalar field's modulus
    uint256 internal constant SCALAR_FIELD_TWO_ADICITY = 28;
    /// @dev The 2-adic root of unity for the BN254 scalar field
    BN254.ScalarField internal constant TWO_ADIC_ROOT = BN254.ScalarField.wrap(
        19_103_219_067_921_713_944_291_392_827_692_070_036_145_651_957_329_286_315_305_642_004_821_462_161_904
    );

    /// @notice Compute the nth root of unity for the BN254 scalar field
    /// @param n The exponent, assumed to be a power of 2
    /// @return The nth root of unity
    function rootOfUnity(uint256 n) internal pure returns (BN254.ScalarField) {
        uint256 log2n = Math.log2(n);

        // Compute the nth root from the base
        uint256 p = BN254.R_MOD;
        uint256 root = BN254.ScalarField.unwrap(TWO_ADIC_ROOT);
        assembly {
            for { let i := log2n } lt(i, SCALAR_FIELD_TWO_ADICITY) { i := add(i, 1) } { root := mulmod(root, root, p) }
        }

        return BN254.ScalarField.wrap(root);
    }

    /// @notice Compute the fifth power of a scalar field element
    /// @param a The scalar field element to raise to the fifth power
    /// @return The fifth power of the scalar field element
    function fifthPower(BN254.ScalarField a) internal pure returns (BN254.ScalarField) {
        BN254.ScalarField a2 = BN254.mul(a, a);
        BN254.ScalarField a4 = BN254.mul(a2, a2);
        BN254.ScalarField a5 = BN254.mul(a4, a);
        return a5;
    }

    // --- Serialization --- //

    /// @notice Converts a little-endian bytes array to a uint256
    /// @param buf The bytes32 array to convert
    /// @return The scalar field element
    function scalarFromLeBytes(bytes32 buf) internal pure returns (BN254.ScalarField) {
        uint256 scalarBytes = BN254Util.reverseEndianness(uint256(buf));
        return BN254.ScalarField.wrap(scalarBytes % BN254.R_MOD);
    }

    /// @notice Converts a scalar value to little-endian bytes
    /// @param scalar The scalar field element to convert
    /// @return The bytes representing the scalar
    function scalarToLeBytes(BN254.ScalarField scalar) internal pure returns (bytes32) {
        uint256 scalarBytes = BN254Util.reverseEndianness(BN254.ScalarField.unwrap(scalar));
        return bytes32(scalarBytes);
    }

    /// @notice Serialize a G1 point for a transcript
    /// @dev This implementation is taken from `solidity-bn254` with a final allocation removed
    /// @param point The point to serialize
    /// @return The serialized point
    function serializePoint(BN254.G1Point memory point) internal pure returns (bytes32) {
        uint256 mask = 0;

        // Set the 254-th bit to 1 for infinity
        // https://docs.rs/ark-serialize/0.3.0/src/ark_serialize/flags.rs.html#117
        if (BN254.isInfinity(point)) {
            mask |= 0x4000000000000000000000000000000000000000000000000000000000000000;
        }

        // Set the 255-th bit to 1 for positive Y
        // https://docs.rs/ark-serialize/0.3.0/src/ark_serialize/flags.rs.html#118
        if (!BN254.isYNegative(point)) {
            mask = 0x8000000000000000000000000000000000000000000000000000000000000000;
        }

        return bytes32(BN254Util.reverseEndianness(BN254.BaseField.unwrap(point.x) | mask));
    }
}

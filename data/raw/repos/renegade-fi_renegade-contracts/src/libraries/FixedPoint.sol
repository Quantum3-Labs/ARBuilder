// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice A fixed point representation of a real number
/// @dev The precision used is specified in `DarkpoolConstants.FIXED_POINT_PRECISION_BITS`
/// @dev The real number represented is `repr / 2^{FIXED_POINT_PRECISION_BITS}`
struct FixedPoint {
    /// @dev The representation of the number
    uint256 repr;
}

/// @title FixedPointLib
/// @author Renegade Eng
/// @notice A library for fixed point math
library FixedPointLib {
    /// @notice The fixed point precision used in the darkpool
    /// @dev This implies that the representation of a real number is floor(x * 2^{FIXED_POINT_PRECISION})
    uint256 internal constant FIXED_POINT_PRECISION_BITS = 63;
    /// @notice The maximum integer part bit-width that we can represent
    /// @dev This is done to match circuit logic where we limit bit width to prevent overflow
    uint256 internal constant MAX_INTEGER_PART_BITS = 63;

    // --- Conversions --- //

    /// @notice Wrap a uint256 into a FixedPoint
    /// @param x The uint256 to wrap
    /// @return A FixedPoint with the given representation
    function wrap(uint256 x) public pure returns (FixedPoint memory) {
        return FixedPoint({ repr: x });
    }

    /// @notice Generate a fixed point representation of a natural number
    /// @param x The integer to convert to a fixed point representation
    /// @return The fixed point representation of the integer
    function integerToFixedPoint(uint256 x) public pure returns (FixedPoint memory) {
        return FixedPoint({ repr: x * (1 << FIXED_POINT_PRECISION_BITS) });
    }

    /// @notice Convert a fixed point representation to an integer
    /// @param x The fixed point representation to convert
    /// @return The integer representation of the fixed point
    function fixedPointToInteger(FixedPoint memory x) public pure returns (uint256) {
        return x.repr / (1 << FIXED_POINT_PRECISION_BITS);
    }

    // --- Arithmetic --- //

    /// @notice Divide two fixed points and return the truncated result
    /// @param x The first fixed point to divide
    /// @param y The second fixed point to divide
    /// @return The truncated result of the division
    function div(FixedPoint memory x, FixedPoint memory y) public pure returns (FixedPoint memory) {
        uint256 repr = (x.repr * (1 << FIXED_POINT_PRECISION_BITS)) / y.repr;
        return FixedPoint({ repr: repr });
    }

    /// @notice Divide two integers and return a fixed point result
    /// @dev This avoids the overflow that occurs when converting both integers to fixed point first
    /// @param x The numerator (as an integer)
    /// @param y The denominator (as an integer)
    /// @return The fixed point result of x / y
    function divIntegers(uint256 x, uint256 y) public pure returns (FixedPoint memory) {
        uint256 repr = (x * (1 << FIXED_POINT_PRECISION_BITS)) / y;
        return FixedPoint({ repr: repr });
    }

    /// @notice Divide a fixed point by a scalar and return the truncated result
    /// @param x The fixed point to divide
    /// @param scalar The scalar to divide by
    /// @return The truncated result of the division
    function divByInteger(FixedPoint memory x, uint256 scalar) public pure returns (FixedPoint memory) {
        uint256 repr = x.repr / scalar;
        return FixedPoint({ repr: repr });
    }

    /// @notice Multiply a fixed point by a scalar and return the truncated result
    /// @dev Computes `(self.repr * scalar) / DarkpoolConstants.FIXED_POINT_PRECISION_BITS`
    /// @dev The repr already has the fixed point scaling value, so we only need to undo the
    /// @dev scaling once to get the desired result. Because division naturally truncates in
    /// @dev Solidity, we can use this will implement the floor of the above division.
    /// @dev This function is unsafe because it does not check for overflows
    /// @param self The fixed point to multiply
    /// @param scalar The scalar to multiply by
    /// @return The truncated result of the multiplication
    function unsafeFixedPointMul(FixedPoint memory self, uint256 scalar) public pure returns (uint256) {
        /// forge-lint: disable-next-line(incorrect-shift)
        return (self.repr * scalar) / (1 << FIXED_POINT_PRECISION_BITS);
    }

    /// @notice Divide an integer by a fixed point number and return the truncated integer result
    /// @dev Computes `(x * 2^FIXED_POINT_PRECISION_BITS) / y.repr`
    /// @dev Since y.repr = y_real * 2^FIXED_POINT_PRECISION_BITS, this gives us x / y_real
    /// @param x The integer numerator
    /// @param y The fixed point denominator
    /// @return The truncated integer result of x / y
    function divIntegerByFixedPoint(uint256 x, FixedPoint memory y) public pure returns (uint256) {
        return (x * (1 << FIXED_POINT_PRECISION_BITS)) / y.repr;
    }
}

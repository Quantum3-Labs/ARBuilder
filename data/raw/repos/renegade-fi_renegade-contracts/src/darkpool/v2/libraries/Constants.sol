// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";

/// @title DarkpoolConstants
/// @author Renegade Eng
/// @notice This library contains constants for the darkpool
library DarkpoolConstants {
    /// @notice The address used for native tokens in trade settlement
    /// @dev This is currently just ETH, but intentionally written abstractly
    address internal constant NATIVE_TOKEN_ADDRESS = 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE;
    /// @notice The default depth Merkle tree to insert state elements into
    uint256 internal constant DEFAULT_MERKLE_DEPTH = 10;
    /// @notice The maximum bitlength of an amount in the darkpool
    uint256 internal constant AMOUNT_BITS = 100;
    /// @notice The maximum relayer fee allowed by the darkpool (1%)
    /// @dev This is the representation of a fixed point value 0.01; i.e. `0.01 * FIXED_POINT_PRECISION`.
    uint256 internal constant MAX_RELAYER_FEE_REPR = 92_233_720_368_547_758;
    /// @notice The number of integral bits allowed for a price
    uint256 internal constant PRICE_INTEGRAL_BITS = 64;
    /// @notice The maximum price fixed point representation allowed
    /// @dev We allow PRICE_INTEGRAL_BITS integral bits for a price, and inherit the fractional bits from the fixed
    /// point precision.
    /// So the max price is `2 ** (FixedPointLib.FIXED_POINT_PRECISION_BITS + PRICE_INTEGRAL_BITS) - 1`.
    uint256 internal constant MAX_PRICE_REPR = 2 ** (FixedPointLib.FIXED_POINT_PRECISION_BITS + PRICE_INTEGRAL_BITS) - 1;

    /// @notice Get the maximum relayer fee as a FixedPoint struct
    /// @dev Returns the maximum relayer fee (1%) as a FixedPoint
    /// @return The maximum relayer fee as a FixedPoint struct
    function maxRelayerFee() public pure returns (FixedPoint memory) {
        return FixedPoint({ repr: MAX_RELAYER_FEE_REPR });
    }
    /// @notice The number of bits allowed in a price's representation
    /// @dev This includes the fixed point precision
    /// @dev This is the default fixed point precision plus 64 bits for the integral part

    uint256 internal constant PRICE_BITS = FixedPointLib.FIXED_POINT_PRECISION_BITS + 64;

    /// @notice Check whether an address is the native token address
    /// @param addr The address to check
    /// @return True if the address is the native token address, false otherwise
    function isNativeToken(address addr) public pure returns (bool) {
        return addr == NATIVE_TOKEN_ADDRESS;
    }

    /// @notice Check whether an amount is valid
    /// @param amount The amount to check
    function validateAmount(uint256 amount) public pure {
        if (amount > 2 ** AMOUNT_BITS - 1) {
            revert IDarkpoolV2.AmountTooLarge(amount);
        }
    }

    /// @notice Check whether a fee rate is valid
    /// @param feeRate The fee rate to check
    function validateFeeRate(FixedPoint memory feeRate) public pure {
        if (feeRate.repr > MAX_RELAYER_FEE_REPR) {
            revert IDarkpoolV2.FeeRateTooLarge(feeRate.repr);
        }
    }

    /// @notice Check whether a price is valid
    /// @param price The price to check
    function validatePrice(FixedPoint memory price) public pure {
        if (price.repr > 2 ** PRICE_BITS - 1) {
            revert IDarkpoolV2.PriceTooLarge(price.repr);
        }
    }
}

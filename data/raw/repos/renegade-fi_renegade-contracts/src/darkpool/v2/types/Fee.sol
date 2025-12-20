// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import { SimpleTransfer, SimpleTransferType } from "darkpoolv2-types/transfers/SimpleTransfer.sol";

/// @notice A fee rate for a match
struct FeeRate {
    /// @dev The fee rate
    FixedPoint rate;
    /// @dev The address to which the fee is paid
    address recipient;
}

/// @title FeeRateLib
/// @author Renegade Eng
/// @notice Library for fee rates
library FeeRateLib {
    using FixedPointLib for FixedPoint;

    /// @notice Error thrown when a fee rate is invalid
    error InvalidFeeRate();

    /// @notice Verify that a given fee rate is within allowable bounds
    /// @param feeRate The fee rate to verify
    /// @dev Reverts with InvalidFeeRate if the fee rate is out of bounds
    function validate(FeeRate memory feeRate) public pure {
        DarkpoolConstants.validateFeeRate(feeRate.rate);
    }

    /// @notice Compute a fee take from a fee rate and receive amount
    /// @param feeRate The fee rate to compute the fee take from
    /// @param receiveAmount The amount to compute the fee take for
    /// @return The fee take
    /// SAFETY: The fee rate is verified to be within bounds and the receive amount must be separately constrained to be
    /// with amount bounds. See `DarkpoolConstants.AMOUNT_BITS`.
    function computeFeeTake(
        FeeRate memory feeRate,
        address mint,
        uint256 receiveAmount
    )
        public
        pure
        returns (FeeTake memory)
    {
        validate(feeRate);
        uint256 fee = feeRate.rate.unsafeFixedPointMul(receiveAmount);
        return FeeTake({ mint: mint, fee: fee, recipient: feeRate.recipient });
    }
}

/// @notice A fee take for a match
/// @dev A fee take represents the fees due to a party in a match rather than the rate
struct FeeTake {
    /// @dev The mint of the token to withdraw
    address mint;
    /// @dev The fee due to the recipient
    uint256 fee;
    /// @dev The recipient of the fee
    address recipient;
}

/// @title FeeTakeLib
/// @author Renegade Eng
/// @notice Library for fee takes
library FeeTakeLib {
    /// @notice Build a withdrawal transfer for a fee take
    /// @param feeTake The fee take to build the withdrawal transfer for
    /// @return The withdrawal transfer
    function buildWithdrawalTransfer(FeeTake memory feeTake) public pure returns (SimpleTransfer memory) {
        return SimpleTransfer({
            account: feeTake.recipient,
            mint: feeTake.mint,
            amount: feeTake.fee,
            transferType: SimpleTransferType.Withdrawal
        });
    }
}

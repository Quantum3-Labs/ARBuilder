// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { FixedPoint } from "renegade-lib/FixedPoint.sol";

// This file contains types for fees due from trades in the darkpool

// -------------
// | Fee Types |
// -------------

/// @title FeeTake
/// @notice The fees due by a party in a match
struct FeeTake {
    /// @dev The fee due to the relayer
    uint256 relayerFee;
    /// @dev The fee due to the protocol
    uint256 protocolFee;
}

/// @title FeeTakeRate
/// @notice A pair of fee rates that generate a fee take when multiplied by a match amount
struct FeeTakeRate {
    /// @dev The relayer fee rate
    FixedPoint relayerFeeRate;
    /// @dev The protocol fee rate
    FixedPoint protocolFeeRate;
}

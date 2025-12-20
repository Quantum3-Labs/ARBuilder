// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";

import { BoundedMatchResult, BoundedMatchResultLib } from "darkpoolv2-types/BoundedMatchResult.sol";

import { DarkpoolV2TestUtils } from "../DarkpoolV2TestUtils.sol";

/// @title Bounded Match Result Test Utils
/// @notice Shared utilities for bounded match result tests
/// @author Renegade Eng
contract BoundedMatchResultTestUtils is DarkpoolV2TestUtils {
    using BoundedMatchResultLib for BoundedMatchResult;
    using FixedPointLib for FixedPoint;

    // ---------
    // | Utils |
    // ---------

    /// @notice Create a valid bounded match result with default parameters
    /// @return The bounded match result with valid bounds and future deadline
    function createValidBoundedMatchResult() internal returns (BoundedMatchResult memory) {
        uint256 minInternalPartyAmountIn = 100;
        uint256 maxInternalPartyAmountIn = 1000;
        uint256 blockDeadline = block.number + 100;

        return createBoundedMatchResult(
            address(baseToken), address(quoteToken), minInternalPartyAmountIn, maxInternalPartyAmountIn, blockDeadline
        );
    }

    /// @notice Create a bounded match result with custom deadline and default parameters
    /// @param blockDeadline The block deadline
    /// @return The bounded match result with default bounds and custom deadline
    function createBoundedMatchResultWithDeadline(uint256 blockDeadline) internal returns (BoundedMatchResult memory) {
        uint256 minInternalPartyAmountIn = 100;
        uint256 maxInternalPartyAmountIn = 1000;

        return createBoundedMatchResult(
            address(baseToken), address(quoteToken), minInternalPartyAmountIn, maxInternalPartyAmountIn, blockDeadline
        );
    }

    /// @notice Create a bounded match result with custom bounds and default parameters
    /// @param minInternalPartyAmountIn The minimum internal party amount in
    /// @param maxInternalPartyAmountIn The maximum internal party amount in
    /// @return The bounded match result with custom bounds and default deadline
    function createBoundedMatchResultWithBounds(
        uint256 minInternalPartyAmountIn,
        uint256 maxInternalPartyAmountIn
    )
        internal
        returns (BoundedMatchResult memory)
    {
        uint256 blockDeadline = block.number + 100;

        return createBoundedMatchResult(
            address(baseToken), address(quoteToken), minInternalPartyAmountIn, maxInternalPartyAmountIn, blockDeadline
        );
    }

    /// @notice Create a bounded match result with custom parameters (generates random price)
    /// @param inputToken The input token address
    /// @param outputToken The output token address
    /// @param minInternalPartyAmountIn The minimum internal party amount in
    /// @param maxInternalPartyAmountIn The maximum internal party amount in
    /// @param blockDeadline The block deadline
    /// @return The bounded match result
    function createBoundedMatchResult(
        address inputToken,
        address outputToken,
        uint256 minInternalPartyAmountIn,
        uint256 maxInternalPartyAmountIn,
        uint256 blockDeadline
    )
        internal
        returns (BoundedMatchResult memory)
    {
        FixedPoint memory price = randomPrice();
        return BoundedMatchResult({
            internalPartyInputToken: inputToken,
            internalPartyOutputToken: outputToken,
            price: price,
            minInternalPartyAmountIn: minInternalPartyAmountIn,
            maxInternalPartyAmountIn: maxInternalPartyAmountIn,
            blockDeadline: blockDeadline
        });
    }
}


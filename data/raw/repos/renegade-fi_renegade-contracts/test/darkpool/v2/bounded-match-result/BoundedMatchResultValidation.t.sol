// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

/* solhint-disable func-name-mixedcase */

import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";

import { BoundedMatchResult, BoundedMatchResultLib } from "darkpoolv2-types/BoundedMatchResult.sol";
import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";

import { BoundedMatchResultTestUtils } from "./Utils.sol";

contract BoundedMatchResultValidationTest is BoundedMatchResultTestUtils {
    using FixedPointLib for FixedPoint;
    using BoundedMatchResultLib for BoundedMatchResult;

    // -----------
    // | Helpers |
    // -----------

    /// @notice Wrapper to convert memory to calldata for library call
    function _validateBounds(BoundedMatchResult calldata boundedMatchResult) external pure {
        BoundedMatchResultLib.validateBounds(boundedMatchResult);
    }

    /// @notice Wrapper to convert memory to calldata for library call
    function _validateDeadline(BoundedMatchResult calldata boundedMatchResult) external view {
        BoundedMatchResultLib.validateDeadline(boundedMatchResult);
    }

    /// @notice Wrapper to convert memory to calldata for library call
    function _validateAmountIn(
        BoundedMatchResult calldata boundedMatchResult,
        uint256 externalPartyAmountIn
    )
        external
        pure
    {
        BoundedMatchResultLib.validateAmountIn(boundedMatchResult, externalPartyAmountIn);
    }

    /// @notice Wrapper to convert memory to calldata for library call
    function _computeInternalPartyAmountIn(
        BoundedMatchResult calldata boundedMatchResult,
        uint256 externalPartyAmountIn
    )
        external
        pure
        returns (uint256)
    {
        return BoundedMatchResultLib.computeInternalPartyAmountIn(boundedMatchResult, externalPartyAmountIn);
    }

    // ---------
    // | Tests |
    // ---------

    // --- validateBounds() --- //

    function test_validateBounds_invalidMinGreaterThanMax() public {
        BoundedMatchResult memory matchResult = createBoundedMatchResultWithBounds(
            1000, /* min */
            100 /* max */
        );

        // Should revert with InvalidBounds
        vm.expectRevert(IDarkpoolV2.InvalidBoundedMatchBounds.selector);
        this._validateBounds(matchResult);
    }

    function test_validateBounds_validMinEqualsMax() public {
        BoundedMatchResult memory matchResult = createBoundedMatchResultWithBounds(
            100, /* min */
            100 /* max */
        );

        // Should not revert - min == max is allowed
        this._validateBounds(matchResult);
    }

    function test_validateBounds_invalidAmountTooLarge() public {
        uint256 invalidAmount = 2 ** DarkpoolConstants.AMOUNT_BITS; // exceeds max

        // Test with min too large
        BoundedMatchResult memory matchResultMin = createBoundedMatchResultWithBounds(
            invalidAmount, /* min */
            1000 /* max */
        );

        // Should revert with AmountTooLarge
        vm.expectRevert(abi.encodeWithSelector(IDarkpoolV2.AmountTooLarge.selector, invalidAmount));
        this._validateBounds(matchResultMin);

        // Test with max too large
        BoundedMatchResult memory matchResultMax = createBoundedMatchResultWithBounds(
            100, /* min */
            invalidAmount /* max */
        );

        // Should revert with AmountTooLarge
        vm.expectRevert(abi.encodeWithSelector(IDarkpoolV2.AmountTooLarge.selector, invalidAmount));
        this._validateBounds(matchResultMax);
    }

    // --- validateDeadline() --- //

    function test_validateDeadline_expired() public {
        BoundedMatchResult memory matchResult = createBoundedMatchResultWithDeadline(block.number - 1); // Past deadline

        // Should revert with MatchExpired
        vm.expectRevert(IDarkpoolV2.BoundedMatchExpired.selector);
        this._validateDeadline(matchResult);
    }

    function test_validateDeadline_currentBlock() public {
        BoundedMatchResult memory matchResult = createBoundedMatchResultWithDeadline(block.number); // Current block

        // Should not revert (block.number == deadline is valid)
        this._validateDeadline(matchResult);
    }

    // --- validateAmountIn() --- //

    function test_validateAmountIn_zero() public {
        BoundedMatchResult memory matchResult = createValidBoundedMatchResult();

        // Should revert with ZeroAmount
        vm.expectRevert(IDarkpoolV2.BoundedMatchZeroAmount.selector);
        this._validateAmountIn(matchResult, 0);
    }

    function test_validateAmountIn_tooLow() public {
        BoundedMatchResult memory matchResult = createValidBoundedMatchResult();
        uint256 minInternalPartyAmountIn = matchResult.minInternalPartyAmountIn;
        uint256 maxInternalPartyAmountIn = matchResult.maxInternalPartyAmountIn;
        FixedPoint memory price = matchResult.price;

        // Choose external amount that results in internal amount below min
        uint256 minExternalAmount = price.unsafeFixedPointMul(minInternalPartyAmountIn);
        uint256 corruptedExternalPartyAmountIn = minExternalAmount - 1;

        // Should revert with AmountOutOfBounds
        vm.expectRevert(
            abi.encodeWithSelector(
                IDarkpoolV2.BoundedMatchAmountOutOfBounds.selector,
                minInternalPartyAmountIn - 1, // internalPartyAmountIn
                minInternalPartyAmountIn, // minInternalPartyAmountIn
                maxInternalPartyAmountIn // maxInternalPartyAmountIn
            )
        );
        this._validateAmountIn(matchResult, corruptedExternalPartyAmountIn);
    }

    function test_validateAmountIn_tooHigh() public {
        BoundedMatchResult memory matchResult = createValidBoundedMatchResult();
        uint256 minInternalPartyAmountIn = matchResult.minInternalPartyAmountIn;
        uint256 maxInternalPartyAmountIn = matchResult.maxInternalPartyAmountIn;
        FixedPoint memory price = matchResult.price;

        // Choose external amount that results in internal amount above max
        uint256 maxExternalAmount = price.unsafeFixedPointMul(maxInternalPartyAmountIn);
        uint256 corruptedExternalPartyAmountIn = maxExternalAmount * 2; // 2x to guarantee we're above bound

        uint256 computedInternalAmount = this._computeInternalPartyAmountIn(matchResult, corruptedExternalPartyAmountIn);

        // Should revert with AmountOutOfBounds
        vm.expectRevert(
            abi.encodeWithSelector(
                IDarkpoolV2.BoundedMatchAmountOutOfBounds.selector,
                computedInternalAmount, // internalPartyAmountIn
                minInternalPartyAmountIn, // minInternalPartyAmountIn
                maxInternalPartyAmountIn // maxInternalPartyAmountIn
            )
        );
        this._validateAmountIn(matchResult, corruptedExternalPartyAmountIn);
    }

    function test_validateAmountIn_amountTooLarge() public {
        BoundedMatchResult memory matchResult = createValidBoundedMatchResult();

        uint256 tooLargeAmount = 2 ** DarkpoolConstants.AMOUNT_BITS; // exceeds max

        // Should revert with AmountTooLarge
        vm.expectRevert(abi.encodeWithSelector(IDarkpoolV2.AmountTooLarge.selector, tooLargeAmount));
        this._validateAmountIn(matchResult, tooLargeAmount);
    }
}


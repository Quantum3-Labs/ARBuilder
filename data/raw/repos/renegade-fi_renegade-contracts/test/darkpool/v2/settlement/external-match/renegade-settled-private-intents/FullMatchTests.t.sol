// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

/* solhint-disable func-name-mixedcase */

import { BoundedMatchResult } from "darkpoolv2-types/BoundedMatchResult.sol";
import { BoundedMatchResultBundle } from "darkpoolv2-types/settlement/BoundedMatchResultBundle.sol";
import { FeeTake } from "darkpoolv2-types/Fee.sol";
import { SettlementBundle } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";
import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";

import { BalanceSnapshots, ExpectedDifferences } from "../../SettlementTestUtils.sol";
import { RenegadeSettledBoundedPrivateIntentTestUtils } from "./Utils.sol";
import { ERC20Mock } from "oz-contracts/mocks/token/ERC20Mock.sol";

contract FullMatchTests is RenegadeSettledBoundedPrivateIntentTestUtils {
    using FixedPointLib for FixedPoint;

    function setUp() public virtual override {
        super.setUp();
        // Mint max amounts of the base and quote tokens to the darkpool to capitalize fee payments
        uint256 maxAmt = 2 ** DarkpoolConstants.AMOUNT_BITS - 1;
        baseToken.mint(address(darkpool), maxAmt);
        quoteToken.mint(address(darkpool), maxAmt);
    }

    // -----------
    // | Helpers |
    // -----------

    /// @dev Create match data for a simulated trade
    function _createMatchData(bool isFirstFill)
        internal
        returns (
            SettlementObligation memory internalPartyObligation,
            SettlementObligation memory externalPartyObligation,
            BoundedMatchResultBundle memory matchBundle,
            SettlementBundle memory internalPartySettlementBundle
        )
    {
        // Create obligations for the trade
        FixedPoint memory price;
        (internalPartyObligation, externalPartyObligation, price) = createTradeObligations();

        // Create bounded match result and bundle
        BoundedMatchResult memory matchResult = createBoundedMatchResultForObligation(internalPartyObligation, price);
        matchBundle = createBoundedMatchResultBundleWithSigners(matchResult, executor.privateKey);

        // Create the internal party settlement bundle
        internalPartySettlementBundle = createRenegadeSettledBoundedBundle(isFirstFill, matchResult, oneTimeOwner);

        // Capitalize the parties for their obligations
        // For renegade-settled, internal party's capital is in darkpool (private balances)
        // External party uses normal EOA balances
        capitalizeExternalParty(externalPartyObligation);
    }

    // ---------
    // | Tests |
    // ---------

    // --- Valid Test Cases --- //

    /// @notice Test a basic bounded match settlement with first fill
    function test_boundedMatch_firstFill() public {
        // Create match data for first fill
        (
            SettlementObligation memory internalPartyObligation,
            SettlementObligation memory externalPartyObligation,
            BoundedMatchResultBundle memory matchBundle,
            SettlementBundle memory internalPartySettlementBundle
        ) =
            _createMatchData(
                true /* isFirstFill */
            );

        // Choose a trade size and build the actual obligations that will be used in settlement
        (uint256 externalPartyAmountIn,) =
            randomExternalPartyAmountIn(externalPartyObligation, matchBundle.permit.matchResult.price);
        address recipient = externalParty.addr;
        (SettlementObligation memory actualExternalObligation, SettlementObligation memory actualInternalObligation) =
            buildObligationsFromMatchResult(matchBundle.permit.matchResult, externalPartyAmountIn);

        // Compute fees that will be deducted from internal party's output
        (FeeTake memory relayerFeeTake, FeeTake memory protocolFeeTake) = computeMatchFees(actualInternalObligation);
        uint256 totalFee = relayerFeeTake.fee + protocolFeeTake.fee;

        // Set up expected differences accounting for fees
        // Internal party: No ERC20 changes (uses darkpool private balances)
        // External party: Normal ERC20 deposits/withdrawals
        // Darkpool: Loses internal party's input, gains external party's input minus fees
        ExpectedDifferences memory expectedDifferences = createEmptyExpectedDifferences();
        expectedDifferences.party0BaseChange = 0; // Internal party uses darkpool balances
        expectedDifferences.party0QuoteChange = 0; // Internal party uses darkpool balances
        expectedDifferences.party1BaseChange = int256(actualExternalObligation.amountOut);
        expectedDifferences.party1QuoteChange = -int256(actualExternalObligation.amountIn);
        expectedDifferences.relayerFeeBaseChange = 0;
        expectedDifferences.relayerFeeQuoteChange = int256(relayerFeeTake.fee);
        expectedDifferences.protocolFeeBaseChange = 0;
        expectedDifferences.protocolFeeQuoteChange = int256(protocolFeeTake.fee);
        expectedDifferences.darkpoolBaseChange = -int256(actualInternalObligation.amountIn); // Input token sent to
        // external party
        expectedDifferences.darkpoolQuoteChange = int256(actualExternalObligation.amountIn) - int256(totalFee); // Received
        // from external party minus fees

        // Check balances before and after settlement
        BalanceSnapshots memory preMatch = _captureBalances();
        vm.prank(externalParty.addr);
        darkpool.settleExternalMatch(externalPartyAmountIn, recipient, matchBundle, internalPartySettlementBundle);
        BalanceSnapshots memory postMatch = _captureBalances();
        _verifyBalanceChanges(preMatch, postMatch, expectedDifferences);
    }

    /// @notice Test a bounded match settlement with subsequent fill
    function test_boundedMatch_subsequentFill() public {
        // Create match data for subsequent fill
        (
            SettlementObligation memory internalPartyObligation,
            SettlementObligation memory externalPartyObligation,
            BoundedMatchResultBundle memory matchBundle,
            SettlementBundle memory internalPartySettlementBundle
        ) =
            _createMatchData(
                false /* isFirstFill */
            );

        // Choose a trade size and build the actual obligations that will be used in settlement
        (uint256 externalPartyAmountIn,) =
            randomExternalPartyAmountIn(externalPartyObligation, matchBundle.permit.matchResult.price);
        address recipient = externalParty.addr;
        (SettlementObligation memory actualExternalObligation, SettlementObligation memory actualInternalObligation) =
            buildObligationsFromMatchResult(matchBundle.permit.matchResult, externalPartyAmountIn);

        // Compute fees that will be deducted from internal party's output
        (FeeTake memory relayerFeeTake, FeeTake memory protocolFeeTake) = computeMatchFees(actualInternalObligation);
        uint256 totalFee = relayerFeeTake.fee + protocolFeeTake.fee;

        // Set up expected differences accounting for fees
        // Darkpool: Loses internal party's input, gains external party's input minus fees
        ExpectedDifferences memory expectedDifferences = createEmptyExpectedDifferences();
        expectedDifferences.party0BaseChange = 0; // Internal party uses darkpool balances
        expectedDifferences.party0QuoteChange = 0; // Internal party uses darkpool balances
        expectedDifferences.party1BaseChange = int256(actualExternalObligation.amountOut);
        expectedDifferences.party1QuoteChange = -int256(actualExternalObligation.amountIn);
        expectedDifferences.relayerFeeBaseChange = 0;
        expectedDifferences.relayerFeeQuoteChange = int256(relayerFeeTake.fee);
        expectedDifferences.protocolFeeBaseChange = 0;
        expectedDifferences.protocolFeeQuoteChange = int256(protocolFeeTake.fee);
        expectedDifferences.darkpoolBaseChange = -int256(actualInternalObligation.amountIn); // Input token sent to
        // external party
        expectedDifferences.darkpoolQuoteChange = int256(actualExternalObligation.amountIn) - int256(totalFee); // Received
        // from external party minus fees

        // Check balances before and after settlement
        BalanceSnapshots memory preMatch = _captureBalances();
        vm.prank(externalParty.addr);
        darkpool.settleExternalMatch(externalPartyAmountIn, recipient, matchBundle, internalPartySettlementBundle);
        BalanceSnapshots memory postMatch = _captureBalances();
        _verifyBalanceChanges(preMatch, postMatch, expectedDifferences);
    }
}


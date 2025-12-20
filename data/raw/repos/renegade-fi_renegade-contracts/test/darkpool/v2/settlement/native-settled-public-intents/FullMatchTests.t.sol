// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

/* solhint-disable func-name-mixedcase */

import { Intent } from "darkpoolv2-types/Intent.sol";
import { SettlementBundle } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { ObligationBundle, ObligationType } from "darkpoolv2-types/settlement/ObligationBundle.sol";
import { PublicIntentPermit, PublicIntentPermitLib } from "darkpoolv2-types/settlement/IntentBundle.sol";
import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";
import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { FeeTake } from "darkpoolv2-types/Fee.sol";
import { PublicIntentSettlementTestUtils } from "./Utils.sol";
import { ExpectedDifferences, SettlementTestUtils } from "../SettlementTestUtils.sol";

contract FullMatchTests is PublicIntentSettlementTestUtils {
    using PublicIntentPermitLib for PublicIntentPermit;
    using FixedPointLib for FixedPoint;

    // -----------
    // | Helpers |
    // -----------

    /// @dev Create match data for a simulated trade
    function _createMatchData()
        internal
        returns (
            PublicIntentPermit memory permit0,
            PublicIntentPermit memory permit1,
            SettlementObligation memory obligation0,
            SettlementObligation memory obligation1
        )
    {
        // Create obligations for the trade
        FixedPoint memory price;
        (obligation0, obligation1, price) = createTradeObligations();
        uint256 baseAmount = obligation0.amountIn;
        uint256 quoteAmount = obligation0.amountOut;

        // Create intent 0, sell the base for the quote
        uint256 minPriceRepr = price.repr / 2;
        uint256 intentSize0 = vm.randomUint(baseAmount, baseAmount * 2);
        Intent memory intent0 = Intent({
            inToken: address(baseToken),
            outToken: address(quoteToken),
            owner: party0.addr,
            minPrice: FixedPointLib.wrap(minPriceRepr),
            amountIn: intentSize0
        });
        permit0 = PublicIntentPermit({ intent: intent0, executor: executor.addr });

        // Create intent 1, buy the base for the quote
        uint256 minIntentSize1 = price.unsafeFixedPointMul(intentSize0);
        uint256 intentSize1 = vm.randomUint(minIntentSize1, minIntentSize1 * 2);
        FixedPoint memory minPriceFixed = FixedPointLib.divIntegers(baseAmount, quoteAmount);
        uint256 minPriceRepr1 = minPriceFixed.repr / 2;
        Intent memory intent1 = Intent({
            inToken: address(quoteToken),
            outToken: address(baseToken),
            owner: party1.addr,
            minPrice: FixedPointLib.wrap(minPriceRepr1),
            amountIn: intentSize1
        });
        permit1 = PublicIntentPermit({ intent: intent1, executor: executor.addr });

        // Capitalize the parties for their obligations
        capitalizeParty(party0.addr, intent0);
        capitalizeParty(party1.addr, intent1);
    }

    // ---------
    // | Tests |
    // ---------

    /// @notice Test a basic full match settlement
    function test_fullMatch_basic() public {
        // Create match data
        (
            PublicIntentPermit memory permit0,
            PublicIntentPermit memory permit1,
            SettlementObligation memory obligation0,
            SettlementObligation memory obligation1
        ) = _createMatchData();

        ObligationBundle memory obligationBundle =
            ObligationBundle({ obligationType: ObligationType.PUBLIC, data: abi.encode(obligation0, obligation1) });
        SettlementBundle memory party0Bundle = createPublicIntentSettlementBundleWithSigners(
            permit0.intent, obligation0, party0.privateKey, executor.privateKey
        );
        SettlementBundle memory party1Bundle = createPublicIntentSettlementBundleWithSigners(
            permit1.intent, obligation1, party1.privateKey, executor.privateKey
        );

        (FeeTake memory relayerFeeTake0, FeeTake memory protocolFeeTake0) = computeMatchFees(obligation0);
        (FeeTake memory relayerFeeTake1, FeeTake memory protocolFeeTake1) = computeMatchFees(obligation1);
        uint256 totalFee0 = relayerFeeTake0.fee + protocolFeeTake0.fee;
        uint256 totalFee1 = relayerFeeTake1.fee + protocolFeeTake1.fee;

        ExpectedDifferences memory expectedDifferences = createEmptyExpectedDifferences();
        expectedDifferences.party0BaseChange = -int256(obligation0.amountIn);
        expectedDifferences.party0QuoteChange = int256(obligation0.amountOut) - int256(totalFee0);
        expectedDifferences.party1BaseChange = int256(obligation1.amountOut) - int256(totalFee1);
        expectedDifferences.party1QuoteChange = -int256(obligation1.amountIn);
        expectedDifferences.relayerFeeBaseChange = int256(relayerFeeTake1.fee);
        expectedDifferences.relayerFeeQuoteChange = int256(relayerFeeTake0.fee);
        expectedDifferences.protocolFeeBaseChange = int256(protocolFeeTake1.fee);
        expectedDifferences.protocolFeeQuoteChange = int256(protocolFeeTake0.fee);
        expectedDifferences.darkpoolBaseChange = 0;
        expectedDifferences.darkpoolQuoteChange = 0;
        checkBalancesBeforeAndAfterSettlement(obligationBundle, party0Bundle, party1Bundle, expectedDifferences);

        // Verify the amount remaining on the intents
        bytes32 intentHash0 = permit0.computeHash();
        bytes32 intentHash1 = permit1.computeHash();
        uint256 expectedAmountRemaining0 = permit0.intent.amountIn - obligation0.amountIn;
        uint256 expectedAmountRemaining1 = permit1.intent.amountIn - obligation1.amountIn;
        assertEq(darkpool.openPublicIntents(intentHash0), expectedAmountRemaining0, "intent0 amount remaining");
        assertEq(darkpool.openPublicIntents(intentHash1), expectedAmountRemaining1, "intent1 amount remaining");
    }

    /// @notice Test a sequence of two fills for a public intent
    function test_fullMatch_multipleFills() public {
        // --- First Fill --- //

        // Create match data
        (
            PublicIntentPermit memory permit0,
            PublicIntentPermit memory permit1,
            SettlementObligation memory trade1Obligation0,
            SettlementObligation memory trade1Obligation1
        ) = _createMatchData();
        FixedPoint memory firstTradePrice = FixedPointLib.div(
            FixedPointLib.wrap(trade1Obligation0.amountOut), FixedPointLib.wrap(trade1Obligation0.amountIn)
        );

        ObligationBundle memory obligationBundle = ObligationBundle({
            obligationType: ObligationType.PUBLIC,
            data: abi.encode(trade1Obligation0, trade1Obligation1)
        });
        SettlementBundle memory party0Bundle = createPublicIntentSettlementBundleWithSigners(
            permit0.intent, trade1Obligation0, party0.privateKey, executor.privateKey
        );
        SettlementBundle memory party1Bundle = createPublicIntentSettlementBundleWithSigners(
            permit1.intent, trade1Obligation1, party1.privateKey, executor.privateKey
        );

        // Compute fees for first trade
        (FeeTake memory relayerFeeTake1_0, FeeTake memory protocolFeeTake1_0) = computeMatchFees(trade1Obligation0);
        (FeeTake memory relayerFeeTake1_1, FeeTake memory protocolFeeTake1_1) = computeMatchFees(trade1Obligation1);
        uint256 totalFee1_0 = relayerFeeTake1_0.fee + protocolFeeTake1_0.fee;
        uint256 totalFee1_1 = relayerFeeTake1_1.fee + protocolFeeTake1_1.fee;

        // Check balances for first settlement
        ExpectedDifferences memory expectedDifferences1 = createEmptyExpectedDifferences();
        expectedDifferences1.party0BaseChange = -int256(trade1Obligation0.amountIn);
        expectedDifferences1.party0QuoteChange = int256(trade1Obligation0.amountOut) - int256(totalFee1_0);
        expectedDifferences1.party1BaseChange = int256(trade1Obligation1.amountOut) - int256(totalFee1_1);
        expectedDifferences1.party1QuoteChange = -int256(trade1Obligation1.amountIn);
        expectedDifferences1.relayerFeeBaseChange = int256(relayerFeeTake1_1.fee);
        expectedDifferences1.relayerFeeQuoteChange = int256(relayerFeeTake1_0.fee);
        expectedDifferences1.protocolFeeBaseChange = int256(protocolFeeTake1_1.fee);
        expectedDifferences1.protocolFeeQuoteChange = int256(protocolFeeTake1_0.fee);
        expectedDifferences1.darkpoolBaseChange = 0;
        expectedDifferences1.darkpoolQuoteChange = 0;
        checkBalancesBeforeAndAfterSettlement(obligationBundle, party0Bundle, party1Bundle, expectedDifferences1);

        // --- Second Fill --- //

        // Sample a new trade size and setup a second fill
        uint256 maxParty0Input = darkpool.openPublicIntents(permit0.computeHash());
        uint256 party0Input = vm.randomUint(1, maxParty0Input);
        uint256 party0Output = firstTradePrice.unsafeFixedPointMul(party0Input);

        // Create new obligations
        SettlementObligation memory trade2Obligation0 = SettlementObligation({
            inputToken: trade1Obligation0.inputToken,
            outputToken: trade1Obligation0.outputToken,
            amountIn: party0Input,
            amountOut: party0Output
        });
        SettlementObligation memory trade2Obligation1 = SettlementObligation({
            inputToken: trade1Obligation1.inputToken,
            outputToken: trade1Obligation1.outputToken,
            amountIn: party0Output,
            amountOut: party0Input
        });
        ObligationBundle memory obligationBundle2 = ObligationBundle({
            obligationType: ObligationType.PUBLIC,
            data: abi.encode(trade2Obligation0, trade2Obligation1)
        });

        SettlementBundle memory party0Bundle2 = createPublicIntentSettlementBundleWithSigners(
            permit0.intent, trade2Obligation0, party0.privateKey, executor.privateKey
        );
        SettlementBundle memory party1Bundle2 = createPublicIntentSettlementBundleWithSigners(
            permit1.intent, trade2Obligation1, party1.privateKey, executor.privateKey
        );

        // Compute fees for second trade
        (FeeTake memory relayerFeeTake2_0, FeeTake memory protocolFeeTake2_0) = computeMatchFees(trade2Obligation0);
        (FeeTake memory relayerFeeTake2_1, FeeTake memory protocolFeeTake2_1) = computeMatchFees(trade2Obligation1);
        uint256 totalFee2_0 = relayerFeeTake2_0.fee + protocolFeeTake2_0.fee;
        uint256 totalFee2_1 = relayerFeeTake2_1.fee + protocolFeeTake2_1.fee;

        // Check balances for second settlement
        ExpectedDifferences memory expectedDifferences2 = createEmptyExpectedDifferences();
        expectedDifferences2.party0BaseChange = -int256(trade2Obligation0.amountIn);
        expectedDifferences2.party0QuoteChange = int256(trade2Obligation0.amountOut) - int256(totalFee2_0);
        expectedDifferences2.party1BaseChange = int256(trade2Obligation1.amountOut) - int256(totalFee2_1);
        expectedDifferences2.party1QuoteChange = -int256(trade2Obligation1.amountIn);
        expectedDifferences2.relayerFeeBaseChange = int256(relayerFeeTake2_1.fee);
        expectedDifferences2.relayerFeeQuoteChange = int256(relayerFeeTake2_0.fee);
        expectedDifferences2.protocolFeeBaseChange = int256(protocolFeeTake2_1.fee);
        expectedDifferences2.protocolFeeQuoteChange = int256(protocolFeeTake2_0.fee);
        expectedDifferences2.darkpoolBaseChange = 0;
        expectedDifferences2.darkpoolQuoteChange = 0;
        checkBalancesBeforeAndAfterSettlement(obligationBundle2, party0Bundle2, party1Bundle2, expectedDifferences2);

        // --- Verify State Updates --- //

        // Get the amount remaining in each intent
        uint256 party0Remaining2 = darkpool.openPublicIntents(permit0.computeHash());
        uint256 party1Remaining2 = darkpool.openPublicIntents(permit1.computeHash());
        uint256 expectedParty0Remaining =
            permit0.intent.amountIn - trade2Obligation0.amountIn - trade1Obligation0.amountIn;
        uint256 expectedParty1Remaining =
            permit1.intent.amountIn - trade2Obligation1.amountIn - trade1Obligation1.amountIn;

        assertEq(party0Remaining2, expectedParty0Remaining, "party0 remaining");
        assertEq(party1Remaining2, expectedParty1Remaining, "party1 remaining");
    }
}

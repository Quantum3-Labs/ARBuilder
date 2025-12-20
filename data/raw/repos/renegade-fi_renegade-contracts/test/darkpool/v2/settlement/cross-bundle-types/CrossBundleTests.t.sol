// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

/* solhint-disable func-name-mixedcase */

import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import { PartyId } from "darkpoolv2-lib/settlement/SettlementLib.sol";
import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";
import { SettlementBundle } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { ObligationBundle } from "darkpoolv2-types/settlement/ObligationBundle.sol";
import { FeeTake } from "darkpoolv2-types/Fee.sol";

import { CrossBundleTypesTestUtils } from "./Utils.sol";
import { ExpectedDifferences, SettlementTestUtils } from "../SettlementTestUtils.sol";

/// @title Cross Bundle Tests
/// @author Renegade Eng
/// @notice Tests for settling matches that cross different bundle types
contract CrossBundleTests is CrossBundleTypesTestUtils {
    function setUp() public virtual override {
        super.setUp();

        // Mint max amounts of the base and quote tokens to the darkpool to capitalize fee payments
        uint256 maxAmt = 2 ** DarkpoolConstants.AMOUNT_BITS - 1;
        baseToken.mint(address(darkpool), maxAmt);
        quoteToken.mint(address(darkpool), maxAmt);
    }

    /// @notice Cross a natively-settled public intent with a natively-settled private intent
    function test_mixedBundleTypes_nativePublicIntent_nativePrivateIntent() public {
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1,) = createTradeObligations();
        ObligationBundle memory obligationBundle = buildObligationBundle(obligation0, obligation1);

        // Create a natively-settled public intent
        bool party0IsPublic = vm.randomBool();
        SettlementBundle memory bundle0;
        SettlementBundle memory bundle1;
        if (party0IsPublic) {
            bundle0 = _createNativePublicIntentBundle(PartyId.PARTY_0, obligation0);
            bundle1 = _createNativePrivateIntentBundle(PartyId.PARTY_1, obligation1);
        } else {
            bundle0 = _createNativePrivateIntentBundle(PartyId.PARTY_0, obligation0);
            bundle1 = _createNativePublicIntentBundle(PartyId.PARTY_1, obligation1);
        }

        // Check the balances before settling
        (FeeTake memory relayerFeeTake0, FeeTake memory protocolFeeTake0) = computeMatchFees(obligation0);
        (FeeTake memory relayerFeeTake1, FeeTake memory protocolFeeTake1) = computeMatchFees(obligation1);
        uint256 totalFee0 = relayerFeeTake0.fee + protocolFeeTake0.fee;
        uint256 totalFee1 = relayerFeeTake1.fee + protocolFeeTake1.fee;

        // Party 0 is selling the base
        ExpectedDifferences memory expectedDifferences = createEmptyExpectedDifferences();
        expectedDifferences.party0BaseChange = -int256(obligation0.amountIn);
        expectedDifferences.party0QuoteChange = int256(obligation0.amountOut) - int256(totalFee0);
        expectedDifferences.party1BaseChange = int256(obligation1.amountOut) - int256(totalFee1);
        expectedDifferences.party1QuoteChange = -int256(obligation1.amountIn);
        expectedDifferences.relayerFeeBaseChange = int256(relayerFeeTake1.fee);
        expectedDifferences.relayerFeeQuoteChange = int256(relayerFeeTake0.fee);
        expectedDifferences.protocolFeeBaseChange = int256(protocolFeeTake1.fee);
        expectedDifferences.protocolFeeQuoteChange = int256(protocolFeeTake0.fee);
        checkBalancesBeforeAndAfterSettlement(obligationBundle, bundle0, bundle1, expectedDifferences);
    }

    /// @notice Cross a natively-settled public intent with a renegade settled private intent
    function test_mixedBundleTypes_nativePublicIntent_renegadeSettledIntent() public {
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1,) = createTradeObligations();
        ObligationBundle memory obligationBundle = buildObligationBundle(obligation0, obligation1);

        // Create a natively-settled public intent and a renegade settled intent
        bool party0IsPublic = vm.randomBool();
        SettlementBundle memory bundle0;
        SettlementBundle memory bundle1;
        if (party0IsPublic) {
            bundle0 = _createNativePublicIntentBundle(PartyId.PARTY_0, obligation0);
            bundle1 = _createRenegadeSettledPrivateIntentBundle(PartyId.PARTY_1, obligation1);
        } else {
            bundle0 = _createRenegadeSettledPrivateIntentBundle(PartyId.PARTY_0, obligation0);
            bundle1 = _createNativePublicIntentBundle(PartyId.PARTY_1, obligation1);
        }

        // Check the balances before settling
        (FeeTake memory relayerFeeTake0, FeeTake memory protocolFeeTake0) = computeMatchFees(obligation0);
        (FeeTake memory relayerFeeTake1, FeeTake memory protocolFeeTake1) = computeMatchFees(obligation1);
        uint256 totalFee0 = relayerFeeTake0.fee + protocolFeeTake0.fee;
        uint256 totalFee1 = relayerFeeTake1.fee + protocolFeeTake1.fee;

        // Party 0 is selling the base
        ExpectedDifferences memory expectedDifferences = createEmptyExpectedDifferences();
        expectedDifferences.party0BaseChange = party0IsPublic ? -int256(obligation0.amountIn) : int256(0);
        expectedDifferences.party0QuoteChange =
            party0IsPublic ? int256(obligation0.amountOut) - int256(totalFee0) : int256(0);
        expectedDifferences.party1BaseChange =
            party0IsPublic ? int256(0) : int256(obligation1.amountOut) - int256(totalFee1);
        expectedDifferences.party1QuoteChange = party0IsPublic ? int256(0) : -int256(obligation1.amountIn);
        expectedDifferences.relayerFeeBaseChange = int256(relayerFeeTake1.fee);
        expectedDifferences.relayerFeeQuoteChange = int256(relayerFeeTake0.fee);
        expectedDifferences.protocolFeeBaseChange = int256(protocolFeeTake1.fee);
        expectedDifferences.protocolFeeQuoteChange = int256(protocolFeeTake0.fee);

        uint256 baseTraded = obligation0.amountIn;
        uint256 quoteTraded = obligation1.amountIn;
        expectedDifferences.darkpoolBaseChange = party0IsPublic ? int256(baseTraded - totalFee1) : -int256(baseTraded);
        expectedDifferences.darkpoolQuoteChange =
            party0IsPublic ? -int256(quoteTraded) : int256(quoteTraded - totalFee0);
        checkBalancesBeforeAndAfterSettlement(obligationBundle, bundle0, bundle1, expectedDifferences);
    }

    /// @notice Cross a natively-settled private intent with a renegade settled private intent
    function test_mixedBundleTypes_nativePrivateIntent_renegadeSettledIntent() public {
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1,) = createTradeObligations();
        ObligationBundle memory obligationBundle = buildObligationBundle(obligation0, obligation1);

        // Create a natively-settled private intent and a renegade settled intent
        bool party0IsPublic = vm.randomBool();
        SettlementBundle memory bundle0;
        SettlementBundle memory bundle1;
        if (party0IsPublic) {
            bundle0 = _createNativePrivateIntentBundle(PartyId.PARTY_0, obligation0);
            bundle1 = _createRenegadeSettledPrivateIntentBundle(PartyId.PARTY_1, obligation1);
        } else {
            bundle0 = _createRenegadeSettledPrivateIntentBundle(PartyId.PARTY_0, obligation0);
            bundle1 = _createNativePrivateIntentBundle(PartyId.PARTY_1, obligation1);
        }

        // Check the balances before settling
        (FeeTake memory relayerFeeTake0, FeeTake memory protocolFeeTake0) = computeMatchFees(obligation0);
        (FeeTake memory relayerFeeTake1, FeeTake memory protocolFeeTake1) = computeMatchFees(obligation1);
        uint256 totalFee0 = relayerFeeTake0.fee + protocolFeeTake0.fee;
        uint256 totalFee1 = relayerFeeTake1.fee + protocolFeeTake1.fee;

        // Party 0 is selling the base
        ExpectedDifferences memory expectedDifferences = createEmptyExpectedDifferences();
        expectedDifferences.party0BaseChange = party0IsPublic ? -int256(obligation0.amountIn) : int256(0);
        expectedDifferences.party0QuoteChange =
            party0IsPublic ? int256(obligation0.amountOut) - int256(totalFee0) : int256(0);
        expectedDifferences.party1BaseChange =
            party0IsPublic ? int256(0) : int256(obligation1.amountOut) - int256(totalFee1);
        expectedDifferences.party1QuoteChange = party0IsPublic ? int256(0) : -int256(obligation1.amountIn);
        expectedDifferences.relayerFeeBaseChange = int256(relayerFeeTake1.fee);
        expectedDifferences.relayerFeeQuoteChange = int256(relayerFeeTake0.fee);
        expectedDifferences.protocolFeeBaseChange = int256(protocolFeeTake1.fee);
        expectedDifferences.protocolFeeQuoteChange = int256(protocolFeeTake0.fee);

        uint256 baseTraded = obligation0.amountIn;
        uint256 quoteTraded = obligation1.amountIn;
        expectedDifferences.darkpoolBaseChange = party0IsPublic ? int256(baseTraded - totalFee1) : -int256(baseTraded);
        expectedDifferences.darkpoolQuoteChange =
            party0IsPublic ? -int256(quoteTraded) : int256(quoteTraded - totalFee0);
        checkBalancesBeforeAndAfterSettlement(obligationBundle, bundle0, bundle1, expectedDifferences);
    }
}

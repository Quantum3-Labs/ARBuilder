// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

/* solhint-disable func-name-mixedcase */

import {
    PartyId,
    SettlementBundle,
    PublicIntentPublicBalanceBundle
} from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { PublicIntentPermit, PublicIntentPermitLib } from "darkpoolv2-types/settlement/IntentBundle.sol";
import { Intent } from "darkpoolv2-types/Intent.sol";
import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";
import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { NativeSettledPublicIntentLib } from "darkpoolv2-lib/settlement/NativeSettledPublicIntent.sol";
import { PublicIntentSettlementTestUtils } from "./Utils.sol";
import { SettlementContext } from "darkpoolv2-types/settlement/SettlementContext.sol";
import { ObligationBundle, ObligationLib } from "darkpoolv2-types/settlement/ObligationBundle.sol";

contract IntentConstraintsTest is PublicIntentSettlementTestUtils {
    using PublicIntentPermitLib for PublicIntentPermit;
    using FixedPointLib for FixedPoint;
    using ObligationLib for ObligationBundle;

    // -----------
    // | Helpers |
    // -----------

    /// @notice Wrapper to convert memory to calldata for library call
    function _validateSettlementBundleCalldata(
        PartyId partyId,
        ObligationBundle calldata obligationBundle,
        SettlementBundle calldata bundle
    )
        external
    {
        SettlementContext memory settlementContext = _createSettlementContext();
        NativeSettledPublicIntentLib.execute(partyId, obligationBundle, bundle, settlementContext, darkpoolState);
    }

    // ---------
    // | Tests |
    // ---------

    /// @notice Test that validation fails when intent and obligation have mismatched token pairs
    function test_validateObligationIntentConstraints_InvalidPair() public {
        // Create an intent for base -> quote
        (SettlementBundle memory bundle, ObligationBundle memory obligationBundle) = createSamplePublicIntentBundle();
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1) =
            obligationBundle.decodePublicObligationsMemory();

        // Corrupt the token pair
        address inputToken = address(quoteToken);
        address outputToken = address(baseToken);
        if (vm.randomBool()) {
            inputToken = address(weth);
        } else {
            outputToken = address(weth);
        }

        // Modify the obligation
        obligation0.inputToken = inputToken;
        obligation0.outputToken = outputToken;
        ObligationBundle memory corruptedObligationBundle = buildObligationBundle(obligation0, obligation1);

        PublicIntentPublicBalanceBundle memory bundleData = abi.decode(bundle.data, (PublicIntentPublicBalanceBundle));
        Intent memory intent = bundleData.auth.permit.intent;
        SettlementBundle memory newBundle = createPublicIntentSettlementBundle(intent, obligation0);

        // Expect the validation to revert with InvalidObligationPair
        vm.expectRevert(NativeSettledPublicIntentLib.InvalidObligationPair.selector);
        this._validateSettlementBundleCalldata(PartyId.PARTY_0, corruptedObligationBundle, newBundle);
    }

    /// @notice Test that validation fails when the input amount is larger than the intent amount
    function test_validateObligationIntentConstraints_InvalidAmountIn() public {
        // Create an intent and an obligation which is too large
        (SettlementBundle memory bundle, ObligationBundle memory obligationBundle) = createSamplePublicIntentBundle();
        PublicIntentPublicBalanceBundle memory bundleData = abi.decode(bundle.data, (PublicIntentPublicBalanceBundle));
        Intent memory intent = bundleData.auth.permit.intent;

        // Decode and corrupt the obligation
        (, SettlementObligation memory obligation1) = obligationBundle.decodePublicObligationsMemory();
        SettlementObligation memory corruptObligation0 = SettlementObligation({
            inputToken: address(baseToken),
            outputToken: address(quoteToken),
            amountIn: intent.amountIn + 1,
            amountOut: 200
        });
        ObligationBundle memory corruptedObligationBundle = buildObligationBundle(corruptObligation0, obligation1);
        SettlementBundle memory newBundle = createPublicIntentSettlementBundle(intent, corruptObligation0);

        // Expect the validation to revert with InvalidObligationAmountIn
        vm.expectRevert(
            abi.encodeWithSelector(
                NativeSettledPublicIntentLib.InvalidObligationAmountIn.selector,
                intent.amountIn, // amountRemaining
                intent.amountIn + 1 // amountIn (from obligation)
            )
        );
        this._validateSettlementBundleCalldata(PartyId.PARTY_0, corruptedObligationBundle, newBundle);
    }

    /// TODO: Add a test which fills a public intent multiple times, overfilling the intent
    /// on the second fill.

    /// @notice Test that validation fails when the implied price of the obligation is less than the minimum authorized
    /// price
    function test_validateObligationIntentConstraints_InvalidPrice() public {
        // Create an intent and an obligation which has a bad price
        (SettlementBundle memory bundle, ObligationBundle memory obligationBundle) = createSamplePublicIntentBundle();
        PublicIntentPublicBalanceBundle memory bundleData = abi.decode(bundle.data, (PublicIntentPublicBalanceBundle));
        Intent memory intent = bundleData.auth.permit.intent;
        (, SettlementObligation memory obligation1) = obligationBundle.decodePublicObligationsMemory();

        // Corrupt the obligation
        uint256 amountIn = vm.randomUint(1, intent.amountIn);
        uint256 minAmountOut = intent.minPrice.unsafeFixedPointMul(amountIn);
        uint256 amountOut = minAmountOut - 1;
        SettlementObligation memory obligation = SettlementObligation({
            inputToken: address(baseToken),
            outputToken: address(quoteToken),
            amountIn: amountIn,
            amountOut: amountOut
        });
        ObligationBundle memory corruptedObligationBundle = buildObligationBundle(obligation, obligation1);
        SettlementBundle memory newBundle = createPublicIntentSettlementBundle(intent, obligation);

        // Expect the validation to revert with InvalidObligationPrice
        vm.expectRevert(
            abi.encodeWithSelector(
                NativeSettledPublicIntentLib.InvalidObligationPrice.selector, amountOut, minAmountOut
            )
        );
        this._validateSettlementBundleCalldata(PartyId.PARTY_0, corruptedObligationBundle, newBundle);
    }
}

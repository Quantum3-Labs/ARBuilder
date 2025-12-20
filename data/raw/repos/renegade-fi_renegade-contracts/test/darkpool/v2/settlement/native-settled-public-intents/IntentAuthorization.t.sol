// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

/* solhint-disable func-name-mixedcase */

import {
    PartyId,
    SettlementBundle,
    SettlementBundleType,
    PublicIntentPublicBalanceBundle
} from "darkpoolv2-types/settlement/SettlementBundle.sol";
import {
    PublicIntentAuthBundle,
    PublicIntentPermit,
    PublicIntentPermitLib,
    SignatureWithNonce
} from "darkpoolv2-types/settlement/IntentBundle.sol";
import { ObligationBundle, ObligationLib } from "darkpoolv2-types/settlement/ObligationBundle.sol";
import { SettlementContext } from "darkpoolv2-types/settlement/SettlementContext.sol";
import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";
import { NativeSettledPublicIntentLib } from "darkpoolv2-lib/settlement/NativeSettledPublicIntent.sol";
import { PublicIntentSettlementTestUtils } from "./Utils.sol";
import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { FeeRate } from "darkpoolv2-types/Fee.sol";
import { DarkpoolStateLib } from "darkpoolv2-lib/DarkpoolState.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";

contract IntentAuthorizationTest is PublicIntentSettlementTestUtils {
    using PublicIntentPermitLib for PublicIntentPermit;
    using FixedPointLib for FixedPoint;
    using ObligationLib for ObligationBundle;

    // -----------
    // | Helpers |
    // -----------

    /// @notice Wrapper to convert memory to calldata for library call
    function _executeSettlementBundle(
        SettlementBundle calldata bundle,
        ObligationBundle calldata obligationBundle
    )
        external
        returns (SettlementContext memory)
    {
        SettlementContext memory settlementContext = _createSettlementContext();
        NativeSettledPublicIntentLib.execute(
            PartyId.PARTY_0, obligationBundle, bundle, settlementContext, darkpoolState
        );
        return settlementContext;
    }

    /// @notice Helper that accepts memory and calls library with calldata
    function authorizeIntentHelper(
        ObligationBundle memory obligationBundle,
        SettlementBundle memory bundle
    )
        internal
        returns (SettlementContext memory context)
    {
        context = this._executeSettlementBundle(bundle, obligationBundle);
    }

    // ---------
    // | Tests |
    // ---------

    function test_validSignatures() public {
        // Should not revert
        (SettlementBundle memory bundle, ObligationBundle memory obligationBundle) = createSamplePublicIntentBundle();
        authorizeIntentHelper(obligationBundle, bundle);
    }

    function test_intentReplay() public {
        // Create bundle and authorize it once
        (SettlementBundle memory bundle, ObligationBundle memory obligationBundle) = createSamplePublicIntentBundle();
        authorizeIntentHelper(obligationBundle, bundle);

        // Try settling the same bundle again, the intent should be replayed
        vm.expectRevert(DarkpoolStateLib.NonceAlreadySpent.selector);
        authorizeIntentHelper(obligationBundle, bundle);
    }

    function test_invalidIntentSignature_wrongSigner() public {
        // Create bundle and replace the intent signature with a wrong signature
        (SettlementBundle memory bundle, ObligationBundle memory obligationBundle) = createSamplePublicIntentBundle();
        PublicIntentPublicBalanceBundle memory bundleData = abi.decode(bundle.data, (PublicIntentPublicBalanceBundle));
        PublicIntentAuthBundle memory authBundle = bundleData.auth;
        SignatureWithNonce memory sig = signIntentPermit(authBundle.permit, wrongSigner.privateKey);
        authBundle.intentSignature = sig;
        bundleData.auth = authBundle;
        bundle.data = abi.encode(bundleData);

        // Should revert with InvalidIntentSignature
        vm.expectRevert(NativeSettledPublicIntentLib.InvalidIntentSignature.selector);
        authorizeIntentHelper(obligationBundle, bundle);
    }

    function test_invalidIntentSignature_modifiedBytes() public {
        // Create bundle with modified intent signature
        (SettlementBundle memory bundle, ObligationBundle memory obligationBundle) = createSamplePublicIntentBundle();
        PublicIntentPublicBalanceBundle memory bundleData = abi.decode(bundle.data, (PublicIntentPublicBalanceBundle));
        PublicIntentAuthBundle memory authBundle = bundleData.auth;
        authBundle.intentSignature.signature[0] = bytes1(uint8(authBundle.intentSignature.signature[0]) ^ 0xFF); // Modify
            // signature
        bundleData.auth = authBundle;
        bundle.data = abi.encode(bundleData);

        // Should revert with ECDSAInvalidSignature (from OpenZeppelin ECDSA library)
        vm.expectRevert();
        authorizeIntentHelper(obligationBundle, bundle);
    }

    function test_invalidExecutorSignature_wrongSigner() public {
        // Create bundle with executor signature from wrong signer
        (SettlementBundle memory bundle, ObligationBundle memory obligationBundle) = createSamplePublicIntentBundle();
        PublicIntentPublicBalanceBundle memory bundleData = abi.decode(bundle.data, (PublicIntentPublicBalanceBundle));
        SettlementObligation memory obligation0 = obligationBundle.decodePublicObligationMemory(PartyId.PARTY_0);

        // Corrupt the executor signature by signing with wrong signer
        SignatureWithNonce memory sig =
            createExecutorSignature(bundleData.relayerFeeRate, obligation0, wrongSigner.privateKey);
        bundleData.auth.executorSignature = sig;
        bundle.data = abi.encode(bundleData);

        // Should revert with InvalidExecutorSignature
        vm.expectRevert(IDarkpoolV2.InvalidExecutorSignature.selector);
        authorizeIntentHelper(obligationBundle, bundle);
    }

    function test_cachedIntentSignature() public {
        // Create bundle and authorize it once
        (SettlementBundle memory bundle, ObligationBundle memory obligationBundle) = createSamplePublicIntentBundle();
        authorizeIntentHelper(obligationBundle, bundle);

        // Verify the intent was cached in the mapping
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1) =
            obligationBundle.decodePublicObligationsMemory();
        PublicIntentPublicBalanceBundle memory bundleData = abi.decode(bundle.data, (PublicIntentPublicBalanceBundle));
        PublicIntentAuthBundle memory authBundle = bundleData.auth;

        bytes32 intentHash = authBundle.permit.computeHash();
        uint256 amountRemaining = darkpoolState.openPublicIntents[intentHash];
        uint256 expectedAmountRemaining = authBundle.permit.intent.amountIn - obligation0.amountIn;
        assertEq(amountRemaining, expectedAmountRemaining, "Intent not cached");

        // Now create a second bundle with the same intent but invalid owner signature
        // This should still pass because we skip signature verification for cached intents
        PublicIntentAuthBundle memory authBundle2 = authBundle;
        authBundle2.intentSignature.signature = hex"deadbeef"; // Invalid signature

        // Setup an obligation for a smaller amount
        obligation0.amountIn = randomUint(1, amountRemaining);
        uint256 minAmountOut = authBundle2.permit.intent.minPrice.unsafeFixedPointMul(obligation0.amountIn);
        obligation0.amountOut = minAmountOut + 1;
        FeeRate memory feeRate2 = relayerFeeRate();
        authBundle2.executorSignature = createExecutorSignature(feeRate2, obligation0, executor.privateKey);
        ObligationBundle memory obligationBundle2 = buildObligationBundle(obligation0, obligation1);

        // Create the second bundle
        PublicIntentPublicBalanceBundle memory bundleData2 =
            PublicIntentPublicBalanceBundle({ auth: authBundle2, relayerFeeRate: feeRate2 });
        SettlementBundle memory bundle2 = SettlementBundle({
            isFirstFill: false,
            bundleType: SettlementBundleType.NATIVELY_SETTLED_PUBLIC_INTENT,
            data: abi.encode(bundleData2)
        });

        // Should not revert even with invalid intent signature because it's cached
        authorizeIntentHelper(obligationBundle2, bundle2);
    }
}

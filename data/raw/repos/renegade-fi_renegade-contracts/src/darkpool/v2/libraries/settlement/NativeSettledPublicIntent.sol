// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {
    BoundedMatchResultBundle,
    BoundedMatchResultPermit,
    BoundedMatchResultPermitLib
} from "darkpoolv2-types/settlement/BoundedMatchResultBundle.sol";
import {
    PartyId,
    PublicIntentPublicBalanceBundle,
    SettlementBundle,
    SettlementBundleLib
} from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { ObligationBundle, ObligationLib } from "darkpoolv2-types/settlement/ObligationBundle.sol";
import {
    PublicIntentAuthBundle,
    PublicIntentPermit,
    PublicIntentPermitLib
} from "darkpoolv2-types/settlement/IntentBundle.sol";
import { SettlementObligation, SettlementObligationLib } from "darkpoolv2-types/Obligation.sol";
import { Intent, IntentLib } from "darkpoolv2-types/Intent.sol";
import { SettlementContext, SettlementContextLib } from "darkpoolv2-types/settlement/SettlementContext.sol";
import { SimpleTransfer } from "darkpoolv2-types/transfers/SimpleTransfer.sol";
import { DarkpoolState, DarkpoolStateLib } from "darkpoolv2-lib/DarkpoolState.sol";
import { FeeRate, FeeRateLib, FeeTake, FeeTakeLib } from "darkpoolv2-types/Fee.sol";

import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { SignatureWithNonce, SignatureWithNonceLib } from "darkpoolv2-types/settlement/SignatureWithNonce.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";

/// @title Native Settled Public Intent Library
/// @author Renegade Eng
/// @notice Library for validating a natively settled public intent
/// @dev A natively settled public intent is a public intent with a public (EOA) balance.
library NativeSettledPublicIntentLib {
    using FixedPointLib for FixedPoint;
    using SignatureWithNonceLib for SignatureWithNonce;
    using SettlementBundleLib for SettlementBundle;
    using SettlementBundleLib for PublicIntentPublicBalanceBundle;
    using ObligationLib for ObligationBundle;
    using SettlementObligationLib for SettlementObligation;
    using PublicIntentPermitLib for PublicIntentPermit;
    using BoundedMatchResultPermitLib for BoundedMatchResultPermit;
    using SettlementContextLib for SettlementContext;
    using DarkpoolStateLib for DarkpoolState;
    using FeeRateLib for FeeRate;
    using FeeTakeLib for FeeTake;

    /// @notice Error thrown when an intent signature is invalid
    error InvalidIntentSignature();
    /// @notice Error thrown when an intent and obligation pair is invalid
    error InvalidObligationPair();
    /// @notice Error thrown when the input amount on the obligation is invalid
    error InvalidObligationAmountIn(uint256 amountRemaining, uint256 amountIn);
    /// @notice Error thrown when the implied price of the obligation does not meet the
    /// minimum authorized price
    error InvalidObligationPrice(uint256 amountOut, uint256 minAmountOut);

    /// @notice Validate and execute a public intent and public balance settlement bundle
    /// @dev Note that in contrast to other settlement bundle types, no balance obligation
    /// constraints are checked here. The balance constraint is implicitly checked by transferring
    /// into the darkpool.
    /// @param partyId The party ID to execute the settlement bundle for
    /// @param obligationBundle The obligation bundle to validate
    /// @param settlementBundle The settlement bundle to validate
    /// @param settlementContext The settlement context to which we append post-validation updates.
    /// @param state The darkpool state containing all storage references
    function execute(
        PartyId partyId,
        ObligationBundle calldata obligationBundle,
        SettlementBundle calldata settlementBundle,
        SettlementContext memory settlementContext,
        DarkpoolState storage state
    )
        internal
    {
        // Decode the settlement bundle data
        PublicIntentPublicBalanceBundle memory bundleData = settlementBundle.decodePublicBundleData();
        SettlementObligation memory obligation = obligationBundle.decodePublicObligation(partyId);

        // Verify that the executor has signed the settlement obligation
        validateObligationAuthorization(bundleData, obligation, state);

        executeInner(bundleData, obligation, settlementContext, state);
    }

    /// @notice Validate and execute a public intent and public balance settlement bundle for a bounded match
    /// @param matchBundle The bounded match result authorization bundle to validate
    /// @param obligation The settlement obligation to validate
    /// @param settlementBundle The settlement bundle to validate
    /// @param settlementContext The settlement context to which we append post-validation updates.
    /// @param state The darkpool state containing all storage references
    function executeBoundedMatch(
        BoundedMatchResultBundle calldata matchBundle,
        SettlementObligation memory obligation,
        SettlementBundle calldata settlementBundle,
        SettlementContext memory settlementContext,
        DarkpoolState storage state
    )
        internal
    {
        // Decode the settlement bundle data
        PublicIntentPublicBalanceBundle memory bundleData = settlementBundle.decodePublicBundleData();

        // Verify that the executor has signed the bounded match result, authorizing the settlement obligation derived
        // from it
        validateBoundedMatchResultAuthorization(bundleData, matchBundle, state);

        executeInner(bundleData, obligation, settlementContext, state);
    }

    /// @notice Execute a public intent and public balance settlement bundle
    /// @param bundleData The validated bundle data
    /// @param obligation The validated settlement obligation
    /// @param settlementContext The settlement context to which we append post-validation updates.
    /// @param state The darkpool state containing all storage references
    function executeInner(
        PublicIntentPublicBalanceBundle memory bundleData,
        SettlementObligation memory obligation,
        SettlementContext memory settlementContext,
        DarkpoolState storage state
    )
        private
    {
        // 1. Validate the intent authorization
        (uint256 amountRemaining, bytes32 intentHash) = validatePublicIntentAuthorization(bundleData, state);

        // 2. Validate the intent and balance constraints on the obligation
        Intent memory intent = bundleData.auth.permit.intent;
        validateObligationIntentConstraints(amountRemaining, intent, obligation);

        // 3. Execute the state updates necessary to settle the bundle
        FeeRate memory relayerFeeRate = bundleData.relayerFeeRate;
        FeeRate memory protocolFeeRate = state.getProtocolFeeRate(obligation.inputToken, obligation.outputToken);
        executeStateUpdates(intentHash, intent, obligation, relayerFeeRate, protocolFeeRate, settlementContext, state);
    }

    // ------------------------
    // | Intent Authorization |
    // ------------------------

    /// @notice Validate the authorization of a public intent
    /// @dev We require that the intent owner has signed a tuple of (executor, intent). This authorizes the intent to be
    /// filled by the executor.
    /// @param bundleData The auth bundle data to validate
    /// @param state The darkpool state containing all storage references
    /// @return amountRemaining The amount remaining on the intent
    /// @return intentHash The hash of the intent
    function validatePublicIntentAuthorization(
        PublicIntentPublicBalanceBundle memory bundleData,
        DarkpoolState storage state
    )
        internal
        returns (uint256 amountRemaining, bytes32 intentHash)
    {
        PublicIntentAuthBundle memory auth = bundleData.auth;

        // If the intent is already in the mapping, we need not check its owner's signature
        intentHash = auth.permit.computeHash();
        amountRemaining = state.getOpenIntentAmountRemaining(intentHash);
        if (amountRemaining > 0) {
            return (amountRemaining, intentHash);
        }

        // If the intent is not in the mapping, this is its first fill, and we must verify the signature
        bool sigValid = auth.intentSignature.verifyPrehashedAndSpendNonce(auth.permit.intent.owner, intentHash, state);
        if (!sigValid) revert InvalidIntentSignature();

        // Verify the intent's fields on its first fill
        IntentLib.validate(auth.permit.intent);

        // Now that we've authorized the intent, update the amount remaining mapping
        amountRemaining = auth.permit.intent.amountIn;
        state.setOpenIntentAmountRemaining(intentHash, amountRemaining);
        return (amountRemaining, intentHash);
    }

    // ----------------------------
    // | Obligation Authorization |
    // ----------------------------

    /// @notice Validate the authorization of a settlement obligation
    /// @dev We require that the executor has signed the settlement obligation. This authorizes the individual fill
    /// parameters.
    /// @param bundleData The auth bundle data to validate
    /// @param obligation The settlement obligation to validate
    /// @param state The darkpool state containing all storage references
    function validateObligationAuthorization(
        PublicIntentPublicBalanceBundle memory bundleData,
        SettlementObligation memory obligation,
        DarkpoolState storage state
    )
        internal
    {
        PublicIntentAuthBundle memory auth = bundleData.auth;

        // Verify that the executor has signed the settlement obligation
        bytes32 executorDigest = bundleData.computeExecutorDigest(obligation);
        bool executorValid =
            auth.executorSignature.verifyPrehashedAndSpendNonce(auth.permit.executor, executorDigest, state);
        if (!executorValid) revert IDarkpoolV2.InvalidExecutorSignature();
    }

    // -------------------------------
    // | Bounded Match Authorization |
    // -------------------------------

    /// @notice Validate the authorization of a bounded match result
    /// @dev We require that the executor signed the bounded match result, which authorizes any obligations derived from
    /// the match result to be settled.
    /// @param bundleData The auth bundle data to validate
    /// @param matchBundle The bounded match result authorization bundle to validate
    /// @param state The darkpool state containing all storage references
    function validateBoundedMatchResultAuthorization(
        PublicIntentPublicBalanceBundle memory bundleData,
        BoundedMatchResultBundle calldata matchBundle,
        DarkpoolState storage state
    )
        internal
    {
        PublicIntentAuthBundle memory auth = bundleData.auth;
        BoundedMatchResultPermit memory permit = matchBundle.permit;

        // Verify that the executor has signed the bounded match result
        bytes32 matchResultHash = permit.computeHash();
        bool executorValid =
            matchBundle.executorSignature.verifyPrehashedAndSpendNonce(auth.permit.executor, matchResultHash, state);
        if (!executorValid) revert IDarkpoolV2.InvalidExecutorSignature();
    }

    // --------------------------
    // | Obligation Constraints |
    // --------------------------

    /// @notice Validate the constraints on the settlement obligation
    /// @param amountRemaining The amount remaining on the intent
    /// @param intent The intent to validate
    /// @param obligation The settlement obligation to validate
    function validateObligationIntentConstraints(
        uint256 amountRemaining,
        Intent memory intent,
        SettlementObligation memory obligation
    )
        internal
        pure
    {
        // Verify that the pair matches the intent
        bool pairValid = intent.inToken == obligation.inputToken && intent.outToken == obligation.outputToken;
        if (!pairValid) revert InvalidObligationPair();

        // Verify that the input amount does not exceed the authorized amount remaining
        if (amountRemaining < obligation.amountIn) {
            revert InvalidObligationAmountIn(amountRemaining, obligation.amountIn);
        }

        // Lastly, the obligation must be matched at a price that is *at least* the minimum authorized price
        // The price here is in units of `outToken/inToken`
        uint256 minAmountOut = intent.minPrice.unsafeFixedPointMul(obligation.amountIn);
        if (obligation.amountOut < minAmountOut) revert InvalidObligationPrice(obligation.amountOut, minAmountOut);
    }

    // -----------------
    // | State Updates |
    // -----------------

    /// @notice Execute the state updates necessary to settle the bundle
    /// @param intentHash The hash of the intent
    /// @param intent The intent to update
    /// @param obligation The settlement obligation to update
    /// @param relayerFeeRate The relayer fee rate to update
    /// @param protocolFeeRate The protocol fee rate to update
    /// @param settlementContext The settlement context to which we append post-validation updates.
    /// @param state The darkpool state containing all storage references
    function executeStateUpdates(
        bytes32 intentHash,
        Intent memory intent,
        SettlementObligation memory obligation,
        FeeRate memory relayerFeeRate,
        FeeRate memory protocolFeeRate,
        SettlementContext memory settlementContext,
        DarkpoolState storage state
    )
        internal
    {
        // Compute the fee takes for the match
        (FeeTake memory relayerFeeTake, FeeTake memory protocolFeeTake) =
            computeFeeTakes(obligation, relayerFeeRate, protocolFeeRate);

        // Add transfers to settle the obligation
        // Deposit the input token into the darkpool
        SimpleTransfer memory deposit = obligation.buildPermit2AllowanceDeposit(intent.owner);
        settlementContext.pushDeposit(deposit);

        // Withdraw the output token from the darkpool to the intent owner
        uint256 totalFee = relayerFeeTake.fee + protocolFeeTake.fee;
        SimpleTransfer memory withdrawal = obligation.buildWithdrawalTransfer(intent.owner, totalFee);
        settlementContext.pushWithdrawal(withdrawal);

        // Withdraw the relayer and protocol fees to their respective recipients
        SimpleTransfer memory relayerWithdrawal = relayerFeeTake.buildWithdrawalTransfer();
        SimpleTransfer memory protocolWithdrawal = protocolFeeTake.buildWithdrawalTransfer();
        settlementContext.pushWithdrawal(relayerWithdrawal);
        settlementContext.pushWithdrawal(protocolWithdrawal);

        // Update the amount remaining on the intent
        state.decrementOpenIntentAmountRemaining(intentHash, obligation.amountIn);
    }

    /// @notice Compute the fee takes for the match
    /// @param obligation The settlement obligation to compute fee takes for
    /// @param relayerFeeRate The relayer fee rate to compute fee takes for
    /// @param protocolFeeRate The protocol fee rate to compute fee takes for
    /// @return relayerFeeTake The relayer fee take
    /// @return protocolFeeTake The protocol fee take
    function computeFeeTakes(
        SettlementObligation memory obligation,
        FeeRate memory relayerFeeRate,
        FeeRate memory protocolFeeRate
    )
        internal
        pure
        returns (FeeTake memory relayerFeeTake, FeeTake memory protocolFeeTake)
    {
        uint256 receiveAmount = obligation.amountOut;
        address receiveToken = obligation.outputToken;
        relayerFeeTake = relayerFeeRate.computeFeeTake(receiveToken, receiveAmount);
        protocolFeeTake = protocolFeeRate.computeFeeTake(receiveToken, receiveAmount);
    }
}

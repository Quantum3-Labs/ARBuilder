// SPDX-License-Identifier: Apache
pragma solidity ^0.8.24;

import { PartyId, SettlementBundle } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import {
    RenegadeSettledPrivateFirstFillBundle,
    RenegadeSettledPrivateFillBundle
} from "darkpoolv2-lib/settlement/bundles/RenegadeSettledPrivateFillLib.sol";
import {
    ObligationBundle, ObligationLib, PrivateObligationBundle
} from "darkpoolv2-types/settlement/ObligationBundle.sol";
import { SettlementContext } from "darkpoolv2-types/settlement/SettlementContext.sol";
import { DarkpoolState } from "darkpoolv2-lib/DarkpoolState.sol";
import { DarkpoolContracts } from "darkpoolv2-contracts/DarkpoolV2.sol";
import { RenegadeSettledPrivateFillLib as RenegadeSettledPrivateFillBundleLib } from
    "darkpoolv2-lib/settlement/bundles/RenegadeSettledPrivateFillLib.sol";

/// @title Renegade Settled Private Fill Library
/// @author Renegade Eng
/// @notice Library for validating renegade settled private fills
/// @dev A renegade settled private fill is a private intent with a private (darkpool) balance where
/// the settlement obligation itself is private.
/// @dev Because the only difference between this settlement bundle type and the `RENEGADE_SETTLED_INTENT` bundle is
/// that the obligations are private, much of the handler logic is the same between the two cases.
/// In particular, intent authorization is the exact same, and state updates are the same except that we pull
/// shares from a different statement type.
library RenegadeSettledPrivateFillLib {
    using ObligationLib for ObligationBundle;
    using RenegadeSettledPrivateFillBundleLib for SettlementBundle;

    // --- Errors --- //

    /// @notice Error thrown when the owner signature is invalid
    error InvalidOwnerSignature();

    // --- Implementation --- //

    /// @notice Execute a renegade settled private fill bundle
    /// @param partyId The party ID to execute the settlement bundle for
    /// @param obligationBundle The obligation bundle to execute
    /// @param settlementBundle The settlement bundle to execute
    /// @param settlementContext The settlement context to which we append post-execution updates.
    /// @param contracts The contract references needed for settlement
    /// @param state The darkpool state containing all storage references
    function execute(
        PartyId partyId,
        ObligationBundle calldata obligationBundle,
        SettlementBundle calldata settlementBundle,
        SettlementContext memory settlementContext,
        DarkpoolContracts memory contracts,
        DarkpoolState storage state
    )
        internal
    {
        if (settlementBundle.isFirstFill) {
            executeFirstFill(partyId, obligationBundle, settlementBundle, settlementContext, contracts, state);
        } else {
            executeSubsequentFill(partyId, obligationBundle, settlementBundle, settlementContext, contracts, state);
        }
    }

    /// @notice Execute the state updates necessary to settle the bundle for a first fill
    /// @param partyId The party ID to execute the settlement bundle for
    /// @param obligationBundle The obligation bundle to execute
    /// @param settlementBundle The settlement bundle to execute
    /// @param settlementContext The settlement context to which we append post-execution updates.
    /// @param contracts The contract references needed for settlement
    /// @param state The darkpool state containing all storage references
    function executeFirstFill(
        PartyId partyId,
        ObligationBundle calldata obligationBundle,
        SettlementBundle calldata settlementBundle,
        SettlementContext memory settlementContext,
        DarkpoolContracts memory contracts,
        DarkpoolState storage state
    )
        internal
    {
        RenegadeSettledPrivateFirstFillBundle memory bundleData =
            settlementBundle.decodeRenegadeSettledPrivateFirstFillBundle();
        PrivateObligationBundle memory obligation = obligationBundle.decodePrivateObligation();

        // 1. Authorize the intent and input balance
        RenegadeSettledPrivateFillBundleLib.authorizeAndUpdateIntentAndBalance(
            partyId, bundleData, obligation, settlementContext, contracts, state
        );

        // 2. Validate the output balance validity
        RenegadeSettledPrivateFillBundleLib.authorizeAndUpdateOutputBalance(
            partyId, bundleData.outputBalanceBundle, obligation, settlementContext, contracts, state
        );
    }

    /// @notice Execute the state updates necessary to settle the bundle for a subsequent fill
    /// @param partyId The party ID to execute the settlement bundle for
    /// @param obligationBundle The obligation bundle to execute
    /// @param settlementBundle The settlement bundle to execute
    /// @param settlementContext The settlement context to which we append post-execution updates.
    /// @param contracts The contract references needed for settlement
    /// @param state The darkpool state containing all storage references
    function executeSubsequentFill(
        PartyId partyId,
        ObligationBundle calldata obligationBundle,
        SettlementBundle calldata settlementBundle,
        SettlementContext memory settlementContext,
        DarkpoolContracts memory contracts,
        DarkpoolState storage state
    )
        internal
    {
        RenegadeSettledPrivateFillBundle memory bundleData = settlementBundle.decodeRenegadeSettledPrivateBundle();
        PrivateObligationBundle memory obligation = obligationBundle.decodePrivateObligation();

        // 1. Authorize the intent and input balance
        RenegadeSettledPrivateFillBundleLib.authorizeAndUpdateIntentAndBalance(
            partyId, bundleData, obligation, settlementContext, contracts, state
        );

        // 2. Validate the output balance validity
        RenegadeSettledPrivateFillBundleLib.authorizeAndUpdateOutputBalance(
            partyId, bundleData.outputBalanceBundle, obligation, settlementContext, contracts, state
        );
    }
}

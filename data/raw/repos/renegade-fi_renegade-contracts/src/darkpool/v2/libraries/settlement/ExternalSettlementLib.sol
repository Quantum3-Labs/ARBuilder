// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { IWETH9 } from "renegade-lib/interfaces/IWETH9.sol";
import { IHasher } from "renegade-lib/interfaces/IHasher.sol";
import { IPermit2 } from "permit2-lib/interfaces/IPermit2.sol";
import { IVerifier } from "darkpoolv2-interfaces/IVerifier.sol";
import { IVkeys } from "darkpoolv2-interfaces/IVkeys.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";

import { BoundedMatchResultBundle } from "darkpoolv2-types/settlement/BoundedMatchResultBundle.sol";
import { BoundedMatchResultLib } from "darkpoolv2-types/BoundedMatchResult.sol";
import {
    SettlementBundle,
    SettlementBundleType,
    SettlementBundleLib
} from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { SettlementObligation, SettlementObligationLib } from "darkpoolv2-types/Obligation.sol";
import { SettlementContext, SettlementContextLib } from "darkpoolv2-types/settlement/SettlementContext.sol";
import { SimpleTransfer } from "darkpoolv2-types/transfers/SimpleTransfer.sol";
import { NativeSettledPublicIntentLib } from "./NativeSettledPublicIntent.sol";
import { NativeSettledPrivateIntentLib } from "./NativeSettledPrivateIntent.sol";
import { RenegadeSettledPrivateIntentLib } from "./RenegadeSettledPrivateIntent.sol";
import { DarkpoolContracts } from "darkpoolv2-contracts/DarkpoolV2.sol";
import { DarkpoolState } from "darkpoolv2-lib/DarkpoolState.sol";
import { SettlementLib } from "./SettlementLib.sol";
import { SettlementVerification } from "./SettlementVerification.sol";

/// @title ExternalSettlementLib
/// @author Renegade Eng
/// @notice Library for external settlement operations
library ExternalSettlementLib {
    using SettlementBundleLib for SettlementBundle;
    using SettlementContextLib for SettlementContext;
    using SettlementObligationLib for SettlementObligation;

    /// @notice Settle a trade with an external party who decides the trade size
    /// @param state The darkpool state containing all storage references
    /// @param contracts The contract references needed for settlement
    /// @param externalPartyAmountIn The input amount for the trade
    /// @param recipient The recipient of the withdrawal
    /// @param matchBundle The bounded match result bundle
    /// @param internalPartySettlementBundle The settlement bundle for the internal party
    function settleExternalMatch(
        DarkpoolState storage state,
        DarkpoolContracts memory contracts,
        uint256 externalPartyAmountIn,
        address recipient,
        BoundedMatchResultBundle calldata matchBundle,
        SettlementBundle calldata internalPartySettlementBundle
    )
        external
    {
        // Allocate a settlement context
        SettlementContext memory settlementContext = allocateExternalSettlementContext(internalPartySettlementBundle);

        // Build settlement obligations from the bounded match result and external party amount in
        (SettlementObligation memory externalObligation, SettlementObligation memory internalObligation) =
            BoundedMatchResultLib.buildObligations(matchBundle.permit.matchResult, externalPartyAmountIn);

        // Validate and authorize the settlement bundles
        executeExternalSettlementBundle(
            matchBundle, internalObligation, internalPartySettlementBundle, settlementContext, contracts, state
        );

        // Allocate transfers for external party
        // Authorization is implied by virtue of the external party being the one settling
        allocateExternalMatchSettlementTransfers(recipient, externalObligation, settlementContext);

        // Execute the transfers necessary for settlement
        // The helpers above will push transfers to the settlement context if necessary
        SettlementLib.executeTransfers(settlementContext, contracts);

        // Verify the proofs necessary for settlement
        // The helpers above will push proofs to the settlement context if necessary
        SettlementVerification.verifySettlementProofs(settlementContext, contracts.verifier);
    }

    // --- Allocation --- //

    /// @notice Allocate a settlement context for an external match
    /// @dev The number of transfers and proofs for the external party is known: (1 deposit + 1 withdrawal + 0 proofs)
    /// @param internalPartySettlementBundle The settlement bundle for the internal party
    /// @return The allocated settlement context
    function allocateExternalSettlementContext(SettlementBundle calldata internalPartySettlementBundle)
        internal
        pure
        returns (SettlementContext memory)
    {
        uint256 numDeposits = SettlementBundleLib.getNumDeposits(internalPartySettlementBundle) + 1;
        uint256 numWithdrawals = SettlementBundleLib.getNumWithdrawals(internalPartySettlementBundle) + 1;
        uint256 proofCapacity = SettlementBundleLib.getNumProofs(internalPartySettlementBundle);
        uint256 proofLinkingCapacity = SettlementBundleLib.getNumProofLinkingArguments(internalPartySettlementBundle);

        return SettlementContextLib.newContext(numDeposits, numWithdrawals, proofCapacity, proofLinkingCapacity);
    }

    /// @notice Allocate transfers to settle an external party's obligation into the settlement context
    /// @dev TODO: Implement fee computation and withdrawal transfers for relayer/protocol fees, and use recipient
    /// parameter for withdrawal
    /// @param recipient The recipient of the withdrawal
    /// @param externalObligation The external party's settlement obligation to settle
    /// @param settlementContext The settlement context to which we append post-validation updates.
    function allocateExternalMatchSettlementTransfers(
        address recipient,
        SettlementObligation memory externalObligation,
        SettlementContext memory settlementContext
    )
        internal
        view
    {
        address owner = msg.sender;

        // Deposit the input token into the darkpool
        SimpleTransfer memory deposit = externalObligation.buildERC20ApprovalDeposit(owner);
        settlementContext.pushDeposit(deposit);

        // Withdraw the output token from the darkpool
        uint256 totalFee = 0;
        SimpleTransfer memory withdrawal = externalObligation.buildWithdrawalTransfer(recipient, totalFee);
        settlementContext.pushWithdrawal(withdrawal);
    }

    // --- Settlement Bundle Validation --- //

    /// @notice Execute an external settlement bundle
    /// @param matchBundle The bounded match result authorization bundle to validate
    /// @param internalObligation The settlement obligation to validate
    /// @param internalPartySettlementBundle The settlement bundle for the internal party
    /// @param settlementContext The settlement context to which we append post-validation updates.
    /// @param contracts The contract references needed for settlement
    /// @param state The darkpool state containing all storage references
    function executeExternalSettlementBundle(
        BoundedMatchResultBundle calldata matchBundle,
        SettlementObligation memory internalObligation,
        SettlementBundle calldata internalPartySettlementBundle,
        SettlementContext memory settlementContext,
        DarkpoolContracts memory contracts,
        DarkpoolState storage state
    )
        internal
    {
        SettlementBundleType bundleType = internalPartySettlementBundle.bundleType;
        if (bundleType == SettlementBundleType.NATIVELY_SETTLED_PUBLIC_INTENT) {
            NativeSettledPublicIntentLib.executeBoundedMatch(
                matchBundle, internalObligation, internalPartySettlementBundle, settlementContext, state
            );
        } else if (bundleType == SettlementBundleType.NATIVELY_SETTLED_PRIVATE_INTENT) {
            NativeSettledPrivateIntentLib.executeBoundedMatch(
                matchBundle, internalObligation, internalPartySettlementBundle, settlementContext, contracts, state
            );
        } else if (bundleType == SettlementBundleType.RENEGADE_SETTLED_INTENT) {
            RenegadeSettledPrivateIntentLib.executeBoundedMatch(
                matchBundle, internalObligation, internalPartySettlementBundle, settlementContext, hasher, vkeys, state
            );
        } else {
            // TODO: Add support for other settlement bundle types
            revert IDarkpoolV2.InvalidSettlementBundleType();
        }
    }
}

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import {
    IntentAndBalanceValidityStatementFirstFill,
    IntentAndBalanceValidityStatement,
    NewOutputBalanceValidityStatement,
    OutputBalanceValidityStatement
} from "darkpoolv2-lib/public_inputs/ValidityProofs.sol";
import { PublicInputsLib } from "darkpoolv2-lib/public_inputs/PublicInputsLib.sol";
import { IntentAndBalancePrivateSettlementStatement } from "darkpoolv2-lib/public_inputs/Settlement.sol";
import { PartyId } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { SettlementBundle, SettlementBundleType } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { LinkingProof, ProofLinkingVK } from "renegade-lib/verifier/Types.sol";
import {
    RenegadeSettledIntentAuthBundleFirstFill,
    RenegadeSettledIntentAuthBundle
} from "darkpoolv2-types/settlement/IntentBundle.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";
import { PostMatchBalanceShare, PostMatchBalanceShareLib } from "darkpoolv2-types/Balance.sol";
import {
    IntentPublicShare,
    IntentPublicShareLib,
    IntentPreMatchShare,
    IntentPreMatchShareLib
} from "darkpoolv2-types/Intent.sol";
import { CommitmentLib } from "darkpoolv2-lib/Commitments.sol";
import { PartialCommitment } from "darkpoolv2-types/PartialCommitment.sol";
import { PrivateObligationBundle } from "darkpoolv2-types/settlement/ObligationBundle.sol";
import { SettlementContext } from "darkpoolv2-types/settlement/SettlementContext.sol";
import { DarkpoolContracts } from "darkpoolv2-contracts/DarkpoolV2.sol";
import { IVkeys } from "darkpoolv2-interfaces/IVkeys.sol";
import { IHasher } from "renegade-lib/interfaces/IHasher.sol";
import { DarkpoolState, DarkpoolStateLib } from "darkpoolv2-lib/DarkpoolState.sol";
import { PrivateIntentPrivateBalanceBundleLib } from
    "darkpoolv2-lib/settlement/bundles/PrivateIntentPrivateBalanceBundleLib.sol";
import {
    OutputBalanceBundle,
    OutputBalanceBundleType,
    OutputBalanceBundleLib,
    NewBalanceBundle,
    ExistingBalanceBundle
} from "darkpoolv2-types/settlement/OutputBalanceBundle.sol";

/// @notice The settlement bundle data for a `RENEGADE_SETTLED_INTENT` bundle on the first fill
/// @dev Note that this is the same as the `RENEGADE_SETTLED_INTENT` bundle, but without the settlement statement and
/// proof
/// These proofs are attached to the obligation bundle, as the proof unifies the two settlement bundles
struct RenegadeSettledPrivateFirstFillBundle {
    /// @dev The private intent authorization payload with signature attached
    RenegadeSettledIntentAuthBundleFirstFill auth;
    /// @dev The calldata bundle containing a proof of output balance validity
    OutputBalanceBundle outputBalanceBundle;
    /// @dev The proof linking argument between the validity proof and the settlement proof
    LinkingProof authSettlementLinkingProof;
}

/// @notice The settlement bundle data for a `RENEGADE_SETTLED_PRIVATE_FILL` bundle on subsequent fills
/// @dev Note that this is the same as the `RENEGADE_SETTLED_INTENT` bundle, but without the settlement statement and
/// proof
/// These proofs are attached to the obligation bundle, as the proof unifies the two settlement bundles
struct RenegadeSettledPrivateFillBundle {
    /// @dev The private intent authorization payload with signature attached
    RenegadeSettledIntentAuthBundle auth;
    /// @dev The calldata bundle containing a proof of output balance validity
    OutputBalanceBundle outputBalanceBundle;
    /// @dev The proof linking argument between the validity proof and the settlement proof
    LinkingProof authSettlementLinkingProof;
}

/// @title Renegade Settled Private Fill Library
/// @author Renegade Eng
/// @notice Library for validating renegade settled private fills
/// @dev A renegade settled private fill is a private intent with a private (darkpool) balance where
/// the settlement obligation itself is private.
library RenegadeSettledPrivateFillLib {
    using PublicInputsLib for IntentAndBalanceValidityStatementFirstFill;
    using PublicInputsLib for IntentAndBalanceValidityStatement;
    using PublicInputsLib for NewOutputBalanceValidityStatement;
    using PublicInputsLib for OutputBalanceValidityStatement;
    using DarkpoolStateLib for DarkpoolState;
    using IntentPreMatchShareLib for IntentPreMatchShare;
    using IntentPublicShareLib for IntentPublicShare;
    using PostMatchBalanceShareLib for PostMatchBalanceShare;
    using OutputBalanceBundleLib for OutputBalanceBundle;

    // ----------
    // | Decode |
    // ----------

    /// @notice Decode a renegade settled private fill settlement bundle for a first fill
    /// @param bundle The settlement bundle to decode
    /// @return bundleData The decoded bundle data
    function decodeRenegadeSettledPrivateFirstFillBundle(SettlementBundle calldata bundle)
        internal
        pure
        returns (RenegadeSettledPrivateFirstFillBundle memory bundleData)
    {
        bool validType = bundle.isFirstFill && bundle.bundleType == SettlementBundleType.RENEGADE_SETTLED_PRIVATE_FILL;
        require(validType, IDarkpoolV2.InvalidSettlementBundleType());
        bundleData = abi.decode(bundle.data, (RenegadeSettledPrivateFirstFillBundle));
    }

    /// @notice Decode a renegade settled private fill settlement bundle
    /// @param bundle The settlement bundle to decode
    /// @return bundleData The decoded bundle data
    function decodeRenegadeSettledPrivateBundle(SettlementBundle calldata bundle)
        internal
        pure
        returns (RenegadeSettledPrivateFillBundle memory bundleData)
    {
        bool validType = !bundle.isFirstFill && bundle.bundleType == SettlementBundleType.RENEGADE_SETTLED_PRIVATE_FILL;
        require(validType, IDarkpoolV2.InvalidSettlementBundleType());
        bundleData = abi.decode(bundle.data, (RenegadeSettledPrivateFillBundle));
    }

    // ----------------------------------
    // | Intent & Input Balance Updates |
    // ----------------------------------

    /// @notice Authorize and update the intent and input balance for a renegade settled private fill on the first fill
    /// @param partyId The party ID to authorize and update
    /// @param bundleData The bundle to authorize and update
    /// @param obligationBundle The obligation bundle to authorize and update
    /// @param settlementContext The settlement context to authorize and update
    /// @param contracts The contract references needed for settlement
    /// @param state The state to use for authorization and update
    function authorizeAndUpdateIntentAndBalance(
        PartyId partyId,
        RenegadeSettledPrivateFirstFillBundle memory bundleData,
        PrivateObligationBundle memory obligationBundle,
        SettlementContext memory settlementContext,
        DarkpoolContracts memory contracts,
        DarkpoolState storage state
    )
        internal
    {
        // Validate the Merkle root used to authorize the input balance
        state.assertRootInHistory(bundleData.auth.statement.merkleRoot);

        // Verify that the owner has signed the intent
        PrivateIntentPrivateBalanceBundleLib._verifyIntentSignature(bundleData.auth, state);

        // Push the validity proof to the settlement context
        ProofLinkingVK memory proofLinkingVkey = _getIntentAndBalanceProofLinkingVkey(partyId, contracts.vkeys);
        PrivateIntentPrivateBalanceBundleLib.pushValidityProof(
            bundleData.auth.statement.statementSerialize(),
            bundleData.auth.validityProof,
            obligationBundle.proof,
            contracts.vkeys.intentAndBalanceFirstFillValidityKeys(),
            proofLinkingVkey,
            bundleData.authSettlementLinkingProof,
            settlementContext
        );

        // Execute state updates for the input balance and intent
        _updateIntentAndBalance(partyId, bundleData, obligationBundle, state, contracts.hasher);
    }

    /// @notice Authorize and update the intent and input balance for a renegade settled private fill on a subsequent
    /// fill
    /// @param partyId The party ID to authorize and update
    /// @param bundleData The bundle to authorize and update
    /// @param obligationBundle The obligation bundle to authorize and update
    /// @param settlementContext The settlement context to authorize and update
    /// @param contracts The contract references needed for settlement
    /// @param state The state to use for authorization and update
    function authorizeAndUpdateIntentAndBalance(
        PartyId partyId,
        RenegadeSettledPrivateFillBundle memory bundleData,
        PrivateObligationBundle memory obligationBundle,
        SettlementContext memory settlementContext,
        DarkpoolContracts memory contracts,
        DarkpoolState storage state
    )
        internal
    {
        // Validate the Merkle roots used for the input balance and intent
        state.assertRootInHistory(bundleData.auth.statement.intentMerkleRoot);
        state.assertRootInHistory(bundleData.auth.statement.balanceMerkleRoot);

        // Push a validity proof to the settlement context
        ProofLinkingVK memory proofLinkingVkey = _getIntentAndBalanceProofLinkingVkey(partyId, contracts.vkeys);
        PrivateIntentPrivateBalanceBundleLib.pushValidityProof(
            bundleData.auth.statement.statementSerialize(),
            bundleData.auth.validityProof,
            obligationBundle.proof,
            contracts.vkeys.intentAndBalanceValidityKeys(),
            proofLinkingVkey,
            bundleData.authSettlementLinkingProof,
            settlementContext
        );

        // Rotate the intent and balance state elements to their updated versions
        _updateIntentAndBalance(partyId, bundleData, obligationBundle, state, contracts.hasher);
    }

    /// @notice Update the intent and input balance after authorization on the first fill
    /// @param partyId The party ID to update the intent and input balance for
    /// @param bundleData The bundle data to update
    /// @param obligation The obligation to update
    /// @param state The state to use for the update
    /// @param hasher The hasher to use for hashing
    function _updateIntentAndBalance(
        PartyId partyId,
        RenegadeSettledPrivateFirstFillBundle memory bundleData,
        PrivateObligationBundle memory obligation,
        DarkpoolState storage state,
        IHasher hasher
    )
        internal
    {
        // 1. Nullify the balance state
        BN254.ScalarField balanceNullifier = bundleData.auth.statement.oldBalanceNullifier;
        state.spendNullifier(balanceNullifier);

        // 2. Insert commitments to the updated balance and intent into the Merkle tree
        BN254.ScalarField newIntentAmountPublicShare;
        PostMatchBalanceShare memory newBalanceShares;
        if (partyId == PartyId.PARTY_0) {
            newIntentAmountPublicShare = obligation.statement.newAmountPublicShare0;
            newBalanceShares = obligation.statement.newInBalancePublicShares0;
        } else if (partyId == PartyId.PARTY_1) {
            newIntentAmountPublicShare = obligation.statement.newAmountPublicShare1;
            newBalanceShares = obligation.statement.newInBalancePublicShares1;
        }

        // Compute commitments to the new intent and the updated balance
        PartialCommitment memory balPartialCommitment = bundleData.auth.statement.balancePartialCommitment;
        BN254.ScalarField intentPrivateShareCommitment = bundleData.auth.statement.intentPrivateShareCommitment;
        IntentPreMatchShare memory intentPartialShare = bundleData.auth.statement.intentPublicShare;
        IntentPublicShare memory newIntentShare = intentPartialShare.toFullPublicShare(newIntentAmountPublicShare);
        BN254.ScalarField newBalanceCommitment =
            computeFullBalanceCommitment(newBalanceShares, balPartialCommitment, hasher);
        BN254.ScalarField newIntentCommitment =
            computeFullIntentCommitment(newIntentShare, intentPrivateShareCommitment, hasher);

        uint256 merkleDepth = bundleData.auth.merkleDepth;
        state.insertMerkleLeaf(merkleDepth, newBalanceCommitment, hasher);
        state.insertMerkleLeaf(merkleDepth, newIntentCommitment, hasher);
    }

    /// @notice Update the intent and input balance after authorization on a subsequent fill
    /// @param partyId The party ID to update the intent and input balance for
    /// @param bundleData The bundle data to update
    /// @param obligation The obligation to update
    /// @param state The state to use for the update
    /// @param hasher The hasher to use for the update
    function _updateIntentAndBalance(
        PartyId partyId,
        RenegadeSettledPrivateFillBundle memory bundleData,
        PrivateObligationBundle memory obligation,
        DarkpoolState storage state,
        IHasher hasher
    )
        internal
    {
        // 1. Nullify the balance and intent states
        BN254.ScalarField balanceNullifier = bundleData.auth.statement.oldBalanceNullifier;
        BN254.ScalarField intentNullifier = bundleData.auth.statement.oldIntentNullifier;
        state.spendNullifier(balanceNullifier);
        state.spendNullifier(intentNullifier);

        // 2. Insert commitments to the updated balance and intent into the Merkle tree
        BN254.ScalarField newIntentAmountPublicShare;
        PostMatchBalanceShare memory newBalanceShares;
        if (partyId == PartyId.PARTY_0) {
            newIntentAmountPublicShare = obligation.statement.newAmountPublicShare0;
            newBalanceShares = obligation.statement.newInBalancePublicShares0;
        } else if (partyId == PartyId.PARTY_1) {
            newIntentAmountPublicShare = obligation.statement.newAmountPublicShare1;
            newBalanceShares = obligation.statement.newInBalancePublicShares1;
        }

        // Compute the commitments to the updated balance and intent
        PartialCommitment memory balPartialCommitment = bundleData.auth.statement.balancePartialCommitment;
        PartialCommitment memory intentPartialCommitment = bundleData.auth.statement.newIntentPartialCommitment;
        BN254.ScalarField newBalanceCommitment =
            computeFullBalanceCommitment(newBalanceShares, balPartialCommitment, hasher);
        BN254.ScalarField newIntentCommitment =
            computeFullIntentCommitment(newIntentAmountPublicShare, intentPartialCommitment, hasher);

        // Insert at the configured depth
        uint256 merkleDepth = bundleData.auth.merkleDepth;
        state.insertMerkleLeaf(merkleDepth, newBalanceCommitment, hasher);
        state.insertMerkleLeaf(merkleDepth, newIntentCommitment, hasher);
    }

    // --------------------------------
    // | Output Balance Authorization |
    // --------------------------------

    /// @notice Authorize and update the output balance for a Renegade settled private fill bundle
    /// @param partyId The party ID to authorize and update
    /// @param outputBalanceBundle The output balance bundle to authorize and update
    /// @param obligationBundle The obligation bundle to authorize and update
    /// @param settlementContext The settlement context to authorize and update
    /// @param contracts The contract references needed for settlement
    /// @param state The state to use for authorization and update
    function authorizeAndUpdateOutputBalance(
        PartyId partyId,
        OutputBalanceBundle memory outputBalanceBundle,
        PrivateObligationBundle memory obligationBundle,
        SettlementContext memory settlementContext,
        DarkpoolContracts memory contracts,
        DarkpoolState storage state
    )
        internal
    {
        if (outputBalanceBundle.bundleType == OutputBalanceBundleType.NEW_BALANCE) {
            _authorizeAndUpdateNewOutputBalance(
                partyId, outputBalanceBundle, obligationBundle, settlementContext, contracts, state
            );
        } else if (outputBalanceBundle.bundleType == OutputBalanceBundleType.EXISTING_BALANCE) {
            _authorizeAndUpdateExistingOutputBalance(
                partyId, outputBalanceBundle, obligationBundle, settlementContext, contracts, state
            );
        } else {
            revert IDarkpoolV2.InvalidOutputBalanceBundleType();
        }
    }

    /// @notice Authorize and update a new output balance for a Renegade settled private fill bundle
    /// @param partyId The party ID to authorize and update
    /// @param outputBalanceBundle The output balance bundle to authorize and update
    /// @param obligationBundle The obligation bundle to authorize and update
    /// @param settlementContext The settlement context to authorize and update
    /// @param contracts The contract references needed for settlement
    /// @param state The state to use for authorization and update
    function _authorizeAndUpdateNewOutputBalance(
        PartyId partyId,
        OutputBalanceBundle memory outputBalanceBundle,
        PrivateObligationBundle memory obligationBundle,
        SettlementContext memory settlementContext,
        DarkpoolContracts memory contracts,
        DarkpoolState storage state
    )
        internal
    {
        NewBalanceBundle memory newBalanceBundle = outputBalanceBundle.decodeNewBalanceBundle();
        ProofLinkingVK memory proofLinkingVkey = _getOutputBalanceProofLinkingVkey(partyId, contracts.vkeys);
        PrivateIntentPrivateBalanceBundleLib.pushValidityProof(
            newBalanceBundle.statement.statementSerialize(),
            outputBalanceBundle.proof,
            obligationBundle.proof,
            contracts.vkeys.newOutputBalanceValidityKeys(),
            proofLinkingVkey,
            outputBalanceBundle.settlementLinkingProof,
            settlementContext
        );

        // Update the output balance in the state
        _updateNewOutputBalance(
            partyId, newBalanceBundle, outputBalanceBundle, obligationBundle.statement, contracts.hasher, state
        );
    }

    /// @notice Authorize and update an existing output balance for a Renegade settled private fill bundle
    /// @param partyId The party ID to authorize and update
    /// @param outputBalanceBundle The output balance bundle to authorize and update
    /// @param obligationBundle The obligation bundle to authorize and update
    /// @param settlementContext The settlement context to authorize and update
    /// @param contracts The contract references needed for settlement
    /// @param state The state to use for authorization and update
    function _authorizeAndUpdateExistingOutputBalance(
        PartyId partyId,
        OutputBalanceBundle memory outputBalanceBundle,
        PrivateObligationBundle memory obligationBundle,
        SettlementContext memory settlementContext,
        DarkpoolContracts memory contracts,
        DarkpoolState storage state
    )
        internal
    {
        ExistingBalanceBundle memory existingBalanceBundle = outputBalanceBundle.decodeExistingBalanceBundle();

        // Validate the Merkle root used to open the balance
        state.assertRootInHistory(existingBalanceBundle.statement.merkleRoot);

        // Push the validity proof to the settlement context
        ProofLinkingVK memory proofLinkingVkey = _getOutputBalanceProofLinkingVkey(partyId, contracts.vkeys);
        PrivateIntentPrivateBalanceBundleLib.pushValidityProof(
            existingBalanceBundle.statement.statementSerialize(),
            outputBalanceBundle.proof,
            obligationBundle.proof,
            contracts.vkeys.outputBalanceValidityKeys(),
            proofLinkingVkey,
            outputBalanceBundle.settlementLinkingProof,
            settlementContext
        );

        // Update the output balance in the state
        _updateExistingOutputBalance(
            partyId, existingBalanceBundle, outputBalanceBundle, obligationBundle.statement, contracts.hasher, state
        );
    }

    /// @notice Update a new output balance bundle in the Renegade state
    /// @param partyId The party ID to update the output balance for
    /// @param newBalanceBundle The new balance bundle to update with
    /// @param outputBalanceBundle The output balance bundle to update with
    /// @param settlementStatement The settlement statement to use for the update
    /// @param hasher The hasher to use for hashing
    /// @param state The state to use for the update
    function _updateNewOutputBalance(
        PartyId partyId,
        NewBalanceBundle memory newBalanceBundle,
        OutputBalanceBundle memory outputBalanceBundle,
        IntentAndBalancePrivateSettlementStatement memory settlementStatement,
        IHasher hasher,
        DarkpoolState storage state
    )
        internal
    {
        // Compute the full commitment to the output balance after settlement is applied
        // Unlike in other settlement paths; the circuit settles the path into the balance and emits the updated public
        // shares, so we only need to hash these shares into the partial commitment.
        PostMatchBalanceShare memory newOutBalancePublicShares;
        if (partyId == PartyId.PARTY_0) {
            newOutBalancePublicShares = settlementStatement.newOutBalancePublicShares0;
        } else if (partyId == PartyId.PARTY_1) {
            newOutBalancePublicShares = settlementStatement.newOutBalancePublicShares1;
        }

        PartialCommitment memory partialCommitment = newBalanceBundle.statement.newBalancePartialCommitment;
        BN254.ScalarField balCommitment =
            computeFullBalanceCommitment(newOutBalancePublicShares, partialCommitment, hasher);
        state.insertMerkleLeaf(outputBalanceBundle.merkleDepth, balCommitment, hasher);

        // Emit a recovery ID for the output balance
        BN254.ScalarField recoveryId = newBalanceBundle.statement.recoveryId;
        emit IDarkpoolV2.RecoveryIdRegistered(recoveryId);
    }

    /// @notice Update an existing output balance bundle in the Renegade state
    /// @param partyId The party ID to update the output balance for
    /// @param existingBalanceBundle The existing balance bundle to update with
    /// @param outputBalanceBundle The output balance bundle to update with
    /// @param settlementStatement The settlement statement to use for the update
    /// @param hasher The hasher to use for hashing
    /// @param state The state to use for the update
    function _updateExistingOutputBalance(
        PartyId partyId,
        ExistingBalanceBundle memory existingBalanceBundle,
        OutputBalanceBundle memory outputBalanceBundle,
        IntentAndBalancePrivateSettlementStatement memory settlementStatement,
        IHasher hasher,
        DarkpoolState storage state
    )
        internal
    {
        // Nullify the previous version of the balance
        state.spendNullifier(existingBalanceBundle.statement.oldBalanceNullifier);

        // Compute the full commitment to the output balance after settlement is applied
        // Unlike in other settlement paths; the circuit settles the path into the balance and emits the updated public
        // shares, so we only need to hash these shares into the partial commitment.
        PostMatchBalanceShare memory newOutBalancePublicShares;
        if (partyId == PartyId.PARTY_0) {
            newOutBalancePublicShares = settlementStatement.newOutBalancePublicShares0;
        } else if (partyId == PartyId.PARTY_1) {
            newOutBalancePublicShares = settlementStatement.newOutBalancePublicShares1;
        }

        PartialCommitment memory partialCommitment = existingBalanceBundle.statement.newPartialCommitment;
        BN254.ScalarField balCommitment =
            computeFullBalanceCommitment(newOutBalancePublicShares, partialCommitment, hasher);
        state.insertMerkleLeaf(outputBalanceBundle.merkleDepth, balCommitment, hasher);

        // Emit a recovery ID for the output balance
        BN254.ScalarField recoveryId = existingBalanceBundle.statement.recoveryId;
        emit IDarkpoolV2.RecoveryIdRegistered(recoveryId);
    }

    // --------------------------
    // | Commitment Computation |
    // --------------------------

    /// @notice Compute the full commitment to a new intent given the intent's public shares and partial commitment
    /// @param newIntentShare The updated intent public share
    /// @param intentPrivateShareCommitment The private commitment to the intent
    /// @param hasher The hasher to use for hashing
    /// @return newIntentCommitment The full commitment to the updated intent
    function computeFullIntentCommitment(
        IntentPublicShare memory newIntentShare,
        BN254.ScalarField intentPrivateShareCommitment,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField newIntentCommitment)
    {
        uint256[] memory publicShares = newIntentShare.scalarSerialize();
        newIntentCommitment =
            CommitmentLib.computeCommitmentWithPublicShares(intentPrivateShareCommitment, publicShares, hasher);
    }

    /// @notice Compute the full commitment to the updated intent for a renegade settled private fill bundle
    /// on its subsequent fill
    /// @dev As with the first fill implementation for private fill bundles; the shares are pre-updated in the circuit,
    /// so we only need to resume the partial commitment.
    /// @param newIntentAmountPublicShare The updated intent amount public share
    /// @param partialCommitment The partial commitment to resume from
    /// @param hasher The hasher to use for hashing
    /// @return newIntentCommitment The full commitment to the updated intent
    function computeFullIntentCommitment(
        BN254.ScalarField newIntentAmountPublicShare,
        PartialCommitment memory partialCommitment,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField newIntentCommitment)
    {
        uint256[] memory remainingShares = new uint256[](1);
        remainingShares[0] = BN254.ScalarField.unwrap(newIntentAmountPublicShare);
        newIntentCommitment = CommitmentLib.computeResumableCommitment(remainingShares, partialCommitment, hasher);
    }

    /// @notice Compute the full commitment to the updated balance for a renegade settled private fill bundle
    /// on its subsequent fill
    /// @dev As with the first fill implementation for private fill bundles; the shares are pre-updated in the circuit,
    /// so we only need to resume the partial commitment.
    /// @param newBalancePublicShares The updated balance public shares
    /// @param partialCommitment The partial commitment to resume from
    /// @param hasher The hasher to use for hashing
    /// @return newBalanceCommitment The full commitment to the updated balance
    function computeFullBalanceCommitment(
        PostMatchBalanceShare memory newBalancePublicShares,
        PartialCommitment memory partialCommitment,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField newBalanceCommitment)
    {
        uint256[] memory remainingShares = newBalancePublicShares.scalarSerialize();
        newBalanceCommitment = CommitmentLib.computeResumableCommitment(remainingShares, partialCommitment, hasher);
    }

    // --- Helpers --- //

    /// @notice Get the proof linking vkey for a Renegade settled private fill bundle based on the party ID
    /// @param partyId The party ID to get the proof linking vkey for
    /// @param vkeys The verification keys to use for the proof linking
    /// @return proofLinkingVkey The proof linking vkey
    function _getIntentAndBalanceProofLinkingVkey(
        PartyId partyId,
        IVkeys vkeys
    )
        internal
        view
        returns (ProofLinkingVK memory proofLinkingVkey)
    {
        if (partyId == PartyId.PARTY_0) {
            proofLinkingVkey = vkeys.intentAndBalanceSettlement0LinkingKey();
        } else {
            proofLinkingVkey = vkeys.intentAndBalanceSettlement1LinkingKey();
        }
    }

    /// @notice Get the proof linking vkey for a Renegade settled private fill bundle based on the party ID
    /// @param partyId The party ID to get the proof linking vkey for
    /// @param vkeys The verification keys to use for the proof linking
    /// @return proofLinkingVkey The proof linking vkey
    function _getOutputBalanceProofLinkingVkey(
        PartyId partyId,
        IVkeys vkeys
    )
        internal
        view
        returns (ProofLinkingVK memory proofLinkingVkey)
    {
        if (partyId == PartyId.PARTY_0) {
            proofLinkingVkey = vkeys.outputBalanceSettlement0LinkingKey();
        } else {
            proofLinkingVkey = vkeys.outputBalanceSettlement1LinkingKey();
        }
    }
}

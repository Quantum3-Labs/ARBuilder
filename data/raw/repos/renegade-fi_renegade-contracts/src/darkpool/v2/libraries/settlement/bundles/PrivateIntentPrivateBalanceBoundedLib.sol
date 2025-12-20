// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { IHasher } from "renegade-lib/interfaces/IHasher.sol";
import {
    PlonkProof,
    LinkingProof,
    VerificationKey,
    ProofLinkingInstance,
    ProofLinkingVK
} from "renegade-lib/verifier/Types.sol";

import { CommitmentLib } from "darkpoolv2-lib/Commitments.sol";
import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import { DarkpoolState, DarkpoolStateLib } from "darkpoolv2-lib/DarkpoolState.sol";
import { FeeRate, FeeRateLib, FeeTake, FeeTakeLib } from "darkpoolv2-types/Fee.sol";
import { BoundedMatchResult, BoundedMatchResultLib } from "darkpoolv2-types/BoundedMatchResult.sol";
import { IDarkpool } from "darkpoolv1-interfaces/IDarkpool.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";
import {
    RenegadeSettledIntentAuthBundleFirstFill,
    RenegadeSettledIntentAuthBundle,
    SignatureWithNonce,
    SignatureWithNonceLib,
    PrivateIntentPrivateBalanceAuthBundleLib
} from "darkpoolv2-types/settlement/IntentBundle.sol";
import {
    OutputBalanceBundle,
    OutputBalanceBundleLib,
    NewBalanceBundle,
    ExistingBalanceBundle,
    OutputBalanceBundleType
} from "darkpoolv2-types/settlement/OutputBalanceBundle.sol";
import { IntentAndBalanceBoundedSettlementStatement } from "darkpoolv2-lib/public_inputs/Settlement.sol";
import { SettlementObligation, SettlementObligationLib } from "darkpoolv2-types/Obligation.sol";
import { SimpleTransfer } from "darkpoolv2-types/transfers/SimpleTransfer.sol";
import { SettlementBundle, SettlementBundleType } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import {
    IntentAndBalanceValidityStatementFirstFill,
    IntentAndBalanceValidityStatement,
    NewOutputBalanceValidityStatement,
    OutputBalanceValidityStatement
} from "darkpoolv2-lib/public_inputs/ValidityProofs.sol";
import {
    IntentPublicShare,
    IntentPublicShareLib,
    IntentPreMatchShare,
    IntentPreMatchShareLib
} from "darkpoolv2-types/Intent.sol";
import { PostMatchBalanceShare, PostMatchBalanceShareLib } from "darkpoolv2-types/Balance.sol";
import { SettlementContext, SettlementContextLib } from "darkpoolv2-types/settlement/SettlementContext.sol";
import { IVkeys } from "darkpoolv2-interfaces/IVkeys.sol";
import { PublicInputsLib } from "darkpoolv2-lib/public_inputs/PublicInputsLib.sol";
import {
    PrivateIntentPrivateBalanceBundleLib
} from "darkpoolv2-lib/settlement/bundles/PrivateIntentPrivateBalanceBundleLib.sol";

// ----------------
// | Bundle Types |
// ----------------

/// @notice The settlement bundle data for a `RENEGADE_SETTLED_PRIVATE_INTENT` bundle on the first fill
/// with bounded settlement (min/max amount constraints)
struct RenegadeSettledIntentBoundedFirstFillBundle {
    /// @dev The private intent authorization payload with signature attached
    RenegadeSettledIntentAuthBundleFirstFill auth;
    /// @dev The calldata bundle containing a proof of output balance validity
    OutputBalanceBundle outputBalanceBundle;
    /// @dev The statement of intent and balance public settlement
    IntentAndBalanceBoundedSettlementStatement settlementStatement;
    /// @dev The proof of intent and balance public settlement
    PlonkProof settlementProof;
    /// @dev The proof linking the authorization and settlement proofs
    LinkingProof authSettlementLinkingProof;
}

/// @notice The settlement bundle data for a `RENEGADE_SETTLED_INTENT` bundle with bounded settlement
struct RenegadeSettledIntentBoundedBundle {
    /// @dev The private intent authorization payload with signature attached
    RenegadeSettledIntentAuthBundle auth;
    /// @dev The calldata bundle containing a proof of output balance validity
    OutputBalanceBundle outputBalanceBundle;
    /// @dev The statement of intent and balance public settlement
    IntentAndBalanceBoundedSettlementStatement settlementStatement;
    /// @dev The proof of intent and balance public settlement
    PlonkProof settlementProof;
    /// @dev The proof linking the authorization and settlement proofs
    LinkingProof authSettlementLinkingProof;
}

// -----------
// | Library |
// -----------

/// @title Private Intent Private Balance Bounded Settlement Library
/// @author Renegade Eng
/// @notice Library for decoding, computing commitments, and extracting values from private intent, private balance
/// bundles using bounded settlement (with min/max amount constraints).
library PrivateIntentPrivateBalanceBoundedLib {
    using BN254 for BN254.ScalarField;
    using IntentPublicShareLib for IntentPublicShare;
    using IntentPreMatchShareLib for IntentPreMatchShare;
    using PostMatchBalanceShareLib for PostMatchBalanceShare;
    using SignatureWithNonceLib for SignatureWithNonce;
    using SettlementContextLib for SettlementContext;
    using DarkpoolStateLib for DarkpoolState;
    using PublicInputsLib for IntentAndBalanceValidityStatementFirstFill;
    using PublicInputsLib for IntentAndBalanceValidityStatement;
    using PublicInputsLib for NewOutputBalanceValidityStatement;
    using PublicInputsLib for OutputBalanceValidityStatement;
    using PublicInputsLib for IntentAndBalanceBoundedSettlementStatement;
    using SettlementObligationLib for SettlementObligation;
    using BoundedMatchResultLib for BoundedMatchResult;
    using FeeRateLib for FeeRate;
    using FeeTakeLib for FeeTake;
    using OutputBalanceBundleLib for OutputBalanceBundle;

    // ----------
    // | Decode |
    // ----------

    /// @notice Decode a Renegade settled private intent settlement bundle
    /// @param bundle The settlement bundle to decode
    /// @return bundleData The decoded bundle data
    function decodeRenegadeSettledIntentBundleDataFirstFill(SettlementBundle calldata bundle)
        internal
        pure
        returns (RenegadeSettledIntentBoundedFirstFillBundle memory bundleData)
    {
        bool validType = bundle.isFirstFill && bundle.bundleType == SettlementBundleType.RENEGADE_SETTLED_INTENT;
        require(validType, IDarkpoolV2.InvalidSettlementBundleType());
        bundleData = abi.decode(bundle.data, (RenegadeSettledIntentBoundedFirstFillBundle));
    }

    /// @notice Decode a Renegade settled private intent settlement bundle
    /// @param bundle The settlement bundle to decode
    /// @return bundleData The decoded bundle data
    function decodeRenegadeSettledIntentBundleData(SettlementBundle calldata bundle)
        internal
        pure
        returns (RenegadeSettledIntentBoundedBundle memory bundleData)
    {
        bool validType = !bundle.isFirstFill && bundle.bundleType == SettlementBundleType.RENEGADE_SETTLED_INTENT;
        require(validType, IDarkpoolV2.InvalidSettlementBundleType());
        bundleData = abi.decode(bundle.data, (RenegadeSettledIntentBoundedBundle));
    }

    // ----------------------------------
    // | Intent & Input Balance Updates |
    // ----------------------------------

    /// @notice Authorize and update the intent and capitalizing balance for a Renegade settled private intent bundle on
    /// its first fill
    /// @param bundleData The bundle to check validity for
    /// @param internalPartyAmountIn The internal party's input amount (determined at runtime)
    /// @param settlementContext The settlement context to check validity for
    /// @param vkeys The contract storing the verification keys
    /// @param hasher The hasher contract
    /// @param state The state to use for verification
    function authorizeAndUpdateIntentAndBalance(
        RenegadeSettledIntentBoundedFirstFillBundle memory bundleData,
        uint256 internalPartyAmountIn,
        SettlementContext memory settlementContext,
        IVkeys vkeys,
        IHasher hasher,
        DarkpoolState storage state
    )
        internal
    {
        RenegadeSettledIntentAuthBundleFirstFill memory authBundle = bundleData.auth;

        // Validate the Merkle root used to authorize the input balance
        state.assertRootInHistory(authBundle.statement.merkleRoot);

        // Verify the intent signature
        PrivateIntentPrivateBalanceBundleLib._verifyIntentSignature(authBundle, state);

        // Push the validity proof to the settlement context
        pushValidityProof(
            authBundle.statement.statementSerialize(),
            authBundle.validityProof,
            bundleData.settlementProof,
            vkeys.intentAndBalanceFirstFillValidityKeys(),
            vkeys.intentAndBalanceSettlement0LinkingKey(),
            bundleData.authSettlementLinkingProof,
            settlementContext
        );

        // Rotate the intent and balance state elements to their updated versions
        _updateIntentAndBalance(bundleData, internalPartyAmountIn, state, hasher);
    }

    /// @notice Authorize and update the intent and capitalizing balance for a Renegade settled private intent bundle on
    /// subsequent fill
    /// @dev Note that we don't need to verify the owner signature here. The presence of the intent in the Merkle tree
    /// implies that the owner's signature has already been verified (in a previous fill). So in this case, we need only
    /// verify the proof attached to the bundle.
    /// @param bundleData The bundle to authorize
    /// @param internalPartyAmountIn The internal party's input amount (determined at runtime)
    /// @param settlementContext The settlement context to authorize the intent for
    /// @param vkeys The contract storing the verification keys
    /// @param hasher The hasher contract
    /// @param state The state to use for authorization
    function authorizeAndUpdateIntentAndBalance(
        RenegadeSettledIntentBoundedBundle memory bundleData,
        uint256 internalPartyAmountIn,
        SettlementContext memory settlementContext,
        IVkeys vkeys,
        IHasher hasher,
        DarkpoolState storage state
    )
        internal
    {
        // Validate the Merkle roots used for the input balance and intent
        state.assertRootInHistory(bundleData.auth.statement.intentMerkleRoot);
        state.assertRootInHistory(bundleData.auth.statement.balanceMerkleRoot);

        // Push a validity proof to the settlement context
        pushValidityProof(
            bundleData.auth.statement.statementSerialize(),
            bundleData.auth.validityProof,
            bundleData.settlementProof,
            vkeys.intentAndBalanceValidityKeys(),
            vkeys.intentAndBalanceSettlement0LinkingKey(),
            bundleData.authSettlementLinkingProof,
            settlementContext
        );

        // Rotate the intent and balance state elements to their updated versions
        _updateIntentAndBalance(bundleData, internalPartyAmountIn, state, hasher);
    }

    /// @notice Update the intent and input balance on the first fill after authorization
    /// @param bundle The bundle to update the intent for
    /// @param internalPartyAmountIn The internal party's input amount (determined at runtime)
    /// @param state The state to use for the update
    /// @param hasher The hasher contract
    function _updateIntentAndBalance(
        RenegadeSettledIntentBoundedFirstFillBundle memory bundle,
        uint256 internalPartyAmountIn,
        DarkpoolState storage state,
        IHasher hasher
    )
        internal
    {
        // 1. Nullify the balance state
        BN254.ScalarField nullifier = bundle.auth.statement.oldBalanceNullifier;
        state.spendNullifier(nullifier);

        // 2. Insert commitments to the updated intent and balance into the Merkle tree
        uint256 merkleDepth = bundle.auth.merkleDepth;
        BN254.ScalarField newIntentCommitment = computeFullIntentCommitment(bundle, internalPartyAmountIn, hasher);
        BN254.ScalarField newBalanceCommitment = computeFullBalanceCommitment(bundle, internalPartyAmountIn, hasher);
        state.insertMerkleLeaf(merkleDepth, newIntentCommitment, hasher);
        state.insertMerkleLeaf(merkleDepth, newBalanceCommitment, hasher);

        // 3. Emit recovery IDs for the intent and balance
        IntentAndBalanceValidityStatementFirstFill memory authStatement = bundle.auth.statement;
        emit IDarkpoolV2.RecoveryIdRegistered(authStatement.intentRecoveryId);
        emit IDarkpoolV2.RecoveryIdRegistered(authStatement.balanceRecoveryId);
    }

    /// @notice Update the intent and input balance on a subsequent fill
    /// @param bundle The bundle to update the intent for
    /// @param internalPartyAmountIn The internal party's input amount (determined at runtime)
    /// @param state The state to use for the update
    /// @param hasher The hasher contract
    function _updateIntentAndBalance(
        RenegadeSettledIntentBoundedBundle memory bundle,
        uint256 internalPartyAmountIn,
        DarkpoolState storage state,
        IHasher hasher
    )
        internal
    {
        // 1. Nullify both the balance and intent states
        BN254.ScalarField balanceNullifier = bundle.auth.statement.oldBalanceNullifier;
        BN254.ScalarField intentNullifier = bundle.auth.statement.oldIntentNullifier;
        state.spendNullifier(balanceNullifier);
        state.spendNullifier(intentNullifier);

        // 2. Insert commitments to the updated intent and balance into the Merkle tree
        uint256 merkleDepth = bundle.auth.merkleDepth;
        BN254.ScalarField newIntentCommitment = computeFullIntentCommitment(bundle, internalPartyAmountIn, hasher);
        BN254.ScalarField newBalanceCommitment = computeFullBalanceCommitment(bundle, internalPartyAmountIn, hasher);
        state.insertMerkleLeaf(merkleDepth, newIntentCommitment, hasher);
        state.insertMerkleLeaf(merkleDepth, newBalanceCommitment, hasher);

        // 3. Emit recovery IDs for the intent and balance
        IntentAndBalanceValidityStatement memory authStatement = bundle.auth.statement;
        emit IDarkpoolV2.RecoveryIdRegistered(authStatement.intentRecoveryId);
        emit IDarkpoolV2.RecoveryIdRegistered(authStatement.balanceRecoveryId);
    }

    // --------------------------------
    // | Output Balance Authorization |
    // --------------------------------

    /// @notice Authorize and update the output balance for a Renegade settled private intent bundle
    /// @dev The output balance receives the obligation's output amount
    /// @dev A settlement *may* create a new output balance, or it may use an existing balance. These two cases
    /// correspond to the helpers below
    /// @param netReceiveAmount The net receive amount of the trader after fees have been applied
    /// @param settlementStatement The settlement statement to use for the update
    /// @param outputBalanceBundle The output balance's authorization bundle
    /// @param settlementProof The settlement proof; included here to proof-link the output balance authorization into
    /// the settlement proof
    /// @param settlementContext The settlement context to authorize the output balance for
    /// @param vkeys The verification keys to use for authorization
    /// @param hasher The hasher contract
    /// @param state The state to use for authorization
    function authorizeAndUpdateOutputBalance(
        uint256 netReceiveAmount,
        IntentAndBalanceBoundedSettlementStatement memory settlementStatement,
        OutputBalanceBundle memory outputBalanceBundle,
        PlonkProof memory settlementProof,
        SettlementContext memory settlementContext,
        IVkeys vkeys,
        IHasher hasher,
        DarkpoolState storage state
    )
        internal
    {
        if (outputBalanceBundle.bundleType == OutputBalanceBundleType.NEW_BALANCE) {
            _authorizeAndUpdateNewOutputBalance(
                netReceiveAmount,
                outputBalanceBundle,
                settlementStatement,
                settlementProof,
                settlementContext,
                vkeys,
                hasher,
                state
            );
        } else if (outputBalanceBundle.bundleType == OutputBalanceBundleType.EXISTING_BALANCE) {
            _authorizeAndUpdateExistingOutputBalance(
                netReceiveAmount,
                outputBalanceBundle,
                settlementStatement,
                settlementProof,
                settlementContext,
                vkeys,
                hasher,
                state
            );
        } else {
            revert IDarkpoolV2.InvalidOutputBalanceBundleType();
        }
    }

    /// @notice Authorize a new output balance for a Renegade settled private intent bundle
    /// @dev A new output balance is created as part of the settlement
    /// @param netReceiveAmount The net receive amount of the trader after fees have been applied
    /// @param bundle The output balance's authorization bundle
    /// @param settlementStatement The settlement statement to use for the update
    /// @param settlementProof The settlement proof; included here to proof-link the output balance authorization into
    /// the settlement proof
    /// @param settlementContext The settlement context to authorize the output balance for
    /// @param vkeys The verification keys to use for authorization
    /// @param hasher The hasher contract
    /// @param state The state to use for the update
    function _authorizeAndUpdateNewOutputBalance(
        uint256 netReceiveAmount,
        OutputBalanceBundle memory bundle,
        IntentAndBalanceBoundedSettlementStatement memory settlementStatement,
        PlonkProof memory settlementProof,
        SettlementContext memory settlementContext,
        IVkeys vkeys,
        IHasher hasher,
        DarkpoolState storage state
    )
        internal
    {
        // Verify the output balance validity proof
        NewBalanceBundle memory newBalanceBundle = bundle.decodeNewBalanceBundle();
        pushValidityProof(
            newBalanceBundle.statement.statementSerialize(),
            bundle.proof,
            settlementProof,
            vkeys.newOutputBalanceValidityKeys(),
            // We use the first party's link group layout for this linking argument regardless of the party ID
            // because in this settlement ring, the settlement proof is per-party, and only has link groups for one
            // output balance.
            vkeys.outputBalanceSettlement0LinkingKey(),
            bundle.settlementLinkingProof,
            settlementContext
        );

        // Update the output balance's contract state
        _updateNewOutputBalance(netReceiveAmount, newBalanceBundle, bundle, settlementStatement, hasher, state);
    }

    /// @notice Authorize an existing output balance for a Renegade settled private intent bundle
    /// @dev An existing output balance is used as part of the settlement
    /// @param netReceiveAmount The net receive amount of the trader after fees have been applied
    /// @param bundle The output balance's authorization bundle
    /// @param settlementStatement The settlement statement to use for the update
    /// @param settlementProof The settlement proof; included here to proof-link the output balance authorization into
    /// the settlement proof
    /// @param settlementContext The settlement context to authorize the output balance for
    /// @param vkeys The verification keys to use for authorization
    /// @param hasher The hasher contract
    /// @param state The state to use for authorization
    function _authorizeAndUpdateExistingOutputBalance(
        uint256 netReceiveAmount,
        OutputBalanceBundle memory bundle,
        IntentAndBalanceBoundedSettlementStatement memory settlementStatement,
        PlonkProof memory settlementProof,
        SettlementContext memory settlementContext,
        IVkeys vkeys,
        IHasher hasher,
        DarkpoolState storage state
    )
        internal
    {
        ExistingBalanceBundle memory existingBalanceBundle = bundle.decodeExistingBalanceBundle();

        // Validate the Merkle root used for the output balance
        state.assertRootInHistory(existingBalanceBundle.statement.merkleRoot);

        // Push the validity proof to the settlement context alongside the proof linking argument
        pushValidityProof(
            existingBalanceBundle.statement.statementSerialize(),
            bundle.proof,
            settlementProof,
            vkeys.outputBalanceValidityKeys(),
            // We use the first party's link group layout for this linking argument regardless of the party ID
            // because in this settlement ring, the settlement proof is per-party, and only has link groups for one
            // output balance.
            vkeys.outputBalanceSettlement0LinkingKey(),
            bundle.settlementLinkingProof,
            settlementContext
        );

        // Update the output balance's contract state
        _updateExistingOutputBalance(
            netReceiveAmount, existingBalanceBundle, bundle, settlementStatement, hasher, state
        );
    }

    /// @notice Update a new output balance's contract state
    /// @param netReceiveAmount The net receive amount of the trader after fees have been applied
    /// @param bundle The new balance bundle
    /// @param outputBalanceBundle The output balance's authorization bundle
    /// @param settlementStatement The settlement statement to use for the update
    /// @param hasher The hasher contract
    /// @param state The state to use for the update
    function _updateNewOutputBalance(
        uint256 netReceiveAmount,
        NewBalanceBundle memory bundle,
        OutputBalanceBundle memory outputBalanceBundle,
        IntentAndBalanceBoundedSettlementStatement memory settlementStatement,
        IHasher hasher,
        DarkpoolState storage state
    )
        internal
    {
        // Compute the commitment to the output balance after the settlement is applied
        // Fees are already paid directly as ERC20 transfers for this settlement bundle type, so we only need to update
        // the balance's `amount` share.
        BN254.ScalarField newBalanceCommitment =
            computeFullNewOutputBalanceCommitment(netReceiveAmount, bundle, settlementStatement, hasher);
        state.insertMerkleLeaf(outputBalanceBundle.merkleDepth, newBalanceCommitment, hasher);

        // Emit a recovery ID for the output balance
        BN254.ScalarField recoveryId = bundle.statement.recoveryId;
        emit IDarkpoolV2.RecoveryIdRegistered(recoveryId);
    }

    /// @notice Update an existing output balance's contract state
    /// @param netReceiveAmount The net receive amount of the trader after fees have been applied
    /// @param bundle The existing balance bundle
    /// @param outputBalanceBundle The output balance's authorization bundle
    /// @param settlementStatement The settlement statement to use for the update
    /// @param hasher The hasher contract
    /// @param state The state to use for the update
    function _updateExistingOutputBalance(
        uint256 netReceiveAmount,
        ExistingBalanceBundle memory bundle,
        OutputBalanceBundle memory outputBalanceBundle,
        IntentAndBalanceBoundedSettlementStatement memory settlementStatement,
        IHasher hasher,
        DarkpoolState storage state
    )
        internal
    {
        // Nullify the previous version of the balance
        state.spendNullifier(bundle.statement.oldBalanceNullifier);

        // Compute the commitment to the output balance after the settlement is applied
        // Fees are already paid directly as ERC20 transfers for this settlement bundle type, so we only need to update
        // the balance's `amount` share.
        BN254.ScalarField newBalanceCommitment =
            computeFullExistingOutputBalanceCommitment(netReceiveAmount, bundle, settlementStatement, hasher);
        state.insertMerkleLeaf(outputBalanceBundle.merkleDepth, newBalanceCommitment, hasher);

        // Emit a recovery ID for the output balance
        BN254.ScalarField recoveryId = bundle.statement.recoveryId;
        emit IDarkpoolV2.RecoveryIdRegistered(recoveryId);
    }

    // ---------------------------
    // | Commitments Computation |
    // ---------------------------

    /// @notice Compute the full commitment to the updated intent for a Renegade settled private intent bundle
    /// on its first fill
    /// @dev The circuit proves the validity of the private share commitment, so we must:
    /// 1. Compute the updated public share which results from applying the settlement to the leaked `amountIn` share.
    /// 2. Compute the full commitment to the updated intent from the private commitment and public shares.
    /// @param bundleData The bundle data to compute the commitment for
    /// @param internalPartyAmountIn The internal party's input amount (determined at runtime)
    /// @param hasher The hasher to use for hashing
    /// @return newIntentCommitment The full commitment to the updated intent
    function computeFullIntentCommitment(
        RenegadeSettledIntentBoundedFirstFillBundle memory bundleData,
        uint256 internalPartyAmountIn,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField newIntentCommitment)
    {
        IntentAndBalanceValidityStatementFirstFill memory authStatement = bundleData.auth.statement;
        IntentAndBalanceBoundedSettlementStatement memory settlementStatement = bundleData.settlementStatement;

        // 1. Compute the updated public share of the amount in field
        BN254.ScalarField newAmountInShare = settlementStatement.amountPublicShare;
        BN254.ScalarField settlementAmount = BN254.ScalarField.wrap(internalPartyAmountIn);
        newAmountInShare = newAmountInShare.sub(settlementAmount);

        // 2. Create the full updated intent public share
        IntentPublicShare memory newIntentPublicShare =
            authStatement.intentPublicShare.toFullPublicShare(newAmountInShare);
        uint256[] memory publicShares = newIntentPublicShare.scalarSerialize();

        // 3. Compute the full commitment to the updated intent
        newIntentCommitment = CommitmentLib.computeCommitmentWithPublicShares(
            authStatement.intentPrivateShareCommitment, publicShares, hasher
        );
    }

    /// @notice Compute the full commitment to the updated balance for a Renegade settled private intent bundle
    /// on its first fill
    /// @dev The circuit proves the validity of a commitment to all fields of the balance which don't change in the
    /// match,
    /// so we must:
    /// 1. Compute the updated public shares of the balance
    /// 2. Compute the full commitment to the updated balance from the partial commitment and public shares.
    /// @param bundleData The bundle data to compute the commitment for
    /// @param internalPartyAmountIn The internal party's input amount (determined at runtime)
    /// @param hasher The hasher to use for hashing
    /// @return newBalanceCommitment The full commitment to the updated balance
    function computeFullBalanceCommitment(
        RenegadeSettledIntentBoundedFirstFillBundle memory bundleData,
        uint256 internalPartyAmountIn,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField newBalanceCommitment)
    {
        IntentAndBalanceValidityStatementFirstFill memory authStatement = bundleData.auth.statement;
        IntentAndBalanceBoundedSettlementStatement memory settlementStatement = bundleData.settlementStatement;

        // 1. Compute the updated public shares of the balance
        // The fees don't update for the input balance, so we leave them as is
        PostMatchBalanceShare memory newInBalancePublicShares = settlementStatement.inBalancePublicShares;
        BN254.ScalarField settlementAmount = BN254.ScalarField.wrap(internalPartyAmountIn);
        newInBalancePublicShares.amount = newInBalancePublicShares.amount.sub(settlementAmount);

        // 2. Resume the partial commitment with updated shares
        uint256[] memory remainingShares = newInBalancePublicShares.scalarSerialize();
        newBalanceCommitment =
            CommitmentLib.computeResumableCommitment(remainingShares, authStatement.balancePartialCommitment, hasher);
    }

    /// @notice Compute the full commitment to the updated intent for a Renegade settled private intent bundle
    /// on its subsequent fill
    /// @dev The partial commitment computed in the circuit is a commitment to all shares except the public share of the
    /// `amountIn` field, which is updated in a match settlement. We must therefore apply the settlement to the
    /// `amountIn` public share and resume the commitment.
    /// @param bundleData The bundle data to compute the commitment for
    /// @param hasher The hasher to use for hashing
    /// @return newIntentCommitment The full commitment to the updated intent
    function computeFullIntentCommitment(
        RenegadeSettledIntentBoundedBundle memory bundleData,
        uint256 internalPartyAmountIn,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField newIntentCommitment)
    {
        IntentAndBalanceValidityStatement memory authStatement = bundleData.auth.statement;
        IntentAndBalanceBoundedSettlementStatement memory settlementStatement = bundleData.settlementStatement;

        // Compute the updated public share of the amount in field
        BN254.ScalarField newAmountInShare = settlementStatement.amountPublicShare;
        BN254.ScalarField settlementAmount = BN254.ScalarField.wrap(internalPartyAmountIn);
        newAmountInShare = newAmountInShare.sub(settlementAmount);

        // Resume the partial commitment with updated shares
        uint256[] memory remainingShares = new uint256[](1);
        remainingShares[0] = BN254.ScalarField.unwrap(newAmountInShare);
        newIntentCommitment =
            CommitmentLib.computeResumableCommitment(remainingShares, authStatement.newIntentPartialCommitment, hasher);
    }

    /// @notice Compute the full commitment to the updated balance for a Renegade settled private intent bundle
    /// on its subsequent fill
    /// @dev The partial commitment computed in the circuit is a commitment to all shares except the public share of the
    /// `amount` field, which is updated in a match settlement. We must therefore apply the settlement to the
    /// `amount` public share and resume the commitment.
    /// @param bundleData The bundle data to compute the commitment for
    /// @param internalPartyAmountIn The internal party's input amount (determined at runtime)
    /// @param hasher The hasher to use for hashing
    /// @return newBalanceCommitment The full commitment to the updated balance
    function computeFullBalanceCommitment(
        RenegadeSettledIntentBoundedBundle memory bundleData,
        uint256 internalPartyAmountIn,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField newBalanceCommitment)
    {
        IntentAndBalanceValidityStatement memory authStatement = bundleData.auth.statement;
        IntentAndBalanceBoundedSettlementStatement memory settlementStatement = bundleData.settlementStatement;

        // Compute the updated public shares of the balance
        PostMatchBalanceShare memory newInBalancePublicShares = settlementStatement.inBalancePublicShares;
        BN254.ScalarField settlementAmount = BN254.ScalarField.wrap(internalPartyAmountIn);
        newInBalancePublicShares.amount = newInBalancePublicShares.amount.sub(settlementAmount);

        // Resume the partial commitment with updated shares
        uint256[] memory remainingShares = newInBalancePublicShares.scalarSerialize();
        newBalanceCommitment =
            CommitmentLib.computeResumableCommitment(remainingShares, authStatement.balancePartialCommitment, hasher);
    }

    /// @notice Compute the full commitment to a new output balance for a Renegade settled private intent
    /// bundle; after updating the balance's amount share to reflect the settlement
    /// @param netReceiveAmount The net receive amount of the trader after fees have been applied
    /// @param bundle The output balance's authorization bundle
    /// @param settlementStatement The settlement statement to use for the update
    /// @param hasher The hasher contract
    /// @return newBalanceCommitment The full commitment to the new output balance
    function computeFullNewOutputBalanceCommitment(
        uint256 netReceiveAmount,
        NewBalanceBundle memory bundle,
        IntentAndBalanceBoundedSettlementStatement memory settlementStatement,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField newBalanceCommitment)
    {
        PostMatchBalanceShare memory newBalancePublicShares = settlementStatement.outBalancePublicShares;
        BN254.ScalarField netReceiveAmountScalar = BN254.ScalarField.wrap(netReceiveAmount);
        newBalancePublicShares.amount = newBalancePublicShares.amount.add(netReceiveAmountScalar);

        uint256[] memory remainingShares = newBalancePublicShares.scalarSerialize();
        newBalanceCommitment = CommitmentLib.computeResumableCommitment(
            remainingShares, bundle.statement.newBalancePartialCommitment, hasher
        );
    }

    /// @notice Compute the full commitment to an existing output balance for a Renegade settled private intent
    /// bundle; after updating the balance's amount share to reflect the settlement
    /// @param netReceiveAmount The net receive amount of the trader after fees have been applied
    /// @param bundle The output balance's authorization bundle
    /// @param settlementStatement The settlement statement to use for the update
    /// @param hasher The hasher contract
    /// @return newBalanceCommitment The full commitment to the existing output balance
    function computeFullExistingOutputBalanceCommitment(
        uint256 netReceiveAmount,
        ExistingBalanceBundle memory bundle,
        IntentAndBalanceBoundedSettlementStatement memory settlementStatement,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField newBalanceCommitment)
    {
        PostMatchBalanceShare memory newBalancePublicShares = settlementStatement.outBalancePublicShares;
        BN254.ScalarField netReceiveAmountScalar = BN254.ScalarField.wrap(netReceiveAmount);
        newBalancePublicShares.amount = newBalancePublicShares.amount.add(netReceiveAmountScalar);

        uint256[] memory remainingShares = newBalancePublicShares.scalarSerialize();
        newBalanceCommitment =
            CommitmentLib.computeResumableCommitment(remainingShares, bundle.statement.newPartialCommitment, hasher);
    }

    // -------------------
    // | Validity Proofs |
    // -------------------

    /// @notice Push a validity proof to the settlement context
    /// @dev This method also pushes a proof linking argument between the validity proof and the settlement proof
    /// @param publicInputs The public inputs to the validity proof
    /// @param validityProof The validity proof to push
    /// @param settlementProof The settlement proof to push
    /// @param validityVKey The verification key to use for the validity proof
    /// @param linkingVKey The verification key to use for the proof linking argument
    /// @param linkingProof The linking proof between the validity and settlement proofs
    /// @param settlementContext The settlement context to push to
    function pushValidityProof(
        BN254.ScalarField[] memory publicInputs,
        PlonkProof memory validityProof,
        PlonkProof memory settlementProof,
        VerificationKey memory validityVKey,
        ProofLinkingVK memory linkingVKey,
        LinkingProof memory linkingProof,
        SettlementContext memory settlementContext
    )
        internal
        pure
    {
        settlementContext.pushProof(publicInputs, validityProof, validityVKey);
        ProofLinkingInstance memory proofLinkingArgument = ProofLinkingInstance({
            wireComm0: validityProof.wireComms[0],
            wireComm1: settlementProof.wireComms[0],
            proof: linkingProof,
            vk: linkingVKey
        });
        settlementContext.pushProofLinkingArgument(proofLinkingArgument);
    }

    // ---------------------
    // | Settlement Proofs |
    // ---------------------

    /// @notice Push a settlement proof to the settlement context
    /// @param boundedMatchResult The bounded match result to validate. The statement has a copy of this bounded match
    /// result, which must match the value passed in here.
    /// @param statement The settlement statement
    /// @param proof The settlement proof to push
    /// @param vkeys The verification keys contract
    /// @param settlementContext The settlement context to push to
    function verifySettlement(
        BoundedMatchResult memory boundedMatchResult,
        IntentAndBalanceBoundedSettlementStatement memory statement,
        PlonkProof memory proof,
        IVkeys vkeys,
        SettlementContext memory settlementContext
    )
        internal
        view
    {
        // The bounded match result in the settlement statement must match the one from the bounded match result bundle
        bool matchResultMatches = boundedMatchResult.isEqualTo(statement.boundedMatchResult);
        if (!matchResultMatches) revert IDarkpoolV2.InvalidBoundedMatchResult();

        // Push the settlement proof to the settlement context
        BN254.ScalarField[] memory publicInputs = statement.statementSerialize();
        // TODO: Update verification keys
        VerificationKey memory vk = vkeys.intentAndBalancePublicSettlementKeys();
        settlementContext.pushProof(publicInputs, proof, vk);
    }

    // -------------
    // | Transfers |
    // -------------

    /// @notice Apply fees to an obligation and allocate transfers to settle the fees
    /// @param settlementStatement The settlement statement to apply the fees to
    /// @param obligation The obligation to apply the fees to
    /// @param state The darkpool state containing all storage references
    /// @param settlementContext The settlement context to which we append post-validation updates.
    /// @return traderNetReceiveAmount The net receive amount after fees
    function applyFees(
        IntentAndBalanceBoundedSettlementStatement memory settlementStatement,
        SettlementObligation memory obligation,
        DarkpoolState storage state,
        SettlementContext memory settlementContext
    )
        internal
        view
        returns (uint256 traderNetReceiveAmount)
    {
        // Transfer fees to the relayer and protocol collection wallets
        (FeeTake memory relayerFeeTake, FeeTake memory protocolFeeTake) =
            _addFeeTransfers(settlementStatement, obligation, state, settlementContext);

        // Calculate the net receive amount after fees
        uint256 totalFee = relayerFeeTake.fee + protocolFeeTake.fee;
        traderNetReceiveAmount = obligation.amountOut - totalFee;
    }

    /// @notice Allocate the transfers to settle the obligation
    /// @dev We transfer fees out of the balance immediately. This is done to avoid the need to update the balance later
    /// to pay fees. It leaks no extra privacy, because the settlement obligation in this case is known.
    /// @param settlementStatement The settlement statement to allocate the transfers for
    /// @param obligation The obligation to allocate the transfers for
    /// @param state The darkpool state containing all storage references
    /// @param settlementContext The settlement context to which we append post-validation updates.
    /// @return relayerFeeTake The relayer fee take
    /// @return protocolFeeTake The protocol fee take
    function _addFeeTransfers(
        IntentAndBalanceBoundedSettlementStatement memory settlementStatement,
        SettlementObligation memory obligation,
        DarkpoolState storage state,
        SettlementContext memory settlementContext
    )
        internal
        view
        returns (FeeTake memory relayerFeeTake, FeeTake memory protocolFeeTake)
    {
        (relayerFeeTake, protocolFeeTake) = _computeFeeTakes(settlementStatement, obligation, state);

        // Add withdrawal transfers for the fees
        SimpleTransfer memory relayerWithdrawal = relayerFeeTake.buildWithdrawalTransfer();
        SimpleTransfer memory protocolWithdrawal = protocolFeeTake.buildWithdrawalTransfer();
        settlementContext.pushWithdrawal(relayerWithdrawal);
        settlementContext.pushWithdrawal(protocolWithdrawal);
    }

    /// @notice Compute the fee takes for the match
    /// @param settlementStatement The settlement statement to compute the fee takes for
    /// @param obligation The obligation to compute the fee takes for
    /// @param state The darkpool state containing all storage references
    /// @return relayerFeeTake The relayer fee take
    /// @return protocolFeeTake The protocol fee take
    function _computeFeeTakes(
        IntentAndBalanceBoundedSettlementStatement memory settlementStatement,
        SettlementObligation memory obligation,
        DarkpoolState storage state
    )
        internal
        view
        returns (FeeTake memory relayerFeeTake, FeeTake memory protocolFeeTake)
    {
        // First compute the fee rates
        FeeRate memory relayerFeeRate = FeeRate({
            rate: settlementStatement.internalRelayerFeeRate, recipient: settlementStatement.relayerFeeAddress
        });
        FeeRate memory protocolFeeRate = state.getProtocolFeeRate(obligation.inputToken, obligation.outputToken);

        // Then multiply the rates with the receive amount
        uint256 receiveAmount = obligation.amountOut;
        address receiveToken = obligation.outputToken;
        relayerFeeTake = relayerFeeRate.computeFeeTake(receiveToken, receiveAmount);
        protocolFeeTake = protocolFeeRate.computeFeeTake(receiveToken, receiveAmount);
    }
}

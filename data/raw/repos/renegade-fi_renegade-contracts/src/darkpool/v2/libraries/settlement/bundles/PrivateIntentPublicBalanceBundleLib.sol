// SPDX-License-Identifier: Apache
/* solhint-disable one-contract-per-file */
pragma solidity ^0.8.24;

import { IHasher } from "renegade-lib/interfaces/IHasher.sol";
import { PlonkProof, LinkingProof, VerificationKey, ProofLinkingInstance } from "renegade-lib/verifier/Types.sol";
import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";
import { BN254 } from "solidity-bn254/BN254.sol";

import { BoundedMatchResult, BoundedMatchResultLib } from "darkpoolv2-types/BoundedMatchResult.sol";
import { CommitmentLib } from "darkpoolv2-lib/Commitments.sol";
import { DarkpoolState, DarkpoolStateLib } from "darkpoolv2-lib/DarkpoolState.sol";
import { FeeRate, FeeRateLib, FeeTake, FeeTakeLib } from "darkpoolv2-types/Fee.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";
import {
    IntentOnlyBoundedSettlementStatement,
    IntentOnlyPublicSettlementStatement
} from "darkpoolv2-lib/public_inputs/Settlement.sol";
import { IntentPublicShare, IntentPublicShareLib } from "darkpoolv2-types/Intent.sol";
import {
    IntentOnlyValidityStatement,
    IntentOnlyValidityStatementFirstFill
} from "darkpoolv2-lib/public_inputs/ValidityProofs.sol";
import { IVkeys } from "darkpoolv2-interfaces/IVkeys.sol";
import { PartialCommitment } from "darkpoolv2-types/PartialCommitment.sol";
import { PrivateIntentAuthBundle, PrivateIntentAuthBundleFirstFill } from "darkpoolv2-types/settlement/IntentBundle.sol";
import { PublicInputsLib } from "darkpoolv2-lib/public_inputs/PublicInputsLib.sol";
import { SettlementBundle, SettlementBundleType } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { SettlementContext, SettlementContextLib } from "darkpoolv2-types/settlement/SettlementContext.sol";
import { DarkpoolContracts } from "darkpoolv2-contracts/DarkpoolV2.sol";
import { SettlementObligation, SettlementObligationLib } from "darkpoolv2-types/Obligation.sol";
import { SignatureWithNonce, SignatureWithNonceLib } from "darkpoolv2-types/settlement/SignatureWithNonce.sol";
import { SimpleTransfer } from "darkpoolv2-types/transfers/SimpleTransfer.sol";

// ---------------------------------
// | Private Intent Bundle Structs |
// ---------------------------------

/// @notice The settlement bundle data for a `NATIVELY_SETTLED_PRIVATE_INTENT` bundle on the first fill
struct PrivateIntentPublicBalanceFirstFillBundle {
    /// @dev The private intent authorization payload with signature attached
    PrivateIntentAuthBundleFirstFill auth;
    /// @dev The statement of single-intent match settlement
    IntentOnlyPublicSettlementStatement settlementStatement;
    /// @dev The proof of single-intent match settlement
    PlonkProof settlementProof;
    /// @dev The proof linking the authorization and settlement proofs
    LinkingProof authSettlementLinkingProof;
}

/// @notice The settlement bundle data for a `NATIVELY_SETTLED_PRIVATE_INTENT` bundle
struct PrivateIntentPublicBalanceBundle {
    /// @dev The private intent authorization payload with signature attached
    PrivateIntentAuthBundle auth;
    /// @dev The statement of single-intent match settlement
    IntentOnlyPublicSettlementStatement settlementStatement;
    /// @dev The proof of single-intent match settlement
    PlonkProof settlementProof;
    /// @dev The proof linking the authorization and settlement proofs
    LinkingProof authSettlementLinkingProof;
}

/// @notice The settlement bundle data for a `NATIVELY_SETTLED_PRIVATE_INTENT` bounded settlement on the first fill
struct PrivateIntentPublicBalanceBoundedFirstFillBundle {
    /// @dev The private intent authorization payload with signature attached
    PrivateIntentAuthBundleFirstFill auth;
    /// @dev The statement of single-intent bounded settlement
    IntentOnlyBoundedSettlementStatement settlementStatement;
    /// @dev The proof of single-intent bounded settlement
    PlonkProof settlementProof;
    /// @dev The proof linking the authorization and settlement proofs
    LinkingProof authSettlementLinkingProof;
}

/// @notice The settlement bundle data for a `NATIVELY_SETTLED_PRIVATE_INTENT` bounded settlement
struct PrivateIntentPublicBalanceBoundedBundle {
    /// @dev The private intent authorization payload with signature attached
    PrivateIntentAuthBundle auth;
    /// @dev The statement of single-intent bounded settlement
    IntentOnlyBoundedSettlementStatement settlementStatement;
    /// @dev The proof of single-intent bounded settlement
    PlonkProof settlementProof;
    /// @dev The proof linking the authorization and settlement proofs
    LinkingProof authSettlementLinkingProof;
}

// ---------------------------------
// | Private Intent Bundle Library |
// ---------------------------------

/// @title Private Intent Public Balance Bundle Library
/// @author Renegade Eng
/// @notice Library for decoding, computing commitments, and extracting values from private intent bundles
library PrivateIntentPublicBalanceBundleLib {
    using BN254 for BN254.ScalarField;
    using BoundedMatchResultLib for BoundedMatchResult;
    using FeeRateLib for FeeRate;
    using FeeTakeLib for FeeTake;
    using IntentPublicShareLib for IntentPublicShare;
    using PublicInputsLib for IntentOnlyBoundedSettlementStatement;
    using PublicInputsLib for IntentOnlyPublicSettlementStatement;
    using PublicInputsLib for IntentOnlyValidityStatement;
    using PublicInputsLib for IntentOnlyValidityStatementFirstFill;
    using SettlementContextLib for SettlementContext;
    using SettlementObligationLib for SettlementObligation;
    using SignatureWithNonceLib for SignatureWithNonce;
    using DarkpoolStateLib for DarkpoolState;

    // ----------
    // | Decode |
    // ----------

    /// @notice Decode a private settlement bundle for a first fill
    /// @param bundle The settlement bundle to decode
    /// @return bundleData The decoded bundle data
    function decodePrivateIntentBundleDataFirstFill(SettlementBundle calldata bundle)
        internal
        pure
        returns (PrivateIntentPublicBalanceFirstFillBundle memory bundleData)
    {
        bool validType = bundle.isFirstFill && bundle.bundleType == SettlementBundleType.NATIVELY_SETTLED_PRIVATE_INTENT;
        require(validType, IDarkpoolV2.InvalidSettlementBundleType());
        bundleData = abi.decode(bundle.data, (PrivateIntentPublicBalanceFirstFillBundle));
    }

    /// @notice Decode a private settlement bundle
    /// @param bundle The settlement bundle to decode
    /// @return bundleData The decoded bundle data
    function decodePrivateIntentBundleData(SettlementBundle calldata bundle)
        internal
        pure
        returns (PrivateIntentPublicBalanceBundle memory bundleData)
    {
        bool validType =
            !bundle.isFirstFill && bundle.bundleType == SettlementBundleType.NATIVELY_SETTLED_PRIVATE_INTENT;
        require(validType, IDarkpoolV2.InvalidSettlementBundleType());
        bundleData = abi.decode(bundle.data, (PrivateIntentPublicBalanceBundle));
    }

    /// @notice Decode a private intent bounded settlement bundle for a first fill
    /// @param bundle The settlement bundle to decode
    /// @return bundleData The decoded bundle data
    function decodePrivateIntentBoundedBundleDataFirstFill(SettlementBundle calldata bundle)
        internal
        pure
        returns (PrivateIntentPublicBalanceBoundedFirstFillBundle memory bundleData)
    {
        bool validType = bundle.isFirstFill && bundle.bundleType == SettlementBundleType.NATIVELY_SETTLED_PRIVATE_INTENT;
        require(validType, IDarkpoolV2.InvalidSettlementBundleType());
        bundleData = abi.decode(bundle.data, (PrivateIntentPublicBalanceBoundedFirstFillBundle));
    }

    /// @notice Decode a private intent bounded settlement bundle
    /// @param bundle The settlement bundle to decode
    /// @return bundleData The decoded bundle data
    function decodePrivateIntentBoundedBundleData(SettlementBundle calldata bundle)
        internal
        pure
        returns (PrivateIntentPublicBalanceBoundedBundle memory bundleData)
    {
        bool validType =
            !bundle.isFirstFill && bundle.bundleType == SettlementBundleType.NATIVELY_SETTLED_PRIVATE_INTENT;
        require(validType, IDarkpoolV2.InvalidSettlementBundleType());
        bundleData = abi.decode(bundle.data, (PrivateIntentPublicBalanceBoundedBundle));
    }

    // --------------------------
    // | Commitment Computation |
    // --------------------------

    /// @notice Compute the full commitment to the updated intent for a natively settled public intent bundle
    /// on its first fill
    /// @param bundleData The bundle data to compute the commitment for
    /// @param hasher The hasher to use for hashing
    /// @return preUpdateIntentCommitment The commitment to the pre-updated intent
    /// @return postUpdateIntentCommitment The commitment to the post-updated intent
    function computeIntentCommitments(
        PrivateIntentPublicBalanceFirstFillBundle memory bundleData,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField preUpdateIntentCommitment, BN254.ScalarField postUpdateIntentCommitment)
    {
        uint256 settlementAmountIn = bundleData.settlementStatement.obligation.amountIn;
        return _computeIntentCommitmentsInner(settlementAmountIn, bundleData.auth.statement, hasher);
    }

    /// @notice Compute the full commitment to the updated intent for a natively settled private intent bundle
    /// on its first fill (bounded settlement variant)
    /// @dev Unlike the exact match variant, the settlement amount is provided at runtime via `internalPartyAmountIn`
    /// rather than being read from the bundle's settlement statement.
    /// @param bundleData The bundle data to compute the commitments for
    /// @param internalPartyAmountIn The internal party's input amount (determined at runtime)
    /// @param hasher The hasher to use for hashing
    /// @return preUpdateIntentCommitment The commitment to the pre-updated intent
    /// @return postUpdateIntentCommitment The commitment to the post-updated intent
    function computeIntentCommitments(
        PrivateIntentPublicBalanceBoundedFirstFillBundle memory bundleData,
        uint256 internalPartyAmountIn,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField preUpdateIntentCommitment, BN254.ScalarField postUpdateIntentCommitment)
    {
        return _computeIntentCommitmentsInner(internalPartyAmountIn, bundleData.auth.statement, hasher);
    }

    /// @notice Internal helper to compute pre- and post-update intent commitments
    /// @dev Only the amount share in the intent changes between the pre- and post-update intent shares, so we can
    /// compute the shared prefix of the two commitments and then resume the commitment for each of the amount shares.
    /// @param settlementAmountIn The settlement amount in (source varies by bundle type)
    /// @param authStatement The validity statement from the authorization bundle
    /// @param hasher The hasher to use for hashing
    /// @return preUpdate The commitment to the pre-updated intent
    /// @return postUpdate The commitment to the post-updated intent
    function _computeIntentCommitmentsInner(
        uint256 settlementAmountIn,
        IntentOnlyValidityStatementFirstFill memory authStatement,
        IHasher hasher
    )
        private
        view
        returns (BN254.ScalarField preUpdate, BN254.ScalarField postUpdate)
    {
        IntentPublicShare memory intentPublicShare = authStatement.intentPublicShare;

        // 1. Compute the shared prefix of the two commitments
        uint256[] memory intentPublicShareScalars = intentPublicShare.scalarSerializeMatchPrefix();
        uint256 prefixHash = hasher.computeResumableCommitment(intentPublicShareScalars);

        // 2. Compute the full pre-update commitment; i.e. the commitment to the original shares
        PartialCommitment memory sharedPrefixPartialComm = PartialCommitment({
            privateCommitment: authStatement.intentPrivateCommitment,
            partialPublicCommitment: BN254.ScalarField.wrap(prefixHash)
        });

        uint256[] memory preUpdateRemainingShares = new uint256[](1);
        preUpdateRemainingShares[0] = BN254.ScalarField.unwrap(authStatement.intentPublicShare.amountIn);
        preUpdate = CommitmentLib.computeResumableCommitment(preUpdateRemainingShares, sharedPrefixPartialComm, hasher);

        // 3. Compute the full post-update commitment
        // To do so we must update the `amountIn` field in the intent public shares to reflect the settlement
        uint256[] memory postUpdateRemainingShares = new uint256[](1);
        BN254.ScalarField settlementAmount = BN254.ScalarField.wrap(settlementAmountIn);
        BN254.ScalarField newAmountInShare = authStatement.intentPublicShare.amountIn.sub(settlementAmount);
        postUpdateRemainingShares[0] = BN254.ScalarField.unwrap(newAmountInShare);
        postUpdate =
            CommitmentLib.computeResumableCommitment(postUpdateRemainingShares, sharedPrefixPartialComm, hasher);
    }

    /// @notice Compute the full commitment to the updated intent for a natively settled private intent bundle
    /// @param bundleData The bundle data to compute the commitment for
    /// @param hasher The hasher to use for hashing
    /// @return newIntentCommitment The full commitment to the updated intent
    function computeFullIntentCommitment(
        PrivateIntentPublicBalanceBundle memory bundleData,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField newIntentCommitment)
    {
        uint256 settlementAmountIn = bundleData.settlementStatement.obligation.amountIn;
        return _computeFullIntentCommitmentInner(settlementAmountIn, bundleData.auth.statement, hasher);
    }

    /// @notice Compute the full commitment to the updated intent for a natively settled private intent bundle
    /// (bounded settlement variant)
    /// @dev Unlike the exact match variant, the settlement amount is provided at runtime via `internalPartyAmountIn`
    /// rather than being read from the bundle's settlement statement.
    /// @param bundleData The bundle data to compute the commitments for
    /// @param internalPartyAmountIn The internal party's input amount (determined at runtime)
    /// @param hasher The hasher to use for hashing
    /// @return newIntentCommitment The full commitment to the updated intent
    function computeFullIntentCommitment(
        PrivateIntentPublicBalanceBoundedBundle memory bundleData,
        uint256 internalPartyAmountIn,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField newIntentCommitment)
    {
        return _computeFullIntentCommitmentInner(internalPartyAmountIn, bundleData.auth.statement, hasher);
    }

    /// @notice Internal helper to compute full intent commitment for subsequent fill
    /// @dev The only remaining share left out of the partial commitment is the public share of the amount field, which
    /// must be updated to reflect the settlement before committing.
    /// @param settlementAmountIn The settlement amount in (source varies by bundle type)
    /// @param authStatement The validity statement from the authorization bundle
    /// @param hasher The hasher to use for hashing
    /// @return The full commitment to the updated intent
    function _computeFullIntentCommitmentInner(
        uint256 settlementAmountIn,
        IntentOnlyValidityStatement memory authStatement,
        IHasher hasher
    )
        private
        view
        returns (BN254.ScalarField)
    {
        // 1. Apply the settlement to the intent public share
        BN254.ScalarField settlementAmount = BN254.ScalarField.wrap(settlementAmountIn);
        BN254.ScalarField newAmountShareScalar = authStatement.newAmountShare.sub(settlementAmount);

        // 2. Compute the full commitment to the updated intent by resuming from the partial commitment
        uint256[] memory postUpdateRemainingShares = new uint256[](1);
        postUpdateRemainingShares[0] = BN254.ScalarField.unwrap(newAmountShareScalar);
        return CommitmentLib.computeResumableCommitment(
            postUpdateRemainingShares, authStatement.newIntentPartialCommitment, hasher
        );
    }

    // ------------------------
    // | Intent Authorization |
    // ------------------------

    /// @notice Internal helper to verify intent commitment signature
    /// @param preMatchIntentCommitment The pre-match commitment to the intent
    /// @param authBundle The authorization bundle containing the signature
    /// @param state The darkpool state containing all storage references
    function verifyIntentCommitmentSignature(
        BN254.ScalarField preMatchIntentCommitment,
        PrivateIntentAuthBundleFirstFill memory authBundle,
        DarkpoolState storage state
    )
        internal
    {
        address intentOwner = authBundle.statement.intentOwner;
        uint256 commitment = BN254.ScalarField.unwrap(preMatchIntentCommitment);

        bytes32 commitmentHash = EfficientHashLib.hash(bytes32(commitment));
        bool valid = authBundle.intentSignature.verifyPrehashedAndSpendNonce(intentOwner, commitmentHash, state);
        if (!valid) revert IDarkpoolV2.InvalidIntentCommitmentSignature();
    }

    // -------------------------
    // | Constraint Validation |
    // -------------------------

    /// @notice Validate that the obligation matches the settlement statement
    /// @param bundleData The bundle to validate
    /// @param obligation The obligation to match against
    /// @dev Reverts if the obligation does not match
    function validateObligation(
        PrivateIntentPublicBalanceFirstFillBundle memory bundleData,
        SettlementObligation memory obligation
    )
        internal
        pure
    {
        bool matches = obligation.isEqualTo(bundleData.settlementStatement.obligation);
        if (!matches) revert IDarkpoolV2.InvalidObligation();
    }

    /// @notice Validate that the obligation matches the settlement statement
    /// @param bundleData The bundle to validate
    /// @param obligation The obligation to match against
    /// @dev Reverts if the obligation does not match
    function validateObligation(
        PrivateIntentPublicBalanceBundle memory bundleData,
        SettlementObligation memory obligation
    )
        internal
        pure
    {
        bool matches = obligation.isEqualTo(bundleData.settlementStatement.obligation);
        if (!matches) revert IDarkpoolV2.InvalidObligation();
    }

    /// @notice Validate that the bounded match result matches the settlement statement
    /// @param bundleData The bundle to validate
    /// @param matchResult The match result to match against
    /// @dev Reverts if the match result does not match
    function validateMatchResult(
        PrivateIntentPublicBalanceBoundedFirstFillBundle memory bundleData,
        BoundedMatchResult memory matchResult
    )
        internal
        pure
    {
        bool matches = matchResult.isEqualTo(bundleData.settlementStatement.boundedMatchResult);
        if (!matches) revert IDarkpoolV2.InvalidBoundedMatchResult();
    }

    /// @notice Validate that the bounded match result matches the settlement statement
    /// @param bundleData The bundle to validate
    /// @param matchResult The match result to match against
    /// @dev Reverts if the match result does not match
    function validateMatchResult(
        PrivateIntentPublicBalanceBoundedBundle memory bundleData,
        BoundedMatchResult memory matchResult
    )
        internal
        pure
    {
        bool matches = matchResult.isEqualTo(bundleData.settlementStatement.boundedMatchResult);
        if (!matches) revert IDarkpoolV2.InvalidBoundedMatchResult();
    }

    // -------------------
    // | Validity Proofs |
    // -------------------

    /// @notice Push the validity proof to the context and validate merkle depth
    /// @param bundleData The bundle containing the validity proof
    /// @param settlementContext The context to push to
    /// @param contracts The contract references needed for settlement
    function pushValidityProof(
        PrivateIntentPublicBalanceFirstFillBundle memory bundleData,
        SettlementContext memory settlementContext,
        DarkpoolContracts memory contracts
    )
        internal
        view
    {
        BN254.ScalarField[] memory publicInputs = bundleData.auth.statement.statementSerialize();
        VerificationKey memory vk = contracts.vkeys.intentOnlyFirstFillValidityKeys();
        _pushValidityProofInner(publicInputs, bundleData.auth.validityProof, vk, settlementContext);
    }

    /// @notice Push the validity proof to the context and validate merkle depth
    /// @param bundleData The bundle containing the validity proof
    /// @param settlementContext The context to push to
    /// @param contracts The contract references needed for settlement
    /// @param state The darkpool state for root validation
    function pushValidityProof(
        PrivateIntentPublicBalanceBundle memory bundleData,
        SettlementContext memory settlementContext,
        DarkpoolContracts memory contracts,
        DarkpoolState storage state
    )
        internal
        view
    {
        BN254.ScalarField[] memory publicInputs = bundleData.auth.statement.statementSerialize();
        VerificationKey memory vk = contracts.vkeys.intentOnlyValidityKeys();
        _pushValidityProofInner(publicInputs, bundleData.auth.validityProof, vk, settlementContext);
        state.assertRootInHistory(bundleData.auth.statement.merkleRoot);
    }

    /// @notice Push the validity proof to the context and validate merkle depth
    /// @param bundleData The bundle containing the validity proof
    /// @param settlementContext The context to push to
    /// @param contracts The contract references needed for settlement
    function pushValidityProof(
        PrivateIntentPublicBalanceBoundedFirstFillBundle memory bundleData,
        SettlementContext memory settlementContext,
        DarkpoolContracts memory contracts
    )
        internal
        view
    {
        BN254.ScalarField[] memory publicInputs = bundleData.auth.statement.statementSerialize();
        VerificationKey memory vk = contracts.vkeys.intentOnlyFirstFillValidityKeys();
        _pushValidityProofInner(publicInputs, bundleData.auth.validityProof, vk, settlementContext);
    }

    /// @notice Push the validity proof to the context and validate merkle depth
    /// @param bundleData The bundle containing the validity proof
    /// @param settlementContext The context to push to
    /// @param contracts The contract references needed for settlement
    /// @param state The darkpool state for root validation
    function pushValidityProof(
        PrivateIntentPublicBalanceBoundedBundle memory bundleData,
        SettlementContext memory settlementContext,
        DarkpoolContracts memory contracts,
        DarkpoolState storage state
    )
        internal
        view
    {
        BN254.ScalarField[] memory publicInputs = bundleData.auth.statement.statementSerialize();
        VerificationKey memory vk = contracts.vkeys.intentOnlyValidityKeys();
        _pushValidityProofInner(publicInputs, bundleData.auth.validityProof, vk, settlementContext);
        state.assertRootInHistory(bundleData.auth.statement.merkleRoot);
    }

    /// @notice Internal helper to validate merkle depth and push validity proof
    /// @param publicInputs The serialized public inputs
    /// @param validityProof The validity proof to push
    /// @param vk The verification key to use
    /// @param settlementContext The context to push to
    function _pushValidityProofInner(
        BN254.ScalarField[] memory publicInputs,
        PlonkProof memory validityProof,
        VerificationKey memory vk,
        SettlementContext memory settlementContext
    )
        private
        pure
    {
        settlementContext.pushProof(publicInputs, validityProof, vk);
    }

    // ---------------------
    // | Settlement Proofs |
    // ---------------------

    /// @notice Push the settlement proof and proof linking argument to the context
    /// @param bundleData The bundle containing proofs
    /// @param settlementContext The context to push to
    /// @param contracts The contract references needed for settlement
    function pushSettlementProofs(
        PrivateIntentPublicBalanceFirstFillBundle memory bundleData,
        SettlementContext memory settlementContext,
        DarkpoolContracts memory contracts
    )
        internal
        view
    {
        _pushSettlementProofsInner(
            bundleData.settlementStatement,
            bundleData.settlementProof,
            bundleData.auth.validityProof,
            bundleData.authSettlementLinkingProof,
            settlementContext,
            contracts
        );
    }

    /// @notice Push the settlement proof and proof linking argument to the context
    /// @param bundleData The bundle containing proofs
    /// @param settlementContext The context to push to
    /// @param contracts The contract references needed for settlement
    function pushSettlementProofs(
        PrivateIntentPublicBalanceBundle memory bundleData,
        SettlementContext memory settlementContext,
        DarkpoolContracts memory contracts
    )
        internal
        view
    {
        _pushSettlementProofsInner(
            bundleData.settlementStatement,
            bundleData.settlementProof,
            bundleData.auth.validityProof,
            bundleData.authSettlementLinkingProof,
            settlementContext,
            contracts
        );
    }

    /// @notice Push the settlement proof to the context for a bounded settlement
    /// @param bundleData The bundle containing proofs
    /// @param settlementContext The context to push to
    function pushSettlementProofs(
        PrivateIntentPublicBalanceBoundedFirstFillBundle memory bundleData,
        SettlementContext memory settlementContext
    )
        internal
        pure
    {
        _pushBoundedSettlementProofInner(bundleData.settlementStatement, bundleData.settlementProof, settlementContext);
    }

    /// @notice Push the settlement proof to the context for a bounded settlement
    /// @param bundleData The bundle containing proofs
    /// @param settlementContext The context to push to
    function pushSettlementProofs(
        PrivateIntentPublicBalanceBoundedBundle memory bundleData,
        SettlementContext memory settlementContext
    )
        internal
        pure
    {
        _pushBoundedSettlementProofInner(bundleData.settlementStatement, bundleData.settlementProof, settlementContext);
    }

    /// @notice Internal helper to push settlement proof and proof linking for exact match
    /// @param settlementStatement The settlement statement
    /// @param settlementProof The settlement proof
    /// @param validityProof The validity proof (for proof linking)
    /// @param authSettlementLinkingProof The proof linking the auth and settlement proofs
    /// @param settlementContext The context to push to
    /// @param contracts The contract references needed for settlement
    function _pushSettlementProofsInner(
        IntentOnlyPublicSettlementStatement memory settlementStatement,
        PlonkProof memory settlementProof,
        PlonkProof memory validityProof,
        LinkingProof memory authSettlementLinkingProof,
        SettlementContext memory settlementContext,
        DarkpoolContracts memory contracts
    )
        private
        view
    {
        // Push the settlement proof
        BN254.ScalarField[] memory publicInputs = settlementStatement.statementSerialize();
        VerificationKey memory vk = contracts.vkeys.intentOnlyPublicSettlementKeys();
        settlementContext.pushProof(publicInputs, settlementProof, vk);

        // Push the proof linking argument
        ProofLinkingInstance memory proofLinkingArgument = ProofLinkingInstance({
            wireComm0: validityProof.wireComms[0],
            wireComm1: settlementProof.wireComms[0],
            proof: authSettlementLinkingProof,
            vk: contracts.vkeys.intentOnlySettlementLinkingKey()
        });
        settlementContext.pushProofLinkingArgument(proofLinkingArgument);
    }

    /// @notice Internal helper to push settlement proof for bounded match
    /// @param settlementStatement The bounded settlement statement
    /// @param settlementProof The settlement proof
    /// @param settlementContext The context to push to
    function _pushBoundedSettlementProofInner(
        IntentOnlyBoundedSettlementStatement memory settlementStatement,
        PlonkProof memory settlementProof,
        SettlementContext memory settlementContext
    )
        private
        pure
    {
        // Push the settlement proof
        BN254.ScalarField[] memory publicInputs = settlementStatement.statementSerialize();
        VerificationKey memory vk = PublicInputsLib.dummyVkey();
        settlementContext.pushProof(publicInputs, settlementProof, vk);

        // TODO: Push the proof linking argument
    }

    // -------------
    // | Transfers |
    // -------------

    /// @notice Allocate transfers to settle the obligation for a first fill exact bundle
    /// @param bundleData The bundle to extract owner and fee rate from
    /// @param obligation The settlement obligation
    /// @param settlementContext The context to push transfers to
    /// @param state The darkpool state containing all storage references
    function allocateTransfers(
        PrivateIntentPublicBalanceFirstFillBundle memory bundleData,
        SettlementObligation memory obligation,
        SettlementContext memory settlementContext,
        DarkpoolState storage state
    )
        internal
        view
    {
        address owner = bundleData.auth.statement.intentOwner;
        FeeRate memory relayerFeeRate = FeeRate({
            rate: bundleData.settlementStatement.relayerFee,
            recipient: bundleData.settlementStatement.relayerFeeRecipient
        });
        _allocateTransfersInner(owner, relayerFeeRate, obligation, settlementContext, state);
    }

    /// @notice Allocate transfers to settle the obligation for a subsequent fill exact bundle
    /// @param bundleData The bundle to extract owner and fee rate from
    /// @param obligation The settlement obligation
    /// @param settlementContext The context to push transfers to
    /// @param state The darkpool state containing all storage references
    function allocateTransfers(
        PrivateIntentPublicBalanceBundle memory bundleData,
        SettlementObligation memory obligation,
        SettlementContext memory settlementContext,
        DarkpoolState storage state
    )
        internal
        view
    {
        address owner = bundleData.auth.statement.intentOwner;
        FeeRate memory relayerFeeRate = FeeRate({
            rate: bundleData.settlementStatement.relayerFee,
            recipient: bundleData.settlementStatement.relayerFeeRecipient
        });
        _allocateTransfersInner(owner, relayerFeeRate, obligation, settlementContext, state);
    }

    /// @notice Allocate transfers to settle the obligation for a first fill bounded bundle
    /// @param bundleData The bundle to extract owner and fee rate from
    /// @param obligation The settlement obligation
    /// @param settlementContext The context to push transfers to
    /// @param state The darkpool state containing all storage references
    function allocateTransfers(
        PrivateIntentPublicBalanceBoundedFirstFillBundle memory bundleData,
        SettlementObligation memory obligation,
        SettlementContext memory settlementContext,
        DarkpoolState storage state
    )
        internal
        view
    {
        address owner = bundleData.auth.statement.intentOwner;
        FeeRate memory relayerFeeRate = FeeRate({
            rate: bundleData.settlementStatement.internalRelayerFeeRate,
            recipient: bundleData.settlementStatement.relayerFeeAddress
        });
        _allocateTransfersInner(owner, relayerFeeRate, obligation, settlementContext, state);
    }

    /// @notice Allocate transfers to settle the obligation for a subsequent fill bounded bundle
    /// @param bundleData The bundle to extract owner and fee rate from
    /// @param obligation The settlement obligation
    /// @param settlementContext The context to push transfers to
    /// @param state The darkpool state containing all storage references
    function allocateTransfers(
        PrivateIntentPublicBalanceBoundedBundle memory bundleData,
        SettlementObligation memory obligation,
        SettlementContext memory settlementContext,
        DarkpoolState storage state
    )
        internal
        view
    {
        address owner = bundleData.auth.statement.intentOwner;
        FeeRate memory relayerFeeRate = FeeRate({
            rate: bundleData.settlementStatement.internalRelayerFeeRate,
            recipient: bundleData.settlementStatement.relayerFeeAddress
        });
        _allocateTransfersInner(owner, relayerFeeRate, obligation, settlementContext, state);
    }

    /// @notice Internal helper to allocate transfers - not exposed to orchestrator
    /// @param owner The owner of the intent
    /// @param relayerFeeRate The relayer fee rate (extracted from bundle)
    /// @param obligation The settlement obligation
    /// @param settlementContext The context to push transfers to
    /// @param state The darkpool state containing all storage references
    function _allocateTransfersInner(
        address owner,
        FeeRate memory relayerFeeRate,
        SettlementObligation memory obligation,
        SettlementContext memory settlementContext,
        DarkpoolState storage state
    )
        private
        view
    {
        // Fetch protocol fee rate from state
        FeeRate memory protocolFeeRate = state.getProtocolFeeRate(obligation.inputToken, obligation.outputToken);

        // Compute fee takes
        FeeTake memory relayerFeeTake = relayerFeeRate.computeFeeTake(obligation.outputToken, obligation.amountOut);
        FeeTake memory protocolFeeTake = protocolFeeRate.computeFeeTake(obligation.outputToken, obligation.amountOut);

        // Deposit the input token into the darkpool
        SimpleTransfer memory deposit = obligation.buildPermit2AllowanceDeposit(owner);
        settlementContext.pushDeposit(deposit);

        // Withdraw the output token from the darkpool (minus fees)
        uint256 totalFee = relayerFeeTake.fee + protocolFeeTake.fee;
        SimpleTransfer memory withdrawal = obligation.buildWithdrawalTransfer(owner, totalFee);
        settlementContext.pushWithdrawal(withdrawal);

        // Withdraw the relayer and protocol fees to their respective recipients
        settlementContext.pushWithdrawal(relayerFeeTake.buildWithdrawalTransfer());
        settlementContext.pushWithdrawal(protocolFeeTake.buildWithdrawalTransfer());
    }
}

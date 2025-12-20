// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import {
    PlonkProof,
    VerificationKey,
    OpeningElements,
    ProofLinkingVK,
    ProofLinkingInstance
} from "renegade-lib/verifier/Types.sol";
import {
    ValidWalletCreateStatement,
    ValidWalletUpdateStatement,
    ValidCommitmentsStatement,
    ValidReblindStatement,
    ValidMatchSettleStatement,
    ValidMatchSettleWithCommitmentsStatement,
    ValidMatchSettleAtomicStatement,
    ValidMatchSettleAtomicWithCommitmentsStatement,
    ValidMalleableMatchSettleAtomicStatement,
    ValidOfflineFeeSettlementStatement,
    ValidFeeRedemptionStatement,
    StatementSerializer
} from "darkpoolv1-lib/PublicInputs.sol";
import {
    PartyMatchPayload,
    MatchProofs,
    MatchLinkingProofs,
    MatchAtomicProofs,
    MatchAtomicLinkingProofs,
    MalleableMatchAtomicProofs
} from "darkpoolv1-types/Settlement.sol";
import { IVKeys } from "darkpoolv1-interfaces/IVKeys.sol";
import { IVerifier } from "darkpoolv1-interfaces/IVerifier.sol";
import { VerifierCore } from "renegade-lib/verifier/VerifierCore.sol";
import { ProofLinkingCore } from "renegade-lib/verifier/ProofLinking.sol";
import { BN254 } from "solidity-bn254/BN254.sol";

using StatementSerializer for ValidWalletCreateStatement;
using StatementSerializer for ValidWalletUpdateStatement;
using StatementSerializer for ValidCommitmentsStatement;
using StatementSerializer for ValidReblindStatement;
using StatementSerializer for ValidMatchSettleStatement;
using StatementSerializer for ValidMatchSettleWithCommitmentsStatement;
using StatementSerializer for ValidMatchSettleAtomicStatement;
using StatementSerializer for ValidMatchSettleAtomicWithCommitmentsStatement;
using StatementSerializer for ValidOfflineFeeSettlementStatement;
using StatementSerializer for ValidFeeRedemptionStatement;
using StatementSerializer for ValidMalleableMatchSettleAtomicStatement;

/// @title PlonK Verifier with the Jellyfish-style arithmetization
/// @author Renegade Eng
/// @notice The methods on this contract are darkpool-specific
contract Verifier is IVerifier {
    /// @notice The number of proofs in a match bundle
    uint256 public constant NUM_MATCH_PROOFS = 5;
    /// @notice The number of linking proofs in a match bundle
    uint256 public constant NUM_MATCH_LINKING_PROOFS = 4;
    /// @notice The number of proofs in an atomic match bundle
    uint256 public constant NUM_ATOMIC_MATCH_PROOFS = 3;
    /// @notice The number of linking proofs in an atomic match bundle
    uint256 public constant NUM_ATOMIC_MATCH_LINKING_PROOFS = 2;
    /// @notice The number of proofs in a malleable match bundle
    uint256 public constant NUM_MALLEABLE_MATCH_PROOFS = 3;
    /// @notice The number of linking proofs in a malleable match bundle
    uint256 public constant NUM_MALLEABLE_MATCH_LINKING_PROOFS = 2;

    /// @notice The verification keys contract
    IVKeys public immutable VKEYS;

    /// @notice Constructor that sets the verification keys contract
    /// @param _vkeys The verification keys contract address
    constructor(IVKeys _vkeys) {
        VKEYS = _vkeys;
    }

    /// @notice Verify a proof of `VALID WALLET CREATE`
    /// @param statement The public inputs to the proof
    /// @param proof The proof to verify
    /// @return True if the proof is valid, false otherwise
    function verifyValidWalletCreate(
        ValidWalletCreateStatement calldata statement,
        PlonkProof calldata proof
    )
        external
        view
        returns (bool)
    {
        VerificationKey memory vk = VKEYS.walletCreateKeys();
        BN254.ScalarField[] memory publicInputs = statement.scalarSerialize();
        return VerifierCore.verify(proof, publicInputs, vk);
    }

    /// @notice Verify a proof of `VALID WALLET UPDATE`
    /// @param statement The public inputs to the proof
    /// @param proof The proof to verify
    /// @return True if the proof is valid, false otherwise
    function verifyValidWalletUpdate(
        ValidWalletUpdateStatement calldata statement,
        PlonkProof calldata proof
    )
        external
        view
        returns (bool)
    {
        VerificationKey memory vk = VKEYS.walletUpdateKeys();
        BN254.ScalarField[] memory publicInputs = statement.scalarSerialize();
        return VerifierCore.verify(proof, publicInputs, vk);
    }

    /// @notice Verify a match bundle
    /// @param party0MatchPayload The payload for the first party
    /// @param party1MatchPayload The payload for the second party
    /// @param matchSettleStatement The statement of `VALID MATCH SETTLE`
    /// @param matchProofs The proofs for the match, including two sets of validity proofs and a settlement proof
    /// @param matchLinkingProofs The proof linking arguments for the match
    /// @return True if the match bundle is valid, false otherwise
    function verifyMatchBundle(
        PartyMatchPayload calldata party0MatchPayload,
        PartyMatchPayload calldata party1MatchPayload,
        ValidMatchSettleStatement calldata matchSettleStatement,
        MatchProofs calldata matchProofs,
        MatchLinkingProofs calldata matchLinkingProofs
    )
        external
        view
        returns (bool)
    {
        // Load the verification keys
        (
            VerificationKey memory commitmentsVk,
            VerificationKey memory reblindVk,
            VerificationKey memory settleVk,
            ProofLinkingVK memory reblindCommitmentsVk,
            ProofLinkingVK memory commitmentsMatchSettleVk0,
            ProofLinkingVK memory commitmentsMatchSettleVk1
        ) = VKEYS.matchBundleKeys();

        // Build the batch
        PlonkProof[] memory proofs = new PlonkProof[](NUM_MATCH_PROOFS);
        BN254.ScalarField[][] memory publicInputs = new BN254.ScalarField[][](NUM_MATCH_PROOFS);
        VerificationKey[] memory vks = new VerificationKey[](NUM_MATCH_PROOFS);
        proofs[0] = matchProofs.validCommitments0;
        proofs[1] = matchProofs.validReblind0;
        proofs[2] = matchProofs.validCommitments1;
        proofs[3] = matchProofs.validReblind1;
        proofs[4] = matchProofs.validMatchSettle;

        publicInputs[0] = party0MatchPayload.validCommitmentsStatement.scalarSerialize();
        publicInputs[1] = party0MatchPayload.validReblindStatement.scalarSerialize();
        publicInputs[2] = party1MatchPayload.validCommitmentsStatement.scalarSerialize();
        publicInputs[3] = party1MatchPayload.validReblindStatement.scalarSerialize();
        publicInputs[4] = matchSettleStatement.scalarSerialize();

        vks[0] = commitmentsVk;
        vks[1] = reblindVk;
        vks[2] = commitmentsVk;
        vks[3] = reblindVk;
        vks[4] = settleVk;

        // Add proof linking instances to the opening
        ProofLinkingInstance[] memory instances = createMatchLinkingInstances(
            matchProofs, matchLinkingProofs, reblindCommitmentsVk, commitmentsMatchSettleVk0, commitmentsMatchSettleVk1
        );
        OpeningElements memory linkOpenings = ProofLinkingCore.createOpeningElements(instances);

        // Verify the batch
        return VerifierCore.batchVerify(proofs, publicInputs, vks, linkOpenings);
    }

    /// @notice Verify a proof of `VALID MATCH SETTLE WITH COMMITMENTS`
    /// @dev We use the same verification types between variants of `VALID MATCH SETTLE`.
    /// @dev The statements and vkeys capture different relations, but their shapes are identical
    /// @dev and the linking group layouts are the same.
    /// @param party0MatchPayload The payload for the first party
    /// @param party1MatchPayload The payload for the second party
    /// @param matchSettleStatement The statement of `VALID MATCH SETTLE WITH COMMITMENTS`
    /// @param matchProofs The proofs for the match, including two sets of validity proofs and a settlement proof
    /// @param matchLinkingProofs The proof linking arguments for the match
    /// @return True if the match bundle is valid, false otherwise
    function verifyMatchBundleWithCommitments(
        PartyMatchPayload calldata party0MatchPayload,
        PartyMatchPayload calldata party1MatchPayload,
        ValidMatchSettleWithCommitmentsStatement calldata matchSettleStatement,
        MatchProofs calldata matchProofs,
        MatchLinkingProofs calldata matchLinkingProofs
    )
        external
        view
        returns (bool)
    {
        // Load the verification keys
        (
            VerificationKey memory commitmentsVk,
            VerificationKey memory reblindVk,
            VerificationKey memory settleVk,
            ProofLinkingVK memory reblindCommitmentsVk,
            ProofLinkingVK memory commitmentsMatchSettleVk0,
            ProofLinkingVK memory commitmentsMatchSettleVk1
        ) = VKEYS.matchBundleWithCommitmentsKeys();

        // Build the batch
        PlonkProof[] memory proofs = new PlonkProof[](NUM_MATCH_PROOFS);
        BN254.ScalarField[][] memory publicInputs = new BN254.ScalarField[][](NUM_MATCH_PROOFS);
        VerificationKey[] memory vks = new VerificationKey[](NUM_MATCH_PROOFS);
        proofs[0] = matchProofs.validCommitments0;
        proofs[1] = matchProofs.validReblind0;
        proofs[2] = matchProofs.validCommitments1;
        proofs[3] = matchProofs.validReblind1;
        proofs[4] = matchProofs.validMatchSettle;

        publicInputs[0] = party0MatchPayload.validCommitmentsStatement.scalarSerialize();
        publicInputs[1] = party0MatchPayload.validReblindStatement.scalarSerialize();
        publicInputs[2] = party1MatchPayload.validCommitmentsStatement.scalarSerialize();
        publicInputs[3] = party1MatchPayload.validReblindStatement.scalarSerialize();
        publicInputs[4] = matchSettleStatement.scalarSerialize();

        vks[0] = commitmentsVk;
        vks[1] = reblindVk;
        vks[2] = commitmentsVk;
        vks[3] = reblindVk;
        vks[4] = settleVk;

        // Add proof linking instances to the opening
        ProofLinkingInstance[] memory instances = createMatchLinkingInstances(
            matchProofs, matchLinkingProofs, reblindCommitmentsVk, commitmentsMatchSettleVk0, commitmentsMatchSettleVk1
        );
        OpeningElements memory linkOpenings = ProofLinkingCore.createOpeningElements(instances);

        // Verify the batch
        return VerifierCore.batchVerify(proofs, publicInputs, vks, linkOpenings);
    }

    /// @notice Verify an atomic match bundle
    /// @param internalPartyPayload The payload for the internal party
    /// @param matchSettleStatement The statement of `VALID MATCH SETTLE ATOMIC`
    /// @param matchProofs The proofs for the match, including a validity proof and a settlement proof
    /// @param matchLinkingProofs The proof linking arguments for the match
    /// @return True if the atomic match bundle is valid, false otherwise
    function verifyAtomicMatchBundle(
        PartyMatchPayload calldata internalPartyPayload,
        ValidMatchSettleAtomicStatement calldata matchSettleStatement,
        MatchAtomicProofs calldata matchProofs,
        MatchAtomicLinkingProofs calldata matchLinkingProofs
    )
        external
        view
        returns (bool)
    {
        // Load the verification keys
        (
            VerificationKey memory commitmentsVk,
            VerificationKey memory reblindVk,
            VerificationKey memory settleVk,
            ProofLinkingVK memory reblindCommitmentsVk,
            ProofLinkingVK memory commitmentsMatchSettleVk
        ) = VKEYS.atomicMatchBundleKeys();

        // Build the batch
        PlonkProof[] memory proofs = new PlonkProof[](NUM_ATOMIC_MATCH_PROOFS);
        BN254.ScalarField[][] memory publicInputs = new BN254.ScalarField[][](NUM_ATOMIC_MATCH_PROOFS);
        VerificationKey[] memory vks = new VerificationKey[](NUM_ATOMIC_MATCH_PROOFS);
        proofs[0] = matchProofs.validCommitments;
        proofs[1] = matchProofs.validReblind;
        proofs[2] = matchProofs.validMatchSettleAtomic;

        publicInputs[0] = internalPartyPayload.validCommitmentsStatement.scalarSerialize();
        publicInputs[1] = internalPartyPayload.validReblindStatement.scalarSerialize();
        publicInputs[2] = matchSettleStatement.scalarSerialize();

        vks[0] = commitmentsVk;
        vks[1] = reblindVk;
        vks[2] = settleVk;

        // Add proof linking instances to the opening
        ProofLinkingInstance[] memory instances = createAtomicMatchLinkingInstances(
            matchProofs, matchLinkingProofs, reblindCommitmentsVk, commitmentsMatchSettleVk
        );
        OpeningElements memory linkOpenings = ProofLinkingCore.createOpeningElements(instances);

        // Verify the batch
        return VerifierCore.batchVerify(proofs, publicInputs, vks, linkOpenings);
    }

    /// @notice Verify a proof of `VALID MATCH SETTLE ATOMIC WITH COMMITMENTS`
    /// @param internalPartyPayload The payload for the internal party
    /// @param matchSettleStatement The statement of `VALID MATCH SETTLE ATOMIC WITH COMMITMENTS`
    /// @param matchProofs The proofs for the match, including a validity proof and a settlement proof
    /// @param matchLinkingProofs The proof linking arguments for the match
    /// @return True if the atomic match bundle is valid, false otherwise
    function verifyAtomicMatchBundleWithCommitments(
        PartyMatchPayload calldata internalPartyPayload,
        ValidMatchSettleAtomicWithCommitmentsStatement calldata matchSettleStatement,
        MatchAtomicProofs calldata matchProofs,
        MatchAtomicLinkingProofs calldata matchLinkingProofs
    )
        external
        view
        returns (bool)
    {
        // Load the verification keys
        (
            VerificationKey memory commitmentsVk,
            VerificationKey memory reblindVk,
            VerificationKey memory settleVk,
            ProofLinkingVK memory reblindCommitmentsVk,
            ProofLinkingVK memory commitmentsMatchSettleVk
        ) = VKEYS.atomicMatchBundleWithCommitmentsKeys();

        // Build the batch
        PlonkProof[] memory proofs = new PlonkProof[](NUM_ATOMIC_MATCH_PROOFS);
        BN254.ScalarField[][] memory publicInputs = new BN254.ScalarField[][](NUM_ATOMIC_MATCH_PROOFS);
        VerificationKey[] memory vks = new VerificationKey[](NUM_ATOMIC_MATCH_PROOFS);
        proofs[0] = matchProofs.validCommitments;
        proofs[1] = matchProofs.validReblind;
        proofs[2] = matchProofs.validMatchSettleAtomic;

        publicInputs[0] = internalPartyPayload.validCommitmentsStatement.scalarSerialize();
        publicInputs[1] = internalPartyPayload.validReblindStatement.scalarSerialize();
        publicInputs[2] = matchSettleStatement.scalarSerialize();

        vks[0] = commitmentsVk;
        vks[1] = reblindVk;
        vks[2] = settleVk;

        // Add proof linking instances to the opening
        ProofLinkingInstance[] memory instances = createAtomicMatchLinkingInstances(
            matchProofs, matchLinkingProofs, reblindCommitmentsVk, commitmentsMatchSettleVk
        );
        OpeningElements memory linkOpenings = ProofLinkingCore.createOpeningElements(instances);

        // Verify the batch
        return VerifierCore.batchVerify(proofs, publicInputs, vks, linkOpenings);
    }

    /// @notice Verify a malleable match bundle
    /// @param internalPartyPayload The payload for the internal party
    /// @param matchSettleStatement The statement of `VALID MALLEABLE MATCH SETTLE ATOMIC`
    /// @param proofBundle The proofs for the match, including a validity proof and a settlement proof
    /// @param linkingProofs The proof linking arguments for the match
    /// @return True if the malleable match bundle is valid, false otherwise
    function verifyMalleableMatchBundle(
        PartyMatchPayload calldata internalPartyPayload,
        ValidMalleableMatchSettleAtomicStatement calldata matchSettleStatement,
        MalleableMatchAtomicProofs calldata proofBundle,
        MatchAtomicLinkingProofs calldata linkingProofs
    )
        external
        view
        returns (bool)
    {
        // Load the verification keys
        (
            VerificationKey memory commitmentsVk,
            VerificationKey memory reblindVk,
            VerificationKey memory settleVk,
            ProofLinkingVK memory reblindCommitmentsVk,
            ProofLinkingVK memory commitmentsMatchSettleVk
        ) = VKEYS.malleableMatchBundleKeys();

        // Build the batch
        PlonkProof[] memory proofs = new PlonkProof[](NUM_MALLEABLE_MATCH_PROOFS);
        BN254.ScalarField[][] memory publicInputs = new BN254.ScalarField[][](NUM_MALLEABLE_MATCH_PROOFS);
        VerificationKey[] memory vks = new VerificationKey[](NUM_MALLEABLE_MATCH_PROOFS);
        proofs[0] = proofBundle.validCommitments;
        proofs[1] = proofBundle.validReblind;
        proofs[2] = proofBundle.validMalleableMatchSettleAtomic;

        publicInputs[0] = internalPartyPayload.validCommitmentsStatement.scalarSerialize();
        publicInputs[1] = internalPartyPayload.validReblindStatement.scalarSerialize();
        publicInputs[2] = matchSettleStatement.scalarSerialize();

        vks[0] = commitmentsVk;
        vks[1] = reblindVk;
        vks[2] = settleVk;

        // Add proof linking instances to the opening
        ProofLinkingInstance[] memory instances = createMalleableMatchLinkingInstances(
            proofBundle, linkingProofs, reblindCommitmentsVk, commitmentsMatchSettleVk
        );
        OpeningElements memory linkOpenings = ProofLinkingCore.createOpeningElements(instances);

        // Verify the batch
        return VerifierCore.batchVerify(proofs, publicInputs, vks, linkOpenings);
    }

    /// @notice Verify a proof of `VALID OFFLINE FEE SETTLEMENT`
    /// @param statement The public inputs to the proof
    /// @param proof The proof to verify
    /// @return True if the proof is valid, false otherwise
    function verifyValidOfflineFeeSettlement(
        ValidOfflineFeeSettlementStatement calldata statement,
        PlonkProof calldata proof
    )
        external
        view
        returns (bool)
    {
        VerificationKey memory vk = VKEYS.offlineFeeSettlementKeys();
        BN254.ScalarField[] memory publicInputs = statement.scalarSerialize();
        return VerifierCore.verify(proof, publicInputs, vk);
    }

    /// @notice Verify a proof of `VALID FEE REDEMPTION`
    /// @param statement The public inputs to the proof
    /// @param proof The proof to verify
    /// @return True if the proof is valid, false otherwise
    function verifyValidFeeRedemption(
        ValidFeeRedemptionStatement calldata statement,
        PlonkProof calldata proof
    )
        external
        view
        returns (bool)
    {
        VerificationKey memory vk = VKEYS.feeRedemptionKeys();
        BN254.ScalarField[] memory publicInputs = statement.scalarSerialize();
        return VerifierCore.verify(proof, publicInputs, vk);
    }

    // --- Helpers --- //

    /// @notice Create a set of match linking instances
    /// @param matchProofs The proofs for the match, including two sets of validity proofs and a settlement proof
    /// @param matchLinkingProofs The proof linking arguments for the match
    /// @param reblindCommitmentsVk The linking key for `VALID REBLIND` -> `VALID COMMITMENTS`
    /// @param commitmentsMatchSettleVk0 The linking key for `VALID COMMITMENTS` -> `VALID MATCH SETTLE`
    /// @param commitmentsMatchSettleVk1 The linking key for `VALID COMMITMENTS` -> `VALID MATCH SETTLE`
    /// @return instances A set of match linking instances
    function createMatchLinkingInstances(
        MatchProofs calldata matchProofs,
        MatchLinkingProofs calldata matchLinkingProofs,
        ProofLinkingVK memory reblindCommitmentsVk,
        ProofLinkingVK memory commitmentsMatchSettleVk0,
        ProofLinkingVK memory commitmentsMatchSettleVk1
    )
        internal
        pure
        returns (ProofLinkingInstance[] memory instances)
    {
        instances = new ProofLinkingInstance[](NUM_MATCH_LINKING_PROOFS);

        // Party 0: VALID REBLIND -> VALID COMMITMENTS
        instances[0] = ProofLinkingInstance({
            wireComm0: matchProofs.validReblind0.wireComms[0],
            wireComm1: matchProofs.validCommitments0.wireComms[0],
            proof: matchLinkingProofs.validReblindCommitments0,
            vk: reblindCommitmentsVk
        });

        // Party 0: VALID COMMITMENTS -> VALID MATCH SETTLE
        instances[1] = ProofLinkingInstance({
            wireComm0: matchProofs.validCommitments0.wireComms[0],
            wireComm1: matchProofs.validMatchSettle.wireComms[0],
            proof: matchLinkingProofs.validCommitmentsMatchSettle0,
            vk: commitmentsMatchSettleVk0
        });

        // Party 1: VALID REBLIND -> VALID COMMITMENTS
        instances[2] = ProofLinkingInstance({
            wireComm0: matchProofs.validReblind1.wireComms[0],
            wireComm1: matchProofs.validCommitments1.wireComms[0],
            proof: matchLinkingProofs.validReblindCommitments1,
            vk: reblindCommitmentsVk
        });

        // Party 1: VALID COMMITMENTS -> VALID MATCH SETTLE
        instances[3] = ProofLinkingInstance({
            wireComm0: matchProofs.validCommitments1.wireComms[0],
            wireComm1: matchProofs.validMatchSettle.wireComms[0],
            proof: matchLinkingProofs.validCommitmentsMatchSettle1,
            vk: commitmentsMatchSettleVk1
        });
    }

    /// @notice Create a set of match linking instances for an atomic match bundle
    /// @param matchProofs The proofs for the match, including a validity proof and a settlement proof
    /// @param matchLinkingProofs The proof linking arguments for the match
    /// @param reblindCommitmentsVk The linking key for `VALID REBLIND` -> `VALID COMMITMENTS`
    /// @param commitmentsMatchSettleVk The linking key for `VALID COMMITMENTS` -> `VALID MATCH SETTLE ATOMIC`
    /// @return instances A set of match linking instances
    function createAtomicMatchLinkingInstances(
        MatchAtomicProofs calldata matchProofs,
        MatchAtomicLinkingProofs calldata matchLinkingProofs,
        ProofLinkingVK memory reblindCommitmentsVk,
        ProofLinkingVK memory commitmentsMatchSettleVk
    )
        internal
        pure
        returns (ProofLinkingInstance[] memory instances)
    {
        instances = new ProofLinkingInstance[](NUM_ATOMIC_MATCH_LINKING_PROOFS);

        // VALID REBLIND -> VALID COMMITMENTS
        instances[0] = ProofLinkingInstance({
            wireComm0: matchProofs.validReblind.wireComms[0],
            wireComm1: matchProofs.validCommitments.wireComms[0],
            proof: matchLinkingProofs.validReblindCommitments,
            vk: reblindCommitmentsVk
        });

        // VALID COMMITMENTS -> VALID MATCH SETTLE ATOMIC
        instances[1] = ProofLinkingInstance({
            wireComm0: matchProofs.validCommitments.wireComms[0],
            wireComm1: matchProofs.validMatchSettleAtomic.wireComms[0],
            proof: matchLinkingProofs.validCommitmentsMatchSettleAtomic,
            vk: commitmentsMatchSettleVk
        });
    }

    /// @notice Create a set of match linking instances for a malleable match bundle
    /// @param proofs The proofs for the match, including a validity proof and a settlement proof
    /// @param linkingProofs The proof linking arguments for the match
    /// @param reblindCommitmentsVk The linking key for `VALID REBLIND` -> `VALID COMMITMENTS`
    /// @param commitmentsMatchSettleVk The linking key for `VALID COMMITMENTS` -> `VALID MALLEABLE MATCH SETTLE ATOMIC`
    /// @return instances A set of match linking instances
    function createMalleableMatchLinkingInstances(
        MalleableMatchAtomicProofs calldata proofs,
        MatchAtomicLinkingProofs calldata linkingProofs,
        ProofLinkingVK memory reblindCommitmentsVk,
        ProofLinkingVK memory commitmentsMatchSettleVk
    )
        internal
        pure
        returns (ProofLinkingInstance[] memory instances)
    {
        instances = new ProofLinkingInstance[](NUM_MALLEABLE_MATCH_LINKING_PROOFS);

        // VALID REBLIND -> VALID COMMITMENTS
        instances[0] = ProofLinkingInstance({
            wireComm0: proofs.validReblind.wireComms[0],
            wireComm1: proofs.validCommitments.wireComms[0],
            proof: linkingProofs.validReblindCommitments,
            vk: reblindCommitmentsVk
        });

        // VALID COMMITMENTS -> VALID MALLEABLE MATCH SETTLE ATOMIC
        instances[1] = ProofLinkingInstance({
            wireComm0: proofs.validCommitments.wireComms[0],
            wireComm1: proofs.validMalleableMatchSettleAtomic.wireComms[0],
            proof: linkingProofs.validCommitmentsMatchSettleAtomic,
            vk: commitmentsMatchSettleVk
        });
    }
}

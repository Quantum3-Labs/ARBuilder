// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { PlonkProof } from "renegade-lib/verifier/Types.sol";
import {
    ValidWalletCreateStatement,
    ValidWalletUpdateStatement,
    ValidMatchSettleStatement,
    ValidMatchSettleWithCommitmentsStatement,
    ValidMatchSettleAtomicStatement,
    ValidMatchSettleAtomicWithCommitmentsStatement,
    ValidMalleableMatchSettleAtomicStatement,
    ValidOfflineFeeSettlementStatement,
    ValidFeeRedemptionStatement
} from "darkpoolv1-lib/PublicInputs.sol";
import {
    PartyMatchPayload,
    MatchProofs,
    MatchLinkingProofs,
    MatchAtomicProofs,
    MatchAtomicLinkingProofs,
    MalleableMatchAtomicProofs
} from "darkpoolv1-types/Settlement.sol";

/// @title IVerifier
/// @author Renegade Eng
/// @notice Interface for verifying zero-knowledge proofs
interface IVerifier {
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
        returns (bool);

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
        returns (bool);

    /// @notice Verify a match bundle
    /// @param party0MatchPayload The payload for the first party
    /// @param party1MatchPayload The payload for the second party
    /// @param matchSettleStatement The statement of `VALID MATCH SETTLE`
    /// @param proofs The proofs for the match, including two sets of validity proofs and a settlement proof
    /// @param linkingProofs The proof-linking arguments for the match
    /// @return True if the match bundle is valid, false otherwise
    function verifyMatchBundle(
        PartyMatchPayload calldata party0MatchPayload,
        PartyMatchPayload calldata party1MatchPayload,
        ValidMatchSettleStatement calldata matchSettleStatement,
        MatchProofs calldata proofs,
        MatchLinkingProofs calldata linkingProofs
    )
        external
        view
        returns (bool);

    /// @notice Verify a proof of `VALID MATCH SETTLE WITH COMMITMENTS`
    /// @param party0MatchPayload The payload for the first party
    /// @param party1MatchPayload The payload for the second party
    /// @param matchSettleStatement The statement of `VALID MATCH SETTLE WITH COMMITMENTS`
    /// @param proofs The proofs for the match, including two sets of validity proofs and a settlement proof
    /// @param linkingProofs The proof-linking arguments for the match
    /// @return True if the match bundle is valid, false otherwise
    function verifyMatchBundleWithCommitments(
        PartyMatchPayload calldata party0MatchPayload,
        PartyMatchPayload calldata party1MatchPayload,
        ValidMatchSettleWithCommitmentsStatement calldata matchSettleStatement,
        MatchProofs calldata proofs,
        MatchLinkingProofs calldata linkingProofs
    )
        external
        view
        returns (bool);

    /// @notice Verify an atomic match bundle
    /// @param internalPartyPayload The payload for the internal party
    /// @param matchSettleStatement The statement of `VALID MATCH SETTLE ATOMIC`
    /// @param proofs The proofs for the match, including a validity proof and a settlement proof
    /// @param linkingProofs The proof linking arguments for the match
    /// @return True if the atomic match bundle is valid, false otherwise
    function verifyAtomicMatchBundle(
        PartyMatchPayload calldata internalPartyPayload,
        ValidMatchSettleAtomicStatement calldata matchSettleStatement,
        MatchAtomicProofs calldata proofs,
        MatchAtomicLinkingProofs calldata linkingProofs
    )
        external
        view
        returns (bool);

    /// @notice Verify a proof of `VALID MATCH SETTLE ATOMIC WITH COMMITMENTS`
    /// @param internalPartyPayload The payload for the internal party
    /// @param matchSettleStatement The statement of `VALID MATCH SETTLE ATOMIC WITH COMMITMENTS`
    /// @param proofs The proofs for the match, including a validity proof and a settlement proof
    /// @param linkingProofs The proof linking arguments for the match
    /// @return True if the proof is valid, false otherwise
    function verifyAtomicMatchBundleWithCommitments(
        PartyMatchPayload calldata internalPartyPayload,
        ValidMatchSettleAtomicWithCommitmentsStatement calldata matchSettleStatement,
        MatchAtomicProofs calldata proofs,
        MatchAtomicLinkingProofs calldata linkingProofs
    )
        external
        view
        returns (bool);

    /// @notice Verify a proof of `VALID MALLEABLE MATCH SETTLE ATOMIC`
    /// @param internalPartyPayload The payload for the internal party
    /// @param statement The public inputs to the proof
    /// @param proofBundle The proofs for the match, including a validity proof and a settlement proof
    /// @param linkingProofs The proof linking arguments for the match. Note that we use the same type
    /// here as the linking proofs for the standard atomic match bundle, but the circuits they link are
    /// different.
    /// @return True if the proof is valid, false otherwise
    function verifyMalleableMatchBundle(
        PartyMatchPayload calldata internalPartyPayload,
        ValidMalleableMatchSettleAtomicStatement calldata statement,
        MalleableMatchAtomicProofs calldata proofBundle,
        MatchAtomicLinkingProofs calldata linkingProofs
    )
        external
        view
        returns (bool);

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
        returns (bool);

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
        returns (bool);
}

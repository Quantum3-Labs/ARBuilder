// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

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
import { PartyMatchPayload } from "darkpoolv1-types/Settlement.sol";
import { MatchProofs, MatchLinkingProofs } from "darkpoolv1-types/Settlement.sol";
import {
    MatchAtomicProofs, MatchAtomicLinkingProofs, MalleableMatchAtomicProofs
} from "darkpoolv1-types/Settlement.sol";
import { IVKeys } from "darkpoolv1-interfaces/IVKeys.sol";
import { IVerifier } from "darkpoolv1-interfaces/IVerifier.sol";
import { Verifier } from "darkpoolv1-contracts/Verifier.sol";

/// @title Test Verifier Implementation
/// @notice This is a test implementation of the `IVerifier` interface that always returns true
/// @notice even if verification fails
contract TestVerifier is IVerifier {
    Verifier private verifier;

    constructor(IVKeys _vkeys) {
        verifier = new Verifier(_vkeys);
    }

    /// @notice Verify a proof of `VALID WALLET CREATE`
    /// @param statement The public inputs to the proof
    /// @param proof The proof to verify
    /// @return True always, regardless of the proof
    function verifyValidWalletCreate(
        ValidWalletCreateStatement calldata statement,
        PlonkProof calldata proof
    )
        external
        view
        returns (bool)
    {
        verifier.verifyValidWalletCreate(statement, proof);
        return true;
    }

    /// @notice Verify a proof of `VALID WALLET UPDATE`
    /// @param statement The public inputs to the proof
    /// @param proof The proof to verify
    /// @return True always, regardless of the proof
    function verifyValidWalletUpdate(
        ValidWalletUpdateStatement calldata statement,
        PlonkProof calldata proof
    )
        external
        view
        returns (bool)
    {
        verifier.verifyValidWalletUpdate(statement, proof);
        return true;
    }

    /// @notice Verify a match bundle
    /// @param party0MatchPayload The payload for the first party
    /// @param party1MatchPayload The payload for the second party
    /// @param matchSettleStatement The statement of `VALID MATCH SETTLE`
    /// @param proofs The proofs for the match, including two sets of validity proofs and a settlement proof
    /// @return True always, regardless of the proof
    function verifyMatchBundle(
        PartyMatchPayload calldata party0MatchPayload,
        PartyMatchPayload calldata party1MatchPayload,
        ValidMatchSettleStatement calldata matchSettleStatement,
        MatchProofs calldata proofs,
        MatchLinkingProofs calldata linkingProofs
    )
        external
        view
        returns (bool)
    {
        verifier.verifyMatchBundle(party0MatchPayload, party1MatchPayload, matchSettleStatement, proofs, linkingProofs);
        return true;
    }

    /// @notice Verify a proof of `VALID MATCH SETTLE WITH COMMITMENTS`
    /// @param party0MatchPayload The payload for the first party
    /// @param party1MatchPayload The payload for the second party
    /// @param matchSettleStatement The statement of `VALID MATCH SETTLE WITH COMMITMENTS`
    /// @param proofs The proofs for the match, including two sets of validity proofs and a settlement proof
    /// @param linkingProofs The proof linking arguments for the match
    /// @return True always, regardless of the proof
    function verifyMatchBundleWithCommitments(
        PartyMatchPayload calldata party0MatchPayload,
        PartyMatchPayload calldata party1MatchPayload,
        ValidMatchSettleWithCommitmentsStatement calldata matchSettleStatement,
        MatchProofs calldata proofs,
        MatchLinkingProofs calldata linkingProofs
    )
        external
        view
        returns (bool)
    {
        verifier.verifyMatchBundleWithCommitments(
            party0MatchPayload, party1MatchPayload, matchSettleStatement, proofs, linkingProofs
        );
        return true;
    }

    /// @notice Verify an atomic match bundle
    /// @param internalPartyPayload The payload for the internal party
    /// @param matchSettleStatement The statement of `VALID MATCH SETTLE ATOMIC`
    /// @param proofs The proofs for the match, including a validity proof and a settlement proof
    /// @param linkingProofs The proof linking arguments for the match
    /// @return True always, regardless of the proof
    function verifyAtomicMatchBundle(
        PartyMatchPayload calldata internalPartyPayload,
        ValidMatchSettleAtomicStatement calldata matchSettleStatement,
        MatchAtomicProofs calldata proofs,
        MatchAtomicLinkingProofs calldata linkingProofs
    )
        external
        view
        returns (bool)
    {
        verifier.verifyAtomicMatchBundle(internalPartyPayload, matchSettleStatement, proofs, linkingProofs);
        return true;
    }

    /// @notice Verify a proof of `VALID MATCH SETTLE ATOMIC WITH COMMITMENTS`
    /// @param internalPartyPayload The payload for the internal party
    /// @param matchSettleStatement The statement of `VALID MATCH SETTLE ATOMIC WITH COMMITMENTS`
    /// @param proofs The proofs for the match, including a validity proof and a settlement proof
    /// @param linkingProofs The proof linking arguments for the match
    /// @return True always, regardless of the proof
    function verifyAtomicMatchBundleWithCommitments(
        PartyMatchPayload calldata internalPartyPayload,
        ValidMatchSettleAtomicWithCommitmentsStatement calldata matchSettleStatement,
        MatchAtomicProofs calldata proofs,
        MatchAtomicLinkingProofs calldata linkingProofs
    )
        external
        view
        returns (bool)
    {
        verifier.verifyAtomicMatchBundleWithCommitments(
            internalPartyPayload, matchSettleStatement, proofs, linkingProofs
        );
        return true;
    }

    /// @notice Verify a malleable match bundle
    /// @param internalPartyPayload The payload for the internal party
    /// @param matchSettleStatement The statement of `VALID MATCH SETTLE ATOMIC`
    /// @param proofBundle The proofs for the match, including a validity proof and a settlement proof
    /// @param linkingProofs The proof linking arguments for the match
    /// @return True always, regardless of the proof
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
        verifier.verifyMalleableMatchBundle(internalPartyPayload, matchSettleStatement, proofBundle, linkingProofs);
        return true;
    }

    /// @notice Verify a proof of `VALID OFFLINE FEE SETTLEMENT`
    /// @param statement The public inputs to the proof
    /// @param proof The proof to verify
    /// @return True always, regardless of the proof
    function verifyValidOfflineFeeSettlement(
        ValidOfflineFeeSettlementStatement calldata statement,
        PlonkProof calldata proof
    )
        external
        view
        returns (bool)
    {
        verifier.verifyValidOfflineFeeSettlement(statement, proof);
        return true;
    }

    /// @notice Verify a proof of `VALID FEE REDEMPTION`
    /// @param statement The public inputs to the proof
    /// @param proof The proof to verify
    /// @return True always, regardless of the proof
    function verifyValidFeeRedemption(
        ValidFeeRedemptionStatement calldata statement,
        PlonkProof calldata proof
    )
        external
        view
        returns (bool)
    {
        verifier.verifyValidFeeRedemption(statement, proof);
        return true;
    }
}

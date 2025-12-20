// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { FixedPoint } from "renegade-lib/FixedPoint.sol";
import { ValidCommitmentsStatement, ValidReblindStatement } from "darkpoolv1-lib/PublicInputs.sol";
import { PlonkProof, LinkingProof } from "renegade-lib/verifier/Types.sol";

// This file contains types for settlement in the darkpool

// --------------------
// | Settlement Types |
// --------------------

/// @title ExternalMatchResult
/// @notice The result of a match between an internal and external party
struct ExternalMatchResult {
    /// @dev The quote mint of the match
    address quoteMint;
    /// @dev The base mint of the match
    address baseMint;
    /// @dev The amount of the match
    uint256 quoteAmount;
    /// @dev The amount of the match
    uint256 baseAmount;
    /// @dev The direction of the match
    ExternalMatchDirection direction;
}

/// @title BoundedMatchResult
/// @notice An external match result that specifies a range of match sizes rather than
/// @notice an exact base amount.
struct BoundedMatchResult {
    /// @dev The quote mint of the match
    address quoteMint;
    /// @dev The base mint of the match
    address baseMint;
    /// @dev The price at which the match will be settled
    FixedPoint price;
    /// @dev The minimum base amount of the match
    uint256 minBaseAmount;
    /// @dev The maximum base amount of the match
    uint256 maxBaseAmount;
    /// @dev The direction of the match
    ExternalMatchDirection direction;
}

/// @title ExternalMatchDirection
/// @notice The direction of a match between an internal and external party
enum ExternalMatchDirection {
    /// @dev The internal party buys the base and sells the quote
    InternalPartyBuy,
    /// @dev The internal party sells the base and buys the quote
    InternalPartySell
}

/// @title PartyMatchPayload
/// @notice Contains the statement types for a single party's validity proofs in a match
struct PartyMatchPayload {
    /// @dev The statement types for the `VALID COMMITMENTS` proof
    ValidCommitmentsStatement validCommitmentsStatement;
    /// @dev The statement types for the `VALID REBLIND` proof
    ValidReblindStatement validReblindStatement;
}

/// @title MatchProofs
/// @notice Contains the proofs for a match between two parties in the darkpool
/// @dev This contains the validity proofs for the two parties and a proof of
/// @dev `VALID MATCH SETTLE` for settlement
struct MatchProofs {
    /// @dev The first party's proof of `VALID COMMITMENTS`
    PlonkProof validCommitments0;
    /// @dev The first party's proof of `VALID REBLIND`
    PlonkProof validReblind0;
    /// @dev The second party's proof of `VALID COMMITMENTS`
    PlonkProof validCommitments1;
    /// @dev The second party's proof of `VALID REBLIND`
    PlonkProof validReblind1;
    /// @dev The proof of `VALID MATCH SETTLE`
    PlonkProof validMatchSettle;
}

/// @title MatchLinkingProofs
/// @notice Contains the proof linking arguments for a match
/// @dev This contains four proofs: two linking the internal party's `VALID REBLIND`
/// @dev to their `VALID COMMITMENTS`, and two linking the internal party's
/// @dev `VALID COMMITMENTS` to the proof of `VALID MATCH SETTLE`
struct MatchLinkingProofs {
    /// @dev The proof of linked inputs between PARTY 0 VALID REBLIND <-> PARTY 0 VALID COMMITMENTS
    LinkingProof validReblindCommitments0;
    /// @dev The proof of linked inputs between PARTY 0 VALID COMMITMENTS <-> VALID MATCH SETTLE
    LinkingProof validCommitmentsMatchSettle0;
    /// @dev The proof of linked inputs between PARTY 1 VALID REBLIND <-> PARTY 1 VALID COMMITMENTS
    LinkingProof validReblindCommitments1;
    /// @dev The proof of linked inputs between PARTY 1 VALID COMMITMENTS <-> VALID MATCH SETTLE
    LinkingProof validCommitmentsMatchSettle1;
}

/// @title MatchAtomicProofs
/// @notice Contains the proofs for a match between two parties in the darkpool
/// @dev This contains the validity proofs for the internal party and a proof of
/// @dev `VALID MATCH SETTLE ATOMIC` for settlement
struct MatchAtomicProofs {
    /// @dev The proof of `VALID COMMITMENTS` for the internal party
    PlonkProof validCommitments;
    /// @dev The proof of `VALID REBLIND` for the internal party
    PlonkProof validReblind;
    /// @dev The proof of `VALID MATCH SETTLE ATOMIC`
    PlonkProof validMatchSettleAtomic;
}

/// @title MatchAtomicLinkingProofs
/// @notice Contains the proof linking arguments for a match
/// @dev This contains one proof that links the internal party's `VALID REBLIND`
/// @dev to their `VALID COMMITMENTS`, and another that links the internal party's
/// @dev `VALID COMMITMENTS` to the proof of `VALID MATCH SETTLE ATOMIC`
struct MatchAtomicLinkingProofs {
    /// @dev The proof of linked inputs between PARTY 0 VALID REBLIND <-> PARTY 0 VALID COMMITMENTS
    LinkingProof validReblindCommitments;
    /// @dev The proof of linked inputs between PARTY 0 VALID COMMITMENTS <-> VALID MATCH SETTLE ATOMIC
    LinkingProof validCommitmentsMatchSettleAtomic;
}

/// @title MalleableMatchAtomicProofs
/// @notice Contains the proofs for a match between two parties in the darkpool
/// @dev This contains the validity proofs for the internal party and a proof of
/// @dev `VALID MALLEABLE MATCH SETTLE ATOMIC` for settlement
struct MalleableMatchAtomicProofs {
    /// @dev The proof of `VALID COMMITMENTS` for the internal party
    PlonkProof validCommitments;
    /// @dev The proof of `VALID REBLIND` for the internal party
    PlonkProof validReblind;
    /// @dev The proof of `VALID MALLEABLE MATCH SETTLE ATOMIC`
    PlonkProof validMalleableMatchSettleAtomic;
}

/// @notice A set of indices into a settlement party's wallet for the receive balance
struct OrderSettlementIndices {
    /// @dev The index of the balance holding the mint which teh wallet will
    /// @dev sell in a match
    uint256 balanceSend;
    /// @dev The index of the balance holding the mint which the wallet will
    /// @dev buy in a match
    uint256 balanceReceive;
    /// @dev the index of the order that is matched in the wallet
    uint256 order;
}

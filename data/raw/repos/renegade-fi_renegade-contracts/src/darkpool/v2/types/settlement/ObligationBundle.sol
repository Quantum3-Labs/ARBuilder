/// SPDX-License-Identifier: Apache
pragma solidity ^0.8.24;

import { PartyId } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";

import { IntentAndBalancePrivateSettlementStatement } from "darkpoolv2-lib/public_inputs/Settlement.sol";
import { PlonkProof } from "renegade-lib/verifier/Types.sol";

// --------------------
// | Obligation Types |
// --------------------

/// @notice The settlement obligation bundle for both users in a trade
/// @dev This data represents the following based on the obligation type:
/// 1. *Public Obligation*: A plaintext settlement obligation for each party in the trade
/// 2. *Private Obligation* A proof attesting to the validity of the _private_ settlement obligations in the trade.
/// @dev In essence, this type captures the result of a trade and hides it behind a ZKP in the case of a private
/// obligation.
struct ObligationBundle {
    /// @dev The type of obligation
    ObligationType obligationType;
    /// @dev The data validating the obligation
    bytes data;
}

/// @notice The types of obligations possible in the darkpool
enum ObligationType {
    PUBLIC,
    PRIVATE
}

/// @notice The data for a private obligation
struct PrivateObligationBundle {
    /// @dev The statement for the proof of intent and balance private settlement
    IntentAndBalancePrivateSettlementStatement statement;
    /// @dev The proof of the obligation
    PlonkProof proof;
}

/// @title Obligation Library
/// @author Renegade Eng
/// @notice Library for decoding and hashing obligation data
library ObligationLib {
    /// @notice The error type emitted when an obligation type check fails
    error InvalidObligationType();

    /// @notice Decode both public obligations for a public obligation bundle
    /// @param bundle The obligation bundle to decode
    /// @return obligation0 The decoded obligation for the first party
    /// @return obligation1 The decoded obligation for the second party
    function decodePublicObligations(ObligationBundle calldata bundle)
        internal
        pure
        returns (SettlementObligation memory obligation0, SettlementObligation memory obligation1)
    {
        require(bundle.obligationType == ObligationType.PUBLIC, InvalidObligationType());
        (obligation0, obligation1) = abi.decode(bundle.data, (SettlementObligation, SettlementObligation));
    }

    /// @notice Decode both public obligations from a memory-allocated bundle
    /// @param bundle The obligation bundle to decode
    /// @return obligation0 The decoded obligation for the first party
    /// @return obligation1 The decoded obligation for the second party
    function decodePublicObligationsMemory(ObligationBundle memory bundle)
        internal
        pure
        returns (SettlementObligation memory obligation0, SettlementObligation memory obligation1)
    {
        require(bundle.obligationType == ObligationType.PUBLIC, InvalidObligationType());
        (obligation0, obligation1) = abi.decode(bundle.data, (SettlementObligation, SettlementObligation));
    }

    /// @notice Decode a public obligation
    /// @param bundle The obligation bundle to decode
    /// @param partyId The party ID to decode the obligation for
    /// @return obligation The decoded obligation for the given party ID
    function decodePublicObligation(
        ObligationBundle calldata bundle,
        PartyId partyId
    )
        internal
        pure
        returns (SettlementObligation memory obligation)
    {
        require(bundle.obligationType == ObligationType.PUBLIC, InvalidObligationType());
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1) =
            abi.decode(bundle.data, (SettlementObligation, SettlementObligation));
        if (partyId == PartyId.PARTY_0) {
            obligation = obligation0;
        } else if (partyId == PartyId.PARTY_1) {
            obligation = obligation1;
        } else {
            revert InvalidObligationType();
        }
    }

    /// @notice Decode a public obligation from a memory-allocated bundle
    /// @param bundle The obligation bundle to decode
    /// @param partyId The party ID to decode the obligation for
    /// @return obligation The decoded obligation for the given party ID
    function decodePublicObligationMemory(
        ObligationBundle memory bundle,
        PartyId partyId
    )
        internal
        pure
        returns (SettlementObligation memory obligation)
    {
        require(bundle.obligationType == ObligationType.PUBLIC, InvalidObligationType());
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1) =
            abi.decode(bundle.data, (SettlementObligation, SettlementObligation));
        if (partyId == PartyId.PARTY_0) {
            obligation = obligation0;
        } else if (partyId == PartyId.PARTY_1) {
            obligation = obligation1;
        } else {
            revert InvalidObligationType();
        }
    }

    /// @notice Decode a private obligation
    /// @param bundle The obligation bundle to decode
    /// @return obligation The decoded obligation
    function decodePrivateObligation(ObligationBundle calldata bundle)
        internal
        pure
        returns (PrivateObligationBundle memory obligation)
    {
        require(bundle.obligationType == ObligationType.PRIVATE, InvalidObligationType());
        obligation = abi.decode(bundle.data, (PrivateObligationBundle));
    }
}

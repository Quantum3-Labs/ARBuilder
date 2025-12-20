// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {
    ValidMatchSettleAtomicStatement, ValidMalleableMatchSettleAtomicStatement
} from "darkpoolv1-lib/PublicInputs.sol";

import {
    PartyMatchPayload,
    MatchAtomicProofs,
    MalleableMatchAtomicProofs,
    MatchAtomicLinkingProofs
} from "darkpoolv1-types/Settlement.sol";

/// @title IGasSponsor
/// @author Renegade Eng
/// @notice Interface for the GasSponsor contract, exposing only the sponsorship methods
interface IGasSponsor {
    /// @notice Initializes the gas sponsor contract with the given darkpool address and auth pubkey
    /// @param initialOwner The initial owner of the gas sponsor contract
    /// @param _darkpoolAddress The address of the darkpool proxy contract
    /// @param _authAddress The public key used to authenticate gas sponsorship
    function initialize(address initialOwner, address _darkpoolAddress, address _authAddress) external;

    /// @notice Sponsor the gas costs of an atomic match settlement
    /// @param receiver The address to receive the tokens
    /// @param internalPartyMatchPayload The internal party match payload
    /// @param validMatchSettleAtomicStatement The valid match settle atomic statement
    /// @param matchProofs The match proofs
    /// @param matchLinkingProofs The match linking proofs
    /// @param refundAddress The address to refund gas costs to
    /// @param refundNativeEth Whether to refund gas costs in native ETH
    /// @param refundAmount The amount to refund
    /// @param nonce A unique nonce for this sponsorship
    /// @param signature The signature authorizing the sponsorship
    /// @return The amount received by the external party
    function sponsorAtomicMatchSettle(
        address receiver,
        PartyMatchPayload calldata internalPartyMatchPayload,
        ValidMatchSettleAtomicStatement calldata validMatchSettleAtomicStatement,
        MatchAtomicProofs calldata matchProofs,
        MatchAtomicLinkingProofs calldata matchLinkingProofs,
        address refundAddress,
        bool refundNativeEth,
        uint256 refundAmount,
        uint256 nonce,
        bytes calldata signature
    )
        external
        payable
        returns (uint256);

    /// @notice Sponsors a malleable atomic match settlement
    /// @param quoteAmount The quote amount for the malleable match
    /// @param baseAmount The base amount for the malleable match
    /// @param receiver The address to receive the tokens
    /// @param internalPartyMatchPayload The internal party match payload
    /// @param malleableMatchSettleStatement The malleable match settle statement
    /// @param matchProofs The match proofs
    /// @param matchLinkingProofs The match linking proofs
    /// @param refundAddress The address to refund gas costs to
    /// @param refundNativeEth Whether to refund gas costs in native ETH
    /// @param refundAmount The amount to refund
    /// @param nonce A unique nonce for this sponsorship
    /// @param signature The signature authorizing the sponsorship
    /// @return The amount received by the external party
    function sponsorMalleableAtomicMatchSettle(
        uint256 quoteAmount,
        uint256 baseAmount,
        address receiver,
        PartyMatchPayload calldata internalPartyMatchPayload,
        ValidMalleableMatchSettleAtomicStatement calldata malleableMatchSettleStatement,
        MalleableMatchAtomicProofs calldata matchProofs,
        MatchAtomicLinkingProofs calldata matchLinkingProofs,
        address refundAddress,
        bool refundNativeEth,
        uint256 refundAmount,
        uint256 nonce,
        bytes calldata signature
    )
        external
        payable
        returns (uint256);
}

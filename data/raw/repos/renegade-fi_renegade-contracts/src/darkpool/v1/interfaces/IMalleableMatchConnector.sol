// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {
    PartyMatchPayload, MalleableMatchAtomicProofs, MatchAtomicLinkingProofs
} from "darkpoolv1-types/Settlement.sol";

import { ValidMalleableMatchSettleAtomicStatement } from "darkpoolv1-lib/PublicInputs.sol";

/// @title IMalleableMatchConnector
/// @author Renegade Eng
/// @notice Interface for the MalleableMatchConnector contract
interface IMalleableMatchConnector {
    /// @notice Sets the base and quote amounts for the malleable match based on the input amount parameter, then
    /// forwards the remaining calldata to the gas sponsor contract
    /// @param inputAmount The input amount for the malleable match
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
    function executeMalleableAtomicMatchWithInput(
        uint256 inputAmount,
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

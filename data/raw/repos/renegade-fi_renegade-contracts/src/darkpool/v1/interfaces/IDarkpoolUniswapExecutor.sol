// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import { SignedOrder } from "uniswapx/base/ReactorStructs.sol";
import { IReactorCallback } from "uniswapx/interfaces/IReactorCallback.sol";
import {
    PartyMatchPayload,
    MatchAtomicProofs,
    MatchAtomicLinkingProofs,
    MalleableMatchAtomicProofs
} from "darkpoolv1-types/Settlement.sol";
import {
    ValidMatchSettleAtomicStatement, ValidMalleableMatchSettleAtomicStatement
} from "darkpoolv1-lib/PublicInputs.sol";

/// @title IDarkpoolUniswapExecutor
/// @author Renegade Eng
/// @notice Interface for the DarkpoolUniswapExecutor contract
interface IDarkpoolUniswapExecutor is IReactorCallback {
    /// @notice Returns the address of the current owner
    /// @return The address of the current owner
    function owner() external view returns (address);

    /// @notice Initializes the DarkpoolUniswapExecutor
    /// @param initialOwner The address that will own the contract
    /// @param darkpool_ The darkpool address
    /// @param uniswapXReactor_ The UniswapX reactor address
    function initialize(address initialOwner, address darkpool_, address uniswapXReactor_) external;

    /// @notice Execute a UniswapX order with atomic match settlement
    /// @param order The signed order to execute
    /// @param internalPartyPayload The validity proofs for the internal party
    /// @param matchSettleStatement The statement (public inputs) of VALID MATCH SETTLE
    /// @param proofs The proofs for the match
    /// @param linkingProofs The proof-linking arguments for the match
    function executeAtomicMatchSettle(
        SignedOrder calldata order,
        PartyMatchPayload calldata internalPartyPayload,
        ValidMatchSettleAtomicStatement calldata matchSettleStatement,
        MatchAtomicProofs calldata proofs,
        MatchAtomicLinkingProofs calldata linkingProofs
    )
        external
        payable;

    /// @notice Execute a UniswapX order with malleable atomic match settlement
    /// @param order The signed order to execute
    /// @param quoteAmount The quote amount of the match, resolving in between the bounds
    /// @param baseAmount The base amount of the match, resolving in between the bounds
    /// @param internalPartyPayload The validity proofs for the internal party
    /// @param matchSettleStatement The statement (public inputs) of VALID MATCH SETTLE
    /// @param proofs The proofs for the match
    /// @param linkingProofs The proof-linking arguments for the match
    function executeMalleableAtomicMatchSettle(
        SignedOrder calldata order,
        uint256 quoteAmount,
        uint256 baseAmount,
        PartyMatchPayload calldata internalPartyPayload,
        ValidMalleableMatchSettleAtomicStatement calldata matchSettleStatement,
        MalleableMatchAtomicProofs calldata proofs,
        MatchAtomicLinkingProofs calldata linkingProofs
    )
        external
        payable;

    /// @notice Add an address to the set of allowed solvers
    /// @param solver The solver address to add
    function whitelistSolver(address solver) external;

    /// @notice Remove an address from the set of allowed solvers
    /// @param solver The solver address to remove
    function removeWhitelistedSolver(address solver) external;

    /// @notice Check if an address is an allowed solver
    /// @param solver The address to check
    /// @return Whether the address is an allowed solver
    function isWhitelistedSolver(address solver) external view returns (bool);
}

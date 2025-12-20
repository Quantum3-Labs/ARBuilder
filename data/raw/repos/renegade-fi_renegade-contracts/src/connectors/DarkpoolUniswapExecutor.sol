// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import { IReactorCallback } from "uniswapx/interfaces/IReactorCallback.sol";
import { ResolvedOrder } from "uniswapx/base/ReactorStructs.sol";

import { Initializable } from "oz-contracts/proxy/utils/Initializable.sol";
import { Ownable } from "oz-contracts/access/Ownable.sol";
import { Ownable2Step } from "oz-contracts/access/Ownable2Step.sol";
import { AccessControl } from "oz-contracts/access/AccessControl.sol";
import { Pausable } from "oz-contracts/utils/Pausable.sol";
import { Address } from "oz-contracts/utils/Address.sol";
import { IDarkpool } from "darkpoolv1-interfaces/IDarkpool.sol";
import { IReactor } from "uniswapx/interfaces/IReactor.sol";
import { SignedOrder } from "uniswapx/base/ReactorStructs.sol";
import {
    PartyMatchPayload,
    MatchAtomicProofs,
    MatchAtomicLinkingProofs,
    MalleableMatchAtomicProofs
} from "darkpoolv1-types/Settlement.sol";
import {
    ValidMatchSettleAtomicStatement, ValidMalleableMatchSettleAtomicStatement
} from "darkpoolv1-lib/PublicInputs.sol";

import { SafeTransferLib } from "solmate/src/utils/SafeTransferLib.sol";
import { ERC20 } from "solmate/src/tokens/ERC20.sol";

/**
 * @title DarkpoolUniswapExecutor
 * @author Renegade Eng
 * @notice A wrapper contract that acts as a UniswapX executor for the darkpool
 * @dev This contract implements IReactorCallback to handle order execution callbacks from UniswapX
 * and routes them to the darkpool for settlement
 */
contract DarkpoolUniswapExecutor is IReactorCallback, Initializable, Ownable2Step, Pausable, AccessControl {
    using SafeTransferLib for ERC20;

    // --- State Variables --- //

    /// @notice The darkpool contract
    IDarkpool public darkpool;
    /// @notice The UniswapX reactor contract
    IReactor public uniswapXReactor;
    /// @notice Role identifier for whitelisted solvers
    bytes32 public constant SOLVER_ROLE = keccak256("SOLVER_ROLE");

    // --- Errors --- //

    /// @notice Thrown when the caller is not whitelisted
    error UnauthorizedCaller();

    // --- Modifiers --- //

    /// @notice Ensures the caller is a whitelisted solver
    modifier onlySolver() {
        _checkRole(SOLVER_ROLE);
        _;
    }

    // --- Initializer --- //

    /// @notice Constructor
    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() Ownable(msg.sender) {
        _disableInitializers();
    }

    /// @notice Initializes the contract
    /// @param initialOwner The initial owner of the contract
    /// @param darkpool_ The darkpool address
    /// @param uniswapXReactor_ The UniswapX reactor address
    function initialize(address initialOwner, address darkpool_, address uniswapXReactor_) public initializer {
        _transferOwnership(initialOwner);
        darkpool = IDarkpool(darkpool_);
        uniswapXReactor = IReactor(uniswapXReactor_);
    }

    // --- Order Execution --- //

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
        payable
        whenNotPaused
        onlySolver
    {
        // Encode callback data for processAtomicMatchSettle
        bytes memory callbackData = abi.encodeWithSelector(
            darkpool.processAtomicMatchSettle.selector,
            address(this), // executor is the receiver
            internalPartyPayload,
            matchSettleStatement,
            proofs,
            linkingProofs
        );

        // Call the reactor's executeWithCallback, which will call back to our reactorCallback
        uniswapXReactor.executeWithCallback{ value: msg.value }(order, callbackData);
    }

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
        payable
        whenNotPaused
        onlySolver
    {
        // Encode callback data for processMalleableAtomicMatchSettle
        bytes memory callbackData = abi.encodeWithSelector(
            darkpool.processMalleableAtomicMatchSettle.selector,
            quoteAmount,
            baseAmount,
            address(this), // executor is the receiver
            internalPartyPayload,
            matchSettleStatement,
            proofs,
            linkingProofs
        );

        // Call the reactor's executeWithCallback, which will call back to our reactorCallback
        uniswapXReactor.executeWithCallback{ value: msg.value }(order, callbackData);
    }

    // --- Admin Functions --- //

    /// @notice Add an address to the set of allowed solvers
    /// @param solver The solver address to add
    function whitelistSolver(address solver) public onlyOwner {
        _grantRole(SOLVER_ROLE, solver);
    }

    /// @notice Remove an address from the set of allowed solvers
    /// @param solver The solver address to remove
    function removeWhitelistedSolver(address solver) public onlyOwner {
        _revokeRole(SOLVER_ROLE, solver);
    }

    /// @notice Check if an address is an allowed solver
    /// @param solver The address to check
    /// @return Whether the address is an allowed solver
    function isWhitelistedSolver(address solver) public view returns (bool) {
        return hasRole(SOLVER_ROLE, solver);
    }

    // --- Callback Logic --- //

    /// @notice Called by the reactor during the execution of an order
    /// @param resolvedOrders The resolved orders
    /// @param callbackData The callbackData specified for an order execution
    /// @dev Must have approved each token and amount in outputs to the msg.sender
    /// @dev For now we assume that there is only one resolved order with a single output token
    function reactorCallback(
        ResolvedOrder[] calldata resolvedOrders,
        bytes calldata callbackData
    )
        external
        override
        whenNotPaused
    {
        // Only the reactor may call this function
        if (msg.sender != address(uniswapXReactor)) revert UnauthorizedCaller();

        // Any ether balance present in the contract is meant as input to the darkpool trade
        // TODO: Properly account for the ether value of the transaction
        uint256 value = address(this).balance;

        // Approve the darkpool to spend the input token
        ResolvedOrder memory resolvedOrder = resolvedOrders[0];
        ERC20 sendToken = resolvedOrder.input.token;
        uint256 balance = sendToken.balanceOf(address(this));
        sendToken.safeApprove(address(darkpool), balance);

        // Forward the call directly to the darkpool
        // The callback data already contains the selector and all properly encoded parameters
        // This will automatically bubble up any revert reason from the darkpool
        Address.functionCallWithValue(address(darkpool), callbackData, value);

        // Finally, approve the reactor to transfer the output tokens
        ERC20 receiveToken = ERC20(resolvedOrder.outputs[0].token);
        uint256 receiveAmount = resolvedOrder.outputs[0].amount;
        receiveToken.safeApprove(address(uniswapXReactor), receiveAmount);
    }
}

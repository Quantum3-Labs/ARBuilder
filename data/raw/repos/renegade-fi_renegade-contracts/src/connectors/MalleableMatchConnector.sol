// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Initializable } from "oz-contracts/proxy/utils/Initializable.sol";
import { IGasSponsor } from "darkpoolv1-interfaces/IGasSponsor.sol";
import { IERC20 } from "oz-contracts/token/ERC20/IERC20.sol";
import { SafeERC20 } from "oz-contracts/token/ERC20/utils/SafeERC20.sol";

import {
    PartyMatchPayload,
    ExternalMatchDirection,
    MalleableMatchAtomicProofs,
    MatchAtomicLinkingProofs
} from "darkpoolv1-types/Settlement.sol";

import { ValidMalleableMatchSettleAtomicStatement } from "darkpoolv1-lib/PublicInputs.sol";
import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { DarkpoolConstants } from "darkpoolv1-lib/Constants.sol";

/// @title MalleableMatchConnector
/// @author Renegade Eng
/// @notice This contract is a connector for the malleable match settlement.
contract MalleableMatchConnector is Initializable {
    using FixedPointLib for FixedPoint;

    /// @notice The gas sponsor contract
    IGasSponsor public gasSponsor;

    /// @notice Constructor that disables initializers for the implementation contract
    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    /**
     * @notice Initializes the malleable match connector with the given gas sponsor address
     * @param _gasSponsor The address of the gas sponsor contract
     */
    function initialize(address _gasSponsor) public initializer {
        gasSponsor = IGasSponsor(_gasSponsor);
    }

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
        returns (uint256)
    {
        // Calculate the amounts based on direction
        address resolvedReceiver = receiver == address(0) ? msg.sender : receiver;
        ExternalMatchDirection direction = malleableMatchSettleStatement.matchResult.direction;
        FixedPoint memory price = malleableMatchSettleStatement.matchResult.price;

        uint256 quoteAmount;
        uint256 baseAmount;
        if (direction == ExternalMatchDirection.InternalPartyBuy) {
            // The external (calling) party inputs the base to sell for the quote
            baseAmount = inputAmount;
            quoteAmount = price.unsafeFixedPointMul(inputAmount);
        } else {
            // The external (calling) party inputs the quote to buy the base
            baseAmount = FixedPointLib.divIntegerByFixedPoint(inputAmount, price);
            quoteAmount = inputAmount;
        }

        // Take custody of tokens from the caller and approve gas sponsor
        _custodyTokens(quoteAmount, baseAmount, malleableMatchSettleStatement);

        // Call the gas sponsor contract
        return gasSponsor.sponsorMalleableAtomicMatchSettle{ value: msg.value }(
            quoteAmount,
            baseAmount,
            resolvedReceiver,
            internalPartyMatchPayload,
            malleableMatchSettleStatement,
            matchProofs,
            matchLinkingProofs,
            refundAddress,
            refundNativeEth,
            refundAmount,
            nonce,
            signature
        );
    }

    /// @notice Take custody of tokens from the caller and approve gas sponsor
    /// @param quoteAmount The quote amount
    /// @param baseAmount The base amount
    /// @param statement The malleable match settle statement
    function _custodyTokens(
        uint256 quoteAmount,
        uint256 baseAmount,
        ValidMalleableMatchSettleAtomicStatement calldata statement
    )
        internal
    {
        // Determine which token the external party is selling
        address sellToken;
        uint256 sellAmount;

        if (statement.matchResult.direction == ExternalMatchDirection.InternalPartyBuy) {
            // External party sells base
            sellToken = statement.matchResult.baseMint;
            sellAmount = baseAmount;
        } else {
            // External party sells quote
            sellToken = statement.matchResult.quoteMint;
            sellAmount = quoteAmount;
        }

        // Only handle ERC20 transfers (native ETH is passed via msg.value)
        if (!DarkpoolConstants.isNativeToken(sellToken)) {
            IERC20 token = IERC20(sellToken);
            // Pull tokens from the caller, then increase the allowance for the gas sponsor
            SafeERC20.safeTransferFrom(token, msg.sender, address(this), sellAmount);
            SafeERC20.safeIncreaseAllowance(token, address(gasSponsor), sellAmount);
        }
    }
}

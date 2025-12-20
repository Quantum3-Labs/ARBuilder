// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { ExternalTransfer, DepositWitness } from "./Transfers.sol";
import { EncryptionKey } from "renegade-lib/Ciphertext.sol";
import { OrderSettlementIndices, ExternalMatchResult, BoundedMatchResult } from "./Settlement.sol";
import { FeeTake, FeeTakeRate } from "./Fees.sol";
import { ExternalMatchDirection } from "./Settlement.sol";
import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";
import { FixedPointLib } from "renegade-lib/FixedPoint.sol";

/// @dev The type hash for the DepositWitness struct
// solhint-disable-next-line gas-small-strings
bytes32 constant DEPOSIT_WITNESS_TYPEHASH = keccak256("DepositWitness(uint256[4] pkRoot)");
/// @dev The type string for the DepositWitness struct
/// @dev We must include the `TokenPermission` type encoding as well as this is concatenated with
/// @dev the `PermitWitnessTransferFrom` type encoding stub of the form:
/// @dev `PermitWitnessTransferFrom(TokenPermissions permitted,address spender,uint256 nonce,uint256 deadline,`
/// @dev So we must prepare our type string to concatenate to the entire type encoding
/// @dev See:
/// https://github.com/Uniswap/permit2/blob/cc56ad0f3439c502c246fc5cfcc3db92bb8b7219/src/libraries/PermitHash.sol#L31-L32
// solhint-disable-next-line gas-small-strings
string constant DEPOSIT_WITNESS_TYPE_STRING =
    "DepositWitness witness)DepositWitness(uint256[4] pkRoot)TokenPermissions(address token,uint256 amount)";

/// @title TypesLib
/// @author Renegade Eng
/// @notice A library that allows us to define function on types in the darkpool
library TypesLib {
    /// @notice Error thrown when base amount is out of bounds
    error BaseAmountOutOfBounds();
    /// @notice Error thrown when quote amount is out of bounds
    error QuoteAmountOutOfBounds();
    /// @notice Error thrown when base or quote amount is zero
    error ZeroAmount();

    // --- External Transfers --- //

    /// @notice Checks if an ExternalTransfer has zero values
    /// @param transfer The ExternalTransfer to check
    /// @return True if the amount is zero
    function isZero(ExternalTransfer memory transfer) public pure returns (bool) {
        return transfer.amount == 0;
    }

    /// @notice Computes the EIP-712 hash of a DepositWitness
    /// @param witness The DepositWitness to hash
    /// @return The EIP-712 hash of the DepositWitness
    function hashWitness(DepositWitness memory witness) public pure returns (bytes32) {
        // Hash the struct data according to EIP-712
        bytes32 pkRootHash = EfficientHashLib.hash(abi.encode(witness.pkRoot));
        return EfficientHashLib.hash(abi.encode(DEPOSIT_WITNESS_TYPEHASH, pkRootHash));
    }

    // --- Order Settlement Indices --- //

    /// @notice Return whether two sets of indices are equal
    /// @param a The first set of indices
    /// @param b The second set of indices
    /// @return True if the indices are equal, false otherwise
    function indicesEqual(
        OrderSettlementIndices memory a,
        OrderSettlementIndices memory b
    )
        public
        pure
        returns (bool)
    {
        return a.balanceSend == b.balanceSend && a.balanceReceive == b.balanceReceive && a.order == b.order;
    }

    // --- Match Settlement --- //

    /// @notice Return the sell mint and amount for the external party
    /// @param matchResult The match result to return the sell mint and amount for
    /// @return The sell mint
    /// @return The sell amount
    function externalPartySellMintAmount(ExternalMatchResult memory matchResult)
        public
        pure
        returns (address, uint256)
    {
        if (matchResult.direction == ExternalMatchDirection.InternalPartyBuy) {
            return (matchResult.baseMint, matchResult.baseAmount);
        } else {
            return (matchResult.quoteMint, matchResult.quoteAmount);
        }
    }

    /// @notice Return the buy mint and amount for the external party
    /// @param matchResult The match result to return the buy mint and amount for
    /// @return The buy mint
    /// @return The buy amount
    function externalPartyBuyMintAmount(ExternalMatchResult memory matchResult)
        public
        pure
        returns (address, uint256)
    {
        if (matchResult.direction == ExternalMatchDirection.InternalPartyBuy) {
            return (matchResult.quoteMint, matchResult.quoteAmount);
        } else {
            return (matchResult.baseMint, matchResult.baseAmount);
        }
    }

    // --- Bounded Match Result --- //

    /// @notice Validate the base amount for a match
    /// @dev This simply validates that the base amount lies in the range constructed
    /// by the relayer. This range is validated in-circuit to be well capitalized.
    /// @param boundedMatchResult The bounded match result to validate against
    /// @param baseAmount The base amount to validate
    function validateBaseAmount(BoundedMatchResult memory boundedMatchResult, uint256 baseAmount) public pure {
        bool amountTooLow = baseAmount < boundedMatchResult.minBaseAmount;
        bool amountTooHigh = baseAmount > boundedMatchResult.maxBaseAmount;
        if (amountTooLow || amountTooHigh) {
            revert BaseAmountOutOfBounds();
        }
    }

    /// @notice Validate the quote amount for a match
    /// @dev We allow an external user to specify a quote amount, but we need to
    /// ensure that they have not given themselves an invalid amount or price
    /// improvement at the expense of the internal party.
    ///
    /// This involves two checks:
    /// 1. The quote amount must be within the range implied by the base amount
    ///    range. Let `min_quote = floor(min_base * price)` and `max_quote =
    ///    floor(max_base * price)`. The quote amount must lie in the range
    ///    `[min_quote, max_quote]`.
    /// 2. The quote amount must imply a price that improves upon the reference
    ///    price in the match result *for the internal party*. Let
    ///    `reference_quote = floor(base_amount * price)`. Then for an external
    ///    sell order, we assert `quote_amount <= reference_quote`; i.e. the
    ///    external party sells at a lower price. For an external buy order, we
    ///    assert `quote_amount >= reference_quote`; i.e. the external party
    ///    buys at a higher price.
    ///
    /// Note that we can combine these two checks by taking the intersection of
    /// their respective intervals. For an external party buy order, this is the
    /// interval:
    ///   [ref_quote, inf) ∩ [min_quote, max_quote] = [ref_quote, max_quote]
    ///
    /// For an external party sell order, this is the interval:
    ///   [0, ref_quote] ∩ [min_quote, max_quote] = [min_quote, ref_quote]
    ///
    /// So we check that the quote lies in the intersection interval.
    ///
    /// SAFETY: All values below are constrained to be within 100 bits, and the
    /// price is constrained to be within 127 bits, so wraparound is impossible
    /// @param boundedMatchResult The bounded match result to validate against
    /// @param quoteAmount The quote amount to validate
    /// @param baseAmount The base amount for the match
    function validateQuoteAmount(
        BoundedMatchResult memory boundedMatchResult,
        uint256 quoteAmount,
        uint256 baseAmount
    )
        public
        pure
    {
        // Compute the quote amount bounds
        uint256 minQuote = FixedPointLib.unsafeFixedPointMul(boundedMatchResult.price, boundedMatchResult.minBaseAmount);
        uint256 maxQuote = FixedPointLib.unsafeFixedPointMul(boundedMatchResult.price, boundedMatchResult.maxBaseAmount);
        uint256 refQuote = FixedPointLib.unsafeFixedPointMul(boundedMatchResult.price, baseAmount);

        // Check that the quote amount lies in the intersection interval
        uint256 rangeMin;
        uint256 rangeMax;
        bool isSell = boundedMatchResult.direction == ExternalMatchDirection.InternalPartyBuy;
        if (isSell) {
            rangeMin = minQuote;
            rangeMax = refQuote;
        } else {
            rangeMin = refQuote;
            rangeMax = maxQuote;
        }

        bool quoteTooLow = quoteAmount < rangeMin;
        bool quoteTooHigh = quoteAmount > rangeMax;
        if (quoteTooLow || quoteTooHigh) {
            revert QuoteAmountOutOfBounds();
        }
    }

    /// @notice Validate the base and quote amount for a match
    /// @param boundedMatchResult The bounded match result to validate against
    /// @param quoteAmount The quote amount to validate
    /// @param baseAmount The base amount to validate
    function validateAmounts(
        BoundedMatchResult memory boundedMatchResult,
        uint256 quoteAmount,
        uint256 baseAmount
    )
        public
        pure
    {
        if (quoteAmount == 0 || baseAmount == 0) {
            revert ZeroAmount();
        }

        validateBaseAmount(boundedMatchResult, baseAmount);
        validateQuoteAmount(boundedMatchResult, quoteAmount, baseAmount);
    }

    /// @notice Build an `ExternalMatchResult` from a `BoundedMatchResult`
    /// @param quoteAmount The quote amount of the match
    /// @param baseAmount The base amount of the match, resolving in between the bounds
    /// @param boundedMatchResult The `BoundedMatchResult` to build the `ExternalMatchResult` from
    /// @return The `ExternalMatchResult`
    function buildExternalMatchResult(
        uint256 quoteAmount,
        uint256 baseAmount,
        BoundedMatchResult memory boundedMatchResult
    )
        public
        pure
        returns (ExternalMatchResult memory)
    {
        // Validate the amounts then build the match result
        validateAmounts(boundedMatchResult, quoteAmount, baseAmount);
        return ExternalMatchResult({
            quoteMint: boundedMatchResult.quoteMint,
            baseMint: boundedMatchResult.baseMint,
            quoteAmount: quoteAmount,
            baseAmount: baseAmount,
            direction: boundedMatchResult.direction
        });
    }

    // --- Fees --- //

    /// @notice Return the total fees due on a fee take
    /// @param feeTake The fee take to compute the total fees for
    /// @return The total fees due
    function total(FeeTake memory feeTake) public pure returns (uint256) {
        return feeTake.relayerFee + feeTake.protocolFee;
    }

    /// @notice Compute a fee take from a set of fee rates and receive amount
    /// @param feeRates The fee rates to compute the fee take from
    /// @param receiveAmount The amount to compute the fee take for
    /// @return The fee take
    function computeFeeTake(FeeTakeRate memory feeRates, uint256 receiveAmount) public pure returns (FeeTake memory) {
        // SAFETY: The fee rates are constrained in-circuit to be less than 2^63, and the receive amount
        // is constrained to be less than 2^100, so the product is less than 2^163, which fits in a uint256
        return FeeTake({
            relayerFee: FixedPointLib.unsafeFixedPointMul(feeRates.relayerFeeRate, receiveAmount),
            protocolFee: FixedPointLib.unsafeFixedPointMul(feeRates.protocolFeeRate, receiveAmount)
        });
    }

    // --- Encryption --- //

    /// @notice Check whether two encryption keys are equal
    /// @param a The first encryption key
    /// @param b The second encryption key
    /// @return Whether the keys are equal
    function encryptionKeyEqual(EncryptionKey memory a, EncryptionKey memory b) public pure returns (bool) {
        bool xEqual = BN254.ScalarField.unwrap(a.point.x) == BN254.ScalarField.unwrap(b.point.x);
        bool yEqual = BN254.ScalarField.unwrap(a.point.y) == BN254.ScalarField.unwrap(b.point.y);
        return xEqual && yEqual;
    }
}

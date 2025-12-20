// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { Vm } from "forge-std/Vm.sol";
import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";

import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";
import {
    BoundedMatchResultPermit,
    BoundedMatchResultBundle,
    BoundedMatchResultPermitLib
} from "darkpoolv2-types/settlement/BoundedMatchResultBundle.sol";
import { BoundedMatchResult, BoundedMatchResultLib } from "darkpoolv2-types/BoundedMatchResult.sol";
import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { SignatureWithNonce } from "darkpoolv2-types/settlement/IntentBundle.sol";
import { SettlementTestUtils } from "../SettlementTestUtils.sol";

contract ExternalMatchTestUtils is SettlementTestUtils {
    using BoundedMatchResultLib for BoundedMatchResult;
    using BoundedMatchResultPermitLib for BoundedMatchResultPermit;
    using FixedPointLib for FixedPoint;

    // ---------
    // | Utils |
    // ---------

    // --- Bounded Match Result --- //

    /// @dev Sign a bounded match result
    function signMatchResult(
        BoundedMatchResultPermit memory permit,
        uint256 signerPrivateKey
    )
        internal
        returns (SignatureWithNonce memory)
    {
        // Sign with the private key
        uint256 nonce = randomUint();
        bytes32 matchResultHash = permit.computeHash();
        bytes32 signatureDigest = EfficientHashLib.hash(matchResultHash, bytes32(nonce));

        (uint8 v, bytes32 r, bytes32 s) = vm.sign(signerPrivateKey, signatureDigest);
        return SignatureWithNonce({ nonce: nonce, signature: abi.encodePacked(r, s, v) });
    }

    /// @dev Create a bounded match result authorization for a given obligation
    /// @param obligation The obligation to create the bounded match result for
    /// @param price The price of the obligation (inToken/outToken)
    /// @return matchResult The bounded match result
    function createBoundedMatchResultForObligation(
        SettlementObligation memory obligation,
        FixedPoint memory price
    )
        internal
        view
        returns (BoundedMatchResult memory matchResult)
    {
        uint256 minInternalPartyAmountIn = 0;
        uint256 maxInternalPartyAmountIn = obligation.amountIn;
        uint256 blockDeadline = block.number + 100;
        matchResult = BoundedMatchResult({
            internalPartyInputToken: obligation.inputToken,
            internalPartyOutputToken: obligation.outputToken,
            price: price,
            minInternalPartyAmountIn: minInternalPartyAmountIn,
            maxInternalPartyAmountIn: maxInternalPartyAmountIn,
            blockDeadline: blockDeadline
        });

        return matchResult;
    }

    /// @dev Create a bounded match result authorization bundle with custom signers
    /// @param matchResult The bounded match result to create the authorization bundle for
    /// @param executorPrivateKey The private key of the executor
    /// @return matchBundle The bounded match result authorization bundle
    function createBoundedMatchResultBundleWithSigners(
        BoundedMatchResult memory matchResult,
        uint256 executorPrivateKey
    )
        internal
        returns (BoundedMatchResultBundle memory)
    {
        // Create the permit and sign it with the executor's key
        BoundedMatchResultPermit memory permit = BoundedMatchResultPermit({ matchResult: matchResult });
        SignatureWithNonce memory matchResultSignature = signMatchResult(permit, executorPrivateKey);

        // Create auth bundle
        return BoundedMatchResultBundle({ permit: permit, executorSignature: matchResultSignature });
    }

    // --- External Match Helpers --- //

    /// @dev Generate a random external party amount in and expected amount out
    /// @param externalObligation The external party's obligation to generate the amount in for
    /// @param price The price of the obligation (inToken/outToken)
    /// @return externalPartyAmountIn The random external party amount in
    /// @return externalPartyAmountOut The expected amount out for the external party
    function randomExternalPartyAmountIn(
        SettlementObligation memory externalObligation,
        FixedPoint memory price
    )
        internal
        returns (uint256 externalPartyAmountIn, uint256 externalPartyAmountOut)
    {
        externalPartyAmountIn = vm.randomUint(0, externalObligation.amountIn);
        externalPartyAmountOut = FixedPointLib.divIntegerByFixedPoint(externalPartyAmountIn, price);
    }

    /// @dev Build obligations from a bounded match result and external party amount in
    /// @param matchResult The bounded match result to build obligations from
    /// @param externalPartyAmountIn The external party amount in
    /// @return externalObligation The external party obligation
    /// @return internalObligation The internal party obligation
    function buildObligationsFromMatchResult(
        BoundedMatchResult memory matchResult,
        uint256 externalPartyAmountIn
    )
        internal
        view
        returns (SettlementObligation memory externalObligation, SettlementObligation memory internalObligation)
    {
        // Use the calldata version via external call for memory-to-calldata conversion
        return this._buildObligationsFromMatchResultCalldata(matchResult, externalPartyAmountIn);
    }

    /// @dev Build obligations from a bounded match result (calldata version)
    function _buildObligationsFromMatchResultCalldata(
        BoundedMatchResult calldata matchResult,
        uint256 externalPartyAmountIn
    )
        external
        view
        returns (SettlementObligation memory externalObligation, SettlementObligation memory internalObligation)
    {
        return BoundedMatchResultLib.buildObligations(matchResult, externalPartyAmountIn);
    }
}

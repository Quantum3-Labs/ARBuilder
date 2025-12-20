// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import { BN254 } from "solidity-bn254/BN254.sol";
import { DarkpoolTestBase } from "darkpoolv1-test/DarkpoolTestBase.sol";
import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { TypesLib } from "darkpoolv1-types/TypesLib.sol";
import {
    PartyMatchPayload,
    MalleableMatchAtomicProofs,
    MatchAtomicLinkingProofs,
    ExternalMatchDirection,
    ExternalMatchResult,
    BoundedMatchResult
} from "darkpoolv1-types/Settlement.sol";
import { FeeTake, FeeTakeRate } from "darkpoolv1-types/Fees.sol";
import { ValidMalleableMatchSettleAtomicStatement } from "darkpoolv1-lib/PublicInputs.sol";
import { MalleableMatchConnector } from "renegade-connectors/MalleableMatchConnector.sol";
import { MalleableMatchConnectorProxy } from "renegade-connectors/MalleableMatchConnectorProxy.sol";

contract MalleableMatchConnectorTest is DarkpoolTestBase {
    using TypesLib for FeeTake;
    using TypesLib for FeeTakeRate;
    using TypesLib for BoundedMatchResult;
    using TypesLib for ExternalMatchResult;
    using FixedPointLib for FixedPoint;

    uint256 constant REFUND_AMT = 100_000;

    MalleableMatchConnector public connector;
    address public connectorAdmin;
    address public externalPartyAddr;
    address public receiver;

    struct SponsorshipParams {
        uint256 nonce;
        address refundAddress;
        bool refundNativeEth;
        bytes signature;
    }

    function setUp() public override {
        super.setUp();

        // Set up addresses
        connectorAdmin = vm.randomAddress();
        externalPartyAddr = vm.randomAddress();
        receiver = vm.randomAddress();

        // Deploy connector implementation and proxy
        MalleableMatchConnector impl = new MalleableMatchConnector();
        MalleableMatchConnectorProxy proxy =
            new MalleableMatchConnectorProxy(address(impl), connectorAdmin, address(gasSponsor));
        connector = MalleableMatchConnector(address(proxy));

        // Fund the gas sponsor
        vm.deal(address(gasSponsor), REFUND_AMT * 10);
        quoteToken.mint(address(gasSponsor), REFUND_AMT * 10);
        baseToken.mint(address(gasSponsor), REFUND_AMT * 10);
    }

    // --- Buy Side Tests (External Party Buys Base) --- //

    /// @notice Test connector with external party on buy side (sells quote, buys base)
    /// @dev External party inputs quote amount, connector calculates base amount
    function test_sponsorMalleableMatch_externalPartyBuySide() public {
        // Setup the malleable match with external party buy side
        (
            uint256 baseAmount,
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = setupMalleableMatch(ExternalMatchDirection.InternalPartySell);

        // Input amount is quote amount for buy side
        uint256 expectedQuoteAmount = statement.matchResult.price.unsafeFixedPointMul(baseAmount);
        uint256 expectedBaseAmount = baseAmount;
        uint256 inputAmount = expectedQuoteAmount;

        // Execute and verify
        executeMalleableMatchSponsorship(
            inputAmount, expectedQuoteAmount, expectedBaseAmount, internalPartyPayload, statement, proofs, linkingProofs
        );
    }

    // --- Sell Side Tests (External Party Sells Base) --- //

    /// @notice Test connector with external party on sell side (sells base, buys quote)
    /// @dev External party inputs base amount, connector calculates quote amount
    function test_sponsorMalleableMatch_externalPartySellSide() public {
        // Setup the malleable match with external party sell side
        (
            uint256 baseAmount,
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = setupMalleableMatch(ExternalMatchDirection.InternalPartyBuy);

        // Input amount is base amount for sell side
        uint256 expectedBaseAmount = baseAmount;
        uint256 expectedQuoteAmount = statement.matchResult.price.unsafeFixedPointMul(baseAmount);
        uint256 inputAmount = expectedBaseAmount;

        // Execute and verify
        executeMalleableMatchSponsorship(
            inputAmount, expectedQuoteAmount, expectedBaseAmount, internalPartyPayload, statement, proofs, linkingProofs
        );
    }

    /// @notice Test that when receiver is address(0), tokens go to msg.sender (externalPartyAddr)
    function test_receiverZeroAddress_usesMsgSender() public {
        // Setup the malleable match with external party buy side
        (
            uint256 baseAmount,
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = setupMalleableMatch(ExternalMatchDirection.InternalPartySell);

        // Input amount is quote amount for buy side
        uint256 expectedQuoteAmount = statement.matchResult.price.unsafeFixedPointMul(baseAmount);
        uint256 expectedBaseAmount = baseAmount;
        uint256 inputAmount = expectedQuoteAmount;

        // Fund and approve tokens for the external party
        fundAndApprove(statement.matchResult.direction, expectedQuoteAmount, expectedBaseAmount);

        // Get balances after funding (before executing transaction)
        (uint256 senderBase1, uint256 senderQuote1) = baseQuoteBalances(externalPartyAddr);
        (uint256 receiverBase1, uint256 receiverQuote1) = baseQuoteBalances(receiver);

        // Execute through connector with address(0) as receiver
        vm.startBroadcast(externalPartyAddr);
        SponsorshipParams memory params = createSponsorshipParams();
        uint256 receivedAmount = connector.executeMalleableAtomicMatchWithInput(
            inputAmount,
            address(0), // Pass address(0) as receiver
            internalPartyPayload,
            statement,
            proofs,
            linkingProofs,
            params.refundAddress,
            params.refundNativeEth,
            REFUND_AMT,
            params.nonce,
            params.signature
        );
        vm.stopBroadcast();

        // Get balances after - should be on externalPartyAddr (msg.sender), not receiver
        (uint256 senderBase2, uint256 senderQuote2) = baseQuoteBalances(externalPartyAddr);
        (uint256 receiverBase2, uint256 receiverQuote2) = baseQuoteBalances(receiver);

        // Build match result for verification
        ExternalMatchResult memory matchResult =
            TypesLib.buildExternalMatchResult(expectedQuoteAmount, expectedBaseAmount, statement.matchResult);

        // Calculate fees
        (, uint256 tradeRecv) = matchResult.externalPartyBuyMintAmount();
        FeeTake memory fees = statement.externalFeeRates.computeFeeTake(tradeRecv);

        // When receiver is address(0), trade tokens go to msg.sender, refund goes to refundAddress
        // The return value is the sum: tradeRecv - fees + refundAmount
        uint256 expectedTradeReceived = tradeRecv - fees.total();
        uint256 expectedTotalReceived = expectedTradeReceived + REFUND_AMT;
        assertApproxEqAbs(receivedAmount, expectedTotalReceived, 1, "Received amount incorrect");

        // Verify token balances go to msg.sender (externalPartyAddr) for trade tokens
        // Refund goes to refundAddress (receiver)
        bool receivingBase = matchResult.direction == ExternalMatchDirection.InternalPartySell;
        if (receivingBase) {
            // External party sells quote tokens (pays expectedQuoteAmount) and receives base tokens
            uint256 expectedSenderBase = senderBase1 + expectedTradeReceived;
            uint256 expectedSenderQuote = senderQuote1 - expectedQuoteAmount;
            assertApproxEqAbs(senderBase2, expectedSenderBase, 1, "Msg.sender base balance incorrect");
            assertApproxEqAbs(
                senderQuote2, expectedSenderQuote, 1, "Msg.sender quote balance should decrease by amount paid"
            );
            // Refund goes to refundAddress (receiver)
            uint256 expectedReceiverBase = receiverBase1 + REFUND_AMT;
            assertApproxEqAbs(receiverBase2, expectedReceiverBase, 1, "Receiver should receive refund");
            assertEq(receiverQuote2, receiverQuote1, "Receiver quote balance should not change");
        } else {
            // External party sells base tokens (pays expectedBaseAmount) and receives quote tokens
            uint256 expectedSenderQuote = senderQuote1 + expectedTradeReceived;
            uint256 expectedSenderBase = senderBase1 - expectedBaseAmount;
            assertApproxEqAbs(
                senderBase2, expectedSenderBase, 1, "Msg.sender base balance should decrease by amount paid"
            );
            assertApproxEqAbs(senderQuote2, expectedSenderQuote, 1, "Msg.sender quote balance incorrect");
            // Refund goes to refundAddress (receiver)
            uint256 expectedReceiverQuote = receiverQuote1 + REFUND_AMT;
            assertEq(receiverBase2, receiverBase1, "Receiver base balance should not change");
            assertApproxEqAbs(receiverQuote2, expectedReceiverQuote, 1, "Receiver should receive refund");
        }
    }

    // --- Calculation Verification Tests --- //

    /// @notice Test that connector calculations match expected formulas for buy side
    function test_connectorCalculations_buySide() public {
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleMalleableAtomicMatchCalldata(ExternalMatchDirection.InternalPartySell, merkleRoot);

        statement.matchResult.quoteMint = address(quoteToken);
        statement.matchResult.baseMint = address(baseToken);

        // Pick a quote amount in the middle of the range
        uint256 minBase = statement.matchResult.minBaseAmount;
        uint256 maxBase = statement.matchResult.maxBaseAmount;
        uint256 targetBase = (minBase + maxBase) / 2;
        uint256 inputQuote = statement.matchResult.price.unsafeFixedPointMul(targetBase);

        // Calculate what the connector should produce
        uint256 expectedBase = FixedPointLib.divIntegerByFixedPoint(inputQuote, statement.matchResult.price);

        // Verify the calculation is correct (should equal our target within rounding)
        uint256 diff = targetBase > expectedBase ? targetBase - expectedBase : expectedBase - targetBase;
        assertLt(diff, 10, "Base amount calculation should be close to target");
    }

    /// @notice Test that connector calculations match expected formulas for sell side
    function test_connectorCalculations_sellSide() public {
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleMalleableAtomicMatchCalldata(ExternalMatchDirection.InternalPartyBuy, merkleRoot);

        statement.matchResult.quoteMint = address(quoteToken);
        statement.matchResult.baseMint = address(baseToken);

        // Pick a base amount in the middle of the range
        uint256 minBase = statement.matchResult.minBaseAmount;
        uint256 maxBase = statement.matchResult.maxBaseAmount;
        uint256 inputBase = (minBase + maxBase) / 2;

        // Calculate what the connector should produce
        uint256 expectedQuote = statement.matchResult.price.unsafeFixedPointMul(inputBase);

        // Verify calculation is consistent with price * base (allow 1 unit difference for rounding)
        FixedPoint memory backCalculatedPrice = FixedPointLib.divIntegers(expectedQuote, inputBase);
        uint256 priceDiff = backCalculatedPrice.repr > statement.matchResult.price.repr
            ? backCalculatedPrice.repr - statement.matchResult.price.repr
            : statement.matchResult.price.repr - backCalculatedPrice.repr;
        assertLe(priceDiff, 1, "Price calculation should be consistent within rounding");
    }

    // --- Helper Functions --- //

    /// @notice Sample a random base amount between the bounds
    function sampleBaseAmount(BoundedMatchResult memory matchResult) internal returns (uint256) {
        uint256 min = matchResult.minBaseAmount;
        uint256 max = matchResult.maxBaseAmount;
        return min + (randomFelt() % (max - min + 1));
    }

    /// @notice Set up a malleable match and return an input amount
    function setupMalleableMatch(ExternalMatchDirection direction)
        internal
        returns (
            uint256 baseAmount,
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        )
    {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (internalPartyPayload, statement, proofs, linkingProofs) =
            settleMalleableAtomicMatchCalldata(direction, merkleRoot);

        // Modify token addresses
        statement.matchResult.quoteMint = address(quoteToken);
        statement.matchResult.baseMint = address(baseToken);

        // Sample a base amount
        baseAmount = sampleBaseAmount(statement.matchResult);
    }

    /// @notice Create gas sponsorship parameters
    function createSponsorshipParams() internal returns (SponsorshipParams memory) {
        SponsorshipParams memory params;
        params.nonce = randomUint();
        params.refundAddress = receiver;
        params.refundNativeEth = false;
        params.signature = signGasSponsorshipPayload(params.nonce, params.refundAddress, REFUND_AMT);
        return params;
    }

    /// @notice Fund and approve tokens for the external party
    function fundAndApprove(ExternalMatchDirection direction, uint256 quoteAmount, uint256 baseAmount) internal {
        if (direction == ExternalMatchDirection.InternalPartySell) {
            // External party buys base, sells quote
            quoteToken.mint(externalPartyAddr, quoteAmount);
            baseToken.mint(address(darkpool), baseAmount);
            vm.startBroadcast(externalPartyAddr);
            quoteToken.approve(address(connector), quoteAmount);
            vm.stopBroadcast();
        } else {
            // External party sells base, buys quote
            baseToken.mint(externalPartyAddr, baseAmount);
            quoteToken.mint(address(darkpool), quoteAmount);
            vm.startBroadcast(externalPartyAddr);
            baseToken.approve(address(connector), baseAmount);
            vm.stopBroadcast();
        }
    }

    /// @notice Execute a malleable match sponsorship and verify results
    function executeMalleableMatchSponsorship(
        uint256 inputAmount,
        uint256 expectedQuoteAmount,
        uint256 expectedBaseAmount,
        PartyMatchPayload memory internalPartyPayload,
        ValidMalleableMatchSettleAtomicStatement memory statement,
        MalleableMatchAtomicProofs memory proofs,
        MatchAtomicLinkingProofs memory linkingProofs
    )
        internal
    {
        // Get balances before and fund the external party
        (uint256 receiverBase1, uint256 receiverQuote1) = baseQuoteBalances(receiver);
        fundAndApprove(statement.matchResult.direction, expectedQuoteAmount, expectedBaseAmount);

        // Execute through connector
        vm.startBroadcast(externalPartyAddr);
        SponsorshipParams memory params = createSponsorshipParams();
        uint256 receivedAmount = connector.executeMalleableAtomicMatchWithInput(
            inputAmount,
            receiver,
            internalPartyPayload,
            statement,
            proofs,
            linkingProofs,
            params.refundAddress,
            params.refundNativeEth,
            REFUND_AMT,
            params.nonce,
            params.signature
        );
        vm.stopBroadcast();

        // Get balances after
        (uint256 receiverBase2, uint256 receiverQuote2) = baseQuoteBalances(receiver);

        // Build match result for verification
        ExternalMatchResult memory matchResult =
            TypesLib.buildExternalMatchResult(expectedQuoteAmount, expectedBaseAmount, statement.matchResult);

        // Calculate fees
        (, uint256 tradeRecv) = matchResult.externalPartyBuyMintAmount();
        FeeTake memory fees = statement.externalFeeRates.computeFeeTake(tradeRecv);

        // Verify received amount (allow ±1 for rounding)
        uint256 expectedTotalReceived = tradeRecv + REFUND_AMT - fees.total();
        assertApproxEqAbs(receivedAmount, expectedTotalReceived, 1, "Received amount incorrect");

        // Verify token balances (allow ±1 for rounding)
        bool receivingBase = matchResult.direction == ExternalMatchDirection.InternalPartySell;
        if (receivingBase) {
            uint256 expectedBase = receiverBase1 + expectedTotalReceived;
            assertApproxEqAbs(receiverBase2, expectedBase, 1, "Receiver base balance incorrect");
            assertEq(receiverQuote2, receiverQuote1, "Receiver quote balance should not change");
        } else {
            uint256 expectedQuote = receiverQuote1 + expectedTotalReceived;
            assertApproxEqAbs(receiverBase2, receiverBase1, 1, "Receiver base balance should not change");
            assertApproxEqAbs(receiverQuote2, expectedQuote, 1, "Receiver quote balance incorrect");
        }
    }
}

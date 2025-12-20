// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import { Vm } from "forge-std/Vm.sol";
import { BN254 } from "solidity-bn254/BN254.sol";
import { DarkpoolTestBase } from "./DarkpoolTestBase.sol";
import { IDarkpool } from "darkpoolv1-interfaces/IDarkpool.sol";
import { NullifierLib as NullifierSetLib } from "renegade-lib/NullifierSet.sol";
import { WalletOperations } from "darkpoolv1-lib/WalletOperations.sol";
import { ExternalTransferLib } from "darkpoolv1-lib/ExternalTransfers.sol";
import { TypesLib } from "darkpoolv1-types/TypesLib.sol";
import {
    PartyMatchPayload,
    MatchAtomicProofs,
    MatchAtomicLinkingProofs,
    ExternalMatchDirection,
    ExternalMatchResult
} from "darkpoolv1-types/Settlement.sol";
import { TransferAuthorization } from "darkpoolv1-types/Transfers.sol";
import { FeeTake } from "darkpoolv1-types/Fees.sol";
import { DarkpoolConstants } from "darkpoolv1-lib/Constants.sol";
import {
    ValidWalletCreateStatement,
    ValidMatchSettleAtomicStatement,
    ValidMatchSettleAtomicWithCommitmentsStatement,
    ValidWalletUpdateStatement
} from "darkpoolv1-lib/PublicInputs.sol";
import { PlonkProof } from "renegade-lib/verifier/Types.sol";

contract SettleAtomicMatchTest is DarkpoolTestBase {
    using TypesLib for FeeTake;

    uint256 constant QUOTE_AMT = 1_000_000;
    uint256 constant BASE_AMT = 5_000_000;

    // --- Valid Match Tests --- //

    /// @notice Test settling an atomic match with the external party buy side
    /// @dev This is the only test in which we test fee receipt
    function test_settleAtomicMatch_externalPartyBuySide() public {
        Vm.Wallet memory externalParty = randomEthereumWallet();
        address relayerFeeAddr = vm.randomAddress();

        // Setup tokens
        quoteToken.mint(externalParty.addr, QUOTE_AMT);
        baseToken.mint(address(darkpool), BASE_AMT);
        (uint256 userBaseBalance1, uint256 userQuoteBalance1) = baseQuoteBalances(externalParty.addr);
        (uint256 darkpoolBaseBalance1, uint256 darkpoolQuoteBalance1) = baseQuoteBalances(address(darkpool));
        (uint256 relayerBaseBalance1, uint256 relayerQuoteBalance1) = baseQuoteBalances(relayerFeeAddr);
        (uint256 protocolBaseBalance1, uint256 protocolQuoteBalance1) = baseQuoteBalances(protocolFeeAddr);

        // Setup the match
        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: address(baseToken),
            quoteAmount: QUOTE_AMT,
            baseAmount: BASE_AMT,
            direction: ExternalMatchDirection.InternalPartySell
        });

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldataWithMatchResult(merkleRoot, matchResult);
        statement.relayerFeeAddress = relayerFeeAddr;

        // Process the match
        vm.startBroadcast(externalParty.addr);
        quoteToken.approve(address(darkpool), QUOTE_AMT);
        darkpool.processAtomicMatchSettle(externalParty.addr, internalPartyPayload, statement, proofs, linkingProofs);
        vm.stopBroadcast();

        // Check the token flows
        FeeTake memory fees = statement.externalPartyFees;
        uint256 totalFee = fees.total();
        assert(totalFee > 0); // Make sure we're testing fees
        uint256 expectedBaseAmt = BASE_AMT - totalFee;

        (uint256 userBaseBalance2, uint256 userQuoteBalance2) = baseQuoteBalances(externalParty.addr);
        (uint256 darkpoolBaseBalance2, uint256 darkpoolQuoteBalance2) = baseQuoteBalances(address(darkpool));
        (uint256 relayerBaseBalance2, uint256 relayerQuoteBalance2) = baseQuoteBalances(relayerFeeAddr);
        (uint256 protocolBaseBalance2, uint256 protocolQuoteBalance2) = baseQuoteBalances(protocolFeeAddr);

        assertEq(userQuoteBalance2, userQuoteBalance1 - QUOTE_AMT);
        assertEq(userBaseBalance2, userBaseBalance1 + expectedBaseAmt);
        assertEq(darkpoolQuoteBalance2, darkpoolQuoteBalance1 + QUOTE_AMT);
        assertEq(darkpoolBaseBalance2, darkpoolBaseBalance1 - BASE_AMT);
        assertEq(relayerQuoteBalance2, relayerQuoteBalance1);
        assertEq(relayerBaseBalance2, relayerBaseBalance1 + fees.relayerFee);
        assertEq(protocolQuoteBalance2, protocolQuoteBalance1);
        assertEq(protocolBaseBalance2, protocolBaseBalance1 + fees.protocolFee);
    }

    /// @notice Test settling an atomic match with the external party sell side
    /// @dev This is the only test in which we test fee receipt
    function test_settleAtomicMatch_externalPartySellSide() public {
        Vm.Wallet memory externalParty = randomEthereumWallet();
        address relayerFeeAddr = vm.randomAddress();

        // Setup tokens
        quoteToken.mint(address(darkpool), QUOTE_AMT);
        baseToken.mint(externalParty.addr, BASE_AMT);
        (uint256 userBaseBalance1, uint256 userQuoteBalance1) = baseQuoteBalances(externalParty.addr);
        (uint256 darkpoolBaseBalance1, uint256 darkpoolQuoteBalance1) = baseQuoteBalances(address(darkpool));
        (uint256 relayerBaseBalance1, uint256 relayerQuoteBalance1) = baseQuoteBalances(relayerFeeAddr);
        (uint256 protocolBaseBalance1, uint256 protocolQuoteBalance1) = baseQuoteBalances(protocolFeeAddr);

        // Setup the match
        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: address(baseToken),
            quoteAmount: QUOTE_AMT,
            baseAmount: BASE_AMT,
            direction: ExternalMatchDirection.InternalPartyBuy
        });

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldataWithMatchResult(merkleRoot, matchResult);
        statement.relayerFeeAddress = relayerFeeAddr;

        // Process the match
        vm.startBroadcast(externalParty.addr);
        baseToken.approve(address(darkpool), BASE_AMT);
        darkpool.processAtomicMatchSettle(externalParty.addr, internalPartyPayload, statement, proofs, linkingProofs);
        vm.stopBroadcast();

        // Check the token flows
        FeeTake memory fees = statement.externalPartyFees;
        uint256 totalFee = fees.total();
        uint256 expectedQuoteAmt = QUOTE_AMT - totalFee;

        (uint256 userBaseBalance2, uint256 userQuoteBalance2) = baseQuoteBalances(externalParty.addr);
        (uint256 darkpoolBaseBalance2, uint256 darkpoolQuoteBalance2) = baseQuoteBalances(address(darkpool));
        (uint256 relayerBaseBalance2, uint256 relayerQuoteBalance2) = baseQuoteBalances(relayerFeeAddr);
        (uint256 protocolBaseBalance2, uint256 protocolQuoteBalance2) = baseQuoteBalances(protocolFeeAddr);

        assertEq(userQuoteBalance2, userQuoteBalance1 + expectedQuoteAmt);
        assertEq(userBaseBalance2, userBaseBalance1 - BASE_AMT);
        assertEq(darkpoolQuoteBalance2, darkpoolQuoteBalance1 - QUOTE_AMT);
        assertEq(darkpoolBaseBalance2, darkpoolBaseBalance1 + BASE_AMT);
        assertEq(relayerQuoteBalance2, relayerQuoteBalance1 + fees.relayerFee);
        assertEq(relayerBaseBalance2, relayerBaseBalance1);
        assertEq(protocolQuoteBalance2, protocolQuoteBalance1 + fees.protocolFee);
        assertEq(protocolBaseBalance2, protocolBaseBalance1);
    }

    /// @notice Test settling an atomic match with a non-sender receiver specified
    function test_settleAtomicMatch_nonSenderReceiver_buySide() public {
        Vm.Wallet memory externalParty = randomEthereumWallet();
        address receiver = vm.randomAddress();

        // Setup tokens
        quoteToken.mint(externalParty.addr, QUOTE_AMT);
        baseToken.mint(address(darkpool), BASE_AMT);
        (uint256 senderBaseBalance1, uint256 senderQuoteBalance1) = baseQuoteBalances(externalParty.addr);
        (uint256 receiverBaseBalance1, uint256 receiverQuoteBalance1) = baseQuoteBalances(receiver);
        (uint256 darkpoolBaseBalance1, uint256 darkpoolQuoteBalance1) = baseQuoteBalances(address(darkpool));

        // Setup the match
        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: address(baseToken),
            quoteAmount: QUOTE_AMT,
            baseAmount: BASE_AMT,
            direction: ExternalMatchDirection.InternalPartySell
        });

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldataWithMatchResult(merkleRoot, matchResult);

        // Process the match
        vm.startBroadcast(externalParty.addr);
        quoteToken.approve(address(darkpool), QUOTE_AMT);
        darkpool.processAtomicMatchSettle(receiver, internalPartyPayload, statement, proofs, linkingProofs);
        vm.stopBroadcast();

        // Check the token flows
        FeeTake memory fees = statement.externalPartyFees;
        uint256 totalFee = fees.total();
        uint256 expectedBaseAmt = BASE_AMT - totalFee;

        (uint256 senderBaseBalance2, uint256 senderQuoteBalance2) = baseQuoteBalances(externalParty.addr);
        (uint256 receiverBaseBalance2, uint256 receiverQuoteBalance2) = baseQuoteBalances(receiver);
        (uint256 darkpoolBaseBalance2, uint256 darkpoolQuoteBalance2) = baseQuoteBalances(address(darkpool));

        assertEq(senderQuoteBalance2, senderQuoteBalance1 - QUOTE_AMT);
        assertEq(senderBaseBalance2, senderBaseBalance1);
        assertEq(receiverQuoteBalance2, receiverQuoteBalance1);
        assertEq(receiverBaseBalance2, receiverBaseBalance1 + expectedBaseAmt);
        assertEq(darkpoolQuoteBalance2, darkpoolQuoteBalance1 + QUOTE_AMT);
        assertEq(darkpoolBaseBalance2, darkpoolBaseBalance1 - BASE_AMT);
    }

    /// @notice Test settling an atomic match with a non-sender receiver specified
    function test_settleAtomicMatch_nonSenderReceiver_sellSide() public {
        Vm.Wallet memory externalParty = randomEthereumWallet();
        address receiver = vm.randomAddress();

        // Setup tokens
        quoteToken.mint(address(darkpool), QUOTE_AMT);
        baseToken.mint(externalParty.addr, BASE_AMT);
        (uint256 senderBaseBalance1, uint256 senderQuoteBalance1) = baseQuoteBalances(externalParty.addr);
        (uint256 receiverBaseBalance1, uint256 receiverQuoteBalance1) = baseQuoteBalances(receiver);
        (uint256 darkpoolBaseBalance1, uint256 darkpoolQuoteBalance1) = baseQuoteBalances(address(darkpool));

        // Setup the match
        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: address(baseToken),
            quoteAmount: QUOTE_AMT,
            baseAmount: BASE_AMT,
            direction: ExternalMatchDirection.InternalPartyBuy
        });

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldataWithMatchResult(merkleRoot, matchResult);

        // Process the match
        vm.startBroadcast(externalParty.addr);
        baseToken.approve(address(darkpool), BASE_AMT);
        darkpool.processAtomicMatchSettle(receiver, internalPartyPayload, statement, proofs, linkingProofs);
        vm.stopBroadcast();

        // Check the token flows
        FeeTake memory fees = statement.externalPartyFees;
        uint256 totalFee = fees.total();
        uint256 expectedQuoteAmt = QUOTE_AMT - totalFee;

        (uint256 senderBaseBalance2, uint256 senderQuoteBalance2) = baseQuoteBalances(externalParty.addr);
        (uint256 receiverBaseBalance2, uint256 receiverQuoteBalance2) = baseQuoteBalances(receiver);
        (uint256 darkpoolBaseBalance2, uint256 darkpoolQuoteBalance2) = baseQuoteBalances(address(darkpool));

        assertEq(senderQuoteBalance2, senderQuoteBalance1);
        assertEq(senderBaseBalance2, senderBaseBalance1 - BASE_AMT);
        assertEq(receiverQuoteBalance2, receiverQuoteBalance1 + expectedQuoteAmt);
        assertEq(receiverBaseBalance2, receiverBaseBalance1);
        assertEq(darkpoolQuoteBalance2, darkpoolQuoteBalance1 - QUOTE_AMT);
        assertEq(darkpoolBaseBalance2, darkpoolBaseBalance1 + BASE_AMT);
    }

    /// @notice Test settling an atomic match with a native token, buy side
    function test_settleAtomicMatch_nativeToken_buySide() public {
        Vm.Wallet memory externalParty = randomEthereumWallet();

        // Setup tokens
        quoteToken.mint(externalParty.addr, QUOTE_AMT);
        weth.mint(address(darkpool), BASE_AMT);

        (uint256 userNativeBalance1, uint256 userQuoteBalance1) = etherQuoteBalances(externalParty.addr);
        (uint256 darkpoolWethBalance1, uint256 darkpoolQuoteBalance1) = wethQuoteBalances(address(darkpool));

        // Setup the match
        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: DarkpoolConstants.NATIVE_TOKEN_ADDRESS,
            quoteAmount: QUOTE_AMT,
            baseAmount: BASE_AMT,
            direction: ExternalMatchDirection.InternalPartySell
        });

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldataWithMatchResult(merkleRoot, matchResult);

        // Process the match
        vm.startBroadcast(externalParty.addr);
        quoteToken.approve(address(darkpool), QUOTE_AMT);
        darkpool.processAtomicMatchSettle(externalParty.addr, internalPartyPayload, statement, proofs, linkingProofs);
        vm.stopBroadcast();

        // Check the token flows
        FeeTake memory fees = statement.externalPartyFees;
        uint256 totalFee = fees.total();
        uint256 expectedBaseAmt = BASE_AMT - totalFee;

        (uint256 userNativeBalance2, uint256 userQuoteBalance2) = etherQuoteBalances(externalParty.addr);
        (uint256 darkpoolWethBalance2, uint256 darkpoolQuoteBalance2) = wethQuoteBalances(address(darkpool));

        assertEq(userQuoteBalance2, userQuoteBalance1 - QUOTE_AMT);
        assertEq(userNativeBalance2, userNativeBalance1 + expectedBaseAmt);
        assertEq(darkpoolQuoteBalance2, darkpoolQuoteBalance1 + QUOTE_AMT);
        assertEq(darkpoolWethBalance2, darkpoolWethBalance1 - BASE_AMT);
    }

    /// @notice Test settling an atomic match with a native token, sell side
    function test_settleAtomicMatch_nativeToken_sellSide() public {
        Vm.Wallet memory externalParty = randomEthereumWallet();

        // Setup tokens
        vm.deal(externalParty.addr, BASE_AMT);
        quoteToken.mint(address(darkpool), QUOTE_AMT);
        (uint256 userNativeBalance1, uint256 userQuoteBalance1) = etherQuoteBalances(externalParty.addr);
        (uint256 darkpoolWethBalance1, uint256 darkpoolQuoteBalance1) = wethQuoteBalances(address(darkpool));

        // Setup the match
        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: DarkpoolConstants.NATIVE_TOKEN_ADDRESS,
            quoteAmount: QUOTE_AMT,
            baseAmount: BASE_AMT,
            direction: ExternalMatchDirection.InternalPartyBuy
        });

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldataWithMatchResult(merkleRoot, matchResult);

        // Process the match
        vm.startBroadcast(externalParty.addr);
        darkpool.processAtomicMatchSettle{ value: BASE_AMT }(
            externalParty.addr, internalPartyPayload, statement, proofs, linkingProofs
        );
        vm.stopBroadcast();

        // Check the token flows
        FeeTake memory fees = statement.externalPartyFees;
        uint256 totalFee = fees.total();
        uint256 expectedQuoteAmt = QUOTE_AMT - totalFee;

        (uint256 userNativeBalance2, uint256 userQuoteBalance2) = etherQuoteBalances(externalParty.addr);
        (uint256 darkpoolWethBalance2, uint256 darkpoolQuoteBalance2) = wethQuoteBalances(address(darkpool));

        assertEq(userQuoteBalance2, userQuoteBalance1 + expectedQuoteAmt);
        assertEq(userNativeBalance2, userNativeBalance1 - BASE_AMT);
        assertEq(darkpoolQuoteBalance2, darkpoolQuoteBalance1 - QUOTE_AMT);
        assertEq(darkpoolWethBalance2, darkpoolWethBalance1 + BASE_AMT);
    }

    /// @notice Test settling an atomic match with a non-default protocol fee rate
    function test_settleAtomicMatch_nonDefaultProtocolFeeRate() public {
        // Get the original protocol fee rate
        uint256 originalProtocolFeeRate = darkpool.getTokenExternalMatchFeeRate(address(baseToken));
        assertEq(originalProtocolFeeRate, TEST_PROTOCOL_FEE);

        // Setup the protocol fee rate
        uint256 protocolFeeRate = 4_611_686_018_427_388; // 0.0005 * 2 ** `FIXED_POINT_PRECISION`
        vm.prank(darkpoolOwner);
        darkpool.setTokenExternalMatchFeeRate(address(baseToken), protocolFeeRate);
        assertEq(darkpool.getTokenExternalMatchFeeRate(address(baseToken)), protocolFeeRate);

        // Setup the tokens
        Vm.Wallet memory externalParty = randomEthereumWallet();
        baseToken.mint(externalParty.addr, BASE_AMT);
        quoteToken.mint(address(darkpool), QUOTE_AMT);
        (uint256 userBaseBalance1, uint256 userQuoteBalance1) = baseQuoteBalances(externalParty.addr);
        (uint256 darkpoolBaseBalance1, uint256 darkpoolQuoteBalance1) = baseQuoteBalances(address(darkpool));

        // Setup the match
        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: address(baseToken),
            quoteAmount: QUOTE_AMT,
            baseAmount: BASE_AMT,
            direction: ExternalMatchDirection.InternalPartyBuy
        });

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldataWithMatchResult(merkleRoot, matchResult);
        FeeTake memory newFees = computeFeesWithRates(QUOTE_AMT, TEST_RELAYER_FEE, protocolFeeRate);
        statement.externalPartyFees = newFees;
        statement.protocolFeeRate = protocolFeeRate;

        // Process the match
        vm.startBroadcast(externalParty.addr);
        baseToken.approve(address(darkpool), BASE_AMT);
        darkpool.processAtomicMatchSettle(externalParty.addr, internalPartyPayload, statement, proofs, linkingProofs);
        vm.stopBroadcast();

        // Check the token flows
        uint256 totalFee = newFees.total();
        uint256 expectedQuoteAmt = QUOTE_AMT - totalFee;

        (uint256 userBaseBalance2, uint256 userQuoteBalance2) = baseQuoteBalances(externalParty.addr);
        (uint256 darkpoolBaseBalance2, uint256 darkpoolQuoteBalance2) = baseQuoteBalances(address(darkpool));

        assertEq(userQuoteBalance2, userQuoteBalance1 + expectedQuoteAmt);
        assertEq(userBaseBalance2, userBaseBalance1 - BASE_AMT);
        assertEq(darkpoolQuoteBalance2, darkpoolQuoteBalance1 - QUOTE_AMT);
        assertEq(darkpoolBaseBalance2, darkpoolBaseBalance1 + BASE_AMT);
    }

    /// @notice Test settling an atomic match with commitments
    function test_settleAtomicMatchWithCommitments_buySide() public {
        vm.skip(true, "Match with commitments tests are disabled");

        Vm.Wallet memory externalParty = randomEthereumWallet();
        address receiver = vm.randomAddress();

        // Setup tokens
        quoteToken.mint(externalParty.addr, QUOTE_AMT);
        baseToken.mint(address(darkpool), BASE_AMT);
        (uint256 senderBaseBalance1, uint256 senderQuoteBalance1) = baseQuoteBalances(externalParty.addr);
        (uint256 receiverBaseBalance1, uint256 receiverQuoteBalance1) = baseQuoteBalances(receiver);
        (uint256 darkpoolBaseBalance1, uint256 darkpoolQuoteBalance1) = baseQuoteBalances(address(darkpool));

        // Setup the match
        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: address(baseToken),
            quoteAmount: QUOTE_AMT,
            baseAmount: BASE_AMT,
            direction: ExternalMatchDirection.InternalPartySell
        });

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicWithCommitmentsStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchWithCommitmentsCalldata(merkleRoot, matchResult);

        // Process the match
        vm.startBroadcast(externalParty.addr);
        quoteToken.approve(address(darkpool), QUOTE_AMT);
        darkpool.processAtomicMatchSettleWithCommitments(
            receiver, internalPartyPayload, statement, proofs, linkingProofs
        );
        vm.stopBroadcast();

        // Check the token flows
        uint256 totalFee = statement.externalPartyFees.total();
        uint256 expectedBaseAmt = BASE_AMT - totalFee;
        (uint256 senderBaseBalance2, uint256 senderQuoteBalance2) = baseQuoteBalances(externalParty.addr);
        (uint256 receiverBaseBalance2, uint256 receiverQuoteBalance2) = baseQuoteBalances(receiver);
        (uint256 darkpoolBaseBalance2, uint256 darkpoolQuoteBalance2) = baseQuoteBalances(address(darkpool));

        assertEq(senderBaseBalance2, senderBaseBalance1);
        assertEq(senderQuoteBalance2, senderQuoteBalance1 - QUOTE_AMT);
        assertEq(receiverBaseBalance2, receiverBaseBalance1 + expectedBaseAmt);
        assertEq(receiverQuoteBalance2, receiverQuoteBalance1);
        assertEq(darkpoolBaseBalance2, darkpoolBaseBalance1 - BASE_AMT);
        assertEq(darkpoolQuoteBalance2, darkpoolQuoteBalance1 + QUOTE_AMT);
    }

    /// @notice Test settling an atomic match with commitments, sell side
    function test_settleAtomicMatchWithCommitments_sellSide() public {
        vm.skip(true, "Match with commitments tests are disabled");

        Vm.Wallet memory externalParty = randomEthereumWallet();
        address receiver = vm.randomAddress();

        // Setup tokens
        baseToken.mint(externalParty.addr, BASE_AMT);
        quoteToken.mint(address(darkpool), QUOTE_AMT);
        (uint256 senderBaseBalance1, uint256 senderQuoteBalance1) = baseQuoteBalances(externalParty.addr);
        (uint256 receiverBaseBalance1, uint256 receiverQuoteBalance1) = baseQuoteBalances(receiver);
        (uint256 darkpoolBaseBalance1, uint256 darkpoolQuoteBalance1) = baseQuoteBalances(address(darkpool));

        // Setup the match
        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: address(baseToken),
            quoteAmount: QUOTE_AMT,
            baseAmount: BASE_AMT,
            direction: ExternalMatchDirection.InternalPartyBuy
        });

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicWithCommitmentsStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchWithCommitmentsCalldata(merkleRoot, matchResult);

        // Process the match
        vm.startBroadcast(externalParty.addr);
        baseToken.approve(address(darkpool), BASE_AMT);
        darkpool.processAtomicMatchSettleWithCommitments(
            receiver, internalPartyPayload, statement, proofs, linkingProofs
        );
        vm.stopBroadcast();

        // Check the token flows
        uint256 totalFee = statement.externalPartyFees.total();
        uint256 expectedQuoteAmt = QUOTE_AMT - totalFee;
        (uint256 senderBaseBalance2, uint256 senderQuoteBalance2) = baseQuoteBalances(externalParty.addr);
        (uint256 receiverBaseBalance2, uint256 receiverQuoteBalance2) = baseQuoteBalances(receiver);
        (uint256 darkpoolBaseBalance2, uint256 darkpoolQuoteBalance2) = baseQuoteBalances(address(darkpool));

        assertEq(senderBaseBalance2, senderBaseBalance1 - BASE_AMT);
        assertEq(senderQuoteBalance2, senderQuoteBalance1);
        assertEq(receiverBaseBalance2, receiverBaseBalance1);
        assertEq(receiverQuoteBalance2, receiverQuoteBalance1 + expectedQuoteAmt);
        assertEq(darkpoolBaseBalance2, darkpoolBaseBalance1 + BASE_AMT);
        assertEq(darkpoolQuoteBalance2, darkpoolQuoteBalance1 - QUOTE_AMT);
    }

    // --- Invalid Match Tests --- //

    /// @notice Test settling an atomic match with an invalid proof
    function test_settleAtomicMatch_invalidProof() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: address(baseToken),
            quoteAmount: QUOTE_AMT,
            baseAmount: BASE_AMT,
            direction: ExternalMatchDirection.InternalPartyBuy
        });

        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldataWithMatchResult(merkleRoot, matchResult);

        // Should fail
        vm.expectRevert(IDarkpool.VerificationFailed.selector);
        darkpoolRealVerifier.processAtomicMatchSettle(
            address(0), internalPartyPayload, statement, proofs, linkingProofs
        );
    }

    /// @notice Test settling an atomic match with a duplicate public blinder share
    function test_settleAtomicMatch_duplicateBlinder() public {
        // Create a wallet using the public blinder
        (ValidWalletCreateStatement memory createStatement, PlonkProof memory createProof) = createWalletCalldata();
        darkpool.createWallet(createStatement, createProof);
        BN254.ScalarField publicBlinder = createStatement.publicShares[createStatement.publicShares.length - 1];

        // Setup the match
        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: address(baseToken),
            quoteAmount: QUOTE_AMT,
            baseAmount: BASE_AMT,
            direction: ExternalMatchDirection.InternalPartyBuy
        });

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldataWithMatchResult(merkleRoot, matchResult);
        statement.internalPartyModifiedShares[statement.internalPartyModifiedShares.length - 1] = publicBlinder;

        // Should fail
        vm.expectRevert(NullifierSetLib.NullifierAlreadySpent.selector);
        darkpool.processAtomicMatchSettle(address(0), internalPartyPayload, statement, proofs, linkingProofs);
    }

    /// @notice Test settling an atomic match wherein the fees exceed the receive amount
    function test_settleAtomicMatch_feesExceedReceiveAmount() public {
        // Setup match
        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: address(baseToken),
            quoteAmount: 100,
            baseAmount: 100,
            direction: ExternalMatchDirection.InternalPartyBuy
        });

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldataWithMatchResult(merkleRoot, matchResult);
        statement.externalPartyFees.relayerFee = 101; // More than receive amount

        // Process the match
        vm.expectRevert();
        darkpool.processAtomicMatchSettle(address(0), internalPartyPayload, statement, proofs, linkingProofs);
    }

    /// @notice Test settling an atomic match with an invalid ETH value
    function test_settleAtomicMatch_invalidValue() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldata(merkleRoot);

        // Process the match
        vm.expectRevert(IDarkpool.InvalidETHValue.selector);
        darkpool.processAtomicMatchSettle{ value: 1 wei }(
            address(0), internalPartyPayload, statement, proofs, linkingProofs
        );
    }

    /// @notice Test settling an atomic match with a spent nullifier from the internal party
    function test_settleAtomicMatch_spentNullifier() public {
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        BN254.ScalarField nullifier = randomScalar();

        // Update a wallet using the nullifier
        (bytes memory newSharesCommitmentSig, ValidWalletUpdateStatement memory statement, PlonkProof memory proof) =
            updateWalletCalldata();
        statement.previousNullifier = nullifier;
        statement.merkleRoot = merkleRoot;
        TransferAuthorization memory transferAuthorization = emptyTransferAuthorization();
        darkpool.updateWallet(newSharesCommitmentSig, transferAuthorization, statement, proof);

        // Setup calldata
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory matchStatement,
            MatchAtomicProofs memory matchProofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldata(merkleRoot);

        // Use the nullifier
        internalPartyPayload.validReblindStatement.originalSharesNullifier = nullifier;

        // Should fail
        vm.expectRevert(NullifierSetLib.NullifierAlreadySpent.selector);
        darkpool.processAtomicMatchSettle(address(0), internalPartyPayload, matchStatement, matchProofs, linkingProofs);
    }

    /// @notice Test settling an atomic match with an invalid merkle root
    function test_settleAtomicMatch_invalidMerkleRoot() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = randomScalar();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldata(merkleRoot);

        // Should fail
        vm.expectRevert(WalletOperations.MerkleRootNotInHistory.selector);
        darkpool.processAtomicMatchSettle(address(0), internalPartyPayload, statement, proofs, linkingProofs);
    }

    /// @notice Test settling an atomic match with inconsistent settlement indices for the internal party
    function test_settleAtomicMatch_inconsistentIndices() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldata(merkleRoot);

        internalPartyPayload.validCommitmentsStatement.indices = randomOrderSettlementIndices();

        // Should fail
        vm.expectRevert(IDarkpool.InvalidOrderSettlementIndices.selector);
        darkpool.processAtomicMatchSettle(address(0), internalPartyPayload, statement, proofs, linkingProofs);
    }

    /// @notice Test settling an atomic match with an invalid protocol fee rate
    function test_settleAtomicMatch_invalidProtocolFeeRate() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldata(merkleRoot);

        statement.protocolFeeRate = BN254.ScalarField.unwrap(randomScalar());

        // Should fail
        vm.expectRevert(IDarkpool.InvalidProtocolFeeRate.selector);
        darkpool.processAtomicMatchSettle(address(0), internalPartyPayload, statement, proofs, linkingProofs);
    }

    /// @notice Test settling an atomic match with insufficient tx value
    function test_settleAtomicMatch_insufficientTxValue() public {
        Vm.Wallet memory externalParty = randomEthereumWallet();
        vm.deal(externalParty.addr, 100);

        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: DarkpoolConstants.NATIVE_TOKEN_ADDRESS,
            quoteAmount: 100,
            baseAmount: 100,
            direction: ExternalMatchDirection.InternalPartyBuy
        });

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldataWithMatchResult(merkleRoot, matchResult);

        // Should fail
        vm.startBroadcast(externalParty.addr);
        vm.expectRevert(ExternalTransferLib.InvalidDepositAmount.selector);
        darkpool.processAtomicMatchSettle{ value: 1 wei }(
            address(0), internalPartyPayload, statement, proofs, linkingProofs
        );
        vm.stopBroadcast();
    }

    /// @notice Test settling an atomic match with commitments with an invalid private share commitment
    function test_settleAtomicMatchWithCommitments_invalidPrivateShareCommitment() public {
        vm.skip(true, "Match with commitments tests are disabled");

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: address(baseToken),
            quoteAmount: QUOTE_AMT,
            baseAmount: BASE_AMT,
            direction: ExternalMatchDirection.InternalPartyBuy
        });

        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicWithCommitmentsStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchWithCommitmentsCalldata(merkleRoot, matchResult);
        statement.privateShareCommitment = randomScalar();

        // Should fail
        vm.expectRevert(IDarkpool.InvalidPrivateShareCommitment.selector);
        darkpool.processAtomicMatchSettleWithCommitments(
            address(0), internalPartyPayload, statement, proofs, linkingProofs
        );
    }
}

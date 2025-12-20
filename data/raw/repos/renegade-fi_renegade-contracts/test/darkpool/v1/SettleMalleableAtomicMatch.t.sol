// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import { BN254 } from "solidity-bn254/BN254.sol";
import { ERC20Mock } from "oz-contracts/mocks/token/ERC20Mock.sol";
import { DarkpoolTestBase } from "./DarkpoolTestBase.sol";
import { IDarkpool } from "darkpoolv1-interfaces/IDarkpool.sol";
import { NullifierLib as NullifierSetLib } from "renegade-lib/NullifierSet.sol";
import { WalletOperations } from "darkpoolv1-lib/WalletOperations.sol";
import { ExternalTransferLib } from "darkpoolv1-lib/ExternalTransfers.sol";

import {
    PartyMatchPayload, MalleableMatchAtomicProofs, MatchAtomicLinkingProofs
} from "darkpoolv1-types/Settlement.sol";
import { FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { TypesLib } from "darkpoolv1-types/TypesLib.sol";
import { FeeTake, FeeTakeRate } from "darkpoolv1-types/Fees.sol";
import { PlonkProof } from "renegade-lib/verifier/Types.sol";
import { ExternalMatchDirection, BoundedMatchResult, ExternalMatchResult } from "darkpoolv1-types/Settlement.sol";
import { TransferAuthorization } from "darkpoolv1-types/Transfers.sol";
import {
    ValidWalletCreateStatement,
    ValidMalleableMatchSettleAtomicStatement,
    ValidWalletUpdateStatement
} from "darkpoolv1-lib/PublicInputs.sol";
import { DarkpoolConstants } from "darkpoolv1-lib/Constants.sol";

contract SettleMalleableAtomicMatch is DarkpoolTestBase {
    using TypesLib for FeeTake;
    using TypesLib for FeeTakeRate;
    using TypesLib for BoundedMatchResult;

    address public txSender;
    address public relayerFeeAddr;

    function setUp() public override {
        super.setUp();
        txSender = vm.randomAddress();
        relayerFeeAddr = vm.randomAddress();
    }

    // --- Valid Match Tests --- //

    /// @notice Test settling a malleable atomic match with the external party buy side
    function test_settleMalleableAtomicMatch_externalPartyBuySide() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = genMalleableMatchCalldata(ExternalMatchDirection.InternalPartySell, merkleRoot);

        // Fund the external party and darkpool
        ExternalMatchResult memory externalMatchResult = sampleExternalMatch(statement.matchResult);
        fundExternalPartyAndDarkpool(externalMatchResult);

        uint256 quoteAmount = externalMatchResult.quoteAmount;
        uint256 baseAmount = externalMatchResult.baseAmount;
        verifyMalleableAtomicMatch(
            txSender, quoteAmount, baseAmount, internalPartyPayload, statement, proofs, linkingProofs
        );
    }

    /// @notice Test settling a malleable atomic match with the external party sell side
    function test_settleMalleableAtomicMatch_externalPartySellSide() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = genMalleableMatchCalldata(ExternalMatchDirection.InternalPartyBuy, merkleRoot);

        // Fund the external party and darkpool
        ExternalMatchResult memory externalMatchResult = sampleExternalMatch(statement.matchResult);
        fundExternalPartyAndDarkpool(externalMatchResult);

        uint256 quoteAmount = externalMatchResult.quoteAmount;
        uint256 baseAmount = externalMatchResult.baseAmount;
        verifyMalleableAtomicMatch(
            txSender, quoteAmount, baseAmount, internalPartyPayload, statement, proofs, linkingProofs
        );
    }

    /// @notice Test settling a malleable atomic match on the native asset, buy side
    function test_settleMalleableAtomicMatch_nativeAssetBuySide() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = genMalleableMatchCalldata(ExternalMatchDirection.InternalPartySell, merkleRoot);
        statement.matchResult.baseMint = DarkpoolConstants.NATIVE_TOKEN_ADDRESS;

        // Fund the external party and darkpool
        ExternalMatchResult memory externalMatchResult = sampleExternalMatch(statement.matchResult);
        fundExternalPartyAndDarkpool(externalMatchResult);

        uint256 quoteAmount = externalMatchResult.quoteAmount;
        uint256 baseAmount = externalMatchResult.baseAmount;
        verifyMalleableAtomicMatch(
            txSender, quoteAmount, baseAmount, internalPartyPayload, statement, proofs, linkingProofs
        );
    }

    /// @notice Test settling a malleable atomic match on the native asset, sell side
    function test_settleMalleableAtomicMatch_nativeAssetSellSide() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = genMalleableMatchCalldata(ExternalMatchDirection.InternalPartyBuy, merkleRoot);
        statement.matchResult.baseMint = DarkpoolConstants.NATIVE_TOKEN_ADDRESS;

        // Fund the external party and darkpool
        ExternalMatchResult memory externalMatchResult = sampleExternalMatch(statement.matchResult);
        fundExternalPartyAndDarkpool(externalMatchResult);

        uint256 quoteAmount = externalMatchResult.quoteAmount;
        uint256 baseAmount = externalMatchResult.baseAmount;
        verifyMalleableAtomicMatch(
            txSender, quoteAmount, baseAmount, internalPartyPayload, statement, proofs, linkingProofs
        );
    }

    /// @notice Test settling a malleable atomic match with a receiver that is not the tx sender
    function test_settleMalleableAtomicMatch_nonSenderReceiver() public {
        address receiver = vm.randomAddress();

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = genMalleableMatchCalldata(ExternalMatchDirection.InternalPartySell, merkleRoot);

        // Fund the external party and darkpool
        ExternalMatchResult memory externalMatchResult = sampleExternalMatch(statement.matchResult);
        fundExternalPartyAndDarkpool(externalMatchResult);

        // Get the receiver and sender's balances before the match
        (uint256 receiverBaseBalance1, uint256 receiverQuoteBalance1) = baseQuoteBalances(receiver);
        (uint256 senderBaseBalance1, uint256 senderQuoteBalance1) = baseQuoteBalances(txSender);

        // Submit the match
        vm.startBroadcast(txSender);
        uint256 quoteAmount = externalMatchResult.quoteAmount;
        uint256 baseAmount = externalMatchResult.baseAmount;
        darkpool.processMalleableAtomicMatchSettle(
            quoteAmount, baseAmount, receiver, internalPartyPayload, statement, proofs, linkingProofs
        );
        vm.stopBroadcast();

        // Get the balances after the match
        (uint256 receiverBaseBalance2, uint256 receiverQuoteBalance2) = baseQuoteBalances(receiver);
        (uint256 senderBaseBalance2, uint256 senderQuoteBalance2) = baseQuoteBalances(txSender);

        // Check the token flows
        FeeTakeRate memory externalPartyFees = statement.externalFeeRates;
        FeeTake memory externalPartyFeeTake = TypesLib.computeFeeTake(externalPartyFees, baseAmount);

        // Check that the receiver got the tokens and sender didn't
        assertEq(receiverBaseBalance2, receiverBaseBalance1 + baseAmount - externalPartyFeeTake.total());
        assertEq(receiverQuoteBalance2, receiverQuoteBalance1);
        assertEq(senderBaseBalance2, senderBaseBalance1);
        assertEq(senderQuoteBalance2, senderQuoteBalance1 - quoteAmount);
    }

    // --- Invalid Match Test Cases --- //

    /// @notice Test settling a malleable match with an invalid proof
    function test_settleMalleableAtomicMatch_invalidProof() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = genMalleableMatchCalldata(ExternalMatchDirection.InternalPartySell, merkleRoot);

        // Should fail
        uint256 baseAmount = statement.matchResult.minBaseAmount;
        uint256 quoteAmount = FixedPointLib.unsafeFixedPointMul(statement.matchResult.price, baseAmount);
        vm.expectRevert(IDarkpool.VerificationFailed.selector);
        darkpoolRealVerifier.processMalleableAtomicMatchSettle(
            quoteAmount, baseAmount, txSender, internalPartyPayload, statement, proofs, linkingProofs
        );
    }

    /// @notice Test settling a malleable match with a duplicate public blinder share
    function test_settleMalleableAtomicMatch_duplicateBlinder() public {
        // Create a wallet using the public blinder
        (ValidWalletCreateStatement memory createStatement, PlonkProof memory createProof) = createWalletCalldata();
        darkpool.createWallet(createStatement, createProof);
        BN254.ScalarField publicBlinder = createStatement.publicShares[createStatement.publicShares.length - 1];

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = genMalleableMatchCalldata(ExternalMatchDirection.InternalPartySell, merkleRoot);
        statement.internalPartyPublicShares[statement.internalPartyPublicShares.length - 1] = publicBlinder;

        // Should fail
        uint256 baseAmount = statement.matchResult.minBaseAmount;
        uint256 quoteAmount = FixedPointLib.unsafeFixedPointMul(statement.matchResult.price, baseAmount) + 1;
        vm.expectRevert(NullifierSetLib.NullifierAlreadySpent.selector);
        darkpool.processMalleableAtomicMatchSettle(
            quoteAmount, baseAmount, txSender, internalPartyPayload, statement, proofs, linkingProofs
        );
    }

    /// @notice Test settling a malleable match with a spent nullifier
    function test_settleMalleableAtomicMatch_spentNullifier() public {
        // Spend the nullifier with an update wallet
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        BN254.ScalarField nullifier = randomScalar();

        // Update a wallet using the nullifier
        (
            bytes memory newSharesCommitmentSig,
            ValidWalletUpdateStatement memory updateStatement,
            PlonkProof memory updateProof
        ) = updateWalletCalldata();
        updateStatement.previousNullifier = nullifier;
        updateStatement.merkleRoot = merkleRoot;
        TransferAuthorization memory transferAuthorization = emptyTransferAuthorization();
        darkpool.updateWallet(newSharesCommitmentSig, transferAuthorization, updateStatement, updateProof);

        // Call the malleable match method with the nullifier
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = genMalleableMatchCalldata(ExternalMatchDirection.InternalPartySell, merkleRoot);

        // Use the nullifier
        internalPartyPayload.validReblindStatement.originalSharesNullifier = nullifier;

        // Should fail
        uint256 baseAmount = statement.matchResult.minBaseAmount;
        uint256 quoteAmount = FixedPointLib.unsafeFixedPointMul(statement.matchResult.price, baseAmount);
        vm.expectRevert(NullifierSetLib.NullifierAlreadySpent.selector);
        darkpool.processMalleableAtomicMatchSettle(
            quoteAmount, baseAmount, txSender, internalPartyPayload, statement, proofs, linkingProofs
        );
    }

    /// @notice Test settling a malleable match with an invalid Merkle root
    function test_settleMalleableAtomicMatch_invalidMerkleRoot() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = randomScalar();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = genMalleableMatchCalldata(ExternalMatchDirection.InternalPartySell, merkleRoot);

        // Should fail
        uint256 baseAmount = statement.matchResult.minBaseAmount;
        uint256 quoteAmount = FixedPointLib.unsafeFixedPointMul(statement.matchResult.price, baseAmount);
        vm.expectRevert(WalletOperations.MerkleRootNotInHistory.selector);
        darkpool.processMalleableAtomicMatchSettle(
            quoteAmount, baseAmount, txSender, internalPartyPayload, statement, proofs, linkingProofs
        );
    }

    /// @notice Test settling a malleable match with a non-zero tx value, when the trade is not on the native asset
    function test_settleMalleableAtomicMatch_nonNativeAssetWithEthValue() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = genMalleableMatchCalldata(ExternalMatchDirection.InternalPartySell, merkleRoot);

        // Should fail
        uint256 baseAmount = statement.matchResult.minBaseAmount;
        uint256 quoteAmount = FixedPointLib.unsafeFixedPointMul(statement.matchResult.price, baseAmount);
        vm.expectRevert(IDarkpool.InvalidETHValue.selector);
        darkpool.processMalleableAtomicMatchSettle{ value: 1 ether }(
            quoteAmount, baseAmount, txSender, internalPartyPayload, statement, proofs, linkingProofs
        );
    }

    /// @notice Test settling a malleable match with too small of an ETH value for a native asset sell
    function test_settleMalleableAtomicMatch_nativeAssetSell_valueTooSmall() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = genMalleableMatchCalldata(ExternalMatchDirection.InternalPartyBuy, merkleRoot);
        statement.matchResult.baseMint = DarkpoolConstants.NATIVE_TOKEN_ADDRESS;

        // Should fail
        uint256 value = statement.matchResult.minBaseAmount - 1;
        vm.deal(txSender, value);

        vm.startBroadcast(txSender);
        uint256 baseAmount = statement.matchResult.minBaseAmount;
        uint256 quoteAmount = FixedPointLib.unsafeFixedPointMul(statement.matchResult.price, baseAmount);
        vm.expectRevert(ExternalTransferLib.InvalidDepositAmount.selector);
        darkpool.processMalleableAtomicMatchSettle{ value: value }(
            quoteAmount, baseAmount, txSender, internalPartyPayload, statement, proofs, linkingProofs
        );
        vm.stopBroadcast();
    }

    /// @notice Test settling a malleable match that uses an incorrect protocol fee rate
    function test_settleMalleableAtomicMatch_incorrectProtocolFeeRate() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = genMalleableMatchCalldata(ExternalMatchDirection.InternalPartySell, merkleRoot);

        // Modify the fee on one of the parties
        bytes4 revertMessage;
        if (vm.randomBool()) {
            // Modify the fee on the internal party's side
            statement.internalFeeRates.protocolFeeRate = randomTakeRate();
            revertMessage = IDarkpool.InvalidProtocolFeeRate.selector;
        } else {
            // Modify the fee on the external party's side
            statement.externalFeeRates.protocolFeeRate = randomTakeRate();
            revertMessage = IDarkpool.InvalidProtocolFeeRate.selector;
        }

        // Should fail
        uint256 baseAmount = statement.matchResult.minBaseAmount;
        uint256 quoteAmount = FixedPointLib.unsafeFixedPointMul(statement.matchResult.price, baseAmount);
        vm.expectRevert(revertMessage);
        darkpool.processMalleableAtomicMatchSettle(
            quoteAmount, baseAmount, txSender, internalPartyPayload, statement, proofs, linkingProofs
        );
    }

    /// @notice Tests settling a malleable match with with a quote amount out of range
    function test_settleMalleableAtomicMatch_quoteAmountOutOfRange() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = genMalleableMatchCalldata(ExternalMatchDirection.InternalPartySell, merkleRoot);

        // Should fail
        uint256 baseAmount = statement.matchResult.minBaseAmount;
        uint256 quoteAmount;
        if (vm.randomBool()) {
            uint256 minBase = statement.matchResult.minBaseAmount;
            uint256 minQuote = FixedPointLib.unsafeFixedPointMul(statement.matchResult.price, minBase);
            quoteAmount = minQuote - 1;
        } else {
            uint256 maxBase = statement.matchResult.maxBaseAmount;
            uint256 maxQuote = FixedPointLib.unsafeFixedPointMul(statement.matchResult.price, maxBase);
            quoteAmount = maxQuote + 1;
        }

        vm.expectRevert(TypesLib.QuoteAmountOutOfBounds.selector);
        darkpool.processMalleableAtomicMatchSettle(
            quoteAmount, baseAmount, txSender, internalPartyPayload, statement, proofs, linkingProofs
        );
    }

    /// @notice Tests settling a malleable match with price improvement that goes to the external user
    function test_settleMalleableAtomicMatch_priceImprovementToExternalUser() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = genMalleableMatchCalldata(ExternalMatchDirection.InternalPartySell, merkleRoot);

        // Should fail
        ExternalMatchResult memory matchRes = sampleExternalMatch(statement.matchResult);
        uint256 baseAmount = matchRes.baseAmount;
        uint256 refQuoteAmount = FixedPointLib.unsafeFixedPointMul(statement.matchResult.price, baseAmount);
        uint256 quoteAmount;

        bool isSell = matchRes.direction == ExternalMatchDirection.InternalPartyBuy;
        if (isSell) {
            // Sell side, the external party tries to increase the price above the reference price
            quoteAmount = refQuoteAmount + 1;
        } else {
            // Buy side, the external party tries to reduce the price below the reference price
            quoteAmount = refQuoteAmount - 1;
        }

        vm.expectRevert(TypesLib.QuoteAmountOutOfBounds.selector);
        darkpool.processMalleableAtomicMatchSettle(
            quoteAmount, baseAmount, txSender, internalPartyPayload, statement, proofs, linkingProofs
        );
    }

    // --- Helper Functions --- //

    /// @notice Sample a random base amount between the bounds on a `BoundedMatchResult`
    function sampleBaseAmount(BoundedMatchResult memory matchResult) internal returns (uint256) {
        uint256 min = matchResult.minBaseAmount;
        uint256 max = matchResult.maxBaseAmount;
        return randomUint(min, max);
    }

    /// @notice Sample an external match from a bounded match
    function sampleExternalMatch(BoundedMatchResult memory matchResult) internal returns (ExternalMatchResult memory) {
        uint256 baseAmt = sampleBaseAmount(matchResult);
        uint256 quoteAmt = FixedPointLib.unsafeFixedPointMul(matchResult.price, baseAmt);
        return TypesLib.buildExternalMatchResult(quoteAmt, baseAmt, matchResult);
    }

    /// @notice Fund the external party and darkpool given a match result
    function fundExternalPartyAndDarkpool(ExternalMatchResult memory externalMatchResult) internal {
        (address sellMint, uint256 sellAmt) = TypesLib.externalPartySellMintAmount(externalMatchResult);
        (address buyMint, uint256 buyAmt) = TypesLib.externalPartyBuyMintAmount(externalMatchResult);

        // Fund the external party and darkpool
        fundExternalParty(sellMint, sellAmt);
        fundDarkpool(buyMint, buyAmt);

        // Approve the darkpool to spend the tokens
        if (!DarkpoolConstants.isNativeToken(sellMint)) {
            ERC20Mock sellToken = ERC20Mock(sellMint);
            vm.startBroadcast(txSender);
            sellToken.approve(address(darkpool), sellAmt);
            vm.stopBroadcast();
        }
    }

    /// @notice Fund the external party with the given amount of the given token
    function fundExternalParty(address token, uint256 amt) internal {
        if (DarkpoolConstants.isNativeToken(token)) {
            vm.deal(txSender, amt);
        } else {
            ERC20Mock erc20 = ERC20Mock(token);
            erc20.mint(txSender, amt);
        }
    }

    /// @notice Fund the darkpool with the given amount of the given token
    function fundDarkpool(address token, uint256 amt) internal {
        if (DarkpoolConstants.isNativeToken(token)) {
            weth.mint(address(darkpool), amt);
        } else {
            ERC20Mock erc20 = ERC20Mock(token);
            erc20.mint(address(darkpool), amt);
        }
    }

    /// @notice Generate the calldata for settling a malleable atomic match, using the testing contracts
    /// @param direction The direction of the match
    /// @param merkleRoot The merkle root of the darkpool
    /// @return internalPartyPayload The internal party payload
    /// @return statement The statement
    /// @return proofs The proofs
    /// @return linkingProofs The linking proofs
    function genMalleableMatchCalldata(
        ExternalMatchDirection direction,
        BN254.ScalarField merkleRoot
    )
        internal
        returns (
            PartyMatchPayload memory,
            ValidMalleableMatchSettleAtomicStatement memory,
            MalleableMatchAtomicProofs memory,
            MatchAtomicLinkingProofs memory
        )
    {
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleMalleableAtomicMatchCalldata(direction, merkleRoot);

        // Modify the pair to be the quote and base token setup by the test harness
        statement.matchResult.quoteMint = address(quoteToken);
        statement.matchResult.baseMint = address(baseToken);
        statement.relayerFeeAddress = relayerFeeAddr;

        return (internalPartyPayload, statement, proofs, linkingProofs);
    }

    /// @notice Submit a malleable atomic match and check the token flows
    function verifyMalleableAtomicMatch(
        address receiver,
        uint256 quoteAmount,
        uint256 baseAmount,
        PartyMatchPayload memory internalPartyPayload,
        ValidMalleableMatchSettleAtomicStatement memory statement,
        MalleableMatchAtomicProofs memory proofs,
        MatchAtomicLinkingProofs memory linkingProofs
    )
        internal
    {
        // Get the balances before the match
        (
            uint256 userBaseBalance1,
            uint256 userQuoteBalance1,
            uint256 darkpoolBaseBalance1,
            uint256 darkpoolQuoteBalance1,
            uint256 relayerBaseBalance1,
            uint256 relayerQuoteBalance1,
            uint256 protocolBaseBalance1,
            uint256 protocolQuoteBalance1
        ) = getPartyBalances(statement.matchResult.baseMint);

        // Submit the match
        uint256 ethValue = 0;
        bool isNative = DarkpoolConstants.isNativeToken(statement.matchResult.baseMint);
        bool externalPartySells = statement.matchResult.direction == ExternalMatchDirection.InternalPartyBuy;
        if (isNative && externalPartySells) {
            ethValue = baseAmount;
        }

        vm.startBroadcast(txSender);
        darkpool.processMalleableAtomicMatchSettle{ value: ethValue }(
            quoteAmount, baseAmount, receiver, internalPartyPayload, statement, proofs, linkingProofs
        );
        vm.stopBroadcast();

        // Get the balances after the match
        (
            uint256 userBaseBalance2,
            uint256 userQuoteBalance2,
            uint256 darkpoolBaseBalance2,
            uint256 darkpoolQuoteBalance2,
            uint256 relayerBaseBalance2,
            uint256 relayerQuoteBalance2,
            uint256 protocolBaseBalance2,
            uint256 protocolQuoteBalance2
        ) = getPartyBalances(statement.matchResult.baseMint);

        ExternalMatchResult memory externalMatchResult =
            TypesLib.buildExternalMatchResult(quoteAmount, baseAmount, statement.matchResult);

        // Check the token flows
        uint256 baseAmt = externalMatchResult.baseAmount;
        uint256 quoteAmt = externalMatchResult.quoteAmount;

        if (externalMatchResult.direction == ExternalMatchDirection.InternalPartySell) {
            FeeTake memory externalPartyFees = statement.externalFeeRates.computeFeeTake(baseAmt);

            // External party buys the base, sells the quote
            assertEq(userBaseBalance2, userBaseBalance1 + baseAmt - externalPartyFees.total());
            assertEq(userQuoteBalance2, userQuoteBalance1 - quoteAmt);
            assertEq(darkpoolBaseBalance2, darkpoolBaseBalance1 - baseAmt);
            assertEq(darkpoolQuoteBalance2, darkpoolQuoteBalance1 + quoteAmt);
            assertEq(relayerBaseBalance2, relayerBaseBalance1 + externalPartyFees.relayerFee);
            assertEq(relayerQuoteBalance2, relayerQuoteBalance1);
            assertEq(protocolBaseBalance2, protocolBaseBalance1 + externalPartyFees.protocolFee);
            assertEq(protocolQuoteBalance2, protocolQuoteBalance1);
        } else {
            FeeTake memory externalPartyFees = statement.externalFeeRates.computeFeeTake(quoteAmt);

            // External party buys the quote, sells the base
            assertEq(userBaseBalance2, userBaseBalance1 - baseAmt);
            assertEq(userQuoteBalance2, userQuoteBalance1 + quoteAmt - externalPartyFees.total());
            assertEq(darkpoolBaseBalance2, darkpoolBaseBalance1 + baseAmt);
            assertEq(darkpoolQuoteBalance2, darkpoolQuoteBalance1 - quoteAmt);
            assertEq(relayerBaseBalance2, relayerBaseBalance1);
            assertEq(relayerQuoteBalance2, relayerQuoteBalance1 + externalPartyFees.relayerFee);
            assertEq(protocolBaseBalance2, protocolBaseBalance1);
            assertEq(protocolQuoteBalance2, protocolQuoteBalance1 + externalPartyFees.protocolFee);
        }
    }

    /// @notice Get the balances of the user, darkpool, relayer, and protocol
    function getPartyBalances(address baseMint)
        internal
        view
        returns (
            uint256 userBaseBalance,
            uint256 userQuoteBalance,
            uint256 darkpoolBaseBalance,
            uint256 darkpoolQuoteBalance,
            uint256 relayerBaseBalance,
            uint256 relayerQuoteBalance,
            uint256 protocolBaseBalance,
            uint256 protocolQuoteBalance
        )
    {
        if (DarkpoolConstants.isNativeToken(baseMint)) {
            (userBaseBalance, userQuoteBalance) = etherQuoteBalances(txSender);
            (darkpoolBaseBalance, darkpoolQuoteBalance) = wethQuoteBalances(address(darkpool));
            (relayerBaseBalance, relayerQuoteBalance) = etherQuoteBalances(relayerFeeAddr);
            (protocolBaseBalance, protocolQuoteBalance) = etherQuoteBalances(protocolFeeAddr);
        } else {
            (userBaseBalance, userQuoteBalance) = baseQuoteBalances(txSender);
            (darkpoolBaseBalance, darkpoolQuoteBalance) = baseQuoteBalances(address(darkpool));
            (relayerBaseBalance, relayerQuoteBalance) = baseQuoteBalances(relayerFeeAddr);
            (protocolBaseBalance, protocolQuoteBalance) = baseQuoteBalances(protocolFeeAddr);
        }
    }
}

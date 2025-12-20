// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import { DarkpoolUniswapExecutor } from "renegade-connectors/DarkpoolUniswapExecutor.sol";
import { Vm } from "forge-std/Vm.sol";
import { UniswapXExecutorProxy } from "darkpoolv1-proxies/UniswapXExecutorProxy.sol";
import { IDarkpoolUniswapExecutor } from "darkpoolv1-interfaces/IDarkpoolUniswapExecutor.sol";
import { IReactorCallback } from "uniswapx/interfaces/IReactorCallback.sol";
import { ResolvedOrder, SignedOrder } from "uniswapx/base/ReactorStructs.sol";
import { ERC20 } from "solmate/src/tokens/ERC20.sol";
import { DarkpoolTestBase } from "test/darkpool/v1/DarkpoolTestBase.sol";
import { BN254 } from "solidity-bn254/BN254.sol";

import { PriorityOrderReactor } from "uniswapx/reactors/PriorityOrderReactor.sol";
import { PriorityOrderLib } from "uniswapx/lib/PriorityOrderLib.sol";
import { PriorityFeeLib } from "uniswapx/lib/PriorityFeeLib.sol";
import {
    PriorityOrder,
    OrderInfo,
    PriorityInput,
    PriorityOutput,
    PriorityCosignerData
} from "uniswapx/lib/PriorityOrderLib.sol";
import { PermitSignature } from "uniswapx-test/util/PermitSignature.sol";
import { IValidationCallback } from "uniswapx/interfaces/IValidationCallback.sol";
import {
    PartyMatchPayload,
    MatchAtomicProofs,
    MatchAtomicLinkingProofs,
    ExternalMatchDirection,
    ExternalMatchResult
} from "darkpoolv1-types/Settlement.sol";
import { ValidMatchSettleAtomicStatement } from "darkpoolv1-lib/PublicInputs.sol";
import { Permit2Lib } from "uniswapx/lib/Permit2Lib.sol";
import { PermitHash } from "permit2/src/libraries/PermitHash.sol";
import { ISignatureTransfer } from "permit2/src/interfaces/ISignatureTransfer.sol";
import { TypesLib } from "darkpoolv1-types/TypesLib.sol";
import { FeeTake } from "darkpoolv1-types/Fees.sol";

/// @title DarkpoolUniswapExecutorTest
/// @notice Test contract for the DarkpoolUniswapExecutor
/// @dev This contract tests the DarkpoolUniswapExecutor contract
contract DarkpoolUniswapExecutorTest is DarkpoolTestBase, PermitSignature {
    using Permit2Lib for ResolvedOrder;
    using PriorityOrderLib for PriorityOrder;
    using PriorityFeeLib for PriorityInput;
    using PriorityFeeLib for PriorityOutput[];
    using PermitHash for ISignatureTransfer.PermitTransferFrom;
    using TypesLib for FeeTake;

    PriorityOrderReactor reactor;
    IDarkpoolUniswapExecutor executor;

    /// @notice Sets up the test environment
    /// @dev For now we test against a `PriorityOrderReactor`, which is the flavor deployed on Base
    function setUp() public override {
        // Deploy the darkpool and tokens
        super.setUp();
        address protocolFeeOwner = vm.randomAddress();

        // Deploy the reactor
        reactor = new PriorityOrderReactor(permit2, protocolFeeOwner);

        // Initialize the UniswapXExecutorProxy
        DarkpoolUniswapExecutor executorImpl = new DarkpoolUniswapExecutor();
        UniswapXExecutorProxy executorProxy =
            new UniswapXExecutorProxy(address(executorImpl), darkpoolOwner, address(darkpool), address(reactor));
        executor = IDarkpoolUniswapExecutor(address(executorProxy));

        // Whitelist this test contract as a solver for execution tests
        vm.prank(darkpoolOwner);
        executor.whitelistSolver(address(this));
    }

    /// @notice Test that the owner is set correctly
    function testOwner() public view {
        // Check that the owner is set correctly
        assertEq(executor.owner(), darkpoolOwner);
    }

    /// @notice Test that unauthorized callers are rejected in reactor callback
    function test_reactorCallback_unauthorizedCaller() public {
        bytes memory callbackData = abi.encodeWithSelector(
            darkpool.processAtomicMatchSettle.selector, address(0), address(0), address(0), address(0), address(0)
        );

        ResolvedOrder[] memory resolvedOrders = new ResolvedOrder[](0);

        vm.expectRevert(DarkpoolUniswapExecutor.UnauthorizedCaller.selector);
        IReactorCallback(address(executor)).reactorCallback(resolvedOrders, callbackData);
    }

    /// @notice Test that non-solver addresses cannot call executeAtomicMatchSettle
    function test_executeAtomicMatchSettle_callerNotSolver() public {
        Vm.Wallet memory userWallet = randomEthereumWallet();

        // Setup dummy parameters
        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: address(baseToken),
            quoteAmount: 1_000_000,
            baseAmount: 5_000_000,
            direction: ExternalMatchDirection.InternalPartySell
        });

        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        ) = settleAtomicMatchCalldataWithMatchResult(merkleRoot, matchResult);
        FeeTake memory feeTake = statement.externalPartyFees;
        SignedOrder memory signedOrder = _createSignedOrder(matchResult, feeTake, userWallet);

        // Create a non-whitelisted address to test with
        address nonSolver = vm.randomAddress();

        // Expect revert when calling without being whitelisted
        vm.prank(nonSolver);
        vm.expectRevert(); // AccessControl will revert with its own error
        executor.executeAtomicMatchSettle(signedOrder, internalPartyPayload, statement, proofs, linkingProofs);
    }

    /// @notice Test atomic match settlement through executeAtomicMatchSettle - external party buy side
    function test_executeAtomicMatchSettle_externalPartyBuySide() public {
        Vm.Wallet memory userWallet = randomEthereumWallet();

        // Setup tokens
        uint256 quoteAmt = 1_000_000;
        uint256 baseAmt = 5_000_000;
        quoteToken.mint(userWallet.addr, quoteAmt);
        baseToken.mint(address(darkpool), baseAmt);

        // Setup the match
        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: address(baseToken),
            quoteAmount: quoteAmt,
            baseAmount: baseAmt,
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
        FeeTake memory feeTake = statement.externalPartyFees;
        SignedOrder memory signedOrder = _createSignedOrder(matchResult, feeTake, userWallet);

        (uint256 userBasePreBalance, uint256 userQuotePreBalance) = baseQuoteBalances(userWallet.addr);
        (uint256 darkpoolBasePreBalance, uint256 darkpoolQuotePreBalance) = baseQuoteBalances(address(darkpool));

        // Approve the permit2 contract to spend the quote token
        vm.startBroadcast(userWallet.addr);
        quoteToken.approve(address(permit2), quoteAmt);
        vm.stopBroadcast();

        // Call executeAtomicMatchSettle
        executor.executeAtomicMatchSettle(signedOrder, internalPartyPayload, statement, proofs, linkingProofs);

        // Check the balance updates
        (uint256 userBasePostBalance, uint256 userQuotePostBalance) = baseQuoteBalances(userWallet.addr);
        (uint256 darkpoolBasePostBalance, uint256 darkpoolQuotePostBalance) = baseQuoteBalances(address(darkpool));

        uint256 totalFee = feeTake.total();
        assertEq(userBasePostBalance, userBasePreBalance + baseAmt - totalFee);
        assertEq(userQuotePostBalance, userQuotePreBalance - quoteAmt);
        assertEq(darkpoolBasePostBalance, darkpoolBasePreBalance - baseAmt);
        assertEq(darkpoolQuotePostBalance, darkpoolQuotePreBalance + quoteAmt);
    }

    /// @notice Test atomic match settlement through executeAtomicMatchSettle - external party sell side
    function test_executeAtomicMatchSettle_externalPartySellSide() public {
        Vm.Wallet memory userWallet = randomEthereumWallet();

        // Setup tokens
        uint256 quoteAmt = 1_000_000;
        uint256 baseAmt = 5_000_000;
        baseToken.mint(userWallet.addr, baseAmt);
        quoteToken.mint(address(darkpool), quoteAmt);

        // Setup the match
        ExternalMatchResult memory matchResult = ExternalMatchResult({
            quoteMint: address(quoteToken),
            baseMint: address(baseToken),
            quoteAmount: quoteAmt,
            baseAmount: baseAmt,
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
        FeeTake memory feeTake = statement.externalPartyFees;
        SignedOrder memory signedOrder = _createSignedOrder(matchResult, feeTake, userWallet);

        (uint256 userBasePreBalance, uint256 userQuotePreBalance) = baseQuoteBalances(userWallet.addr);
        (uint256 darkpoolBasePreBalance, uint256 darkpoolQuotePreBalance) = baseQuoteBalances(address(darkpool));

        // Approve the permit2 contract to spend the quote token
        vm.startBroadcast(userWallet.addr);
        baseToken.approve(address(permit2), baseAmt);
        vm.stopBroadcast();

        // Call executeAtomicMatchSettle
        executor.executeAtomicMatchSettle(signedOrder, internalPartyPayload, statement, proofs, linkingProofs);

        // Check the balance updates
        (uint256 userBasePostBalance, uint256 userQuotePostBalance) = baseQuoteBalances(userWallet.addr);
        (uint256 darkpoolBasePostBalance, uint256 darkpoolQuotePostBalance) = baseQuoteBalances(address(darkpool));

        uint256 totalFee = feeTake.total();
        assertEq(userBasePostBalance, userBasePreBalance - baseAmt);
        assertEq(userQuotePostBalance, userQuotePreBalance + quoteAmt - totalFee);
        assertEq(darkpoolBasePostBalance, darkpoolBasePreBalance + baseAmt);
        assertEq(darkpoolQuotePostBalance, darkpoolQuotePreBalance - quoteAmt);
    }

    // -----------
    // | Helpers |
    // -----------

    // --- UniswapX Helpers --- //

    /// @notice Creates a dummy signed priority order for a given match result, simulating a user order for UniswapX
    /// execution tests.
    /// @param matchResult The ExternalMatchResult specifying the quote/base tokens and amounts for the order.
    /// @param userWallet The wallet of the user who is signing the order.
    /// @return A SignedOrder struct representing the signed priority order.
    function _createSignedOrder(
        ExternalMatchResult memory matchResult,
        FeeTake memory feeTake,
        Vm.Wallet memory userWallet
    )
        internal
        returns (SignedOrder memory)
    {
        // Create the input
        address inputToken;
        address outputToken;
        uint256 inputAmount;
        uint256 outputAmount;

        if (matchResult.direction == ExternalMatchDirection.InternalPartySell) {
            inputToken = address(quoteToken);
            outputToken = address(baseToken);
            inputAmount = matchResult.quoteAmount;
            outputAmount = matchResult.baseAmount;
        } else {
            inputToken = address(baseToken);
            outputToken = address(quoteToken);
            inputAmount = matchResult.baseAmount;
            outputAmount = matchResult.quoteAmount;
        }

        PriorityInput memory input =
            PriorityInput({ token: ERC20(inputToken), amount: inputAmount, mpsPerPriorityFeeWei: 0 });

        // Create the output
        uint256 totalFee = feeTake.total();
        PriorityOutput memory output = PriorityOutput({
            token: outputToken,
            amount: outputAmount - totalFee,
            mpsPerPriorityFeeWei: 0,
            recipient: userWallet.addr
        });
        PriorityOutput[] memory outputs = new PriorityOutput[](1);
        outputs[0] = output;

        // Create the order
        uint256 nonce = randomUint();
        OrderInfo memory info = OrderInfo({
            reactor: reactor,
            swapper: userWallet.addr,
            nonce: nonce,
            deadline: block.timestamp + 1 days,
            additionalValidationContract: IValidationCallback(address(0)),
            additionalValidationData: ""
        });

        // Create the cosigner data
        PriorityCosignerData memory cosignerData = PriorityCosignerData({ auctionTargetBlock: block.number });
        bytes memory cosignature = bytes("");

        // Create the order
        PriorityOrder memory order = PriorityOrder({
            info: info,
            cosigner: address(0),
            auctionStartBlock: block.number,
            baselinePriorityFeeWei: 0,
            input: input,
            outputs: outputs,
            cosignerData: cosignerData,
            cosignature: cosignature
        });

        // Create the permit signature
        SignedOrder memory signedOrder = _signPriorityOrder(userWallet, order);
        return signedOrder;
    }

    /// @notice Constructs and signs a PriorityOrder for the given user and match result, returning a SignedOrder with a
    /// valid Permit2 signature.
    /// @param userWallet The wallet of the user who is signing the order.
    /// @param order The PriorityOrder to sign.
    /// @return signedOrder The SignedOrder with a valid Permit2 signature.
    function _signPriorityOrder(
        Vm.Wallet memory userWallet,
        PriorityOrder memory order
    )
        internal
        view
        returns (SignedOrder memory signedOrder)
    {
        uint256 inputAmount = order.input.amount;
        address inputToken = address(order.input.token);
        ISignatureTransfer.PermitTransferFrom memory permit = ISignatureTransfer.PermitTransferFrom({
            permitted: ISignatureTransfer.TokenPermissions({ token: inputToken, amount: inputAmount }),
            nonce: order.info.nonce,
            deadline: order.info.deadline
        });

        bytes32 witness = order.hash();
        bytes32 domainSeparator = permit2.DOMAIN_SEPARATOR();
        bytes memory sig = getPermitWitnessTransferSignature(
            permit, address(reactor), userWallet.privateKey, PRIORITY_ORDER_TYPE_HASH, witness, domainSeparator
        );

        // Create the signed order
        signedOrder = SignedOrder({ order: abi.encode(order), sig: sig });
        return signedOrder;
    }
}

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Vm } from "forge-std/Vm.sol";
import { ERC20Mock } from "oz-contracts/mocks/token/ERC20Mock.sol";
import { DarkpoolV2TestBase } from "./DarkpoolV2TestBase.sol";

import { BN254 } from "solidity-bn254/BN254.sol";
import { BN254Helpers } from "renegade-lib/verifier/BN254Helpers.sol";
import { MerkleMountainLib } from "renegade-lib/merkle/MerkleMountain.sol";
import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";

import { ObligationBundle, ObligationType } from "darkpoolv2-types/settlement/ObligationBundle.sol";
import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";
import { Intent, IntentPublicShare } from "darkpoolv2-types/Intent.sol";
import { PostMatchBalanceShare } from "darkpoolv2-types/Balance.sol";
import { PartialCommitment } from "darkpoolv2-types/PartialCommitment.sol";
import { DarkpoolState } from "darkpoolv2-contracts/DarkpoolV2.sol";

import { PlonkProof, LinkingProof } from "renegade-lib/verifier/Types.sol";
import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { FeeRate } from "darkpoolv2-types/Fee.sol";

contract DarkpoolV2TestUtils is DarkpoolV2TestBase {
    using FixedPointLib for FixedPoint;
    using MerkleMountainLib for MerkleMountainLib.MerkleMountainRange;

    // Test wallets
    Vm.Wallet internal intentOwner;
    Vm.Wallet internal oneTimeOwner;
    // Party 0 in a simulated trade
    Vm.Wallet internal party0;
    // Internal party in a simulated trade (alias for party0)
    Vm.Wallet internal internalParty;
    // Party 1 in a simulated trade
    Vm.Wallet internal party1;
    // External party in a simulated trade (alias for party1)
    Vm.Wallet internal externalParty;
    Vm.Wallet internal executor;
    Vm.Wallet internal wrongSigner;

    // Bundled darkpool state for testing
    DarkpoolState internal darkpoolState;

    function setUp() public virtual override {
        super.setUp();

        // Create test wallets
        intentOwner = vm.createWallet("intent_owner");
        oneTimeOwner = vm.createWallet("one_time_owner");
        party0 = vm.createWallet("party0");
        party1 = vm.createWallet("party1");
        executor = vm.createWallet("executor");
        wrongSigner = vm.createWallet("wrong_signer");

        internalParty = party0;
        externalParty = party1;
        // Initialize the darkpoolState's merkle mountain range to match the darkpool contract's initialization
        // This ensures that roots stored during initialization are available in the test state
        MerkleMountainLib.initialize(darkpoolState.merkleMountainRange, DarkpoolConstants.DEFAULT_MERKLE_DEPTH);
    }

    // --- ERC20 Balances --- //

    /// @dev Capitalize a party for an intent
    function capitalizeParty(address addr, Intent memory intent) public {
        capitalizeParty(addr, intent.inToken, intent.amountIn);
    }

    /// @dev Capitalize a party for an obligation
    function capitalizeParty(address addr, SettlementObligation memory obligation) public {
        capitalizeParty(addr, obligation.inputToken, obligation.amountIn);
    }

    /// @dev Capitalize a party for a given token and amount
    function capitalizeParty(address addr, address token, uint256 amount) public {
        // Mint the tokens to the party
        ERC20Mock erc20 = ERC20Mock(token);
        erc20.mint(addr, amount);

        // Approve the permit2 contract to spend tokens and generate a permit2 approval for the darkpool
        vm.startPrank(addr);
        erc20.approve(address(permit2), type(uint256).max);
        uint48 expiration = uint48(block.timestamp + 1 days);
        permit2.approve(token, address(darkpool), type(uint160).max, expiration);
        permit2.approve(token, address(darkpoolRealVerifier), type(uint160).max, expiration);
        vm.stopPrank();
    }

    /// @dev Capitalize the external party for a given token and amount
    /// @dev External party uses direct ERC20 approval to darkpool (not permit2)
    function capitalizeExternalParty(address token, uint256 amount) public {
        // Mint the tokens to the party
        ERC20Mock erc20 = ERC20Mock(token);
        erc20.mint(externalParty.addr, amount);

        // Approve the darkpool contract directly (external party doesn't use permit2)
        vm.startPrank(externalParty.addr);
        erc20.approve(address(darkpool), type(uint256).max);
        erc20.approve(address(darkpoolRealVerifier), type(uint256).max);
        vm.stopPrank();
    }

    /// @dev Capitalize the external party for an obligation
    function capitalizeExternalParty(SettlementObligation memory obligation) public {
        capitalizeExternalParty(obligation.inputToken, obligation.amountIn);
    }

    // --- Fuzzing Helpers --- //

    /// @notice Generate a random price for a trade
    function randomPrice() internal returns (FixedPoint memory price) {
        // Min price of 0.01
        FixedPoint memory minPrice = FixedPointLib.integerToFixedPoint(1);
        minPrice = minPrice.divByInteger(100);
        FixedPoint memory maxPrice = FixedPointLib.integerToFixedPoint(1e12);

        price = randomFixedPoint(minPrice, maxPrice);
    }

    /// @notice Generate a random relayer fee rate
    function relayerFeeRate() internal view returns (FeeRate memory feeRate) {
        feeRate = FeeRate({ rate: relayerFeeRateFixedPoint, recipient: relayerFeeAddr });
    }

    /// @dev Generate a random set of intent shares
    /// @dev This is a set of 5 shares for the intent
    function randomIntentPublicShare() internal returns (IntentPublicShare memory) {
        return IntentPublicShare({
            inToken: randomScalar(),
            outToken: randomScalar(),
            owner: randomScalar(),
            minPrice: randomScalar(),
            amountIn: randomScalar()
        });
    }

    /// @dev Generate a random post match balance share
    function randomPostMatchBalanceShare() internal returns (PostMatchBalanceShare memory) {
        return PostMatchBalanceShare({
            relayerFeeBalance: randomScalar(),
            protocolFeeBalance: randomScalar(),
            amount: randomScalar()
        });
    }

    /// @dev Generate a random partial commitment
    function randomPartialCommitment() internal returns (PartialCommitment memory) {
        return PartialCommitment({ privateCommitment: randomScalar(), partialPublicCommitment: randomScalar() });
    }

    // --- Dummy Data --- //

    /// @dev Create an intent for an obligation
    function createIntentForObligation(SettlementObligation memory obligation) internal returns (Intent memory) {
        // Compute the min price
        FixedPoint memory minPrice =
            FixedPointLib.divIntegers(obligation.amountOut, obligation.amountIn).divByInteger(2);

        // Compute the input amount
        uint256 amountIn = randomUint(obligation.amountIn, 2 ** 100);
        return Intent({
            inToken: obligation.inputToken,
            outToken: obligation.outputToken,
            owner: intentOwner.addr,
            minPrice: minPrice,
            amountIn: amountIn
        });
    }

    /// @dev Create two obligations for a simulated trade with random price and amount
    /// @return obligation0 The first party's obligation (selling base, buying quote)
    /// @return obligation1 The second party's obligation (selling quote, buying base)
    function createTradeObligations()
        internal
        returns (
            SettlementObligation memory obligation0,
            SettlementObligation memory obligation1,
            FixedPoint memory price
        )
    {
        price = randomPrice();
        uint256 baseAmount = randomUint(0, 2 ** 50);
        uint256 quoteAmount = price.unsafeFixedPointMul(baseAmount);

        obligation0 = SettlementObligation({
            inputToken: address(baseToken),
            outputToken: address(quoteToken),
            amountIn: baseAmount,
            amountOut: quoteAmount
        });
        obligation1 = createMatchingObligation(obligation0);
    }

    /// @dev Create a matching obligation for a given obligation
    function createMatchingObligation(SettlementObligation memory obligation)
        internal
        pure
        returns (SettlementObligation memory)
    {
        return SettlementObligation({
            inputToken: obligation.outputToken,
            outputToken: obligation.inputToken,
            amountIn: obligation.amountOut,
            amountOut: obligation.amountIn
        });
    }

    /// @dev Build an obligation bundle from two obligations
    function buildObligationBundle(
        SettlementObligation memory obligation0,
        SettlementObligation memory obligation1
    )
        internal
        pure
        returns (ObligationBundle memory)
    {
        return ObligationBundle({ obligationType: ObligationType.PUBLIC, data: abi.encode(obligation0, obligation1) });
    }

    /// @dev Create a dummy PlonkProof
    function createDummyProof() internal pure returns (PlonkProof memory) {
        BN254.G1Point memory pointZero = BN254.P1();

        BN254.G1Point[5] memory wireComms;
        BN254.G1Point[5] memory quotientComms;
        BN254.ScalarField[5] memory wireEvals;
        BN254.ScalarField[4] memory sigmaEvals;

        for (uint256 i = 0; i < 5; i++) {
            wireComms[i] = pointZero;
            quotientComms[i] = pointZero;
            wireEvals[i] = BN254Helpers.ZERO;
            if (i < 4) {
                sigmaEvals[i] = BN254Helpers.ZERO;
            }
        }

        return PlonkProof({
            wireComms: wireComms,
            zComm: pointZero,
            quotientComms: quotientComms,
            wZeta: pointZero,
            wZetaOmega: pointZero,
            wireEvals: wireEvals,
            sigmaEvals: sigmaEvals,
            zBar: BN254Helpers.ZERO
        });
    }

    /// @dev Create a dummy LinkingProof
    function createDummyLinkingProof() internal pure returns (LinkingProof memory) {
        BN254.G1Point memory pointZero = BN254.P1();

        return LinkingProof({ linkingQuotientPolyComm: pointZero, linkingPolyOpening: pointZero });
    }
}

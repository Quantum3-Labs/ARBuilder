// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { Vm } from "forge-std/Vm.sol";

import { ERC20Mock } from "oz-contracts/mocks/token/ERC20Mock.sol";

import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";
import { Intent } from "darkpoolv2-types/Intent.sol";
import { SettlementBundle, PartyId } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { ObligationBundle } from "darkpoolv2-types/settlement/ObligationBundle.sol";
import { SettlementContext } from "darkpoolv2-types/settlement/SettlementContext.sol";

import { PublicIntentSettlementTestUtils } from "../native-settled-public-intents/Utils.sol";
import { PrivateIntentSettlementTestUtils } from "../native-settled-private-intents/Utils.sol";
import { RenegadeSettledPrivateIntentTestUtils } from "../renegade-settled-private-intents/Utils.sol";
import { SettlementTestUtils } from "../SettlementTestUtils.sol";

contract CrossBundleTypesTestUtils is
    PublicIntentSettlementTestUtils,
    PrivateIntentSettlementTestUtils,
    RenegadeSettledPrivateIntentTestUtils
{
    // Override the conflicting _createSettlementContext function from all base classes
    function _createSettlementContext()
        internal
        pure
        override(PublicIntentSettlementTestUtils, PrivateIntentSettlementTestUtils, RenegadeSettledPrivateIntentTestUtils)
        returns (SettlementContext memory context)
    {
        return PublicIntentSettlementTestUtils._createSettlementContext();
    }

    // --- Native Settled Public Intents --- //

    /// @dev Create a natively-settled public intent bundle
    function _createNativePublicIntentBundle(
        PartyId partyId,
        SettlementObligation memory obligation
    )
        internal
        returns (SettlementBundle memory bundle)
    {
        // Create a natively-settled public intent
        bool firstFill = vm.randomBool();
        Vm.Wallet memory partyWallet = _getPartyWallet(partyId);
        Intent memory intent = createIntentForObligation(obligation);
        intent.owner = partyWallet.addr;

        // If we want to simulate a subsequent fill, we need to trade against this intent to setup its state in
        // the darkpool. So we add an extra `obligation.amountIn` to the intent, which we'll trade into.
        if (!firstFill) {
            intent.amountIn += obligation.amountIn;
            _matchNativePublicIntent(partyId, obligation, intent);
        }

        // Capitalize the party and create the settlement bundle
        _capitalizeParty(partyId, obligation);
        bundle = createPublicIntentSettlementBundleWithSigners(
            intent, obligation, partyWallet.privateKey, executor.privateKey
        );
    }

    /// @dev Match a natively settled public intent to setup a subsequent fill test
    function _matchNativePublicIntent(
        PartyId partyId,
        SettlementObligation memory obligation,
        Intent memory intent
    )
        internal
    {
        PartyId oppositePartyId = _getOppositePartyId(partyId);
        Vm.Wallet memory oppositePartyWallet = _getPartyWallet(oppositePartyId);
        Vm.Wallet memory partyWallet = _getPartyWallet(partyId);

        // Create a matching obligation and intent
        SettlementObligation memory matchingObligation = createMatchingObligation(obligation);
        Intent memory matchingIntent = createIntentForObligation(matchingObligation);
        matchingIntent.owner = oppositePartyWallet.addr;

        // Fund the trader
        _capitalizeParty(partyId, obligation);
        _capitalizeParty(oppositePartyId, matchingObligation);

        // Create two settlement bundles
        SettlementBundle memory bundle0 = createPublicIntentSettlementBundleWithSigners(
            intent, obligation, partyWallet.privateKey, executor.privateKey
        );
        SettlementBundle memory bundle1 = createPublicIntentSettlementBundleWithSigners(
            matchingIntent, matchingObligation, oppositePartyWallet.privateKey, executor.privateKey
        );

        // Create an obligation bundle and settle the trade
        ObligationBundle memory obligationBundle = buildObligationBundle(obligation, matchingObligation);
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);
    }

    // --- Native Settled Private Intents --- //

    /// @dev Create a natively-settled private intent bundle
    function _createNativePrivateIntentBundle(
        PartyId partyId,
        SettlementObligation memory obligation
    )
        internal
        returns (SettlementBundle memory bundle)
    {
        bool isFirstFill = vm.randomBool();
        Vm.Wallet memory partyWallet = _getPartyWallet(partyId);
        bundle = createPrivateIntentSettlementBundle(isFirstFill, obligation, partyWallet);
        _capitalizeParty(partyId, obligation);
    }

    // --- Renegade Settled Private Intents --- //

    /// @dev Create a renegade settled private intent bundle
    function _createRenegadeSettledPrivateIntentBundle(
        PartyId partyId,
        SettlementObligation memory obligation
    )
        internal
        returns (SettlementBundle memory bundle)
    {
        bool isFirstFill = vm.randomBool();
        Vm.Wallet memory partyWallet = _getPartyWallet(partyId);
        bundle = createRenegadeSettledBundle(isFirstFill, obligation, partyWallet);

        // For renegade-settled bundles, the tokens this party contributes are managed internally by the darkpool
        // We mint these tokens to the darkpool so it can transfer them to the other party
        // (In production, these would come from the party's internal balance in the darkpool)
        ERC20Mock(obligation.inputToken).mint(address(darkpool), obligation.amountIn);
    }

    // --- General Helpers --- //

    /// @dev Get the wallet for a given party ID
    function _getPartyWallet(PartyId partyId) internal view returns (Vm.Wallet memory wallet) {
        if (partyId == PartyId.PARTY_0) {
            return party0;
        } else {
            return party1;
        }
    }

    /// @dev Get the opposite party ID
    function _getOppositePartyId(PartyId partyId) internal pure returns (PartyId oppositePartyId) {
        if (partyId == PartyId.PARTY_0) {
            return PartyId.PARTY_1;
        } else {
            return PartyId.PARTY_0;
        }
    }

    /// @dev Capitalize the given party for an obligation
    function _capitalizeParty(PartyId partyId, SettlementObligation memory obligation) internal {
        address partyAddr;
        if (partyId == PartyId.PARTY_0) {
            partyAddr = party0.addr;
        } else {
            partyAddr = party1.addr;
        }

        capitalizeParty(partyAddr, obligation);
    }

    /// @dev Get the input and output balance for a given address using the given obligation
    function _getInputOutputBalances(
        address addr,
        SettlementObligation memory obligation
    )
        internal
        view
        returns (uint256 inputBalance, uint256 outputBalance)
    {
        ERC20Mock inputToken = ERC20Mock(obligation.inputToken);
        ERC20Mock outputToken = ERC20Mock(obligation.outputToken);
        inputBalance = inputToken.balanceOf(addr);
        outputBalance = outputToken.balanceOf(addr);
    }
}

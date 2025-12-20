// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

/* solhint-disable func-name-mixedcase */

import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import { ObligationBundle } from "darkpoolv2-types/settlement/ObligationBundle.sol";
import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";
import { SettlementLib } from "darkpoolv2-lib/settlement/SettlementLib.sol";
import { SettlementContext } from "darkpoolv2-types/settlement/SettlementContext.sol";
import { DarkpoolContracts } from "darkpoolv2-contracts/DarkpoolV2.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";
import { IVerifier } from "darkpoolv2-interfaces/IVerifier.sol";
import { TestVerifierV2 } from "test-contracts/TestVerifierV2.sol";
import { PublicIntentSettlementTestUtils } from "./Utils.sol";

contract ObligationCompatibilityTest is PublicIntentSettlementTestUtils {
    // -----------
    // | Helpers |
    // -----------

    /// @notice Wrapper to convert memory to calldata for library call
    function _validateObligationBundle(ObligationBundle calldata bundle) public {
        SettlementContext memory settlementContext = _createSettlementContext();
        // Create a dummy verifier since it's not used in validateObligationBundle
        IVerifier dummyVerifier = new TestVerifierV2();
        DarkpoolContracts memory contracts = getSettlementContracts(dummyVerifier);
        SettlementLib.validateObligationBundle(bundle, settlementContext, darkpoolState, contracts);
    }

    /// @notice Helper that accepts memory and calls library with calldata
    function validateObligationBundleHelper(ObligationBundle memory bundle) internal {
        this._validateObligationBundle(bundle);
    }

    // ---------
    // | Tests |
    // ---------

    function test_compatibleObligations() public {
        // Create compatible obligations
        (SettlementObligation memory party0Obligation, SettlementObligation memory party1Obligation,) =
            createTradeObligations();
        ObligationBundle memory obligationBundle = buildObligationBundle(party0Obligation, party1Obligation);

        // Should not revert
        validateObligationBundleHelper(obligationBundle);
    }

    function test_incompatiblePairs() public {
        // Party 0: Selling base for quote
        (SettlementObligation memory party0Obligation, SettlementObligation memory party1Obligation,) =
            createTradeObligations();

        // Corrupt one of the obligations
        if (vm.randomBool()) {
            party0Obligation.outputToken = address(weth);
        } else {
            party1Obligation.inputToken = address(weth);
        }

        // Should revert with IncompatiblePairs
        ObligationBundle memory obligationBundle = buildObligationBundle(party0Obligation, party1Obligation);
        vm.expectRevert(IDarkpoolV2.IncompatiblePairs.selector);
        validateObligationBundleHelper(obligationBundle);
    }

    function test_incompatibleAmounts() public {
        (SettlementObligation memory party0Obligation, SettlementObligation memory party1Obligation,) =
            createTradeObligations();

        // Corrupt one of the obligations
        if (vm.randomBool()) {
            party0Obligation.amountOut *= 2;
        } else {
            party1Obligation.amountIn *= 2;
        }

        // Should revert with IncompatibleAmounts
        ObligationBundle memory obligationBundle = buildObligationBundle(party0Obligation, party1Obligation);
        vm.expectRevert(IDarkpoolV2.IncompatibleAmounts.selector);
        validateObligationBundleHelper(obligationBundle);
    }

    /// @notice Test that validation fails when the input or output amount is too large
    function test_invalidAmounts() public {
        (SettlementObligation memory party0Obligation, SettlementObligation memory party1Obligation,) =
            createTradeObligations();

        // Corrupt one of the obligations
        uint256 invalidAmount = 2 ** DarkpoolConstants.AMOUNT_BITS;
        if (vm.randomBool()) {
            party0Obligation.amountIn = invalidAmount;
            party1Obligation.amountOut = invalidAmount;
        } else {
            party0Obligation.amountIn = invalidAmount;
            party1Obligation.amountOut = invalidAmount;
        }

        // Should revert with AmountTooLarge
        ObligationBundle memory obligationBundle = buildObligationBundle(party0Obligation, party1Obligation);
        vm.expectRevert(abi.encodeWithSelector(IDarkpoolV2.AmountTooLarge.selector, 2 ** DarkpoolConstants.AMOUNT_BITS));
        validateObligationBundleHelper(obligationBundle);
    }
}

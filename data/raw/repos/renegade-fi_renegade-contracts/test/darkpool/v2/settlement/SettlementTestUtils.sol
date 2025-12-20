// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { SettlementContext } from "darkpoolv2-types/settlement/SettlementContext.sol";
import { SettlementContextLib } from "darkpoolv2-types/settlement/SettlementContext.sol";
import { ObligationBundle } from "darkpoolv2-types/settlement/ObligationBundle.sol";
import { SettlementBundle } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { FeeRate, FeeRateLib, FeeTake } from "darkpoolv2-types/Fee.sol";
import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";
import { FixedPoint } from "renegade-lib/FixedPoint.sol";
import { DarkpoolV2TestUtils } from "../DarkpoolV2TestUtils.sol";

/// @notice The expected differences in balances before and after settlement
struct ExpectedDifferences {
    /// @dev The expected difference in the party0 base balance
    int256 party0BaseChange;
    /// @dev The expected difference in the party0 quote balance
    int256 party0QuoteChange;
    /// @dev The expected difference in the party1 base balance
    int256 party1BaseChange;
    /// @dev The expected difference in the party1 quote balance
    int256 party1QuoteChange;
    /// @dev The expected difference in the darkpool base balance
    int256 darkpoolBaseChange;
    /// @dev The expected difference in the darkpool quote balance
    int256 darkpoolQuoteChange;
    /// @dev The expected difference in the relayer fee base balance
    int256 relayerFeeBaseChange;
    /// @dev The expected difference in the relayer fee quote balance
    int256 relayerFeeQuoteChange;
    /// @dev The expected difference in the protocol fee base balance
    int256 protocolFeeBaseChange;
    /// @dev The expected difference in the protocol fee quote balance
    int256 protocolFeeQuoteChange;
}

/// @notice Balance snapshot for an address
struct BalanceSnapshot {
    int256 base;
    int256 quote;
}

/// @notice All balance snapshots at a point in time
struct BalanceSnapshots {
    BalanceSnapshot party0;
    BalanceSnapshot party1;
    BalanceSnapshot darkpool;
    BalanceSnapshot relayerFee;
    BalanceSnapshot protocolFee;
}

/// @title Settlement Test Utils
/// @author Renegade Eng
/// @notice Utility functions for testing settlement
contract SettlementTestUtils is DarkpoolV2TestUtils {
    using FeeRateLib for FeeRate;

    /// @notice Create an empty expected differences struct
    function createEmptyExpectedDifferences() public pure returns (ExpectedDifferences memory expectedDifferences) {
        expectedDifferences = ExpectedDifferences({
            party0BaseChange: 0,
            party0QuoteChange: 0,
            party1BaseChange: 0,
            party1QuoteChange: 0,
            darkpoolBaseChange: 0,
            darkpoolQuoteChange: 0,
            relayerFeeBaseChange: 0,
            relayerFeeQuoteChange: 0,
            protocolFeeBaseChange: 0,
            protocolFeeQuoteChange: 0
        });
    }

    /// @notice Compute the fees due by a party in a match
    function computeMatchFees(SettlementObligation memory obligation)
        public
        view
        returns (FeeTake memory relayerFeeTake, FeeTake memory protocolFeeTake)
    {
        uint256 receiveAmount = obligation.amountOut;
        FeeRate memory relayerFeeRate = relayerFeeRate();
        relayerFeeTake = relayerFeeRate.computeFeeTake(obligation.outputToken, receiveAmount);

        // Build a protocol fee rate
        FixedPoint memory rate = darkpool.getProtocolFee(obligation.inputToken, obligation.outputToken);
        FeeRate memory protocolFeeRate = FeeRate({ rate: rate, recipient: protocolFeeAddr });
        protocolFeeTake = protocolFeeRate.computeFeeTake(obligation.outputToken, receiveAmount);
    }

    /// @notice Check the balances before and after settlement
    /// @param obligationBundle The obligation bundle
    /// @param party0SettlementBundle The settlement bundle for the first party
    /// @param party1SettlementBundle The settlement bundle for the second party
    /// @param expectedDifferences The expected differences in balances
    function checkBalancesBeforeAndAfterSettlement(
        ObligationBundle memory obligationBundle,
        SettlementBundle memory party0SettlementBundle,
        SettlementBundle memory party1SettlementBundle,
        ExpectedDifferences memory expectedDifferences
    )
        public
    {
        // Settle the match and record balances before and after
        // We have to break up these methods to avoid Yul stack overflows
        BalanceSnapshots memory preMatch = _captureBalances();
        darkpool.settleMatch(obligationBundle, party0SettlementBundle, party1SettlementBundle);
        BalanceSnapshots memory postMatch = _captureBalances();

        // Verify the balance changes
        _verifyBalanceChanges(preMatch, postMatch, expectedDifferences);
    }

    /// @notice Capture all balance snapshots
    function _captureBalances() internal view returns (BalanceSnapshots memory snapshots) {
        (snapshots.party0.base, snapshots.party0.quote) = baseQuoteBalancesSigned(party0.addr);
        (snapshots.party1.base, snapshots.party1.quote) = baseQuoteBalancesSigned(party1.addr);
        (snapshots.darkpool.base, snapshots.darkpool.quote) = baseQuoteBalancesSigned(address(darkpool));
        (snapshots.relayerFee.base, snapshots.relayerFee.quote) = baseQuoteBalancesSigned(relayerFeeAddr);
        (snapshots.protocolFee.base, snapshots.protocolFee.quote) = baseQuoteBalancesSigned(protocolFeeAddr);
    }

    /// @notice Verify balance changes between two snapshots match expected differences
    function _verifyBalanceChanges(
        BalanceSnapshots memory preMatch,
        BalanceSnapshots memory postMatch,
        ExpectedDifferences memory expectedDifferences
    )
        internal
        pure
    {
        assertEq(
            postMatch.party0.base - preMatch.party0.base, expectedDifferences.party0BaseChange, "party0 base change"
        );
        assertEq(
            postMatch.party0.quote - preMatch.party0.quote, expectedDifferences.party0QuoteChange, "party0 quote change"
        );
        assertEq(
            postMatch.party1.base - preMatch.party1.base, expectedDifferences.party1BaseChange, "party1 base change"
        );
        assertEq(
            postMatch.party1.quote - preMatch.party1.quote, expectedDifferences.party1QuoteChange, "party1 quote change"
        );
        assertEq(
            postMatch.darkpool.base - preMatch.darkpool.base,
            expectedDifferences.darkpoolBaseChange,
            "darkpool base change"
        );
        assertEq(
            postMatch.darkpool.quote - preMatch.darkpool.quote,
            expectedDifferences.darkpoolQuoteChange,
            "darkpool quote change"
        );
        assertEq(
            postMatch.relayerFee.base - preMatch.relayerFee.base,
            expectedDifferences.relayerFeeBaseChange,
            "relayer fee base change"
        );
        assertEq(
            postMatch.relayerFee.quote - preMatch.relayerFee.quote,
            expectedDifferences.relayerFeeQuoteChange,
            "relayer fee quote change"
        );
        assertEq(
            postMatch.protocolFee.base - preMatch.protocolFee.base,
            expectedDifferences.protocolFeeBaseChange,
            "protocol fee base change"
        );
        assertEq(
            postMatch.protocolFee.quote - preMatch.protocolFee.quote,
            expectedDifferences.protocolFeeQuoteChange,
            "protocol fee quote change"
        );
    }
}

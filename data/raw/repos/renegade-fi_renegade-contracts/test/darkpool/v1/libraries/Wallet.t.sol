// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import { BN254 } from "solidity-bn254/BN254.sol";
import { ExternalMatchResult, ExternalMatchDirection, OrderSettlementIndices } from "darkpoolv1-types/Settlement.sol";
import { WalletShare, WalletLib, BalanceShare } from "darkpoolv1-types/Wallet.sol";
import { FeeTakeRate, FeeTake } from "darkpoolv1-types/Fees.sol";
import { TypesLib } from "darkpoolv1-types/TypesLib.sol";
import { DarkpoolConstants } from "darkpoolv1-lib/Constants.sol";
import { WalletOperations } from "darkpoolv1-lib/WalletOperations.sol";
import { CalldataUtils } from "darkpoolv1-test/utils/CalldataUtils.sol";

contract WalletTest is CalldataUtils {
    using BN254 for BN254.ScalarField;
    using WalletLib for WalletShare;
    using TypesLib for FeeTakeRate;
    using TypesLib for FeeTake;

    /// @notice Test wallet serialization and deserialization
    function test_walletSerialization() public {
        // Generate random scalars
        BN254.ScalarField[] memory scalars = randomWalletShares();

        // Deserialize into a wallet then re-serialize
        WalletShare memory wallet = WalletLib.scalarDeserialize(scalars);
        BN254.ScalarField[] memory reserialized = wallet.scalarSerialize();

        // Verify all scalars match
        for (uint256 i = 0; i < DarkpoolConstants.N_WALLET_SHARES; i++) {
            assertEq(scalars[i], reserialized[i]);
        }
    }

    /// @notice Test the application of an external match to the wallet's shares
    function test_applyExternalMatchToShares_sellSide() public {
        // Generate a random wallet share and an external match result
        WalletShare memory walletShare = randomWalletShare();
        ExternalMatchResult memory matchResult = randomExternalMatchResult(ExternalMatchDirection.InternalPartySell);
        OrderSettlementIndices memory indices = randomOrderSettlementIndices();
        FeeTakeRate memory feeRates = randomFeeTakeRate();

        // Apply the match to the wallet's shares
        BN254.ScalarField[] memory oldShares = walletShare.scalarSerialize();
        BN254.ScalarField[] memory newShares =
            WalletOperations.applyExternalMatchToShares(oldShares, feeRates, matchResult, indices);

        // Verify the shares have been updated correctly
        WalletShare memory newWalletShare = WalletLib.scalarDeserialize(newShares);
        FeeTake memory expectedFees = feeRates.computeFeeTake(matchResult.quoteAmount);
        uint256 expectedReceiveAmount = matchResult.quoteAmount - expectedFees.total();
        BalanceShare memory recvBal = walletShare.balances[indices.balanceReceive];
        BalanceShare memory sendBal = walletShare.balances[indices.balanceSend];

        BN254.ScalarField expectedOrderSize = walletShare.orders[indices.order].amount.sub(matchResult.baseAmount);
        BN254.ScalarField expectedBalanceSend = sendBal.amount.sub(matchResult.baseAmount);
        BN254.ScalarField expectedBalanceReceive = recvBal.amount.add(expectedReceiveAmount);
        BN254.ScalarField expectedRelayerFee = recvBal.relayerFeeBalance.add(expectedFees.relayerFee);
        BN254.ScalarField expectedProtocolFee = recvBal.protocolFeeBalance.add(expectedFees.protocolFee);

        assertEq(newWalletShare.balances[indices.balanceSend].amount, expectedBalanceSend);
        assertEq(newWalletShare.balances[indices.balanceReceive].amount, expectedBalanceReceive);
        assertEq(newWalletShare.balances[indices.balanceReceive].relayerFeeBalance, expectedRelayerFee);
        assertEq(newWalletShare.balances[indices.balanceReceive].protocolFeeBalance, expectedProtocolFee);
        assertEq(newWalletShare.orders[indices.order].amount, expectedOrderSize);
    }

    /// @notice Test the application of an external match to the wallet's shares
    function test_applyExternalMatchToShares_buySide() public {
        // Generate a random wallet share and an external match result
        WalletShare memory walletShare = randomWalletShare();
        ExternalMatchResult memory matchResult = randomExternalMatchResult(ExternalMatchDirection.InternalPartyBuy);
        OrderSettlementIndices memory indices = randomOrderSettlementIndices();
        FeeTakeRate memory feeRates = randomFeeTakeRate();

        // Apply the match to the wallet's shares
        BN254.ScalarField[] memory oldShares = walletShare.scalarSerialize();
        BN254.ScalarField[] memory newShares =
            WalletOperations.applyExternalMatchToShares(oldShares, feeRates, matchResult, indices);

        // Verify the shares have been updated correctly
        WalletShare memory newWalletShare = WalletLib.scalarDeserialize(newShares);
        FeeTake memory expectedFees = feeRates.computeFeeTake(matchResult.baseAmount);
        uint256 expectedReceiveAmount = matchResult.baseAmount - expectedFees.total();
        BalanceShare memory recvBal = walletShare.balances[indices.balanceReceive];
        BalanceShare memory sendBal = walletShare.balances[indices.balanceSend];

        BN254.ScalarField expectedOrderSize = walletShare.orders[indices.order].amount.sub(matchResult.baseAmount);
        BN254.ScalarField expectedBalanceSend = sendBal.amount.sub(matchResult.quoteAmount);
        BN254.ScalarField expectedBalanceReceive = recvBal.amount.add(expectedReceiveAmount);
        BN254.ScalarField expectedRelayerFee = recvBal.relayerFeeBalance.add(expectedFees.relayerFee);
        BN254.ScalarField expectedProtocolFee = recvBal.protocolFeeBalance.add(expectedFees.protocolFee);

        assertEq(newWalletShare.balances[indices.balanceSend].amount, expectedBalanceSend);
        assertEq(newWalletShare.balances[indices.balanceReceive].amount, expectedBalanceReceive);
        assertEq(newWalletShare.balances[indices.balanceReceive].relayerFeeBalance, expectedRelayerFee);
        assertEq(newWalletShare.balances[indices.balanceReceive].protocolFeeBalance, expectedProtocolFee);
        assertEq(newWalletShare.orders[indices.order].amount, expectedOrderSize);
    }

    // --- Helpers --- //

    /// @dev Generate a random wallet share
    function randomWalletShare() internal returns (WalletShare memory) {
        BN254.ScalarField[] memory scalars = randomWalletShares();
        return WalletLib.scalarDeserialize(scalars);
    }
}

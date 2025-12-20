// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { IPermit2 } from "permit2-lib/interfaces/IPermit2.sol";
import { IWETH9 } from "renegade-lib/interfaces/IWETH9.sol";

import { TypesLib } from "darkpoolv1-types/TypesLib.sol";
import { ExternalTransferLib } from "darkpoolv1-lib/ExternalTransfers.sol";
import { ExternalTransfer, TransferAuthorization } from "darkpoolv1-types/Transfers.sol";
import { PublicRootKey } from "darkpoolv1-types/Keychain.sol";
import { ExternalMatchResult } from "darkpoolv1-types/Settlement.sol";
import { FeeTake } from "darkpoolv1-types/Fees.sol";

/// @title TransferExecutor
/// @author Renegade Eng
/// @notice A contract that executes external transfers for the Darkpool contract
/// @dev This contract is designed to be used with delegatecall from the Darkpool contract
contract TransferExecutor {
    using TypesLib for ExternalMatchResult;
    using TypesLib for FeeTake;

    /// @notice Executes a single external transfer
    /// @param transfer The external transfer to execute
    /// @param oldPkRoot The public root key of the sender's Renegade wallet
    /// @param transferAuthorization The authorization data for the transfer
    /// @param permit2 The Permit2 contract instance for handling deposits
    function executeTransfer(
        ExternalTransfer calldata transfer,
        PublicRootKey calldata oldPkRoot,
        TransferAuthorization calldata transferAuthorization,
        IPermit2 permit2
    )
        external
    {
        ExternalTransferLib.executeTransfer(transfer, oldPkRoot, transferAuthorization, permit2);
    }

    /// @notice Builds and executes a batch of transfers for an atomic match
    /// @param externalParty The address of the external party
    /// @param relayerFeeAddr The address to receive relayer fees
    /// @param protocolFeeRecipient The address to receive protocol fees
    /// @param matchResult The result of the match
    /// @param feeTake The fee take information
    /// @param weth The WETH9 contract for native token handling
    /// @return traderTake The amount received by the trader
    function executeAtomicMatchTransfers(
        address externalParty,
        address relayerFeeAddr,
        address protocolFeeRecipient,
        ExternalMatchResult calldata matchResult,
        FeeTake calldata feeTake,
        IWETH9 weth
    )
        external
        payable
        returns (uint256)
    {
        (uint256 traderTake, ExternalTransferLib.SimpleTransfer[] memory transfers) =
            buildAtomicMatchTransfers(externalParty, relayerFeeAddr, protocolFeeRecipient, matchResult, feeTake);

        ExternalTransferLib.executeTransferBatch(transfers, weth);
        return traderTake;
    }

    /// @notice Build a list of simple transfers to settle an atomic match
    /// @param externalParty The address of the external party
    /// @param relayerFeeAddr The address to receive relayer fees
    /// @param protocolFeeRecipient The address to receive protocol fees
    /// @param matchResult The result of the match
    /// @param feeTake The fee take information
    /// @return traderTake The amount of the trader's take
    /// @return transfers An array of simple transfers to execute
    function buildAtomicMatchTransfers(
        address externalParty,
        address relayerFeeAddr,
        address protocolFeeRecipient,
        ExternalMatchResult memory matchResult,
        FeeTake memory feeTake
    )
        public
        view
        returns (uint256 traderTake, ExternalTransferLib.SimpleTransfer[] memory transfers)
    {
        (address sellMint, uint256 sellAmount) = matchResult.externalPartySellMintAmount();
        (address buyMint, uint256 buyAmount) = matchResult.externalPartyBuyMintAmount();

        // Build the transfers
        transfers = new ExternalTransferLib.SimpleTransfer[](4);

        // 1. Deposit the sell amount
        transfers[0] = ExternalTransferLib.SimpleTransfer({
            account: msg.sender,
            mint: sellMint,
            amount: sellAmount,
            transferType: ExternalTransferLib.SimpleTransferType.Deposit
        });

        // 2. Withdraw the buy amount net of fees
        // Tx will revert if the buy amount is less than the total fees
        uint256 totalFees = feeTake.total();
        traderTake = buyAmount - totalFees;
        transfers[1] = ExternalTransferLib.SimpleTransfer({
            account: externalParty,
            mint: buyMint,
            amount: traderTake,
            transferType: ExternalTransferLib.SimpleTransferType.Withdrawal
        });

        // 3. Withdraw the relayer's fee on the external party to the relayer
        transfers[2] = ExternalTransferLib.SimpleTransfer({
            account: relayerFeeAddr,
            mint: buyMint,
            amount: feeTake.relayerFee,
            transferType: ExternalTransferLib.SimpleTransferType.Withdrawal
        });

        // 4. Withdraw the protocol's fee on the external party to the protocol
        transfers[3] = ExternalTransferLib.SimpleTransfer({
            account: protocolFeeRecipient,
            mint: buyMint,
            amount: feeTake.protocolFee,
            transferType: ExternalTransferLib.SimpleTransferType.Withdrawal
        });
    }
}

// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { TypesLib, DEPOSIT_WITNESS_TYPE_STRING } from "darkpoolv1-types/TypesLib.sol";
import { DepositWitness, ExternalTransfer, TransferType, TransferAuthorization } from "darkpoolv1-types/Transfers.sol";
import { PublicRootKey, publicKeyToUints } from "darkpoolv1-types/Keychain.sol";

import { DarkpoolConstants } from "darkpoolv1-lib/Constants.sol";
import { WalletOperations } from "darkpoolv1-lib/WalletOperations.sol";
import { IDarkpool } from "darkpoolv1-interfaces/IDarkpool.sol";
import { IPermit2 } from "permit2-lib/interfaces/IPermit2.sol";
import { IWETH9 } from "renegade-lib/interfaces/IWETH9.sol";
import { ISignatureTransfer } from "permit2-lib/interfaces/ISignatureTransfer.sol";
import { IERC20 } from "oz-contracts/token/ERC20/IERC20.sol";
import { SafeERC20 } from "oz-contracts/token/ERC20/utils/SafeERC20.sol";
import { SafeTransferLib } from "solmate/src/utils/SafeTransferLib.sol";
import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";

/// @title ExternalTransferLib
/// @author Renegade Eng
/// @notice This library implements the logic for executing external transfers
/// @notice External transfers are either deposits or withdrawals into/from the darkpool
library ExternalTransferLib {
    using TypesLib for DepositWitness;

    // --- Errors --- //

    /// @notice Thrown when balance after transfer does not match expected balance
    error BalanceMismatch();
    /// @notice Thrown when msg.value does not match deposit amount for native token
    error InvalidDepositAmount();
    /// @notice Thrown when withdrawal signature is invalid
    error InvalidWithdrawalSignature();

    // --- Types --- //

    /// @notice A simple ERC20 transfer
    struct SimpleTransfer {
        /// @dev The address to withdraw to or deposit from
        address account;
        /// @dev The ERC20 token to transfer
        address mint;
        /// @dev The amount of tokens to transfer
        uint256 amount;
        /// @dev The type of transfer
        SimpleTransferType transferType;
    }

    /// @notice The type of a simple ERC20 transfer
    enum SimpleTransferType {
        /// @dev A withdrawal
        Withdrawal,
        /// @dev A deposit
        Deposit
    }

    // --- Interface --- //

    /// @notice Executes an external transfer (deposit or withdrawal) for the darkpool
    /// @param transfer The external transfer details including account, mint, amount and type
    /// @param oldPkRoot The public root key of the sender's Renegade wallet
    /// @param authorization The authorization data for the transfer (permit2 or withdrawal signature)
    /// @param permit2 The Permit2 contract instance for handling deposits
    function executeTransfer(
        ExternalTransfer calldata transfer,
        PublicRootKey calldata oldPkRoot,
        TransferAuthorization calldata authorization,
        IPermit2 permit2
    )
        internal
    {
        // Get the darkpool balance before the transfer
        uint256 balanceBefore = getDarkpoolBalance(transfer.mint);
        uint256 expectedBalance;
        bool isDeposit = transfer.transferType == TransferType.Deposit;
        if (isDeposit) {
            executeDeposit(oldPkRoot, transfer, authorization, permit2);
            expectedBalance = balanceBefore + transfer.amount;
        } else {
            executeWithdrawal(oldPkRoot, transfer, authorization);
            expectedBalance = balanceBefore - transfer.amount;
        }

        // Check that the balance after the transfer equals the expected balance
        uint256 balanceAfter = getDarkpoolBalance(transfer.mint);
        if (balanceAfter != expectedBalance) revert BalanceMismatch();
        emit IDarkpool.ExternalTransfer(transfer.account, transfer.mint, !isDeposit, transfer.amount);
    }

    /// @notice Execute a batch of simple ERC20 transfers
    /// @param transfers The batch of transfers to execute
    /// @param wrapper The WETH9 wrapper contract for native token handling
    function executeTransferBatch(SimpleTransfer[] memory transfers, IWETH9 wrapper) internal {
        for (uint256 i = 0; i < transfers.length; ++i) {
            // Do nothing if the transfer amount i zero
            if (transfers[i].amount == 0) {
                continue;
            }

            // Otherwise, execute the transfer
            uint256 balanceBefore = getDarkpoolBalanceMaybeNative(transfers[i].mint, wrapper);
            uint256 expectedBalance;
            SimpleTransferType transferType = transfers[i].transferType;
            if (transferType == SimpleTransferType.Withdrawal) {
                executeSimpleWithdrawal(transfers[i], wrapper);
                expectedBalance = balanceBefore - transfers[i].amount;
            } else {
                executeSimpleDeposit(transfers[i], wrapper);
                expectedBalance = balanceBefore + transfers[i].amount;
            }

            // Check that the balance after the transfer equals the expected balance
            uint256 balanceAfter = getDarkpoolBalanceMaybeNative(transfers[i].mint, wrapper);
            if (balanceAfter != expectedBalance) revert BalanceMismatch();
        }
    }

    // --- Deposit --- //

    /// @notice Executes a deposit of shares into the darkpool
    /// @dev Deposits flow through the permit2 contract, which allows us to attach the public root
    /// @dev key to the deposit's witness. This provides a link between the on-chain wallet and the
    /// @dev Renegade wallet, ensuring that only one Renegade wallet may redeem the permit.
    /// @param oldPkRoot The public root key of the depositor's wallet
    /// @param transfer The transfer to execute
    /// @param authorization The authorization for the deposit
    /// @param permit2 The permit2 contract
    function executeDeposit(
        PublicRootKey calldata oldPkRoot,
        ExternalTransfer calldata transfer,
        TransferAuthorization calldata authorization,
        IPermit2 permit2
    )
        internal
    {
        // Build the permit
        ISignatureTransfer.TokenPermissions memory tokenPermissions =
            ISignatureTransfer.TokenPermissions({ token: transfer.mint, amount: transfer.amount });
        ISignatureTransfer.PermitTransferFrom memory permit = ISignatureTransfer.PermitTransferFrom({
            permitted: tokenPermissions,
            nonce: authorization.permit2Nonce,
            deadline: authorization.permit2Deadline
        });
        ISignatureTransfer.SignatureTransferDetails memory signatureTransferDetails =
            ISignatureTransfer.SignatureTransferDetails({ to: address(this), requestedAmount: transfer.amount });
        DepositWitness memory depositWitness = DepositWitness({ pkRoot: publicKeyToUints(oldPkRoot) });
        bytes32 depositWitnessHash = depositWitness.hashWitness();

        address owner = transfer.account;
        permit2.permitWitnessTransferFrom(
            permit,
            signatureTransferDetails,
            owner,
            depositWitnessHash,
            DEPOSIT_WITNESS_TYPE_STRING,
            authorization.permit2Signature
        );
    }

    /// @notice Execute a simple ERC20 deposit
    /// @dev It is assumed that the address from which we deposit has approved the darkpool to spend the tokens
    /// @param transfer The transfer to execute
    /// @param wrapper The WETH9 wrapper contract for native token handling
    function executeSimpleDeposit(SimpleTransfer memory transfer, IWETH9 wrapper) internal {
        // Handle native token deposits by wrapping the transaction value
        if (DarkpoolConstants.isNativeToken(transfer.mint)) {
            if (msg.value != transfer.amount) revert InvalidDepositAmount();
            wrapper.deposit{ value: transfer.amount }();
            return;
        }

        IERC20 token = IERC20(transfer.mint);
        address self = address(this);
        SafeERC20.safeTransferFrom(token, transfer.account, self, transfer.amount);
    }

    // --- Withdrawal --- //

    /// @notice Executes a withdrawal of shares from the darkpool
    /// @param oldPkRoot The public root key of the withdrawer's wallet
    /// @param transfer The transfer to execute
    /// @param authorization The authorization for the withdrawal
    function executeWithdrawal(
        PublicRootKey calldata oldPkRoot,
        ExternalTransfer calldata transfer,
        TransferAuthorization calldata authorization
    )
        internal
    {
        // 1. Verify the signature of the withdrawal
        bytes memory transferBytes = abi.encode(transfer);
        bytes32 transferHash = EfficientHashLib.hash(transferBytes);
        bool sigValid =
            WalletOperations.verifyRootKeySignature(transferHash, authorization.externalTransferSignature, oldPkRoot);
        if (!sigValid) revert InvalidWithdrawalSignature();

        // 2. Execute the withdrawal as a direct ERC20 transfer
        IERC20 token = IERC20(transfer.mint);
        SafeERC20.safeTransfer(token, transfer.account, transfer.amount);
    }

    /// @notice Execute a simple ERC20 withdrawal
    /// @param transfer The transfer to execute
    /// @param wrapper The WETH9 wrapper contract for native token handling
    function executeSimpleWithdrawal(SimpleTransfer memory transfer, IWETH9 wrapper) internal {
        // Handle native token withdrawals by unwrapping the transfer amount into ETH
        if (DarkpoolConstants.isNativeToken(transfer.mint)) {
            wrapper.withdraw(transfer.amount);
            SafeTransferLib.safeTransferETH(transfer.account, transfer.amount);
            return;
        }

        IERC20 token = IERC20(transfer.mint);
        SafeERC20.safeTransfer(token, transfer.account, transfer.amount);
    }

    // --- Helpers --- //

    /// @notice Get the balance of the darkpool for a given ERC20 token
    /// @param token The ERC20 token address
    /// @return The balance of the darkpool for the given token
    function getDarkpoolBalance(address token) internal view returns (uint256) {
        return IERC20(token).balanceOf(address(this));
    }

    /// @notice Get a darkpool balance for an ERC20 token address that might be the native token
    /// @dev The darkpool only ever holds the wrapped native asset, so use the wrapped balance if the token is native
    /// @param token The ERC20 token address (or native token address)
    /// @param wrapper The WETH9 wrapper contract
    /// @return The balance of the darkpool for the given token
    function getDarkpoolBalanceMaybeNative(address token, IWETH9 wrapper) internal view returns (uint256) {
        if (DarkpoolConstants.isNativeToken(token)) {
            return wrapper.balanceOf(address(this));
        }

        return getDarkpoolBalance(token);
    }
}

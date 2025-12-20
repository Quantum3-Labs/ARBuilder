// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { IWETH9 } from "renegade-lib/interfaces/IWETH9.sol";
import { IAllowanceTransfer } from "permit2-lib/interfaces/IAllowanceTransfer.sol";
import { ISignatureTransfer } from "permit2-lib/interfaces/ISignatureTransfer.sol";
import { IERC20 } from "oz-contracts/token/ERC20/IERC20.sol";
import { SafeERC20 } from "oz-contracts/token/ERC20/utils/SafeERC20.sol";
import { SafeTransferLib } from "solmate/src/utils/SafeTransferLib.sol";
import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";
import { ECDSALib } from "renegade-lib/ECDSA.sol";
import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import { SimpleTransfer, SimpleTransferType } from "darkpoolv2-types/transfers/SimpleTransfer.sol";
import {
    Deposit,
    DepositAuth,
    DepositWitness,
    DepositLib,
    DEPOSIT_WITNESS_TYPE_STRING
} from "darkpoolv2-types/transfers/Deposit.sol";
import { Withdrawal, WithdrawalAuth } from "darkpoolv2-types/transfers/Withdrawal.sol";

/// @title ExternalTransferLib
/// @author Renegade Eng
/// @notice This library implements the logic for executing ERC20 transfers
/// @notice External transfers are either deposits or withdrawals into/from the darkpool
/// @dev This library handles both ERC20 transfers that from native settlements as well as
/// individual deposit/withdrawals into/from Merklized balances.
library ExternalTransferLib {
    using DepositLib for DepositWitness;
    // --- Errors --- //
    /// @notice Thrown when balance after transfer does not match expected balance

    error BalanceMismatch();
    /// @notice Thrown when the deposit amount does not match the msg.value for a native token deposit
    error InvalidDepositAmount();
    /// @notice Thrown when the withdrawal signature is invalid
    error InvalidWithdrawalSignature();

    // --- Interface --- //

    /// @notice Execute a single ERC20 transfer
    /// @param transfer The transfer to execute
    /// @param wrapper The WETH9 wrapper contract for native token handling
    /// @param permit2 The permit2 contract instance
    function executeTransfer(SimpleTransfer memory transfer, IWETH9 wrapper, IAllowanceTransfer permit2) public {
        // If the amount is zero, do nothing
        if (transfer.amount == 0) {
            return;
        }

        // Otherwise, execute the transfer
        uint256 balanceBefore = getDarkpoolBalanceMaybeNative(transfer.mint, wrapper);
        uint256 expectedBalance;
        SimpleTransferType transferType = transfer.transferType;
        if (transferType == SimpleTransferType.Withdrawal) {
            executeSimpleWithdrawal(transfer, wrapper);
            expectedBalance = balanceBefore - transfer.amount;
        } else if (transferType == SimpleTransferType.Permit2AllowanceDeposit) {
            executePermit2AllowanceDeposit(transfer, permit2);
            expectedBalance = balanceBefore + transfer.amount;
        } else {
            executeDirectErc20Deposit(transfer, wrapper);
            expectedBalance = balanceBefore + transfer.amount;
        }

        // Check that the balance after the transfer equals the expected balance
        uint256 balanceAfter = getDarkpoolBalanceMaybeNative(transfer.mint, wrapper);
        if (balanceAfter != expectedBalance) revert BalanceMismatch();
    }

    /// @notice Execute a batch of simple ERC20 transfers
    /// @param transfers The batch of transfers to execute
    /// @param wrapper The WETH9 wrapper contract for native token handling
    /// @param permit2 The permit2 contract instance
    function executeTransfers(SimpleTransfer[] memory transfers, IWETH9 wrapper, IAllowanceTransfer permit2) internal {
        for (uint256 i = 0; i < transfers.length; ++i) {
            executeTransfer(transfers[i], wrapper, permit2);
        }
    }

    // --- Deposit --- //

    /// @notice Execute a direct ERC20 deposit
    /// @dev It is assumed that the address from which we deposit has approved the darkpool to spend the tokens
    /// @param transfer The transfer to execute
    /// @param wrapper The WETH9 wrapper contract for native token handling
    function executeDirectErc20Deposit(SimpleTransfer memory transfer, IWETH9 wrapper) internal {
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

    /// @notice Execute a permit2 allowance deposit
    /// @param transfer The transfer to execute
    /// @param permit2 The permit2 contract instance
    /// TODO: Allow this method to register a previously unused permit2 allowance
    function executePermit2AllowanceDeposit(SimpleTransfer memory transfer, IAllowanceTransfer permit2) internal {
        address to = address(this);
        uint160 amount = uint160(transfer.amount);
        permit2.transferFrom(transfer.account, to, amount, transfer.mint);
    }

    /// @notice Execute a permit2 signature deposit with witness
    /// @dev Deposits flow through the permit2 contract, which allows us to attach the new balance commitment
    /// @dev to the deposit's witness. This provides a link between the on-chain deposit and the updated
    /// @dev Merklized balance, ensuring the deposit is bound to a _specific_ balance update.
    /// @param deposit The deposit to execute
    /// @param newBalanceCommitment The commitment to the updated balance after deposit
    /// @param auth The authorization for the deposit
    /// @param permit2 The permit2 signature transfer contract
    function executePermit2SignatureDeposit(
        Deposit memory deposit,
        BN254.ScalarField newBalanceCommitment,
        DepositAuth memory auth,
        ISignatureTransfer permit2
    )
        internal
    {
        // 1. Record the balance before the deposit
        uint256 balanceBefore = getDarkpoolBalance(deposit.token);

        // 2. Build the permit
        ISignatureTransfer.TokenPermissions memory tokenPermissions =
            ISignatureTransfer.TokenPermissions({ token: deposit.token, amount: deposit.amount });
        ISignatureTransfer.PermitTransferFrom memory permit = ISignatureTransfer.PermitTransferFrom({
            permitted: tokenPermissions,
            nonce: auth.permit2Nonce,
            deadline: auth.permit2Deadline
        });
        ISignatureTransfer.SignatureTransferDetails memory transferDetails =
            ISignatureTransfer.SignatureTransferDetails({ to: address(this), requestedAmount: deposit.amount });

        // Hash the witness
        uint256 newBalanceCommitmentUint = BN254.ScalarField.unwrap(newBalanceCommitment);
        DepositWitness memory witness = DepositWitness({ newBalanceCommitment: newBalanceCommitmentUint });
        bytes32 witnessHash = witness.hashWitness();

        // 3. Execute the permit witness transfer
        permit2.permitWitnessTransferFrom(
            permit, transferDetails, deposit.from, witnessHash, DEPOSIT_WITNESS_TYPE_STRING, auth.permit2Signature
        );

        // 4. Check that the balance after the deposit equals the expected balance
        uint256 balanceAfter = getDarkpoolBalance(deposit.token);
        if (balanceAfter != balanceBefore + deposit.amount) revert BalanceMismatch();
    }

    // --- Withdrawal --- //

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

    /// @notice Execute a signed withdrawal
    /// @param newBalanceCommitment The commitment to the updated balance after the withdrawal executes
    /// @param auth The authorization for the withdrawal
    /// @param withdrawal The withdrawal to execute
    function executeSignedWithdrawal(
        BN254.ScalarField newBalanceCommitment,
        WithdrawalAuth memory auth,
        Withdrawal memory withdrawal
    )
        internal
    {
        // 1. Record the balance before the withdrawal
        uint256 balanceBefore = getDarkpoolBalance(withdrawal.token);

        // 2. Verify the signature over the new balance commitment by the owner
        // The `withdrawal.to` address is constrained to be the owner of the balance in-circuit
        bytes32 withdrawalHash = EfficientHashLib.hash(BN254.ScalarField.unwrap(newBalanceCommitment));
        bool sigValid = ECDSALib.verify(withdrawalHash, auth.signature, withdrawal.to);
        if (!sigValid) revert InvalidWithdrawalSignature();

        // 3. Execute the withdrawal as a direct ERC20 transfer
        IERC20 token = IERC20(withdrawal.token);
        SafeERC20.safeTransfer(token, withdrawal.to, withdrawal.amount);

        // 4. Check that the balance after the withdrawal equals the expected balance
        uint256 balanceAfter = getDarkpoolBalance(withdrawal.token);
        if (balanceAfter != balanceBefore - withdrawal.amount) revert BalanceMismatch();
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

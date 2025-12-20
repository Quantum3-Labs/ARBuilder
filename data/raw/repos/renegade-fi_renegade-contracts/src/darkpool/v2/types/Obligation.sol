// SPDX-License-Identifier: Apache
pragma solidity ^0.8.24;

import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";
import { SimpleTransfer, SimpleTransferType } from "darkpoolv2-types/transfers/SimpleTransfer.sol";

/// @notice A settlement obligation for a user
struct SettlementObligation {
    /// @dev The input token address
    address inputToken;
    /// @dev The output token address
    address outputToken;
    /// @dev The amount of the input token to trade
    uint256 amountIn;
    /// @dev The amount of the output token to receive, before fees
    uint256 amountOut;
}

/// @title Settlement Obligation Library
/// @author Renegade Eng
/// @notice Library for settlement obligation operations
library SettlementObligationLib {
    /// @notice Return whether two obligations are equal
    /// @param obligation0 The first obligation to compare
    /// @param obligation1 The second obligation to compare
    /// @return Whether the obligations are equal
    function isEqualTo(
        SettlementObligation memory obligation0,
        SettlementObligation memory obligation1
    )
        internal
        pure
        returns (bool)
    {
        return obligation0.inputToken == obligation1.inputToken && obligation0.outputToken == obligation1.outputToken
            && obligation0.amountIn == obligation1.amountIn && obligation0.amountOut == obligation1.amountOut;
    }

    /// @notice Compute the obligation hash for a given settlement obligation
    /// @param obligation The settlement obligation to compute the hash for
    /// @return The hash of the obligation
    function computeObligationHash(SettlementObligation memory obligation) internal pure returns (bytes32) {
        bytes memory obligationBytes = abi.encode(obligation);
        return EfficientHashLib.hash(obligationBytes);
    }

    /// @notice Get the deposit transfer for a settlement obligation using a permit2 allowance transfer
    /// @param obligation The settlement obligation to get the deposit transfer for
    /// @param owner The owner of the settlement obligation
    /// @return The deposit transfer
    function buildPermit2AllowanceDeposit(
        SettlementObligation memory obligation,
        address owner
    )
        internal
        pure
        returns (SimpleTransfer memory)
    {
        return SimpleTransfer({
            account: owner,
            mint: obligation.inputToken,
            amount: obligation.amountIn,
            transferType: SimpleTransferType.Permit2AllowanceDeposit
        });
    }

    /// @notice Get the deposit transfer for a settlement obligation using an ERC20 approval transfer
    /// @param obligation The settlement obligation to get the ERC20 approval deposit transfer for
    /// @param owner The owner of the settlement obligation
    /// @return The ERC20 approval deposit transfer
    function buildERC20ApprovalDeposit(
        SettlementObligation memory obligation,
        address owner
    )
        internal
        pure
        returns (SimpleTransfer memory)
    {
        return SimpleTransfer({
            account: owner,
            mint: obligation.inputToken,
            amount: obligation.amountIn,
            transferType: SimpleTransferType.ERC20ApprovalDeposit
        });
    }

    /// @notice Get the withdrawal transfer for a settlement obligation
    /// @param obligation The settlement obligation to get the withdrawal transfer for
    /// @param owner The owner of the settlement obligation
    /// @param totalFee The total fee to deduct from the raw obligation amount out
    /// @return The withdrawal transfer
    function buildWithdrawalTransfer(
        SettlementObligation memory obligation,
        address owner,
        uint256 totalFee
    )
        internal
        pure
        returns (SimpleTransfer memory)
    {
        return SimpleTransfer({
            account: owner,
            mint: obligation.outputToken,
            amount: obligation.amountOut - totalFee,
            transferType: SimpleTransferType.Withdrawal
        });
    }
}

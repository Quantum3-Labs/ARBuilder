// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { Deposit } from "darkpoolv2-types/transfers/Deposit.sol";
import { Withdrawal } from "darkpoolv2-types/transfers/Withdrawal.sol";

// --- Deposit Statements --- //

/// @notice A statement proving validity of a deposit into an existing balance
struct ValidDepositStatement {
    /// @dev The deposit to execute
    Deposit deposit;
    /// @dev The Merkle root to which the old balance opens
    BN254.ScalarField merkleRoot;
    /// @dev The nullifier of the previous version of the balance
    BN254.ScalarField oldBalanceNullifier;
    /// @dev A commitment to the updated balance
    BN254.ScalarField newBalanceCommitment;
    /// @dev The new recovery identifier of the balance
    /// @dev This value is emitted as an event for chain indexers to track the balance's update
    BN254.ScalarField recoveryId;
    /// @dev The new public share of the amount field on the balance
    /// @dev We only leak the public shares of the updated fields in each state transition
    BN254.ScalarField newAmountShare;
}

/// @notice A statement proving validity of a deposit into a new balance
struct ValidBalanceCreateStatement {
    /// @dev The deposit to execute
    Deposit deposit;
    /// @dev A commitment to the updated balance
    /// TODO: Decide whether this should be a partial commitment or a full commitment
    BN254.ScalarField newBalanceCommitment;
    /// @dev the recovery id of the balance
    BN254.ScalarField recoveryId;
    /// @dev The public shares of the new balance
    /// @dev These shares represent an entire balance
    BN254.ScalarField[7] newBalancePublicShares;
}

// --- Withdrawal Statements --- //

/// @notice A statement proving validity of a withdrawal from a balance
struct ValidWithdrawalStatement {
    /// @dev The withdrawal to execute
    Withdrawal withdrawal;
    /// @dev The Merkle root to which the old balance opens
    BN254.ScalarField merkleRoot;
    /// @dev The nullifier of the previous version of the balance
    BN254.ScalarField oldBalanceNullifier;
    /// @dev The commitment to the updated balance after the withdrawal executes
    BN254.ScalarField newBalanceCommitment;
    /// @dev The new recovery identifier of the balance
    /// @dev This value is emitted as an event for chain indexers to track the balance's update
    BN254.ScalarField recoveryId;
    /// @dev The new public share of the amount field on the balance
    /// @dev This is verified in the proof and placed here to leak it in calldata for recovery logic
    BN254.ScalarField newAmountShare;
}

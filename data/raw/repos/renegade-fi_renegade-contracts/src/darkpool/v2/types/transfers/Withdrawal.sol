// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title Withdrawal
/// @author Renegade Eng
/// @notice A withdrawal from a balance in the darkpool
struct Withdrawal {
    /// @dev The token to withdraw
    address token;
    /// @dev The address from which to withdraw
    address to;
    /// @dev The amount to withdraw
    uint256 amount;
}

/// @notice The authorization for a withdrawal
/// @dev This authorizes a signature transfer of the withdrawal amount
/// @dev The signature here is over the commitment to the updated balance after the withdrawal executes
struct WithdrawalAuth {
    /// @dev The signature of the post-withdrawal balance commitment
    bytes signature;
}

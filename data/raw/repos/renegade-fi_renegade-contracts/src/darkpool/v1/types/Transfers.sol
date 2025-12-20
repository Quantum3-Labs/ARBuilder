// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

// This file contains types for external transfers

// ---------------------
// | External Transfer |
// ---------------------

/// @notice An external transfer representing a deposit or withdrawal into/from the darkpool
struct ExternalTransfer {
    /// @dev The account address of the sender/recipient
    address account;
    /// @dev The mint (erc20 address) of the token
    address mint;
    /// @dev The amount of the transfer
    uint256 amount;
    /// @dev Indicates if it's a deposit or withdrawal
    TransferType transferType;
}

/// @notice The type of transfer
enum TransferType {
    Deposit,
    Withdrawal
}

/// @notice Auxiliary data authorizing a transfer
/// @dev This struct is effectively a union of the auth required for
/// @dev a deposit (permit2) and that required for a withdrawal (a simple signature)
/// @dev The external transfer implementation will use the appropriate authorization
/// @dev based on the transfer type
struct TransferAuthorization {
    /// @dev The nonce of the permit
    uint256 permit2Nonce;
    /// @dev The deadline of the permit
    uint256 permit2Deadline;
    /// @dev The signature of the permit
    bytes permit2Signature;
    /// @dev The signature of the external transfer
    bytes externalTransferSignature;
}

/// @notice The permit2 witness for a deposit
/// @dev The Permit2 witness type used in a deposit
struct DepositWitness {
    /// @dev The limb-serialization of the public key of the old wallet
    uint256[4] pkRoot;
}

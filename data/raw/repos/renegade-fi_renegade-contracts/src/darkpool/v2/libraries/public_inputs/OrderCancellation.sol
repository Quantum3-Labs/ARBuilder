// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";

/// @title Order Cancellation Public Inputs Library
/// @author Renegade Eng
/// @notice Library for operating on proof public inputs for order cancellation
struct ValidOrderCancellationStatement {
    /// @dev The Merkle root to which the old intent opens
    BN254.ScalarField merkleRoot;
    /// @dev The nullifier of the old intent
    BN254.ScalarField oldIntentNullifier;
    /// @dev The owner of the intent, leaked in the statement to allow the contracts to verify
    /// that cancellation is authorized by the owner.
    address owner;
}

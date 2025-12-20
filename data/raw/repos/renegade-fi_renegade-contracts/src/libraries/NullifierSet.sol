// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";

/// @title NullifierSet
/// @author Renegade Eng
/// @notice Tracks the set of spent nullifiers in the darkpool, ensuring that a pre-update wallet
/// @notice cannot create two separate post-update wallets
library NullifierLib {
    using NullifierLib for NullifierLib.NullifierSet;

    /// @notice The nullifier has already been spent
    error NullifierAlreadySpent();

    /// @notice The nullifiers in the set
    struct NullifierSet {
        mapping(uint256 => bool) nullifiers;
    }

    /// @notice Check if a nullifier has been spent
    /// @param self The nullifier set
    /// @param nullifier The nullifier to check
    /// @return True if the nullifier has been spent, false otherwise
    function isSpent(NullifierSet storage self, BN254.ScalarField nullifier) public view returns (bool) {
        uint256 nullifierUint = BN254.ScalarField.unwrap(nullifier);
        return self.nullifiers[nullifierUint];
    }

    /// @notice Mark a nullifier as spent
    /// @param self The nullifier set
    /// @param nullifier The nullifier to spend
    function spend(NullifierSet storage self, BN254.ScalarField nullifier) public {
        require(!isSpent(self, nullifier), NullifierAlreadySpent());
        uint256 nullifierUint = BN254.ScalarField.unwrap(nullifier);
        self.nullifiers[nullifierUint] = true;
    }
}

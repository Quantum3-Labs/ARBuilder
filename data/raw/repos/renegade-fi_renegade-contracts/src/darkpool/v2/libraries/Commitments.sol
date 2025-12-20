// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { IHasher } from "renegade-lib/interfaces/IHasher.sol";
import { PartialCommitment } from "darkpoolv2-types/PartialCommitment.sol";

/// @title CommitmentLib
/// @notice Library for computing commitments from partial commitments
library CommitmentLib {
    /// @notice Compute a full commitment from a partial commitment and remaining shares
    /// @param remainingShares The remaining shares to hash with the partial public commitment
    /// @param partialComm The partial commitment containing the private commitment and partial public commitment
    /// @param hasher The hasher to use for hashing
    /// @return The full commitment
    function computeResumableCommitment(
        uint256[] memory remainingShares,
        PartialCommitment memory partialComm,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField)
    {
        // 1. Compute the full public commitment by resuming from the partial public commitment
        uint256[] memory publicCommitmentInputs = new uint256[](remainingShares.length + 1);
        publicCommitmentInputs[0] = BN254.ScalarField.unwrap(partialComm.partialPublicCommitment);
        for (uint256 i = 0; i < remainingShares.length; ++i) {
            publicCommitmentInputs[i + 1] = remainingShares[i];
        }

        uint256 publicCommitmentHash = hasher.computeResumableCommitment(publicCommitmentInputs);

        // 2. Compute the full commitment: H(privateCommitment || publicCommitment)
        return computeCommitment(partialComm.privateCommitment, BN254.ScalarField.wrap(publicCommitmentHash), hasher);
    }

    /// @notice Compute a commitment to a state element given a private commitment and all public shares
    /// @dev This differs from the method above in that there is no partial public commitment to resume from.
    /// @param privateCommitment The private commitment to the state element
    /// @param publicShares The public shares to hash with the private commitment
    /// @param hasher The hasher to use for hashing
    /// @return The full commitment
    function computeCommitmentWithPublicShares(
        BN254.ScalarField privateCommitment,
        uint256[] memory publicShares,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField)
    {
        // Compute a commitment to the public shares
        uint256 publicCommitment = hasher.computeResumableCommitment(publicShares);

        // Compute the full commitment: H(privateCommitment || publicCommitment)
        return computeCommitment(privateCommitment, BN254.ScalarField.wrap(publicCommitment), hasher);
    }

    /// @notice Compute a commitment to a state element given a private commitment and a public commitment
    /// @param privateCommitment The private commitment to the state element
    /// @param publicCommitment The public commitment to the state element
    /// @param hasher The hasher to use for hashing
    /// @return The full commitment
    function computeCommitment(
        BN254.ScalarField privateCommitment,
        BN254.ScalarField publicCommitment,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField)
    {
        uint256[] memory commitmentInputs = new uint256[](2);
        commitmentInputs[0] = BN254.ScalarField.unwrap(privateCommitment);
        commitmentInputs[1] = BN254.ScalarField.unwrap(publicCommitment);
        uint256 fullCommitment = hasher.spongeHash(commitmentInputs);
        return BN254.ScalarField.wrap(fullCommitment);
    }
}

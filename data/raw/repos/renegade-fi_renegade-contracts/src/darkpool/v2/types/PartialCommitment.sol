// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";

/// @notice A partial commitment to a state element
/// @dev Because the structure of a commitment ultimately involves
/// H(private_commitment || public_commitment), a partial commitment must store
/// the full private commitment and the partial public commitment
struct PartialCommitment {
    /// @dev The private commitment
    BN254.ScalarField privateCommitment;
    /// @dev The partial public commitment
    BN254.ScalarField partialPublicCommitment;
}

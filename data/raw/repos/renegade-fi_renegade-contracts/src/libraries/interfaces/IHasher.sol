// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

/// @title IHasher
/// @author Renegade Eng
/// @notice Interface for hashing, both sponge and Merkle tree hashing
interface IHasher {
    /// @notice Hash a leaf into the merkle tree
    /// @param idx The index of the leaf in the tree
    /// @param input The input to the leaf
    /// @param sisterLeaves The sister leaves of the current node
    /// @return The incremental hashes up the tree, including the root, the root is the last element of the array
    function merkleHash(
        uint256 idx,
        uint256 input,
        uint256[] memory sisterLeaves
    )
        external
        view
        returns (uint256[] memory);

    /// @notice Hash a series of inputs into a sponge and squeeze
    /// @param inputs The inputs to the sponge
    /// @return The hash of the inputs
    function spongeHash(uint256[] memory inputs) external view returns (uint256);

    /// @notice Hash a series of inputs in a resumable fashion beginning with the given seed
    /// @dev A resumable commitment resets the hasher state in between each newly hashed element.
    /// This allows for the circuits to compute a partial commitment and for the contracts to "resume"
    /// the commitment with the remaining field elements.
    /// @param elements The elements to hash
    /// @return The hash of the elements
    function computeResumableCommitment(uint256[] memory elements) external view returns (uint256);
}

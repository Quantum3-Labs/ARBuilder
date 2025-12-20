// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { MerkleTreeLib } from "renegade-lib/merkle/MerkleTree.sol";
import { IHasher } from "renegade-lib/interfaces/IHasher.sol";

/// @title MerkleMountainLib
/// @author Renegade Eng
/// @notice Library for Merkle mountain range operations
/// @dev Our Merkle mountain range is not technically a mountain range. We create and store many sub-trees
/// but do not accumulate their roots into a global tree root. Rather, we store each historical root for each
/// sub-tree. This makes indexing and validity checks much simpler, at the cost of a bit more gas.
/// @dev As a result, we store an active sub-tree for each desired Merkle depth. The roots of these sub-trees
/// are tracked together in a single mapping of `historicalRoots`. When a sub-tree fills up; a new, empty sub-tree
/// of the same depth is created and becomes the active sub-tree for that depth.
library MerkleMountainLib {
    using MerkleTreeLib for MerkleTreeLib.MerkleTree;

    /// @notice A Merkle mountain range is a collection of Merkle trees
    struct MerkleMountainRange {
        /// @notice A list of all historical roots for all sub-trees
        mapping(BN254.ScalarField => bool) historicalRoots;
        /// @notice A mapping from depth to the active sub-tree at that depth
        mapping(uint256 => MerkleTreeLib.MerkleTree) activeSubTrees;
    }

    /// @notice Initialize an empty Merkle tree at a given depth
    /// @param mountain The Merkle mountain range to initialize the sub-tree in
    /// @param depth The depth of the sub-tree to initialize
    /// @dev We do this to avoid initialization cost on the first insert and to aid testing by making a dummy root
    /// available on contract creation.
    function initialize(MerkleMountainRange storage mountain, uint256 depth) internal {
        _replaceActiveSubTree(mountain, depth);
        _storeRoot(mountain, mountain.activeSubTrees[depth].getRoot());
    }

    /// @notice Get the root of the active sub-tree at the given depth
    /// @param mountain The Merkle mountain range to get the root of
    /// @param depth The depth of the sub-tree to get the root of
    /// @return The root of the active sub-tree at the given depth
    function getRoot(MerkleMountainRange storage mountain, uint256 depth) internal view returns (BN254.ScalarField) {
        return mountain.activeSubTrees[depth].getRoot();
    }

    /// @notice Check if a root is in the historical roots
    /// @param mountain The Merkle mountain range to check the root in
    /// @param root The root to check
    /// @return Whether the root is in the historical roots
    function rootInHistory(MerkleMountainRange storage mountain, BN254.ScalarField root) internal view returns (bool) {
        return mountain.historicalRoots[root];
    }

    /// @notice Insert a leaf into the mountain range in a tree of the given depth
    /// @param mountain The Merkle mountain range to insert the leaf into
    /// @param depth The depth of the tree to insert the leaf into
    /// @param leaf The leaf to insert
    /// @param hasher The hasher to use for computing Merkle hashes
    function insertLeaf(
        MerkleMountainRange storage mountain,
        uint256 depth,
        BN254.ScalarField leaf,
        IHasher hasher
    )
        internal
    {
        MerkleTreeLib.MerkleTree storage tree = mountain.activeSubTrees[depth];
        if (!tree.isInitialized() || tree.isFull()) {
            _replaceActiveSubTree(mountain, depth);
        }

        tree.insertLeaf(leaf, hasher);
        _storeRoot(mountain, tree.getRoot());
    }

    /// @notice Replace the active sub-tree at the given depth
    /// @param mountain The Merkle mountain range to create the sub-tree in
    /// @param depth The depth of the sub-tree to create
    function _replaceActiveSubTree(MerkleMountainRange storage mountain, uint256 depth) private {
        MerkleTreeLib.MerkleTreeConfig memory config =
            MerkleTreeLib.MerkleTreeConfig({ depth: depth, storeRoots: false });
        MerkleTreeLib.MerkleTree storage tree = mountain.activeSubTrees[depth];
        tree.initialize(config);
    }

    /// @notice Store a root for the mountain range
    /// @param mountain The Merkle mountain range to store the root in
    /// @param root The root to store
    function _storeRoot(MerkleMountainRange storage mountain, BN254.ScalarField root) private {
        mountain.historicalRoots[root] = true;
    }
}

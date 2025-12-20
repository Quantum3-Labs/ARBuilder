// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { IHasher } from "renegade-lib/interfaces/IHasher.sol";
import { DarkpoolConstants } from "darkpoolv1-lib/Constants.sol";
import { MerkleZeros } from "./MerkleZeros.sol";

/// @title MerkleTreeLib
/// @author Renegade Eng
/// @notice Library for Merkle tree operations
library MerkleTreeLib {
    // --- Errors --- //

    /// @notice Error thrown when the Merkle tree is full
    error MerkleTreeFull();
    /// @notice Error thrown when the Merkle tree does not support historical roots
    error RootHistoryDisabled();

    // --- Events --- //

    /// @notice Emitted when an internal Merkle node is updated
    /// @param depth The depth at which the node is updated
    /// @param index The index of the node in the Merkle tree
    /// @param new_value The new value of the node
    /// forge-lint: disable-next-line(mixed-case-variable)
    event MerkleOpeningNode(uint8 indexed depth, uint128 indexed index, uint256 new_value); // solhint-disable-line
    /// @notice Emitted when a Merkle leaf is inserted into the tree
    /// @param index The leaf index
    /// @param value The value of the leaf
    /// forge-lint: disable-next-line(mixed-case-variable)
    event MerkleInsertion(uint128 indexed index, uint256 indexed value);

    // --- Structs --- //

    /// @notice Structure containing Merkle tree state
    struct MerkleTree {
        /// @notice The config for the Merkle tree
        MerkleTreeConfig config;
        /// @notice The next available leaf index
        uint64 nextIndex;
        /// @notice The current root of the tree
        BN254.ScalarField root;
        /// @notice The current path of siblings for the next leaf to be inserted.
        BN254.ScalarField[] siblingPath;
        /// @notice The root history, mapping from historic roots to a boolean
        mapping(BN254.ScalarField => bool) rootHistory;
    }

    /// @notice The config for the Merkle tree
    struct MerkleTreeConfig {
        /// @notice Whether the Merkle tree should store historical roots
        bool storeRoots;
        /// @notice The depth of the Merkle tree
        uint256 depth;
    }

    // --- Implementation --- //

    /// @notice Get the zero value for a given height in the Merkle tree
    /// @param height The height in the Merkle tree
    /// @return The zero value for the given height
    function zeroValue(uint256 height) internal pure returns (BN254.ScalarField) {
        // Use the assembly-based getter for maximum gas efficiency
        return BN254.ScalarField.wrap(MerkleZeros.getZeroValue(height));
    }

    /// @notice Whether the Merkle tree is full
    /// @param tree The tree to check if it is full
    /// @return full Whether the Merkle tree is full
    function isFull(MerkleTree storage tree) internal view returns (bool full) {
        full = tree.nextIndex == (1 << tree.config.depth);
    }

    /// @notice Whether the Merkle tree has been initialized
    /// @param tree The tree to check if it has been initialized
    /// @return initialized Whether the Merkle tree has been initialized
    function isInitialized(MerkleTree storage tree) internal view returns (bool initialized) {
        initialized = tree.config.depth != 0;
    }

    /// @notice Initialize the Merkle tree
    /// @param tree The tree to initialize
    /// @param config_ The config to use for the Merkle tree
    function initialize(MerkleTree storage tree, MerkleTreeConfig memory config_) internal {
        tree.config = config_;
        tree.nextIndex = 0;
        tree.root = BN254.ScalarField.wrap(MerkleZeros.getZeroValue(tree.config.depth));
        if (tree.config.storeRoots) {
            tree.rootHistory[tree.root] = true;
        }

        // Initialize the sibling path array
        tree.siblingPath = new BN254.ScalarField[](tree.config.depth);
        for (uint256 i = 0; i < tree.config.depth; ++i) {
            tree.siblingPath[i] = zeroValue(i);
        }
    }

    /// @notice Returns the root of the tree
    /// @param tree The tree to get the root of
    /// @return The root of the tree
    function getRoot(MerkleTree storage tree) internal view returns (BN254.ScalarField) {
        return tree.root;
    }

    /// @notice Returns whether the given root is in the history of the tree
    /// @param tree The tree to check the root history of
    /// @param historicalRoot The root to check
    /// @return Whether the root is in the history of the tree
    function rootInHistory(MerkleTree storage tree, BN254.ScalarField historicalRoot) internal view returns (bool) {
        require(tree.config.storeRoots, RootHistoryDisabled());
        return tree.rootHistory[historicalRoot];
    }

    /* solhint-disable function-max-lines */
    /// @notice Insert a leaf into the tree
    /// @param tree The tree to insert the leaf into
    /// @param leaf The leaf to insert
    /// @param hasher The hasher to use for computing Merkle hashes
    function insertLeaf(MerkleTree storage tree, BN254.ScalarField leaf, IHasher hasher) internal {
        // Compute the hash of the leaf into the tree
        uint256 idx = tree.nextIndex;
        if (idx > DarkpoolConstants.MAX_MERKLE_LEAVES - 1) revert MerkleTreeFull();

        uint256 leafUint = BN254.ScalarField.unwrap(leaf);
        uint256[] memory sisterLeaves = new uint256[](tree.siblingPath.length);
        for (uint256 i = 0; i < tree.siblingPath.length; ++i) {
            sisterLeaves[i] = BN254.ScalarField.unwrap(tree.siblingPath[i]);
        }
        uint256[] memory hashes = hasher.merkleHash(idx, leafUint, sisterLeaves);

        // Update the tree
        ++tree.nextIndex;
        BN254.ScalarField newRoot = BN254.ScalarField.wrap(hashes[hashes.length - 1]);
        tree.root = newRoot;
        if (tree.config.storeRoots) {
            tree.rootHistory[newRoot] = true;
        }

        // Update the sibling paths, switching between left and right nodes as appropriate
        // `subtreeFilled` maintains whether the subtree rooted at the current node is full
        // This is initially true, as the current node is the leaf being inserted
        bool subtreeFilled = true;
        uint256 depth = tree.config.depth;
        for (uint256 height = 0; height < depth; ++height) {
            // Compute the insertion coordinates at the current height
            uint256 idxAtHeight = idx >> height;
            bool isRightChild = (idxAtHeight & 1) == 1;

            // If the subtree is full, we need to switch the sibling path entry at this height
            if (subtreeFilled) {
                if (isRightChild) {
                    // Right node, the new sibling is in a new sub-tree, and is the zero value
                    // for this depth in the tree
                    tree.siblingPath[height] = zeroValue(height);
                } else {
                    // Left node, the new sibling is the intermediate hash computed in the merkle insertion
                    tree.siblingPath[height] = BN254.ScalarField.wrap(hashes[height]);
                }
            }

            // The parent's subtree is full if the current node is the right child, and its subtree is full
            subtreeFilled = isRightChild && subtreeFilled;

            // Emit an event for indexers to track the opening of the current insertion
            emit MerkleOpeningNode(
                uint8(depth - height), uint128(isRightChild ? idxAtHeight - 1 : idxAtHeight + 1), sisterLeaves[height]
            );
        }

        // Log the updates to the Merkle tree after an insertion
        emit MerkleInsertion(uint128(idx), leafUint);
    }
    /* solhint-enable function-max-lines */
}

// SPDX-License-Identifier: MIT
// solhint-disable func-name-mixedcase
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { HasherTest } from "./Hasher.t.sol";
import { MerkleMountainLib } from "renegade-lib/merkle/MerkleMountain.sol";

contract MerkleMountainTest is HasherTest {
    MerkleMountainLib.MerkleMountainRange private mountain;

    /// @notice Test the root after a single insert
    function test_rootAfterSingleInsert() public {
        uint256 depth = randomUint(5, 32);

        uint256[] memory inputs = new uint256[](1);
        inputs[0] = randomFelt();
        uint256 expectedRoot = runMerkleRootReferenceImpl(depth, inputs);

        MerkleMountainLib.insertLeaf(mountain, depth, BN254.ScalarField.wrap(inputs[0]), hasher);
        BN254.ScalarField actualRoot = MerkleMountainLib.getRoot(mountain, depth);
        assertEq(BN254.ScalarField.unwrap(actualRoot), expectedRoot);

        bool rootInHistory = MerkleMountainLib.rootInHistory(mountain, actualRoot);
        assertEq(rootInHistory, true);
    }

    /// @notice Test the root after incremental insertions
    function test_rootAfterIncrementalInserts() public {
        uint256 depth = randomUint(5, 32);
        uint256 nInserts = randomUint(1, 10);
        uint256[] memory inputs = new uint256[](nInserts);
        for (uint256 i = 0; i < nInserts; i++) {
            inputs[i] = randomFelt();

            // Build a partial input to get the expected root
            uint256[] memory tempInputs = new uint256[](i + 1);
            for (uint256 j = 0; j <= i; j++) {
                tempInputs[j] = inputs[j];
            }
            uint256 expectedRoot = runMerkleRootReferenceImpl(depth, tempInputs);

            BN254.ScalarField leaf = BN254.ScalarField.wrap(inputs[i]);
            MerkleMountainLib.insertLeaf(mountain, depth, leaf, hasher);

            // Check the root
            BN254.ScalarField actualRoot = MerkleMountainLib.getRoot(mountain, depth);
            assertEq(BN254.ScalarField.unwrap(actualRoot), expectedRoot);

            // Check the root's history
            bool rootInHistory = MerkleMountainLib.rootInHistory(mountain, actualRoot);
            assertEq(rootInHistory, true);
        }
    }

    /// @notice Test the root after a number of inserts
    function test_mountainRangeRootAfterMultipleInserts() public {
        uint256 depth = randomUint(5, 32);
        uint256 nInserts = randomUint(1, 20);
        uint256[] memory inputs = new uint256[](nInserts);
        for (uint256 i = 0; i < nInserts; i++) {
            inputs[i] = randomFelt();
        }

        uint256 expectedRoot = runMerkleRootReferenceImpl(depth, inputs);
        for (uint256 i = 0; i < nInserts; i++) {
            MerkleMountainLib.insertLeaf(mountain, depth, BN254.ScalarField.wrap(inputs[i]), hasher);
        }
        BN254.ScalarField actualRoot = MerkleMountainLib.getRoot(mountain, depth);
        assertEq(BN254.ScalarField.unwrap(actualRoot), expectedRoot);

        bool rootInHistory = MerkleMountainLib.rootInHistory(mountain, actualRoot);
        assertEq(rootInHistory, true);
    }

    /// @notice Fill up an active sub-tree and insert into a new sub-tree
    function test_fullActiveSubTree_Insert() public {
        uint256 depth = randomUint(2, 8);

        // Build insert data
        uint256 nInserts = (1 << depth);
        uint256[] memory inputs = new uint256[](nInserts);
        for (uint256 i = 0; i < nInserts; i++) {
            inputs[i] = randomFelt();
        }

        // Fill up the sub-tree and check the root
        uint256 expectedRoot = runMerkleRootReferenceImpl(depth, inputs);
        for (uint256 i = 0; i < nInserts; i++) {
            BN254.ScalarField leaf = BN254.ScalarField.wrap(inputs[i]);
            MerkleMountainLib.insertLeaf(mountain, depth, leaf, hasher);
        }
        BN254.ScalarField actualRoot = MerkleMountainLib.getRoot(mountain, depth);
        assertEq(BN254.ScalarField.unwrap(actualRoot), expectedRoot);

        bool rootInHistory = MerkleMountainLib.rootInHistory(mountain, actualRoot);
        assertEq(rootInHistory, true);

        // Insert into a new sub-tree and check the root
        uint256[] memory newInserts = new uint256[](1);
        newInserts[0] = randomFelt();
        uint256 expectedNewRoot = runMerkleRootReferenceImpl(depth, newInserts);

        BN254.ScalarField newLeaf = BN254.ScalarField.wrap(newInserts[0]);
        MerkleMountainLib.insertLeaf(mountain, depth, newLeaf, hasher);

        // Check the new root, it should be the root of a new Merkle tree with only the
        // latest leaf inserted
        BN254.ScalarField actualNewRoot = MerkleMountainLib.getRoot(mountain, depth);
        assertEq(BN254.ScalarField.unwrap(actualNewRoot), expectedNewRoot);

        // Both the original and new roots should be in the history
        bool originalRootInHistory = MerkleMountainLib.rootInHistory(mountain, actualRoot);
        assertEq(originalRootInHistory, true);
        bool newRootInHistory = MerkleMountainLib.rootInHistory(mountain, actualNewRoot);
        assertEq(newRootInHistory, true);
    }

    /// @notice Test inserting into multiple sub-trees
    function test_multipleSubTrees_Insert() public {
        uint256 depth1 = randomUint(5, 10);
        uint256 depth2 = randomUint(depth1, 32);

        // Build insert data
        uint256 nInserts1 = randomUint(1, 20);
        uint256 nInserts2 = randomUint(1, 20);
        uint256[] memory inputs1 = new uint256[](nInserts1);
        uint256[] memory inputs2 = new uint256[](nInserts2);
        for (uint256 i = 0; i < nInserts1; i++) {
            inputs1[i] = randomFelt();
        }
        for (uint256 i = 0; i < nInserts2; i++) {
            inputs2[i] = randomFelt();
        }

        // Insert into the first sub-tree
        uint256 expectedRoot1 = runMerkleRootReferenceImpl(depth1, inputs1);
        for (uint256 i = 0; i < nInserts1; i++) {
            BN254.ScalarField leaf = BN254.ScalarField.wrap(inputs1[i]);
            MerkleMountainLib.insertLeaf(mountain, depth1, leaf, hasher);
        }
        BN254.ScalarField actualRoot1 = MerkleMountainLib.getRoot(mountain, depth1);
        assertEq(BN254.ScalarField.unwrap(actualRoot1), expectedRoot1);

        // Insert into the second sub-tree
        uint256 expectedRoot2 = runMerkleRootReferenceImpl(depth2, inputs2);
        for (uint256 i = 0; i < nInserts2; i++) {
            BN254.ScalarField leaf = BN254.ScalarField.wrap(inputs2[i]);
            MerkleMountainLib.insertLeaf(mountain, depth2, leaf, hasher);
        }
        BN254.ScalarField actualRoot2 = MerkleMountainLib.getRoot(mountain, depth2);
        assertEq(BN254.ScalarField.unwrap(actualRoot2), expectedRoot2);

        // Both the original and new roots should be in the history
        bool originalRootInHistory = MerkleMountainLib.rootInHistory(mountain, actualRoot1);
        assertEq(originalRootInHistory, true);
        bool newRootInHistory = MerkleMountainLib.rootInHistory(mountain, actualRoot2);
        assertEq(newRootInHistory, true);
    }
}

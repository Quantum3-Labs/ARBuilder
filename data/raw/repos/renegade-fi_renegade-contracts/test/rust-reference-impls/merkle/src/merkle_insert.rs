//! Handler for inserting elements into a Merkle tree sequentially

use renegade_constants::Scalar;
use renegade_crypto::hash::compute_poseidon_hash;

use crate::{
    util::{get_merkle_zero, print_scalar_result},
    InsertAndGetRootArgs,
};

// We want to be able to test the following:
// 1. Root after insert
// 2. Sibling path after insert
//
//

/// Compute the root after inserting elements into a Merkle tree sequentially
pub(crate) fn handle_insert_get_root(args: InsertAndGetRootArgs) {
    // Parse input values to Scalars
    let inputs: Vec<Scalar> = args
        .inputs
        .iter()
        .map(|s| Scalar::from_decimal_string(s).unwrap())
        .collect();

    let tree = TestMerkleTree::new(args.depth, inputs);
    let root = tree.root();
    print_scalar_result(root);
}

/// A simple Merkle tree query implementation
struct TestMerkleTree {
    /// The height of the tree
    height: u64,
    /// The leaves of the tree
    leaves: Vec<Scalar>,
    /// The zeros at each height
    zeros: Vec<Scalar>,
}

impl TestMerkleTree {
    /// Create a new Merkle tree
    pub fn new(height: u64, leaves: Vec<Scalar>) -> Self {
        let zeros = (0..=height).map(|h| get_merkle_zero(h as usize)).collect();
        Self {
            height,
            leaves,
            zeros,
        }
    }

    /// Update the leaf at the given index
    #[cfg(test)]
    pub fn update(&mut self, index: u64, new_leaf: Scalar) {
        if self.leaves.len() <= index as usize {
            self.leaves.resize(index as usize + 1, self.zeros[0]);
        }
        self.leaves[index as usize] = new_leaf;
    }

    /// The number of leaves at the given height
    fn max_leaves_at_height(&self, height: u64) -> u64 {
        let depth = self.height - height;
        1 << depth
    }

    /// Get the root of the tree
    pub fn root(&self) -> Scalar {
        self.get_node(self.height, 0 /* idx */)
    }

    /// Whether or not the subtree at the given coordinates is empty
    fn subtree_empty(&self, height: u64, idx: u64) -> bool {
        let full_leaves = self.leaves.len() as u64;
        let idx_first_leaf = idx * (1 << height);

        full_leaves < idx_first_leaf
    }

    /// Get the node at the given height and index
    fn get_node(&self, height: u64, idx: u64) -> Scalar {
        // Bounds checks
        assert!(height <= self.height, "Height out of bounds");
        assert!(
            idx < self.max_leaves_at_height(height),
            "Index out of bounds"
        );

        // Base case: leaf node
        if height == 0 {
            let zero_leaf = self.zeros[0];
            return self.leaves.get(idx as usize).copied().unwrap_or(zero_leaf);
        }

        // If the subtree is empty, return the zero value for this height
        if self.subtree_empty(height, idx) {
            return self.zeros[height as usize];
        }

        // Otherwise, recursively evaluate the tree
        let left_idx = 2 * idx;
        let right_idx = left_idx + 1;
        let left_node = self.get_node(height - 1, left_idx);
        let right_node = self.get_node(height - 1, right_idx);
        compute_poseidon_hash(&[left_node, right_node])
    }
}

#[cfg(test)]
mod tree_tests {
    use rand::thread_rng;

    use crate::util::build_full_arkworks_tree;

    use super::*;

    const TEST_TREE_HEIGHT: u64 = 10;

    #[test]
    fn test_tree_empty() {
        let tree = TestMerkleTree::new(TEST_TREE_HEIGHT, vec![]);
        assert_eq!(tree.root(), get_merkle_zero(TEST_TREE_HEIGHT as usize));
    }

    #[test]
    fn test_tree_single_leaf() {
        let mut rng = thread_rng();
        let leaf = Scalar::random(&mut rng);
        let tree = TestMerkleTree::new(TEST_TREE_HEIGHT, vec![leaf]);

        let mut expected_root = leaf;
        for height in 0..TEST_TREE_HEIGHT {
            let zero = get_merkle_zero(height as usize);
            expected_root = compute_poseidon_hash(&[expected_root, zero]);
        }

        assert_eq!(tree.root(), expected_root);
    }

    #[test]
    fn test_against_arkworks() {
        const N: usize = 100;
        let mut rng = thread_rng();
        let mut ark_tree = build_full_arkworks_tree(TEST_TREE_HEIGHT as usize, vec![]);
        let mut test_tree = TestMerkleTree::new(TEST_TREE_HEIGHT, vec![]);

        let new_leaf = Scalar::random(&mut rng);
        test_tree.update(0, new_leaf);
        ark_tree.update(0, &new_leaf.inner()).unwrap();

        for i in 0..N {
            let leaf = Scalar::random(&mut rng);
            ark_tree.update(i, &leaf.inner()).unwrap();
            test_tree.update(i as u64, leaf);

            // Check that the roots align after each insert
            let ark_root = ark_tree.root();
            let test_root = test_tree.root().inner();
            assert_eq!(test_root, ark_root);
        }
    }
}

//! Utility functions for the hashing reference implementation

use std::{borrow::Borrow, iter};

use ark_crypto_primitives::{
    crh::{CRHScheme, TwoToOneCRHScheme},
    merkle_tree::{Config, IdentityDigestConverter, MerkleTree},
};
use common::merkle_helpers::generate_leaf_zero_value;
use itertools::Itertools;
use rand::{thread_rng, Rng};
use renegade_constants::{Scalar, ScalarField};
use renegade_crypto::hash::compute_poseidon_hash;

// --- Hashing --- //

/// Get the merkle tree zero value for a given height
pub fn get_merkle_zero(height: usize) -> Scalar {
    let mut curr = generate_leaf_zero_value();
    for _ in 0..height {
        curr = compute_poseidon_hash(&[curr, curr]);
    }

    curr
}

/// Hash the input through the Merkle tree using the given sister nodes
///
/// Returns the incremental results at each level, representing the updated values to the insertion path
pub fn hash_merkle(idx: u64, input: Scalar, sister_leaves: &[Scalar]) -> Vec<Scalar> {
    let mut results = Vec::new();
    let mut current = input;
    let mut current_idx = idx;

    for sister in sister_leaves.iter().copied() {
        // The input is a left-hand node if the index is even at this level
        let inputs = if current_idx % 2 == 0 {
            [current, sister]
        } else {
            [sister, current]
        };

        current = compute_poseidon_hash(&inputs);
        results.push(current);
        current_idx /= 2;
    }

    results
}

// --- Test Helpers --- //

pub struct IdentityHasher;
impl CRHScheme for IdentityHasher {
    type Input = ScalarField;
    type Output = ScalarField;
    type Parameters = ();

    fn setup<R: Rng>(_: &mut R) -> Result<Self::Parameters, ark_crypto_primitives::Error> {
        Ok(())
    }

    fn evaluate<T: Borrow<Self::Input>>(
        _parameters: &Self::Parameters,
        input: T,
    ) -> Result<Self::Output, ark_crypto_primitives::Error> {
        Ok(*input.borrow())
    }
}

/// A dummy hasher to build an arkworks Merkle tree on top of
pub struct Poseidon2Hasher;
impl TwoToOneCRHScheme for Poseidon2Hasher {
    type Input = ScalarField;
    type Output = ScalarField;
    type Parameters = ();

    fn setup<R: Rng>(_: &mut R) -> Result<Self::Parameters, ark_crypto_primitives::Error> {
        Ok(())
    }

    fn evaluate<T: Borrow<Self::Input>>(
        _parameters: &Self::Parameters,
        left_input: T,
        right_input: T,
    ) -> Result<Self::Output, ark_crypto_primitives::Error> {
        let lhs = Scalar::new(*left_input.borrow());
        let rhs = Scalar::new(*right_input.borrow());
        let res = compute_poseidon_hash(&[lhs, rhs]);

        Ok(res.inner())
    }

    fn compress<T: Borrow<Self::Output>>(
        parameters: &Self::Parameters,
        left_input: T,
        right_input: T,
    ) -> Result<Self::Output, ark_crypto_primitives::Error> {
        <Self as TwoToOneCRHScheme>::evaluate(parameters, left_input, right_input)
    }
}

pub struct MerkleConfig {}
impl Config for MerkleConfig {
    type Leaf = ScalarField;
    type LeafDigest = ScalarField;
    type InnerDigest = ScalarField;

    type LeafHash = IdentityHasher;
    type TwoToOneHash = Poseidon2Hasher;
    type LeafInnerDigestConverter = IdentityDigestConverter<ScalarField>;
}

/// Build an arkworks tree and fill it with random values
pub fn build_arkworks_tree(height: usize, n_leaves: usize) -> MerkleTree<MerkleConfig> {
    let mut rng = thread_rng();
    let leaves = (0..n_leaves)
        .map(|_| Scalar::random(&mut rng))
        .collect_vec();

    build_arkworks_tree_with_leaves(height, &leaves)
}

/// Build a full arkworks tree with the given leaves
///
/// Pads the set of leaves to fill the tree
pub fn build_full_arkworks_tree(height: usize, leaves: Vec<Scalar>) -> MerkleTree<MerkleConfig> {
    let expected_leaves = 1 << height;
    let zero_leaf = get_merkle_zero(0);
    let leaves = leaves
        .into_iter()
        .chain(iter::repeat(zero_leaf))
        .take(expected_leaves)
        .collect_vec();

    build_arkworks_tree_with_leaves(height, &leaves)
}

/// Build an arkworks tree with the given leaves
///
/// Leaves must fill the tree
pub fn build_arkworks_tree_with_leaves(
    height: usize,
    leaves: &[Scalar],
) -> MerkleTree<MerkleConfig> {
    let expected_n_leaves = 1 << height;
    assert!(
        leaves.len() == expected_n_leaves,
        "Number of leaves must fill the tree"
    );

    let inner_scalars: Vec<ScalarField> = leaves.iter().map(Scalar::inner).collect();
    MerkleTree::<MerkleConfig>::new(&(), &(), inner_scalars).unwrap()
}

// --- Solidity FFI Helpers --- //

/// Print the given scalar as an FFI result
pub fn print_scalar_result(scalar: Scalar) {
    let res_hex = format!("{:x}", scalar.to_biguint());
    println!("RES:0x{res_hex}");
}

/// Print a string result
pub fn print_string_result(s: &str) {
    println!("RES:{}", s);
}

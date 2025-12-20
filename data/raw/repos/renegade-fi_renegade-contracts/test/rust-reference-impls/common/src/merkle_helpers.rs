//! Helper functions for merkle tree operations

use renegade_constants::{Scalar, MERKLE_HEIGHT};
use renegade_crypto::hash::compute_poseidon_hash;
use tiny_keccak::{Hasher, Keccak};

/// The string that is used to create leaf zero values
pub const LEAF_KECCAK_PREIMAGE: &str = "renegade";

/// Generate the zero values for each height in the Merkle tree
pub fn generate_zero_values() -> Vec<Scalar> {
    let mut result = vec![generate_leaf_zero_value()];
    for height in 1..=MERKLE_HEIGHT {
        let last_zero = result[height - 1];
        let next_zero = compute_poseidon_hash(&[last_zero, last_zero]);
        result.push(next_zero);
    }
    result
}

/// Generate the zero value for a leaf in the Merkle tree
pub fn generate_leaf_zero_value() -> Scalar {
    // Create a Keccak-256 hasher
    let mut hasher = Keccak::v256();

    // Prepare input and output buffers
    let input = LEAF_KECCAK_PREIMAGE.as_bytes();
    let mut output = [0u8; 32]; // 256 bits = 32 bytes

    // Compute the hash
    hasher.update(input);
    hasher.finalize(&mut output);

    Scalar::from_be_bytes_mod_order(&output)
}

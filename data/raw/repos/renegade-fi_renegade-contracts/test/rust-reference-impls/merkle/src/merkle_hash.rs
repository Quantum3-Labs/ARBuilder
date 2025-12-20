/// Hash through a Merkle tree
use renegade_constants::Scalar;
use renegade_crypto::fields::scalar_to_biguint;

use crate::{util, MerkleHashArgs};

/// Handle the Merkle hash operation
pub(crate) fn handle_merkle_hash(args: MerkleHashArgs) {
    if args.sister_leaves.len() != args.depth as usize {
        eprintln!(
            "Expected {} sister leaves, got {}",
            args.depth,
            args.sister_leaves.len()
        );
        std::process::exit(1);
    }

    let input = Scalar::from_decimal_string(&args.input).unwrap();

    // Parse sister leaves directly from arguments
    let sister_leaves: Vec<Scalar> = args
        .sister_leaves
        .iter()
        .map(|s| Scalar::from_decimal_string(s).unwrap())
        .collect();

    let results = util::hash_merkle(args.idx, input, &sister_leaves);

    // Output results as space-separated decimal values
    let result_strings: Vec<String> = results
        .iter()
        .map(|r| scalar_to_biguint(r).to_string())
        .collect();

    let res_str = result_strings.join(" ");
    util::print_string_result(&res_str);
}

#[cfg(test)]
mod tests {
    //! We test the Merkle tree helper above against the reference implementation in Arkworks
    //! for a known reference implementation.
    //!
    //! It is difficult to test the huff contracts against the Arkworks impl because the Arkworks impl
    //! handles deep trees very inefficiently, making a 32-depth tree impossible to run.
    //!
    //! Instead, we opt to test our helper against Arkworks on a shallower tree, thereby testing the
    //! huff implementation only transitively.

    use rand::{thread_rng, Rng};
    use renegade_constants::Scalar;

    use crate::util::{build_arkworks_tree, hash_merkle};

    /// The height of the Merkle tree
    const TEST_TREE_HEIGHT: usize = 10;
    /// The number of leaves in the tree
    const N_LEAVES: usize = 1 << (TEST_TREE_HEIGHT - 1);

    /// Test the Merkle helper against an arkworks tree
    #[test]
    fn test_merkle_tree() {
        // Build an arkworks tree and fill it with random values
        let mut rng = thread_rng();
        let mut tree = build_arkworks_tree(TEST_TREE_HEIGHT, N_LEAVES);

        // Choose a random index to update into
        let idx = rng.gen_range(0..N_LEAVES);
        let input = Scalar::random(&mut rng);

        // Get a sibling path for the input
        let path = tree.generate_proof(idx).unwrap();
        let mut sister_scalars = vec![Scalar::new(path.leaf_sibling_hash)];
        sister_scalars.extend(path.auth_path.into_iter().rev().map(Scalar::new));

        // Get the updated path
        let res = hash_merkle(idx as u64, input, &sister_scalars);
        let new_root = res.last().unwrap();

        // Update the tree with the input
        tree.update(idx, &input.inner()).unwrap();
        assert_eq!(tree.root(), new_root.inner());
    }
}

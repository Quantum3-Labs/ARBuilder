//! Handlers for cli hash operations
use renegade_constants::Scalar;
use renegade_crypto::hash::compute_poseidon_hash;

use crate::util;
use crate::SpongeHashArgs;

/// Handle the Sponge hash operation
pub(crate) fn handle_sponge_hash(args: SpongeHashArgs) {
    // Parse input values to Scalars
    let inputs: Vec<Scalar> = args
        .inputs
        .iter()
        .map(|s| Scalar::from_decimal_string(s).unwrap())
        .collect();

    let res = compute_poseidon_hash(&inputs);
    util::print_scalar_result(res);
}

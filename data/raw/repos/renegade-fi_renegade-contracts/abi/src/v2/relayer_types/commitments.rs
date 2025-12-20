//! Commitment type conversions

use renegade_circuit_types_v2::state_wrapper::PartialCommitment;
use renegade_crypto_v2::fields::scalar_to_u256;

use crate::v2::IDarkpoolV2;

impl From<PartialCommitment> for IDarkpoolV2::PartialCommitment {
    fn from(partial_commitment: PartialCommitment) -> Self {
        Self {
            privateCommitment: scalar_to_u256(&partial_commitment.private_commitment),
            partialPublicCommitment: scalar_to_u256(&partial_commitment.partial_public_commitment),
        }
    }
}

use common::abi_types::{PlonkProof, VerificationKey};
use mpc_relation::traits::Circuit;
use renegade_circuit_types::{traits::SingleProverCircuit, PlonkCircuit};
use renegade_constants::Scalar;

const NUM_INPUTS: usize = 10;

struct SumPowCircuit;
impl SingleProverCircuit for SumPowCircuit {
    type Statement = Scalar;
    type Witness = [Scalar; NUM_INPUTS];

    fn name() -> String {
        "sum-pow".to_string()
    }

    fn apply_constraints(
        witness_var: <Self::Witness as renegade_circuit_types::traits::CircuitBaseType>::VarType,
        statement_var: <Self::Statement as renegade_circuit_types::traits::CircuitBaseType>::VarType,
        cs: &mut PlonkCircuit,
    ) -> Result<(), mpc_plonk::errors::PlonkError> {
        let mut sum = cs.zero();
        for value in witness_var.iter() {
            sum = cs.add(sum, *value)?;
        }

        let sum_pow = cs.pow5(sum)?;
        cs.enforce_equal(sum_pow, statement_var)?;
        Ok(())
    }
}

/// Generate the verification key for the sum-pow circuit
pub fn generate_verification_key() -> VerificationKey {
    let renegade_vk = SumPowCircuit::verifying_key();
    VerificationKey::from(renegade_vk.as_ref().clone())
}

/// Generate a proof for the sum-pow circuit
pub fn generate_proof(inputs: Vec<Scalar>, expected: Scalar) -> PlonkProof {
    let statement = expected;
    let witness = inputs.try_into().unwrap();
    let proof = SumPowCircuit::prove(witness, statement).unwrap();
    proof.into()
}

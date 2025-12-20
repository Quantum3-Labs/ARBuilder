use common::abi_types::{PlonkProof, VerificationKey};
use mpc_relation::traits::Circuit;
use renegade_circuit_types::{traits::SingleProverCircuit, PlonkCircuit};
use renegade_constants::Scalar;

/// The mul two circuit
///
/// Takes as witness two values `a` and `b`, and a public input `c`
///
/// Constrains: `c = a * b`
struct MulTwoCircuit;
impl SingleProverCircuit for MulTwoCircuit {
    type Statement = Scalar;
    type Witness = [Scalar; 2];

    fn name() -> String {
        "mul-two".to_string()
    }

    fn apply_constraints(
        witness_var: <Self::Witness as renegade_circuit_types::traits::CircuitBaseType>::VarType,
        statement_var: <Self::Statement as renegade_circuit_types::traits::CircuitBaseType>::VarType,
        cs: &mut PlonkCircuit,
    ) -> Result<(), mpc_plonk::errors::PlonkError> {
        let prod = cs.mul(witness_var[0], witness_var[1])?;
        cs.enforce_equal(prod, statement_var)?;

        Ok(())
    }
}

/// Generate the verification key for the mul-two circuit
pub fn generate_verification_key() -> VerificationKey {
    let renegade_vk = MulTwoCircuit::verifying_key();
    VerificationKey::from(renegade_vk.as_ref().clone())
}

/// Generate a proof for the mul-two circuit
pub fn generate_proof(a: Scalar, b: Scalar, c: Scalar) -> PlonkProof {
    let statement = c;
    let witness = [a, b];
    let proof = MulTwoCircuit::prove(witness, statement).unwrap();
    proof.into()
}

//! Defines a circuit that checks if the witness is a permutation of the public input

use common::abi_types::{PlonkProof, VerificationKey};
use mpc_plonk::errors::PlonkError;
use mpc_relation::{traits::Circuit, Variable};
use renegade_circuit_macros::circuit_type;
use renegade_circuit_types::{traits::*, PlonkCircuit};
use renegade_constants::{Scalar, ScalarField};

// --- Witness & Statement --- //

pub const N: usize = 5;
type PermutationWitness = [Scalar; N];

#[derive(Clone, Debug)]
#[circuit_type(singleprover_circuit)]
pub(super) struct PermutationStatement {
    /// A random challenge for the permutation check
    pub random_challenge: Scalar,
    /// The values that are permuted
    pub values: PermutationWitness,
}

// --- Circuit --- //

struct PermutationCircuit;
impl SingleProverCircuit for PermutationCircuit {
    type Statement = PermutationStatement;
    type Witness = PermutationWitness;

    fn name() -> String {
        "permutation".to_string()
    }

    fn apply_constraints(
        witness_var: <Self::Witness as CircuitBaseType>::VarType,
        statement_var: <Self::Statement as CircuitBaseType>::VarType,
        cs: &mut PlonkCircuit,
    ) -> Result<(), mpc_plonk::errors::PlonkError> {
        let challenge = statement_var.random_challenge;
        let statement_product = Self::challenge_product(&statement_var.values, challenge, cs)?;
        let witness_product = Self::challenge_product(&witness_var, challenge, cs)?;

        cs.enforce_equal(statement_product, witness_product)?;
        Ok(())
    }
}

impl PermutationCircuit {
    // --- Private Helpers --- //

    /// Computes the product of the values, shifted by the challenge:
    /// i.e. (x_1 + r) * (x_2 + r) * ... * (x_n + r)
    fn challenge_product(
        values: &[Variable],
        challenge: Variable,
        cs: &mut PlonkCircuit,
    ) -> Result<Variable, PlonkError> {
        let mut product = cs.one();
        for v in values {
            let challenge_shift = cs.add(challenge, *v)?;
            product = cs.mul(product, challenge_shift)?;
        }

        Ok(product)
    }
}

/// Generate the verification key for the permutation circuit
pub fn generate_verification_key() -> VerificationKey {
    let renegade_vk = PermutationCircuit::verifying_key();
    VerificationKey::from(renegade_vk.as_ref().clone())
}

/// Generate a proof for the permutation circuit
pub fn generate_proof(statement: PermutationStatement, witness: PermutationWitness) -> PlonkProof {
    let proof = PermutationCircuit::prove(witness, statement).unwrap();
    proof.into()
}

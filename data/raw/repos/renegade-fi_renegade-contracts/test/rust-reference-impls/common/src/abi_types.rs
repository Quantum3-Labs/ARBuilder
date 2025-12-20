//! Types for the verifier solidity interface

use alloy::{primitives::U256, sol_types::sol};
use ark_bn254::{Fq as BnField, Fr as BnScalar, G1Affine as BnG1, G2Affine as BnG2};
use ark_ec::AffineRepr;
use itertools::Itertools;
use mpc_relation::proof_linking::GroupLayout;
use num_bigint::BigUint;
use renegade_circuit_types::PlonkLinkProof;
use renegade_constants::{Scalar, SystemCurve};

// -------------
// | ABI Types |
// -------------

sol! {
    /// @dev The number of wire types in the arithmetization
    uint256 constant NUM_WIRE_TYPES = 5;
    /// @dev The number of selectors in the arithmetization
    uint256 constant NUM_SELECTORS = 13;
    /// @notice type alias for BN254::ScalarField
    type ScalarField is uint256;
    /// @notice type alias for BN254::BaseField
    type BaseField is uint256;

    // @dev G1 group element, a point on the BN254 curve
    struct G1Point {
        BaseField x;
        BaseField y;
    }

    // @dev G2 group element where x \in Fp2 = c0 + c1 * X
    struct G2Point {
        BaseField x0;
        BaseField x1;
        BaseField y0;
        BaseField y1;
    }

    /// @title A Plonk proof
    /// @notice This matches the Rust implementation from mpc-jellyfish
    struct PlonkProof {
        /// @dev The commitments to the wire polynomials
        G1Point[NUM_WIRE_TYPES] wire_comms;
        /// @dev The commitment to the grand product polynomial encoding the permutation argument
        G1Point z_comm;
        /// @dev The commitments to the split quotient polynomials
        G1Point[NUM_WIRE_TYPES] quotient_comms;
        /// @dev The opening proof of evaluations at challenge point `zeta`
        G1Point w_zeta;
        /// @dev The opening proof of evaluations at challenge point `zeta * omega`
        G1Point w_zeta_omega;
        /// @dev The evaluations of the wire polynomials at the challenge point `zeta`
        ScalarField[NUM_WIRE_TYPES] wire_evals;
        /// @dev The evaluations of the permutation polynomials at the challenge point `zeta`
        ScalarField[NUM_WIRE_TYPES - 1] sigma_evals;
        /// @dev The evaluation of the grand product polynomial at the challenge point `zeta * omega`
        ScalarField z_bar;
    }

    /// @title A Plonk verification key
    struct VerificationKey {
        /// The number of gates in the circuit
        uint64 n;
        /// The number of public inputs to the circuit
        uint64 l;
        /// The constants used to generate the cosets of the evaluation domain
        ScalarField[NUM_WIRE_TYPES] k;
        /// The commitments to the selector polynomials
        G1Point[NUM_SELECTORS] q_comms;
        /// The commitments to the permutation polynomials
        G1Point[NUM_WIRE_TYPES] sigma_comms;
        /// The generator of G1
        G1Point g;
        /// The generator of G2
        G2Point h;
        /// The secret evaluation point multiplied by the generator of G2
        G2Point x_h;
    }

    /// @title A proof of a group of linked inputs between two Plonk proofs
    struct LinkingProof {
        /// @dev The commitment to the linking quotient polynomial
        G1Point linking_quotient_poly_comm;
        /// @dev The opening proof of the linking polynomial
        G1Point linking_poly_opening;
    }

    /// @title A verification key for the proof linking relation
    struct ProofLinkingVK {
        /// @dev The generator of the subdomain over which the linked inputs are defined
        ScalarField link_group_generator;
        /// @dev The offset into the domain at which the subdomain begins
        uint256 link_group_offset;
        /// @dev The number of linked inputs, equivalently the size of the subdomain
        uint256 link_group_size;
    }
}

// ---------------
// | Conversions |
// ---------------

type SystemVkey = mpc_plonk::proof_system::structs::VerifyingKey<SystemCurve>;
type SystemProof = mpc_plonk::proof_system::structs::Proof<SystemCurve>;

impl From<SystemVkey> for VerificationKey {
    fn from(vkey: SystemVkey) -> Self {
        VerificationKey {
            n: vkey.domain_size as u64,
            l: vkey.num_inputs as u64,
            k: vkey
                .k
                .iter()
                .copied()
                .map(u256_from_scalar)
                .collect_vec()
                .try_into()
                .unwrap(),
            q_comms: vkey
                .selector_comms
                .iter()
                .map(|c| convert_g1_point(c.0))
                .collect_vec()
                .try_into()
                .map_err(|_| "Failed to convert selector commitments to G1Point")
                .unwrap(),
            sigma_comms: vkey
                .sigma_comms
                .iter()
                .map(|c| convert_g1_point(c.0))
                .collect_vec()
                .try_into()
                .map_err(|_| "Failed to convert sigma commitments to G1Point")
                .unwrap(),
            g: convert_g1_point(vkey.open_key.g),
            h: convert_g2_point(vkey.open_key.h),
            x_h: convert_g2_point(vkey.open_key.beta_h),
        }
    }
}

impl From<SystemProof> for PlonkProof {
    fn from(proof: SystemProof) -> Self {
        PlonkProof {
            wire_comms: proof
                .wires_poly_comms
                .iter()
                .map(|c| convert_g1_point(c.0))
                .collect_vec()
                .try_into()
                .map_err(|_| "Failed to convert wire commitments to G1Point")
                .unwrap(),
            z_comm: convert_g1_point(proof.prod_perm_poly_comm.0),
            quotient_comms: proof
                .split_quot_poly_comms
                .iter()
                .map(|c| convert_g1_point(c.0))
                .collect_vec()
                .try_into()
                .map_err(|_| "Failed to convert quotient commitments to G1Point")
                .unwrap(),
            w_zeta: convert_g1_point(proof.opening_proof.0),
            w_zeta_omega: convert_g1_point(proof.shifted_opening_proof.0),
            wire_evals: proof
                .poly_evals
                .wires_evals
                .iter()
                .copied()
                .map(u256_from_scalar)
                .collect_vec()
                .try_into()
                .unwrap(),
            sigma_evals: proof
                .poly_evals
                .wire_sigma_evals
                .iter()
                .copied()
                .map(u256_from_scalar)
                .collect_vec()
                .try_into()
                .unwrap(),
            z_bar: u256_from_scalar(proof.poly_evals.perm_next_eval),
        }
    }
}

impl From<GroupLayout> for ProofLinkingVK {
    fn from(layout: GroupLayout) -> Self {
        let generator = layout.get_domain_generator();
        ProofLinkingVK {
            link_group_generator: u256_from_scalar(generator),
            link_group_offset: U256::from(layout.offset),
            link_group_size: U256::from(layout.size),
        }
    }
}

impl From<PlonkLinkProof> for LinkingProof {
    fn from(proof: PlonkLinkProof) -> Self {
        LinkingProof {
            linking_quotient_poly_comm: convert_g1_point(proof.quotient_commitment.0),
            linking_poly_opening: convert_g1_point(proof.opening_proof.proof),
        }
    }
}

// --- Conversion Helpers --- //

/// Create a `U256` from a `ScalarField`
fn u256_from_scalar(scalar: BnScalar) -> U256 {
    let bytes = Scalar::new(scalar).to_bytes_be();
    u256_from_bytes(&bytes)
}

/// Create a `U256` from a `BaseField`
fn u256_from_base_field(felt: BnField) -> U256 {
    let bigint = BigUint::from(felt);
    u256_from_bytes(&bigint.to_bytes_be())
}

/// Create a `U256` from big endian bytes
fn u256_from_bytes(bytes: &[u8]) -> U256 {
    let mut padded = [0u8; 32];
    let offset = 32 - bytes.len();
    padded[offset..].copy_from_slice(bytes);
    U256::from_be_bytes::<32>(padded)
}

/// Create a `G1Point` from a `BnG1`
fn convert_g1_point(point: BnG1) -> G1Point {
    G1Point {
        x: u256_from_base_field(point.x),
        y: u256_from_base_field(point.y),
    }
}

/// Create a `G2Point` from a `BnG2`
fn convert_g2_point(point: BnG2) -> G2Point {
    let x = point.x().unwrap();
    let y = point.y().unwrap();

    G2Point {
        x0: u256_from_base_field(x.c0),
        x1: u256_from_base_field(x.c1),
        y0: u256_from_base_field(y.c0),
        y1: u256_from_base_field(y.c1),
    }
}

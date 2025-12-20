mod mul_two;
mod permutation;
mod proof_link;
mod sum_pow;

use alloy_sol_types::SolValue;
use clap::{Parser, Subcommand};
use itertools::Itertools;
use permutation::PermutationStatement;
use proof_link::{ProductCircuitWitness, SumCircuitWitness};
use renegade_constants::Scalar;

// -------
// | CLI |
// -------

#[derive(Parser)]
#[command(
    author,
    version,
    about = "Reference implementation for PLONK circuit verification"
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Multiply two witness values and constrain their product to a public input
    MulTwo {
        #[command(subcommand)]
        action: MulTwoAction,
    },
    /// Compute (x₁ + x₂ + ... + xₙ)^5
    SumPow {
        #[command(subcommand)]
        action: SumPowAction,
    },
    /// Check if a witness is a permutation of a public input
    Permutation {
        #[command(subcommand)]
        action: PermutationAction,
    },
    /// Commands for the linked sum and product circuits
    ProofLink {
        #[command(subcommand)]
        action: ProofLinkAction,
    },
}

#[derive(Subcommand)]
enum MulTwoAction {
    /// Print the verification key for the mul-two circuit
    PrintVkey,
    /// Generate a proof for the mul-two circuit
    Prove {
        /// First witness value (as hex string)
        a: String,
        /// Second witness value (as hex string)
        b: String,
        /// Expected product (as hex string)
        c: String,
    },
}

#[derive(Subcommand)]
enum SumPowAction {
    /// Print the verification key for the sum-pow circuit
    PrintVkey,
    /// Generate a proof for the sum-pow circuit
    Prove {
        /// Input values to sum and raise to the fifth power (as hex strings)
        #[arg(required = true, num_args = 10)]
        inputs: Vec<String>,
        /// Expected result of (sum)^5 (as hex string)
        expected: String,
    },
}

#[derive(Subcommand)]
enum PermutationAction {
    /// Print the verification key for the permutation circuit
    PrintVkey,
    /// Generate a proof for the permutation circuit
    Prove {
        /// The random challenge (as hex string)
        #[arg(long)]
        random_challenge: String,
        /// The original values to permute (as hex strings)
        #[arg(long, required = true, num_args = permutation::N)]
        values: Vec<String>,
        /// The permuted values (as hex strings)
        #[arg(long, required = true, num_args = permutation::N)]
        permuted_values: Vec<String>,
    },
}

#[derive(Subcommand)]
enum ProofLinkAction {
    /// Generate verification key for the sum circuit
    GenSumVk,
    /// Generate verification key for the product circuit
    GenProdVk,
    /// Generate verification key for the linking relation
    GenLinkVk,
    /// Generate proofs for both circuits with a linking argument
    Prove {
        /// The shared witness values (as hex strings)
        #[arg(long, required = true, num_args = proof_link::LINKING_WITNESS_SIZE)]
        shared: Vec<String>,
        /// Private witness for sum circuit (as hex string)
        #[arg(long)]
        sum_private: String,
        /// Private witness for product circuit (as hex string)
        #[arg(long)]
        prod_private: String,
    },
}

// --------------
// | Entrypoint |
// --------------

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::MulTwo { action } => match action {
            MulTwoAction::PrintVkey => {
                let vk = mul_two::generate_verification_key();
                let encoded = vk.abi_encode();
                println!("RES:{}", hex::encode(encoded));
            }
            MulTwoAction::Prove { a, b, c } => {
                let a = Scalar::from_decimal_string(&a).unwrap();
                let b = Scalar::from_decimal_string(&b).unwrap();
                let c = Scalar::from_decimal_string(&c).unwrap();
                let proof = mul_two::generate_proof(a, b, c);
                let encoded = proof.abi_encode();
                println!("RES:{}", hex::encode(encoded));
            }
        },
        Commands::SumPow { action } => match action {
            SumPowAction::PrintVkey => {
                let vk = sum_pow::generate_verification_key();
                let encoded = vk.abi_encode();
                println!("RES:{}", hex::encode(encoded));
            }
            SumPowAction::Prove { inputs, expected } => {
                let inputs = inputs
                    .iter()
                    .map(|s| Scalar::from_decimal_string(s).unwrap())
                    .collect_vec();
                let expected = Scalar::from_decimal_string(&expected).unwrap();

                let proof = sum_pow::generate_proof(inputs, expected);
                let encoded = proof.abi_encode();
                println!("RES:{}", hex::encode(encoded));
            }
        },
        Commands::Permutation { action } => match action {
            PermutationAction::PrintVkey => {
                let vk = permutation::generate_verification_key();
                let encoded = vk.abi_encode();
                println!("RES:{}", hex::encode(encoded));
            }
            PermutationAction::Prove {
                random_challenge,
                values,
                permuted_values,
            } => {
                let random_challenge = Scalar::from_decimal_string(&random_challenge).unwrap();
                let statement_values: [Scalar; permutation::N] = values
                    .iter()
                    .map(|s| Scalar::from_decimal_string(s).unwrap())
                    .collect_vec()
                    .try_into()
                    .unwrap();
                let witness_values: [Scalar; permutation::N] = permuted_values
                    .iter()
                    .map(|s| Scalar::from_decimal_string(s).unwrap())
                    .collect_vec()
                    .try_into()
                    .unwrap();

                let witness = witness_values;
                let statement = PermutationStatement {
                    random_challenge,
                    values: statement_values,
                };

                let proof = permutation::generate_proof(statement, witness);
                let encoded = proof.abi_encode();
                println!("RES:{}", hex::encode(encoded));
            }
        },
        Commands::ProofLink { action } => match action {
            ProofLinkAction::GenSumVk => {
                let vk = proof_link::generate_sum_circuit_verification_key();
                let encoded = vk.abi_encode();
                println!("RES:{}", hex::encode(encoded));
            }
            ProofLinkAction::GenProdVk => {
                let vk = proof_link::generate_product_circuit_verification_key();
                let encoded = vk.abi_encode();
                println!("RES:{}", hex::encode(encoded));
            }
            ProofLinkAction::GenLinkVk => {
                let vk = proof_link::generate_sum_product_linking_verification_key();
                let encoded = vk.abi_encode();
                println!("RES:{}", hex::encode(encoded));
            }
            ProofLinkAction::Prove {
                shared,
                sum_private,
                prod_private,
            } => {
                let shared_vals: Vec<Scalar> = shared
                    .iter()
                    .map(|s| Scalar::from_decimal_string(s).unwrap())
                    .collect();
                let sum_private = Scalar::from_decimal_string(&sum_private).unwrap();
                let prod_private = Scalar::from_decimal_string(&prod_private).unwrap();

                let shared_array = shared_vals.try_into().unwrap();

                let sum_witness = SumCircuitWitness {
                    shared_witness: shared_array,
                    private_witness: sum_private,
                };
                let prod_witness = ProductCircuitWitness {
                    shared_witness: shared_array,
                    private_witness: prod_private,
                };

                let (sum_proof, prod_proof, link_proof) =
                    proof_link::generate_proofs(sum_witness, prod_witness);

                let encoded = (sum_proof, prod_proof, link_proof).abi_encode();
                println!("RES:{}", hex::encode(encoded));
            }
        },
    }
}

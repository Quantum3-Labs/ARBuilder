//! Utils for fetching and operating on Merkle openings

use alloy::{
    primitives::{TxHash, U256},
    providers::Provider,
    rpc::types::TransactionReceipt,
    sol_types::SolEventInterface,
};
use eyre::{Result, eyre};
use itertools::Itertools;
use num_bigint::BigUint;
use renegade_abi::v2::IDarkpoolV2::{self, IDarkpoolV2Events};
use renegade_circuit_types::{
    state_wrapper::StateWrapper,
    traits::{CircuitBaseType, SecretShareBaseType},
};
use renegade_common::types::merkle::MerkleAuthenticationPath;
use renegade_constants::{MERKLE_HEIGHT, Scalar};
use renegade_crypto::fields::{scalar_to_u256, u256_to_scalar};

use crate::util::darkpool::Darkpool;

// Helper function to size a vector (copied from proof_bundles since it's private)
fn size_vec<const N: usize, T>(vec: Vec<T>) -> [T; N] {
    let size = vec.len();
    if size != N {
        panic!("vector is not the correct size: expected {N}, got {size}");
    }
    vec.try_into().map_err(|_| ()).unwrap()
}

// -----------------
// | Merkle Proofs |
// -----------------

/// Find the Merkle opening for a state element
pub async fn find_state_element_opening<T>(
    state_element: &StateWrapper<T>,
    receipt: &TransactionReceipt,
) -> Result<MerkleAuthenticationPath>
where
    T: SecretShareBaseType + CircuitBaseType,
    T::ShareType: CircuitBaseType,
{
    let commitment = state_element.compute_commitment();
    parse_merkle_opening_from_receipt(commitment, receipt)
}

/// Fetch a Merkle opening for a given commitment in a tx
///
/// Takes the commitment and returns the sibling path used to hash the commitment into the
/// merkle tree
pub async fn fetch_merkle_opening(
    commitment: Scalar,
    darkpool: &Darkpool,
) -> Result<MerkleAuthenticationPath> {
    // 1. Find the commitment in the darkpool logs
    let (_, tx_hash) = find_commitment(commitment, darkpool).await?;

    // 2. Fetch all Merkle opening logs for the tx
    fetch_merkle_openings(commitment, tx_hash, darkpool).await
}

/// Find the given commitment in the Merkle insertion logs
///
/// Returns the index of the commitment in the Merkle tree, and the tx hash
async fn find_commitment(commitment: Scalar, darkpool: &Darkpool) -> Result<(u128, TxHash)> {
    let commitment_u256 = scalar_to_u256(&commitment);
    let block = darkpool.provider().get_block_number().await?;
    let from_block = block.saturating_sub(1000);
    let logs = darkpool
        .MerkleInsertion_filter()
        .topic2(commitment_u256)
        .from_block(from_block)
        .to_block(block)
        .query()
        .await?;

    let (data, log) = logs
        .last()
        .ok_or(eyre!("no logs found for MerkleInsertion"))?;
    Ok((data.index, log.transaction_hash.unwrap()))
}

/// Fetch the Merkle opening logs for a given tx hash
///
/// Returns the logs in order of increasing height (decreasing depth)
async fn fetch_merkle_openings(
    commitment: Scalar,
    tx_hash: TxHash,
    darkpool: &Darkpool,
) -> Result<MerkleAuthenticationPath> {
    let tx_receipt = darkpool
        .provider()
        .get_transaction_receipt(tx_hash)
        .await?
        .expect("no tx receipt");

    parse_merkle_opening_from_receipt(commitment, &tx_receipt)
}

/// Parse a Merkle opening from a tx receipt
///
/// Extracts MerkleOpeningNode events from the transaction receipt and returns them
/// sorted by increasing height (decreasing depth).
///
/// Returns a vector of (index, value) tuples representing the sibling nodes
pub fn parse_merkle_opening_from_receipt(
    commitment: Scalar,
    receipt: &TransactionReceipt,
) -> Result<MerkleAuthenticationPath> {
    let commitment_u256 = scalar_to_u256(&commitment);

    let mut commitment_found = false;
    let mut leaf_index = 0;
    let mut opening_index = 0;
    let mut all_sister_nodes = Vec::with_capacity(MERKLE_HEIGHT);
    for log in receipt.logs() {
        let log = match IDarkpoolV2::IDarkpoolV2Events::decode_log(&log.inner) {
            Ok(l) => l,
            Err(_) => continue,
        };

        match log.data {
            IDarkpoolV2Events::MerkleInsertion(data) => {
                if data.value == commitment_u256 {
                    commitment_found = true;
                    leaf_index = data.index;
                    break;
                } else {
                    opening_index += 1;
                }
            }
            IDarkpoolV2Events::MerkleOpeningNode(data) => {
                all_sister_nodes.push((data.depth, data.index, data.new_value));
            }
            _ => continue,
        }
    }

    if !commitment_found {
        return Err(eyre!("commitment not found in transaction"));
    }

    // Multiple insertions may have been made in this transaction. We want the `opening_index`th group of `MERKLE_HEIGHT` sister nodes
    let start_idx = opening_index * MERKLE_HEIGHT;
    let end_idx = start_idx + MERKLE_HEIGHT;
    let mut opening_nodes = all_sister_nodes[start_idx..end_idx].to_vec();

    // Sort by decreasing depth
    opening_nodes.sort_by_key(|(depth, _, _)| -(*depth as i8));
    let siblings = opening_nodes
        .into_iter()
        .map(|(_idx, i, v)| (i, v))
        .collect();
    Ok(build_authentication_path(leaf_index, commitment, siblings))
}

/// Build an authentication path from a vector of sibling nodes
fn build_authentication_path(
    leaf_index: u128,
    commitment: Scalar,
    siblings: Vec<(u128, U256)>,
) -> MerkleAuthenticationPath {
    let path_siblings = size_vec(
        siblings
            .into_iter()
            .map(|(_, v)| u256_to_scalar(&v))
            .collect_vec(),
    );

    MerkleAuthenticationPath {
        path_siblings,
        leaf_index: BigUint::from(leaf_index),
        value: commitment,
    }
}

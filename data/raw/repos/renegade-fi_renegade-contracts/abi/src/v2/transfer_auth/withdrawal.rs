//! Withdrawal authorization helpers

use alloy::{
    primitives::{keccak256, B256, U256},
    signers::{local::PrivateKeySigner, Error as SignerError, SignerSync},
    sol_types::SolValue,
};

use crate::v2::IDarkpoolV2::WithdrawalAuth;

/// Create a withdrawal authorization signature
///
/// The signature is over the hash of the newBalanceCommitment, matching what the contract expects.
pub fn create_withdrawal_auth(
    new_balance_commitment: U256,
    signer: &PrivateKeySigner,
) -> Result<WithdrawalAuth, SignerError> {
    // Sign the keccak hash of the commitment
    let commitment_bytes = new_balance_commitment.abi_encode();
    let commitment_hash = B256::from_slice(keccak256(&commitment_bytes).as_slice());

    let signature = signer.sign_hash_sync(&commitment_hash)?;
    let sig_bytes = signature.as_bytes().to_vec();
    Ok(WithdrawalAuth {
        signature: sig_bytes.into(),
    })
}

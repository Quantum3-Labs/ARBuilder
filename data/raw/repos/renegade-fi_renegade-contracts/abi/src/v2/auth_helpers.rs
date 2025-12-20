//! Authorization helpers for the V2 ABI

use alloy::{
    primitives::{keccak256, U256},
    signers::{local::PrivateKeySigner, Error as SignerError, SignerSync},
};

use crate::v2::IDarkpoolV2::SignatureWithNonce;

/// Generate a signature with a nonce for a given message
///
/// This is H(H(payload) || nonce)
pub fn sign_with_nonce(
    payload: &[u8],
    signer: &PrivateKeySigner,
) -> Result<SignatureWithNonce, SignerError> {
    // Pre-hash the payload
    let payload_digest = keccak256(payload);

    // Hash the payload with the nonce
    let nonce = U256::random();
    let nonce_bytes = nonce.to_be_bytes::<{ U256::BYTES }>();
    let full_payload = [payload_digest.as_slice(), nonce_bytes.as_slice()].concat();
    let digest = keccak256(&full_payload);

    let signature = signer.sign_hash_sync(&digest)?;
    let sig_bytes = signature.as_bytes().to_vec();
    Ok(SignatureWithNonce {
        nonce,
        signature: sig_bytes.into(),
    })
}

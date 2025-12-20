//! A test for paying a private relayer fee

use alloy::sol_types::SolValue;
use eyre::Result;
use renegade_abi::v2::{
    IDarkpoolV2::{ElGamalCiphertext, PrivateRelayerFeePaymentProofBundle, SignatureWithNonce},
    auth_helpers::sign_with_nonce,
};
use renegade_circuit_types::{
    PlonkProof,
    balance::DarkpoolStateBalance,
    note::{Note, NoteCiphertext},
};
use renegade_circuits::{
    singleprover_prove,
    test_helpers::random_elgamal_encryption_key,
    zk_circuits::fees::valid_private_relayer_fee_payment::{
        SizedValidPrivateRelayerFeePayment, ValidPrivateRelayerFeePaymentStatement,
        ValidPrivateRelayerFeePaymentWitness,
    },
};
use renegade_common::types::merkle::MerkleAuthenticationPath;
use test_helpers::{assert_eq_result, integration_test_async};

use crate::{
    test_args::TestArgs, tests::state_updates::setup_private_intent_private_balance,
    util::transactions::wait_for_tx_success,
};

/// Test paying a private relayer fee
pub async fn test_pay_private_relayer_fee(args: TestArgs) -> Result<()> {
    let mut state_elements = setup_private_intent_private_balance(&args).await?;

    // Build a proof bundle
    let bal = &mut state_elements.output_balance;
    let opening = state_elements.output_balance_opening;
    let proof_bundle = build_proof_bundle(bal, &opening, &args)?;

    // Send the txn and check the recipient balances before and after
    let recipient = bal.inner.relayer_fee_recipient;
    let token = bal.inner.mint;
    let recipient_bal_before = args.balance(recipient, token).await?;

    let tx = args.darkpool.payPrivateRelayerFee(proof_bundle);
    wait_for_tx_success(tx).await?;

    let recipient_bal_after = args.balance(recipient, token).await?;

    // Recipient balance should not change for private fee payment, only after note redemption will the recipient EOA balance change
    assert_eq_result!(recipient_bal_after, recipient_bal_before)
}
integration_test_async!(test_pay_private_relayer_fee);

// -----------
// | Helpers |
// -----------

/// Build a proof bundle for paying a private relayer fee
pub fn build_proof_bundle(
    bal: &mut DarkpoolStateBalance,
    opening: &MerkleAuthenticationPath,
    args: &TestArgs,
) -> Result<PrivateRelayerFeePaymentProofBundle> {
    // Prove the fee payment relation
    let (note, statement, proof) = generate_proof_bundle(bal, opening)?;

    // Create and sign the ciphertext
    let key = random_elgamal_encryption_key();
    let (ciphertext, _) = note.encrypt(&key);
    let relayer_sig = sign_ciphertext(&ciphertext, args)?;

    // Prove the fee payment relation
    Ok(PrivateRelayerFeePaymentProofBundle::new(
        ciphertext,
        relayer_sig,
        statement,
        proof,
    ))
}

/// Sign a ciphertext with the relayer's signer
fn sign_ciphertext(cipher: &NoteCiphertext, args: &TestArgs) -> Result<SignatureWithNonce> {
    let signer = &args.relayer_signer;
    let ciphertext = ElGamalCiphertext::from(cipher.clone());
    let sig = sign_with_nonce(&ciphertext.abi_encode(), signer)?;
    Ok(sig)
}

/// Generate a proof bundle for paying a private relayer fee
pub fn generate_proof_bundle(
    bal: &mut DarkpoolStateBalance,
    opening: &MerkleAuthenticationPath,
) -> Result<(Note, ValidPrivateRelayerFeePaymentStatement, PlonkProof)> {
    let old_balance = bal.clone();
    let old_balance_nullifier = old_balance.compute_nullifier();
    let note = bal.pay_relayer_fee();
    let new_relayer_fee_balance_share = bal.reencrypt_relayer_fee();
    let recovery_id = bal.compute_recovery_id();
    let new_balance_commitment = bal.compute_commitment();

    let witness = ValidPrivateRelayerFeePaymentWitness {
        old_balance,
        old_balance_opening: opening.clone().into(),
        blinder: note.blinder,
    };

    let statement = ValidPrivateRelayerFeePaymentStatement {
        merkle_root: opening.compute_root(),
        old_balance_nullifier,
        new_balance_commitment,
        recovery_id,
        new_relayer_fee_balance_share,
        relayer_fee_receiver: bal.inner.relayer_fee_recipient,
        note_commitment: note.commitment(),
    };

    let proof = singleprover_prove::<SizedValidPrivateRelayerFeePayment>(&witness, &statement)?;
    Ok((note, statement, proof))
}

//! A test for paying a private protocol fee

use alloy::primitives::Address;
use eyre::Result;
use renegade_abi::v2::IDarkpoolV2::PrivateProtocolFeePaymentProofBundle;
use renegade_circuit_types::{
    PlonkProof, balance::DarkpoolStateBalance, elgamal::EncryptionKey, note::Note,
};
use renegade_circuits::{
    singleprover_prove,
    zk_circuits::fees::valid_private_protocol_fee_payment::{
        SizedValidPrivateProtocolFeePayment, ValidPrivateProtocolFeePaymentStatement,
        ValidPrivateProtocolFeePaymentWitness,
    },
};
use renegade_common::types::merkle::MerkleAuthenticationPath;
use test_helpers::{assert_eq_result, integration_test_async};

use crate::{
    test_args::TestArgs, tests::state_updates::setup_private_intent_private_balance,
    util::transactions::wait_for_tx_success,
};

/// Test paying a private protocol fee
pub async fn test_pay_private_protocol_fee(args: TestArgs) -> Result<()> {
    let mut state_elements = setup_private_intent_private_balance(&args).await?;
    let recipient = args.protocol_fee_recipient().await?;

    // Build a proof bundle
    let bal = &mut state_elements.output_balance;
    let opening = state_elements.output_balance_opening;
    let proof_bundle = build_proof_bundle(bal, &opening, &args).await?;

    // Send the txn and check the recipient balances before and after
    let token = bal.inner.mint;
    let recipient_bal_before = args.balance(recipient, token).await?;

    let tx = args.darkpool.payPrivateProtocolFee(proof_bundle);
    wait_for_tx_success(tx).await?;

    let recipient_bal_after = args.balance(recipient, token).await?;

    // Verify the balance update
    // Balances should not change for private fee payments, only after note redemption will the recipient EOA balance change
    assert_eq_result!(recipient_bal_after, recipient_bal_before)
}
integration_test_async!(test_pay_private_protocol_fee);

// -----------
// | Helpers |
// -----------

/// Build a proof bundle for paying a private protocol fee
pub async fn build_proof_bundle(
    bal: &mut DarkpoolStateBalance,
    opening: &MerkleAuthenticationPath,
    args: &TestArgs,
) -> Result<PrivateProtocolFeePaymentProofBundle> {
    let (_, proof_bundle) = build_proof_bundle_with_note(bal, opening, args).await?;
    Ok(proof_bundle)
}

pub async fn build_proof_bundle_with_note(
    bal: &mut DarkpoolStateBalance,
    opening: &MerkleAuthenticationPath,
    args: &TestArgs,
) -> Result<(Note, PrivateProtocolFeePaymentProofBundle)> {
    let recipient = args.protocol_fee_recipient().await?;
    let protocol_fee_key = args.protocol_fee_encryption_key().await?;
    let (note, statement, proof) =
        prove_private_protocol_fee_payment_relation(recipient, protocol_fee_key, bal, opening)?;
    let proof_bundle = PrivateProtocolFeePaymentProofBundle::new(statement, proof);
    Ok((note, proof_bundle))
}

/// Prove the private protocol fee payment relation
pub fn prove_private_protocol_fee_payment_relation(
    recipient: Address,
    protocol_fee_key: EncryptionKey,
    bal: &mut DarkpoolStateBalance,
    opening: &MerkleAuthenticationPath,
) -> Result<(Note, ValidPrivateProtocolFeePaymentStatement, PlonkProof)> {
    // Rotate the balance
    let old_balance = bal.clone();
    let old_balance_nullifier = old_balance.compute_nullifier();
    let note = bal.pay_protocol_fee(recipient);
    let new_protocol_fee_balance_share = bal.reencrypt_protocol_fee();
    let recovery_id = bal.compute_recovery_id();
    let new_balance_commitment = bal.compute_commitment();

    // Encrypt the note
    let (ciphertext, randomness) = note.encrypt(&protocol_fee_key);

    let witness = ValidPrivateProtocolFeePaymentWitness {
        old_balance,
        old_balance_opening: opening.clone().into(),
        blinder: note.blinder,
        encryption_randomness: randomness,
    };

    let statement = ValidPrivateProtocolFeePaymentStatement {
        merkle_root: opening.compute_root(),
        old_balance_nullifier,
        new_balance_commitment,
        recovery_id,
        new_protocol_fee_balance_share,
        protocol_fee_receiver: recipient,
        note_commitment: note.commitment(),
        note_ciphertext: ciphertext,
        protocol_encryption_key: protocol_fee_key,
    };

    // Prove the relation
    let proof = singleprover_prove::<SizedValidPrivateProtocolFeePayment>(&witness, &statement)?;
    Ok((note, statement, proof))
}

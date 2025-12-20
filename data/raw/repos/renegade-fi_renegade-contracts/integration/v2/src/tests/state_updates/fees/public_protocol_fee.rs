//! A test for paying a public protocol fee

use alloy::primitives::{Address, U256};
use eyre::Result;
use renegade_abi::v2::IDarkpoolV2::PublicProtocolFeePaymentProofBundle;
use renegade_circuit_types::{PlonkProof, balance::DarkpoolStateBalance};
use renegade_circuits::{
    singleprover_prove,
    zk_circuits::fees::valid_public_protocol_fee_payment::{
        SizedValidPublicProtocolFeePayment, SizedValidPublicProtocolFeePaymentWitness,
        ValidPublicProtocolFeePaymentStatement,
    },
};
use renegade_common::types::merkle::MerkleAuthenticationPath;
use test_helpers::{assert_eq_result, integration_test_async};

use crate::{
    test_args::TestArgs, tests::state_updates::setup_private_intent_private_balance,
    util::transactions::wait_for_tx_success,
};

/// Test paying a public protocol fee
pub async fn test_pay_public_protocol_fee(args: TestArgs) -> Result<()> {
    let mut state_elements = setup_private_intent_private_balance(&args).await?;
    let bal = &mut state_elements.output_balance;
    let protocol_fee_balance = U256::from(bal.inner.protocol_fee_balance);

    // Build a proof bundle
    let recipient = args.protocol_fee_recipient().await?;
    let opening = state_elements.output_balance_opening;
    let proof_bundle = build_proof_bundle(recipient, bal, &opening)?;

    // Send the txn and check the recipient balances before and after
    let token = bal.inner.mint;
    let recipient_bal_before = args.balance(recipient, token).await?;

    let tx = args.darkpool.payPublicProtocolFee(proof_bundle);
    wait_for_tx_success(tx).await?;

    let recipient_bal_after = args.balance(recipient, token).await?;

    // Verify the balance update
    assert_eq_result!(
        recipient_bal_after,
        recipient_bal_before + protocol_fee_balance
    )
}
integration_test_async!(test_pay_public_protocol_fee);

// -----------
// | Helpers |
// -----------

/// Build a proof bundle for paying a public protocol fee
pub fn build_proof_bundle(
    recipient: Address,
    bal: &mut DarkpoolStateBalance,
    opening: &MerkleAuthenticationPath,
) -> Result<PublicProtocolFeePaymentProofBundle> {
    let (statement, proof) = generate_fee_payment_proof(recipient, bal, opening)?;
    Ok(PublicProtocolFeePaymentProofBundle::new(statement, proof))
}

/// Prove the public protocol fee payment relation
pub fn generate_fee_payment_proof(
    recipient: Address,
    bal: &mut DarkpoolStateBalance,
    opening: &MerkleAuthenticationPath,
) -> Result<(ValidPublicProtocolFeePaymentStatement, PlonkProof)> {
    let witness = SizedValidPublicProtocolFeePaymentWitness {
        old_balance: bal.clone(),
        old_balance_opening: opening.clone().into(),
    };

    let old_balance_nullifier = bal.compute_nullifier();
    let note = bal.pay_protocol_fee(recipient);
    let new_protocol_fee_balance_share = bal.reencrypt_protocol_fee();
    let recovery_id = bal.compute_recovery_id();
    let new_balance_commitment = bal.compute_commitment();
    let statement = ValidPublicProtocolFeePaymentStatement {
        merkle_root: opening.compute_root(),
        old_balance_nullifier,
        new_balance_commitment,
        recovery_id,
        new_protocol_fee_balance_share,
        note,
    };

    let proof = singleprover_prove::<SizedValidPublicProtocolFeePayment>(&witness, &statement)?;
    Ok((statement, proof))
}

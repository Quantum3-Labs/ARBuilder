//! A test for paying a public relayer fee

use alloy::primitives::U256;
use eyre::Result;
use renegade_abi::v2::IDarkpoolV2::PublicRelayerFeePaymentProofBundle;
use renegade_circuit_types::{PlonkProof, balance::DarkpoolStateBalance};
use renegade_circuits::{
    singleprover_prove,
    zk_circuits::fees::valid_public_relayer_fee_payment::{
        SizedValidPublicRelayerFeePayment, SizedValidPublicRelayerFeePaymentWitness,
        ValidPublicRelayerFeePaymentStatement,
    },
};
use renegade_common::types::merkle::MerkleAuthenticationPath;
use test_helpers::{assert_eq_result, integration_test_async};

use crate::{
    test_args::TestArgs, tests::state_updates::setup_private_intent_private_balance,
    util::transactions::wait_for_tx_success,
};

/// Test paying a public relayer fee
pub async fn test_pay_public_relayer_fee(args: TestArgs) -> Result<()> {
    let mut state_elements = setup_private_intent_private_balance(&args).await?;
    let bal = &mut state_elements.output_balance;
    let relayer_fee_balance = U256::from(bal.inner.relayer_fee_balance);

    // Build a proof bundle
    let opening = state_elements.output_balance_opening;
    let proof_bundle = build_proof_bundle(bal, &opening)?;

    // Send the txn and check the recipient balances before and after
    let recipient = bal.inner.relayer_fee_recipient;
    let token = bal.inner.mint;
    let recipient_bal_before = args.balance(recipient, token).await?;

    let tx = args.darkpool.payPublicRelayerFee(proof_bundle);
    wait_for_tx_success(tx).await?;

    let recipient_bal_after = args.balance(recipient, token).await?;

    // Verify the balance update
    assert_eq_result!(
        recipient_bal_after,
        recipient_bal_before + relayer_fee_balance
    )
}
integration_test_async!(test_pay_public_relayer_fee);

// -----------
// | Helpers |
// -----------

/// Build a proof bundle for paying a public relayer fee
pub fn build_proof_bundle(
    bal: &mut DarkpoolStateBalance,
    opening: &MerkleAuthenticationPath,
) -> Result<PublicRelayerFeePaymentProofBundle> {
    let (statement, proof) = generate_fee_payment_proof(bal, opening)?;
    Ok(PublicRelayerFeePaymentProofBundle::new(statement, proof))
}

/// Prove the public relayer fee payment relation
pub fn generate_fee_payment_proof(
    bal: &mut DarkpoolStateBalance,
    opening: &MerkleAuthenticationPath,
) -> Result<(ValidPublicRelayerFeePaymentStatement, PlonkProof)> {
    let witness = SizedValidPublicRelayerFeePaymentWitness {
        old_balance: bal.clone(),
        old_balance_opening: opening.clone().into(),
    };

    let old_balance_nullifier = bal.compute_nullifier();
    let note = bal.pay_relayer_fee();
    let new_relayer_fee_balance_share = bal.reencrypt_relayer_fee();
    let recovery_id = bal.compute_recovery_id();
    let new_balance_commitment = bal.compute_commitment();
    let statement = ValidPublicRelayerFeePaymentStatement {
        merkle_root: opening.compute_root(),
        old_balance_nullifier,
        new_balance_commitment,
        recovery_id,
        new_relayer_fee_balance_share,
        note,
    };

    let proof = singleprover_prove::<SizedValidPublicRelayerFeePayment>(&witness, &statement)?;
    Ok((statement, proof))
}

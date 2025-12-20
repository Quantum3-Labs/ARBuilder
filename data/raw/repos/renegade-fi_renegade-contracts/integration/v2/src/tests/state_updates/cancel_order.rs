//! Tests for canceling an order

use eyre::Result;
use renegade_abi::v2::{
    IDarkpoolV2::{OrderCancellationAuth, OrderCancellationProofBundle},
    auth_helpers::sign_with_nonce,
};
use renegade_circuit_types::{PlonkProof, intent::DarkpoolStateIntent};
use renegade_circuits::{
    singleprover_prove,
    zk_circuits::valid_order_cancellation::{
        SizedValidOrderCancellationCircuit, ValidOrderCancellationStatement,
        ValidOrderCancellationWitness,
    },
};
use renegade_common::types::merkle::MerkleAuthenticationPath;
use renegade_crypto::fields::scalar_to_u256;
use test_helpers::{assert_true_result, integration_test_async};

use crate::{
    test_args::TestArgs, tests::state_updates::setup_private_intent_private_balance,
    util::transactions::wait_for_tx_success,
};

/// Test canceling an order
async fn test_cancel_order(args: TestArgs) -> Result<()> {
    // Start by setting up an intent and balances
    let elements = setup_private_intent_private_balance(&args).await?;

    // Submit a cancellation transaction
    let (auth, bundle) =
        generate_cancellation_bundle(&elements.intent, &elements.intent_opening, &args)?;
    let tx = args.darkpool.cancelOrder(auth, bundle);
    wait_for_tx_success(tx).await?;

    // Check that the intent's nullifier is spent
    let nullifier = elements.intent.compute_nullifier();
    let nullifier_u256 = scalar_to_u256(&nullifier);
    let spent = args.darkpool.nullifierSpent(nullifier_u256).call().await?;
    assert_true_result!(spent)
}
integration_test_async!(test_cancel_order);

// -----------
// | Helpers |
// -----------

// --- Proof Bundles --- //

/// Generate a proof bundle for cancelling an order
pub fn generate_cancellation_bundle(
    intent: &DarkpoolStateIntent,
    intent_opening: &MerkleAuthenticationPath,
    args: &TestArgs,
) -> Result<(OrderCancellationAuth, OrderCancellationProofBundle)> {
    let auth = create_auth_bundle(intent, args)?;

    let (statement, proof) = generate_cancellation_proof(intent, intent_opening)?;
    let bundle = OrderCancellationProofBundle::new(statement, proof);

    Ok((auth, bundle))
}

/// Create an auth bundle for cancelling an order
fn create_auth_bundle(
    intent: &DarkpoolStateIntent,
    args: &TestArgs,
) -> Result<OrderCancellationAuth> {
    let nullifier = intent.compute_nullifier();
    let signature = sign_with_nonce(&nullifier.to_bytes_be(), &args.party0_signer())?;

    Ok(OrderCancellationAuth { signature })
}

// --- Proof Generation --- //

/// Generate a proof for cancelling an order
fn generate_cancellation_proof(
    intent: &DarkpoolStateIntent,
    intent_opening: &MerkleAuthenticationPath,
) -> Result<(ValidOrderCancellationStatement, PlonkProof)> {
    let witness = ValidOrderCancellationWitness {
        old_intent: intent.clone(),
        old_intent_opening: intent_opening.clone().into(),
    };

    let statement = ValidOrderCancellationStatement {
        owner: intent.inner.owner,
        merkle_root: intent_opening.compute_root(),
        old_intent_nullifier: intent.compute_nullifier(),
    };

    let proof = singleprover_prove::<SizedValidOrderCancellationCircuit>(&witness, &statement)?;
    Ok((statement, proof))
}

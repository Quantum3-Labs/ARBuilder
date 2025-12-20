//! Tests for settling a natively-settled private intent

use alloy::{
    primitives::{Address, U160, U256, aliases::U48, keccak256},
    signers::local::PrivateKeySigner,
};
use eyre::Result;
use rand::{Rng, thread_rng};
use renegade_abi::v2::{
    IDarkpoolV2::{
        ObligationBundle, PrivateIntentAuthBundle, PrivateIntentAuthBundleFirstFill,
        SettlementBundle,
    },
    auth_helpers::sign_with_nonce,
};
use renegade_circuit_types::{
    Commitment, PlonkLinkProof, PlonkProof, ProofLinkingHint,
    intent::{DarkpoolStateIntent, Intent},
    settlement_obligation::SettlementObligation,
    state_wrapper::StateWrapper,
};
use renegade_circuits::{
    singleprover_prove_with_hint,
    test_helpers::{BOUNDED_MAX_AMT, random_price},
    zk_circuits::{
        proof_linking::intent_only::link_sized_intent_only_settlement,
        settlement::intent_only_public_settlement::{
            self, IntentOnlyPublicSettlementCircuit, IntentOnlyPublicSettlementStatement,
        },
        validity_proofs::{
            intent_only::{self, IntentOnlyValidityStatement, SizedIntentOnlyValidityCircuit},
            intent_only_first_fill::{
                self, IntentOnlyFirstFillValidityCircuit, IntentOnlyFirstFillValidityStatement,
            },
        },
    },
};
use renegade_common::types::merkle::MerkleAuthenticationPath;
use renegade_constants::{MERKLE_HEIGHT, Scalar};
use renegade_crypto::fields::scalar_to_u256;
use test_helpers::{assert_eq_result, integration_test_async};

use crate::{
    test_args::TestArgs,
    tests::settlement::{compute_fee_take, settlement_relayer_fee, split_obligation},
    util::{
        fuzzing::create_matching_intents_and_obligations,
        merkle::find_state_element_opening,
        transactions::{send_tx, wait_for_tx_success},
    },
};

/// Tests settling a natively-settled private intent
///
/// This test will settle twice to test both the first and subsequent fill paths.
#[allow(non_snake_case)]
async fn test_settlement__native_settled_private_intent(args: TestArgs) -> Result<()> {
    // Fund the parties, party0 sells the base; party1 sells the quote
    fund_parties(&args).await?;

    // Build the obligations and split them in two for two fills
    let (intent0, intent1, obligation0, obligation1) =
        create_intents_and_obligations(&args).await?;
    let (first_obligation0, second_obligation0) = split_obligation(&obligation0);
    let (first_obligation1, second_obligation1) = split_obligation(&obligation1);

    // --- First Fill --- //

    // On the first fill, settle half of the obligations
    let (mut state_intent0, settlement_bundle0) =
        build_settlement_bundle_first_fill(&args.party0_signer(), &intent0, &first_obligation0)?;
    let (mut state_intent1, settlement_bundle1) =
        build_settlement_bundle_first_fill(&args.party1_signer(), &intent1, &first_obligation1)?;
    let obligation_bundle = build_obligation_bundle(&first_obligation0, &first_obligation1);

    let party0_base_before = args.base_balance(args.party0_addr()).await?;
    let party1_base_before = args.base_balance(args.party1_addr()).await?;
    let party0_quote_before = args.quote_balance(args.party0_addr()).await?;
    let party1_quote_before = args.quote_balance(args.party1_addr()).await?;
    let tx = args
        .darkpool
        .settleMatch(obligation_bundle, settlement_bundle0, settlement_bundle1);
    let tx_receipt = wait_for_tx_success(tx).await?;

    let party0_base_after = args.base_balance(args.party0_addr()).await?;
    let party1_base_after = args.base_balance(args.party1_addr()).await?;
    let party0_quote_after = args.quote_balance(args.party0_addr()).await?;
    let party1_quote_after = args.quote_balance(args.party1_addr()).await?;

    // Verify balance updates
    let fee_take0 = compute_fee_take(&first_obligation0, &args).await?;
    let fee_take1 = compute_fee_take(&first_obligation1, &args).await?;
    let total_fee0 = U256::from(fee_take0.total());
    let total_fee1 = U256::from(fee_take1.total());
    assert_eq_result!(
        party0_base_after,
        party0_base_before - U256::from(first_obligation0.amount_in)
    )?;
    assert_eq_result!(
        party0_quote_after,
        party0_quote_before + U256::from(first_obligation0.amount_out) - total_fee0
    )?;
    assert_eq_result!(
        party1_base_after,
        party1_base_before + U256::from(first_obligation1.amount_out) - total_fee1
    )?;
    assert_eq_result!(
        party1_quote_after,
        party1_quote_before - U256::from(first_obligation1.amount_in)
    )?;

    // --- Subsequent Fill --- //

    // Update the state intents and search for their commitments
    state_intent0.apply_settlement_obligation(&first_obligation0);
    state_intent1.apply_settlement_obligation(&first_obligation1);
    let opening0 = find_state_element_opening(&state_intent0, &tx_receipt).await?;
    let opening1 = find_state_element_opening(&state_intent1, &tx_receipt).await?;
    let settlement_bundle0 =
        build_settlement_bundle_subsequent_fill(&state_intent0, &opening0, &second_obligation0)?;
    let settlement_bundle1 =
        build_settlement_bundle_subsequent_fill(&state_intent1, &opening1, &second_obligation1)?;
    let obligation_bundle = build_obligation_bundle(&second_obligation0, &second_obligation1);

    // Settle the match
    let party0_base_before = args.base_balance(args.party0_addr()).await?;
    let party1_base_before = args.base_balance(args.party1_addr()).await?;
    let party0_quote_before = args.quote_balance(args.party0_addr()).await?;
    let party1_quote_before = args.quote_balance(args.party1_addr()).await?;
    let tx = args
        .darkpool
        .settleMatch(obligation_bundle, settlement_bundle0, settlement_bundle1);
    wait_for_tx_success(tx).await?;

    let party0_base_after = args.base_balance(args.party0_addr()).await?;
    let party1_base_after = args.base_balance(args.party1_addr()).await?;
    let party0_quote_after = args.quote_balance(args.party0_addr()).await?;
    let party1_quote_after = args.quote_balance(args.party1_addr()).await?;

    // Verify balance updates
    let fee_take0 = compute_fee_take(&second_obligation0, &args).await?;
    let fee_take1 = compute_fee_take(&second_obligation1, &args).await?;
    let total_fee0 = U256::from(fee_take0.total());
    let total_fee1 = U256::from(fee_take1.total());
    assert_eq_result!(
        party0_base_after,
        party0_base_before - U256::from(second_obligation0.amount_in)
    )?;
    assert_eq_result!(
        party0_quote_after,
        party0_quote_before + U256::from(second_obligation0.amount_out) - total_fee0
    )?;
    assert_eq_result!(
        party1_base_after,
        party1_base_before + U256::from(second_obligation1.amount_out) - total_fee1
    )?;
    assert_eq_result!(
        party1_quote_after,
        party1_quote_before - U256::from(second_obligation1.amount_in)
    )?;

    Ok(())
}
integration_test_async!(test_settlement__native_settled_private_intent);

// -----------
// | Helpers |
// -----------

// --- Funding --- //

/// Fund the two parties with the base and quote tokens
///
/// Test setup will fund the parties with the tokens and approve the permit2 contract to spend the tokens.
async fn fund_parties(args: &TestArgs) -> Result<()> {
    let base = args.base_addr()?;
    let quote = args.quote_addr()?;
    approve_balance(base, &args.party0_signer(), args).await?;
    approve_balance(quote, &args.party1_signer(), args).await?;
    Ok(())
}

/// Approve a balance to be spent by the darkpool via the permit2 contract
async fn approve_balance(token: Address, signer: &PrivateKeySigner, args: &TestArgs) -> Result<()> {
    let amt = U160::MAX;
    let permit2 = args.permit2_with_signer(signer)?;
    let darkpool = args.darkpool_addr();
    let expiration = U48::MAX;
    send_tx(permit2.approve(token, darkpool, amt, expiration)).await?;

    Ok(())
}

// --- Intents --- //

/// Create two matching intents and obligations
///
/// Party 0 sells the base; party1 sells the quote
async fn create_intents_and_obligations(
    args: &TestArgs,
) -> Result<(Intent, Intent, SettlementObligation, SettlementObligation)> {
    let mut rng = thread_rng();
    let amount_in = rng.gen_range(0..=BOUNDED_MAX_AMT);
    let min_price = random_price();
    let intent0 = Intent {
        in_token: args.base_addr()?,
        out_token: args.quote_addr()?,
        owner: args.party0_addr(),
        min_price,
        amount_in,
    };

    let counterparty = args.party1_addr();
    let (intent1, obligation0, obligation1) =
        create_matching_intents_and_obligations(&intent0, counterparty)?;
    Ok((intent0, intent1, obligation0, obligation1))
}

// --- Prover --- //

/// Generate first fill validity proofs for an intent
///
/// Also return a commitment to the intent
fn generate_first_fill_validity_proof(
    intent: &Intent,
) -> Result<(
    Commitment,
    DarkpoolStateIntent,
    IntentOnlyFirstFillValidityStatement,
    PlonkProof,
    ProofLinkingHint,
)> {
    // Build the witness and statement
    let (witness, statement) =
        intent_only_first_fill::test_helpers::create_witness_statement_with_intent(intent);

    // Compute a commitment to the initial intent
    let intent = witness.intent.clone();
    let share_stream_seed = witness.initial_intent_share_stream.seed;
    let recovery_stream_seed = witness.initial_intent_recovery_stream.seed;
    let mut state_intent =
        DarkpoolStateIntent::new(intent, share_stream_seed, recovery_stream_seed);
    state_intent.compute_recovery_id();
    let comm = state_intent.compute_commitment();

    // Generate the validity proof
    let (proof, link_hint) =
        singleprover_prove_with_hint::<IntentOnlyFirstFillValidityCircuit>(&witness, &statement)?;
    Ok((comm, state_intent, statement, proof, link_hint))
}

/// Generate a subsequent fill validity proof for an intent
fn generate_subsequent_fill_validity_proof(
    intent: &StateWrapper<Intent>,
    merkle_opening: &MerkleAuthenticationPath,
) -> Result<(IntentOnlyValidityStatement, PlonkProof, ProofLinkingHint)> {
    // Generate the witness and statement
    let (mut witness, mut statement) =
        intent_only::test_helpers::create_witness_statement_with_state_intent(intent.clone());

    // Replace the dummy Merkle opening with the real one
    statement.merkle_root = merkle_opening.compute_root();
    witness.old_intent_opening = merkle_opening.clone().into();

    // Prove the circuit
    let (proof, link_hint) =
        singleprover_prove_with_hint::<SizedIntentOnlyValidityCircuit>(&witness, &statement)?;
    Ok((statement, proof, link_hint))
}

/// Generate a settlement proof for a private intent
fn generate_settlement_proof(
    intent: &Intent,
    obligation: &SettlementObligation,
) -> Result<(
    IntentOnlyPublicSettlementStatement,
    PlonkProof,
    ProofLinkingHint,
)> {
    let (witness, mut statement) = intent_only_public_settlement::test_helpers::create_witness_statement_with_intent_and_obligation(intent, obligation);
    statement.relayer_fee = settlement_relayer_fee();
    let (proof, link_hint) =
        singleprover_prove_with_hint::<IntentOnlyPublicSettlementCircuit>(&witness, &statement)?;

    Ok((statement, proof, link_hint))
}

// --- Calldata Bundles --- //

/// Build an obligation bundle for two public obligations
pub fn build_obligation_bundle(
    obligation0: &SettlementObligation,
    obligation1: &SettlementObligation,
) -> ObligationBundle {
    ObligationBundle::new_public(obligation0.clone().into(), obligation1.clone().into())
}

/// Build a settlement bundle for the first fill
pub fn build_settlement_bundle_first_fill(
    owner: &PrivateKeySigner,
    intent: &Intent,
    obligation: &SettlementObligation,
) -> Result<(DarkpoolStateIntent, SettlementBundle)> {
    // Generate proofs
    let (commitment, state_intent, validity_statement, validity_proof, validity_link_hint) =
        generate_first_fill_validity_proof(intent)?;
    let (settlement_statement, settlement_proof, settlement_link_hint) =
        generate_settlement_proof(intent, obligation)?;
    let linking_proof = generate_linking_proof(&validity_link_hint, &settlement_link_hint)?;

    // Build bundles
    let auth_bundle =
        build_auth_bundle_first_fill(owner, commitment, &validity_statement, &validity_proof)?;
    let settlement_bundle = SettlementBundle::private_intent_public_balance_first_fill(
        auth_bundle.clone(),
        settlement_statement.clone().into(),
        settlement_proof.clone().into(),
        linking_proof.into(),
    );

    Ok((state_intent, settlement_bundle))
}

/// Build a settlement bundle for a subsequent fill
pub fn build_settlement_bundle_subsequent_fill(
    intent: &StateWrapper<Intent>,
    merkle_opening: &MerkleAuthenticationPath,
    obligation: &SettlementObligation,
) -> Result<SettlementBundle> {
    // Generate proofs
    let (validity_statement, validity_proof, validity_link_hint) =
        generate_subsequent_fill_validity_proof(intent, merkle_opening)?;
    let (settlement_statement, settlement_proof, settlement_link_hint) =
        generate_settlement_proof(&intent.inner, obligation)?;
    let linking_proof = generate_linking_proof(&validity_link_hint, &settlement_link_hint)?;

    // Build bundles
    let auth_bundle = build_auth_bundle_subsequent_fill(&validity_statement, &validity_proof)?;
    Ok(SettlementBundle::private_intent_public_balance(
        auth_bundle.clone(),
        settlement_statement.clone().into(),
        settlement_proof.clone().into(),
        linking_proof.into(),
    ))
}

/// Build an auth bundle for an intent
fn build_auth_bundle_first_fill(
    owner: &PrivateKeySigner,
    commitment: Scalar,
    validity_statement: &IntentOnlyFirstFillValidityStatement,
    validity_proof: &PlonkProof,
) -> Result<PrivateIntentAuthBundleFirstFill> {
    let comm_u256 = scalar_to_u256(&commitment);
    let comm_hash = keccak256(comm_u256.to_be_bytes_vec());
    let signature = sign_with_nonce(comm_hash.as_slice(), owner)?;

    Ok(PrivateIntentAuthBundleFirstFill {
        intentSignature: signature,
        merkleDepth: U256::from(MERKLE_HEIGHT),
        statement: validity_statement.clone().into(),
        validityProof: validity_proof.clone().into(),
    })
}

/// Build an auth bundle for a subsequent fill
fn build_auth_bundle_subsequent_fill(
    validity_statement: &IntentOnlyValidityStatement,
    validity_proof: &PlonkProof,
) -> Result<PrivateIntentAuthBundle> {
    Ok(PrivateIntentAuthBundle {
        merkleDepth: U256::from(MERKLE_HEIGHT),
        statement: validity_statement.clone().into(),
        validityProof: validity_proof.clone().into(),
    })
}

/// Generate a linking proof between a validity proof and a settlement proof
fn generate_linking_proof(
    validity_link_hint: &ProofLinkingHint,
    settlement_link_hint: &ProofLinkingHint,
) -> Result<PlonkLinkProof> {
    let proof = link_sized_intent_only_settlement(validity_link_hint, settlement_link_hint)?;
    Ok(proof)
}

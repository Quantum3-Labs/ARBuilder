//! Settle a ring 2 (private intent, private balance) user's match against another use
//!
//! For simplicity, we use a ring-0 order for the counterparty.

use alloy::{
    primitives::{Address, U256},
    rpc::types::TransactionReceipt,
    signers::local::PrivateKeySigner,
};
use eyre::Result;
use rand::{Rng, thread_rng};
use renegade_abi::v2::{
    IDarkpoolV2::{
        self, Deposit, ObligationBundle, OutputBalanceBundle, PublicIntentAuthBundle,
        PublicIntentPermit, RenegadeSettledIntentAuthBundle,
        RenegadeSettledIntentAuthBundleFirstFill, SettlementBundle,
    },
    auth_helpers::sign_with_nonce,
};
use renegade_circuit_types::{
    PlonkLinkProof, PlonkProof, ProofLinkingHint,
    balance::{Balance, DarkpoolStateBalance, PostMatchBalanceShare},
    intent::{DarkpoolStateIntent, Intent, PreMatchIntentShare},
    settlement_obligation::SettlementObligation,
    state_wrapper::StateWrapper,
};
use renegade_circuits::{
    singleprover_prove_with_hint,
    test_helpers::{BOUNDED_MAX_AMT, random_price},
    zk_circuits::{
        proof_linking::{
            intent_and_balance::link_sized_intent_and_balance_settlement,
            output_balance::link_sized_output_balance_settlement,
        },
        settlement::intent_and_balance_public_settlement::{
            IntentAndBalancePublicSettlementCircuit, IntentAndBalancePublicSettlementStatement,
            IntentAndBalancePublicSettlementWitness,
        },
        validity_proofs::{
            intent_and_balance::{
                INTENT_PARTIAL_COMMITMENT_SIZE, IntentAndBalanceValidityStatement,
                IntentAndBalanceValidityWitness, SizedIntentAndBalanceValidityCircuit,
            },
            intent_and_balance_first_fill::{
                BALANCE_PARTIAL_COMMITMENT_SIZE, IntentAndBalanceFirstFillValidityStatement,
                IntentAndBalanceFirstFillValidityWitness,
                SizedIntentAndBalanceFirstFillValidityCircuit,
            },
            new_output_balance::{
                NewOutputBalanceValidityCircuit, NewOutputBalanceValidityStatement,
                test_helpers::create_witness_statement_with_balance as create_new_output_balance_witness_statement,
            },
            output_balance::{
                OutputBalanceValidityStatement, OutputBalanceValidityWitness,
                SizedOutputBalanceValidityCircuit,
            },
        },
    },
};
use renegade_common::types::merkle::MerkleAuthenticationPath;
use renegade_constants::{MERKLE_HEIGHT, Scalar};
use renegade_crypto::{
    fields::{address_to_scalar, scalar_to_u256},
    hash::compute_poseidon_hash,
};
use test_helpers::{assert_eq_result, integration_test_async};

use crate::{
    test_args::TestArgs,
    tests::{
        settlement::{
            compute_fee_take, settlement_relayer_fee, settlement_relayer_fee_rate, split_obligation,
        },
        state_updates::create_balance::create_balance,
    },
    util::{
        deposit::fund_for_deposit, fuzzing::create_matching_intents_and_obligations,
        merkle::find_state_element_opening, transactions::wait_for_tx_success,
    },
};

/// Test settling a Ring 2 match
///
/// Party0 owns the ring-2 order and sells the base token
#[allow(non_snake_case)]
async fn test_settlement__private_intent_private_balance(args: TestArgs) -> Result<()> {
    // Build the intents and obligations
    let (intent0, intent1, obligation0, obligation1) = create_intents_and_obligations(&args)?;

    // Fund both parties
    let (mut party0_bal, party0_bal_opening) =
        fund_ring2_party(&args.party0_signer(), &obligation0, &args).await?;
    fund_ring0_party(&args.party1_signer(), &obligation1, &args).await?;

    // Split the obligations in two for two fills
    let (first_obligation0, second_obligation0) = split_obligation(&obligation0);
    let (first_obligation1, second_obligation1) = split_obligation(&obligation1);

    // --- First Fill --- //

    // On the first fill, settle half of the obligations
    let obligation_bundle = ObligationBundle::new_public(
        first_obligation0.clone().into(),
        first_obligation1.clone().into(),
    );
    let (mut state_intent0, mut out_balance0, settlement_bundle0) =
        build_settlement_bundle_first_fill(
            &args.party0_signer(),
            &intent0,
            &first_obligation0,
            &mut party0_bal,
            &party0_bal_opening,
            &args,
        )?;
    let settlement_bundle1 =
        build_settlement_bundle_ring0(&args.party1_signer(), &intent1, &first_obligation1, &args)?;

    let (party0_base_before, party0_quote_before) =
        args.base_and_quote_balances(args.party0_addr()).await?;
    let (party1_base_before, party1_quote_before) =
        args.base_and_quote_balances(args.party1_addr()).await?;

    let tx = args
        .darkpool
        .settleMatch(obligation_bundle, settlement_bundle0, settlement_bundle1);
    let tx_receipt = wait_for_tx_success(tx).await?;

    let (party0_base_after, party0_quote_after) =
        args.base_and_quote_balances(args.party0_addr()).await?;
    let (party1_base_after, party1_quote_after) =
        args.base_and_quote_balances(args.party1_addr()).await?;

    // Party 0 balances should not change; they're settled into the darkpool state
    assert_eq_result!(party0_base_after, party0_base_before)?;
    assert_eq_result!(party0_quote_after, party0_quote_before)?;
    // Party 1 balances should increase by the amount of the obligation
    let fee_take1 = compute_fee_take(&first_obligation1, &args).await?;
    let net_receive = first_obligation1.amount_out - fee_take1.total();
    assert_eq_result!(
        party1_base_after,
        party1_base_before + U256::from(net_receive)
    )?;
    assert_eq_result!(
        party1_quote_after,
        party1_quote_before - U256::from(first_obligation1.amount_in)
    )?;

    // --- Subsequent Fill --- //

    // Update the state values to match their post-settlement state committed on-chain
    let fee_take = compute_fee_take(&first_obligation0, &args).await?;
    state_intent0.apply_settlement_obligation(&first_obligation0);
    party0_bal.apply_obligation_in_balance(&first_obligation0);
    out_balance0.apply_obligation_out_balance_no_fees(&first_obligation0, &fee_take);

    // Build a settlement bundle for the next fill
    let obligation_bundle = ObligationBundle::new_public(
        second_obligation0.clone().into(),
        second_obligation1.clone().into(),
    );
    let settlement_bundle0 = build_settlement_bundle_subsequent_fill(
        &mut state_intent0,
        &mut party0_bal,
        &mut out_balance0,
        &second_obligation0,
        &tx_receipt,
    )
    .await?;
    let settlement_bundle1 =
        build_settlement_bundle_ring0(&args.party1_signer(), &intent1, &second_obligation1, &args)?;

    let (party0_base_before, party0_quote_before) =
        args.base_and_quote_balances(args.party0_addr()).await?;
    let (party1_base_before, party1_quote_before) =
        args.base_and_quote_balances(args.party1_addr()).await?;

    let tx = args
        .darkpool
        .settleMatch(obligation_bundle, settlement_bundle0, settlement_bundle1);
    wait_for_tx_success(tx).await?;

    let (party0_base_after, party0_quote_after) =
        args.base_and_quote_balances(args.party0_addr()).await?;
    let (party1_base_after, party1_quote_after) =
        args.base_and_quote_balances(args.party1_addr()).await?;

    // Party 0 balances should not change; they're settled into the darkpool state
    assert_eq_result!(party0_base_after, party0_base_before)?;
    assert_eq_result!(party0_quote_after, party0_quote_before)?;
    // Party 1 balances should increase by the amount of the obligation
    let fee_take1 = compute_fee_take(&second_obligation1, &args).await?;
    let net_receive = second_obligation1.amount_out - fee_take1.total();
    assert_eq_result!(
        party1_base_after,
        party1_base_before + U256::from(net_receive)
    )?;
    assert_eq_result!(
        party1_quote_after,
        party1_quote_before - U256::from(second_obligation1.amount_in)
    )?;

    Ok(())
}
integration_test_async!(test_settlement__private_intent_private_balance);

// -----------
// | Helpers |
// -----------

// --- Match Setup --- //

/// Create intents and obligations for the match
pub fn create_intents_and_obligations(
    args: &TestArgs,
) -> Result<(Intent, Intent, SettlementObligation, SettlementObligation)> {
    let mut rng = thread_rng();
    let amount_in = rng.gen_range(0..=BOUNDED_MAX_AMT);
    let party0_intent = Intent {
        in_token: args.base_addr()?,
        out_token: args.quote_addr()?,
        owner: args.party0_addr(),
        min_price: random_price(),
        amount_in,
    };

    let (counterparty_intent, obligation0, obligation1) =
        create_matching_intents_and_obligations(&party0_intent, args.party1_addr())?;
    Ok((party0_intent, counterparty_intent, obligation0, obligation1))
}

// --- Funding --- //

/// Fund the ring-2 party with a deposit
pub async fn fund_ring2_party(
    signer: &PrivateKeySigner,
    obligation: &SettlementObligation,
    args: &TestArgs,
) -> Result<(DarkpoolStateBalance, MerkleAuthenticationPath)> {
    let deposit = Deposit {
        from: signer.address(),
        token: obligation.input_token,
        amount: U256::from(obligation.amount_in),
    };

    fund_for_deposit(obligation.input_token, signer, &deposit, args).await?;
    let (receipt, bal) = create_balance(signer, &deposit, args).await?;
    let opening = find_state_element_opening(&bal, &receipt).await?;
    Ok((bal, opening))
}

/// Fund the ring-0 party
pub async fn fund_ring0_party(
    signer: &PrivateKeySigner,
    obligation: &SettlementObligation,
    args: &TestArgs,
) -> Result<()> {
    // Mint the obligation amount to the given party
    let token = obligation.input_token;
    let amount = U256::from(obligation.amount_in);
    let erc20 = args.erc20_from_addr_with_signer(token, signer.clone())?;
    let mint_tx = erc20.mint(signer.address(), amount);
    wait_for_tx_success(mint_tx).await?;

    // Approve the darkpool to spend the tokens
    args.permit2_approve_darkpool(token, signer).await
}

// --- First Fill Bundle --- //

/// Build a ring 0 settlement bundle
pub fn build_settlement_bundle_ring0(
    signer: &PrivateKeySigner,
    intent: &Intent,
    obligation: &SettlementObligation,
    args: &TestArgs,
) -> Result<SettlementBundle> {
    let permit = PublicIntentPermit {
        intent: intent.clone().into(),
        executor: args.relayer_signer_addr(),
    };

    // Sign the intent with the owner's key
    let intent_signature = permit.sign(signer)?;
    let contracts_obligation = IDarkpoolV2::SettlementObligation::from(obligation.clone());
    let relayer_fee = settlement_relayer_fee_rate(args);
    let executor_signer = &args.relayer_signer;
    let executor_signature =
        contracts_obligation.create_executor_signature(&relayer_fee, executor_signer)?;
    let auth_bundle = PublicIntentAuthBundle {
        permit,
        intentSignature: intent_signature,
        executorSignature: executor_signature,
    };

    Ok(SettlementBundle::public_intent_settlement(
        auth_bundle,
        relayer_fee,
    ))
}

/// Build a settlement bundle for the first fill
///
/// Updates the state intent's public shares to match the validity statement's values.
/// This ensures that after settlement, we can correctly compute the commitment using
/// the same values that Solidity uses from the validity proof.
pub fn build_settlement_bundle_first_fill(
    signer: &PrivateKeySigner,
    intent: &Intent,
    obligation: &SettlementObligation,
    in_balance: &mut DarkpoolStateBalance,
    balance_opening: &MerkleAuthenticationPath,
    args: &TestArgs,
) -> Result<(DarkpoolStateIntent, DarkpoolStateBalance, SettlementBundle)> {
    // Generate the validity proofs
    let (state_intent, validity_statement, validity_proof, validity_hint) =
        generate_validity_proof_first_fill(intent, in_balance, balance_opening)?;
    let (out_balance, new_output_statement, new_output_proof, new_output_hint) =
        generate_new_output_balance_validity_proof(signer.address(), obligation, args)?;

    // Generate the settlement proof
    let (settlement_statement, settlement_proof, settlement_hint) =
        generate_settlement_proof(&state_intent, in_balance, &out_balance, obligation)?;

    // Build the auth bundles
    let commitment = validity_statement.intent_and_authorizing_address_commitment;
    let auth_bundle =
        build_auth_bundle_first_fill(signer, commitment, &validity_statement, &validity_proof)?;
    let validity_link_proof =
        generate_validity_settlement_linking_proof(&validity_hint, &settlement_hint)?;

    let output_balance_link_proof =
        generate_output_balance_settlement_linking_proof(&new_output_hint, &settlement_hint)?;
    let new_output_auth_bundle = OutputBalanceBundle::new_output_balance(
        U256::from(MERKLE_HEIGHT),
        new_output_statement.into(),
        new_output_proof.into(),
        output_balance_link_proof.into(),
    );

    let bundle = SettlementBundle::renegade_settled_private_intent_first_fill(
        auth_bundle,
        new_output_auth_bundle,
        settlement_statement.into(),
        settlement_proof.into(),
        validity_link_proof.into(),
    );

    Ok((state_intent, out_balance, bundle))
}

/// Build an auth bundle for the first fill
pub(crate) fn build_auth_bundle_first_fill(
    owner: &PrivateKeySigner,
    commitment: Scalar,
    validity_statement: &IntentAndBalanceFirstFillValidityStatement,
    validity_proof: &PlonkProof,
) -> Result<RenegadeSettledIntentAuthBundleFirstFill> {
    let comm_bytes = scalar_to_u256(&commitment).to_be_bytes_vec();
    let signature = sign_with_nonce(comm_bytes.as_slice(), owner)?;

    Ok(RenegadeSettledIntentAuthBundleFirstFill {
        merkleDepth: U256::from(MERKLE_HEIGHT),
        ownerSignature: signature,
        statement: validity_statement.clone().into(),
        validityProof: validity_proof.clone().into(),
    })
}

// --- Subsequent Fill Bundle --- //

/// Build a settlement bundle for the subsequent fill
pub async fn build_settlement_bundle_subsequent_fill(
    intent: &mut DarkpoolStateIntent,
    in_balance: &mut DarkpoolStateBalance,
    out_balance: &mut DarkpoolStateBalance,
    obligation: &SettlementObligation,
    first_fill_receipt: &TransactionReceipt,
) -> Result<SettlementBundle> {
    // Find the Merkle openings for all state elements
    let intent_opening = find_state_element_opening(intent, first_fill_receipt).await?;
    let in_balance_opening = find_state_element_opening(in_balance, first_fill_receipt)
        .await
        .map_err(|e| eyre::eyre!("Failed to find in balance opening: {e}"))?;
    let out_balance_opening = find_state_element_opening(out_balance, first_fill_receipt)
        .await
        .map_err(|e| eyre::eyre!("Failed to find out balance opening: {e}"))?;

    // Generate validity proofs
    let (validity_statement, validity_proof, validity_hint) =
        generate_validity_proof_subsequent_fill(
            intent,
            in_balance,
            &intent_opening,
            &in_balance_opening,
        )?;
    let (output_balance_statement, output_balance_proof, output_balance_hint) =
        generate_existing_output_balance_validity_proof(out_balance, &out_balance_opening)?;

    // Generate a settlement proof
    let (settlement_statement, settlement_proof, settlement_hint) =
        generate_settlement_proof(intent, in_balance, out_balance, obligation)?;

    // Build the auth bundles
    let validity_link_proof =
        generate_validity_settlement_linking_proof(&validity_hint, &settlement_hint)?;
    let auth_bundle = RenegadeSettledIntentAuthBundle {
        merkleDepth: U256::from(MERKLE_HEIGHT),
        statement: validity_statement.clone().into(),
        validityProof: validity_proof.into(),
    };

    let output_balance_link_proof =
        generate_output_balance_settlement_linking_proof(&output_balance_hint, &settlement_hint)?;
    let existing_output_auth_bundle = OutputBalanceBundle::existing_output_balance(
        U256::from(MERKLE_HEIGHT),
        output_balance_statement.clone().into(),
        output_balance_proof.into(),
        output_balance_link_proof.into(),
    );

    Ok(SettlementBundle::renegade_settled_private_intent(
        auth_bundle,
        existing_output_auth_bundle,
        settlement_statement.clone().into(),
        settlement_proof.into(),
        validity_link_proof.into(),
    ))
}

// --- Proofs --- //

/// Generate a validity proof for the ring 2 party on the first fill
pub(crate) fn generate_validity_proof_first_fill(
    intent: &Intent,
    bal: &mut DarkpoolStateBalance,
    balance_opening: &MerkleAuthenticationPath,
) -> Result<(
    DarkpoolStateIntent,
    IntentAndBalanceFirstFillValidityStatement,
    PlonkProof,
    ProofLinkingHint,
)> {
    let mut rng = thread_rng();

    // Generate the witness and statement
    let old_balance = bal.clone();
    let share_stream_seed = Scalar::random(&mut rng);
    let recovery_stream_seed = Scalar::random(&mut rng);
    let initial_intent = StateWrapper::new(intent.clone(), share_stream_seed, recovery_stream_seed);
    let mut state_intent = initial_intent.clone();

    let initial_intent_commitment = state_intent.compute_commitment();
    let old_balance_nullifier = bal.compute_nullifier();

    // Re-encrypt the new amount public share
    let new_amount_public_share = state_intent.public_share.amount_in;

    // Re-encrypt the post-match balance shares
    let new_one_time_address = bal.inner.one_time_authority;
    let new_one_time_share = bal.stream_cipher_encrypt(&new_one_time_address);
    let post_match_balance_shares = bal.reencrypt_post_match_share();
    bal.public_share.one_time_authority = new_one_time_share;

    let witness = IntentAndBalanceFirstFillValidityWitness {
        intent: intent.clone(),
        initial_intent_share_stream: initial_intent.share_stream.clone(),
        initial_intent_recovery_stream: initial_intent.recovery_stream.clone(),
        private_intent_shares: state_intent.private_shares(),
        new_amount_public_share,
        balance: old_balance.inner.clone(),
        old_balance,
        post_match_balance_shares,
        // TODO: Remove this when we remove one time addresses
        new_one_time_address,
        balance_opening: balance_opening.clone().into(),
    };

    // TODO: Remove this value
    let intent_and_authorizing_address_commitment = compute_poseidon_hash(&[
        initial_intent_commitment,
        address_to_scalar(&new_one_time_address),
    ]);

    let intent_public_share = PreMatchIntentShare::from(state_intent.public_share());
    let intent_recovery_id = state_intent.compute_recovery_id();
    let intent_private_share_commitment = state_intent.compute_private_commitment();
    let balance_recovery_id = bal.compute_recovery_id();
    let balance_partial_commitment =
        bal.compute_partial_commitment(BALANCE_PARTIAL_COMMITMENT_SIZE);

    let statement = IntentAndBalanceFirstFillValidityStatement {
        merkle_root: balance_opening.compute_root(),
        // TODO: Remove this when we implement in-circuit verification
        intent_and_authorizing_address_commitment,
        intent_public_share,
        intent_private_share_commitment,
        intent_recovery_id,
        balance_partial_commitment,
        new_one_time_address_public_share: new_one_time_share,
        old_balance_nullifier,
        balance_recovery_id,
        one_time_authorizing_address: bal.inner.one_time_authority,
    };

    // Prove the relation
    let (proof, hint) = singleprover_prove_with_hint::<
        SizedIntentAndBalanceFirstFillValidityCircuit,
    >(&witness, &statement)?;

    Ok((state_intent, statement, proof, hint))
}

/// Generate a validity proof for a subsequent fill
pub(crate) fn generate_validity_proof_subsequent_fill(
    intent: &mut DarkpoolStateIntent,
    in_balance: &mut DarkpoolStateBalance,
    intent_opening: &MerkleAuthenticationPath,
    in_balance_opening: &MerkleAuthenticationPath,
) -> Result<(
    IntentAndBalanceValidityStatement,
    PlonkProof,
    ProofLinkingHint,
)> {
    // Update the intent
    let old_intent = intent.clone();
    let old_intent_nullifier = old_intent.compute_nullifier();
    let new_amount_public_share = intent.reencrypt_amount_in();

    let intent_recovery_id = intent.compute_recovery_id();
    let intent_partial_commitment =
        intent.compute_partial_commitment(INTENT_PARTIAL_COMMITMENT_SIZE);

    // Update the balance
    let old_balance = in_balance.clone();
    let old_balance_nullifier = old_balance.compute_nullifier();
    let post_match_balance_shares = in_balance.reencrypt_post_match_share();

    let balance_recovery_id = in_balance.compute_recovery_id();
    let balance_partial_commitment =
        in_balance.compute_partial_commitment(BALANCE_PARTIAL_COMMITMENT_SIZE);

    // Build the witness and statement
    let witness = IntentAndBalanceValidityWitness {
        intent: old_intent.inner.clone(),
        old_intent,
        old_intent_opening: intent_opening.clone().into(),
        new_amount_public_share,
        balance: old_balance.inner.clone(),
        old_balance,
        old_balance_opening: in_balance_opening.clone().into(),
        post_match_balance_shares,
    };

    let statement = IntentAndBalanceValidityStatement {
        intent_merkle_root: intent_opening.compute_root(),
        old_intent_nullifier,
        new_intent_partial_commitment: intent_partial_commitment,
        intent_recovery_id,
        balance_merkle_root: in_balance_opening.compute_root(),
        old_balance_nullifier,
        balance_partial_commitment,
        balance_recovery_id,
    };

    // Prove the validity relation
    let (proof, hint) =
        singleprover_prove_with_hint::<SizedIntentAndBalanceValidityCircuit>(&witness, &statement)?;
    Ok((statement, proof, hint))
}

/// Generate a new output balance validity proof
pub(crate) fn generate_new_output_balance_validity_proof(
    owner: Address,
    obligation: &SettlementObligation,
    test_args: &TestArgs,
) -> Result<(
    DarkpoolStateBalance,
    NewOutputBalanceValidityStatement,
    PlonkProof,
    ProofLinkingHint,
)> {
    let relayer_fee_recipient = test_args.relayer_signer_addr();
    let one_time_authority = owner;
    let bal = Balance::new(
        obligation.output_token,
        owner,
        relayer_fee_recipient,
        one_time_authority,
    );

    // Build the witness and statement
    let (witness, statement) = create_new_output_balance_witness_statement(bal.clone());
    let (proof, hint) =
        singleprover_prove_with_hint::<NewOutputBalanceValidityCircuit>(&witness, &statement)?;

    let share_seed = witness.initial_share_stream.seed;
    let recovery_seed = witness.initial_recovery_stream.seed;

    // Build the balance; compute a recovery ID to match the stream state after the circuit applies
    let mut state_balance = StateWrapper::new(bal, share_seed, recovery_seed);
    state_balance.compute_recovery_id();
    Ok((state_balance, statement, proof, hint))
}

/// Generate an output balance validity proof for an existing balance
pub(crate) fn generate_existing_output_balance_validity_proof(
    balance: &mut DarkpoolStateBalance,
    balance_opening: &MerkleAuthenticationPath,
) -> Result<(OutputBalanceValidityStatement, PlonkProof, ProofLinkingHint)> {
    // Build the witness and statement
    let old_balance = balance.clone();
    let old_balance_nullifier = old_balance.compute_nullifier();
    let post_match_balance_shares = balance.reencrypt_post_match_share();

    let recovery_id = balance.compute_recovery_id();
    let new_partial_commitment =
        balance.compute_partial_commitment(BALANCE_PARTIAL_COMMITMENT_SIZE);

    let witness = OutputBalanceValidityWitness {
        balance: old_balance.inner.clone(),
        old_balance,
        balance_opening: balance_opening.clone().into(),
        post_match_balance_shares,
    };

    let statement = OutputBalanceValidityStatement {
        merkle_root: balance_opening.compute_root(),
        old_balance_nullifier,
        new_partial_commitment,
        recovery_id,
    };

    // Prove the relation
    let (proof, hint) =
        singleprover_prove_with_hint::<SizedOutputBalanceValidityCircuit>(&witness, &statement)?;
    Ok((statement, proof, hint))
}

/// Generate a settlement proof for the fill
fn generate_settlement_proof(
    intent: &DarkpoolStateIntent,
    input_balance: &DarkpoolStateBalance,
    output_balance: &DarkpoolStateBalance,
    obligation: &SettlementObligation,
) -> Result<(
    IntentAndBalancePublicSettlementStatement,
    PlonkProof,
    ProofLinkingHint,
)> {
    let pre_settlement_amount_public_share = intent.public_share.amount_in;
    let pre_settlement_in_balance_shares =
        PostMatchBalanceShare::from(input_balance.public_share.clone());
    let pre_settlement_out_balance_shares =
        PostMatchBalanceShare::from(output_balance.public_share.clone());

    let witness = IntentAndBalancePublicSettlementWitness {
        intent: intent.inner.clone(),
        pre_settlement_amount_public_share,
        in_balance: input_balance.inner.clone(),
        pre_settlement_in_balance_shares: pre_settlement_in_balance_shares.clone(),
        out_balance: output_balance.inner.clone(),
        pre_settlement_out_balance_shares: pre_settlement_out_balance_shares.clone(),
    };

    let statement = IntentAndBalancePublicSettlementStatement {
        settlement_obligation: obligation.clone(),
        amount_public_share: pre_settlement_amount_public_share,
        in_balance_public_shares: pre_settlement_in_balance_shares,
        out_balance_public_shares: pre_settlement_out_balance_shares,
        relayer_fee: settlement_relayer_fee(),
        relayer_fee_recipient: output_balance.inner.relayer_fee_recipient,
    };

    // Prove the relation
    let (proof, hint) = singleprover_prove_with_hint::<IntentAndBalancePublicSettlementCircuit>(
        &witness, &statement,
    )?;
    Ok((statement, proof, hint))
}

// --- Proof Linking --- //

/// Generate a linking proof between a validity proof and a settlement proof
fn generate_validity_settlement_linking_proof(
    validity_hint: &ProofLinkingHint,
    settlement_hint: &ProofLinkingHint,
) -> Result<PlonkLinkProof> {
    let proof = link_sized_intent_and_balance_settlement(validity_hint, settlement_hint)?;

    Ok(proof)
}

/// Generate a linking proof between an output balance validity proof and a settlement proof
fn generate_output_balance_settlement_linking_proof(
    output_balance_hint: &ProofLinkingHint,
    settlement_hint: &ProofLinkingHint,
) -> Result<PlonkLinkProof> {
    let proof = link_sized_output_balance_settlement(output_balance_hint, settlement_hint)?;
    Ok(proof)
}

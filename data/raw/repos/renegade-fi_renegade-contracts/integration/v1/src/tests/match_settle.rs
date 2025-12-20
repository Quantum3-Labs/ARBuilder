//! Tests for settling internal matches

use abi::v1::{
    relayer_types::{address_to_biguint, biguint_to_address, u256_to_scalar},
    IDarkpool::{
        MatchLinkingProofs, MatchProofs, PartyMatchPayload,
        ValidMatchSettleStatement as ContractValidMatchSettleStatement,
        ValidMatchSettleWithCommitmentsStatement as ContractValidMatchSettleWithCommitmentsStatement,
    },
};
use eyre::{eyre, Result};
use renegade_circuit_types::{
    balance::Balance,
    fixed_point::FixedPoint,
    native_helpers::{compute_wallet_commitment_from_private, create_wallet_shares_from_private},
    order::Order,
    r#match::{MatchResult, OrderSettlementIndices},
    PlonkProof, ProofLinkingHint, SizedWallet,
};
use renegade_circuits::{
    singleprover_prove_with_hint,
    test_helpers::random_orders_and_match,
    zk_circuits::{
        proof_linking::{
            link_sized_commitments_match_settle,
            link_sized_commitments_match_settle_with_commitments, link_sized_commitments_reblind,
        },
        valid_commitments::{
            SizedValidCommitments, SizedValidCommitmentsWitness, ValidCommitmentsStatement,
        },
        valid_match_settle::{
            SizedValidMatchSettle, SizedValidMatchSettleStatement,
            SizedValidMatchSettleWithCommitments, SizedValidMatchSettleWithCommitmentsStatement,
            ValidMatchSettleWitness,
        },
        valid_reblind::{SizedValidReblind, SizedValidReblindWitness, ValidReblindStatement},
    },
};
use renegade_common::types::wallet::{OrderIdentifier, Wallet};
use renegade_constants::Scalar;
use renegade_util::matching_engine::{
    apply_match_to_shares, compute_fee_obligation_with_protocol_fee,
};
use test_helpers::integration_test_async;

use crate::{
    util::{merkle::update_wallet_opening, transactions::call_helper, WrapEyre},
    TestArgs,
};

use super::{
    create_wallet::create_darkpool_wallet,
    update_wallet::{fund_and_deposit, submit_wallet_update},
};

/// Test settling a match
async fn test_match_settle(args: TestArgs) -> Result<(), eyre::Error> {
    let darkpool = args.darkpool.clone();
    let (price, match_result, mut wallet1, mut wallet2) = create_match_and_wallets(&args).await?;

    // Generate calldata and submit the match
    let protocol_fee_rate = call_helper(darkpool.protocolFeeRate()).await?;
    let fee_rate = FixedPoint::from_repr(u256_to_scalar(protocol_fee_rate));
    let (
        party0_payload,
        party1_payload,
        match_settle_statement,
        match_proofs,
        match_linking_proofs,
    ) = prove_match_bundle(price, fee_rate, &wallet1, &wallet2, match_result)?;
    let call = darkpool.processMatchSettle(
        party0_payload,
        party1_payload,
        match_settle_statement,
        match_proofs,
        match_linking_proofs,
    );
    call_helper(call).await?;

    // Refresh the Merkle proofs for both wallets
    update_wallet_opening(&mut wallet1, &darkpool).await?;
    update_wallet_opening(&mut wallet2, &darkpool).await?;

    Ok(())
}
integration_test_async!(test_match_settle);

/// Test settling a match with commitments attached
#[allow(unused, dead_code)]
async fn test_match_settle_with_commitments(args: TestArgs) -> Result<(), eyre::Error> {
    println!("[skipped] match with commitments is currently disabled");
    return Ok(());

    let darkpool = args.darkpool.clone();
    let (price, match_result, mut wallet1, mut wallet2) = create_match_and_wallets(&args).await?;

    // Generate calldata and submit the match
    let protocol_fee_rate = call_helper(darkpool.protocolFeeRate()).await?;
    let fee_rate = FixedPoint::from_repr(u256_to_scalar(protocol_fee_rate));
    let (
        party0_payload,
        party1_payload,
        match_settle_statement,
        match_proofs,
        match_linking_proofs,
    ) = prove_match_bundle_with_commitments(price, fee_rate, &wallet1, &wallet2, match_result)?;
    let call = darkpool.processMatchSettleWithCommitments(
        party0_payload,
        party1_payload,
        match_settle_statement,
        match_proofs,
        match_linking_proofs,
    );
    call_helper(call).await?;

    // Refresh the Merkle proofs for both wallets
    update_wallet_opening(&mut wallet1, &darkpool).await?;
    update_wallet_opening(&mut wallet2, &darkpool).await?;

    Ok(())
}
integration_test_async!(test_match_settle_with_commitments);

// -----------
// | Helpers |
// -----------

/// Create two wallets for a match
async fn create_match_and_wallets(
    args: &TestArgs,
) -> Result<(FixedPoint, MatchResult, Wallet, Wallet)> {
    let darkpool = args.darkpool.clone();

    // Create two wallets
    let old_wallet1 = create_darkpool_wallet(args).await?;
    let old_wallet2 = create_darkpool_wallet(args).await?;
    let mut wallet1 = old_wallet1.clone();
    let mut wallet2 = old_wallet2.clone();

    // Place orders in each wallet
    let oid1 = OrderIdentifier::new_v4();
    let oid2 = OrderIdentifier::new_v4();
    let (o1, o2, price, match_result) = create_match_data(args)?;
    wallet1.add_order(oid1, o1.clone().into()).to_eyre()?;
    wallet2.add_order(oid2, o2.clone().into()).to_eyre()?;
    wallet1.reblind_wallet();
    wallet2.reblind_wallet();

    submit_wallet_update(old_wallet1, wallet1.clone(), args).await?;
    submit_wallet_update(old_wallet2, wallet2.clone(), args).await?;
    update_wallet_opening(&mut wallet1, &darkpool).await?;
    update_wallet_opening(&mut wallet2, &darkpool).await?;

    // Deposit into each wallet
    fund_wallet_for_match(&match_result, &o1, &mut wallet1, args).await?;
    fund_wallet_for_match(&match_result, &o2, &mut wallet2, args).await?;

    Ok((price, match_result, wallet1, wallet2))
}

/// --- Test Data --- //

/// Create two orders and a match
pub(crate) fn create_match_data(
    args: &TestArgs,
) -> Result<(Order, Order, FixedPoint, MatchResult)> {
    let base_addr = address_to_biguint(*args.base_token()?.address());
    let quote_addr = address_to_biguint(*args.quote_token()?.address());

    let (mut o1, mut o2, price, mut match_result) = random_orders_and_match();
    o1.base_mint = base_addr.clone();
    o1.quote_mint = quote_addr.clone();
    o2.base_mint = base_addr.clone();
    o2.quote_mint = quote_addr.clone();
    match_result.base_mint = base_addr.clone();
    match_result.quote_mint = quote_addr.clone();
    Ok((o1, o2, price, match_result))
}

// --- Funding --- //

/// Fund a wallet ahead of a match
pub(crate) async fn fund_wallet_for_match(
    match_result: &MatchResult,
    order: &Order,
    wallet: &mut Wallet,
    args: &TestArgs,
) -> Result<(), eyre::Error> {
    let (sell_mint, sell_amount) = match_result.send_mint_amount(order.side);
    let sell_token = biguint_to_address(sell_mint);
    fund_and_deposit(sell_token, sell_amount, wallet, args).await
}

// --- Prover Helpers --- //

/// Get a match bundle for the orders and match result
fn prove_match_bundle(
    price: FixedPoint,
    protocol_fee_rate: FixedPoint,
    w1: &Wallet,
    w2: &Wallet,
    match_result: MatchResult,
) -> Result<
    (
        PartyMatchPayload,
        PartyMatchPayload,
        ContractValidMatchSettleStatement,
        MatchProofs,
        MatchLinkingProofs,
    ),
    eyre::Error,
> {
    let mut w1 = w1.clone();
    let mut w2 = w2.clone();

    // Construct validity proofs for each wallet
    let (reblind_statement1, reblind_proof1, reblind_hint1) = prove_reblind(&mut w1)?;
    let (reblind_statement2, reblind_proof2, reblind_hint2) = prove_reblind(&mut w2)?;
    let (commitments_statement1, commitments_witness1, commitments_proof1, commitments_hint1) =
        prove_commitments(&match_result, &w1)?;
    let (commitments_statement2, commitments_witness2, commitments_proof2, commitments_hint2) =
        prove_commitments(&match_result, &w2)?;

    // Construct a proof of `VALID MATCH SETTLE`
    let (match_settle_statement, match_settle_proof, match_settle_hint) = prove_match_settle(
        price,
        protocol_fee_rate,
        commitments_statement1,
        commitments_statement2,
        commitments_witness1,
        commitments_witness2,
        match_result,
    )?;

    // Proof linking
    let reblind_commitments_link1 =
        link_sized_commitments_reblind(&reblind_hint1, &commitments_hint1)?;
    let reblind_commitments_link2 =
        link_sized_commitments_reblind(&reblind_hint2, &commitments_hint2)?;

    let match_settle_commitments_link1 = link_sized_commitments_match_settle(
        0, /* party_id */
        &commitments_hint1,
        &match_settle_hint,
    )?;
    let match_settle_commitments_link2 = link_sized_commitments_match_settle(
        1, /* party_id */
        &commitments_hint2,
        &match_settle_hint,
    )?;

    // Construct the calldata payloads
    let party0_payload = PartyMatchPayload {
        validReblindStatement: reblind_statement1.into(),
        validCommitmentsStatement: commitments_statement1.into(),
    };
    let party1_payload = PartyMatchPayload {
        validReblindStatement: reblind_statement2.into(),
        validCommitmentsStatement: commitments_statement2.into(),
    };
    let match_proofs = MatchProofs {
        validReblind0: reblind_proof1.into(),
        validCommitments0: commitments_proof1.into(),
        validCommitments1: commitments_proof2.into(),
        validReblind1: reblind_proof2.into(),
        validMatchSettle: match_settle_proof.into(),
    };
    let match_linking_proofs = MatchLinkingProofs {
        validReblindCommitments0: reblind_commitments_link1.into(),
        validCommitmentsMatchSettle0: match_settle_commitments_link1.into(),
        validCommitmentsMatchSettle1: match_settle_commitments_link2.into(),
        validReblindCommitments1: reblind_commitments_link2.into(),
    };

    Ok((
        party0_payload,
        party1_payload,
        match_settle_statement.into(),
        match_proofs,
        match_linking_proofs,
    ))
}

/// Prove a match bundle with commitments
fn prove_match_bundle_with_commitments(
    price: FixedPoint,
    protocol_fee_rate: FixedPoint,
    w1: &Wallet,
    w2: &Wallet,
    match_result: MatchResult,
) -> Result<
    (
        PartyMatchPayload,
        PartyMatchPayload,
        ContractValidMatchSettleWithCommitmentsStatement,
        MatchProofs,
        MatchLinkingProofs,
    ),
    eyre::Error,
> {
    let mut w1 = w1.clone();
    let mut w2 = w2.clone();

    // Construct validity proofs for each wallet
    let (reblind_statement1, reblind_proof1, reblind_hint1) = prove_reblind(&mut w1)?;
    let (reblind_statement2, reblind_proof2, reblind_hint2) = prove_reblind(&mut w2)?;
    let (commitments_statement1, commitments_witness1, commitments_proof1, commitments_hint1) =
        prove_commitments(&match_result, &w1)?;
    let (commitments_statement2, commitments_witness2, commitments_proof2, commitments_hint2) =
        prove_commitments(&match_result, &w2)?;

    // Construct a proof of `VALID MATCH SETTLE`
    let (match_settle_statement, match_settle_proof, match_settle_hint) =
        prove_match_settle_with_commitments(
            price,
            protocol_fee_rate,
            reblind_statement1.clone(),
            reblind_statement2.clone(),
            commitments_statement1,
            commitments_statement2,
            commitments_witness1,
            commitments_witness2,
            match_result,
        )?;

    // Proof linking
    let reblind_commitments_link1 =
        link_sized_commitments_reblind(&reblind_hint1, &commitments_hint1)?;
    let reblind_commitments_link2 =
        link_sized_commitments_reblind(&reblind_hint2, &commitments_hint2)?;

    let match_settle_commitments_link1 = link_sized_commitments_match_settle_with_commitments(
        0, /* party_id */
        &commitments_hint1,
        &match_settle_hint,
    )?;
    let match_settle_commitments_link2 = link_sized_commitments_match_settle_with_commitments(
        1, /* party_id */
        &commitments_hint2,
        &match_settle_hint,
    )?;

    // Construct the calldata payloads
    let party0_payload = PartyMatchPayload {
        validReblindStatement: reblind_statement1.into(),
        validCommitmentsStatement: commitments_statement1.into(),
    };
    let party1_payload = PartyMatchPayload {
        validReblindStatement: reblind_statement2.into(),
        validCommitmentsStatement: commitments_statement2.into(),
    };
    let match_proofs = MatchProofs {
        validReblind0: reblind_proof1.into(),
        validCommitments0: commitments_proof1.into(),
        validCommitments1: commitments_proof2.into(),
        validReblind1: reblind_proof2.into(),
        validMatchSettle: match_settle_proof.into(),
    };
    let match_linking_proofs = MatchLinkingProofs {
        validReblindCommitments0: reblind_commitments_link1.into(),
        validCommitmentsMatchSettle0: match_settle_commitments_link1.into(),
        validCommitmentsMatchSettle1: match_settle_commitments_link2.into(),
        validReblindCommitments1: reblind_commitments_link2.into(),
    };

    Ok((
        party0_payload,
        party1_payload,
        match_settle_statement.into(),
        match_proofs,
        match_linking_proofs,
    ))
}

/// Prove valid reblind for a wallet
///
/// Modifies the wallet in place by reblinding
pub(crate) fn prove_reblind(
    wallet: &mut Wallet,
) -> Result<(ValidReblindStatement, PlonkProof, ProofLinkingHint)> {
    let original_wallet = wallet.clone();
    wallet.reblind_wallet();
    let merkle_proof = original_wallet
        .merkle_proof
        .clone()
        .ok_or(eyre!("no merkle proof"))?;
    let merkle_root = merkle_proof.compute_root();

    let witness = SizedValidReblindWitness {
        original_wallet_private_shares: original_wallet.private_shares.clone(),
        original_wallet_public_shares: original_wallet.blinded_public_shares.clone(),
        reblinded_wallet_private_shares: wallet.private_shares.clone(),
        reblinded_wallet_public_shares: wallet.blinded_public_shares.clone(),
        original_share_opening: merkle_proof.into(),
        sk_match: original_wallet.key_chain.sk_match(),
    };

    let original_shares_nullifier = original_wallet.get_wallet_nullifier();
    let reblinded_private_share_commitment = wallet.get_private_share_commitment();
    let statement = ValidReblindStatement {
        merkle_root,
        original_shares_nullifier,
        reblinded_private_share_commitment,
    };

    let (proof, hint) =
        singleprover_prove_with_hint::<SizedValidReblind>(witness.clone(), statement.clone())?;
    Ok((statement, proof, hint))
}

/// Prove valid commitments for a wallet
///
/// Assumes the wallet only has one order for simplicity
///
/// Assumes that the wallet has already been reblinded
pub(crate) fn prove_commitments(
    match_result: &MatchResult,
    wallet: &Wallet,
) -> Result<
    (
        ValidCommitmentsStatement,
        SizedValidCommitmentsWitness,
        PlonkProof,
        ProofLinkingHint,
    ),
    eyre::Error,
> {
    assert!(wallet.orders.len() == 1, "only one order supported");
    let mut augmented_wallet = wallet.clone();

    let order = wallet.orders.values().next().unwrap().clone();
    let (send_mint, _) = match_result.send_mint_amount(order.side);
    let (recv_mint, _) = match_result.receive_mint_amount(order.side);

    let order_idx = 0;
    let send_bal_idx = wallet
        .get_balance_index(&send_mint)
        .expect("must have send balance");
    let balance_send = wallet.get_balance(&send_mint).unwrap().clone();

    // Augment the wallet with the receive balance
    let empty_bal = Balance::new_from_mint(recv_mint.clone());
    augmented_wallet.add_balance(empty_bal).to_eyre()?;
    let recv_bal_idx = augmented_wallet.balances.index_of(&recv_mint).unwrap();
    let balance_receive = augmented_wallet.get_balance(&recv_mint).unwrap().clone();

    let blinder = augmented_wallet.blinder;
    let augmented_circuit_wallet: SizedWallet = augmented_wallet.into();
    let (_, augmented_public_shares) = create_wallet_shares_from_private(
        &augmented_circuit_wallet,
        &wallet.private_shares.clone(),
        blinder,
    );

    let statement = ValidCommitmentsStatement {
        indices: OrderSettlementIndices {
            order: order_idx,
            balance_send: send_bal_idx,
            balance_receive: recv_bal_idx,
        },
    };

    let reblinded_private_shares = wallet.private_shares.clone();
    let reblinded_public_shares = wallet.blinded_public_shares.clone();
    let witness = SizedValidCommitmentsWitness {
        private_secret_shares: reblinded_private_shares,
        public_secret_shares: reblinded_public_shares,
        augmented_public_shares,
        order: order.into(),
        balance_send,
        balance_receive,
        relayer_fee: FixedPoint::from_integer(0),
    };

    let (proof, hint) =
        singleprover_prove_with_hint::<SizedValidCommitments>(witness.clone(), statement)?;
    Ok((statement, witness, proof, hint))
}

/// Prove valid match settle
fn prove_match_settle(
    price: FixedPoint,
    fee_rate: FixedPoint,
    commitments_statement1: ValidCommitmentsStatement,
    commitments_statement2: ValidCommitmentsStatement,
    commitments_witness1: SizedValidCommitmentsWitness,
    commitments_witness2: SizedValidCommitmentsWitness,
    match_result: MatchResult,
) -> Result<(SizedValidMatchSettleStatement, PlonkProof, ProofLinkingHint), eyre::Error> {
    // Compute the fees
    let relayer_fee = FixedPoint::from_integer(0);
    let o1 = &commitments_witness1.order;
    let o2 = &commitments_witness2.order;
    let fee1 =
        compute_fee_obligation_with_protocol_fee(relayer_fee, fee_rate, o1.side, &match_result);
    let fee2 =
        compute_fee_obligation_with_protocol_fee(relayer_fee, fee_rate, o2.side, &match_result);

    // Apply the match to the shares
    let order0 = commitments_witness1.order;
    let order1 = commitments_witness2.order;
    let balance0 = commitments_witness1.balance_send;
    let balance1 = commitments_witness2.balance_send;
    let balance_receive0 = commitments_witness1.balance_receive;
    let balance_receive1 = commitments_witness2.balance_receive;
    let party0_indices = commitments_statement1.indices;
    let party1_indices = commitments_statement2.indices;
    let mut party0_shares = commitments_witness1.augmented_public_shares.clone();
    let mut party1_shares = commitments_witness2.augmented_public_shares.clone();
    apply_match_to_shares(
        &mut party0_shares,
        &party0_indices,
        fee1,
        &match_result,
        order0.side,
    );
    apply_match_to_shares(
        &mut party1_shares,
        &party1_indices,
        fee2,
        &match_result,
        order1.side,
    );

    // Build the statement and witness
    let statement = SizedValidMatchSettleStatement {
        party0_indices: commitments_statement1.indices,
        party1_indices: commitments_statement2.indices,
        party0_modified_shares: party0_shares.clone(),
        party1_modified_shares: party1_shares.clone(),
        protocol_fee: fee_rate,
    };

    let match_amt = match_result.base_amount;
    let witness = ValidMatchSettleWitness {
        order0: order0.clone(),
        balance0,
        balance_receive0,
        relayer_fee0: FixedPoint::from_integer(0),
        party0_fees: fee1,
        price0: price,
        amount0: Scalar::from(match_amt),
        order1: order1.clone(),
        balance1,
        balance_receive1,
        relayer_fee1: FixedPoint::from_integer(0),
        party1_fees: fee2,
        price1: price,
        amount1: Scalar::from(match_amt),
        match_res: match_result,
        party0_public_shares: commitments_witness1.augmented_public_shares.clone(),
        party1_public_shares: commitments_witness2.augmented_public_shares.clone(),
    };

    let (proof, hint) =
        singleprover_prove_with_hint::<SizedValidMatchSettle>(witness, statement.clone())?;
    Ok((statement, proof, hint))
}

/// Prove valid match settle with commitments
#[allow(clippy::too_many_arguments)]
#[allow(clippy::needless_pass_by_value)]
fn prove_match_settle_with_commitments(
    price: FixedPoint,
    fee_rate: FixedPoint,
    reblind_statement1: ValidReblindStatement,
    reblind_statement2: ValidReblindStatement,
    commitments_statement1: ValidCommitmentsStatement,
    commitments_statement2: ValidCommitmentsStatement,
    commitments_witness1: SizedValidCommitmentsWitness,
    commitments_witness2: SizedValidCommitmentsWitness,
    match_result: MatchResult,
) -> Result<
    (
        SizedValidMatchSettleWithCommitmentsStatement,
        PlonkProof,
        ProofLinkingHint,
    ),
    eyre::Error,
> {
    // Compute the fees
    let relayer_fee = FixedPoint::from_integer(0);
    let o1 = &commitments_witness1.order;
    let o2 = &commitments_witness2.order;
    let fee1 =
        compute_fee_obligation_with_protocol_fee(relayer_fee, fee_rate, o1.side, &match_result);
    let fee2 =
        compute_fee_obligation_with_protocol_fee(relayer_fee, fee_rate, o2.side, &match_result);

    // Apply the match to the shares
    let order0 = commitments_witness1.order;
    let order1 = commitments_witness2.order;
    let balance0 = commitments_witness1.balance_send;
    let balance1 = commitments_witness2.balance_send;
    let balance_receive0 = commitments_witness1.balance_receive;
    let balance_receive1 = commitments_witness2.balance_receive;
    let party0_indices = commitments_statement1.indices;
    let party1_indices = commitments_statement2.indices;
    let mut party0_shares = commitments_witness1.augmented_public_shares.clone();
    let mut party1_shares = commitments_witness2.augmented_public_shares.clone();
    apply_match_to_shares(
        &mut party0_shares,
        &party0_indices,
        fee1,
        &match_result,
        order0.side,
    );
    apply_match_to_shares(
        &mut party1_shares,
        &party1_indices,
        fee2,
        &match_result,
        order1.side,
    );

    // Compute the new share commitments
    let private_share_commitment0 = reblind_statement1.reblinded_private_share_commitment;
    let private_share_commitment1 = reblind_statement2.reblinded_private_share_commitment;
    let new_share_commitment0 =
        compute_wallet_commitment_from_private(&party0_shares, private_share_commitment0);
    let new_share_commitment1 =
        compute_wallet_commitment_from_private(&party1_shares, private_share_commitment1);

    // Build the statement and witness
    let statement = SizedValidMatchSettleWithCommitmentsStatement {
        private_share_commitment0,
        private_share_commitment1,
        new_share_commitment0,
        new_share_commitment1,
        party0_indices: commitments_statement1.indices,
        party1_indices: commitments_statement2.indices,
        party0_modified_shares: party0_shares.clone(),
        party1_modified_shares: party1_shares.clone(),
        protocol_fee: fee_rate,
    };

    let match_amt = match_result.base_amount;
    let witness = ValidMatchSettleWitness {
        order0: order0.clone(),
        balance0,
        balance_receive0,
        relayer_fee0: FixedPoint::from_integer(0),
        party0_fees: fee1,
        price0: price,
        amount0: Scalar::from(match_amt),
        order1: order1.clone(),
        balance1,
        balance_receive1,
        relayer_fee1: FixedPoint::from_integer(0),
        party1_fees: fee2,
        price1: price,
        amount1: Scalar::from(match_amt),
        match_res: match_result,
        party0_public_shares: commitments_witness1.augmented_public_shares.clone(),
        party1_public_shares: commitments_witness2.augmented_public_shares.clone(),
    };

    let (proof, hint) = singleprover_prove_with_hint::<SizedValidMatchSettleWithCommitments>(
        witness,
        statement.clone(),
    )?;
    Ok((statement, proof, hint))
}

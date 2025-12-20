//! Integration tests for atomic match settlement

use abi::v1::IDarkpool::{
    MatchAtomicLinkingProofs, MatchAtomicProofs, PartyMatchPayload,
    ValidMatchSettleAtomicStatement as ContractValidMatchSettleAtomicStatement,
};
use alloy::primitives::{Address, U256};
use eyre::Result;
use renegade_circuit_types::{
    fixed_point::FixedPoint,
    r#match::{ExternalMatchResult, MatchResult},
    PlonkProof, ProofLinkingHint,
};
use renegade_circuits::{
    singleprover_prove_with_hint,
    zk_circuits::{
        proof_linking::{link_sized_commitments_match_settle, link_sized_commitments_reblind},
        valid_commitments::{SizedValidCommitmentsWitness, ValidCommitmentsStatement},
        valid_match_settle_atomic::{
            SizedValidMatchSettleAtomic, SizedValidMatchSettleAtomicStatement,
            SizedValidMatchSettleAtomicWitness,
        },
    },
};
use renegade_common::types::wallet::{OrderIdentifier, Wallet};
use renegade_darkpool_client::conversion::{
    address_to_biguint, biguint_to_address, u256_to_scalar,
};
use renegade_util::matching_engine::{
    apply_match_to_shares, compute_fee_obligation_with_protocol_fee,
};
use test_helpers::integration_test_async;

use crate::{
    util::{
        merkle::update_wallet_opening,
        transactions::{call_helper, send_tx},
        WrapEyre,
    },
    TestArgs,
};

use super::{
    create_wallet::create_darkpool_wallet,
    match_settle::{create_match_data, fund_wallet_for_match, prove_commitments, prove_reblind},
    update_wallet::submit_wallet_update,
};

/// Test atomic match settlement
async fn test_atomic_match_settle(args: TestArgs) -> Result<(), eyre::Error> {
    let darkpool = args.darkpool.clone();

    // Get the protocol fee rate
    let protocol_fee_rate = call_helper(darkpool.protocolFeeRate()).await?;
    let fee_rate = FixedPoint::from_repr(u256_to_scalar(protocol_fee_rate));

    // Create an internal party wallet
    let old_internal_wallet = create_darkpool_wallet(&args).await?;
    let mut internal_wallet = old_internal_wallet.clone();

    // Place an order in the wallet and deposit into it
    let oid = OrderIdentifier::new_v4();
    let (o1, _o2, price, match_res) = create_match_data(&args)?;

    internal_wallet
        .add_order(oid, o1.clone().into())
        .to_eyre()?;
    internal_wallet.reblind_wallet();

    submit_wallet_update(old_internal_wallet, internal_wallet.clone(), &args).await?;
    update_wallet_opening(&mut internal_wallet, &args.darkpool).await?;
    fund_wallet_for_match(&match_res, &o1, &mut internal_wallet, &args).await?;

    // Generate the atomic match bundle with all proofs and linking
    let (internal_party_payload, atomic_match_statement, atomic_proofs, atomic_linking_proofs) =
        prove_atomic_match_bundle(price, fee_rate, &internal_wallet, &match_res)?;

    // Call processAtomicMatchSettle on the darkpool
    fund_external_party(&match_res, &args).await?;
    let call = darkpool.processAtomicMatchSettle(
        args.wallet_addr(),
        internal_party_payload,
        atomic_match_statement,
        atomic_proofs,
        atomic_linking_proofs,
    );
    send_tx(call).await?;

    // Refresh the Merkle proof for the internal wallet
    update_wallet_opening(&mut internal_wallet, &darkpool).await?;
    Ok(())
}

integration_test_async!(test_atomic_match_settle);

// -----------
// | Helpers |
// -----------

/// Fund the external party with the amount needed to settle the match
async fn fund_external_party(match_res: &MatchResult, args: &TestArgs) -> Result<(), eyre::Error> {
    // 1. Mint tokens to the sender
    let external_match_res: ExternalMatchResult = match_res.clone().into();
    let (sell_mint, sell_amount) = external_match_res.external_party_send();
    let sell_addr = biguint_to_address(&sell_mint)?;
    args.fund_address(args.wallet_addr(), sell_addr, sell_amount)
        .await?;

    // 2. Approve the darkpool to spend the tokens
    let erc20 = args.erc20_from_addr(sell_addr)?;
    let approve_tx = erc20.approve(args.darkpool_addr(), U256::from(sell_amount));
    send_tx(approve_tx).await?;

    Ok(())
}

/// Prove an atomic match bundle for the orders and match
fn prove_atomic_match_bundle(
    price: FixedPoint,
    protocol_fee_rate: FixedPoint,
    wallet: &Wallet,
    match_result: &MatchResult,
) -> Result<
    (
        PartyMatchPayload,
        ContractValidMatchSettleAtomicStatement,
        MatchAtomicProofs,
        MatchAtomicLinkingProofs,
    ),
    eyre::Error,
> {
    let mut wallet = wallet.clone();

    // Generate reblind and commitments proofs
    let (reblind_statement, reblind_proof, reblind_linking_hint) = prove_reblind(&mut wallet)?;
    let (commitments_statement, commitments_witness, commitments_proof, commitments_linking_hint) =
        prove_commitments(match_result, &wallet)?;

    // Generate atomic match settle proof
    let (atomic_match_statement, atomic_match_proof, atomic_match_linking_hint) =
        prove_atomic_match_settle(
            price,
            protocol_fee_rate,
            commitments_statement,
            commitments_witness,
            match_result,
        )?;

    // Generate the linking proofs
    let reblind_commitments_link =
        link_sized_commitments_reblind(&reblind_linking_hint, &commitments_linking_hint)?;
    let commitments_match_settle_link = link_sized_commitments_match_settle(
        0, /* party_id */
        &commitments_linking_hint,
        &atomic_match_linking_hint,
    )?;

    // Build calldata for an atomic match settle
    let internal_party_payload = PartyMatchPayload {
        validReblindStatement: reblind_statement.into(),
        validCommitmentsStatement: commitments_statement.into(),
    };

    let atomic_proofs = MatchAtomicProofs {
        validReblind: reblind_proof.into(),
        validCommitments: commitments_proof.into(),
        validMatchSettleAtomic: atomic_match_proof.into(),
    };

    let atomic_linking_proofs = MatchAtomicLinkingProofs {
        validReblindCommitments: reblind_commitments_link.into(),
        validCommitmentsMatchSettleAtomic: commitments_match_settle_link.into(),
    };

    Ok((
        internal_party_payload,
        atomic_match_statement.into(),
        atomic_proofs,
        atomic_linking_proofs,
    ))
}

/// Prove atomic match settle
fn prove_atomic_match_settle(
    price: FixedPoint,
    protocol_fee_rate: FixedPoint,
    commitments_statement: ValidCommitmentsStatement,
    commitments_witness: SizedValidCommitmentsWitness,
    match_result: &MatchResult,
) -> Result<
    (
        SizedValidMatchSettleAtomicStatement,
        PlonkProof,
        ProofLinkingHint,
    ),
    eyre::Error,
> {
    // Extract values from the commitments witness and statement
    let internal_party_order = commitments_witness.order;
    let internal_party_balance = commitments_witness.balance_send;
    let internal_party_receive_balance = commitments_witness.balance_receive;
    let internal_party_public_shares = commitments_witness.augmented_public_shares.clone();
    let internal_party_indices = commitments_statement.indices;
    let relayer_fee = commitments_witness.relayer_fee;

    // Compute the fees
    let internal_party_fees = compute_fee_obligation_with_protocol_fee(
        relayer_fee,
        protocol_fee_rate,
        internal_party_order.side,
        match_result,
    );
    let external_party_fees = compute_fee_obligation_with_protocol_fee(
        relayer_fee,
        protocol_fee_rate,
        internal_party_order.side.opposite(),
        match_result,
    );

    // Apply the match to the internal party's shares
    let mut internal_party_modified_shares = internal_party_public_shares.clone();
    apply_match_to_shares(
        &mut internal_party_modified_shares,
        &internal_party_indices,
        internal_party_fees,
        match_result,
        internal_party_order.side,
    );

    // Use a zero address for the relayer fee address in tests
    let relayer_fee_address = address_to_biguint(&Address::ZERO)?;

    // Build the statement and witness
    let statement = SizedValidMatchSettleAtomicStatement {
        match_result: match_result.clone().into(),
        external_party_fees,
        internal_party_modified_shares: internal_party_modified_shares.clone(),
        internal_party_indices,
        protocol_fee: protocol_fee_rate,
        relayer_fee_address,
    };

    let witness = SizedValidMatchSettleAtomicWitness {
        internal_party_order,
        internal_party_balance,
        internal_party_receive_balance,
        relayer_fee,
        internal_party_public_shares,
        price,
        internal_party_fees,
    };

    // Generate the proof
    let (proof, hint) =
        singleprover_prove_with_hint::<SizedValidMatchSettleAtomic>(witness, statement.clone())?;

    Ok((statement, proof, hint))
}

//! State update tests

use eyre::Result;
use renegade_circuit_types::{balance::DarkpoolStateBalance, intent::DarkpoolStateIntent};
use renegade_common::types::merkle::MerkleAuthenticationPath;

use crate::{
    test_args::TestArgs,
    tests::settlement::{
        private_fill::{self, SubsequentFillStateElements},
        private_intent_private_balance::{self, fund_ring2_party},
        split_obligation,
    },
    util::{merkle::find_state_element_opening, transactions::wait_for_tx_success},
};

mod cancel_order;
pub mod create_balance;
mod deposit;
mod fees;
mod withdraw;

/// The state elements for a private intent and private balance
#[allow(unused)]
pub(crate) struct PrivateIntentPrivateBalanceElements {
    /// The intent
    intent: DarkpoolStateIntent,
    /// The opening of the intent
    intent_opening: MerkleAuthenticationPath,
    /// The input balance
    input_balance: DarkpoolStateBalance,
    /// The opening of the input balance
    input_balance_opening: MerkleAuthenticationPath,
    /// The output balance
    output_balance: DarkpoolStateBalance,
    /// The opening of the output balance
    output_balance_opening: MerkleAuthenticationPath,
}

/// Setup a private intent and private balance for tests
///
/// This is facilitated by matching an intent against a ring-0 order to create the intent and output balance
///
/// These state elements are intentionally not completely filled or exhausted, so that we can test both the first and subsequent fill paths. We test a ring 3 match so that fees are accrued on the output balance for testing fee payments.
pub(crate) async fn setup_private_intent_private_balance(
    args: &TestArgs,
) -> Result<PrivateIntentPrivateBalanceElements> {
    // Build intents and obligations for a trade
    let (intent0, intent1, obligation0, obligation1) =
        private_intent_private_balance::create_intents_and_obligations(args)?;

    // Split the obligations
    // We want to return a set of state elements that are not completely filled or exhausted, so we only execute a first fill
    let (first_obligation0, _) = split_obligation(&obligation0);
    let (first_obligation1, _) = split_obligation(&obligation1);

    // Create the input balance and fund each party
    let party0_signer = args.party0_signer();
    let party1_signer = args.party1_signer();
    let (mut input_balance, input_balance_opening) =
        fund_ring2_party(&party0_signer, &obligation0, args).await?;
    let (mut counterparty_input_balance, counterparty_input_balance_opening) =
        fund_ring2_party(&party1_signer, &obligation1, args).await?;

    // Build the settlement bundles
    let (settlement_bundle0, settlement_bundle1, obligation_bundle, subsequent_fill_state_elements) =
        private_fill::build_first_fill_bundles(
            &intent0,
            &intent1,
            &first_obligation0,
            &first_obligation1,
            &mut input_balance,
            &mut counterparty_input_balance,
            &input_balance_opening,
            &counterparty_input_balance_opening,
            args,
        )
        .await?;

    // Settle the match
    let tx = args
        .darkpool
        .settleMatch(obligation_bundle, settlement_bundle0, settlement_bundle1);
    let tx_receipt = wait_for_tx_success(tx).await?;

    // Update the state values to match their post-settlement state committed on-chain
    let SubsequentFillStateElements {
        intent0: state_intent,
        input_bal0: input_balance,
        output_bal0: output_balance,
        ..
    } = subsequent_fill_state_elements;
    let intent_opening = find_state_element_opening(&state_intent, &tx_receipt).await?;
    let input_balance_opening = find_state_element_opening(&input_balance, &tx_receipt).await?;
    let output_balance_opening = find_state_element_opening(&output_balance, &tx_receipt).await?;

    Ok(PrivateIntentPrivateBalanceElements {
        intent: state_intent,
        intent_opening,
        input_balance,
        input_balance_opening,
        output_balance,
        output_balance_opening,
    })
}

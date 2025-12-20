//! Fuzzing helpers for integration tests

use crate::test_args::TestArgs;
use alloy::primitives::{Address, U256};
use eyre::Result;
use rand::{thread_rng, Rng};
use renegade_abi::v2::IDarkpoolV2::{Deposit, Withdrawal};
use renegade_circuit_types::{
    intent::Intent, max_amount, settlement_obligation::SettlementObligation, Amount,
};
use renegade_circuits::test_helpers::{compute_implied_price, compute_min_amount_out};

/// A random "amount" in the Renegade sense
///
/// An amount is a U256 of size at most 2 ** AMOUNT_BITS
pub fn random_amount() -> U256 {
    let amt_u128 = renegade_circuits::test_helpers::random_amount();
    U256::from(amt_u128)
}

/// Create a random deposit
pub fn random_deposit(args: &TestArgs) -> Result<Deposit> {
    Ok(Deposit {
        from: args.party0_addr(),
        token: args.base_addr()?,
        amount: random_amount(),
    })
}

/// Create a random withdrawal
pub fn random_withdrawal(
    max_amount: Amount,
    args: &TestArgs,
) -> Result<renegade_abi::v2::IDarkpoolV2::Withdrawal> {
    let mut rng = thread_rng();
    let amount = rng.gen_range(0..max_amount);
    Ok(Withdrawal {
        to: args.party0_addr(),
        token: args.base_addr()?,
        amount: U256::from(amount),
    })
}

/// Given an intent, create a compatible intent and two settlement obligations representing a trade
///
/// Returns: the counterparty's intent, the input party's obligation, the counterparty's obligation
pub fn create_matching_intents_and_obligations(
    intent: &Intent,
    counterparty: Address,
) -> Result<(Intent, SettlementObligation, SettlementObligation)> {
    // 1. Determine the trade parameters
    let mut rng = thread_rng();
    let party0_amt_in = rng.gen_range(0..intent.amount_in);
    let min_amt_out = compute_min_amount_out(intent, party0_amt_in);
    let party0_amt_out = rng.gen_range(min_amt_out..=max_amount());

    // 2. Build two compatible obligations
    let party0_obligation = SettlementObligation {
        input_token: intent.in_token,
        output_token: intent.out_token,
        amount_in: party0_amt_in,
        amount_out: party0_amt_out,
    };
    let party1_obligation = SettlementObligation {
        input_token: intent.out_token,
        output_token: intent.in_token,
        amount_in: party0_amt_out,
        amount_out: party0_amt_in,
    };

    // 3. Create a compatible intent for the counterparty
    let trade_price =
        compute_implied_price(party1_obligation.amount_out, party1_obligation.amount_in);
    let min_price = trade_price / 2u8;
    let amount_in = rng.gen_range(party0_amt_out..=max_amount());
    let counterparty_intent = Intent {
        in_token: intent.out_token,
        out_token: intent.in_token,
        owner: counterparty,
        min_price,
        amount_in,
    };

    Ok((counterparty_intent, party0_obligation, party1_obligation))
}

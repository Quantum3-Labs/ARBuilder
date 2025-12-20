//! Settlement tests

use eyre::Result;
use renegade_abi::v2::IDarkpoolV2::FeeRate;
use renegade_circuit_types::{
    fee::FeeTake, fixed_point::FixedPoint, settlement_obligation::SettlementObligation,
};
use renegade_crypto::fields::scalar_to_u128;

use crate::test_args::TestArgs;

pub(crate) mod private_fill;
pub(crate) mod private_intent_private_balance;
mod private_intent_public_balance;

/// The settlement relayer fee to use for testing
pub fn settlement_relayer_fee() -> FixedPoint {
    FixedPoint::from_f64_round_down(0.0001) // 1bp
}

/// Get the relayer's fee rate for settlement
pub fn settlement_relayer_fee_rate(args: &TestArgs) -> FeeRate {
    FeeRate {
        rate: settlement_relayer_fee().into(),
        recipient: args.relayer_signer_addr(),
    }
}

/// Get the total fee applicable to a settlement
pub async fn get_total_fee(args: &TestArgs) -> Result<(FixedPoint, FixedPoint)> {
    let protocol_fee = args.protocol_fee().await?;
    let relayer_fee = settlement_relayer_fee();
    Ok((relayer_fee, protocol_fee))
}

/// Compute the fee take for an obligation
pub async fn compute_fee_take(
    obligation: &SettlementObligation,
    args: &TestArgs,
) -> Result<FeeTake> {
    let (relayer_fee_rate, protocol_fee_rate) = get_total_fee(args).await?;
    let relayer_fee = relayer_fee_rate.floor_mul_int(obligation.amount_out);
    let protocol_fee = protocol_fee_rate.floor_mul_int(obligation.amount_out);

    Ok(FeeTake {
        relayer_fee: scalar_to_u128(&relayer_fee),
        protocol_fee: scalar_to_u128(&protocol_fee),
    })
}

/// Split an obligation in two
///
/// Returns the two splits of the obligation
pub(crate) fn split_obligation(
    obligation: &SettlementObligation,
) -> (SettlementObligation, SettlementObligation) {
    let mut obligation0 = obligation.clone();
    let mut obligation1 = obligation.clone();
    obligation0.amount_in /= 2;
    obligation0.amount_out /= 2;
    obligation1.amount_in /= 2;
    obligation1.amount_out /= 2;

    (obligation0, obligation1)
}

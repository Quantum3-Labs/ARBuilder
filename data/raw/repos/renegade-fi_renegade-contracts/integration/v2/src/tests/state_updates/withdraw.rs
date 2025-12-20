//! Tests for withdrawing from an existing balance

use eyre::Result;
use renegade_abi::v2::{
    IDarkpoolV2::{Withdrawal, WithdrawalProofBundle},
    relayer_types::u256_to_u128,
    transfer_auth::withdrawal::create_withdrawal_auth,
};
use renegade_circuit_types::balance::DarkpoolStateBalance;
use renegade_circuits::{
    singleprover_prove,
    test_helpers::check_constraints_satisfied,
    zk_circuits::valid_withdrawal::{
        SizedValidWithdrawal, SizedValidWithdrawalWitness, ValidWithdrawalStatement,
        ValidWithdrawalWitness,
    },
};
use renegade_common::types::merkle::MerkleAuthenticationPath;
use test_helpers::{assert_eq_result, assert_true_result, integration_test_async};

use crate::{
    test_args::TestArgs,
    tests::state_updates::create_balance::create_balance,
    util::{
        deposit::fund_for_deposit,
        fuzzing::{random_deposit, random_withdrawal},
        merkle::fetch_merkle_opening,
        transactions::wait_for_tx_success,
    },
};

/// Test withdrawing from an existing balance
async fn test_withdraw(args: TestArgs) -> Result<()> {
    // First, create a balance in the darkpool from a deposit
    let deposit = random_deposit(&args)?;
    let addr = deposit.token;
    fund_for_deposit(addr, &args.party0_signer(), &deposit, &args).await?;
    let (_receipt, balance) = create_balance(&args.party0_signer(), &deposit, &args).await?;

    // Find the balance's Merkle opening
    let commitment = balance.compute_commitment();
    let merkle_path = fetch_merkle_opening(commitment, &args.darkpool).await?;

    // Build a withdrawal for the wallet
    let withdrawal = random_withdrawal(balance.inner.amount, &args)?;
    let proof_bundle = create_proof_bundle(&withdrawal, &balance, &merkle_path)?;
    let new_balance_commitment = proof_bundle.statement.newBalanceCommitment;
    let withdrawal_auth = create_withdrawal_auth(new_balance_commitment, &args.party0_signer())?;

    // Send the withdrawal txn
    let party0_balance_before = args.base_balance(args.party0_addr()).await?;
    let darkpool_balance_before = args.base_balance(args.darkpool_addr()).await?;

    let call = args.darkpool.withdraw(withdrawal_auth, proof_bundle);
    wait_for_tx_success(call).await?;

    let party0_balance_after = args.base_balance(args.party0_addr()).await?;
    let darkpool_balance_after = args.base_balance(args.darkpool_addr()).await?;

    assert_eq_result!(
        party0_balance_after,
        party0_balance_before + withdrawal.amount
    )?;
    assert_eq_result!(
        darkpool_balance_after,
        darkpool_balance_before - withdrawal.amount
    )?;

    Ok(())
}
integration_test_async!(test_withdraw);

// -----------
// | Helpers |
// -----------

// --- Circuits Helpers --- //

/// Create a proof of the withdrawal
pub fn create_proof_bundle(
    withdrawal: &Withdrawal,
    balance: &DarkpoolStateBalance,
    opening: &MerkleAuthenticationPath,
) -> Result<WithdrawalProofBundle> {
    let (witness, statement) = build_witness_statement(withdrawal, balance, opening)?;
    let valid = check_constraints_satisfied::<SizedValidWithdrawal>(&witness, &statement);
    assert_true_result!(valid)?;

    let proof = singleprover_prove::<SizedValidWithdrawal>(&witness, &statement)?;

    // Create the bundle using the helper
    let bundle = WithdrawalProofBundle::new(statement, proof);
    Ok(bundle)
}

/// Build a witness statement for the withdrawal
fn build_witness_statement(
    withdrawal: &Withdrawal,
    balance: &DarkpoolStateBalance,
    opening: &MerkleAuthenticationPath,
) -> Result<(SizedValidWithdrawalWitness, ValidWithdrawalStatement)> {
    let witness = ValidWithdrawalWitness {
        old_balance: balance.clone(),
        old_balance_opening: opening.clone().into(),
    };

    // Build the new balance and re-encrypt the amount field
    let old_balance_nullifier = balance.compute_nullifier();
    let mut new_balance = balance.clone();
    new_balance.inner.amount -= u256_to_u128(withdrawal.amount);

    let new_amount = new_balance.inner.amount;
    let new_public_share = new_balance.stream_cipher_encrypt(&new_amount);
    new_balance.public_share.amount = new_public_share;

    // Compute a recovery ID and new balance commitment
    let recovery_id = new_balance.compute_recovery_id();
    let new_balance_commitment = new_balance.compute_commitment();

    let merkle_root = opening.compute_root();

    // Convert ABI Withdrawal to circuit Withdrawal
    let circuit_withdrawal = renegade_circuit_types::withdrawal::Withdrawal {
        to: withdrawal.to,
        token: withdrawal.token,
        amount: u256_to_u128(withdrawal.amount),
    };

    let statement = ValidWithdrawalStatement {
        withdrawal: circuit_withdrawal,
        merkle_root,
        old_balance_nullifier,
        new_balance_commitment,
        recovery_id,
        new_amount_share: new_public_share,
    };

    Ok((witness, statement))
}

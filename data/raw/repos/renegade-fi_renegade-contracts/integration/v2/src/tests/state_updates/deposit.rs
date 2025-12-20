//! Tests for depositing into an existing balance

use eyre::Result;
use renegade_abi::v2::{
    IDarkpoolV2::{Deposit, DepositProofBundle},
    relayer_types::u256_to_u128,
};
use renegade_circuit_types::balance::DarkpoolStateBalance;
use renegade_circuits::{
    singleprover_prove,
    test_helpers::check_constraints_satisfied,
    zk_circuits::valid_deposit::{
        SizedValidDeposit, SizedValidDepositWitness, ValidDepositStatement, ValidDepositWitness,
    },
};
use renegade_common::types::merkle::MerkleAuthenticationPath;
use renegade_crypto::fields::u256_to_scalar;
use test_helpers::{assert_eq_result, assert_true_result, integration_test_async};

use crate::{
    test_args::TestArgs,
    tests::state_updates::create_balance::create_balance,
    util::{
        deposit::{build_deposit_permit, fund_for_deposit},
        fuzzing::random_deposit,
        merkle::fetch_merkle_opening,
        transactions::wait_for_tx_success,
    },
};

/// Test depositing into an existing balance
async fn test_deposit(args: TestArgs) -> Result<()> {
    // First, create a balance in the darkpool from a deposit
    let deposit = random_deposit(&args)?;
    let addr = deposit.token;
    fund_for_deposit(addr, &args.party0_signer(), &deposit, &args).await?;
    let (_receipt, balance) = create_balance(&args.party0_signer(), &deposit, &args).await?;

    // Find the balance's Merkle opening
    let commitment = balance.compute_commitment();
    let merkle_path = fetch_merkle_opening(commitment, &args.darkpool).await?;

    // Build a second deposit for the wallet
    let second_deposit = random_deposit(&args)?;
    fund_for_deposit(addr, &args.party0_signer(), &second_deposit, &args).await?;

    let proof_bundle = create_proof_bundle(&second_deposit, &balance, &merkle_path)?;
    let commitment = u256_to_scalar(&proof_bundle.statement.newBalanceCommitment);
    let deposit_auth =
        build_deposit_permit(commitment, &second_deposit, &args.party0_signer(), &args).await?;

    // Send the deposit txn
    let party0_balance_before = args.base_balance(args.party0_addr()).await?;
    let darkpool_balance_before = args.base_balance(args.darkpool_addr()).await?;

    let call = args.darkpool.deposit(deposit_auth, proof_bundle.clone());
    wait_for_tx_success(call).await?;

    let party0_balance_after = args.base_balance(args.party0_addr()).await?;
    let darkpool_balance_after = args.base_balance(args.darkpool_addr()).await?;

    assert_eq_result!(
        party0_balance_after,
        party0_balance_before - second_deposit.amount
    )?;
    assert_eq_result!(
        darkpool_balance_after,
        darkpool_balance_before + second_deposit.amount
    )?;

    Ok(())
}
integration_test_async!(test_deposit);

// -----------
// | Helpers |
// -----------

// --- Circuits Helpers --- //

/// Create a proof of the deposit
pub fn create_proof_bundle(
    deposit: &Deposit,
    balance: &DarkpoolStateBalance,
    opening: &MerkleAuthenticationPath,
) -> Result<DepositProofBundle> {
    let (witness, statement) = build_witness_statement(deposit, balance, opening)?;
    let valid = check_constraints_satisfied::<SizedValidDeposit>(&witness, &statement);
    assert_true_result!(valid)?;

    let proof = singleprover_prove::<SizedValidDeposit>(&witness, &statement)?;
    let bundle = DepositProofBundle::new(statement, proof);
    Ok(bundle)
}

/// Build a witness statement for the deposit
fn build_witness_statement(
    deposit: &Deposit,
    balance: &DarkpoolStateBalance,
    opening: &MerkleAuthenticationPath,
) -> Result<(SizedValidDepositWitness, ValidDepositStatement)> {
    let witness = ValidDepositWitness {
        old_balance: balance.clone(),
        old_balance_opening: opening.clone().into(),
    };

    // Build the new balance and re-encrypt the amount field
    let old_balance_nullifier = balance.compute_nullifier();
    let mut new_balance = balance.clone();
    new_balance.inner.amount += u256_to_u128(deposit.amount);

    let new_amount = new_balance.inner.amount;
    let new_public_share = new_balance.stream_cipher_encrypt(&new_amount);
    new_balance.public_share.amount = new_public_share;

    // Compute a recovery ID and new balance commitment
    let recovery_id = new_balance.compute_recovery_id();
    let new_balance_commitment = new_balance.compute_commitment();

    let merkle_root = opening.compute_root();
    let statement = ValidDepositStatement {
        deposit: deposit.clone().into(),
        merkle_root,
        old_balance_nullifier,
        new_balance_commitment,
        recovery_id,
        new_amount_share: new_public_share,
    };

    Ok((witness, statement))
}

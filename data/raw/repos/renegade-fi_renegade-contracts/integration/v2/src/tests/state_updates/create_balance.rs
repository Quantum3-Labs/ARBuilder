//! Tests for creating a new balance and depositing into it

use alloy::{rpc::types::TransactionReceipt, signers::local::PrivateKeySigner};
use eyre::Result;
use renegade_abi::v2::{
    IDarkpoolV2::{Deposit, NewBalanceDepositProofBundle},
    relayer_types::u256_to_u128,
};
use renegade_circuit_types::{
    balance::{Balance, DarkpoolStateBalance},
    state_wrapper::StateWrapper,
};
use renegade_circuits::{
    singleprover_prove,
    test_helpers::{check_constraints_satisfied, random_csprng},
    zk_circuits::valid_balance_create::{
        ValidBalanceCreate, ValidBalanceCreateStatement, ValidBalanceCreateWitness,
    },
};
use renegade_crypto::fields::u256_to_scalar;
use test_helpers::{assert_eq_result, assert_true_result, integration_test_async};

use crate::{
    test_args::TestArgs,
    util::{
        deposit::{build_deposit_permit, fund_for_deposit},
        fuzzing::random_deposit,
        transactions::wait_for_tx_success,
    },
};

/// Test creating a balance in the darkpool
async fn test_create_balance(args: TestArgs) -> Result<()> {
    // First, fund the signer with some of the ERC20 to deposit
    let deposit = random_deposit(&args)?;
    let addr = deposit.token;
    fund_for_deposit(addr, &args.party0_signer(), &deposit, &args).await?;

    // Measure balances before and after the deposit
    let party0_addr = args.party0_addr();
    let darkpool_addr = args.darkpool_addr();
    let my_balance_before = args.base_balance(party0_addr).await?;
    let darkpool_balance_before = args.base_balance(darkpool_addr).await?;
    create_balance(&args.party0_signer(), &deposit, &args).await?;

    let my_balance_after = args.base_balance(party0_addr).await?;
    let darkpool_balance_after = args.base_balance(darkpool_addr).await?;

    assert_eq_result!(my_balance_after, my_balance_before - deposit.amount)?;
    assert_eq_result!(
        darkpool_balance_after,
        darkpool_balance_before + deposit.amount
    )?;
    Ok(())
}
integration_test_async!(test_create_balance);

/// Helper to create a balance in the darkpool from the given deposit
///
/// Assumes that the signer has already been funded with the deposit amount
/// and that the Permit2 contract has been approved to spend the tokens
pub async fn create_balance(
    signer: &PrivateKeySigner,
    deposit: &Deposit,
    args: &TestArgs,
) -> Result<(TransactionReceipt, DarkpoolStateBalance)> {
    // Build calldata for the balance creation
    let (witness, bundle) = create_proof_bundle(deposit, args)?;
    let commitment = u256_to_scalar(&bundle.statement.newBalanceCommitment);
    let deposit_auth = build_deposit_permit(commitment, deposit, signer, args).await?;

    // Send the txn
    let call = args
        .darkpool
        .depositNewBalance(deposit_auth, bundle.clone());
    let receipt = wait_for_tx_success(call).await?;

    // Build the post-txn balance
    let mut balance = DarkpoolStateBalance::new(
        witness.balance,
        witness.initial_share_stream.seed,
        witness.initial_recovery_stream.seed,
    );

    // Simulate the recovery ID computation that happens in the circuit
    balance.compute_recovery_id();
    Ok((receipt, balance))
}

// -----------
// | Helpers |
// -----------

// --- Circuits Helpers --- //

/// Create a proof of the balance creation
fn create_proof_bundle(
    deposit: &Deposit,
    args: &TestArgs,
) -> Result<(ValidBalanceCreateWitness, NewBalanceDepositProofBundle)> {
    let (witness, statement) = build_witness_statement(deposit, args)?;
    let valid = check_constraints_satisfied::<ValidBalanceCreate>(&witness, &statement);
    assert_true_result!(valid)?;

    let proof = singleprover_prove::<ValidBalanceCreate>(&witness, &statement)?;
    let bundle = NewBalanceDepositProofBundle::new(statement, proof);
    Ok((witness, bundle))
}

/// Build a witness and statement for the deposit
fn build_witness_statement(
    deposit: &Deposit,
    args: &TestArgs,
) -> Result<(ValidBalanceCreateWitness, ValidBalanceCreateStatement)> {
    // Build a state object
    let amount_u128 = u256_to_u128(deposit.amount);
    let balance = Balance::new(
        deposit.token,
        deposit.from,
        args.relayer_signer_addr(),
        deposit.from,
    )
    .with_amount(amount_u128);

    // Sample stream seeds
    let share_stream = random_csprng();
    let recovery_stream = random_csprng();

    // Encrypt the balance
    let mut initial_state =
        StateWrapper::new(balance.clone(), share_stream.seed, recovery_stream.seed);
    let balance_public_share = initial_state.public_share();
    let recovery_id = initial_state.compute_recovery_id();
    let balance_commitment = initial_state.compute_commitment();

    let witness = ValidBalanceCreateWitness {
        balance,
        initial_share_stream: share_stream,
        initial_recovery_stream: recovery_stream,
    };
    let statement = ValidBalanceCreateStatement {
        deposit: deposit.clone().into(),
        new_balance_share: balance_public_share,
        recovery_id,
        balance_commitment,
    };

    Ok((witness, statement))
}

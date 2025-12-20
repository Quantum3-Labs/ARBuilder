//! Tests for creating a wallet

use eyre::Result;
use renegade_circuits::{
    singleprover_prove,
    zk_circuits::valid_wallet_create::{
        SizedValidWalletCreate, SizedValidWalletCreateStatement, SizedValidWalletCreateWitness,
    },
};
use renegade_common::types::wallet::Wallet;
use renegade_constants::Scalar;
use test_helpers::{assert_true_result, integration_test_async};

use crate::{
    util::{
        merkle::{fetch_merkle_opening, update_wallet_opening},
        transactions::wait_for_tx_success,
    },
    TestArgs,
};

// ---------
// | Tests |
// ---------

/// Tests recovering a wallet from a `createWallet` transaction
#[allow(non_snake_case)]
async fn test_create_wallet__recover_wallet(args: TestArgs) -> Result<()> {
    // Create a wallet in the darkpool
    let darkpool = &args.darkpool;
    let wallet = create_darkpool_wallet(&args).await?;

    // Find the merkle opening for the wallet
    let comm = wallet.get_wallet_share_commitment();
    let opening = fetch_merkle_opening(comm, darkpool).await?;

    // Validate the opening
    let root = opening.compute_root();
    let valid_root = args.check_root(root).await?;
    assert_true_result!(valid_root)
}
integration_test_async!(test_create_wallet__recover_wallet);

// -----------
// | Helpers |
// -----------

/// Create a wallet in the darkpool and return the circuit representation
pub async fn create_darkpool_wallet(args: &TestArgs) -> Result<Wallet> {
    let darkpool = args.darkpool.clone();
    let (blinder_seed, mut wallet) = args.build_empty_renegade_wallet()?;

    let (witness, statement) = create_sized_witness_statement_with_wallet(blinder_seed, &wallet);
    let proof = singleprover_prove::<SizedValidWalletCreate>(witness.clone(), statement.clone())?;

    let contract_statement = statement.clone().into();
    let contract_proof = proof.into();
    let tx = darkpool.createWallet(contract_statement, contract_proof);

    // Wait for the transaction receipt and ensure it was successful
    wait_for_tx_success(tx).await?;
    update_wallet_opening(&mut wallet, &darkpool).await?;

    Ok(wallet)
}

/// Create a `VALID WALLET CREATE` statement and witness, using the given keychain
pub fn create_sized_witness_statement_with_wallet(
    blinder_seed: Scalar,
    wallet: &Wallet,
) -> (
    SizedValidWalletCreateWitness,
    SizedValidWalletCreateStatement,
) {
    let wallet_share_commitment = wallet.get_wallet_share_commitment();

    (
        SizedValidWalletCreateWitness {
            private_wallet_share: wallet.private_shares.clone(),
            blinder_seed,
        },
        SizedValidWalletCreateStatement {
            wallet_share_commitment,
            public_wallet_shares: wallet.blinded_public_shares.clone(),
        },
    )
}

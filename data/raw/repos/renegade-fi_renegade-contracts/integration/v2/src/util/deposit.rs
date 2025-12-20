//! Utilities for building deposit-related data structures

use alloy::{primitives::Address, signers::local::PrivateKeySigner};
use eyre::Result;
use renegade_abi::v2::{
    transfer_auth::deposit::create_deposit_permit,
    IDarkpoolV2::{Deposit, DepositAuth},
};
use renegade_constants::Scalar;
use renegade_crypto::fields::scalar_to_u256;

use crate::{test_args::TestArgs, util::transactions::wait_for_tx_success};

/// Fund the signer with some of the ERC20 deposit and approve the Permit2 contract to spend the tokens
pub async fn fund_for_deposit(
    address: Address,
    signer: &PrivateKeySigner,
    deposit: &Deposit,
    args: &TestArgs,
) -> Result<()> {
    // Fund the signer
    let erc20 = args.erc20_from_addr_with_signer(address, signer.clone())?;
    let mint_tx = erc20.mint(signer.address(), deposit.amount);
    wait_for_tx_success(mint_tx).await?;

    // Approve Permit2 (must be called from the signer's address)
    let permit2_addr = args.permit2_addr()?;
    let approve_tx = erc20.approve(permit2_addr, deposit.amount);
    wait_for_tx_success(approve_tx).await?;
    Ok(())
}

/// Build a permit2 signature for the deposit
pub async fn build_deposit_permit(
    new_balance_commitment: Scalar,
    deposit: &Deposit,
    signer: &PrivateKeySigner,
    args: &TestArgs,
) -> Result<DepositAuth> {
    // Compute a dummy note commitment for the deposit (random note for testing)
    // In real tests, you may want to compute an actual note, but for now, random is sufficient.
    let commitment = scalar_to_u256(&new_balance_commitment);

    let chain_id = args.chain_id().await?;
    let darkpool = args.darkpool_addr();
    let permit2 = args.permit2_addr()?;

    // Call create_deposit_permit with all required parameters
    let (witness, signature) = create_deposit_permit(
        commitment,
        deposit.clone(),
        chain_id,
        darkpool,
        permit2,
        signer,
    )?;

    let sig_bytes = signature.as_bytes().to_vec();
    Ok(DepositAuth {
        permit2Nonce: witness.nonce,
        permit2Deadline: witness.deadline,
        permit2Signature: sig_bytes.into(),
    })
}

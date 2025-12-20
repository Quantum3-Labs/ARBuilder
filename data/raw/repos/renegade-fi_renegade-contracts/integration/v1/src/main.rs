//! Integration tests for the Renegade solidity contracts

#![deny(missing_docs)]
#![deny(clippy::missing_docs_in_private_items)]
#![deny(unsafe_code)]
#![deny(clippy::needless_pass_by_value)]
#![deny(clippy::needless_pass_by_ref_mut)]
#![allow(incomplete_features)]
#![feature(generic_const_exprs)]

mod contracts;
mod tests;
mod util;

use std::path::PathBuf;
use std::str::FromStr;

use crate::util::deployments::read_deployment;
use abi::v1::relayer_types::scalar_to_u256;
use abi::v1::IDarkpool::IDarkpoolInstance;
use alloy::network::Ethereum;
use alloy::primitives::{Address, U256};
use alloy::providers::{DynProvider, Provider, ProviderBuilder};
use alloy::signers::local::PrivateKeySigner;
use alloy::transports::http::reqwest::Url;
use clap::Parser;
use contracts::erc20::ERC20Mock;
use contracts::erc20::ERC20MockInstance;
use eyre::{eyre, Result};
use renegade_circuit_types::Amount;
use renegade_common::types::wallet::{
    derivation::{
        derive_blinder_seed, derive_share_seed, derive_wallet_id, derive_wallet_keychain,
    },
    Wallet as RenegadeWallet,
};
use renegade_constants::Scalar;
use test_helpers::{integration_test_main, types::TestVerbosity};
use util::transactions::{call_helper, send_tx};

/// The default private key for the tests, the first default account in an Anvil node
const DEFAULT_PKEY: &str = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";

/// The provider type for the tests
pub type Wallet = DynProvider<Ethereum>;
/// A darkpool instance using the default generics
pub type Darkpool = IDarkpoolInstance<Wallet, Ethereum>;
/// An ERC20 instance with default generics
pub type ERC20 = ERC20MockInstance<Wallet, Ethereum>;

/// The CLI arguments for the integration tests
#[derive(Debug, Clone, Parser)]
struct CliArgs {
    /// The path to the deployments.json file
    #[clap(long, default_value = "../deployments.devnet.json")]
    deployments: PathBuf,
    /// The private key to use for testing
    #[clap(short = 'p', long, default_value = DEFAULT_PKEY)]
    pkey: String,
    /// The RPC url to run the tests against
    #[clap(short = 'r', long, default_value = "http://127.0.0.1:8545")]
    rpc_url: String,

    // --- Test Harness Args --- //
    /// The test to run
    #[arg(short, long, value_parser)]
    test: Option<String>,
    /// The verbosity of the test
    #[clap(short = 'v', long, default_value = "default")]
    verbosity: TestVerbosity,
}

/// The arguments for the integration tests
#[derive(Clone)]
struct TestArgs {
    /// The deployments path
    deployments: String,
    /// The private key used for testing
    pkey: PrivateKeySigner,
    /// The darkpool contract instance
    darkpool: Darkpool,
}

impl TestArgs {
    /// Get the chain ID of the test
    async fn chain_id(&self) -> Result<u64> {
        let provider = self.darkpool.provider().clone();
        let chain_id = provider.get_chain_id().await?;
        Ok(chain_id)
    }

    /// Get the signer for the wallet
    fn signer(&self) -> PrivateKeySigner {
        self.pkey.clone()
    }

    /// Get the address of the wallet
    fn wallet_addr(&self) -> Address {
        self.pkey.address()
    }

    /// Read the address for the quote token
    fn quote_token(&self) -> Result<ERC20> {
        let addr = read_deployment("QuoteToken", &self.deployments)?;
        self.erc20_from_addr(addr)
    }

    /// Read the address for the base token
    fn base_token(&self) -> Result<ERC20> {
        let addr = read_deployment("BaseToken", &self.deployments)?;
        self.erc20_from_addr(addr)
    }

    /// Get the address of the permit2 contract
    fn permit2_addr(&self) -> Result<Address> {
        read_deployment("Permit2", &self.deployments)
    }

    /// Get the address of the darkpool contract
    fn darkpool_addr(&self) -> Address {
        *self.darkpool.address()
    }

    /// Read an ERC20 from an address
    fn erc20_from_addr(&self, addr: Address) -> Result<ERC20> {
        let provider = self.darkpool.provider().clone();
        let erc20 = ERC20Mock::new(addr, provider);
        Ok(erc20)
    }

    /// Fund the test wallet with the given erc20
    async fn fund_address(
        &self,
        who: Address,
        mint: Address,
        amt: Amount,
    ) -> Result<(), eyre::Error> {
        let erc20 = self.erc20_from_addr(mint)?;
        let mint_tx = erc20.mint(who, U256::from(amt));
        send_tx(mint_tx).await?;

        Ok(())
    }

    /// Check whether a given root is a valid historical root
    pub async fn check_root(&self, root: Scalar) -> Result<bool> {
        let root_u256 = scalar_to_u256(root);
        let call = self.darkpool.rootInHistory(root_u256);
        let res = call_helper(call).await?;
        Ok(res)
    }

    /// Derive a keychain for the wallet
    ///
    /// Returns the blinder seed and the wallet
    fn build_empty_renegade_wallet(&self) -> Result<(Scalar, RenegadeWallet)> {
        let wallet = PrivateKeySigner::random();
        let wallet_id = derive_wallet_id(&wallet).map_err(|e| eyre!(e))?;
        let blinder_seed = derive_blinder_seed(&wallet).map_err(|e| eyre!(e))?;
        let share_seed = derive_share_seed(&wallet).map_err(|e| eyre!(e))?;
        let keychain = derive_wallet_keychain(&wallet, 1).map_err(|e| eyre!(e))?;
        let wallet =
            RenegadeWallet::new_empty_wallet(wallet_id, blinder_seed, share_seed, keychain);

        Ok((blinder_seed, wallet))
    }
}

// --- Setup --- //

impl From<CliArgs> for TestArgs {
    fn from(args: CliArgs) -> Self {
        let signer = PrivateKeySigner::from_str(&args.pkey).expect("Failed to parse private key");
        let wallet = setup_wallet(&args.rpc_url, signer.clone()).expect("Failed to setup wallet");

        // Read darkpool address from deployments file
        let deployments_path = args.deployments.to_str().unwrap().to_string();
        let darkpool_addr = read_deployment("DarkpoolProxy", &deployments_path)
            .expect("Failed to read darkpool address from deployments file");
        let darkpool = IDarkpoolInstance::new(darkpool_addr, wallet.clone());

        Self {
            deployments: deployments_path,
            pkey: signer,
            darkpool,
        }
    }
}

/// Setup a provider for tests
fn setup_wallet(rpc_url: &str, pkey: PrivateKeySigner) -> Result<Wallet, eyre::Error> {
    let url = Url::parse(rpc_url)?;
    let provider = ProviderBuilder::new().wallet(pkey).connect_http(url);
    Ok(DynProvider::new(provider))
}

integration_test_main!(CliArgs, TestArgs);

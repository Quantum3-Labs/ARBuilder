//! Defines arguments passed to each test

use std::{path::PathBuf, str::FromStr};

use alloy::{
    primitives::{Address, U160, U256, aliases::U48},
    providers::{DynProvider, Provider, ProviderBuilder},
    signers::local::PrivateKeySigner,
    transports::http::reqwest::Url,
};
use eyre::Result;
use renegade_circuit_types::{elgamal::EncryptionKey, fixed_point::FixedPoint};

use crate::{
    CliArgs,
    util::{
        abis::{IPermit2Instance, Permit2},
        darkpool::{Darkpool, create_darkpool_client},
        deployments::{DARKPOOL_PROXY_DEPLOYMENT_KEY, read_deployment},
        erc20::{ERC20, ERC20Mock},
        transactions::wait_for_tx_success,
    },
};

/// The CLI arguments for the integration tests
#[derive(Debug, Clone)]
pub(crate) struct TestArgs {
    /// The path to the deployments.json file
    pub deployments: PathBuf,
    /// A darkpool instance to use for testing
    pub darkpool: Darkpool,
    /// The signer for the first party
    pub party0_signer: PrivateKeySigner,
    /// The signer for the second party
    pub party1_signer: PrivateKeySigner,
    /// The tx submitter for the tests
    pub tx_submitter: PrivateKeySigner,
    /// The relayer's signer which is used to authorize fee payments
    pub relayer_signer: PrivateKeySigner,
    /// The RPC URL for the test network
    pub rpc_url: String,
}

impl TestArgs {
    /// Get the chain ID of the test
    pub async fn chain_id(&self) -> Result<u64> {
        let provider = self.darkpool.provider().clone();
        let chain_id = provider.get_chain_id().await?;
        Ok(chain_id)
    }

    /// Get an RPC provider for the test
    pub fn rpc_provider(&self) -> DynProvider {
        self.darkpool.provider().clone()
    }

    /// Get the signer for the wallet
    pub fn party0_signer(&self) -> PrivateKeySigner {
        self.party0_signer.clone()
    }

    /// Get the signer for the second party
    pub fn party1_signer(&self) -> PrivateKeySigner {
        self.party1_signer.clone()
    }

    // --- Darkpool Interaction --- //

    /// Get the protocol fee for the trading pair in the tests
    pub async fn protocol_fee(&self) -> Result<FixedPoint> {
        let base = self.base_addr()?;
        let quote = self.quote_addr()?;
        let fee = self.darkpool.getProtocolFee(base, quote).call().await?;
        Ok(fee.into())
    }

    /// Get the recipient of the public protocol fee
    pub async fn protocol_fee_recipient(&self) -> Result<Address> {
        let recipient = self.darkpool.getProtocolFeeRecipient().call().await?;
        Ok(recipient)
    }

    /// Get the encryption key for protocol fee notes
    pub async fn protocol_fee_encryption_key(&self) -> Result<EncryptionKey> {
        let key = self.darkpool.getProtocolFeeKey().call().await?;
        Ok(key.into())
    }

    // --- Addresses and Contracts --- //

    /// Get the address of the wallet
    pub fn party0_addr(&self) -> Address {
        self.party0_signer.address()
    }

    /// Get the address of the second party
    pub fn party1_addr(&self) -> Address {
        self.party1_signer.address()
    }

    /// Get the address of the base token
    pub fn base_addr(&self) -> Result<Address> {
        read_deployment("BaseToken", &self.deployments)
    }

    /// Read the ERC20 for the base token
    pub fn base_token(&self) -> Result<ERC20> {
        let addr = self.base_addr()?;
        self.erc20_from_addr(addr)
    }

    /// Read the ERC20 for the base token with a specific signer    
    pub fn base_token_with_signer(&self, signer: &PrivateKeySigner) -> Result<ERC20> {
        let addr = self.base_addr()?;
        self.erc20_from_addr_with_signer(addr, signer.clone())
    }

    /// Get the address of the quote token
    pub fn quote_addr(&self) -> Result<Address> {
        read_deployment("QuoteToken", &self.deployments)
    }

    /// Read the ERC20 for the quote token
    pub fn quote_token(&self) -> Result<ERC20> {
        let addr = self.quote_addr()?;
        self.erc20_from_addr(addr)
    }

    /// Read the ERC20 for the quote token with a specific signer
    pub fn quote_token_with_signer(&self, signer: &PrivateKeySigner) -> Result<ERC20> {
        let addr = self.quote_addr()?;
        self.erc20_from_addr_with_signer(addr, signer.clone())
    }

    /// Create an ERC20 instance from an address
    pub fn erc20_from_addr(&self, addr: Address) -> Result<ERC20> {
        let provider = self.darkpool.provider().clone();
        let erc20 = ERC20Mock::new(addr, provider);
        Ok(erc20)
    }

    /// Create an ERC20 instance from an address with a specific signer
    pub fn erc20_from_addr_with_signer(
        &self,
        addr: Address,
        signer: PrivateKeySigner,
    ) -> Result<ERC20> {
        let provider = self.create_provider_with_signer(&signer)?;
        let erc20 = ERC20Mock::new(addr, provider);
        Ok(erc20)
    }

    /// Get the address of the permit2 contract
    pub fn permit2_addr(&self) -> Result<Address> {
        read_deployment("Permit2", &self.deployments)
    }

    /// Get an instance of the permit2 contract
    pub fn permit2_with_signer(&self, signer: &PrivateKeySigner) -> Result<Permit2> {
        let addr = self.permit2_addr()?;
        let provider = self.create_provider_with_signer(signer)?;
        let permit2 = IPermit2Instance::new(addr, provider);
        Ok(permit2)
    }

    /// Get the address of the darkpool contract
    pub fn darkpool_addr(&self) -> Address {
        *self.darkpool.address()
    }

    /// Get the address of the relayer's signer
    pub fn relayer_signer_addr(&self) -> Address {
        self.relayer_signer.address()
    }

    // --- Balances --- //

    /// Get the balance of the given address for the given token
    pub async fn balance(&self, addr: Address, token: Address) -> Result<U256> {
        let erc20 = self.erc20_from_addr(token)?;
        let balance = erc20.balanceOf(addr).call().await?;
        Ok(balance)
    }

    /// Get the base balance of the given address
    pub async fn base_balance(&self, addr: Address) -> Result<U256> {
        let erc20 = self.base_token()?;
        let balance = erc20.balanceOf(addr).call().await?;
        Ok(balance)
    }

    /// Get the quote balance of the given address
    pub async fn quote_balance(&self, addr: Address) -> Result<U256> {
        let erc20 = self.quote_token()?;
        let balance = erc20.balanceOf(addr).call().await?;
        Ok(balance)
    }

    /// Get the base and quote balances for a given address
    pub async fn base_and_quote_balances(&self, addr: Address) -> Result<(U256, U256)> {
        let base = self.base_balance(addr).await?;
        let quote = self.quote_balance(addr).await?;
        Ok((base, quote))
    }

    // --- Approvals --- //

    /// Approve the darkpool to spend the given token through permit2
    pub async fn permit2_approve_darkpool(
        &self,
        token: Address,
        signer: &PrivateKeySigner,
    ) -> Result<()> {
        let amt = U160::MAX;
        let permit2 = self.permit2_with_signer(signer)?;
        let darkpool = self.darkpool_addr();
        let expiration = U48::MAX;

        let approve_tx = permit2.approve(token, darkpool, amt, expiration);
        wait_for_tx_success(approve_tx).await?;
        Ok(())
    }

    fn create_provider_with_signer(&self, signer: &PrivateKeySigner) -> Result<DynProvider> {
        let url = Url::parse(&self.rpc_url)?;
        let provider = ProviderBuilder::new()
            .wallet(signer.clone())
            .with_simple_nonce_management()
            .connect_http(url);
        Ok(DynProvider::new(provider))
    }
}

impl From<CliArgs> for TestArgs {
    fn from(cli_args: CliArgs) -> Self {
        let darkpool_addr = read_deployment(DARKPOOL_PROXY_DEPLOYMENT_KEY, &cli_args.deployments)
            .expect("failed to read darkpool address from deployments file");
        let tx_submitter = PrivateKeySigner::from_str(&cli_args.pkey).unwrap();
        let darkpool =
            create_darkpool_client(darkpool_addr, tx_submitter.clone(), &cli_args.rpc_url)
                .expect("failed to create darkpool instance");
        let relayer_signer = PrivateKeySigner::random();

        // Sample a second private key for the second party
        let party0_signer = PrivateKeySigner::random();
        let party1_signer = PrivateKeySigner::random();

        Self {
            deployments: cli_args.deployments,
            darkpool,
            party0_signer,
            party1_signer,
            tx_submitter,
            relayer_signer,
            rpc_url: cli_args.rpc_url,
        }
    }
}

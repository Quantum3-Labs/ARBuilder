//! Utilities for the Darkpool contract

use alloy::{
    network::Ethereum,
    primitives::Address,
    providers::{DynProvider, ProviderBuilder},
    signers::local::PrivateKeySigner,
    transports::http::reqwest::Url,
};
use eyre::Result;
use renegade_abi::v2::IDarkpoolV2::IDarkpoolV2Instance;

/// The provider type for the tests
pub type Wallet = DynProvider<Ethereum>;
/// A darkpool instance using the default generics
pub type Darkpool = IDarkpoolV2Instance<Wallet, Ethereum>;

/// Create a new darkpool instance
pub fn create_darkpool_client(
    darkpool_address: Address,
    signer: PrivateKeySigner,
    rpc_url: &str,
) -> Result<Darkpool> {
    let url = Url::parse(rpc_url)?;
    let provider = ProviderBuilder::new()
        .wallet(signer.clone())
        .with_simple_nonce_management()
        .connect_http(url);
    let dyn_provider = DynProvider::new(provider);

    Ok(IDarkpoolV2Instance::new(darkpool_address, dyn_provider))
}

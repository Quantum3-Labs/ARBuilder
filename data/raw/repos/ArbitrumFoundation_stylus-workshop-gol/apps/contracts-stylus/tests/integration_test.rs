mod abi;
mod common;

use abi::Erc721;
use alloy::{
    network::EthereumWallet, primitives::U256, providers::ProviderBuilder,
    signers::local::PrivateKeySigner,
};

#[tokio::test]
async fn test_mint() {
    let private_key = "0xb6b15c8cb491557369f3c7d2c287b053eb229daa9c22138887752191c9520659";
    let endpoint = "http://localhost:8547";

    let signer: PrivateKeySigner = private_key.parse().expect("should parse private key");
    let addr = signer.address();
    let wallet = EthereumWallet::from(signer);

    let provider = ProviderBuilder::new()
        .with_recommended_fillers()
        .wallet(wallet)
        .on_http(endpoint.parse().unwrap());

    let deployed_contract_address = common::setup(private_key, endpoint)
        .await
        .expect("Failed to get contract address");

    let contract = Erc721::new(deployed_contract_address, provider.clone());

    let name_ret = contract.name().call().await;

    assert_eq!(name_ret.unwrap().name, "Game of Life");

    let token_id = U256::from(524);

    let tx = contract
        .mint(addr, token_id)
        .send()
        .await
        .expect("failed to send tx")
        .watch()
        .await
        .expect("failed to submit tx");

    println!("submitted tx hash {:?}", tx);

    let new_owner = contract.ownerOf(token_id).call().await;
    assert_eq!(new_owner.unwrap().ownerOf, addr);
}

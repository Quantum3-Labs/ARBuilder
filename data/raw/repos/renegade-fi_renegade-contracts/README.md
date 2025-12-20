<div align="center">
  <img
    alt="Renegade Logo"
    width="60%"
    src="./img/logo_light_contract.svg#gh-light-mode-only"
  />
  <img
    alt="Renegade Logo"
    width="60%"
    src="./img/logo_dark_contract.svg#gh-dark-mode-only"
  />
</div>

---

<div>
  <a href="https://twitter.com/renegade_fi" target="_blank">
    <img src="https://img.shields.io/twitter/follow/renegade_fi?style=social" />
  </a>
  <a href="https://discord.gg/renegade-fi" target="_blank">
    <img src="https://img.shields.io/discord/1032770899675463771?label=Join%20Discord&logo=discord&style=social" />
  </a>
</div>

This repository contains the solidity code for Renegade's settlement contracts. The contracts encapsulate the Merklized exchange state, PlonK verifier, and settlement logic which together compose the Renegade darkpool.

Please refer to our [whitepaper](https://www.renegade.fi/whitepaper.pdf) and [docs](https://docs.renegade.fi/) for an introduction the Renegade protocol as a whole.

## Contract Development Setup

### Setup Foundry

``` shell
curl -L https://foundry.paradigm.xyz | bash
```

### Install `huffc`

```shell
curl -L get.huff.sh | bash
```

### Install Cargo
The integration tests are written in rust, and the unit test use rust reference implementations:
``` shell
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### Clone the repo
``` shell
git clone --recurse-submodules https://github.com/renegade-fi/renegade-solidity-contracts
```

## Running unit tests

``` shell
forge test --ffi -vv
```

## Running integration tests

Assuming you have installed foundry and cargo, you can run the integration tests directly with:
```shell
./scripts/run-integration-tests.sh --release
```
This will:
1. Start an `anvil` node
2. Deploy the Renegade contracts to the node
3. Run the integration tests against the node. These tests simulate a rust-based client interacting with the darkpool.

## Development Tools

The repository includes several helpful tools for development and deployment.

### Deploying Contracts

To deploy Renegade contracts to an EVM chain:

```shell
./script/bin/deploy.sh --rpc-url <RPC_URL> --pkey <PRIVATE_KEY>
```

This will prompt for any missing configuration values like fee rates and contract addresses.

### Deploying Test Tokens

For testing purposes, you can deploy dummy ERC20 tokens or a WETH mock:

```shell
# Deploy a regular ERC20 token (will prompt for name, symbol, and decimals)
./script/bin/deploy-token.sh --rpc-url <RPC_URL> --pkey <PRIVATE_KEY>

# Deploy a WETH mock
./script/bin/deploy-token.sh --rpc-url <RPC_URL> --pkey <PRIVATE_KEY> --weth
```

You can also specify token details directly:

```shell
# Deploy with all parameters specified
./script/bin/deploy-token.sh --rpc-url <RPC_URL> --pkey <PRIVATE_KEY> --name "My Token" --symbol "TKN" --decimals 18
```


# Renegade Contract Deployment Tool

This is a CLI tool for deploying Renegade contracts to an EVM network.

## Prerequisites

- Rust toolchain
- Foundry (forge)

## Building

From the `tools/deploy` directory, run:

```bash
cargo build
```

## Usage

You can use the tool directly:

```bash
cargo run -- --help
```

## Available Commands

- `deploy-darkpool` - Deploy the Darkpool contracts
- `deploy-gas-sponsor` - Deploy the GasSponsor contract
- `deploy-darkpool-implementation` - Deploy only the Darkpool implementation (for upgrades)
- `deploy-gas-sponsor-implementation` - Deploy only the GasSponsor implementation (for upgrades)
- `deploy-malleable-match-connector` - Deploy the MalleableMatchConnector contract
- `deploy-malleable-match-connector-implementation` - Deploy only the MalleableMatchConnector implementation (for upgrades)

### Example Commands

#### Deploy Darkpool

```bash
cargo run -- deploy-darkpool \
  --rpc-url https://eth-mainnet.alchemyapi.io/v2/YOUR_API_KEY \
  --owner 0xYourOwnerAddress \
  --permit2 0x000000000022D473030F116dDEE9F6B43aC78BA3 \
  --weth 0x4200000000000000000000000000000000000006 \
  --fee-recipient 0xYourFeeRecipientAddress \
  --protocol-fee-rate 0.02 \
  --pkey YOUR_PRIVATE_KEY
```

#### Deploy GasSponsor

```bash
cargo run -- deploy-gas-sponsor \
  --rpc-url https://eth-mainnet.alchemyapi.io/v2/YOUR_API_KEY \
  --owner 0xYourOwnerAddress \
  --darkpool 0xYourDarkpoolAddress \
  --auth-address 0xYourAuthAddress \
  --pkey YOUR_PRIVATE_KEY
```

#### Deploy MalleableMatchConnector

```bash
cargo run -- deploy-malleable-match-connector \
  --rpc-url https://eth-mainnet.alchemyapi.io/v2/YOUR_API_KEY \
  --admin 0xYourAdminAddress \
  --gas-sponsor 0xYourGasSponsorAddress \
  --pkey YOUR_PRIVATE_KEY
```

#### Deploy MalleableMatchConnector Implementation (for upgrades)

```bash
cargo run -- deploy-malleable-match-connector-implementation \
  --rpc-url https://eth-mainnet.alchemyapi.io/v2/YOUR_API_KEY \
  --pkey YOUR_PRIVATE_KEY
```

## Environment Variables

You can use environment variables instead of some command-line arguments:

```bash
# Set RPC URL
export RPC_URL=https://eth-mainnet.alchemyapi.io/v2/YOUR_API_KEY

# Set private key
export PKEY=your_private_key_here

# Run with environment variables
cargo run -- \
  --permit2 0x000000000022D473030F116dDEE9F6B43aC78BA3 \
  --weth 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 \
  --fee-recipient 0xYourFeeRecipientAddress \
  --protocol-fee-rate 0.02
```

## Common Options

All commands support these options:

- `-r, --rpc-url` - RPC URL to deploy to (default: http://localhost:8545), can be set with RPC_URL env var
- `--pkey` - Private key for signing transactions, can be set with PKEY env var
- `--verbosity` - Verbosity level (v, vv, vvv) (default: v)

## Command-Specific Options

### deploy-darkpool

- `--owner` - Owner address for the contracts
- `--permit2` - Permit2 contract address
- `--weth` - WETH contract address
- `--protocol-fee-rate` - Protocol fee rate (between 0.0 and 1.0)
- `--fee-recipient` - Protocol fee recipient address
- `--fee-dec-key` - Optional fee decryption key as hex string

### deploy-gas-sponsor

- `--owner` - Owner address (also used as proxy admin)
- `--darkpool` - Darkpool contract address
- `--auth-address` - Auth address for gas sponsorship (will be generated if not provided)

### deploy-malleable-match-connector

- `--admin` - Admin address (serves as proxy admin)
- `--gas-sponsor` - Gas sponsor contract address 
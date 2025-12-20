# 0xCatchup contracts

The repo contains the smart contracts in Solidity

This backend is based on PaulRBerg [Forge Template](https://github.com/PaulRBerg/foundry-template).

## Requirements
- Rust [installation instructions](https://www.rust-lang.org/tools/install)
- Forge [installation instructions](https://getfoundry.sh/)

## Scripts

### `pnpm test`

Runs the test via forge

### `pnpm test:coverage`

Runs the test via forge and return the coverage

### `pnpm anvil`

Run a local instance of Anvil. Run on http://127.0.0.1:8545 ChainID `1337`

### `pnpm deploy:local`

Deploy the contract in the local Anvil environment. Useful for testing the integration with the frontend

### `pnpm build`

Compile the .sol files


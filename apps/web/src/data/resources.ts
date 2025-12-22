/**
 * Static resources for Stylus development.
 * Ported from Python MCP resources.
 */

export const NETWORK_CONFIGS = {
  lastUpdated: "2025-12",
  networks: {
    arbitrum_sepolia: {
      name: "Arbitrum Sepolia",
      type: "testnet" as const,
      chainId: 421614,
      parentChain: "Ethereum Sepolia",
      rpcEndpoints: {
        primary: "https://sepolia-rollup.arbitrum.io/rpc",
        sequencer: "https://sepolia-rollup-sequencer.arbitrum.io/rpc",
      },
      explorer: {
        url: "https://sepolia.arbiscan.io",
        api: "https://api-sepolia.arbiscan.io/api",
      },
      faucets: [
        { name: "QuickNode", url: "https://faucet.quicknode.com/arbitrum/sepolia" },
        { name: "Chainlink", url: "https://faucets.chain.link/arbitrum-sepolia" },
      ],
      nativeCurrency: { name: "Ethereum", symbol: "ETH", decimals: 18 },
      stylusSupport: true,
      recommendedFor: ["development", "testing", "staging"],
    },
    arbitrum_one: {
      name: "Arbitrum One",
      type: "mainnet" as const,
      chainId: 42161,
      parentChain: "Ethereum Mainnet",
      rpcEndpoints: {
        primary: "https://arb1.arbitrum.io/rpc",
        sequencer: "https://arb1-sequencer.arbitrum.io/rpc",
      },
      explorer: {
        url: "https://arbiscan.io",
        api: "https://api.arbiscan.io/api",
      },
      nativeCurrency: { name: "Ethereum", symbol: "ETH", decimals: 18 },
      stylusSupport: true,
      recommendedFor: ["production"],
      warnings: [
        "MAINNET - Real funds at risk",
        "Thoroughly test on Sepolia before deploying",
      ],
    },
    arbitrum_nova: {
      name: "Arbitrum Nova",
      type: "mainnet" as const,
      chainId: 42170,
      parentChain: "Ethereum Mainnet",
      rpcEndpoints: {
        primary: "https://nova.arbitrum.io/rpc",
      },
      explorer: {
        url: "https://nova.arbiscan.io",
      },
      nativeCurrency: { name: "Ethereum", symbol: "ETH", decimals: 18 },
      dataAvailability: "AnyTrust (DAC)",
      stylusSupport: true,
      recommendedFor: ["gaming", "social", "high-volume-low-value"],
    },
  },
};

export const STYLUS_CLI = {
  tool: "cargo-stylus",
  version: "0.5.x+",
  lastUpdated: "2025-12",
  installation: {
    command: "cargo install --force cargo-stylus",
    prerequisites: [
      "Rust toolchain v1.81 (v1.82+ may have issues)",
      "WASM target: rustup target add wasm32-unknown-unknown",
      "Docker (for reproducible builds)",
    ],
  },
  commands: {
    new: {
      description: "Create a new Stylus project from template",
      usage: "cargo stylus new <NAME>",
      options: {
        "--minimal": "Create minimal project without examples",
      },
    },
    check: {
      description: "Validate contract is compatible with Stylus VM",
      usage: "cargo stylus check",
      options: {
        "--endpoint <URL>": "RPC endpoint to validate against",
      },
    },
    deploy: {
      description: "Deploy a Stylus contract to Arbitrum",
      usage: "cargo stylus deploy --private-key-path=./key.txt --endpoint=<RPC>",
      options: {
        "--estimate-gas": "Estimate gas without deploying",
        "--no-verify": "Skip Docker-based reproducible builds",
      },
    },
    "export-abi": {
      description: "Export Solidity ABI for the contract",
      usage: "cargo stylus export-abi",
    },
    verify: {
      description: "Verify deployed contract source code",
      usage: "cargo stylus verify --deployment-tx <TX_HASH>",
    },
    trace: {
      description: "Trace a transaction for debugging",
      usage: "cargo stylus trace --tx <HASH> --endpoint <URL>",
    },
  },
  troubleshooting: {
    wasm_too_large: {
      symptoms: ["Contract exceeds size limit"],
      solutions: [
        "Enable release profile optimizations",
        "Use opt-level = 's' or 'z'",
        "Enable LTO (link-time optimization)",
        "Set codegen-units = 1",
      ],
    },
    activation_failed: {
      symptoms: ["Deployment succeeds but activation fails"],
      solutions: [
        "Check for unsupported WASM features",
        "Verify contract doesn't use floating point",
      ],
    },
  },
};

export const BUILD_WORKFLOW = {
  name: "Build Stylus Contract",
  description: "Complete workflow for building a Stylus smart contract",
  prerequisites: [
    { check: "rustup --version", install: "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh" },
    { check: "rustup default", install: "rustup default 1.81", note: "Rust 1.81 recommended" },
    { check: "cargo stylus --version", install: "cargo install --force cargo-stylus" },
  ],
  steps: [
    {
      step: 1,
      name: "Verify Project Structure",
      description: "Ensure project has correct Cargo.toml configuration",
      checkFiles: ["Cargo.toml", "src/lib.rs"],
    },
    {
      step: 2,
      name: "Build for WASM",
      command: "cargo build --release --target wasm32-unknown-unknown",
      description: "Compile the contract to WebAssembly",
    },
    {
      step: 3,
      name: "Validate with cargo stylus check",
      command: "cargo stylus check",
      description: "Verify the WASM is compatible with Stylus VM",
    },
    {
      step: 4,
      name: "Export ABI (optional)",
      command: "cargo stylus export-abi",
      description: "Generate Solidity-compatible ABI",
    },
  ],
  sampleCargoToml: `[package]
name = "my-stylus-contract"
version = "0.1.0"
edition = "2021"

[dependencies]
stylus-sdk = "0.8.4"
alloy-primitives = "0.8.14"
alloy-sol-types = "0.8.14"

[features]
export-abi = ["stylus-sdk/export-abi"]

[lib]
crate-type = ["cdylib"]

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"`,
};

export const DEPLOY_WORKFLOW = {
  name: "Deploy Stylus Contract",
  description: "Complete workflow for deploying a Stylus contract to Arbitrum",
  prerequisites: [
    "Contract passes cargo stylus check",
    "Wallet with ETH on target network",
    "Private key file (chmod 600)",
  ],
  steps: [
    {
      step: 1,
      name: "Prepare Private Key",
      description: "Securely prepare your deployment key",
      command: "echo 'YOUR_PRIVATE_KEY' > key.txt && chmod 600 key.txt",
      security: ["NEVER commit key.txt to git", "Use chmod 600 to restrict permissions"],
    },
    {
      step: 2,
      name: "Check Wallet Balance",
      command: "cast balance <YOUR_ADDRESS> --rpc-url <RPC_URL>",
      required: "~0.01 ETH for testnet",
    },
    {
      step: 3,
      name: "Estimate Gas",
      command: "cargo stylus deploy --estimate-gas --private-key-path=./key.txt --endpoint=<RPC_URL>",
    },
    {
      step: 4,
      name: "Deploy Contract",
      command: "cargo stylus deploy --private-key-path=./key.txt --endpoint=<RPC_URL>",
    },
    {
      step: 5,
      name: "Verify Deployment",
      commands: [
        "Check on block explorer",
        "cargo stylus export-abi > abi.json",
        "cast call <CONTRACT_ADDRESS> 'functionName()' --rpc-url <RPC_URL>",
      ],
    },
  ],
  commonIssues: {
    insufficient_funds: {
      error: "insufficient funds for gas",
      solution: "Add ETH to wallet. Use faucet for testnet.",
    },
    nonce_too_low: {
      error: "nonce too low",
      solution: "Wait for pending transactions or use higher nonce",
    },
  },
};

export const TEST_WORKFLOW = {
  name: "Test Stylus Contract",
  description: "Complete workflow for testing Stylus smart contracts",
  testTypes: {
    unit_tests: {
      description: "Test individual functions in isolation",
      framework: "Rust native #[test] with stylus-test",
    },
    stylus_test: {
      description: "Stylus SDK native testing framework (SDK 0.8.0+)",
      setup: 'stylus-sdk = { version = "0.8.4", features = ["stylus-test"] }',
    },
  },
  steps: [
    {
      step: 1,
      name: "Write Unit Tests",
      template: `#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_function_name() {
        let mut contract = Contract::default();
        // Setup, Action, Assert
        assert_eq!(contract.some_function(), expected_value);
    }
}`,
    },
    {
      step: 2,
      name: "Run Rust Tests",
      command: "cargo test",
      options: {
        "-- --nocapture": "Show println! output",
        "--test <name>": "Run specific test file",
      },
    },
    {
      step: 3,
      name: "Test on Testnet",
      commands: [
        "cargo stylus deploy --endpoint https://sepolia-rollup.arbitrum.io/rpc ...",
        "cast call <ADDRESS> 'functionName(args)' --rpc-url <RPC>",
      ],
    },
  ],
  debugging: {
    replay_transaction: "cargo stylus replay --tx <HASH> --endpoint <RPC>",
    trace_transaction: "cargo stylus trace --tx <HASH> --endpoint <RPC>",
    decode_error: "cast 4byte-decode <ERROR_SELECTOR>",
  },
};

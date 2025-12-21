"""
Stylus Development Workflows.

These workflows provide step-by-step guidance for common Stylus development tasks.
The AI IDE uses these to guide users through build, deploy, and test processes.

Last updated: December 2025
Sources:
- https://docs.arbitrum.io/stylus/stylus-quickstart
- https://docs.arbitrum.io/stylus/cli-tools-overview
"""

BUILD_WORKFLOW = {
    "name": "Build Stylus Contract",
    "description": "Complete workflow for building a Stylus smart contract",
    "prerequisites": [
        {"check": "rustup --version", "install": "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"},
        {"check": "rustup default", "install": "rustup default 1.81", "note": "Rust 1.81 recommended, 1.82+ may have issues"},
        {"check": "rustup target list --installed | grep wasm32-unknown-unknown", "install": "rustup target add wasm32-unknown-unknown --toolchain 1.81"},
        {"check": "cargo stylus --version", "install": "cargo install --force cargo-stylus"},
        {"check": "docker --version", "install": "Install Docker from docker.com", "note": "Required for reproducible builds"},
    ],
    "steps": [
        {
            "step": 1,
            "name": "Verify Project Structure",
            "description": "Ensure project has correct Cargo.toml configuration",
            "check_files": ["Cargo.toml", "src/lib.rs"],
            "required_in_cargo_toml": [
                "stylus-sdk dependency",
                "crate-type = [\"cdylib\"]",
                "export-abi feature",
            ],
        },
        {
            "step": 2,
            "name": "Build for WASM",
            "command": "cargo build --release --target wasm32-unknown-unknown",
            "description": "Compile the contract to WebAssembly",
            "expected_output": "Compiling... Finished release [optimized] target",
            "output_file": "target/wasm32-unknown-unknown/release/<name>.wasm",
            "common_errors": {
                "unresolved import `std`": "Ensure #![no_std] or proper std feature flags",
                "linking with `cc` failed": "Install WASM toolchain: rustup target add wasm32-unknown-unknown",
            },
        },
        {
            "step": 3,
            "name": "Validate with cargo stylus check",
            "command": "cargo stylus check",
            "description": "Verify the WASM is compatible with Stylus VM",
            "expected_output": "contract is valid",
            "common_errors": {
                "contract size exceeds": "Enable optimizations in Cargo.toml [profile.release]",
                "unresolved import": "Using unsupported WASM feature or host function",
            },
        },
        {
            "step": 4,
            "name": "Export ABI (optional)",
            "command": "cargo stylus export-abi",
            "description": "Generate Solidity-compatible ABI for frontend integration",
            "save_to": "abi.json",
        },
    ],
    "optimization_tips": [
        "Use opt-level = 's' for size optimization",
        "Enable LTO: lto = true",
        "Set codegen-units = 1 for better optimization",
        "Use panic = 'abort' to reduce binary size",
        "strip = true removes debug symbols",
    ],
    "sample_cargo_toml": """[package]
name = "my-stylus-contract"
version = "0.1.0"
edition = "2021"

[dependencies]
stylus-sdk = "0.8.4"
alloy-primitives = "0.8.14"
alloy-sol-types = "0.8.14"

[dev-dependencies]
stylus-sdk = { version = "0.8.4", features = ["stylus-test"] }

[features]
export-abi = ["stylus-sdk/export-abi"]

[lib]
crate-type = ["cdylib"]

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"
""",
}

DEPLOY_WORKFLOW = {
    "name": "Deploy Stylus Contract",
    "description": "Complete workflow for deploying a Stylus contract to Arbitrum",
    "prerequisites": [
        "Contract passes cargo stylus check",
        "Wallet with ETH on target network",
        "Private key (file or environment variable)",
        "RPC endpoint for target network",
    ],
    "networks": {
        "arbitrum_sepolia": {
            "name": "Arbitrum Sepolia (Testnet)",
            "rpc": "https://sepolia-rollup.arbitrum.io/rpc",
            "chain_id": 421614,
            "explorer": "https://sepolia.arbiscan.io",
            "faucet": "https://faucet.quicknode.com/arbitrum/sepolia",
        },
        "arbitrum_one": {
            "name": "Arbitrum One (Mainnet)",
            "rpc": "https://arb1.arbitrum.io/rpc",
            "chain_id": 42161,
            "explorer": "https://arbiscan.io",
            "warning": "MAINNET - Use with caution, real funds at risk",
        },
        "arbitrum_nova": {
            "name": "Arbitrum Nova",
            "rpc": "https://nova.arbitrum.io/rpc",
            "chain_id": 42170,
            "explorer": "https://nova.arbiscan.io",
        },
    },
    "steps": [
        {
            "step": 1,
            "name": "Prepare Private Key",
            "description": "Securely prepare your deployment key",
            "options": [
                {
                    "method": "Key File",
                    "command": "echo 'YOUR_PRIVATE_KEY' > key.txt && chmod 600 key.txt",
                    "usage": "--private-key-path=./key.txt",
                    "recommended": True,
                },
                {
                    "method": "Environment Variable",
                    "command": "export PRIVATE_KEY='YOUR_PRIVATE_KEY'",
                    "usage": "--private-key=$PRIVATE_KEY",
                    "recommended": False,
                    "warning": "Key may appear in shell history",
                },
            ],
            "security": [
                "NEVER commit key.txt to git (add to .gitignore)",
                "Use chmod 600 to restrict file permissions",
                "Consider hardware wallet for mainnet deployments",
            ],
        },
        {
            "step": 2,
            "name": "Check Wallet Balance",
            "description": "Ensure wallet has sufficient ETH for deployment",
            "command": "cast balance <YOUR_ADDRESS> --rpc-url <RPC_URL>",
            "alternative": "Check on block explorer",
            "required": "~0.01 ETH for testnet, varies for mainnet",
        },
        {
            "step": 3,
            "name": "Estimate Gas (Optional)",
            "command": "cargo stylus deploy --estimate-gas --private-key-path=./key.txt --endpoint=<RPC_URL>",
            "description": "Estimate deployment cost without actually deploying",
        },
        {
            "step": 4,
            "name": "Deploy Contract",
            "command": "cargo stylus deploy --private-key-path=./key.txt --endpoint=<RPC_URL>",
            "description": "Deploy and activate the contract",
            "expected_output": {
                "fields": [
                    "Deploying program to address: 0x...",
                    "Activating program at address: 0x...",
                    "Program activated successfully",
                ],
            },
            "save_output": "Save the contract address for future reference",
        },
        {
            "step": 5,
            "name": "Verify Deployment",
            "commands": [
                "Check on block explorer: <EXPLORER_URL>/address/<CONTRACT_ADDRESS>",
                "Export ABI: cargo stylus export-abi > abi.json",
                "Test interaction: cast call <CONTRACT_ADDRESS> 'functionName()' --rpc-url <RPC_URL>",
            ],
        },
    ],
    "post_deployment": {
        "record_keeping": [
            "Contract address",
            "Deployment transaction hash",
            "Activation transaction hash",
            "ABI file",
            "Git commit hash of deployed code",
        ],
        "verification": {
            "command": "cargo stylus verify --deployment-tx <TX_HASH> --endpoint <RPC_URL>",
            "description": "Verify source code matches deployed bytecode",
        },
    },
    "common_issues": {
        "insufficient_funds": {
            "error": "insufficient funds for gas",
            "solution": "Add ETH to wallet. Use faucet for testnet.",
        },
        "nonce_too_low": {
            "error": "nonce too low",
            "solution": "Wait for pending transactions or use higher nonce",
        },
        "contract_size": {
            "error": "program too large",
            "solution": "Optimize build settings, reduce code size",
        },
        "activation_failed": {
            "error": "activation failed",
            "solution": "Check for unsupported WASM features, verify imports",
        },
    },
}

TEST_WORKFLOW = {
    "name": "Test Stylus Contract",
    "description": "Complete workflow for testing Stylus smart contracts",
    "test_types": {
        "unit_tests": {
            "description": "Test individual functions in isolation",
            "location": "src/lib.rs or separate test files",
            "framework": "Rust native #[test] with stylus-test",
        },
        "stylus_test": {
            "description": "Stylus SDK native testing framework (SDK 0.8.0+)",
            "location": "src/lib.rs with #[cfg(test)]",
            "framework": "stylus_sdk::testing",
            "setup": 'stylus-sdk = { version = "0.8.4", features = ["stylus-test"] }',
        },
        "integration_tests": {
            "description": "Test contract interactions end-to-end",
            "location": "tests/ directory",
            "framework": "Foundry or custom harness",
        },
        "fuzz_tests": {
            "description": "Property-based testing with random inputs",
            "framework": "cargo-fuzz or proptest",
        },
    },
    "steps": [
        {
            "step": 1,
            "name": "Write Unit Tests",
            "description": "Add #[cfg(test)] module to lib.rs",
            "template": """
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_function_name() {
        let mut contract = Contract::default();
        // Setup
        // Action
        // Assert
        assert_eq!(contract.some_function(), expected_value);
    }
}
""",
        },
        {
            "step": 2,
            "name": "Run Rust Tests",
            "command": "cargo test",
            "options": {
                "-- --nocapture": "Show println! output",
                "--test <name>": "Run specific test file",
                "<test_name>": "Run specific test by name",
            },
        },
        {
            "step": 3,
            "name": "Test on Local Node (Optional)",
            "description": "Deploy to local Arbitrum node for integration testing",
            "setup": [
                "Start local node: docker run --rm -it offchainlabs/nitro-node ...",
                "Deploy contract to local node",
                "Run integration tests against local deployment",
            ],
        },
        {
            "step": 4,
            "name": "Test on Testnet",
            "description": "Deploy to Arbitrum Sepolia for live testing",
            "commands": [
                "cargo stylus deploy --endpoint https://sepolia-rollup.arbitrum.io/rpc ...",
                "cast call <ADDRESS> 'functionName(args)' --rpc-url <RPC>",
                "cast send <ADDRESS> 'functionName(args)' --private-key ... --rpc-url <RPC>",
            ],
        },
    ],
    "foundry_integration": {
        "setup": [
            "Install Foundry: curl -L https://foundry.paradigm.xyz | bash && foundryup",
            "Export ABI: cargo stylus export-abi > abi.json",
            "Create Foundry test file in test/ directory",
        ],
        "sample_test": """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

interface IStylusContract {
    function someFunction() external view returns (uint256);
}

contract StylusContractTest is Test {
    IStylusContract public stylusContract;

    function setUp() public {
        // Fork testnet or use deployed address
        stylusContract = IStylusContract(DEPLOYED_ADDRESS);
    }

    function testSomeFunction() public {
        uint256 result = stylusContract.someFunction();
        assertEq(result, expectedValue);
    }
}
""",
        "run_command": "forge test --fork-url <RPC_URL>",
    },
    "debugging": {
        "replay_transaction": "cargo stylus replay --tx <HASH> --endpoint <RPC>",
        "trace_transaction": "cargo stylus trace --tx <HASH> --endpoint <RPC> --use-native-tracer",
        "trace_call": "cast call --trace <ADDRESS> 'function()' --rpc-url <RPC>",
        "decode_error": "cast 4byte-decode <ERROR_SELECTOR>",
    },
}

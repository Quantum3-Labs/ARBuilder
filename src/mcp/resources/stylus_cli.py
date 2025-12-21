"""
Stylus CLI Commands Reference.

This resource provides complete documentation for cargo-stylus commands
that the AI IDE can use to guide users through build/deploy workflows.
"""

STYLUS_CLI_RESOURCE = {
    "tool": "cargo-stylus",
    "version": "0.5.x",
    "installation": {
        "command": "cargo install cargo-stylus",
        "prerequisites": [
            "Rust toolchain (rustup)",
            "wasm32-unknown-unknown target: rustup target add wasm32-unknown-unknown",
        ],
        "verify": "cargo stylus --version",
    },
    "commands": {
        "new": {
            "description": "Create a new Stylus project from template",
            "usage": "cargo stylus new <NAME>",
            "options": {
                "--minimal": "Create minimal project without examples",
            },
            "example": "cargo stylus new my-contract",
            "output": "Creates a new directory with Cargo.toml and src/lib.rs template",
        },
        "check": {
            "description": "Validate that a contract is compatible with Stylus (compiles to valid WASM)",
            "usage": "cargo stylus check [OPTIONS]",
            "options": {
                "--endpoint <URL>": "RPC endpoint to validate against (default: Arbitrum Sepolia)",
                "--wasm-file <PATH>": "Path to pre-built WASM file instead of building",
                "--program-address <ADDR>": "Check if deployment would succeed for existing program",
            },
            "example": "cargo stylus check --endpoint https://sepolia-rollup.arbitrum.io/rpc",
            "notes": [
                "Must be run from project root (where Cargo.toml is)",
                "Validates WASM size, imports, and compatibility",
                "Does NOT deploy - only validates",
            ],
            "common_errors": {
                "contract size too large": "Optimize with cargo stylus check --release or reduce code size",
                "invalid memory import": "Ensure using stylus-sdk memory allocator",
                "unresolved import": "Check for unsupported host functions",
            },
        },
        "deploy": {
            "description": "Deploy a Stylus contract to Arbitrum",
            "usage": "cargo stylus deploy [OPTIONS]",
            "required_options": {
                "--private-key <KEY>": "Private key for deployment (or use --private-key-path)",
                "--private-key-path <PATH>": "Path to file containing private key",
            },
            "optional_options": {
                "--endpoint <URL>": "RPC endpoint (default: Arbitrum Sepolia)",
                "--estimate-gas": "Only estimate gas without deploying",
                "--no-verify": "Skip on-chain verification",
                "--wasm-file <PATH>": "Deploy pre-built WASM file",
                "--cargo-stylus-version <VER>": "Specify cargo-stylus version for reproducibility",
            },
            "example": "cargo stylus deploy --private-key-path=./key.txt --endpoint=https://sepolia-rollup.arbitrum.io/rpc",
            "output_fields": {
                "contract_address": "Address where contract is deployed",
                "transaction_hash": "Deployment transaction hash",
                "gas_used": "Total gas consumed",
                "activation_tx": "Transaction that activated the contract",
            },
            "notes": [
                "Deployment is a 2-step process: deploy WASM + activate",
                "Activation compiles WASM to native code on-chain",
                "Requires ETH for gas fees on the target network",
            ],
            "security_warnings": [
                "NEVER commit private keys to git",
                "Use environment variables or secure key files",
                "Consider using hardware wallets for mainnet",
            ],
        },
        "export-abi": {
            "description": "Export the Solidity ABI for a Stylus contract",
            "usage": "cargo stylus export-abi",
            "example": "cargo stylus export-abi > abi.json",
            "notes": [
                "Requires #[public] attribute on impl blocks",
                "ABI is compatible with standard Solidity tooling",
                "Can be used with ethers.js, viem, or foundry",
            ],
        },
        "verify": {
            "description": "Verify a deployed contract's source code",
            "usage": "cargo stylus verify [OPTIONS]",
            "options": {
                "--deployment-tx <TX>": "Transaction hash of deployment",
                "--endpoint <URL>": "RPC endpoint",
            },
            "notes": [
                "Verifies that local code matches deployed bytecode",
                "Useful for auditing and transparency",
            ],
        },
        "cgen": {
            "description": "Generate C code bindings for Stylus contract",
            "usage": "cargo stylus cgen",
            "notes": ["Advanced feature for C/C++ interop"],
        },
        "replay": {
            "description": "Replay a transaction locally for debugging",
            "usage": "cargo stylus replay --tx <HASH> --endpoint <URL>",
            "notes": [
                "Useful for debugging failed transactions",
                "Shows detailed execution trace",
            ],
        },
    },
    "environment_variables": {
        "STYLUS_ENDPOINT": "Default RPC endpoint",
        "ETH_RPC_URL": "Alternative RPC endpoint variable",
        "PRIVATE_KEY": "Private key for signing (not recommended, use file)",
    },
    "cargo_toml_config": {
        "required_features": [
            '[features]\nexport-abi = ["stylus-sdk/export-abi"]',
        ],
        "recommended_profile": """
[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"
""",
        "dependencies": {
            "stylus-sdk": "0.6.0",
            "alloy-primitives": "0.7.6",
            "alloy-sol-types": "0.7.6",
        },
    },
    "troubleshooting": {
        "wasm_too_large": {
            "symptoms": ["Contract exceeds size limit", "deployment fails with size error"],
            "solutions": [
                "Enable release profile optimizations",
                "Use opt-level = 's' or 'z'",
                "Enable LTO (link-time optimization)",
                "Remove unused dependencies",
                "Split into multiple contracts",
            ],
        },
        "activation_failed": {
            "symptoms": ["Deployment succeeds but activation fails"],
            "solutions": [
                "Check for unsupported WASM features",
                "Ensure all imports are valid Stylus host functions",
                "Verify contract doesn't use floating point",
            ],
        },
        "rpc_connection": {
            "symptoms": ["Cannot connect to RPC", "timeout errors"],
            "solutions": [
                "Verify endpoint URL is correct",
                "Check network connectivity",
                "Try alternative RPC providers",
            ],
        },
    },
}

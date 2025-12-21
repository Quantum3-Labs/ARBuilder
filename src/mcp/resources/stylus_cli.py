"""
Stylus CLI Commands Reference.

This resource provides complete documentation for cargo-stylus commands
that the AI IDE can use to guide users through build/deploy workflows.

Last updated: December 2025
Sources:
- https://docs.arbitrum.io/stylus/cli-tools-overview
- https://docs.arbitrum.io/stylus/stylus-quickstart
- https://github.com/OffchainLabs/cargo-stylus
"""

STYLUS_CLI_RESOURCE = {
    "tool": "cargo-stylus",
    "version": "0.5.x+",
    "last_updated": "2025-12",
    "installation": {
        "command": "cargo install --force cargo-stylus",
        "prerequisites": [
            "Rust toolchain v1.81 or newer (v1.82+ may have issues)",
            "WASM target: rustup target add wasm32-unknown-unknown --toolchain 1.81",
            "Docker (required for reproducible builds and some commands)",
        ],
        "setup_commands": [
            "rustup default 1.81",
            "rustup target add wasm32-unknown-unknown --toolchain 1.81",
            "cargo install --force cargo-stylus",
        ],
        "verify": "cargo stylus --version",
    },
    "commands": {
        "new": {
            "description": "Create a new Stylus project from template",
            "usage": "cargo stylus new <NAME>",
            "options": {
                "--minimal": "Create minimal project without examples (barebones structure)",
            },
            "examples": [
                "cargo stylus new my-contract",
                "cargo stylus new --minimal minimal-contract",
            ],
            "output": "Creates a new directory with Cargo.toml and src/lib.rs template",
        },
        "init": {
            "description": "Initialize a Stylus project in the current directory",
            "usage": "cargo stylus init",
            "options": {
                "--minimal": "Create minimal project structure",
            },
            "examples": [
                "mkdir my-contract && cd my-contract && cargo stylus init",
            ],
            "notes": [
                "Similar to 'new' but initializes in current directory",
                "Useful when you already have a directory structure",
            ],
        },
        "check": {
            "description": "Validate that a contract is compatible with Stylus (compiles to valid WASM)",
            "usage": "cargo stylus check [OPTIONS]",
            "alias": "c",
            "options": {
                "--endpoint <URL>": "RPC endpoint to validate against (default: Arbitrum Sepolia)",
                "--wasm-file <PATH>": "Path to pre-built WASM file instead of building",
                "--contract-address <ADDR>": "Target contract address (default: random)",
            },
            "examples": [
                "cargo stylus check",
                "cargo stylus check --endpoint=https://arb1.arbitrum.io/rpc",
                "cargo stylus check --wasm-file=./contract.wasm",
            ],
            "notes": [
                "Must be run from project root (where Cargo.toml is)",
                "Validates WASM size (must be under 24KB compressed), imports, and compatibility",
                "Does NOT deploy - only validates",
                "Requires Docker for reproducible builds",
            ],
            "common_errors": {
                "contract size too large": "Optimize with release profile or reduce code size (24KB limit)",
                "invalid memory import": "Ensure using stylus-sdk memory allocator",
                "unresolved import": "Check for unsupported host functions",
            },
        },
        "deploy": {
            "description": "Deploy a Stylus contract to Arbitrum (deploys WASM + activates)",
            "usage": "cargo stylus deploy [OPTIONS]",
            "alias": "d",
            "required_options": {
                "--private-key <KEY>": "Private key for deployment (or use --private-key-path)",
                "--private-key-path <PATH>": "Path to file containing private key",
            },
            "optional_options": {
                "--endpoint <URL>": "RPC endpoint (default: Arbitrum Sepolia)",
                "--estimate-gas": "Only estimate gas without deploying",
                "--no-verify": "Skip Docker-based reproducible builds",
                "--no-activate": "Deploy without triggering activation",
                "--wasm-file <PATH>": "Deploy pre-built WASM file",
            },
            "examples": [
                "cargo stylus deploy --private-key-path=./key.txt --estimate-gas",
                "cargo stylus deploy --private-key-path=./key.txt --endpoint=https://sepolia-rollup.arbitrum.io/rpc",
                "cargo stylus deploy --endpoint=https://arb1.arbitrum.io/rpc --private-key-path=./key.txt",
            ],
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
                "Requires Docker for reproducible builds (unless --no-verify)",
            ],
            "security_warnings": [
                "NEVER commit private keys to git",
                "Use environment variables or secure key files",
                "Consider using hardware wallets for mainnet",
            ],
        },
        "activate": {
            "description": "Activate an already deployed contract",
            "usage": "cargo stylus activate [OPTIONS]",
            "alias": "a",
            "options": {
                "--address <ADDR>": "Address of deployed contract to activate",
                "--endpoint <URL>": "RPC endpoint",
                "--private-key-path <PATH>": "Path to private key file",
            },
            "notes": [
                "Contracts need re-activation once per year (365 days)",
                "Re-activation required after Stylus upgrades",
                "Separate from deploy if using --no-activate during deployment",
            ],
        },
        "cache": {
            "description": "Cache a contract using the Stylus CacheManager for faster execution",
            "usage": "cargo stylus cache <SUBCOMMAND>",
            "subcommands": {
                "status": {
                    "description": "Check if a contract is cached",
                    "usage": "cargo stylus cache status --address=<CONTRACT_ADDRESS>",
                },
                "suggest-bid": {
                    "description": "Get minimum bid required to cache a contract",
                    "usage": "cargo stylus cache suggest-bid --address=<CONTRACT_ADDRESS>",
                },
                "bid": {
                    "description": "Place a bid to cache a contract",
                    "usage": "cargo stylus cache bid --address=<CONTRACT_ADDRESS> --private-key-path=<PATH>",
                },
            },
            "notes": [
                "CacheManager can hold approximately 4,000 contracts in memory",
                "Cached contracts execute faster (no WASM interpretation)",
                "Bidding is competitive - higher bids get priority",
            ],
        },
        "export-abi": {
            "description": "Export the Solidity ABI for a Stylus contract",
            "usage": "cargo stylus export-abi [OPTIONS]",
            "options": {
                "--output <PATH>": "Output file path (default: stdout)",
                "--json": "Generate JSON-format ABI (requires solc)",
            },
            "examples": [
                "cargo stylus export-abi",
                "cargo stylus export-abi > abi.json",
                "cargo stylus export-abi --output=./abi.json --json",
            ],
            "notes": [
                "Requires #[public] attribute on impl blocks",
                "ABI is compatible with standard Solidity tooling",
                "Can be used with ethers.js, viem, or foundry",
            ],
        },
        "verify": {
            "description": "Verify a deployed contract's source code",
            "usage": "cargo stylus verify [OPTIONS]",
            "alias": "v",
            "options": {
                "--deployment-tx <TX>": "Transaction hash of deployment",
                "--endpoint <URL>": "RPC endpoint",
                "--no-verify": "Skip Docker-based reproducible builds",
            },
            "examples": [
                "cargo stylus verify --deployment-tx=0x1234abcd...",
                "cargo stylus verify --endpoint=https://arb1.arbitrum.io/rpc --deployment-tx=0x5678...",
            ],
            "notes": [
                "Verifies that local code matches deployed bytecode",
                "Useful for auditing and transparency",
                "Requires v0.5.0+ for Arbiscan verification",
            ],
        },
        "replay": {
            "description": "Replay a transaction locally for debugging (in gdb)",
            "usage": "cargo stylus replay --tx <HASH> --endpoint <URL>",
            "alias": "r",
            "options": {
                "--tx <HASH>": "Transaction hash to replay",
                "--endpoint <URL>": "RPC endpoint",
                "--project <PATH>": "Project path",
            },
            "notes": [
                "Useful for debugging failed transactions",
                "Shows detailed execution trace in gdb",
                "Requires local project with matching source code",
            ],
        },
        "trace": {
            "description": "Trace a transaction for debugging",
            "usage": "cargo stylus trace --tx <HASH> --endpoint <URL>",
            "alias": "t",
            "options": {
                "--tx <HASH>": "Transaction hash to trace",
                "--endpoint <URL>": "RPC endpoint (default: http://localhost:8547)",
                "--project <PATH>": "Project path",
                "--use-native-tracer": "Use native Stylus tracer instead of JS tracer",
            },
            "examples": [
                "cargo stylus trace --tx=0x1234... --endpoint=https://arb1.arbitrum.io/rpc",
                "cargo stylus trace --tx=0x1234... --endpoint=$RPC_URL --use-native-tracer",
            ],
            "notes": [
                "Uses debug_traceTransaction RPC call",
                "--use-native-tracer has broader RPC provider support",
            ],
        },
        "cgen": {
            "description": "Generate C code bindings for Stylus contract",
            "usage": "cargo stylus cgen",
            "notes": ["Advanced feature for C/C++ interop"],
        },
    },
    "environment_variables": {
        "STYLUS_ENDPOINT": "Default RPC endpoint",
        "ETH_RPC_URL": "Alternative RPC endpoint variable (Foundry compatible)",
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
            "stylus-sdk": "0.8.4",
            "alloy-primitives": "0.8.14",
            "alloy-sol-types": "0.8.14",
        },
        "dev_dependencies": {
            "stylus-sdk": '{ version = "0.8.4", features = ["stylus-test"] }',
        },
    },
    "rust_requirements": {
        "version": "1.81 or newer",
        "unsupported": "1.82+ (may have compatibility issues)",
        "target": "wasm32-unknown-unknown",
    },
    "size_limits": {
        "max_compressed_size": "24KB",
        "compression": "Brotli",
        "notes": "Brotli-compressed WASM binaries must fit within 24KB",
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
                "Set codegen-units = 1",
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
                "Note: Public RPCs do not support WebSocket",
            ],
        },
        "rust_version": {
            "symptoms": ["Compilation errors", "WASM build fails"],
            "solutions": [
                "Use Rust 1.81: rustup default 1.81",
                "Avoid Rust 1.82+ which may have issues",
                "Ensure WASM target is installed for correct toolchain",
            ],
        },
        "docker_required": {
            "symptoms": ["Reproducible build failed", "verify command fails"],
            "solutions": [
                "Install Docker from docker.com",
                "Ensure Docker daemon is running",
                "Use --no-verify flag to skip (not recommended for production)",
            ],
        },
        "yearly_reactivation": {
            "symptoms": ["Contract stopped working after ~1 year"],
            "solutions": [
                "Contracts need re-activation every 365 days",
                "Use: cargo stylus activate --address=<ADDR> --private-key-path=<PATH>",
                "Also required after Stylus protocol upgrades",
            ],
        },
    },
}

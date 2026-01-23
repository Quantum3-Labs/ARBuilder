"""
Stylus Coding Rules Resource.

Provides coding guidelines and patterns for Stylus smart contract development.
This is the single source of truth for AI assistant rules.
"""

STYLUS_CODING_RULES = {
    "name": "Stylus Coding Rules",
    "version": "1.0.0",
    "description": "Guidelines for AI assistants generating Stylus smart contracts",

    "sdk_version": {
        "stylus_sdk": "0.9.2",
        "alloy_primitives": "=0.8.20",
        "alloy_sol_types": "=0.8.20",
        "rust_version": "1.81",
        "rust_version_note": "1.82+ may have compatibility issues",
    },

    "file_header": '''#![cfg_attr(not(any(feature = "export-abi", test)), no_std)]
#![cfg_attr(not(test), no_main)]
extern crate alloc;

use stylus_sdk::{prelude::*, alloy_primitives::{Address, U256}};''',

    "cargo_toml": {
        "dependencies": '''[dependencies]
stylus-sdk = "0.9.2"
alloy-primitives = "=0.8.20"
alloy-sol-types = "=0.8.20"

[dev-dependencies]
stylus-sdk = { version = "0.9.2", features = ["stylus-test"] }

[features]
export-abi = ["stylus-sdk/export-abi"]

[lib]
crate-type = ["cdylib"]''',

        "release_profile": '''[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"''',
    },

    "patterns": {
        "storage": {
            "description": "Use sol_storage! macro for all contract storage",
            "example": '''sol_storage! {
    #[entrypoint]
    pub struct MyContract {
        uint256 value;
        mapping(address => uint256) balances;
    }
}''',
            "access": {
                "read_value": ".get()",
                "write_value": ".set(value)",
                "read_mapping": ".getter(key)",
                "write_mapping": ".setter(key)",
            },
        },

        "public_interface": {
            "description": "Mark public functions with #[public] attribute",
            "example": '''#[public]
impl MyContract {
    pub fn get_value(&self) -> U256 {
        self.value.get()
    }

    pub fn set_value(&mut self, value: U256) {
        self.value.set(value);
    }
}''',
        },

        "events": {
            "description": "Define events with sol! macro, emit with evm::log()",
            "definition": '''sol! {
    event Transfer(address indexed from, address indexed to, uint256 value);
}''',
            "emit": '''evm::log(Transfer {
    from: sender,
    to: recipient,
    value: amount,
});''',
        },

        "errors": {
            "description": "Define errors with sol! macro, return encoded",
            "definition": '''sol! {
    error InsufficientBalance(address account, uint256 required, uint256 available);
    error Unauthorized();
}''',
            "usage": '''if balance < amount {
    return Err(InsufficientBalance {
        account: sender,
        required: amount,
        available: balance,
    }.encode());
}''',
        },

        "tests": {
            "description": "Unit tests with stylus-test feature",
            "example": '''#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_initial_value() {
        let contract = Contract::default();
        assert_eq!(contract.value.get(), U256::ZERO);
    }
}''',
        },
    },

    "constraints": {
        "size_limit": "24KB (Brotli-compressed WASM)",
        "no_floating_point": "Floating point operations not supported",
        "no_std": "Use #![no_std] with alloc for heap allocations",
        "yearly_reactivation": "Contracts need reactivation after 365 days",
    },

    "common_pitfalls": [
        "Storage not initialized - Use StorageType::default()",
        "Exceeding 24KB - Optimize release profile, reduce dependencies",
        "Wrong Rust version - Use 1.81, not 1.82+",
        "Missing WASM target - rustup target add wasm32-unknown-unknown",
        "Floating point operations - Not supported in Stylus WASM",
        "Direct std usage - Use #![no_std] with alloc",
    ],

    "cli_commands": {
        "check": "cargo stylus check",
        "deploy": "cargo stylus deploy --private-key-path=./key.txt --endpoint=<RPC_URL>",
        "export_abi": "cargo stylus export-abi",
        "trace": "cargo stylus trace --tx=<HASH> --endpoint=<RPC_URL> --use-native-tracer",
    },

    "networks": {
        "arbitrum_sepolia": "https://sepolia-rollup.arbitrum.io/rpc",
        "arbitrum_one": "https://arb1.arbitrum.io/rpc",
        "arbitrum_nova": "https://nova.arbitrum.io/rpc",
    },
}

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
        "stylus_sdk": "0.10.0",
        "alloy_primitives": "1.0.1",
        "alloy_sol_types": "1.0.1",
        "rust_version": "1.88.0",
        "rust_version_note": "Requires rust-toolchain.toml with channel 1.88.0",
    },

    "file_header": '''#![cfg_attr(not(any(feature = "export-abi", test)), no_std)]
#![cfg_attr(not(test), no_main)]
extern crate alloc;

use stylus_sdk::{prelude::*, alloy_primitives::{Address, U256}};''',

    "cargo_toml": {
        "dependencies": '''[dependencies]
stylus-sdk = "0.10.0"
alloy-primitives = "1.0.1"
alloy-sol-types = "1.0.1"

[dev-dependencies]
stylus-sdk = { version = "0.10.0", features = ["stylus-test"] }

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
            "description": "Define events with sol! macro, emit with self.vm().log()",
            "definition": '''sol! {
    event Transfer(address indexed from, address indexed to, uint256 value);
}''',
            "emit": '''self.vm().log(Transfer {
    from: sender,
    to: recipient,
    value: amount,
});''',
        },

        "errors": {
            "description": "Define errors with sol! macro, derive SolidityError on enum, return abi_encode()",
            "definition": '''sol! {
    error InsufficientBalance(address account, uint256 required, uint256 available);
    error Unauthorized();
}

#[derive(SolidityError)]
pub enum ContractError {
    InsufficientBalance(InsufficientBalance),
    Unauthorized(Unauthorized),
}''',
            "usage": '''// MUST import SolError for .abi_encode():
// use alloy_sol_types::SolError;
if balance < amount {
    return Err(InsufficientBalance {
        account: sender,
        required: amount,
        available: balance,
    }.abi_encode());
}''',
        },

        "eth_transfer": {
            "description": "Transfer ETH using stylus_sdk::call::transfer (NOT evm::transfer_eth)",
            "example": '''use stylus_sdk::call::transfer_eth;

// Inside a #[public] method (needs &mut self for vm context):
transfer_eth(self, to, amount)?;''',
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
        "Wrong Rust version - Use 1.88.0 via rust-toolchain.toml",
        "Missing WASM target - rustup target add wasm32-unknown-unknown",
        "Floating point operations - Not supported in Stylus WASM",
        "Direct std usage - Use #![no_std] with alloc",
        "Missing Stylus.toml - Required since SDK 0.10.0, must have [workspace], [workspace.networks], and [contract] sections",
        "Missing rust-toolchain.toml - Required since SDK 0.10.0",
        "Using deprecated msg::sender() - Use self.vm().msg_sender() since 0.10.0",
        "Using deprecated evm::log() - Use self.vm().log() since 0.10.0",
        "Using `use stylus_sdk::evm` - Module removed in 0.10.0, use self.vm() methods",
        "Using evm::transfer_eth() - Moved to stylus_sdk::call::transfer_eth(self, to, amount)",
        "Missing SolError import - .abi_encode() on errors requires use alloy_sol_types::SolError",
        "Chained .setter() borrows - Read with .get() first, then .setter().set() separately",
    ],

    "forbidden_imports": [
        "stylus_sdk::evm",
        "stylus_sdk::msg",
    ],

    "required_files": {
        "Stylus.toml": '[workspace]\n\n[workspace.networks]\n\n[contract]\n',
        "rust-toolchain.toml": '[toolchain]\nchannel = "1.88.0"\ntargets = ["wasm32-unknown-unknown"]\n',
    },

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

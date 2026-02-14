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

    "file_header": '''#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]
#[macro_use]
extern crate alloc;

use alloc::{vec, vec::Vec};
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
crate-type = ["lib", "cdylib"]''',

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
            "description": "Transfer ETH using stylus_sdk::call::transfer::transfer_eth (NOT evm::transfer_eth)",
            "example": '''use stylus_sdk::call::transfer::transfer_eth;

// Inside a #[public] method (needs &mut self for vm context):
transfer_eth(self, to, amount)?;''',
        },

        "raw_call_eth_transfer": {
            "description": "Transfer ETH via RawCall (requires self.vm() and unsafe block)",
            "example": '''use stylus_sdk::call::RawCall;

// Inside a #[public] method — MUST be unsafe:
unsafe {
    let _ = RawCall::new_with_value(self.vm(), amount).call(recipient, &[]);
}''',
        },

        "main_rs": {
            "description": "Required src/main.rs for cargo stylus deploy (ABI export via print_from_args)",
            "example": '''#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]

#[cfg(not(any(test, feature = "export-abi")))]
#[unsafe(no_mangle)]
pub extern "C" fn main() {}

#[cfg(feature = "export-abi")]
fn main() {
    my_contract::print_from_args();
}''',
        },

        "package_naming": {
            "description": "Cargo.toml package name MUST use underscores for cargo-stylus compatibility",
            "example": '''[package]
name = "my_contract"  # NOT "my-contract" — hyphens prevent cargo-stylus from finding the WASM file

[[bin]]
name = "my_contract"  # Must match package name
path = "src/main.rs"''',
        },

        "uint8_gotcha": {
            "description": "uint8 in sol_storage! maps to Uint<8,1>, not native u8",
            "note": "Comparisons between Uint<8,1> and u8 won't compile. Either use .try_into() or prefer uint256 for simplicity.",
        },

        "cross_contract_calls": {
            "description": "Call external contracts using sol_interface! macro with Host + CallContext pattern",
            "definition": '''sol_interface! {
    interface IToken {
        function transfer(address to, uint256 amount) external returns (bool);
        function balanceOf(address account) external view returns (uint256);
    }
}''',
            "usage": '''// Call is available from stylus_sdk::prelude::* (no separate import needed)
// Or explicitly: use stylus_sdk::call::Call;

// sol_interface! generates methods with signature:
//   method_name(&self, host: &impl Host, context: impl CallContext, ...solidity_args)
//
// host = self.vm()
// context = Call::new() | Call::new_mutating() | Call::new_payable()

// View call:
let balance = token.balance_of(self.vm(), Call::new(), account)?;

// Mutating call:
let success = token.transfer(self.vm(), Call::new(), recipient, amount)?;

// Payable call with gas/value config:
let config = Call::new()
    .gas(100_000)
    .value(U256::from(1_000_000));
let result = token.transfer(self.vm(), config, recipient, amount)?;''',
            "note": "In SDK 0.10.0, Call::new_in(self) from 0.9.x is removed. Use Call::new() with self.vm() as host arg.",
        },

        "abi_naming": {
            "description": "Stylus exports snake_case Rust function names as camelCase in the ABI",
            "example": "pub fn create_market(...) → ABI name: 'createMarket' (NOT 'create_market')",
            "note": "Frontend/backend code must use camelCase function names when calling the contract via viem/wagmi. Single-word names are unchanged (e.g. increment stays increment).",
        },

        "view_function_gotcha": {
            "description": "Stylus &self view functions CANNOT make external contract calls — they revert",
            "note": "Unlike Solidity view functions, Stylus view methods (&self) cannot call other contracts. External calls (e.g. reading a Chainlink oracle) require &mut self. Workaround: read the external data from the frontend via wagmi/viem instead, or change the function to &mut self.",
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
        "Using evm::transfer_eth() - Moved to stylus_sdk::call::transfer::transfer_eth(self, to, amount)",
        "Missing SolError import - .abi_encode() on errors requires use alloy_sol_types::SolError",
        "Chained .setter() borrows - Read with .get() first, then .setter().set() separately",
        "Missing src/main.rs - Required for cargo stylus deploy (uses print_from_args(), NOT print_abi())",
        "Package name with hyphens - Must use underscores in Cargo.toml (my_contract, NOT my-contract)",
        "crate-type only cdylib - Must be ['lib', 'cdylib'] so bin target can link to lib",
        "Missing use alloc::vec; - sol_storage! macro needs the vec module in scope",
        "RawCall without self.vm() - RawCall::new_with_value needs self.vm() as first arg and unsafe block",
        "uint8 in sol_storage! - Maps to Uint<8,1>, not u8. Use .try_into() for comparisons or prefer uint256",
        "Using Call::new_in(self) — removed in 0.10.0. Use Call::new() / Call::new_mutating() / Call::new_payable() with self.vm() as host",
        "snake_case ABI names in frontend — Stylus exports snake_case Rust fns as camelCase (create_market → createMarket). Use camelCase in wagmi/viem functionName",
        "External calls from &self view functions — Stylus view fns revert on external calls (unlike Solidity). Use &mut self or read from frontend",
        "MetaMask L2 gas underestimation — On Arbitrum Sepolia, MetaMask may underestimate maxFeePerGas causing 'max fee per gas less than block base fee'. Add explicit gas overrides in frontend",
    ],

    "forbidden_imports": [
        "stylus_sdk::evm",
        "stylus_sdk::msg",
        "Call::new_in",
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

"""
Curated working templates from official Stylus examples.
These templates are verified to compile and deploy correctly.

Sources (migrated to SDK 0.10.0):
- Counter: https://github.com/OffchainLabs/stylus-hello-world
- VendingMachine: https://github.com/OffchainLabs/stylus-quickstart-vending-machine
- ERC20: Simplified version based on Stylus patterns
"""

import json
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class StylusTemplate:
    """A curated Stylus contract template."""

    name: str
    description: str
    contract_type: str  # token, nft, defi, utility, custom
    sdk_version: str
    features: List[str]
    lib_rs: str
    cargo_toml: str
    main_rs: str  # For ABI export: cargo run --features export-abi
    stylus_toml: str = ""  # Required since SDK 0.10.0
    rust_toolchain_toml: str = ""  # Required since SDK 0.10.0


# Counter template - Simple storage pattern
# From: stylus-hello-world (migrated to SDK 0.10.0)
COUNTER_TEMPLATE = StylusTemplate(
    name="Counter",
    description="Simple counter with increment, add, multiply operations",
    contract_type="utility",
    sdk_version="0.10.0",
    features=["storage", "public functions", "payable", "tests"],
    lib_rs="""#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]
#[macro_use]
extern crate alloc;

use alloc::{vec, vec::Vec};
use stylus_sdk::{alloy_primitives::U256, prelude::*};

sol_storage! {
    #[entrypoint]
    pub struct Counter {
        uint256 number;
    }
}

#[public]
impl Counter {
    pub fn number(&self) -> U256 {
        self.number.get()
    }

    pub fn set_number(&mut self, new_number: U256) {
        self.number.set(new_number);
    }

    pub fn increment(&mut self) {
        let number = self.number.get();
        self.set_number(number + U256::from(1));
    }

    pub fn add_number(&mut self, new_number: U256) {
        self.number.set(new_number + self.number.get());
    }

    pub fn mul_number(&mut self, new_number: U256) {
        self.number.set(new_number * self.number.get());
    }

    #[payable]
    pub fn add_from_msg_value(&mut self) {
        let number = self.number.get();
        self.set_number(number + self.vm().msg_value());
    }
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn test_counter() {
        use stylus_sdk::testing::*;
        let vm = TestVM::default();
        let mut contract = Counter::from(&vm);

        assert_eq!(U256::ZERO, contract.number());
        contract.increment();
        assert_eq!(U256::from(1), contract.number());
        contract.add_number(U256::from(3));
        assert_eq!(U256::from(4), contract.number());
        contract.mul_number(U256::from(2));
        assert_eq!(U256::from(8), contract.number());
        contract.set_number(U256::from(100));
        assert_eq!(U256::from(100), contract.number());
        vm.set_value(U256::from(2));
        contract.add_from_msg_value();
        assert_eq!(U256::from(102), contract.number());
    }
}""",
    cargo_toml='''[package]
name = "stylus_counter"
version = "0.1.0"
edition = "2021"
license = "MIT OR Apache-2.0"

[dependencies]
stylus-sdk = "0.10.0"
alloy-primitives = "1.0.1"
alloy-sol-types = "1.0.1"

[dev-dependencies]
stylus-sdk = { version = "0.10.0", features = ["stylus-test"] }

[features]
default = ["mini-alloc"]
export-abi = ["stylus-sdk/export-abi"]
debug = ["stylus-sdk/debug"]
mini-alloc = ["stylus-sdk/mini-alloc"]

[lib]
crate-type = ["lib", "cdylib"]

[[bin]]
name = "stylus_counter"
path = "src/main.rs"

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"''',
    main_rs="""#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]

#[cfg(not(any(test, feature = "export-abi")))]
#[unsafe(no_mangle)]
pub extern "C" fn main() {}

#[cfg(feature = "export-abi")]
fn main() {
    stylus_counter::print_from_args();
}""",
    stylus_toml="[workspace]\n\n[workspace.networks]\n\n[contract]\n",
    rust_toolchain_toml='[toolchain]\nchannel = "1.91.0"\ntargets = ["wasm32-unknown-unknown"]\n',
)

# Vending Machine template - Mappings and time-based logic
VENDING_MACHINE_TEMPLATE = StylusTemplate(
    name="VendingMachine",
    description="Mapping storage with time-based distribution logic",
    contract_type="defi",
    sdk_version="0.10.0",
    features=["mappings", "timestamps", "rate limiting", "tests"],
    lib_rs="""#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]
#[macro_use]
extern crate alloc;

use alloc::{vec, vec::Vec};
use stylus_sdk::alloy_primitives::{Address, U256};
use stylus_sdk::prelude::*;

sol_storage! {
    #[entrypoint]
    pub struct VendingMachine {
        mapping(address => uint256) balances;
        mapping(address => uint256) last_claim_time;
    }
}

#[public]
impl VendingMachine {
    /// Claim tokens if enough time has passed since last claim
    pub fn claim(&mut self, user: Address) -> Result<bool, Vec<u8>> {
        let last_claim = self.last_claim_time.get(user);
        let cooldown = U256::from(60); // 60 seconds cooldown
        let min_claim_time = last_claim + cooldown;
        let current_time = U256::from(self.vm().block_timestamp());

        if current_time >= min_claim_time {
            // Update balance (get current first to avoid borrow conflict)
            let current_balance = self.balances.get(user);
            self.balances.setter(user).set(current_balance + U256::from(1));

            // Update last claim time
            self.last_claim_time.setter(user).set(current_time);

            Ok(true)
        } else {
            Ok(false)
        }
    }

    /// Get balance for a user
    pub fn balance_of(&self, user: Address) -> U256 {
        self.balances.get(user)
    }

    /// Get time until next claim is available
    pub fn time_until_claim(&self, user: Address) -> U256 {
        let last_claim = self.last_claim_time.get(user);
        let cooldown = U256::from(60);
        let next_claim_time = last_claim + cooldown;
        let current_time = U256::from(self.vm().block_timestamp());

        if current_time >= next_claim_time {
            U256::ZERO
        } else {
            next_claim_time - current_time
        }
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use stylus_sdk::testing::*;
    use stylus_sdk::alloy_primitives::address;

    #[test]
    fn test_claim() {
        let vm = TestVM::default();
        let mut contract = VendingMachine::from(&vm);
        let user = address!("0xCDC41bff86a62716f050622325CC17a317f99404");

        // Initial balance should be 0
        assert_eq!(contract.balance_of(user), U256::ZERO);

        // First claim should succeed (no cooldown yet)
        vm.set_block_timestamp(100);
        assert!(contract.claim(user).unwrap());
        assert_eq!(contract.balance_of(user), U256::from(1));

        // Immediate second claim should fail (cooldown)
        assert!(!contract.claim(user).unwrap());
        assert_eq!(contract.balance_of(user), U256::from(1));

        // After cooldown, claim should succeed
        vm.set_block_timestamp(161); // 100 + 60 + 1
        assert!(contract.claim(user).unwrap());
        assert_eq!(contract.balance_of(user), U256::from(2));
    }
}""",
    cargo_toml='''[package]
name = "stylus_vending_machine"
version = "0.1.0"
edition = "2021"
license = "MIT OR Apache-2.0"

[dependencies]
stylus-sdk = "0.10.0"
alloy-primitives = "1.0.1"
alloy-sol-types = "1.0.1"

[dev-dependencies]
stylus-sdk = { version = "0.10.0", features = ["stylus-test"] }

[features]
default = ["mini-alloc"]
export-abi = ["stylus-sdk/export-abi"]
debug = ["stylus-sdk/debug"]
mini-alloc = ["stylus-sdk/mini-alloc"]

[lib]
crate-type = ["lib", "cdylib"]

[[bin]]
name = "stylus_vending_machine"
path = "src/main.rs"

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"''',
    main_rs="""#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]

#[cfg(not(any(test, feature = "export-abi")))]
#[unsafe(no_mangle)]
pub extern "C" fn main() {}

#[cfg(feature = "export-abi")]
fn main() {
    stylus_vending_machine::print_from_args();
}""",
    stylus_toml="[workspace]\n\n[workspace.networks]\n\n[contract]\n",
    rust_toolchain_toml='[toolchain]\nchannel = "1.91.0"\ntargets = ["wasm32-unknown-unknown"]\n',
)

# Simple ERC20 template - Basic token without OpenZeppelin
SIMPLE_ERC20_TEMPLATE = StylusTemplate(
    name="SimpleERC20",
    description="Basic ERC20 token with transfer, approve, transferFrom",
    contract_type="token",
    sdk_version="0.10.0",
    features=["ERC20", "mappings", "events", "error handling"],
    lib_rs="""#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]
#[macro_use]
extern crate alloc;

use alloc::{string::String, vec, vec::Vec};
use stylus_sdk::{
    alloy_primitives::{Address, U8, U256},
    alloy_sol_types::{sol, SolError},
    prelude::*,
};

// Define events
sol! {
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}

// Define errors
sol! {
    error InsufficientBalance(address from, uint256 have, uint256 want);
    error InsufficientAllowance(address spender, uint256 have, uint256 want);
}

sol_storage! {
    #[entrypoint]
    pub struct Erc20 {
        string name;
        string symbol;
        uint8 decimals;
        uint256 total_supply;
        mapping(address => uint256) balances;
        mapping(address => mapping(address => uint256)) allowances;
    }
}

#[public]
impl Erc20 {
    /// Initialize the token with name, symbol, and initial supply
    pub fn initialize(
        &mut self,
        name: String,
        symbol: String,
        decimals: u8,
        initial_supply: U256,
    ) {
        self.name.set_str(&name);
        self.symbol.set_str(&symbol);
        self.decimals.set(U8::from(decimals));
        self.total_supply.set(initial_supply);
        self.balances.setter(self.vm().msg_sender()).set(initial_supply);
    }

    /// Get token name
    pub fn name(&self) -> String {
        self.name.get_string()
    }

    /// Get token symbol
    pub fn symbol(&self) -> String {
        self.symbol.get_string()
    }

    /// Get decimals
    pub fn decimals(&self) -> u8 {
        self.decimals.get().try_into().unwrap_or(18)
    }

    /// Get total supply
    pub fn total_supply(&self) -> U256 {
        self.total_supply.get()
    }

    /// Get balance of an address
    pub fn balance_of(&self, owner: Address) -> U256 {
        self.balances.get(owner)
    }

    /// Transfer tokens to another address
    pub fn transfer(&mut self, to: Address, value: U256) -> Result<bool, Vec<u8>> {
        let from = self.vm().msg_sender();
        self._transfer(from, to, value)?;
        Ok(true)
    }

    /// Get allowance
    pub fn allowance(&self, owner: Address, spender: Address) -> U256 {
        self.allowances.get(owner).get(spender)
    }

    /// Approve spender to spend tokens
    pub fn approve(&mut self, spender: Address, value: U256) -> bool {
        let owner = self.vm().msg_sender();
        self.allowances.setter(owner).setter(spender).set(value);
        self.vm().log(Approval { owner, spender, value });
        true
    }

    /// Transfer tokens from one address to another (requires allowance)
    pub fn transfer_from(
        &mut self,
        from: Address,
        to: Address,
        value: U256,
    ) -> Result<bool, Vec<u8>> {
        let spender = self.vm().msg_sender();
        let current_allowance = self.allowances.get(from).get(spender);

        if current_allowance < value {
            return Err(InsufficientAllowance {
                spender,
                have: current_allowance,
                want: value,
            }
            .abi_encode());
        }

        self.allowances
            .setter(from)
            .setter(spender)
            .set(current_allowance - value);
        self._transfer(from, to, value)?;
        Ok(true)
    }

    /// Internal transfer function
    fn _transfer(&mut self, from: Address, to: Address, value: U256) -> Result<(), Vec<u8>> {
        let from_balance = self.balances.get(from);

        if from_balance < value {
            return Err(InsufficientBalance {
                from,
                have: from_balance,
                want: value,
            }
            .abi_encode());
        }

        self.balances.setter(from).set(from_balance - value);
        let to_balance = self.balances.get(to);
        self.balances.setter(to).set(to_balance + value);

        self.vm().log(Transfer { from, to, value });
        Ok(())
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use stylus_sdk::testing::*;
    use stylus_sdk::alloy_primitives::address;

    #[test]
    fn test_transfer() {
        let vm = TestVM::default();
        let mut contract = Erc20::from(&vm);

        let owner = address!("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266");
        let recipient = address!("0x70997970C51812dc3A010C7d01b50e0d17dc79C8");

        vm.set_sender(owner);
        contract.initialize(
            "Test Token".into(),
            "TEST".into(),
            18,
            U256::from(1000000),
        );

        assert_eq!(contract.balance_of(owner), U256::from(1000000));
        assert!(contract.transfer(recipient, U256::from(1000)).unwrap());
        assert_eq!(contract.balance_of(owner), U256::from(999000));
        assert_eq!(contract.balance_of(recipient), U256::from(1000));
    }
}""",
    cargo_toml='''[package]
name = "stylus_erc20"
version = "0.1.0"
edition = "2021"
license = "MIT OR Apache-2.0"

[dependencies]
stylus-sdk = "0.10.0"
alloy-primitives = "1.0.1"
alloy-sol-types = "1.0.1"

[dev-dependencies]
stylus-sdk = { version = "0.10.0", features = ["stylus-test"] }

[features]
default = ["mini-alloc"]
export-abi = ["stylus-sdk/export-abi"]
debug = ["stylus-sdk/debug"]
mini-alloc = ["stylus-sdk/mini-alloc"]

[lib]
crate-type = ["lib", "cdylib"]

[[bin]]
name = "stylus_erc20"
path = "src/main.rs"

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"''',
    main_rs="""#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]

#[cfg(not(any(test, feature = "export-abi")))]
#[unsafe(no_mangle)]
pub extern "C" fn main() {}

#[cfg(feature = "export-abi")]
fn main() {
    stylus_erc20::print_from_args();
}""",
    stylus_toml="[workspace]\n\n[workspace.networks]\n\n[contract]\n",
    rust_toolchain_toml='[toolchain]\nchannel = "1.91.0"\ntargets = ["wasm32-unknown-unknown"]\n',
)

# Access Control template - Owner-only functions
ACCESS_CONTROL_TEMPLATE = StylusTemplate(
    name="AccessControl",
    description="Contract with owner-only functions and ownership transfer",
    contract_type="utility",
    sdk_version="0.10.0",
    features=["access control", "ownership", "modifiers"],
    lib_rs="""#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]
#[macro_use]
extern crate alloc;

use alloc::{vec, vec::Vec};
use stylus_sdk::{
    alloy_primitives::{Address, U8, U256},
    alloy_sol_types::{sol, SolError},
    prelude::*,
};

sol! {
    event OwnershipTransferred(address indexed previous_owner, address indexed new_owner);
    event ValueUpdated(uint256 old_value, uint256 new_value);

    error NotOwner(address caller, address owner);
    error ZeroAddress();
}

sol_storage! {
    #[entrypoint]
    pub struct Ownable {
        address owner;
        uint256 value;
    }
}

#[public]
impl Ownable {
    /// Initialize with deployer as owner
    pub fn initialize(&mut self) {
        let caller = self.vm().msg_sender();
        self.owner.set(caller);
        self.vm().log(OwnershipTransferred {
            previous_owner: Address::ZERO,
            new_owner: caller,
        });
    }

    /// Get current owner
    pub fn owner(&self) -> Address {
        self.owner.get()
    }

    /// Get stored value
    pub fn value(&self) -> U256 {
        self.value.get()
    }

    /// Update value (owner only)
    pub fn set_value(&mut self, new_value: U256) -> Result<(), Vec<u8>> {
        self.only_owner()?;
        let old_value = self.value.get();
        self.value.set(new_value);
        self.vm().log(ValueUpdated { old_value, new_value });
        Ok(())
    }

    /// Transfer ownership (owner only)
    pub fn transfer_ownership(&mut self, new_owner: Address) -> Result<(), Vec<u8>> {
        self.only_owner()?;

        if new_owner == Address::ZERO {
            return Err(ZeroAddress {}.abi_encode());
        }

        let previous_owner = self.owner.get();
        self.owner.set(new_owner);
        self.vm().log(OwnershipTransferred {
            previous_owner,
            new_owner,
        });
        Ok(())
    }

    /// Renounce ownership (owner only)
    pub fn renounce_ownership(&mut self) -> Result<(), Vec<u8>> {
        self.only_owner()?;
        let previous_owner = self.owner.get();
        self.owner.set(Address::ZERO);
        self.vm().log(OwnershipTransferred {
            previous_owner,
            new_owner: Address::ZERO,
        });
        Ok(())
    }

    /// Internal: Check if caller is owner
    fn only_owner(&self) -> Result<(), Vec<u8>> {
        let caller = self.vm().msg_sender();
        let owner = self.owner.get();
        if caller != owner {
            return Err(NotOwner { caller, owner }.abi_encode());
        }
        Ok(())
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use stylus_sdk::testing::*;
    use stylus_sdk::alloy_primitives::address;

    #[test]
    fn test_ownership() {
        let vm = TestVM::default();
        let mut contract = Ownable::from(&vm);

        let owner = address!("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266");
        let other = address!("0x70997970C51812dc3A010C7d01b50e0d17dc79C8");

        vm.set_sender(owner);
        contract.initialize();
        assert_eq!(contract.owner(), owner);

        // Owner can set value
        assert!(contract.set_value(U256::from(42)).is_ok());
        assert_eq!(contract.value(), U256::from(42));

        // Non-owner cannot set value
        vm.set_sender(other);
        assert!(contract.set_value(U256::from(100)).is_err());

        // Owner can transfer ownership
        vm.set_sender(owner);
        assert!(contract.transfer_ownership(other).is_ok());
        assert_eq!(contract.owner(), other);
    }
}""",
    cargo_toml='''[package]
name = "stylus_ownable"
version = "0.1.0"
edition = "2021"
license = "MIT OR Apache-2.0"

[dependencies]
stylus-sdk = "0.10.0"
alloy-primitives = "1.0.1"
alloy-sol-types = "1.0.1"

[dev-dependencies]
stylus-sdk = { version = "0.10.0", features = ["stylus-test"] }

[features]
default = ["mini-alloc"]
export-abi = ["stylus-sdk/export-abi"]
debug = ["stylus-sdk/debug"]
mini-alloc = ["stylus-sdk/mini-alloc"]

[lib]
crate-type = ["lib", "cdylib"]

[[bin]]
name = "stylus_ownable"
path = "src/main.rs"

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"''',
    main_rs="""#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]

#[cfg(not(any(test, feature = "export-abi")))]
#[unsafe(no_mangle)]
pub extern "C" fn main() {}

#[cfg(feature = "export-abi")]
fn main() {
    stylus_ownable::print_from_args();
}""",
    stylus_toml="[workspace]\n\n[workspace.networks]\n\n[contract]\n",
    rust_toolchain_toml='[toolchain]\nchannel = "1.91.0"\ntargets = ["wasm32-unknown-unknown"]\n',
)

# DeFi Vault template - ETH deposits, withdrawals, cross-contract calls
# Demonstrates ALL advanced SDK 0.10.0 patterns:
# - transfer_eth for ETH withdrawals
# - sol_interface! for cross-contract calls
# - (self.vm(), Call::new(), args) call pattern
# - Events and errors with sol!
# - .get() on all storage reads
DEFI_VAULT_TEMPLATE = StylusTemplate(
    name="DeFiVault",
    description="ETH vault with deposits, withdrawals, oracle price feeds, and access control",
    contract_type="defi",
    sdk_version="0.10.0",
    features=[
        "ETH transfer",
        "cross-contract calls",
        "events",
        "errors",
        "access control",
        "mappings",
    ],
    lib_rs="""#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]
#[macro_use]
extern crate alloc;

use alloc::{vec, vec::Vec};
use stylus_sdk::{
    alloy_primitives::{Address, U256},
    alloy_sol_types::{sol, SolError},
    call::transfer::transfer_eth,
    prelude::*,
};

// Events
sol! {
    event Deposit(address indexed user, uint256 amount);
    event Withdrawal(address indexed user, uint256 amount, address indexed to);
}

// Errors
sol! {
    error InsufficientBalance(address user, uint256 have, uint256 want);
    error Unauthorized(address caller, address owner);
}

#[derive(SolidityError)]
pub enum VaultError {
    InsufficientBalance(InsufficientBalance),
    Unauthorized(Unauthorized),
}

// Cross-contract interfaces — use sol_interface! (NOT sol!) for external calls
sol_interface! {
    interface IPriceFeed {
        function latestPrice() external view returns (uint256);
    }
    interface IToken {
        function transfer(address to, uint256 amount) external returns (bool);
    }
}

sol_storage! {
    #[entrypoint]
    pub struct Vault {
        address owner;
        mapping(address => uint256) balances;
        uint256 total_deposits;
        address price_feed;
    }
}

#[public]
impl Vault {
    /// Initialize the vault with an owner and price feed address
    pub fn initialize(&mut self, price_feed: Address) {
        self.owner.set(self.vm().msg_sender());
        self.price_feed.set(price_feed);
    }

    /// Deposit ETH into the vault
    #[payable]
    pub fn deposit(&mut self) -> Result<(), Vec<u8>> {
        let sender = self.vm().msg_sender();
        let amount = self.vm().msg_value();

        // Read current balance with .get(), then write with .setter().set()
        let current = self.balances.get(sender);
        self.balances.setter(sender).set(current + amount);

        let total = self.total_deposits.get();
        self.total_deposits.set(total + amount);

        self.vm().log(Deposit {
            user: sender,
            amount,
        });
        Ok(())
    }

    /// Withdraw ETH from the vault — uses transfer_eth(self.vm(), to, amount)
    pub fn withdraw(&mut self, amount: U256, to: Address) -> Result<(), Vec<u8>> {
        let sender = self.vm().msg_sender();
        let balance = self.balances.get(sender);

        if balance < amount {
            return Err(InsufficientBalance {
                user: sender,
                have: balance,
                want: amount,
            }
            .abi_encode());
        }

        self.balances.setter(sender).set(balance - amount);
        let total = self.total_deposits.get();
        self.total_deposits.set(total - amount);

        // transfer_eth requires self.vm() as first arg (Host context)
        transfer_eth(self.vm(), to, amount)?;

        self.vm().log(Withdrawal {
            user: sender,
            amount,
            to,
        });
        Ok(())
    }

    /// Read price from external oracle — VIEW call uses Call::new()
    pub fn get_price(&mut self) -> Result<U256, Vec<u8>> {
        let feed_addr = self.price_feed.get();
        let feed = IPriceFeed::new(feed_addr);
        // VIEW (read-only) cross-contract call: Call::new() is fine
        let price = feed.latest_price(self.vm(), Call::new())?;
        Ok(price)
    }

    /// Transfer tokens via external contract (state-modifying)
    pub fn transfer_tokens(
        &mut self,
        token: Address,
        to: Address,
        amount: U256,
    ) -> Result<bool, Vec<u8>> {
        let tok = IToken::new(token);
        // State-modifying call: extract Call first to avoid borrow conflict
        let call = Call::new_mutating(self);
        let success = tok.transfer(self.vm(), call, to, amount)?;
        Ok(success)
    }

    /// Get balance for a user
    pub fn balance_of(&self, user: Address) -> U256 {
        self.balances.get(user)
    }

    /// Get total deposits
    pub fn total_deposits(&self) -> U256 {
        self.total_deposits.get()
    }

    /// Get vault owner
    pub fn owner(&self) -> Address {
        self.owner.get()
    }

    /// Owner-only withdrawal
    pub fn owner_withdraw(&mut self, amount: U256, to: Address) -> Result<(), Vec<u8>> {
        let caller = self.vm().msg_sender();
        let owner = self.owner.get();
        if caller != owner {
            return Err(Unauthorized { caller, owner }.abi_encode());
        }
        transfer_eth(self.vm(), to, amount)?;
        Ok(())
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use stylus_sdk::testing::*;
    use stylus_sdk::alloy_primitives::address;

    #[test]
    fn test_deposit_and_balance() {
        let vm = TestVM::default();
        let mut contract = Vault::from(&vm);

        let user = address!("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266");

        vm.set_sender(user);
        vm.set_value(U256::from(1000));
        assert!(contract.deposit().is_ok());
        assert_eq!(contract.balance_of(user), U256::from(1000));
        assert_eq!(contract.total_deposits(), U256::from(1000));
    }
}""",
    cargo_toml='''[package]
name = "stylus_vault"
version = "0.1.0"
edition = "2021"
license = "MIT OR Apache-2.0"

[dependencies]
stylus-sdk = "0.10.0"
alloy-primitives = "1.0.1"
alloy-sol-types = "1.0.1"

[dev-dependencies]
stylus-sdk = { version = "0.10.0", features = ["stylus-test"] }

[features]
default = ["mini-alloc"]
export-abi = ["stylus-sdk/export-abi"]
debug = ["stylus-sdk/debug"]
mini-alloc = ["stylus-sdk/mini-alloc"]

[lib]
crate-type = ["lib", "cdylib"]

[[bin]]
name = "stylus_vault"
path = "src/main.rs"

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"''',
    main_rs="""#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]

#[cfg(not(any(test, feature = "export-abi")))]
#[unsafe(no_mangle)]
pub extern "C" fn main() {}

#[cfg(feature = "export-abi")]
fn main() {
    stylus_vault::print_from_args();
}""",
    stylus_toml="[workspace]\n\n[workspace.networks]\n\n[contract]\n",
    rust_toolchain_toml='[toolchain]\nchannel = "1.91.0"\ntargets = ["wasm32-unknown-unknown"]\n',
)

# Staking Rewards template — ETH staking with time-based rewards
# Focused template for staking prompts (smaller than DeFiVault, no sol_interface!)
# Demonstrates: #[payable], transfer_eth, block_timestamp, mapping patterns, events, errors
STAKING_REWARDS_TEMPLATE = StylusTemplate(
    name="StakingRewards",
    description="ETH staking with time-based rewards, stake/unstake/claim",
    contract_type="defi",
    sdk_version="0.10.0",
    features=["ETH transfer", "staking", "rewards", "events", "errors", "mappings", "block timestamp"],
    lib_rs="""#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]
#[macro_use]
extern crate alloc;

use alloc::{vec, vec::Vec};
use stylus_sdk::{
    alloy_primitives::{Address, U256},
    alloy_sol_types::{sol, SolError},
    call::transfer::transfer_eth,
    prelude::*,
};

// Events
sol! {
    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount);
    event RewardClaimed(address indexed user, uint256 reward);
}

// Errors
sol! {
    error InsufficientStake(uint256 available, uint256 requested);
    error ZeroAmount();
}

#[derive(SolidityError)]
pub enum StakingError {
    InsufficientStake(InsufficientStake),
    ZeroAmount(ZeroAmount),
}

sol_storage! {
    #[entrypoint]
    pub struct StakingRewards {
        address owner;
        mapping(address => uint256) staked_balances;
        mapping(address => uint256) rewards;
        mapping(address => uint256) last_update_time;
        uint256 total_staked;
        uint256 reward_rate;
    }
}

#[public]
impl StakingRewards {
    /// Initialize with owner and reward rate
    pub fn initialize(&mut self, rate: U256) {
        self.owner.set(self.vm().msg_sender());
        self.reward_rate.set(rate);
    }

    /// Stake ETH — payable function
    #[payable]
    pub fn stake(&mut self) -> Result<(), Vec<u8>> {
        let amount = self.vm().msg_value();
        if amount == U256::ZERO {
            return Err(ZeroAmount {}.abi_encode());
        }

        let caller = self.vm().msg_sender();
        self.update_rewards(caller);

        let current = self.staked_balances.get(caller);
        self.staked_balances.setter(caller).set(current + amount);

        let total = self.total_staked.get();
        self.total_staked.set(total + amount);

        self.vm().log(Staked { user: caller, amount });
        Ok(())
    }

    /// Unstake ETH — uses transfer_eth(self.vm(), to, amount)
    pub fn unstake(&mut self, amount: U256) -> Result<(), Vec<u8>> {
        let caller = self.vm().msg_sender();
        let staked = self.staked_balances.get(caller);
        if staked < amount {
            return Err(InsufficientStake {
                available: staked,
                requested: amount,
            }
            .abi_encode());
        }

        self.update_rewards(caller);

        self.staked_balances.setter(caller).set(staked - amount);
        let total = self.total_staked.get();
        self.total_staked.set(total - amount);

        // transfer_eth requires self.vm() as first arg
        transfer_eth(self.vm(), caller, amount)?;

        self.vm().log(Unstaked { user: caller, amount });
        Ok(())
    }

    /// Claim accumulated rewards
    pub fn claim_rewards(&mut self) -> Result<(), Vec<u8>> {
        let caller = self.vm().msg_sender();
        self.update_rewards(caller);

        let reward = self.rewards.get(caller);
        if reward == U256::ZERO {
            return Err(ZeroAmount {}.abi_encode());
        }

        self.rewards.setter(caller).set(U256::ZERO);
        transfer_eth(self.vm(), caller, reward)?;

        self.vm().log(RewardClaimed { user: caller, reward });
        Ok(())
    }

    /// View staked balance
    pub fn staked_balance_of(&self, account: Address) -> U256 {
        self.staked_balances.get(account)
    }

    /// View pending rewards
    pub fn pending_rewards(&self, account: Address) -> U256 {
        self.rewards.get(account)
    }

    /// View total staked
    pub fn total_staked(&self) -> U256 {
        self.total_staked.get()
    }
}

/// Internal helpers — outside #[public] to avoid ABI exposure
impl StakingRewards {
    fn update_rewards(&mut self, account: Address) {
        let staked = self.staked_balances.get(account);
        if staked > U256::ZERO {
            let now = U256::from(self.vm().block_timestamp());
            let last = self.last_update_time.get(account);
            if last > U256::ZERO {
                let elapsed = now - last;
                let rate = self.reward_rate.get();
                let new_reward = staked * elapsed * rate / U256::from(1_000_000);
                let current = self.rewards.get(account);
                self.rewards.setter(account).set(current + new_reward);
            }
        }
        let now = U256::from(self.vm().block_timestamp());
        self.last_update_time.setter(account).set(now);
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use stylus_sdk::testing::*;
    use stylus_sdk::alloy_primitives::address;

    #[test]
    fn test_stake_and_balance() {
        let vm = TestVM::default();
        let mut contract = StakingRewards::from(&vm);

        let user = address!("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266");

        vm.set_sender(user);
        contract.initialize(U256::from(100));

        vm.set_value(U256::from(1000));
        assert!(contract.stake().is_ok());
        assert_eq!(contract.staked_balance_of(user), U256::from(1000));
        assert_eq!(contract.total_staked(), U256::from(1000));
    }
}""",
    cargo_toml="""[package]
name = "stylus_staking"
version = "0.1.0"
edition = "2021"
license = "MIT OR Apache-2.0"

[dependencies]
stylus-sdk = "0.10.0"
alloy-primitives = "1.0.1"
alloy-sol-types = "1.0.1"
[dev-dependencies]
stylus-sdk = { version = "0.10.0", features = ["stylus-test"] }

[features]
default = ["mini-alloc"]
export-abi = ["stylus-sdk/export-abi"]
debug = ["stylus-sdk/debug"]
mini-alloc = ["stylus-sdk/mini-alloc"]

[lib]
crate-type = ["lib", "cdylib"]

[[bin]]
name = "stylus_staking"
path = "src/main.rs"

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s\"""",
    main_rs="""#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]

#[cfg(not(any(test, feature = "export-abi")))]
#[unsafe(no_mangle)]
pub extern "C" fn main() {}

#[cfg(feature = "export-abi")]
fn main() {
    stylus_staking::print_from_args();
}""",
    stylus_toml="[workspace]\n\n[workspace.networks]\n\n[contract]\n",
    rust_toolchain_toml='[toolchain]\nchannel = "1.91.0"\ntargets = ["wasm32-unknown-unknown"]\n',
)

# NFT Registry template - Dynamic arrays and mappings
# Demonstrates push() for StorageVec, sol! events with camelCase fields
NFT_REGISTRY_TEMPLATE = StylusTemplate(
    name="NftRegistry",
    description="NFT registry with minting, ownership tracking, and dynamic token ID array",
    contract_type="nft",
    sdk_version="0.10.0",
    features=["dynamic arrays", "mappings", "events", "access control", "mint"],
    lib_rs="""#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]
#[macro_use]
extern crate alloc;

use alloc::{vec, vec::Vec};
use stylus_sdk::{
    alloy_primitives::{Address, U256},
    alloy_sol_types::{sol, SolError},
    prelude::*,
};

// Events — use camelCase for field names (Solidity convention)
sol! {
    event Transfer(address indexed from, address indexed to, uint256 tokenId);
    event Approval(address indexed owner, address indexed approved, uint256 tokenId);
}

// Errors
sol! {
    error TokenNotFound(uint256 tokenId);
    error NotOwner(address caller, address owner);
    error AlreadyMinted(uint256 tokenId);
    error ZeroAddress();
}

#[derive(SolidityError)]
pub enum NftError {
    TokenNotFound(TokenNotFound),
    NotOwner(NotOwner),
    AlreadyMinted(AlreadyMinted),
    ZeroAddress(ZeroAddress),
}

sol_storage! {
    #[entrypoint]
    pub struct NftRegistry {
        address contract_owner;
        uint256 next_token_id;
        mapping(uint256 => address) owners;
        mapping(address => uint256) balances;
        mapping(uint256 => address) token_approvals;
        uint256[] all_token_ids;
    }
}

#[public]
impl NftRegistry {
    /// Initialize the registry with deployer as contract owner
    pub fn initialize(&mut self) {
        self.contract_owner.set(self.vm().msg_sender());
    }

    /// Mint a new NFT to the given address
    pub fn mint(&mut self, to: Address) -> Result<U256, Vec<u8>> {
        if to == Address::ZERO {
            return Err(ZeroAddress {}.abi_encode());
        }

        // Get and increment token ID
        let token_id = self.next_token_id.get();
        self.next_token_id.set(token_id + U256::from(1));

        // Set ownership
        self.owners.setter(token_id).set(to);

        // Update balance
        let balance = self.balances.get(to);
        self.balances.setter(to).set(balance + U256::from(1));

        // Track token ID in dynamic array — use push() for primitives
        self.all_token_ids.push(token_id);

        self.vm().log(Transfer {
            from: Address::ZERO,
            to,
            tokenId: token_id,
        });

        Ok(token_id)
    }

    /// Transfer NFT from one address to another
    pub fn transfer_from(
        &mut self,
        from: Address,
        to: Address,
        token_id: U256,
    ) -> Result<(), Vec<u8>> {
        let token_owner = self.owners.get(token_id);
        if token_owner == Address::ZERO {
            return Err(TokenNotFound { tokenId: token_id }.abi_encode());
        }

        let caller = self.vm().msg_sender();
        let approved = self.token_approvals.get(token_id);
        if caller != token_owner && caller != approved {
            return Err(NotOwner {
                caller,
                owner: token_owner,
            }
            .abi_encode());
        }

        if to == Address::ZERO {
            return Err(ZeroAddress {}.abi_encode());
        }

        // Update ownership
        self.owners.setter(token_id).set(to);

        // Update balances
        let from_balance = self.balances.get(from);
        self.balances.setter(from).set(from_balance - U256::from(1));
        let to_balance = self.balances.get(to);
        self.balances.setter(to).set(to_balance + U256::from(1));

        // Clear approval
        self.token_approvals.setter(token_id).set(Address::ZERO);

        self.vm().log(Transfer {
            from,
            to,
            tokenId: token_id,
        });

        Ok(())
    }

    /// Approve another address to transfer a specific token
    pub fn approve(&mut self, to: Address, token_id: U256) -> Result<(), Vec<u8>> {
        let token_owner = self.owners.get(token_id);
        if token_owner == Address::ZERO {
            return Err(TokenNotFound { tokenId: token_id }.abi_encode());
        }

        let caller = self.vm().msg_sender();
        if caller != token_owner {
            return Err(NotOwner {
                caller,
                owner: token_owner,
            }
            .abi_encode());
        }

        self.token_approvals.setter(token_id).set(to);
        self.vm().log(Approval {
            owner: token_owner,
            approved: to,
            tokenId: token_id,
        });

        Ok(())
    }

    /// Get the owner of a token
    pub fn owner_of(&self, token_id: U256) -> Address {
        self.owners.get(token_id)
    }

    /// Get token balance for an address
    pub fn balance_of(&self, owner: Address) -> U256 {
        self.balances.get(owner)
    }

    /// Get total number of minted tokens
    pub fn total_supply(&self) -> U256 {
        self.next_token_id.get()
    }

    /// Get token ID at a specific index in the all_token_ids array
    pub fn token_by_index(&self, index: U256) -> U256 {
        self.all_token_ids.get(index).unwrap_or_default()
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use stylus_sdk::testing::*;
    use stylus_sdk::alloy_primitives::address;

    #[test]
    fn test_mint_and_transfer() {
        let vm = TestVM::default();
        let mut contract = NftRegistry::from(&vm);

        let owner = address!("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266");
        let recipient = address!("0x70997970C51812dc3A010C7d01b50e0d17dc79C8");

        vm.set_sender(owner);
        contract.initialize();

        // Mint first token
        let token_id = contract.mint(owner).unwrap();
        assert_eq!(token_id, U256::ZERO);
        assert_eq!(contract.owner_of(U256::ZERO), owner);
        assert_eq!(contract.balance_of(owner), U256::from(1));
        assert_eq!(contract.total_supply(), U256::from(1));

        // Check dynamic array tracking
        assert_eq!(contract.token_by_index(U256::ZERO), U256::ZERO);

        // Mint second token
        let token_id_2 = contract.mint(owner).unwrap();
        assert_eq!(token_id_2, U256::from(1));
        assert_eq!(contract.balance_of(owner), U256::from(2));

        // Transfer token 0 to recipient
        assert!(contract
            .transfer_from(owner, recipient, U256::ZERO)
            .is_ok());
        assert_eq!(contract.owner_of(U256::ZERO), recipient);
        assert_eq!(contract.balance_of(owner), U256::from(1));
        assert_eq!(contract.balance_of(recipient), U256::from(1));
    }

    #[test]
    fn test_approve_and_transfer() {
        let vm = TestVM::default();
        let mut contract = NftRegistry::from(&vm);

        let owner = address!("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266");
        let approved = address!("0x70997970C51812dc3A010C7d01b50e0d17dc79C8");

        vm.set_sender(owner);
        contract.initialize();

        // Mint and approve
        contract.mint(owner).unwrap();
        assert!(contract.approve(approved, U256::ZERO).is_ok());

        // Approved address can transfer
        vm.set_sender(approved);
        assert!(contract
            .transfer_from(owner, approved, U256::ZERO)
            .is_ok());
        assert_eq!(contract.owner_of(U256::ZERO), approved);
    }
}""",
    cargo_toml='''[package]
name = "stylus_nft_registry"
version = "0.1.0"
edition = "2021"
license = "MIT OR Apache-2.0"

[dependencies]
stylus-sdk = "0.10.0"
alloy-primitives = "1.0.1"
alloy-sol-types = "1.0.1"

[dev-dependencies]
stylus-sdk = { version = "0.10.0", features = ["stylus-test"] }

[features]
default = ["mini-alloc"]
export-abi = ["stylus-sdk/export-abi"]
debug = ["stylus-sdk/debug"]
mini-alloc = ["stylus-sdk/mini-alloc"]

[lib]
crate-type = ["lib", "cdylib"]

[[bin]]
name = "stylus_nft_registry"
path = "src/main.rs"

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"''',
    main_rs="""#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]

#[cfg(not(any(test, feature = "export-abi")))]
#[unsafe(no_mangle)]
pub extern "C" fn main() {}

#[cfg(feature = "export-abi")]
fn main() {
    stylus_nft_registry::print_from_args();
}""",
    stylus_toml="[workspace]\n\n[workspace.networks]\n\n[contract]\n",
    rust_toolchain_toml='[toolchain]\nchannel = "1.91.0"\ntargets = ["wasm32-unknown-unknown"]\n',
)

# All available templates indexed by contract type
TEMPLATES = {
    "counter": COUNTER_TEMPLATE,
    "utility": COUNTER_TEMPLATE,
    "vending_machine": VENDING_MACHINE_TEMPLATE,
    "vault": DEFI_VAULT_TEMPLATE,
    "defi": DEFI_VAULT_TEMPLATE,
    "staking": STAKING_REWARDS_TEMPLATE,
    "token": SIMPLE_ERC20_TEMPLATE,
    "erc20": SIMPLE_ERC20_TEMPLATE,
    "access_control": ACCESS_CONTROL_TEMPLATE,
    "ownable": ACCESS_CONTROL_TEMPLATE,
    "nft": NFT_REGISTRY_TEMPLATE,
    "erc721": NFT_REGISTRY_TEMPLATE,
    "registry": NFT_REGISTRY_TEMPLATE,
}


def adapt_template(template: StylusTemplate, target_version: str) -> StylusTemplate:
    """Adapt a template to a different SDK version.

    For 0.10.x targets: returns template as-is (templates are already 0.10.0).
    For 0.9.x targets: reverse-transforms lib_rs, adjusts Cargo.toml deps,
    clears 0.10-only files (main_rs, stylus_toml, rust_toolchain_toml),
    adds back evm/msg imports.

    Args:
        template: Source template (always 0.10.0).
        target_version: Target SDK version (e.g., "0.9.0", "0.10.0").

    Returns:
        Adapted StylusTemplate (new object if changed, same object if no change).
    """
    # Import version_manager lazily to avoid circular imports
    try:
        from src.utils.version_manager import (
            _to_major_minor,
            apply_version_transforms,
            get_cargo_deps_for_version,
            is_at_least_010,
        )
    except ImportError:
        return template

    target_mm = _to_major_minor(target_version)
    template_mm = _to_major_minor(template.sdk_version)

    # No adaptation needed if same major.minor
    if target_mm == template_mm:
        return template

    # Apply reverse transforms to lib.rs (0.10.0 → 0.9.x)
    adapted_lib_rs = apply_version_transforms(template.lib_rs, template.sdk_version, target_version)

    # Get dependency versions for target
    deps = get_cargo_deps_for_version(target_version)

    # Adapt Cargo.toml
    adapted_cargo = template.cargo_toml
    adapted_cargo = re.sub(
        r'stylus-sdk = "([^"]+)"',
        f'stylus-sdk = "{deps["stylus_sdk"]}"',
        adapted_cargo,
    )
    adapted_cargo = re.sub(
        r'(stylus-sdk = \{{ version = )"([^"]+)"',
        rf'\1"{deps["stylus_sdk"]}"',
        adapted_cargo,
    )
    adapted_cargo = re.sub(
        r'alloy-primitives = "([^"]+)"',
        f'alloy-primitives = "{deps["alloy_primitives"]}"',
        adapted_cargo,
    )
    adapted_cargo = re.sub(
        r'alloy-sol-types = "([^"]+)"',
        f'alloy-sol-types = "{deps["alloy_sol_types"]}"',
        adapted_cargo,
    )

    # Adjust crate-type for 0.9.x (only cdylib, no lib)
    crate_type_str = json.dumps(deps["crate_type"])
    adapted_cargo = re.sub(
        r"crate-type = \[.*?\]",
        f"crate-type = {crate_type_str}",
        adapted_cargo,
    )

    # For 0.9.x: remove [[bin]] section and dev-dependencies stylus-test feature
    is_pre_010 = not is_at_least_010(target_version)
    if is_pre_010:
        # Remove [[bin]] section
        adapted_cargo = re.sub(
            r'\[\[bin\]\]\n.*?path = "src/main\.rs"\n\n?',
            "",
            adapted_cargo,
            flags=re.DOTALL,
        )

    # Build adapted template
    return StylusTemplate(
        name=template.name,
        description=template.description,
        contract_type=template.contract_type,
        sdk_version=target_version,
        features=template.features,
        lib_rs=adapted_lib_rs,
        cargo_toml=adapted_cargo,
        # 0.9.x doesn't need main_rs, stylus_toml, rust_toolchain_toml
        main_rs="" if is_pre_010 else template.main_rs,
        stylus_toml="" if is_pre_010 else template.stylus_toml,
        rust_toolchain_toml="" if is_pre_010 else template.rust_toolchain_toml,
    )


def select_template(
    contract_type: str, prompt: str, target_version: Optional[str] = None
) -> StylusTemplate:
    """Select the best template based on contract type, prompt keywords, and target version.

    Args:
        contract_type: Type of contract (token, defi, utility, custom).
        prompt: User's description of the contract.
        target_version: Target SDK version. If not 0.10.x, template is adapted.

    Returns:
        Best-matching StylusTemplate, adapted to target_version if needed.
    """
    lower_prompt = prompt.lower()

    # Check for specific keywords in prompt
    # ERC20 explicit match FIRST — "erc20" is unambiguous
    if "erc20" in lower_prompt or "erc-20" in lower_prompt:
        template = SIMPLE_ERC20_TEMPLATE
    # NFT keywords — "mint" alone is ambiguous (ERC20 also mints),
    # so only match when combined with NFT-specific terms
    elif any(
        kw in lower_prompt
        for kw in ["nft", "erc721", "erc-721", "token id", "collectible",
                    "nft registry"]
    ) or ("mint" in lower_prompt and "token" not in lower_prompt):
        template = NFT_REGISTRY_TEMPLATE
    elif any(kw in lower_prompt for kw in ["token", "transfer", "balance"]):
        template = SIMPLE_ERC20_TEMPLATE
    elif any(kw in lower_prompt for kw in ["owner", "admin", "access control", "permission"]):
        template = ACCESS_CONTROL_TEMPLATE
    elif any(kw in lower_prompt for kw in ["vending", "claim", "cooldown", "rate limit"]):
        template = VENDING_MACHINE_TEMPLATE
    elif any(kw in lower_prompt for kw in ["stake", "staking", "unstake", "reward"]):
        template = STAKING_REWARDS_TEMPLATE
    elif any(
        kw in lower_prompt
        for kw in [
            "vault",
            "deposit",
            "withdraw",
            "swap",
            "pool",
            "liquidity",
            "oracle",
            "price",
            "feed",
            "prediction",
            "market",
            "bet",
            "wager",
            "auction",
            "lending",
            "borrow",
            "collateral",
            "bridge",
        ]
    ):
        template = DEFI_VAULT_TEMPLATE
    else:
        # Fall back to contract type
        template = TEMPLATES.get(contract_type, COUNTER_TEMPLATE)

    # Adapt to target version if specified and different from template's version
    if target_version:
        template = adapt_template(template, target_version)

    return template


def get_template(contract_type: str) -> Optional[StylusTemplate]:
    """Get template for specific contract type."""
    return TEMPLATES.get(contract_type)


def list_templates() -> List[StylusTemplate]:
    """List all available templates."""
    return [
        COUNTER_TEMPLATE,
        VENDING_MACHINE_TEMPLATE,
        DEFI_VAULT_TEMPLATE,
        STAKING_REWARDS_TEMPLATE,
        SIMPLE_ERC20_TEMPLATE,
        ACCESS_CONTROL_TEMPLATE,
        NFT_REGISTRY_TEMPLATE,
    ]

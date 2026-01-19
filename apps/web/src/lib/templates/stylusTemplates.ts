/**
 * Curated working templates from official Stylus examples.
 * These templates are verified to compile and deploy correctly.
 *
 * Sources:
 * - Counter: https://github.com/OffchainLabs/stylus-hello-world (v0.9.0)
 * - VendingMachine: https://github.com/OffchainLabs/stylus-quickstart-vending-machine (v0.8.4)
 * - ERC20: https://github.com/OpenZeppelin/rust-contracts-stylus (v0.9.0)
 */

export interface StylusTemplate {
  name: string;
  description: string;
  contractType: "token" | "nft" | "defi" | "utility" | "custom";
  sdkVersion: string;
  libRs: string;
  cargoToml: string;
  features: string[];
}

/**
 * Counter template - Simple storage pattern
 * From: stylus-hello-world (v0.9.0)
 */
export const COUNTER_TEMPLATE: StylusTemplate = {
  name: "Counter",
  description: "Simple counter with increment, add, multiply operations",
  contractType: "utility",
  sdkVersion: "0.9.0",
  features: ["storage", "public functions", "payable", "tests"],
  libRs: `#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]
#[macro_use]
extern crate alloc;

use alloc::vec::Vec;
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
}`,
  cargoToml: `[package]
name = "stylus-counter"
version = "0.1.0"
edition = "2021"
license = "MIT OR Apache-2.0"

[dependencies]
stylus-sdk = "0.9.0"
alloy-primitives = "=0.8.20"
alloy-sol-types = "=0.8.20"
ruint = "=1.15.0"
[dev-dependencies]
tokio = { version = "1.21.0", features = ["full"] }
ethers = "2.0"

[features]
default = ["mini-alloc"]
export-abi = ["stylus-sdk/export-abi"]
debug = ["stylus-sdk/debug"]
mini-alloc = ["stylus-sdk/mini-alloc"]

[lib]
crate-type = ["lib", "cdylib"]

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"`,
};

/**
 * Vending Machine template - Mappings and time-based logic
 * From: stylus-quickstart-vending-machine (v0.8.4)
 */
export const VENDING_MACHINE_TEMPLATE: StylusTemplate = {
  name: "VendingMachine",
  description: "Mapping storage with time-based distribution logic",
  contractType: "defi",
  sdkVersion: "0.9.0", // Updated to 0.9.0 patterns
  features: ["mappings", "timestamps", "rate limiting", "tests"],
  libRs: `#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]
#[macro_use]
extern crate alloc;

use alloc::vec::Vec;
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
}`,
  cargoToml: `[package]
name = "stylus-vending-machine"
version = "0.1.0"
edition = "2021"
license = "MIT OR Apache-2.0"

[dependencies]
stylus-sdk = "0.9.0"
alloy-primitives = "=0.8.20"
alloy-sol-types = "=0.8.20"
ruint = "=1.15.0"
[dev-dependencies]
tokio = { version = "1.21.0", features = ["full"] }
ethers = "2.0"

[features]
default = ["mini-alloc"]
export-abi = ["stylus-sdk/export-abi"]
debug = ["stylus-sdk/debug"]
mini-alloc = ["stylus-sdk/mini-alloc"]

[lib]
crate-type = ["lib", "cdylib"]

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"`,
};

/**
 * Simple ERC20 template - Basic token without OpenZeppelin
 * This is a simplified version that doesn't require external libraries
 */
export const SIMPLE_ERC20_TEMPLATE: StylusTemplate = {
  name: "SimpleERC20",
  description: "Basic ERC20 token with transfer, approve, transferFrom",
  contractType: "token",
  sdkVersion: "0.9.0",
  features: ["ERC20", "mappings", "events", "error handling"],
  libRs: `#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]
#[macro_use]
extern crate alloc;

use alloc::{string::String, vec::Vec};
use stylus_sdk::{
    alloy_primitives::{Address, U8, U256},
    alloy_sol_types::{sol, SolError},
    evm, msg,
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
        self.balances.setter(msg::sender()).set(initial_supply);
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
        let from = msg::sender();
        self._transfer(from, to, value)?;
        Ok(true)
    }

    /// Get allowance
    pub fn allowance(&self, owner: Address, spender: Address) -> U256 {
        self.allowances.get(owner).get(spender)
    }

    /// Approve spender to spend tokens
    pub fn approve(&mut self, spender: Address, value: U256) -> bool {
        let owner = msg::sender();
        self.allowances.setter(owner).setter(spender).set(value);
        evm::log(Approval { owner, spender, value });
        true
    }

    /// Transfer tokens from one address to another (requires allowance)
    pub fn transfer_from(
        &mut self,
        from: Address,
        to: Address,
        value: U256,
    ) -> Result<bool, Vec<u8>> {
        let spender = msg::sender();
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

        evm::log(Transfer { from, to, value });
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
}`,
  cargoToml: `[package]
name = "stylus-erc20"
version = "0.1.0"
edition = "2021"
license = "MIT OR Apache-2.0"

[dependencies]
stylus-sdk = "0.9.0"
alloy-primitives = "=0.8.20"
alloy-sol-types = "=0.8.20"
ruint = "=1.15.0"
[dev-dependencies]
tokio = { version = "1.21.0", features = ["full"] }
ethers = "2.0"

[features]
default = ["mini-alloc"]
export-abi = ["stylus-sdk/export-abi"]
debug = ["stylus-sdk/debug"]
mini-alloc = ["stylus-sdk/mini-alloc"]

[lib]
crate-type = ["lib", "cdylib"]

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"`,
};

/**
 * Access Control template - Owner-only functions
 */
export const ACCESS_CONTROL_TEMPLATE: StylusTemplate = {
  name: "AccessControl",
  description: "Contract with owner-only functions and ownership transfer",
  contractType: "utility",
  sdkVersion: "0.9.0",
  features: ["access control", "ownership", "modifiers"],
  libRs: `#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]
#[macro_use]
extern crate alloc;

use alloc::vec::Vec;
use stylus_sdk::{
    alloy_primitives::{Address, U8, U256},
    alloy_sol_types::{sol, SolError},
    evm, msg,
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
        let caller = msg::sender();
        self.owner.set(caller);
        evm::log(OwnershipTransferred {
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
        evm::log(ValueUpdated { old_value, new_value });
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
        evm::log(OwnershipTransferred {
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
        evm::log(OwnershipTransferred {
            previous_owner,
            new_owner: Address::ZERO,
        });
        Ok(())
    }

    /// Internal: Check if caller is owner
    fn only_owner(&self) -> Result<(), Vec<u8>> {
        let caller = msg::sender();
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
}`,
  cargoToml: `[package]
name = "stylus-ownable"
version = "0.1.0"
edition = "2021"
license = "MIT OR Apache-2.0"

[dependencies]
stylus-sdk = "0.9.0"
alloy-primitives = "=0.8.20"
alloy-sol-types = "=0.8.20"
ruint = "=1.15.0"
[dev-dependencies]
tokio = { version = "1.21.0", features = ["full"] }
ethers = "2.0"

[features]
default = ["mini-alloc"]
export-abi = ["stylus-sdk/export-abi"]
debug = ["stylus-sdk/debug"]
mini-alloc = ["stylus-sdk/mini-alloc"]

[lib]
crate-type = ["lib", "cdylib"]

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"`,
};

/**
 * All available templates indexed by contract type
 */
export const TEMPLATES: Record<string, StylusTemplate> = {
  counter: COUNTER_TEMPLATE,
  utility: COUNTER_TEMPLATE,
  vending_machine: VENDING_MACHINE_TEMPLATE,
  defi: VENDING_MACHINE_TEMPLATE,
  token: SIMPLE_ERC20_TEMPLATE,
  erc20: SIMPLE_ERC20_TEMPLATE,
  access_control: ACCESS_CONTROL_TEMPLATE,
  ownable: ACCESS_CONTROL_TEMPLATE,
};

/**
 * Select the best template based on contract type and prompt
 */
export function selectTemplate(
  contractType: string,
  prompt: string
): StylusTemplate {
  const lowerPrompt = prompt.toLowerCase();

  // Check for specific keywords in prompt
  if (
    lowerPrompt.includes("erc20") ||
    lowerPrompt.includes("token") ||
    lowerPrompt.includes("transfer") ||
    lowerPrompt.includes("balance")
  ) {
    return SIMPLE_ERC20_TEMPLATE;
  }

  if (
    lowerPrompt.includes("owner") ||
    lowerPrompt.includes("admin") ||
    lowerPrompt.includes("access control") ||
    lowerPrompt.includes("permission")
  ) {
    return ACCESS_CONTROL_TEMPLATE;
  }

  if (
    lowerPrompt.includes("vending") ||
    lowerPrompt.includes("claim") ||
    lowerPrompt.includes("cooldown") ||
    lowerPrompt.includes("rate limit")
  ) {
    return VENDING_MACHINE_TEMPLATE;
  }

  // Fall back to contract type
  return TEMPLATES[contractType] || COUNTER_TEMPLATE;
}

/**
 * Get template for specific contract type
 */
export function getTemplate(contractType: string): StylusTemplate | undefined {
  return TEMPLATES[contractType];
}

/**
 * List all available templates
 */
export function listTemplates(): StylusTemplate[] {
  return [
    COUNTER_TEMPLATE,
    VENDING_MACHINE_TEMPLATE,
    SIMPLE_ERC20_TEMPLATE,
    ACCESS_CONTROL_TEMPLATE,
  ];
}

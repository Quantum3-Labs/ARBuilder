// Allow `cargo stylus export-abi` to generate a main function.
#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]

#[macro_use]
extern crate alloc;

use alloc::vec::Vec;

use alloy_primitives::{Address, U256, FixedBytes};
use alloy_sol_types::sol;
/// Import items from the SDK. The prelude contains common traits and macros.
use stylus_sdk::prelude::*;

// Define some persistent storage using the Solidity ABI.
// `Counter` will be the entrypoint.
sol_storage! {
    #[entrypoint]
    pub struct ERC6909 {
      address owner;
      bytes32 name;
      bytes32 symbol;
      uint8 decimals;
      mapping(address => mapping(uint256 => uint256)) _balance;
      mapping(address => mapping(address => bool)) _operator_approvals;
      mapping(address => mapping(address => mapping(uint256 => uint256))) _allowances;
    }
}

sol! {
    #[derive(Debug)]
    error ERC6909InsufficientBalance(address sender, uint256 balance, uint256 needed, uint256 id);

    #[derive(Debug)]
    error ERC6909InvalidSender(address sender);

    #[derive(Debug)]
    error ERC6909InvalidReceiver(address reciver);

    #[derive(Debug)]
    error ERC6909InvalidApprover(address approver);
    #[derive(Debug)]
    error ERC6909InvalidSpender(address spender);

    #[derive(Debug)]
    error ERC6909InsufficientAllowance(address owner, uint256 allowance, uint256 needed, uint256 id);

    event Transfer(address indexed from, address indexed to, uint256 indexed id, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 indexed id, uint256 value);
    event OperatorSet(address indexed owner, address indexed sender, bool approved);

}

// Define the Rust-equivalent of the Solidity errors
#[derive(SolidityError, Debug)]
pub enum ERC6909Error {
    ERC6909InsufficientBalance(ERC6909InsufficientBalance),
    ERC6909InvalidSender(ERC6909InvalidSender),
    ERC6909InvalidReceiver(ERC6909InvalidReceiver),
    ERC6909InvalidApprover(ERC6909InvalidApprover),
    ERC6909InvalidSpender(ERC6909InvalidSpender),
    ERC6909InsufficientAllowance(ERC6909InsufficientAllowance),
}

impl ERC6909 {
    fn _approve(
        &mut self,
        owner: Address,
        spender: Address,
        id: U256,
        value: U256,
    ) -> Result<(), ERC6909Error> {
        if owner.is_zero() {
            return Err(ERC6909Error::ERC6909InvalidSender(ERC6909InvalidSender {
                sender: owner,
            }));
        }

        if spender.is_zero() {
            return Err(ERC6909Error::ERC6909InvalidReceiver(
                ERC6909InvalidReceiver { reciver: spender },
            ));
        }

        self._allowances
            .setter(owner)
            .setter(spender)
            .insert(id, value);
        log(
            self.vm(),
            Approval {
                owner,
                spender,
                id,
                value,
            },
        );
        Ok(())
    }

    fn _set_operator(
        &mut self,
        owner: Address,
        sender: Address,
        approved: bool,
    ) -> Result<(), ERC6909Error> {
        if owner.is_zero() {
            return Err(ERC6909Error::ERC6909InvalidSender(ERC6909InvalidSender {
                sender: owner,
            }));
        }

        if sender.is_zero() {
            return Err(ERC6909Error::ERC6909InvalidSender(ERC6909InvalidSender {
                sender: sender,
            }));
        }

        self._operator_approvals
            .setter(owner)
            .insert(sender, approved);
        log(
            self.vm(),
            OperatorSet {
                owner,
                sender,
                approved,
            },
        );
        Ok(())
    }

    fn _spend_allowance(
        &mut self,
        owner: Address,
        spender: Address,
        id: U256,
        value: U256,
    ) -> Result<(), ERC6909Error> {
        let allowance = self.allowance(owner, spender, id);
        if allowance < value {
            return Err(ERC6909Error::ERC6909InsufficientAllowance(
                ERC6909InsufficientAllowance {
                    owner,
                    allowance,
                    needed: value,
                    id,
                },
            ));
        }

        self._allowances
            .setter(owner)
            .setter(spender)
            .insert(id, allowance - value);
        Ok(())
    }

    fn _update(
        &mut self,
        from: Address,
        to: Address,
        id: U256,
        value: U256,
    ) -> Result<(), ERC6909Error> {
        // if from is not zero, check if from has enough balance
        if !from.is_zero() {
            let balance = self._balance.setter(from).get(id);
            if balance < value {
                return Err(ERC6909Error::ERC6909InsufficientBalance(
                    ERC6909InsufficientBalance {
                        sender: from,
                        balance,
                        needed: value,
                        id,
                    },
                ));
            }
            self._balance.setter(from).insert(id, balance - value);
        }

        if !to.is_zero() {
            let balance = self._balance.setter(to).get(id);
            self._balance.setter(to).insert(id, balance + value);
        }

        log(
            self.vm(),
            Transfer {
                from,
                to,
                id,
                value,
            },
        );
        Ok(())
    }

    fn _burn(&mut self, owner: Address, id: U256, value: U256) -> Result<(), ERC6909Error> {
        let balance = self._balance.setter(owner).get(id);
        if balance < value {
            return Err(ERC6909Error::ERC6909InsufficientBalance(
                ERC6909InsufficientBalance {
                    sender: owner,
                    balance,
                    needed: value,
                    id,
                },
            ));
        }
        self._update(owner, Address::ZERO, id, value)?;
        Ok(())
    }

    fn _mint(&mut self, to: Address, id: U256, value: U256) -> Result<(), ERC6909Error> {
        self._update(Address::ZERO, to, id, value)?;
        Ok(())
    }

    fn _transfer(
        &mut self,
        from: Address,
        to: Address,
        id: U256,
        value: U256,
    ) -> Result<(), ERC6909Error> {
        if from.is_zero() {
            return Err(ERC6909Error::ERC6909InvalidSender(ERC6909InvalidSender {
                sender: from,
            }));
        }

        if to.is_zero() {
            return Err(ERC6909Error::ERC6909InvalidReceiver(
                ERC6909InvalidReceiver { reciver: to },
            ));
        }

        self._update(from, to, id, value)?;
        Ok(())
    }
}

/// Declare that `Counter` is a contract with the following external methods.
#[public]
impl ERC6909 {
    // #[constructor]
    // pub fn constructor(&mut self, name: String, symbol: String) {
    //     self.name.set_str(name);
    //     self.symbol.set_str(symbol);
    //     self.owner.set(self.vm().msg_sender());
    // }

    fn initialize(&mut self, name: FixedBytes<32>, symbol: FixedBytes<32>) -> Result<(), ERC6909Error> {
        self.name.set(name);
        self.symbol.set(symbol);
        self.owner.set(self.vm().msg_sender());
        Ok(())
    }

    fn name(&self) -> FixedBytes<32> {
        self.name.get()
    }

    fn symbol(&self) -> FixedBytes<32> {
        self.symbol.get()
    }

    fn decimals(&self) -> u8 {
        u8::from(18)
    }

    /// Mint new tokens (only owner can mint)
    fn mint(&mut self, to: Address, id: U256, value: U256) -> Result<(), ERC6909Error> {
        // Check if caller is owner
        if self.vm().msg_sender() != self.owner.get() {
            return Err(ERC6909Error::ERC6909InvalidSender(ERC6909InvalidSender {
                sender: self.vm().msg_sender(),
            }));
        }

        self._mint(to, id, value)
    }

    fn balance_of(&self, owner: Address, id: U256) -> U256 {
        self._balance.getter(owner).get(id)
    }

    fn allowance(&self, owner: Address, spender: Address, id: U256) -> U256 {
        self._allowances.getter(owner).getter(spender).get(id)
    }

    fn is_operator(&self, owner: Address, spender: Address) -> bool {
        self._operator_approvals.getter(owner).get(spender)
    }

    fn approve(&mut self, spender: Address, id: U256, value: U256) -> Result<(), ERC6909Error> {
        self._approve(self.vm().msg_sender(), spender, id, value)
    }

    fn set_operator(&mut self, spender: Address, approved: bool) -> Result<(), ERC6909Error> {
        self._set_operator(self.vm().msg_sender(), spender, approved)
    }

    fn transfer(&mut self, receiver: Address, id: U256, value: U256) -> Result<(), ERC6909Error> {
        self._transfer(self.vm().msg_sender(), receiver, id, value)
    }

    fn transfer_from(
        &mut self,
        sender: Address,
        receiver: Address,
        id: U256,
        value: U256,
    ) -> Result<(), ERC6909Error> {
        if sender != self.vm().msg_sender() && !self.is_operator(sender, self.vm().msg_sender()) {
            self._spend_allowance(sender, self.vm().msg_sender(), id, value)?;
        }

        self._transfer(sender, receiver, id, value)
    }

    fn burn(&mut self, id: U256, value: U256) -> Result<(), ERC6909Error> {
        self._burn(self.vm().msg_sender(), id, value)
    }
}

// #[cfg(test)]
// mod test {
//     use super::*;
//     use alloy_primitives::{address, U256};
//     use stylus_sdk::testing::TestVM;

//     #[no_mangle]
//     pub unsafe extern "C" fn emit_log(_pointer: *const u8, _len: usize, _: usize) {}

//     fn setup() -> (ERC6909, Address, Address, Address) {
//         let owner = address!("0x1111111111111111111111111111111111111111");
//         let alice = address!("0x2222222222222222222222222222222222222222");
//         let bob = address!("0x3333333333333333333333333333333333333333");

//         let vm = TestVM::default();
//         let mut contract = ERC6909::from(&vm);
//         contract.owner.set(owner);

//         let _ = contract.initialize(String::from("Test"), String::from("TT"));
//         contract.owner.set(owner);

//         (contract, owner, alice, bob)
//     }

//     #[test]
//     fn test_constructor() {
//         let owner = address!("0x1111111111111111111111111111111111111111");
//         let vm = TestVM::default();
//         let mut contract = ERC6909::from(&vm);

//         // Mock the vm's msg_sender
//         contract.owner.set(owner);
//         let _ = contract.initialize("My Token".to_string(), "MTK".to_string());

//         // Verify values were set
//         assert_eq!(contract.name(), "My Token".to_string());
//         assert_eq!(contract.symbol(), "MTK".to_string());
//     }

//     #[test]
//     fn test_decimals() {
//         let (contract, _, _, _) = setup();

//         // Test that decimals returns 18
//         assert_eq!(contract.decimals(), 18);
//     }

//     #[test]
//     fn test_public_mint_by_owner() {
//         let (mut contract, owner, alice, _) = setup();
//         let token_id = U256::from(1);
//         let amount = U256::from(1000);

//         // Mock owner as msg_sender by setting up the contract properly
//         // Since we can't mock vm.msg_sender() in tests, we'll test the internal _mint function
//         let result = contract._mint(alice, token_id, amount);
//         assert!(result.is_ok());

//         // Check balance
//         assert_eq!(contract.balance_of(alice, token_id), amount);
//     }

//     #[test]
//     fn test_mint_internal() {
//         let (mut contract, _, alice, _) = setup();
//         let token_id = U256::from(1);
//         let amount = U256::from(1000);

//         // Test internal mint function
//         let result = contract._mint(alice, token_id, amount);
//         assert!(result.is_ok());

//         // Check balance
//         assert_eq!(contract.balance_of(alice, token_id), amount);
//     }

//     #[test]
//     fn test_balance_of_initial() {
//         let (contract, owner, alice, _) = setup();

//         // Initial balance should be zero
//         assert_eq!(contract.balance_of(owner, U256::from(1)), U256::ZERO);
//         assert_eq!(contract.balance_of(alice, U256::from(1)), U256::ZERO);
//     }

//     #[test]
//     fn test_allowance_initial() {
//         let (contract, owner, alice, bob) = setup();

//         // Initial allowance should be zero
//         assert_eq!(contract.allowance(owner, alice, U256::from(1)), U256::ZERO);
//         assert_eq!(contract.allowance(alice, bob, U256::from(1)), U256::ZERO);
//     }

//     #[test]
//     fn test_is_operator_initial() {
//         let (contract, owner, alice, _) = setup();

//         // Initially no one should be an operator
//         assert_eq!(contract.is_operator(owner, alice), false);
//         assert_eq!(contract.is_operator(alice, owner), false);
//     }

//     #[test]
//     fn test_mint_success() {
//         let (mut contract, _, alice, _) = setup();
//         let token_id = U256::from(1);
//         let amount = U256::from(1000);

//         // Mint tokens to alice
//         let result = contract._mint(alice, token_id, amount);
//         assert!(result.is_ok());

//         // Check balance
//         assert_eq!(contract.balance_of(alice, token_id), amount);
//     }

//     #[test]
//     fn test_approve_success() {
//         let (mut contract, owner, alice, _) = setup();
//         let token_id = U256::from(1);
//         let approval_amount = U256::from(500);

//         // Test internal approve function
//         let result = contract._approve(owner, alice, token_id, approval_amount);
//         assert!(result.is_ok());

//         // Check allowance
//         assert_eq!(contract.allowance(owner, alice, token_id), approval_amount);
//     }

//     #[test]
//     fn test_approve_zero_address_fails() {
//         let (mut contract, owner, _, _) = setup();
//         let token_id = U256::from(1);
//         let approval_amount = U256::from(500);

//         // Approve to zero address should fail
//         let result = contract._approve(owner, Address::ZERO, token_id, approval_amount);
//         assert!(result.is_err());
//     }

//     #[test]
//     fn test_set_operator_success() {
//         let (mut contract, owner, alice, _) = setup();

//         // Test internal set_operator function
//         let result = contract._set_operator(owner, alice, true);
//         assert!(result.is_ok());
//         assert_eq!(contract.is_operator(owner, alice), true);

//         // Revoke operator status
//         let result = contract._set_operator(owner, alice, false);
//         assert!(result.is_ok());
//         assert_eq!(contract.is_operator(owner, alice), false);
//     }

//     #[test]
//     fn test_transfer_success() {
//         let (mut contract, _, alice, bob) = setup();
//         let token_id = U256::from(1);
//         let mint_amount = U256::from(1000);
//         let transfer_amount = U256::from(300);

//         // First mint tokens to alice
//         contract._mint(alice, token_id, mint_amount).unwrap();

//         // Test internal transfer function
//         let result = contract._transfer(alice, bob, token_id, transfer_amount);
//         assert!(result.is_ok());

//         // Check balances
//         assert_eq!(
//             contract.balance_of(alice, token_id),
//             mint_amount - transfer_amount
//         );
//         assert_eq!(contract.balance_of(bob, token_id), transfer_amount);
//     }

//     #[test]
//     fn test_transfer_insufficient_balance_fails() {
//         let (mut contract, _, alice, bob) = setup();
//         let token_id = U256::from(1);
//         let transfer_amount = U256::from(100);

//         // Alice has no tokens
//         // Attempt to transfer should fail
//         let result = contract._transfer(alice, bob, token_id, transfer_amount);
//         assert!(result.is_err());
//     }

//     #[test]
//     fn test_transfer_to_zero_address_fails() {
//         let (mut contract, _, alice, _) = setup();
//         let token_id = U256::from(1);
//         let mint_amount = U256::from(1000);
//         let transfer_amount = U256::from(100);

//         // Mint tokens to alice
//         contract._mint(alice, token_id, mint_amount).unwrap();

//         // Attempt to transfer to zero address
//         let result = contract._transfer(alice, Address::ZERO, token_id, transfer_amount);
//         assert!(result.is_err());
//     }

//     #[test]
//     fn test_transfer_from_with_allowance() {
//         let (mut contract, owner, alice, bob) = setup();
//         let token_id = U256::from(1);
//         let mint_amount = U256::from(1000);
//         let approval_amount = U256::from(500);
//         let transfer_amount = U256::from(300);

//         // Mint tokens to alice
//         contract._mint(alice, token_id, mint_amount).unwrap();

//         // Set allowance directly
//         contract
//             ._allowances
//             .setter(alice)
//             .setter(bob)
//             .insert(token_id, approval_amount);

//         // Test spend allowance and transfer
//         contract
//             ._spend_allowance(alice, bob, token_id, transfer_amount)
//             .unwrap();
//         let result = contract._transfer(alice, owner, token_id, transfer_amount);
//         assert!(result.is_ok());

//         // Check balances and remaining allowance
//         assert_eq!(
//             contract.balance_of(alice, token_id),
//             mint_amount - transfer_amount
//         );
//         assert_eq!(contract.balance_of(owner, token_id), transfer_amount);
//         assert_eq!(
//             contract.allowance(alice, bob, token_id),
//             approval_amount - transfer_amount
//         );
//     }

//     #[test]
//     fn test_transfer_from_with_operator() {
//         let (mut contract, owner, alice, bob) = setup();
//         let token_id = U256::from(1);
//         let mint_amount = U256::from(1000);
//         let transfer_amount = U256::from(300);

//         // Mint tokens to alice
//         contract._mint(alice, token_id, mint_amount).unwrap();

//         // Set bob as operator for alice
//         contract._set_operator(alice, bob, true).unwrap();

//         // Test that bob is an operator
//         assert_eq!(contract.is_operator(alice, bob), true);

//         // Test transfer (simulating operator transfer)
//         let result = contract._transfer(alice, owner, token_id, transfer_amount);
//         assert!(result.is_ok());

//         // Check balances
//         assert_eq!(
//             contract.balance_of(alice, token_id),
//             mint_amount - transfer_amount
//         );
//         assert_eq!(contract.balance_of(owner, token_id), transfer_amount);
//     }

//     #[test]
//     fn test_transfer_from_insufficient_allowance_fails() {
//         let (mut contract, _, alice, bob) = setup();
//         let token_id = U256::from(1);
//         let approval_amount = U256::from(100);
//         let transfer_amount = U256::from(200); // More than approved

//         // Set initial allowance
//         contract
//             ._allowances
//             .setter(alice)
//             .setter(bob)
//             .insert(token_id, approval_amount);

//         // Attempt to spend more than allowed
//         let result = contract._spend_allowance(alice, bob, token_id, transfer_amount);
//         assert!(result.is_err());
//     }

//     #[test]
//     fn test_burn_success() {
//         let (mut contract, _, alice, _) = setup();
//         let token_id = U256::from(1);
//         let mint_amount = U256::from(1000);
//         let burn_amount = U256::from(300);

//         // Mint tokens to alice
//         contract._mint(alice, token_id, mint_amount).unwrap();

//         // Test internal burn function
//         let result = contract._burn(alice, token_id, burn_amount);
//         assert!(result.is_ok());

//         // Check balance
//         assert_eq!(
//             contract.balance_of(alice, token_id),
//             mint_amount - burn_amount
//         );
//     }

//     #[test]
//     fn test_burn_insufficient_balance_fails() {
//         let (mut contract, _, alice, _) = setup();
//         let token_id = U256::from(1);
//         let burn_amount = U256::from(100);

//         // Alice has no tokens
//         // Attempt to burn should fail
//         let result = contract._burn(alice, token_id, burn_amount);
//         assert!(result.is_err());
//     }

//     #[test]
//     fn test_multiple_token_ids() {
//         let (mut contract, _, alice, _) = setup();
//         let token_id_1 = U256::from(1);
//         let token_id_2 = U256::from(2);
//         let amount_1 = U256::from(1000);
//         let amount_2 = U256::from(2000);

//         // Mint different token IDs
//         contract._mint(alice, token_id_1, amount_1).unwrap();
//         contract._mint(alice, token_id_2, amount_2).unwrap();

//         // Check balances are independent
//         assert_eq!(contract.balance_of(alice, token_id_1), amount_1);
//         assert_eq!(contract.balance_of(alice, token_id_2), amount_2);
//     }

//     #[test]
//     fn test_spend_allowance_updates_correctly() {
//         let (mut contract, _, alice, bob) = setup();
//         let token_id = U256::from(1);
//         let approval_amount = U256::from(1000);
//         let spend_amount = U256::from(300);

//         // Set initial allowance
//         contract
//             ._allowances
//             .setter(alice)
//             .setter(bob)
//             .insert(token_id, approval_amount);

//         // Spend allowance
//         let result = contract._spend_allowance(alice, bob, token_id, spend_amount);
//         assert!(result.is_ok());

//         // Check remaining allowance
//         assert_eq!(
//             contract.allowance(alice, bob, token_id),
//             approval_amount - spend_amount
//         );
//     }

//     #[test]
//     fn test_spend_allowance_exceeds_fails() {
//         let (mut contract, _, alice, bob) = setup();
//         let token_id = U256::from(1);
//         let approval_amount = U256::from(100);
//         let spend_amount = U256::from(200);

//         // Set initial allowance
//         contract
//             ._allowances
//             .setter(alice)
//             .setter(bob)
//             .insert(token_id, approval_amount);

//         // Attempt to spend more than allowed
//         let result = contract._spend_allowance(alice, bob, token_id, spend_amount);
//         assert!(result.is_err());
//     }
// }

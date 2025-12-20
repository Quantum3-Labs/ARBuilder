#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
extern crate alloc;

use alloy_primitives::{Address, Uint};
use core::convert::TryInto;
use stylus_sdk::{
    prelude::*,
    storage::{StorageMap, StorageU64, StorageU32, StorageVec, StorageAddress},
};

#[entrypoint]
#[storage]
pub struct Fortune {
    total_minted: StorageU64,
    fortune_list: StorageVec<StorageU32>,
    owners: StorageMap<u64, StorageAddress>,
    balances: StorageMap<Address, StorageU64>,
    admin: StorageAddress,
}

#[public]
impl Fortune {
    /// Mints a fortune and assigns it to the caller.
    pub fn mint_fortune(&mut self, fortune: u32) {
        let total_minted = self.total_minted_value();

        // Append the new fortune to the list.
        self.set_fortune_list(fortune);

        // Record the owner of this newly minted fortune.
        self.set_owner(total_minted, self.vm().msg_sender());

        // Increment the total minted count.
        self.set_total_minted(total_minted + 1);

        // Increase the caller’s balance.
        let balance = self.balances(self.vm().msg_sender());
        self.set_balances(self.vm().msg_sender(), balance + 1);
    }

    /// Retrieves the fortune at the specified index.
    pub fn get_fortune(&self, index: u64) -> u32 {
        self.fortune_list
            .get(index)
            .map(|val| {
                let bytes: [u8; 4] = val.to_be_bytes();
                u32::from_be_bytes(bytes)
            })
            .unwrap_or_default()
    }

    /// Generates a somewhat random fortune from the list of minted fortunes.
    pub fn generate_fortune(&self) -> u32 {
        let total = self.total_minted_value();
        if total == 0 {
            return 0;
        }
        let random_index = self.pseudo_random(total);
        self.get_fortune(random_index)
    }

    /// Retrieves the total number of fortunes minted.
    pub fn total_minted_value(&self) -> u64 {
        let val = self.total_minted.get();
        let bytes: [u8; 8] = val.to_be_bytes();
        u64::from_be_bytes(bytes)
    }

    /// Sets the total number of fortunes minted.
    pub fn set_total_minted(&mut self, total: u64) {
        let value = Uint::<64, 1>::from_be_bytes(total.to_be_bytes());
        self.total_minted.set(value);
    }

    /// Appends a fortune to the fortune list.
    pub fn set_fortune_list(&mut self, fortune: u32) {
        let value = Uint::<32, 1>::from_be_bytes(fortune.to_be_bytes());
        self.fortune_list.push(value);
    }

    /// Records the owner of the fortune at the specified index.
    pub fn set_owner(&mut self, index: u64, owner: Address) {
        self.owners.insert(index, owner);
    }

    /// Retrieves the balance of the specified address.
    pub fn balances(&self, address: Address) -> u64 {
        let val = self.balances.get(address);
        let bytes: [u8; 8] = val.to_be_bytes();
        u64::from_be_bytes(bytes)
    }

    /// Sets the balance of the specified address.
    pub fn set_balances(&mut self, address: Address, balance: u64) {
        let value = Uint::<64, 1>::from_be_bytes(balance.to_be_bytes());
        self.balances.insert(address, value);
    }

    /// Internal helper to generate a pseudo-random index.
    ///
    /// Combines the current block's timestamp and the caller's address bytes
    /// to produce some entropy.
    fn pseudo_random(&self, total: u64) -> u64 {
        let timestamp = self.vm().block_timestamp();
        let sender = self.vm().msg_sender();

        // Get the underlying byte slice of the Address.
        let sender_bytes: &[u8] = sender.as_ref();
        // Extract the first 8 bytes.
        let seed = timestamp ^ u64::from_be_bytes(sender_bytes[0..8].try_into().unwrap());
        seed % total
    }
}

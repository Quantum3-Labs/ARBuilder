#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]

#[macro_use]
extern crate alloc;

use alloc::vec::Vec;

use stylus_sdk::{
    alloy_primitives::{FixedBytes, U256},
    alloy_sol_types::{sol, SolCall},
    prelude::*,
};

#[cfg(target_arch = "wasm32")]
#[link(wasm_import_module = "vm_hooks")]
unsafe extern "C" {
    fn transient_load_bytes32(key: *const u8, dest: *const u8);
    fn transient_store_bytes32(key: *const u8, value: *const u8);
}

#[cfg(not(target_arch = "wasm32"))]
pub fn transient_load_bytes32(key: *const u8, dest: *const u8) {}

#[cfg(not(target_arch = "wasm32"))]
pub fn transient_store_bytes32(key: *const u8, value: *const u8) {}

fn tload(key: U256) -> U256 {
    let mut dest = [0u8; 32];
    unsafe {
        transient_load_bytes32(key.to_be_bytes::<32>().as_ptr(), dest.as_mut_ptr());
    }
    U256::from_be_bytes(dest)
}

fn store(key: U256, val: U256) {
    unsafe {
        transient_store_bytes32(
            key.to_be_bytes::<32>().as_ptr(),
            val.to_be_bytes::<32>().as_ptr(),
        );
    }
}

#[storage]
#[cfg_attr(any(feature = "contract-1", feature = "contract-2"), entrypoint)]
struct TStoreExample;

sol! {
    function hello() external view returns (string);
}

#[cfg_attr(feature = "contract-1", public)]
impl TStoreExample {
    pub fn hello() -> U256 {
        tload(U256::from(123))
    }
}

#[cfg_attr(feature = "contract-2", public)]
impl TStoreExample {
    pub fn reentrant(&self) -> FixedBytes<32> {
        store(U256::from(123), U256::from(456));
        let addr = self.vm().contract_address();
        FixedBytes::from_slice(
            &self
                .vm()
                .static_call(&self, addr, &helloCall {}.abi_encode())
                .unwrap(),
        )
    }
}

#[cfg(not(any(feature = "contract-1", feature = "contract-2")))]
compile_error!("contract-1 and contract-2 not enabled!");

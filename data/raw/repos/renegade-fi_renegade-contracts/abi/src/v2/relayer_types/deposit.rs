//! Conversion for deposit types

use crate::v2::{
    relayer_types::{u128_to_u256, u256_to_u128},
    IDarkpoolV2,
};

use renegade_circuit_types_v2::deposit::Deposit as CircuitDeposit;

impl From<IDarkpoolV2::Deposit> for CircuitDeposit {
    fn from(deposit: IDarkpoolV2::Deposit) -> Self {
        Self {
            from: deposit.from,
            token: deposit.token,
            amount: u256_to_u128(deposit.amount),
        }
    }
}

impl From<CircuitDeposit> for IDarkpoolV2::Deposit {
    fn from(deposit: CircuitDeposit) -> Self {
        Self {
            from: deposit.from,
            token: deposit.token,
            amount: u128_to_u256(deposit.amount),
        }
    }
}

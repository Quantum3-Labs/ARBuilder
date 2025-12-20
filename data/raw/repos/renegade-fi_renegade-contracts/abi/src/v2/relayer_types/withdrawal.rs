//! Conversion for withdrawal types

use crate::v2::{
    relayer_types::{u128_to_u256, u256_to_u128},
    IDarkpoolV2,
};

use renegade_circuit_types_v2::withdrawal::Withdrawal as CircuitWithdrawal;

impl From<IDarkpoolV2::Withdrawal> for CircuitWithdrawal {
    fn from(withdrawal: IDarkpoolV2::Withdrawal) -> Self {
        Self {
            to: withdrawal.to,
            token: withdrawal.token,
            amount: u256_to_u128(withdrawal.amount),
        }
    }
}

impl From<CircuitWithdrawal> for IDarkpoolV2::Withdrawal {
    fn from(withdrawal: CircuitWithdrawal) -> Self {
        Self {
            to: withdrawal.to,
            token: withdrawal.token,
            amount: u128_to_u256(withdrawal.amount),
        }
    }
}

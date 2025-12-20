//! Relayer type interactions and conversions for the V2 ABI

use alloy::primitives::U256;
use renegade_circuit_types_v2::elgamal::BabyJubJubPoint;
use renegade_circuit_types_v2::fixed_point::FixedPoint;
use renegade_constants_v2::Scalar;
use renegade_crypto_v2::fields::scalar_to_u256;

use crate::v2::IDarkpoolV2;
use crate::v2::BN254;

pub mod balance;
pub mod ciphertext;
pub mod commitments;
pub mod deposit;
pub mod intent;
pub mod note;
pub mod obligation;
pub mod proof_bundles;
pub mod withdrawal;

// ----------------------
// | Conversion Helpers |
// ----------------------

/// Convert a `U256` to a `u128`
pub fn u256_to_u128(u256: U256) -> u128 {
    let mut u128_bytes = [0u8; 16];
    let u256_bytes = u256.to_le_bytes::<{ U256::BYTES }>();
    u128_bytes.copy_from_slice(&u256_bytes[..16]);
    u128::from_le_bytes(u128_bytes)
}

/// Convert a `u128` to a `U256`
pub fn u128_to_u256(x: u128) -> U256 {
    U256::from(x)
}

/// Convert a `Scalar` to a `BN254.ScalarField`
pub fn scalar_to_contract_scalar(scalar: Scalar) -> BN254::ScalarField {
    let u256 = scalar_to_u256(&scalar);
    BN254::ScalarField::from_underlying(u256)
}

/// Convert a `U256` to a `Scalar`
pub fn u256_to_scalar(u256: U256) -> Scalar {
    let bytes: [u8; 32] = u256.to_be_bytes();
    Scalar::from_be_bytes_mod_order(&bytes)
}

/// Convert a `FixedPoint` to a contract `FixedPoint`
impl From<FixedPoint> for IDarkpoolV2::FixedPoint {
    fn from(fixed_point: FixedPoint) -> Self {
        Self {
            repr: scalar_to_u256(&fixed_point.repr),
        }
    }
}

/// Convert a contract `FixedPoint` to a `FixedPoint`
impl From<IDarkpoolV2::FixedPoint> for FixedPoint {
    fn from(fixed_point: IDarkpoolV2::FixedPoint) -> Self {
        Self {
            repr: u256_to_scalar(fixed_point.repr),
        }
    }
}

/// Convert a `BabyJubJubPoint` to a `IDarkpoolV2::BabyJubJubPoint`
impl From<BabyJubJubPoint> for IDarkpoolV2::BabyJubJubPoint {
    fn from(point: BabyJubJubPoint) -> Self {
        Self {
            x: scalar_to_u256(&point.x),
            y: scalar_to_u256(&point.y),
        }
    }
}

/// Convert a `IDarkpoolV2::BabyJubJubPoint` to a `BabyJubJubPoint`
impl From<IDarkpoolV2::BabyJubJubPoint> for BabyJubJubPoint {
    fn from(point: IDarkpoolV2::BabyJubJubPoint) -> Self {
        Self {
            x: u256_to_scalar(point.x),
            y: u256_to_scalar(point.y),
        }
    }
}

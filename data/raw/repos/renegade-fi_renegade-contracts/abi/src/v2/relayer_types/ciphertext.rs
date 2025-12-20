//! Ciphertext type conversions

use renegade_circuit_types_v2::elgamal::{ElGamalCiphertext, EncryptionKey};
use renegade_constants_v2::Scalar;
use renegade_crypto_v2::fields::scalar_to_u256;

use crate::v2::{
    relayer_types::{proof_bundles::size_vec, u256_to_scalar},
    IDarkpoolV2,
};

impl<const N: usize> From<ElGamalCiphertext<N>> for IDarkpoolV2::ElGamalCiphertext {
    fn from(v: ElGamalCiphertext<N>) -> Self {
        let ciphertext = v.ciphertext.iter().map(scalar_to_u256).collect();
        Self {
            ephemeralKey: v.ephemeral_key.into(),
            ciphertext,
        }
    }
}

impl<const N: usize> From<IDarkpoolV2::ElGamalCiphertext> for ElGamalCiphertext<N> {
    fn from(v: IDarkpoolV2::ElGamalCiphertext) -> Self {
        let ciphertext: Vec<Scalar> = v.ciphertext.iter().map(|x| u256_to_scalar(*x)).collect();
        let sized_ciphertext = size_vec(ciphertext);
        Self {
            ephemeral_key: v.ephemeralKey.into(),
            ciphertext: sized_ciphertext,
        }
    }
}

impl From<EncryptionKey> for IDarkpoolV2::EncryptionKey {
    fn from(v: EncryptionKey) -> Self {
        Self { point: v.into() }
    }
}

impl From<IDarkpoolV2::EncryptionKey> for EncryptionKey {
    fn from(v: IDarkpoolV2::EncryptionKey) -> Self {
        v.point.into()
    }
}

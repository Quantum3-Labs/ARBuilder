//! Note types helpers

use renegade_circuit_types_v2::note::Note;
use renegade_crypto_v2::fields::scalar_to_u256;

use crate::v2::{
    relayer_types::{u128_to_u256, u256_to_scalar, u256_to_u128},
    IDarkpoolV2,
};

impl From<Note> for IDarkpoolV2::Note {
    fn from(note: Note) -> Self {
        Self {
            mint: note.mint,
            amount: u128_to_u256(note.amount),
            receiver: note.receiver,
            blinder: scalar_to_u256(&note.blinder),
        }
    }
}

impl From<IDarkpoolV2::Note> for Note {
    fn from(note: IDarkpoolV2::Note) -> Self {
        Self {
            mint: note.mint,
            amount: u256_to_u128(note.amount),
            receiver: note.receiver,
            blinder: u256_to_scalar(note.blinder),
        }
    }
}

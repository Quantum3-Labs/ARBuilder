//! Conversion for intent types

use super::u256_to_scalar;
#[cfg(feature = "v2-auth-helpers")]
use crate::v2::IDarkpoolV2::SignatureWithNonce;
use crate::v2::{
    relayer_types::{u128_to_u256, u256_to_u128},
    IDarkpoolV2::{self, PublicIntentPermit},
};
#[cfg(feature = "v2-auth-helpers")]
use alloy::signers::Error as SignerError;
use alloy::{signers::local::PrivateKeySigner, sol_types::SolValue};
use renegade_circuit_types_v2::{
    fixed_point::FixedPointShare,
    intent::{Intent as CircuitIntent, IntentShare, PreMatchIntentShare},
};
use renegade_crypto_v2::fields::scalar_to_u256;

impl From<IDarkpoolV2::Intent> for CircuitIntent {
    fn from(intent: IDarkpoolV2::Intent) -> Self {
        Self {
            in_token: intent.inToken,
            out_token: intent.outToken,
            owner: intent.owner,
            min_price: intent.minPrice.into(),
            amount_in: u256_to_u128(intent.amountIn),
        }
    }
}

impl From<CircuitIntent> for IDarkpoolV2::Intent {
    fn from(intent: CircuitIntent) -> Self {
        Self {
            inToken: intent.in_token,
            outToken: intent.out_token,
            owner: intent.owner,
            minPrice: intent.min_price.into(),
            amountIn: u128_to_u256(intent.amount_in),
        }
    }
}

impl From<IntentShare> for IDarkpoolV2::IntentPublicShare {
    fn from(share: IntentShare) -> Self {
        Self {
            inToken: scalar_to_u256(&share.in_token),
            outToken: scalar_to_u256(&share.out_token),
            owner: scalar_to_u256(&share.owner),
            minPrice: scalar_to_u256(&share.min_price.repr),
            amountIn: scalar_to_u256(&share.amount_in),
        }
    }
}

impl From<IDarkpoolV2::IntentPublicShare> for IntentShare {
    fn from(share: IDarkpoolV2::IntentPublicShare) -> Self {
        Self {
            in_token: u256_to_scalar(share.inToken),
            out_token: u256_to_scalar(share.outToken),
            owner: u256_to_scalar(share.owner),
            min_price: FixedPointShare {
                repr: u256_to_scalar(share.minPrice),
            },
            amount_in: u256_to_scalar(share.amountIn),
        }
    }
}

impl From<PreMatchIntentShare> for IDarkpoolV2::IntentPreMatchShare {
    fn from(share: PreMatchIntentShare) -> Self {
        Self {
            inToken: scalar_to_u256(&share.in_token),
            outToken: scalar_to_u256(&share.out_token),
            owner: scalar_to_u256(&share.owner),
            minPrice: scalar_to_u256(&share.min_price.repr),
        }
    }
}

impl From<IDarkpoolV2::IntentPreMatchShare> for PreMatchIntentShare {
    fn from(share: IDarkpoolV2::IntentPreMatchShare) -> Self {
        Self {
            in_token: u256_to_scalar(share.inToken),
            out_token: u256_to_scalar(share.outToken),
            owner: u256_to_scalar(share.owner),
            min_price: FixedPointShare {
                repr: u256_to_scalar(share.minPrice),
            },
        }
    }
}

#[cfg(feature = "v2-auth-helpers")]
impl PublicIntentPermit {
    /// Create a signature for a public intent permit
    pub fn sign(&self, signer: &PrivateKeySigner) -> Result<SignatureWithNonce, SignerError> {
        use crate::v2::auth_helpers::sign_with_nonce;
        sign_with_nonce(self.abi_encode().as_slice(), signer)
    }
}

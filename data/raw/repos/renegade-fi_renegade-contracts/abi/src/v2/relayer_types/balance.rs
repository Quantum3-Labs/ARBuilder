//! Balance type conversions

use renegade_circuit_types_v2::balance::{PostMatchBalanceShare, PreMatchBalanceShare};
use renegade_crypto_v2::fields::scalar_to_u256;

use crate::v2::{relayer_types::u256_to_scalar, IDarkpoolV2};

impl From<PostMatchBalanceShare> for IDarkpoolV2::PostMatchBalanceShare {
    fn from(share: PostMatchBalanceShare) -> Self {
        Self {
            relayerFeeBalance: scalar_to_u256(&share.relayer_fee_balance),
            protocolFeeBalance: scalar_to_u256(&share.protocol_fee_balance),
            amount: scalar_to_u256(&share.amount),
        }
    }
}

impl From<IDarkpoolV2::PostMatchBalanceShare> for PostMatchBalanceShare {
    fn from(share: IDarkpoolV2::PostMatchBalanceShare) -> Self {
        Self {
            relayer_fee_balance: u256_to_scalar(share.relayerFeeBalance),
            protocol_fee_balance: u256_to_scalar(share.protocolFeeBalance),
            amount: u256_to_scalar(share.amount),
        }
    }
}

impl From<PreMatchBalanceShare> for IDarkpoolV2::PreMatchBalanceShare {
    fn from(share: PreMatchBalanceShare) -> Self {
        Self {
            mint: scalar_to_u256(&share.mint),
            owner: scalar_to_u256(&share.owner),
            relayerFeeRecipient: scalar_to_u256(&share.relayer_fee_recipient),
            oneTimeAuthority: scalar_to_u256(&share.one_time_authority),
        }
    }
}

impl From<IDarkpoolV2::PreMatchBalanceShare> for PreMatchBalanceShare {
    fn from(share: IDarkpoolV2::PreMatchBalanceShare) -> Self {
        Self {
            mint: u256_to_scalar(share.mint),
            owner: u256_to_scalar(share.owner),
            relayer_fee_recipient: u256_to_scalar(share.relayerFeeRecipient),
            one_time_authority: u256_to_scalar(share.oneTimeAuthority),
        }
    }
}

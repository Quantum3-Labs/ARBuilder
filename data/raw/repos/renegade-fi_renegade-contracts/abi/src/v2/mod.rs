use alloy::sol;

#[cfg(feature = "transfer-auth")]
pub mod transfer_auth;

// We use a combined ABI between the darkpool v2, verifier, and vkeys interfaces as the sol macro currently requires all
// types to be present in the same macro invocation.
sol! {
    #![sol(all_derives)]
    #[allow(missing_docs, clippy::too_many_arguments)]
    #[sol(rpc)]
    IDarkpoolV2,
    "ICombinedV2.json",
}

#[cfg(feature = "v2-relayer-types")]
pub mod relayer_types;

#[cfg(feature = "v2-auth-helpers")]
pub mod auth_helpers;

pub mod calldata_bundles;

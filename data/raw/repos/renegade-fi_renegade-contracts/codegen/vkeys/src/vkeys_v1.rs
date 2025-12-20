//! Code for generating verification keys for the Renegade circuits

use std::fmt::{self, Display};

use crate::{NamedLinkingVkey, NamedVkey};
use reference_impl_common::abi_types::{ProofLinkingVK, VerificationKey};
use renegade_circuit_types_v1::traits::SingleProverCircuit;
use renegade_circuits_v1::zk_circuits::{
    proof_linking::{
        get_commitments_match_settle_group_layout, get_reblind_commitments_group_layout,
    },
    valid_commitments::SizedValidCommitments,
    valid_fee_redemption::SizedValidFeeRedemption,
    valid_malleable_match_settle_atomic::SizedValidMalleableMatchSettleAtomic,
    valid_match_settle::{SizedValidMatchSettle, SizedValidMatchSettleWithCommitments},
    valid_match_settle_atomic::{
        SizedValidMatchSettleAtomic, SizedValidMatchSettleAtomicWithCommitments,
    },
    valid_offline_fee_settlement::SizedValidOfflineFeeSettlement,
    valid_reblind::SizedValidReblind,
    valid_wallet_create::SizedValidWalletCreate,
    valid_wallet_update::SizedValidWalletUpdate,
};
use renegade_constants_v1::{MAX_BALANCES, MAX_ORDERS, MERKLE_HEIGHT};

/// The circuit to generate a verification key for
#[derive(Debug, Clone, Copy)]
#[allow(clippy::enum_variant_names)]
enum V1Circuit {
    /// The `VALID WALLET CREATE` circuit
    ValidWalletCreate,
    /// The `VALID WALLET UPDATE` circuit
    ValidWalletUpdate,
    /// The `VALID REBLIND` circuit
    ValidReblind,
    /// The `VALID COMMITMENTS` circuit
    ValidCommitments,
    /// The `VALID MATCH SETTLE` circuit
    ValidMatchSettle,
    /// The `VALID MATCH SETTLE WITH COMMITMENTS` circuit
    ValidMatchSettleWithCommitments,
    /// The `VALID MATCH SETTLE ATOMIC` circuit
    ValidMatchSettleAtomic,
    /// The `VALID MATCH SETTLE ATOMIC WITH COMMITMENTS` circuit
    ValidMatchSettleAtomicWithCommitments,
    /// The `VALID MALLEABLE MATCH SETTLE ATOMIC` circuit
    ValidMalleableMatchSettleAtomic,
    /// The `VALID OFFLINE FEE SETTLEMENT` circuit
    ValidOfflineFeeSettlement,
    /// The `VALID FEE REDEMPTION` circuit
    ValidFeeRedemption,
}
impl Display for V1Circuit {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.name())
    }
}

impl V1Circuit {
    /// Generate the verification key for the circuit
    ///
    /// `SingleProverCircuit` cannot be a trait object, so we must handle each
    /// circuit explicitly
    pub fn vkey(&self) -> VerificationKey {
        match self {
            Self::ValidWalletCreate => generate_vkey_for_circuit::<SizedValidWalletCreate>(),
            Self::ValidWalletUpdate => generate_vkey_for_circuit::<SizedValidWalletUpdate>(),
            Self::ValidReblind => generate_vkey_for_circuit::<SizedValidReblind>(),
            Self::ValidCommitments => generate_vkey_for_circuit::<SizedValidCommitments>(),
            Self::ValidMatchSettle => generate_vkey_for_circuit::<SizedValidMatchSettle>(),
            Self::ValidMatchSettleWithCommitments => {
                generate_vkey_for_circuit::<SizedValidMatchSettleWithCommitments>()
            }
            Self::ValidMatchSettleAtomic => {
                generate_vkey_for_circuit::<SizedValidMatchSettleAtomic>()
            }
            Self::ValidMalleableMatchSettleAtomic => {
                generate_vkey_for_circuit::<SizedValidMalleableMatchSettleAtomic>()
            }
            Self::ValidMatchSettleAtomicWithCommitments => {
                generate_vkey_for_circuit::<SizedValidMatchSettleAtomicWithCommitments>()
            }
            Self::ValidOfflineFeeSettlement => {
                generate_vkey_for_circuit::<SizedValidOfflineFeeSettlement>()
            }
            Self::ValidFeeRedemption => generate_vkey_for_circuit::<SizedValidFeeRedemption>(),
        }
    }

    /// Get the name of the circuit for the purpose of generating a Solidity constant
    pub fn name(&self) -> &'static str {
        match self {
            Self::ValidWalletCreate => "VALID_WALLET_CREATE",
            Self::ValidWalletUpdate => "VALID_WALLET_UPDATE",
            Self::ValidReblind => "VALID_REBLIND",
            Self::ValidCommitments => "VALID_COMMITMENTS",
            Self::ValidMatchSettle => "VALID_MATCH_SETTLE",
            Self::ValidMatchSettleWithCommitments => "VALID_MATCH_SETTLE_WITH_COMMITMENTS",
            Self::ValidMatchSettleAtomic => "VALID_MATCH_SETTLE_ATOMIC",
            Self::ValidMatchSettleAtomicWithCommitments => {
                "VALID_MATCH_SETTLE_ATOMIC_WITH_COMMITMENTS"
            }
            Self::ValidMalleableMatchSettleAtomic => "VALID_MALLEABLE_MATCH_SETTLE_ATOMIC",
            Self::ValidOfflineFeeSettlement => "VALID_OFFLINE_FEE_SETTLEMENT",
            Self::ValidFeeRedemption => "VALID_FEE_REDEMPTION",
        }
    }

    /// Get all circuits
    pub fn all() -> Vec<Self> {
        vec![
            Self::ValidWalletCreate,
            Self::ValidWalletUpdate,
            Self::ValidReblind,
            Self::ValidCommitments,
            Self::ValidMatchSettle,
            Self::ValidMatchSettleWithCommitments,
            Self::ValidMatchSettleAtomic,
            Self::ValidMatchSettleAtomicWithCommitments,
            Self::ValidMalleableMatchSettleAtomic,
            Self::ValidOfflineFeeSettlement,
            Self::ValidFeeRedemption,
        ]
    }
}

/// Represents all the linking instances in the Renegade circuits
#[derive(Debug, Clone, Copy)]
pub enum V1LinkingInstance {
    /// The proof link between `VALID REBLIND` and `VALID COMMITMENTS`
    ValidReblindCommitments,
    /// The proof link between `VALID COMMITMENTS` and `VALID MATCH SETTLE` for the first party
    ValidCommitmentsMatchSettle0,
    /// The proof link between `VALID COMMITMENTS` and `VALID MATCH SETTLE` for the second party
    ValidCommitmentsMatchSettle1,
}

impl V1LinkingInstance {
    /// Generate a verification key for the linking instance
    pub fn vkey(&self) -> ProofLinkingVK {
        match self {
            Self::ValidReblindCommitments => generate_reblind_commitments_link_vkey(),
            Self::ValidCommitmentsMatchSettle0 => {
                generate_commitments_match_settle_link_vkey(0 /* party */)
            }
            Self::ValidCommitmentsMatchSettle1 => {
                generate_commitments_match_settle_link_vkey(1 /* party */)
            }
        }
    }

    /// Get the name of the linking instance
    pub fn name(&self) -> &'static str {
        match self {
            Self::ValidReblindCommitments => "VALID_REBLIND_COMMITMENTS_LINK",
            Self::ValidCommitmentsMatchSettle0 => "VALID_COMMITMENTS_MATCH_SETTLE_LINK0",
            Self::ValidCommitmentsMatchSettle1 => "VALID_COMMITMENTS_MATCH_SETTLE_LINK1",
        }
    }

    /// Get all linking instances
    pub fn all() -> Vec<Self> {
        vec![
            Self::ValidReblindCommitments,
            Self::ValidCommitmentsMatchSettle0,
            Self::ValidCommitmentsMatchSettle1,
        ]
    }
}

// --- Helpers --- //

/// Generate all verification keys and linking instances for v1
pub fn gen_all_vkeys() -> (Vec<NamedVkey>, Vec<NamedLinkingVkey>) {
    let circuits: Vec<NamedVkey> = V1Circuit::all()
        .into_iter()
        .map(|circuit| NamedVkey {
            name: circuit.name().to_string(),
            vkey: circuit.vkey(),
        })
        .collect();

    let linking_instances: Vec<NamedLinkingVkey> = V1LinkingInstance::all()
        .into_iter()
        .map(|instance| NamedLinkingVkey {
            name: instance.name().to_string(),
            vkey: instance.vkey(),
        })
        .collect();

    (circuits, linking_instances)
}

/// Generate the verification keys for all circuits
///
/// Returns a map from the circuit name to the verification key
fn generate_vkey_for_circuit<T: SingleProverCircuit>() -> VerificationKey {
    let vk = T::verifying_key();
    let vkey = VerificationKey::from(vk.as_ref().clone());
    vkey
}

/// Generate the linking verification key for the `VALID REBLIND <-> VALID COMMITMENTS` link
fn generate_reblind_commitments_link_vkey() -> ProofLinkingVK {
    let group_layout =
        get_reblind_commitments_group_layout::<MAX_BALANCES, MAX_ORDERS, MERKLE_HEIGHT>().unwrap();
    ProofLinkingVK::from(group_layout)
}

/// Generate the linking verification key for the `VALID COMMITMENTS <-> VALID MATCH SETTLE` link
fn generate_commitments_match_settle_link_vkey(party: u64) -> ProofLinkingVK {
    let group_layout =
        get_commitments_match_settle_group_layout::<MAX_BALANCES, MAX_ORDERS>(party).unwrap();
    ProofLinkingVK::from(group_layout)
}

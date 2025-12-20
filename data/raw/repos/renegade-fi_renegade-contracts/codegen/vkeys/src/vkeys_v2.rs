//! Code for generating verification keys for the Renegade circuits (v2)

use renegade_circuit_types_v2::traits::SingleProverCircuit;
use renegade_circuits_v2::zk_circuits::fees::valid_note_redemption::SizedValidNoteRedemption;
use renegade_circuits_v2::zk_circuits::fees::valid_private_protocol_fee_payment::SizedValidPrivateProtocolFeePayment;
use renegade_circuits_v2::zk_circuits::fees::valid_private_relayer_fee_payment::SizedValidPrivateRelayerFeePayment;
use renegade_circuits_v2::zk_circuits::fees::valid_public_protocol_fee_payment::SizedValidPublicProtocolFeePayment;
use renegade_circuits_v2::zk_circuits::fees::valid_public_relayer_fee_payment::SizedValidPublicRelayerFeePayment;
use renegade_circuits_v2::zk_circuits::proof_linking::intent_and_balance::get_group_layout as get_intent_and_balance_settlement_group_layout;
use renegade_circuits_v2::zk_circuits::proof_linking::intent_only::get_intent_public_settlement_group_layout;
use renegade_circuits_v2::zk_circuits::proof_linking::output_balance::get_group_layout as get_output_balance_settlement_group_layout;
use renegade_circuits_v2::zk_circuits::settlement::{
    intent_and_balance_private_settlement::IntentAndBalancePrivateSettlementCircuit,
    intent_and_balance_public_settlement::IntentAndBalancePublicSettlementCircuit,
    intent_only_public_settlement::SizedIntentOnlyPublicSettlementCircuit,
};
use renegade_circuits_v2::zk_circuits::valid_order_cancellation::SizedValidOrderCancellationCircuit;
use renegade_circuits_v2::zk_circuits::valid_withdrawal::SizedValidWithdrawal;
use renegade_circuits_v2::zk_circuits::validity_proofs::new_output_balance::NewOutputBalanceValidityCircuit;
use renegade_circuits_v2::zk_circuits::validity_proofs::{
    intent_and_balance::SizedIntentAndBalanceValidityCircuit,
    intent_and_balance_first_fill::SizedIntentAndBalanceFirstFillValidityCircuit,
    intent_only::IntentOnlyValidityCircuit,
    intent_only_first_fill::IntentOnlyFirstFillValidityCircuit,
    output_balance::SizedOutputBalanceValidityCircuit,
};
use renegade_circuits_v2::zk_circuits::{
    valid_balance_create::ValidBalanceCreate, valid_deposit::SizedValidDeposit,
};
use renegade_constants_v2::MERKLE_HEIGHT;
use std::fmt::{self, Display};

use crate::{NamedLinkingVkey, NamedVkey};
use reference_impl_common::abi_types::{ProofLinkingVK, VerificationKey};

/// The circuit to generate a verification key for
#[derive(Debug, Clone, Copy)]
#[allow(clippy::enum_variant_names)]
enum V2Circuit {
    // --- State Updates --- //
    ValidBalanceCreate,
    ValidDeposit,
    ValidWithdrawal,
    ValidOrderCancellation,
    // --- Fee Payments --- //
    ValidPrivateProtocolFeePayment,
    ValidPrivateRelayerFeePayment,
    ValidPublicProtocolFeePayment,
    ValidPublicRelayerFeePayment,
    ValidNoteRedemption,
    // --- Validity Proofs ---//
    IntentOnlyFirstFillValidity,
    IntentOnlyValidity,
    IntentAndBalanceFirstFillValidity,
    IntentAndBalanceValidity,
    NewOutputBalanceValidity,
    OutputBalanceValidity,
    // --- Settlement Circuits --- //
    IntentOnlyPublicSettlement,
    IntentAndBalancePublicSettlement,
    IntentAndBalancePrivateSettlement,
}

impl Display for V2Circuit {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.name())
    }
}

impl V2Circuit {
    /// Generate the verification key for the circuit
    pub fn vkey(&self) -> VerificationKey {
        match self {
            Self::ValidBalanceCreate => generate_vkey_for_circuit::<ValidBalanceCreate>(),
            Self::ValidDeposit => generate_vkey_for_circuit::<SizedValidDeposit>(),
            Self::ValidWithdrawal => generate_vkey_for_circuit::<SizedValidWithdrawal>(),
            Self::ValidOrderCancellation => {
                generate_vkey_for_circuit::<SizedValidOrderCancellationCircuit>()
            }
            Self::ValidNoteRedemption => generate_vkey_for_circuit::<SizedValidNoteRedemption>(),
            Self::ValidPrivateProtocolFeePayment => {
                generate_vkey_for_circuit::<SizedValidPrivateProtocolFeePayment>()
            }
            Self::ValidPrivateRelayerFeePayment => {
                generate_vkey_for_circuit::<SizedValidPrivateRelayerFeePayment>()
            }
            Self::ValidPublicProtocolFeePayment => {
                generate_vkey_for_circuit::<SizedValidPublicProtocolFeePayment>()
            }
            Self::ValidPublicRelayerFeePayment => {
                generate_vkey_for_circuit::<SizedValidPublicRelayerFeePayment>()
            }
            Self::IntentOnlyFirstFillValidity => {
                generate_vkey_for_circuit::<IntentOnlyFirstFillValidityCircuit>()
            }
            Self::IntentOnlyValidity => {
                generate_vkey_for_circuit::<IntentOnlyValidityCircuit<MERKLE_HEIGHT>>()
            }
            Self::IntentAndBalanceFirstFillValidity => {
                generate_vkey_for_circuit::<SizedIntentAndBalanceFirstFillValidityCircuit>()
            }
            Self::IntentAndBalanceValidity => {
                generate_vkey_for_circuit::<SizedIntentAndBalanceValidityCircuit>()
            }
            Self::NewOutputBalanceValidity => {
                generate_vkey_for_circuit::<NewOutputBalanceValidityCircuit>()
            }
            Self::OutputBalanceValidity => {
                generate_vkey_for_circuit::<SizedOutputBalanceValidityCircuit>()
            }
            Self::IntentOnlyPublicSettlement => {
                generate_vkey_for_circuit::<SizedIntentOnlyPublicSettlementCircuit>()
            }
            Self::IntentAndBalancePublicSettlement => {
                generate_vkey_for_circuit::<IntentAndBalancePublicSettlementCircuit>()
            }
            Self::IntentAndBalancePrivateSettlement => {
                generate_vkey_for_circuit::<IntentAndBalancePrivateSettlementCircuit>()
            }
        }
    }

    /// Get the name of the circuit for the purpose of generating a Solidity constant
    pub fn name(&self) -> &'static str {
        match self {
            Self::ValidBalanceCreate => "VALID_BALANCE_CREATE",
            Self::ValidDeposit => "VALID_DEPOSIT",
            Self::ValidWithdrawal => "VALID_WITHDRAWAL",
            Self::ValidOrderCancellation => "VALID_ORDER_CANCELLATION",
            Self::ValidNoteRedemption => "VALID_NOTE_REDEMPTION",
            Self::ValidPrivateProtocolFeePayment => "VALID_PRIVATE_PROTOCOL_FEE_PAYMENT",
            Self::ValidPrivateRelayerFeePayment => "VALID_PRIVATE_RELAYER_FEE_PAYMENT",
            Self::ValidPublicProtocolFeePayment => "VALID_PUBLIC_PROTOCOL_FEE_PAYMENT",
            Self::ValidPublicRelayerFeePayment => "VALID_PUBLIC_RELAYER_FEE_PAYMENT",
            Self::IntentOnlyFirstFillValidity => "INTENT_ONLY_FIRST_FILL_VALIDITY",
            Self::IntentOnlyValidity => "INTENT_ONLY_VALIDITY",
            Self::IntentAndBalanceFirstFillValidity => "INTENT_AND_BALANCE_FIRST_FILL_VALIDITY",
            Self::IntentAndBalanceValidity => "INTENT_AND_BALANCE_VALIDITY",
            Self::NewOutputBalanceValidity => "NEW_OUTPUT_BALANCE_VALIDITY",
            Self::OutputBalanceValidity => "OUTPUT_BALANCE_VALIDITY",
            Self::IntentOnlyPublicSettlement => "INTENT_ONLY_PUBLIC_SETTLEMENT",
            Self::IntentAndBalancePublicSettlement => "INTENT_AND_BALANCE_PUBLIC_SETTLEMENT",
            Self::IntentAndBalancePrivateSettlement => "INTENT_AND_BALANCE_PRIVATE_SETTLEMENT",
        }
    }

    /// Get all circuits
    pub fn all() -> Vec<Self> {
        vec![
            Self::ValidBalanceCreate,
            Self::ValidDeposit,
            Self::ValidWithdrawal,
            Self::ValidOrderCancellation,
            Self::ValidNoteRedemption,
            Self::ValidPrivateProtocolFeePayment,
            Self::ValidPrivateRelayerFeePayment,
            Self::ValidPublicProtocolFeePayment,
            Self::ValidPublicRelayerFeePayment,
            Self::IntentOnlyFirstFillValidity,
            Self::IntentOnlyValidity,
            Self::IntentAndBalanceFirstFillValidity,
            Self::IntentAndBalanceValidity,
            Self::NewOutputBalanceValidity,
            Self::OutputBalanceValidity,
            Self::IntentOnlyPublicSettlement,
            Self::IntentAndBalancePublicSettlement,
            Self::IntentAndBalancePrivateSettlement,
        ]
    }
}

/// Represents all the linking instances in the Renegade circuits
#[derive(Debug, Clone, Copy)]
pub enum V2LinkingInstance {
    /// The linking instance between intent-only validity and intent-only settlement
    IntentOnlySettlement,
    /// The linking instance between intent and balance validity and intent and balance settlement for the first party
    IntentAndBalanceSettlement0,
    /// The linking instance between intent and balance validity and intent and balance settlement for the second party
    IntentAndBalanceSettlement1,
    /// The linking instance between output balance validity and output balance settlement for the first party
    OutputBalanceSettlement0,
    /// The linking instance between output balance validity and output balance settlement for the second party
    OutputBalanceSettlement1,
}

impl V2LinkingInstance {
    /// Generate a verification key for the linking instance
    pub fn vkey(&self) -> ProofLinkingVK {
        match self {
            Self::IntentOnlySettlement => generate_intent_only_settlement_link_vkey(),
            Self::IntentAndBalanceSettlement0 => {
                generate_intent_and_balance_settlement_link_vkey(0)
            }
            Self::IntentAndBalanceSettlement1 => {
                generate_intent_and_balance_settlement_link_vkey(1)
            }
            Self::OutputBalanceSettlement0 => generate_output_balance_settlement_link_vkey(0),
            Self::OutputBalanceSettlement1 => generate_output_balance_settlement_link_vkey(1),
        }
    }

    /// Get the name of the linking instance
    pub fn name(&self) -> &'static str {
        match self {
            Self::IntentOnlySettlement => "INTENT_ONLY_SETTLEMENT",
            Self::IntentAndBalanceSettlement0 => "INTENT_AND_BALANCE_SETTLEMENT0",
            Self::IntentAndBalanceSettlement1 => "INTENT_AND_BALANCE_SETTLEMENT1",
            Self::OutputBalanceSettlement0 => "OUTPUT_BALANCE_SETTLEMENT0",
            Self::OutputBalanceSettlement1 => "OUTPUT_BALANCE_SETTLEMENT1",
        }
    }

    /// Get all linking instances
    pub fn all() -> Vec<Self> {
        vec![
            Self::IntentOnlySettlement,
            Self::IntentAndBalanceSettlement0,
            Self::IntentAndBalanceSettlement1,
            Self::OutputBalanceSettlement0,
            Self::OutputBalanceSettlement1,
        ]
    }
}

// --- Helpers --- //

/// Generate all verification keys and linking instances for v2
pub fn gen_all_vkeys() -> (Vec<NamedVkey>, Vec<NamedLinkingVkey>) {
    let circuits: Vec<NamedVkey> = V2Circuit::all()
        .into_iter()
        .map(|circuit| NamedVkey {
            name: circuit.name().to_string(),
            vkey: circuit.vkey(),
        })
        .collect();

    let linking_instances: Vec<NamedLinkingVkey> = V2LinkingInstance::all()
        .into_iter()
        .map(|instance| NamedLinkingVkey {
            name: instance.name().to_string(),
            vkey: instance.vkey(),
        })
        .collect();

    (circuits, linking_instances)
}

// --- Helpers --- //

/// Generate the verification keys for all circuits
///
/// Returns a map from the circuit name to the verification key
fn generate_vkey_for_circuit<T: SingleProverCircuit>() -> VerificationKey {
    let vk = T::verifying_key();
    let vkey = VerificationKey::from(vk.as_ref().clone());
    vkey
}

// --- Proof Linking Keys --- //

/// Generate the link verification key for the intent-only settlement linking instance
fn generate_intent_only_settlement_link_vkey() -> ProofLinkingVK {
    let layout = get_intent_public_settlement_group_layout::<MERKLE_HEIGHT>().unwrap();
    ProofLinkingVK::from(layout)
}

/// Generate the link verification key for the intent and balance settlement linking instance for the given party
fn generate_intent_and_balance_settlement_link_vkey(party: u8) -> ProofLinkingVK {
    let layout = get_intent_and_balance_settlement_group_layout::<MERKLE_HEIGHT>(party).unwrap();
    ProofLinkingVK::from(layout)
}

/// Generate the link verification key for the output balance settlement linking instance for the given party
fn generate_output_balance_settlement_link_vkey(party: u8) -> ProofLinkingVK {
    let layout = get_output_balance_settlement_group_layout::<MERKLE_HEIGHT>(party).unwrap();
    ProofLinkingVK::from(layout)
}

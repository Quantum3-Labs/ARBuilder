//! Proof bundle conversion helpers

use super::*;
use crate::v2::IDarkpoolV2::{self, SignatureWithNonce};
use crate::v2::BN254::G1Point;
use renegade_circuit_types_v2::{
    note::NoteCiphertext, traits::BaseType, PlonkLinkProof, PlonkProof,
};
use renegade_circuits_v2::zk_circuits::fees::valid_note_redemption::ValidNoteRedemptionStatement;
use renegade_circuits_v2::zk_circuits::fees::valid_private_protocol_fee_payment::ValidPrivateProtocolFeePaymentStatement;
use renegade_circuits_v2::zk_circuits::{
    fees::{
        valid_private_relayer_fee_payment::ValidPrivateRelayerFeePaymentStatement,
        valid_public_protocol_fee_payment::ValidPublicProtocolFeePaymentStatement,
        valid_public_relayer_fee_payment::ValidPublicRelayerFeePaymentStatement,
    },
    settlement::{
        intent_and_balance_private_settlement::IntentAndBalancePrivateSettlementStatement,
        intent_and_balance_public_settlement::IntentAndBalancePublicSettlementStatement,
        intent_only_public_settlement::IntentOnlyPublicSettlementStatement,
    },
    valid_balance_create::ValidBalanceCreateStatement,
    valid_deposit::ValidDepositStatement,
    valid_order_cancellation::ValidOrderCancellationStatement,
    valid_withdrawal::ValidWithdrawalStatement,
    validity_proofs::{
        intent_and_balance::IntentAndBalanceValidityStatement,
        intent_and_balance_first_fill::IntentAndBalanceFirstFillValidityStatement,
        intent_only::IntentOnlyValidityStatement,
        intent_only_first_fill::IntentOnlyFirstFillValidityStatement,
        new_output_balance::NewOutputBalanceValidityStatement,
        output_balance::OutputBalanceValidityStatement,
    },
};
use renegade_crypto_v2::fields::scalar_to_u256;

use ark_ec::AffineRepr;
use ark_ff::{BigInteger, PrimeField};
use jf_primitives::pcs::prelude::Commitment as JfCommitment;
use renegade_constants_v2::MERKLE_HEIGHT;

// -----------------
// | Proof Bundles |
// -----------------

impl IDarkpoolV2::NewBalanceDepositProofBundle {
    /// Create a new proof bundle from a statement and proof
    pub fn new(statement: ValidBalanceCreateStatement, proof: PlonkProof) -> Self {
        let merkle_depth = U256::from(MERKLE_HEIGHT);
        Self {
            // We use the default merkle height for now
            merkleDepth: merkle_depth,
            statement: statement.into(),
            proof: proof.into(),
        }
    }
}

impl IDarkpoolV2::DepositProofBundle {
    /// Create a new proof bundle from a statement and proof
    pub fn new(statement: ValidDepositStatement, proof: PlonkProof) -> Self {
        let merkle_depth = U256::from(MERKLE_HEIGHT);
        Self {
            // We use the default merkle height for now
            merkleDepth: merkle_depth,
            statement: statement.into(),
            proof: proof.into(),
        }
    }
}

impl IDarkpoolV2::WithdrawalProofBundle {
    /// Create a new proof bundle from a statement and proof
    pub fn new(statement: ValidWithdrawalStatement, proof: PlonkProof) -> Self {
        let merkle_depth = U256::from(MERKLE_HEIGHT);
        Self {
            // We use the default merkle height for now
            merkleDepth: merkle_depth,
            statement: statement.into(),
            proof: proof.into(),
        }
    }
}

impl IDarkpoolV2::OrderCancellationProofBundle {
    /// Create a new proof bundle from a statement and proof
    pub fn new(statement: ValidOrderCancellationStatement, proof: PlonkProof) -> Self {
        Self {
            statement: statement.into(),
            proof: proof.into(),
        }
    }
}

impl IDarkpoolV2::PublicRelayerFeePaymentProofBundle {
    /// Create a new proof bundle from a statement and proof
    pub fn new(statement: ValidPublicRelayerFeePaymentStatement, proof: PlonkProof) -> Self {
        Self {
            // We use the default merkle height for now
            merkleDepth: U256::from(MERKLE_HEIGHT),
            statement: statement.into(),
            proof: proof.into(),
        }
    }
}

impl IDarkpoolV2::PublicProtocolFeePaymentProofBundle {
    /// Create a new proof bundle from a statement and proof
    pub fn new(statement: ValidPublicProtocolFeePaymentStatement, proof: PlonkProof) -> Self {
        Self {
            // We use the default merkle height for now
            merkleDepth: U256::from(MERKLE_HEIGHT),
            statement: statement.into(),
            proof: proof.into(),
        }
    }
}

impl IDarkpoolV2::PrivateRelayerFeePaymentProofBundle {
    /// Create a new proof bundle from a statement and proof
    pub fn new(
        note_ciphertext: NoteCiphertext,
        relayer_ciphertext_signature: SignatureWithNonce,
        statement: ValidPrivateRelayerFeePaymentStatement,
        proof: PlonkProof,
    ) -> Self {
        Self {
            // We use the default merkle height for now
            merkleDepth: U256::from(MERKLE_HEIGHT),
            noteCiphertext: note_ciphertext.into(),
            relayerCiphertextSignature: relayer_ciphertext_signature,
            statement: statement.into(),
            proof: proof.into(),
        }
    }
}

impl IDarkpoolV2::PrivateProtocolFeePaymentProofBundle {
    /// Create a new proof bundle from a statement and proof
    pub fn new(statement: ValidPrivateProtocolFeePaymentStatement, proof: PlonkProof) -> Self {
        Self {
            // We use the default merkle height for now
            merkleDepth: U256::from(MERKLE_HEIGHT),
            statement: statement.into(),
            proof: proof.into(),
        }
    }
}

impl IDarkpoolV2::NoteRedemptionProofBundle {
    /// Create a new proof bundle from a statement and proof
    pub fn new(statement: ValidNoteRedemptionStatement, proof: PlonkProof) -> Self {
        Self {
            statement: statement.into(),
            proof: proof.into(),
        }
    }
}

// -------------------
// | Statement Types |
// -------------------

// --- State Update Statements --- //

impl From<ValidBalanceCreateStatement> for IDarkpoolV2::ValidBalanceCreateStatement {
    fn from(statement: ValidBalanceCreateStatement) -> Self {
        Self {
            deposit: statement.deposit.into(),
            newBalanceCommitment: scalar_to_u256(&statement.balance_commitment),
            newBalancePublicShares: size_vec(
                statement
                    .new_balance_share
                    .to_scalars()
                    .into_iter()
                    .map(|s| scalar_to_u256(&s))
                    .collect(),
            ),
            recoveryId: scalar_to_u256(&statement.recovery_id),
        }
    }
}

impl From<ValidDepositStatement> for IDarkpoolV2::ValidDepositStatement {
    fn from(statement: ValidDepositStatement) -> Self {
        Self {
            deposit: statement.deposit.into(),
            merkleRoot: scalar_to_u256(&statement.merkle_root),
            oldBalanceNullifier: scalar_to_u256(&statement.old_balance_nullifier),
            newBalanceCommitment: scalar_to_u256(&statement.new_balance_commitment),
            recoveryId: scalar_to_u256(&statement.recovery_id),
            newAmountShare: scalar_to_u256(&statement.new_amount_share),
        }
    }
}

impl From<ValidWithdrawalStatement> for IDarkpoolV2::ValidWithdrawalStatement {
    fn from(statement: ValidWithdrawalStatement) -> Self {
        Self {
            withdrawal: statement.withdrawal.into(),
            merkleRoot: scalar_to_u256(&statement.merkle_root),
            oldBalanceNullifier: scalar_to_u256(&statement.old_balance_nullifier),
            newBalanceCommitment: scalar_to_u256(&statement.new_balance_commitment),
            recoveryId: scalar_to_u256(&statement.recovery_id),
            newAmountShare: scalar_to_u256(&statement.new_amount_share),
        }
    }
}

impl From<ValidOrderCancellationStatement> for IDarkpoolV2::ValidOrderCancellationStatement {
    fn from(statement: ValidOrderCancellationStatement) -> Self {
        Self {
            owner: statement.owner,
            merkleRoot: scalar_to_u256(&statement.merkle_root),
            oldIntentNullifier: scalar_to_u256(&statement.old_intent_nullifier),
        }
    }
}

impl From<ValidPublicRelayerFeePaymentStatement>
    for IDarkpoolV2::ValidPublicRelayerFeePaymentStatement
{
    fn from(statement: ValidPublicRelayerFeePaymentStatement) -> Self {
        Self {
            merkleRoot: scalar_to_u256(&statement.merkle_root),
            oldBalanceNullifier: scalar_to_u256(&statement.old_balance_nullifier),
            newBalanceCommitment: scalar_to_u256(&statement.new_balance_commitment),
            recoveryId: scalar_to_u256(&statement.recovery_id),
            newRelayerFeeBalanceShare: scalar_to_u256(&statement.new_relayer_fee_balance_share),
            note: statement.note.into(),
        }
    }
}

impl From<ValidPublicProtocolFeePaymentStatement>
    for IDarkpoolV2::ValidPublicProtocolFeePaymentStatement
{
    fn from(statement: ValidPublicProtocolFeePaymentStatement) -> Self {
        Self {
            merkleRoot: scalar_to_u256(&statement.merkle_root),
            oldBalanceNullifier: scalar_to_u256(&statement.old_balance_nullifier),
            newBalanceCommitment: scalar_to_u256(&statement.new_balance_commitment),
            recoveryId: scalar_to_u256(&statement.recovery_id),
            newProtocolFeeBalanceShare: scalar_to_u256(&statement.new_protocol_fee_balance_share),
            note: statement.note.into(),
        }
    }
}

impl From<ValidPrivateRelayerFeePaymentStatement>
    for IDarkpoolV2::ValidPrivateRelayerFeePaymentStatement
{
    fn from(statement: ValidPrivateRelayerFeePaymentStatement) -> Self {
        Self {
            merkleRoot: scalar_to_u256(&statement.merkle_root),
            relayerFeeReceiver: statement.relayer_fee_receiver,
            noteCommitment: scalar_to_u256(&statement.note_commitment),
            oldBalanceNullifier: scalar_to_u256(&statement.old_balance_nullifier),
            newBalanceCommitment: scalar_to_u256(&statement.new_balance_commitment),
            recoveryId: scalar_to_u256(&statement.recovery_id),
            newRelayerFeeBalanceShare: scalar_to_u256(&statement.new_relayer_fee_balance_share),
        }
    }
}

impl From<ValidPrivateProtocolFeePaymentStatement>
    for IDarkpoolV2::ValidPrivateProtocolFeePaymentStatement
{
    fn from(statement: ValidPrivateProtocolFeePaymentStatement) -> Self {
        Self {
            merkleRoot: scalar_to_u256(&statement.merkle_root),
            oldBalanceNullifier: scalar_to_u256(&statement.old_balance_nullifier),
            newBalanceCommitment: scalar_to_u256(&statement.new_balance_commitment),
            recoveryId: scalar_to_u256(&statement.recovery_id),
            newProtocolFeeBalanceShare: scalar_to_u256(&statement.new_protocol_fee_balance_share),
            protocolFeeReceiver: statement.protocol_fee_receiver,
            noteCommitment: scalar_to_u256(&statement.note_commitment),
            noteCiphertext: statement.note_ciphertext.into(),
            protocolEncryptionKey: statement.protocol_encryption_key.into(),
        }
    }
}

impl From<ValidNoteRedemptionStatement> for IDarkpoolV2::ValidNoteRedemptionStatement {
    fn from(statement: ValidNoteRedemptionStatement) -> Self {
        Self {
            note: statement.note.into(),
            noteRoot: scalar_to_u256(&statement.note_root),
            noteNullifier: scalar_to_u256(&statement.note_nullifier),
        }
    }
}

// --- Validity Statements --- //

impl From<IntentOnlyFirstFillValidityStatement>
    for IDarkpoolV2::IntentOnlyValidityStatementFirstFill
{
    fn from(statement: IntentOnlyFirstFillValidityStatement) -> Self {
        Self {
            intentOwner: statement.owner,
            intentPrivateCommitment: scalar_to_u256(&statement.intent_private_commitment),
            recoveryId: scalar_to_u256(&statement.recovery_id),
            intentPublicShare: statement.intent_public_share.into(),
        }
    }
}

impl From<IntentOnlyValidityStatement> for IDarkpoolV2::IntentOnlyValidityStatement {
    fn from(statement: IntentOnlyValidityStatement) -> Self {
        Self {
            intentOwner: statement.owner,
            merkleRoot: scalar_to_u256(&statement.merkle_root),
            oldIntentNullifier: scalar_to_u256(&statement.old_intent_nullifier),
            newAmountShare: scalar_to_u256(&statement.new_amount_public_share),
            newIntentPartialCommitment: statement.new_intent_partial_commitment.into(),
            recoveryId: scalar_to_u256(&statement.recovery_id),
        }
    }
}

impl From<IntentAndBalanceFirstFillValidityStatement>
    for IDarkpoolV2::IntentAndBalanceValidityStatementFirstFill
{
    fn from(statement: IntentAndBalanceFirstFillValidityStatement) -> Self {
        Self {
            merkleRoot: scalar_to_u256(&statement.merkle_root),
            intentAndAuthorizingAddressCommitment: scalar_to_u256(
                &statement.intent_and_authorizing_address_commitment,
            ),
            intentPublicShare: statement.intent_public_share.into(),
            intentPrivateShareCommitment: scalar_to_u256(
                &statement.intent_private_share_commitment,
            ),
            intentRecoveryId: scalar_to_u256(&statement.intent_recovery_id),
            balancePartialCommitment: statement.balance_partial_commitment.into(),
            newOneTimeAddressPublicShare: scalar_to_u256(
                &statement.new_one_time_address_public_share,
            ),
            oldBalanceNullifier: scalar_to_u256(&statement.old_balance_nullifier),
            balanceRecoveryId: scalar_to_u256(&statement.balance_recovery_id),
            oneTimeAuthorizingAddress: statement.one_time_authorizing_address,
        }
    }
}

impl From<IntentAndBalanceValidityStatement> for IDarkpoolV2::IntentAndBalanceValidityStatement {
    fn from(statement: IntentAndBalanceValidityStatement) -> Self {
        Self {
            intentMerkleRoot: scalar_to_u256(&statement.intent_merkle_root),
            oldIntentNullifier: scalar_to_u256(&statement.old_intent_nullifier),
            newIntentPartialCommitment: statement.new_intent_partial_commitment.into(),
            intentRecoveryId: scalar_to_u256(&statement.intent_recovery_id),
            balanceMerkleRoot: scalar_to_u256(&statement.balance_merkle_root),
            oldBalanceNullifier: scalar_to_u256(&statement.old_balance_nullifier),
            balancePartialCommitment: statement.balance_partial_commitment.into(),
            balanceRecoveryId: scalar_to_u256(&statement.balance_recovery_id),
        }
    }
}

impl From<NewOutputBalanceValidityStatement> for IDarkpoolV2::NewOutputBalanceValidityStatement {
    fn from(statement: NewOutputBalanceValidityStatement) -> Self {
        Self {
            preMatchBalanceShares: statement.pre_match_balance_shares.into(),
            newBalancePartialCommitment: statement.new_balance_partial_commitment.into(),
            recoveryId: scalar_to_u256(&statement.recovery_id),
        }
    }
}

impl From<OutputBalanceValidityStatement> for IDarkpoolV2::OutputBalanceValidityStatement {
    fn from(statement: OutputBalanceValidityStatement) -> Self {
        Self {
            merkleRoot: scalar_to_u256(&statement.merkle_root),
            oldBalanceNullifier: scalar_to_u256(&statement.old_balance_nullifier),
            newPartialCommitment: statement.new_partial_commitment.into(),
            recoveryId: scalar_to_u256(&statement.recovery_id),
        }
    }
}

// --- Settlement Statements --- //

impl From<IntentOnlyPublicSettlementStatement>
    for IDarkpoolV2::IntentOnlyPublicSettlementStatement
{
    fn from(statement: IntentOnlyPublicSettlementStatement) -> Self {
        Self {
            obligation: statement.settlement_obligation.into(),
            relayerFee: statement.relayer_fee.into(),
            relayerFeeRecipient: statement.relayer_fee_recipient,
        }
    }
}

impl From<IntentAndBalancePublicSettlementStatement>
    for IDarkpoolV2::IntentAndBalancePublicSettlementStatement
{
    fn from(statement: IntentAndBalancePublicSettlementStatement) -> Self {
        Self {
            inBalancePublicShares: statement.in_balance_public_shares.into(),
            outBalancePublicShares: statement.out_balance_public_shares.into(),
            relayerFee: statement.relayer_fee.into(),
            relayerFeeRecipient: statement.relayer_fee_recipient,
            settlementObligation: statement.settlement_obligation.into(),
            amountPublicShare: scalar_to_u256(&statement.amount_public_share),
        }
    }
}

impl From<IntentAndBalancePrivateSettlementStatement>
    for IDarkpoolV2::IntentAndBalancePrivateSettlementStatement
{
    fn from(statement: IntentAndBalancePrivateSettlementStatement) -> Self {
        Self {
            newAmountPublicShare0: scalar_to_u256(&statement.new_amount_public_share0),
            newInBalancePublicShares0: statement.new_in_balance_public_shares0.into(),
            newOutBalancePublicShares0: statement.new_out_balance_public_shares0.into(),
            newAmountPublicShare1: scalar_to_u256(&statement.new_amount_public_share1),
            newInBalancePublicShares1: statement.new_in_balance_public_shares1.into(),
            newOutBalancePublicShares1: statement.new_out_balance_public_shares1.into(),
            relayerFee0: statement.relayer_fee0.into(),
            relayerFee1: statement.relayer_fee1.into(),
            protocolFee: statement.protocol_fee.into(),
        }
    }
}

// --------------------------
// | Plonk Type Conversions |
// --------------------------

impl From<PlonkProof> for IDarkpoolV2::PlonkProof {
    fn from(proof: PlonkProof) -> Self {
        let evals = proof.poly_evals;
        Self {
            wireComms: size_vec(
                proof
                    .wires_poly_comms
                    .into_iter()
                    .map(convert_jf_commitment)
                    .collect(),
            ),
            zComm: convert_jf_commitment(proof.prod_perm_poly_comm),
            quotientComms: size_vec(
                proof
                    .split_quot_poly_comms
                    .into_iter()
                    .map(convert_jf_commitment)
                    .collect(),
            ),
            wZeta: convert_jf_commitment(proof.opening_proof),
            wZetaOmega: convert_jf_commitment(proof.shifted_opening_proof),
            wireEvals: size_vec(evals.wires_evals.into_iter().map(fr_to_u256).collect()),
            sigmaEvals: size_vec(evals.wire_sigma_evals.into_iter().map(fr_to_u256).collect()),
            zBar: fr_to_u256(evals.perm_next_eval),
        }
    }
}

impl From<PlonkLinkProof> for IDarkpoolV2::LinkingProof {
    fn from(proof: PlonkLinkProof) -> Self {
        Self {
            linkingQuotientPolyComm: convert_jf_commitment(proof.quotient_commitment),
            linkingPolyOpening: convert_g1_point(proof.opening_proof.proof),
        }
    }
}

// ----------------------
// | Conversion Helpers |
// ----------------------

/// Size a vector of values to be a known fixed size
pub(crate) fn size_vec<const N: usize, T>(vec: Vec<T>) -> [T; N] {
    let size = vec.len();
    if size != N {
        panic!("vector is not the correct size: expected {N}, got {size}");
    }
    vec.try_into().map_err(|_| ()).unwrap()
}

/// Convert a point in the BN254 base field to a Uint256
fn base_field_to_u256(fq: ark_bn254::Fq) -> U256 {
    let bytes = fq.into_bigint().to_bytes_be();
    bytes_to_u256(&bytes)
}

/// Convert a set of big endian bytes to a Uint256
///
/// Handles padding as necessary
fn bytes_to_u256(bytes: &[u8]) -> U256 {
    let mut buf = [0u8; 32];
    buf[..bytes.len()].copy_from_slice(bytes);
    U256::from_be_bytes(buf)
}

/// Convert a `Fr` to a `U256`
fn fr_to_u256(fr: ark_bn254::Fr) -> U256 {
    let bytes = fr.into_bigint().to_bytes_be();
    bytes_to_u256(&bytes)
}

/// Convert a point on the BN254 curve to a `G1Point` in the contract's format
fn convert_g1_point(point: ark_bn254::G1Affine) -> G1Point {
    let x = point.x().expect("x is zero");
    let y = point.y().expect("y is zero");

    G1Point {
        x: base_field_to_u256(*x),
        y: base_field_to_u256(*y),
    }
}

/// Convert a `JfCommitment` to a `G1Point`
fn convert_jf_commitment(commitment: JfCommitment<ark_bn254::Bn254>) -> G1Point {
    convert_g1_point(commitment.0)
}

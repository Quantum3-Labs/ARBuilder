//! Note redemption tests

use alloy::primitives::U256;
use eyre::Result;
use renegade_abi::v2::IDarkpoolV2::NoteRedemptionProofBundle;
use renegade_circuit_types::{PlonkProof, note::Note};
use renegade_circuits::{
    singleprover_prove,
    zk_circuits::fees::valid_note_redemption::{
        SizedValidNoteRedemption, ValidNoteRedemptionStatement, ValidNoteRedemptionWitness,
    },
};
use renegade_common::types::merkle::MerkleAuthenticationPath;
use test_helpers::{assert_eq_result, integration_test_async};

use crate::{
    test_args::TestArgs,
    tests::state_updates::{fees::private_protocol_fee, setup_private_intent_private_balance},
    util::{merkle::parse_merkle_opening_from_receipt, transactions::wait_for_tx_success},
};

/// Test redeeming a note
pub async fn test_redeem_note(args: TestArgs) -> Result<()> {
    let mut state_elements = setup_private_intent_private_balance(&args).await?;

    // Pay a private fee to generate a note
    let bal = &mut state_elements.output_balance;
    let opening = state_elements.output_balance_opening;
    let (note, proof_bundle) =
        private_protocol_fee::build_proof_bundle_with_note(bal, &opening, &args).await?;

    let tx = args.darkpool.payPrivateProtocolFee(proof_bundle);
    let receipt = wait_for_tx_success(tx).await?;
    let note_opening = parse_merkle_opening_from_receipt(note.commitment(), &receipt)?;

    // Redeem the note
    let recipient = note.receiver;
    let mint = note.mint;
    let amt = U256::from(note.amount);
    let proof_bundle = generate_proof_bundle(note, note_opening)?;

    let recipient_bal_before = args.balance(recipient, mint).await?;
    let tx = args.darkpool.redeemNote(proof_bundle);
    wait_for_tx_success(tx).await?;
    let recipient_bal_after = args.balance(recipient, mint).await?;

    // Verify the balance update
    assert_eq_result!(recipient_bal_after, recipient_bal_before + amt)
}
integration_test_async!(test_redeem_note);

// -----------
// | Helpers |
// -----------

/// Generate a note redemption proof bundle
pub fn generate_proof_bundle(
    note: Note,
    note_opening: MerkleAuthenticationPath,
) -> Result<NoteRedemptionProofBundle> {
    let (statement, proof) = generate_note_redemption_proof(note, note_opening)?;
    Ok(NoteRedemptionProofBundle::new(statement, proof))
}

/// Generate a proof of note redemption
fn generate_note_redemption_proof(
    note: Note,
    note_opening: MerkleAuthenticationPath,
) -> Result<(ValidNoteRedemptionStatement, PlonkProof)> {
    let witness = ValidNoteRedemptionWitness {
        note_opening: note_opening.clone().into(),
    };

    let note_nullifier = note.nullifier();
    let statement = ValidNoteRedemptionStatement {
        note,
        note_root: note_opening.compute_root(),
        note_nullifier,
    };

    // Prove the relation
    let proof = singleprover_prove::<SizedValidNoteRedemption>(&witness, &statement)?;
    Ok((statement, proof))
}

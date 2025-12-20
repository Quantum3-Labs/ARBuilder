// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import { BN254 } from "solidity-bn254/BN254.sol";
import { DarkpoolTestBase } from "./DarkpoolTestBase.sol";
import { IDarkpool } from "darkpoolv1-interfaces/IDarkpool.sol";
import { NullifierLib as NullifierSetLib } from "renegade-lib/NullifierSet.sol";
import { WalletOperations } from "darkpoolv1-lib/WalletOperations.sol";
import { PlonkProof } from "renegade-lib/verifier/Types.sol";
import { PartyMatchPayload, MatchProofs, MatchLinkingProofs } from "darkpoolv1-types/Settlement.sol";
import { TransferAuthorization } from "darkpoolv1-types/Transfers.sol";
import {
    ValidWalletCreateStatement,
    ValidWalletUpdateStatement,
    ValidMatchSettleStatement,
    ValidMatchSettleWithCommitmentsStatement
} from "darkpoolv1-lib/PublicInputs.sol";

contract SettleMatchTest is DarkpoolTestBase {
    // --- Settle Match --- //

    /// @notice Test settling a match
    function test_settleMatch_validMatch() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory party0Payload,
            PartyMatchPayload memory party1Payload,
            ValidMatchSettleStatement memory statement,
            MatchProofs memory proofs,
            MatchLinkingProofs memory linkingProofs
        ) = settleMatchCalldata(merkleRoot);

        // Process the match
        darkpool.processMatchSettle(party0Payload, party1Payload, statement, proofs, linkingProofs);

        // Check that the nullifiers are used
        BN254.ScalarField nullifier0 = party0Payload.validReblindStatement.originalSharesNullifier;
        BN254.ScalarField nullifier1 = party1Payload.validReblindStatement.originalSharesNullifier;
        assertEq(darkpool.nullifierSpent(nullifier0), true);
        assertEq(darkpool.nullifierSpent(nullifier1), true);
    }

    /// @notice Test settling a match with commitments attached
    function test_settleMatchWithCommitments_validMatch() public {
        vm.skip(true, "Match with commitments tests are disabled");

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory party0Payload,
            PartyMatchPayload memory party1Payload,
            ValidMatchSettleWithCommitmentsStatement memory statement,
            MatchProofs memory proofs,
            MatchLinkingProofs memory linkingProofs
        ) = settleMatchWithCommitmentsCalldata(merkleRoot);

        // Process the match
        darkpool.processMatchSettleWithCommitments(party0Payload, party1Payload, statement, proofs, linkingProofs);

        // Check that the nullifiers are used
        BN254.ScalarField nullifier0 = party0Payload.validReblindStatement.originalSharesNullifier;
        BN254.ScalarField nullifier1 = party1Payload.validReblindStatement.originalSharesNullifier;
        assertEq(darkpool.nullifierSpent(nullifier0), true);
        assertEq(darkpool.nullifierSpent(nullifier1), true);
    }

    // --- Invalid Test Cases --- //

    /// @notice Test settling a match with an invalid proof
    function test_settleMatch_invalidProof() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory party0Payload,
            PartyMatchPayload memory party1Payload,
            ValidMatchSettleStatement memory statement,
            MatchProofs memory proofs,
            MatchLinkingProofs memory linkingProofs
        ) = settleMatchCalldata(merkleRoot);

        // Should fail
        vm.expectRevert(IDarkpool.VerificationFailed.selector);
        darkpoolRealVerifier.processMatchSettle(party0Payload, party1Payload, statement, proofs, linkingProofs);
    }

    /// @notice Test settling a match with a duplicate public blinder share
    function test_settleMatch_duplicateBlinder() public {
        // Create a wallet using the public blinder
        (ValidWalletCreateStatement memory createStatement, PlonkProof memory createProof) = createWalletCalldata();
        darkpool.createWallet(createStatement, createProof);
        BN254.ScalarField publicBlinder = createStatement.publicShares[createStatement.publicShares.length - 1];

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory party0Payload,
            PartyMatchPayload memory party1Payload,
            ValidMatchSettleStatement memory statement,
            MatchProofs memory proofs,
            MatchLinkingProofs memory linkingProofs
        ) = settleMatchCalldata(merkleRoot);

        if (vm.randomBool()) {
            // Party 0 uses the duplicate public blinder
            statement.firstPartyPublicShares[statement.firstPartyPublicShares.length - 1] = publicBlinder;
        } else {
            // Party 1 uses the duplicate public blinder
            statement.secondPartyPublicShares[statement.secondPartyPublicShares.length - 1] = publicBlinder;
        }

        // Should fail
        vm.expectRevert(NullifierSetLib.NullifierAlreadySpent.selector);
        darkpool.processMatchSettle(party0Payload, party1Payload, statement, proofs, linkingProofs);
    }

    /// @notice Test settling a match in which the nullifier of one party is spent
    function test_settleMatch_spentNullifier() public {
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        BN254.ScalarField nullifier = randomScalar();

        // Update a wallet using the nullifier
        (bytes memory newSharesCommitmentSig, ValidWalletUpdateStatement memory statement, PlonkProof memory proof) =
            updateWalletCalldata();
        statement.previousNullifier = nullifier;
        statement.merkleRoot = merkleRoot;
        TransferAuthorization memory transferAuthorization = emptyTransferAuthorization();
        darkpool.updateWallet(newSharesCommitmentSig, transferAuthorization, statement, proof);

        // Setup calldata
        (
            PartyMatchPayload memory party0Payload,
            PartyMatchPayload memory party1Payload,
            ValidMatchSettleStatement memory matchStatement,
            MatchProofs memory matchProofs,
            MatchLinkingProofs memory linkingProofs
        ) = settleMatchCalldata(merkleRoot);

        if (vm.randomBool()) {
            // Party 0 uses the invalid nullifier
            party0Payload.validReblindStatement.originalSharesNullifier = nullifier;
        } else {
            // Party 1 uses the invalid nullifier
            party1Payload.validReblindStatement.originalSharesNullifier = nullifier;
        }

        // Should fail
        vm.expectRevert(NullifierSetLib.NullifierAlreadySpent.selector);
        darkpool.processMatchSettle(party0Payload, party1Payload, matchStatement, matchProofs, linkingProofs);
    }

    /// @notice Test settling a match in which one party is using an invalid Merkle root
    function test_settleMatch_invalidMerkleRoot() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory party0Payload,
            PartyMatchPayload memory party1Payload,
            ValidMatchSettleStatement memory statement,
            MatchProofs memory proofs,
            MatchLinkingProofs memory linkingProofs
        ) = settleMatchCalldata(merkleRoot);

        if (vm.randomBool()) {
            // Party 0 has an invalid Merkle root
            party0Payload.validReblindStatement.merkleRoot = randomScalar();
        } else {
            // Party 1 has an invalid Merkle root
            party1Payload.validReblindStatement.merkleRoot = randomScalar();
        }

        // Should fail
        vm.expectRevert(WalletOperations.MerkleRootNotInHistory.selector);
        darkpool.processMatchSettle(party0Payload, party1Payload, statement, proofs, linkingProofs);
    }

    /// @notice Test settling a match in which one party's settlement indices are inconsistent
    function test_settleMatch_inconsistentIndices() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory party0Payload,
            PartyMatchPayload memory party1Payload,
            ValidMatchSettleStatement memory statement,
            MatchProofs memory proofs,
            MatchLinkingProofs memory linkingProofs
        ) = settleMatchCalldata(merkleRoot);

        if (vm.randomBool()) {
            // Party 0 has an invalid settlement indices
            party0Payload.validCommitmentsStatement.indices = randomOrderSettlementIndices();
        } else {
            // Party 1 has an invalid settlement indices
            party1Payload.validCommitmentsStatement.indices = randomOrderSettlementIndices();
        }

        // Should fail
        vm.expectRevert(IDarkpool.InvalidOrderSettlementIndices.selector);
        darkpool.processMatchSettle(party0Payload, party1Payload, statement, proofs, linkingProofs);
    }

    /// @notice Test settling a match in which the protocol fee rate is invalid
    function test_settleMatch_invalidProtocolFeeRate() public {
        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory party0Payload,
            PartyMatchPayload memory party1Payload,
            ValidMatchSettleStatement memory statement,
            MatchProofs memory proofs,
            MatchLinkingProofs memory linkingProofs
        ) = settleMatchCalldata(merkleRoot);
        statement.protocolFeeRate = BN254.ScalarField.unwrap(randomScalar());

        // Should fail
        vm.expectRevert(IDarkpool.InvalidProtocolFeeRate.selector);
        darkpool.processMatchSettle(party0Payload, party1Payload, statement, proofs, linkingProofs);
    }

    /// @notice Test settling a match with commitments in which one party's settlement indices are inconsistent
    function test_settleMatchWithCommitments_inconsistentIndices() public {
        vm.skip(true, "Match with commitments tests are disabled");

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory party0Payload,
            PartyMatchPayload memory party1Payload,
            ValidMatchSettleWithCommitmentsStatement memory statement,
            MatchProofs memory proofs,
            MatchLinkingProofs memory linkingProofs
        ) = settleMatchWithCommitmentsCalldata(merkleRoot);

        bytes memory revertString;
        if (vm.randomBool()) {
            // Party 0 has an invalid settlement indices
            party0Payload.validCommitmentsStatement.indices = randomOrderSettlementIndices();
            revertString = "Invalid party 0 order settlement indices";
        } else {
            // Party 1 has an invalid settlement indices
            party1Payload.validCommitmentsStatement.indices = randomOrderSettlementIndices();
            revertString = "Invalid party 1 order settlement indices";
        }

        // Should fail
        vm.expectRevert(revertString);
        darkpool.processMatchSettleWithCommitments(party0Payload, party1Payload, statement, proofs, linkingProofs);
    }

    /// @notice Test settling a match with commitments in which one party's private share commitment is invalid
    function test_settleMatchWithCommitments_invalidPrivateShareCommitment() public {
        vm.skip(true, "Match with commitments tests are disabled");

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory party0Payload,
            PartyMatchPayload memory party1Payload,
            ValidMatchSettleWithCommitmentsStatement memory statement,
            MatchProofs memory proofs,
            MatchLinkingProofs memory linkingProofs
        ) = settleMatchWithCommitmentsCalldata(merkleRoot);

        bytes memory revertString;
        if (vm.randomBool()) {
            // Party 0 has an invalid private share commitment
            party0Payload.validReblindStatement.newPrivateShareCommitment = randomScalar();
            revertString = "Invalid party 0 private share commitment";
        } else {
            // Party 1 has an invalid private share commitment
            party1Payload.validReblindStatement.newPrivateShareCommitment = randomScalar();
            revertString = "Invalid party 1 private share commitment";
        }

        // Should fail
        vm.expectRevert(revertString);
        darkpool.processMatchSettleWithCommitments(party0Payload, party1Payload, statement, proofs, linkingProofs);
    }

    /// @notice Test settling a match with commitments in which the protocol fee rate is invalid
    function test_settleMatchWithCommitments_invalidProtocolFeeRate() public {
        vm.skip(true, "Match with commitments tests are disabled");

        // Setup calldata
        BN254.ScalarField merkleRoot = darkpool.getMerkleRoot();
        (
            PartyMatchPayload memory party0Payload,
            PartyMatchPayload memory party1Payload,
            ValidMatchSettleWithCommitmentsStatement memory statement,
            MatchProofs memory proofs,
            MatchLinkingProofs memory linkingProofs
        ) = settleMatchWithCommitmentsCalldata(merkleRoot);
        statement.protocolFeeRate = BN254.ScalarField.unwrap(randomScalar());

        // Should fail
        vm.expectRevert(IDarkpool.InvalidProtocolFeeRate.selector);
        darkpool.processMatchSettleWithCommitments(party0Payload, party1Payload, statement, proofs, linkingProofs);
    }
}

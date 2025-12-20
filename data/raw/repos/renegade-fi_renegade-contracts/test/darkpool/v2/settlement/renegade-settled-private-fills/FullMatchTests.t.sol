// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/* solhint-disable func-name-mixedcase */

import { BN254 } from "solidity-bn254/BN254.sol";

import { SettlementBundle } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import {
    ObligationBundle,
    ObligationType,
    ObligationLib,
    PrivateObligationBundle
} from "darkpoolv2-types/settlement/ObligationBundle.sol";
import {
    RenegadeSettledPrivateFillBundle,
    RenegadeSettledPrivateFirstFillBundle,
    RenegadeSettledPrivateFillLib
} from "darkpoolv2-lib/settlement/bundles/RenegadeSettledPrivateFillLib.sol";
import { RenegadeSettledPrivateFillTestUtils } from "./Utils.sol";
import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { VerifierCore } from "renegade-lib/verifier/VerifierCore.sol";
import { MerkleTreeLib } from "renegade-lib/merkle/MerkleTree.sol";
import { NullifierLib } from "renegade-lib/NullifierSet.sol";
import { DarkpoolStateLib } from "darkpoolv2-lib/DarkpoolState.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";
import { IntentPublicShare, IntentPreMatchShare, IntentPreMatchShareLib } from "darkpoolv2-types/Intent.sol";
import {
    OutputBalanceBundle,
    OutputBalanceBundleType,
    OutputBalanceBundleLib,
    NewBalanceBundle
} from "darkpoolv2-types/settlement/OutputBalanceBundle.sol";

contract FullMatchTests is RenegadeSettledPrivateFillTestUtils {
    using ObligationLib for ObligationBundle;
    using RenegadeSettledPrivateFillLib for RenegadeSettledPrivateFirstFillBundle;
    using RenegadeSettledPrivateFillLib for RenegadeSettledPrivateFillBundle;
    using FixedPointLib for FixedPoint;
    using MerkleTreeLib for MerkleTreeLib.MerkleTree;
    using IntentPreMatchShareLib for IntentPreMatchShare;
    using OutputBalanceBundleLib for OutputBalanceBundle;

    MerkleTreeLib.MerkleTree private testTree;

    // -----------
    // | Helpers |
    // -----------

    /// @dev Create match data for a simulated trade with private obligations
    function _createMatchData(bool isFirstFill)
        internal
        returns (
            ObligationBundle memory obligationBundle,
            SettlementBundle memory bundle0,
            SettlementBundle memory bundle1
        )
    {
        // Create private obligation bundle
        PrivateObligationBundle memory privateObligation = createPrivateObligationBundle();
        obligationBundle =
            ObligationBundle({ obligationType: ObligationType.PRIVATE, data: abi.encode(privateObligation) });

        // Create two settlement bundles
        bundle0 = createRenegadeSettledPrivateFillBundle(isFirstFill, party0);
        bundle1 = createRenegadeSettledPrivateFillBundle(isFirstFill, party1);
    }

    // ---------
    // | Tests |
    // ---------

    // --- Valid Test Cases --- //

    /// @notice Test a basic full match settlement with private fills
    function test_fullMatch() public {
        bool isFirstFill = vm.randomBool();
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(isFirstFill);
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);
    }

    /// @notice Test mixing first fill and subsequent fill bundles
    function test_fullMatch_mixedFillTypes() public {
        // Create private obligation bundle
        PrivateObligationBundle memory privateObligation = createPrivateObligationBundle();
        ObligationBundle memory obligationBundle =
            ObligationBundle({ obligationType: ObligationType.PRIVATE, data: abi.encode(privateObligation) });

        // Create two settlement bundles with different fill types
        SettlementBundle memory bundle0 = createRenegadeSettledPrivateFillBundle(true, party0);
        SettlementBundle memory bundle1 = createRenegadeSettledPrivateFillBundle(false, party1);
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);
    }

    /// @notice Check the Merkle mountain range roots and nullifiers after a full match settlement (first fill)
    function test_fullMatch_merkleRootsAndNullifiers_firstFill() public {
        // Create match data (first fill)
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(true);
        RenegadeSettledPrivateFirstFillBundle memory bundleData0 =
            abi.decode(bundle0.data, (RenegadeSettledPrivateFirstFillBundle));
        RenegadeSettledPrivateFirstFillBundle memory bundleData1 =
            abi.decode(bundle1.data, (RenegadeSettledPrivateFirstFillBundle));
        PrivateObligationBundle memory obligation = abi.decode(obligationBundle.data, (PrivateObligationBundle));

        // Settle the match
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);

        // 1. Check that the balance nullifiers are spent (first fill only nullifies balance, not intent)
        bool balanceNullifier0Spent = darkpool.nullifierSpent(bundleData0.auth.statement.oldBalanceNullifier);
        bool balanceNullifier1Spent = darkpool.nullifierSpent(bundleData1.auth.statement.oldBalanceNullifier);
        assertTrue(balanceNullifier0Spent, "balance nullifier0 not spent");
        assertTrue(balanceNullifier1Spent, "balance nullifier1 not spent");

        // 2. Check that the Merkle root matches the expected root
        // Compute the commitments to the updated intents and balances
        IntentPreMatchShare memory intentPartialShare0 = bundleData0.auth.statement.intentPublicShare;
        IntentPreMatchShare memory intentPartialShare1 = bundleData1.auth.statement.intentPublicShare;
        IntentPublicShare memory newIntentShare0 =
            intentPartialShare0.toFullPublicShare(obligation.statement.newAmountPublicShare0);
        IntentPublicShare memory newIntentShare1 =
            intentPartialShare1.toFullPublicShare(obligation.statement.newAmountPublicShare1);
        BN254.ScalarField intentCommitment0 = RenegadeSettledPrivateFillLib.computeFullIntentCommitment(
            newIntentShare0, bundleData0.auth.statement.intentPrivateShareCommitment, hasher
        );
        BN254.ScalarField intentCommitment1 = RenegadeSettledPrivateFillLib.computeFullIntentCommitment(
            newIntentShare1, bundleData1.auth.statement.intentPrivateShareCommitment, hasher
        );
        // For first fill, _updateIntentAndBalance inserts input balance first, then intent
        BN254.ScalarField inputBalanceCommitment0 = RenegadeSettledPrivateFillLib.computeFullBalanceCommitment(
            obligation.statement.newInBalancePublicShares0, bundleData0.auth.statement.balancePartialCommitment, hasher
        );
        BN254.ScalarField inputBalanceCommitment1 = RenegadeSettledPrivateFillLib.computeFullBalanceCommitment(
            obligation.statement.newInBalancePublicShares1, bundleData1.auth.statement.balancePartialCommitment, hasher
        );

        // Decode output balance bundles and get their partial commitments
        // authorizeAndUpdateOutputBalance inserts the output balance using newBalancePartialCommitment
        NewBalanceBundle memory outputBalanceBundle0 = bundleData0.outputBalanceBundle.decodeNewBalanceBundle();
        NewBalanceBundle memory outputBalanceBundle1 = bundleData1.outputBalanceBundle.decodeNewBalanceBundle();

        BN254.ScalarField outBalanceCommitment0 = RenegadeSettledPrivateFillLib.computeFullBalanceCommitment(
            obligation.statement.newOutBalancePublicShares0,
            outputBalanceBundle0.statement.newBalancePartialCommitment,
            hasher
        );
        BN254.ScalarField outBalanceCommitment1 = RenegadeSettledPrivateFillLib.computeFullBalanceCommitment(
            obligation.statement.newOutBalancePublicShares1,
            outputBalanceBundle1.statement.newBalancePartialCommitment,
            hasher
        );

        // Validate against a single Merkle tree
        // Order per party: balance (from _updateIntentAndBalance), intent, output balance (from
        // authorizeAndUpdateOutputBalance)
        MerkleTreeLib.MerkleTreeConfig memory config =
            MerkleTreeLib.MerkleTreeConfig({ storeRoots: false, depth: bundleData0.auth.merkleDepth });
        MerkleTreeLib.initialize(testTree, config);
        testTree.insertLeaf(inputBalanceCommitment0, hasher);
        testTree.insertLeaf(intentCommitment0, hasher);
        testTree.insertLeaf(outBalanceCommitment0, hasher);
        testTree.insertLeaf(inputBalanceCommitment1, hasher);
        testTree.insertLeaf(intentCommitment1, hasher);
        testTree.insertLeaf(outBalanceCommitment1, hasher);

        // Get the root of the tree and check that it's in the Merkle mountain range history
        BN254.ScalarField root = testTree.getRoot();
        bool rootInHistory = darkpool.rootInHistory(root);
        assertTrue(rootInHistory, "root not in history");
    }

    /// @notice Check the Merkle mountain range roots and nullifiers after a full match settlement (subsequent fill)
    function test_fullMatch_merkleRootsAndNullifiers_subsequentFill() public {
        // Create match data (subsequent fill)
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(false);
        RenegadeSettledPrivateFillBundle memory bundleData0 =
            abi.decode(bundle0.data, (RenegadeSettledPrivateFillBundle));
        RenegadeSettledPrivateFillBundle memory bundleData1 =
            abi.decode(bundle1.data, (RenegadeSettledPrivateFillBundle));
        PrivateObligationBundle memory obligation = abi.decode(obligationBundle.data, (PrivateObligationBundle));

        // Settle the match
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);

        // 1. Check that both intent and balance nullifiers are spent
        bool intentNullifier0Spent = darkpool.nullifierSpent(bundleData0.auth.statement.oldIntentNullifier);
        bool balanceNullifier0Spent = darkpool.nullifierSpent(bundleData0.auth.statement.oldBalanceNullifier);
        bool intentNullifier1Spent = darkpool.nullifierSpent(bundleData1.auth.statement.oldIntentNullifier);
        bool balanceNullifier1Spent = darkpool.nullifierSpent(bundleData1.auth.statement.oldBalanceNullifier);

        assertTrue(intentNullifier0Spent, "intent nullifier0 not spent");
        assertTrue(balanceNullifier0Spent, "balance nullifier0 not spent");
        assertTrue(intentNullifier1Spent, "intent nullifier1 not spent");
        assertTrue(balanceNullifier1Spent, "balance nullifier1 not spent");

        // 2. Check that the Merkle root matches the expected root
        // Compute the commitments to the updated intents and balances
        BN254.ScalarField intentCommitment0 = RenegadeSettledPrivateFillLib.computeFullIntentCommitment(
            obligation.statement.newAmountPublicShare0, bundleData0.auth.statement.newIntentPartialCommitment, hasher
        );
        BN254.ScalarField intentCommitment1 = RenegadeSettledPrivateFillLib.computeFullIntentCommitment(
            obligation.statement.newAmountPublicShare1, bundleData1.auth.statement.newIntentPartialCommitment, hasher
        );
        BN254.ScalarField inBalanceCommitment0 = RenegadeSettledPrivateFillLib.computeFullBalanceCommitment(
            obligation.statement.newInBalancePublicShares0, bundleData0.auth.statement.balancePartialCommitment, hasher
        );
        BN254.ScalarField inBalanceCommitment1 = RenegadeSettledPrivateFillLib.computeFullBalanceCommitment(
            obligation.statement.newInBalancePublicShares1, bundleData1.auth.statement.balancePartialCommitment, hasher
        );

        // Decode output balance bundles and get their partial commitments
        NewBalanceBundle memory outputBalanceBundle0 = bundleData0.outputBalanceBundle.decodeNewBalanceBundle();
        NewBalanceBundle memory outputBalanceBundle1 = bundleData1.outputBalanceBundle.decodeNewBalanceBundle();

        BN254.ScalarField outBalanceCommitment0 = RenegadeSettledPrivateFillLib.computeFullBalanceCommitment(
            obligation.statement.newOutBalancePublicShares0,
            outputBalanceBundle0.statement.newBalancePartialCommitment,
            hasher
        );
        BN254.ScalarField outBalanceCommitment1 = RenegadeSettledPrivateFillLib.computeFullBalanceCommitment(
            obligation.statement.newOutBalancePublicShares1,
            outputBalanceBundle1.statement.newBalancePartialCommitment,
            hasher
        );

        // Validate against a single Merkle tree
        MerkleTreeLib.MerkleTreeConfig memory config =
            MerkleTreeLib.MerkleTreeConfig({ storeRoots: false, depth: bundleData0.auth.merkleDepth });
        MerkleTreeLib.initialize(testTree, config);
        testTree.insertLeaf(inBalanceCommitment0, hasher);
        testTree.insertLeaf(intentCommitment0, hasher);
        testTree.insertLeaf(outBalanceCommitment0, hasher);
        testTree.insertLeaf(inBalanceCommitment1, hasher);
        testTree.insertLeaf(intentCommitment1, hasher);
        testTree.insertLeaf(outBalanceCommitment1, hasher);

        // Get the root of the tree and check that it's in the Merkle mountain range history
        BN254.ScalarField root = testTree.getRoot();
        bool rootInHistory = darkpool.rootInHistory(root);
        assertTrue(rootInHistory, "root not in history");
    }

    // --- Invalid Test Cases --- //

    /// @notice Test a full match settlement with an invalid proof
    function test_fullMatch_invalidProof() public {
        // Create match data
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(false);
        vm.expectRevert(IDarkpoolV2.SettlementVerificationFailed.selector);
        darkpoolRealVerifier.settleMatch(obligationBundle, bundle0, bundle1);
    }

    /// @notice Test a replay attack on a user's intent (first fill)
    function test_fullMatch_ownerSignatureReplay_firstFill() public {
        // Create match data (first fill)
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(true);
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);

        // Try settling the same match again, the owner signature nonce should be replayed
        vm.expectRevert(DarkpoolStateLib.NonceAlreadySpent.selector);
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);
    }

    /// @notice Test the case in which a balance nullifier is already spent on a settlement bundle (first fill)
    function test_fullMatch_balanceNullifierAlreadySpent_firstFill() public {
        // Create match data and settle
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(true);
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);

        // Create new match data with the same parties but different obligations
        (ObligationBundle memory obligationBundle2, SettlementBundle memory bundle2, SettlementBundle memory bundle3) =
            _createMatchData(true);

        // Replace the balance nullifier in bundle2 with the one from bundle0 (already spent)
        RenegadeSettledPrivateFirstFillBundle memory bundleData0 =
            abi.decode(bundle0.data, (RenegadeSettledPrivateFirstFillBundle));
        RenegadeSettledPrivateFirstFillBundle memory bundleData2 =
            abi.decode(bundle2.data, (RenegadeSettledPrivateFirstFillBundle));
        bundleData2.auth.statement.oldBalanceNullifier = bundleData0.auth.statement.oldBalanceNullifier;
        bundle2.data = abi.encode(bundleData2);

        // Try settling the new match, the balance nullifier should already be spent
        vm.expectRevert(NullifierLib.NullifierAlreadySpent.selector);
        darkpool.settleMatch(obligationBundle2, bundle2, bundle3);
    }

    /// @notice Test the case in which an intent nullifier is already spent (subsequent fill)
    function test_fullMatch_intentNullifierAlreadySpent_subsequentFill() public {
        // Create match data and settle
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(false);
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);

        // Try settling the same match again, the intent nullifier should be spent
        vm.expectRevert(NullifierLib.NullifierAlreadySpent.selector);
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);
    }
}

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/* solhint-disable func-name-mixedcase */

import { BN254 } from "solidity-bn254/BN254.sol";

import { SettlementBundle, SettlementBundleLib } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";
import { ObligationBundle, ObligationType, ObligationLib } from "darkpoolv2-types/settlement/ObligationBundle.sol";
import {
    OutputBalanceBundle,
    OutputBalanceBundleLib,
    ExistingBalanceBundle
} from "darkpoolv2-types/settlement/OutputBalanceBundle.sol";
import {
    RenegadeSettledIntentFirstFillBundle,
    RenegadeSettledIntentBundle,
    PrivateIntentPrivateBalanceBundleLib
} from "darkpoolv2-lib/settlement/bundles/PrivateIntentPrivateBalanceBundleLib.sol";
import { RenegadeSettledPrivateIntentTestUtils } from "./Utils.sol";
import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { VerifierCore } from "renegade-lib/verifier/VerifierCore.sol";
import { MerkleTreeLib } from "renegade-lib/merkle/MerkleTree.sol";
import { NullifierLib } from "renegade-lib/NullifierSet.sol";
import { DarkpoolStateLib } from "darkpoolv2-lib/DarkpoolState.sol";
import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";
import { FeeTake } from "darkpoolv2-types/Fee.sol";
import { ExpectedDifferences } from "../SettlementTestUtils.sol";

contract FullMatchTests is RenegadeSettledPrivateIntentTestUtils {
    using ObligationLib for ObligationBundle;
    using OutputBalanceBundleLib for OutputBalanceBundle;
    using PrivateIntentPrivateBalanceBundleLib for RenegadeSettledIntentBundle;
    using PrivateIntentPrivateBalanceBundleLib for RenegadeSettledIntentFirstFillBundle;
    using FixedPointLib for FixedPoint;
    using MerkleTreeLib for MerkleTreeLib.MerkleTree;

    MerkleTreeLib.MerkleTree private testTree;

    function setUp() public virtual override {
        super.setUp();
        // Mint max amounts of the base and quote tokens to the darkpool to capitalize fee payments
        uint256 maxAmt = 2 ** DarkpoolConstants.AMOUNT_BITS - 1;
        baseToken.mint(address(darkpool), maxAmt);
        quoteToken.mint(address(darkpool), maxAmt);
    }

    // -----------
    // | Helpers |
    // -----------

    /// @dev Create match data for a simulated trade
    function _createMatchData(bool isFirstFill)
        internal
        returns (
            ObligationBundle memory obligationBundle,
            SettlementBundle memory bundle0,
            SettlementBundle memory bundle1
        )
    {
        // Create two settlement obligations and obligation bundle
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1,) = createTradeObligations();
        obligationBundle =
            ObligationBundle({ obligationType: ObligationType.PUBLIC, data: abi.encode(obligation0, obligation1) });

        // Create two settlement bundles
        bundle0 = createRenegadeSettledBundle(isFirstFill, obligation0, party0);
        bundle1 = createRenegadeSettledBundle(isFirstFill, obligation1, party1);
    }

    // ---------
    // | Tests |
    // ---------

    // --- Valid Test Cases --- //

    /// @notice Test a basic full match settlement
    function test_fullMatch_twoRenegadeSettledPrivateIntents() public {
        bool isFirstFill = vm.randomBool();
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(isFirstFill);
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);
    }

    /// @notice Test mixing first fill and subsequent fill bundles
    function test_fullMatch_mixedFillTypes() public {
        // Create two settlement obligations and obligation bundle
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1,) = createTradeObligations();
        ObligationBundle memory obligationBundle =
            ObligationBundle({ obligationType: ObligationType.PUBLIC, data: abi.encode(obligation0, obligation1) });

        // Create two settlement bundles
        SettlementBundle memory bundle0 = createRenegadeSettledBundle(true, obligation0, party0);
        SettlementBundle memory bundle1 = createRenegadeSettledBundle(false, obligation1, party1);
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);
    }

    /// @notice Check the Merkle mountain range roots and nullifiers after a full match settlement (first fill)
    function test_fullMatch_merkleRootsAndNullifiers_firstFill() public {
        // Create match data (first fill)
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(true);
        RenegadeSettledIntentFirstFillBundle memory bundleData0 =
            abi.decode(bundle0.data, (RenegadeSettledIntentFirstFillBundle));
        RenegadeSettledIntentFirstFillBundle memory bundleData1 =
            abi.decode(bundle1.data, (RenegadeSettledIntentFirstFillBundle));

        // Only the relayer and protocol fee accounts should see erc20 balance updates
        // Obligation 0 is selling the base
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1) =
            abi.decode(obligationBundle.data, (SettlementObligation, SettlementObligation));
        (FeeTake memory relayerFeeTake0, FeeTake memory protocolFeeTake0) = computeMatchFees(obligation0);
        (FeeTake memory relayerFeeTake1, FeeTake memory protocolFeeTake1) = computeMatchFees(obligation1);
        uint256 totalFee0 = relayerFeeTake0.fee + protocolFeeTake0.fee;
        uint256 totalFee1 = relayerFeeTake1.fee + protocolFeeTake1.fee;
        uint256 netReceiveAmount0 = obligation0.amountOut - totalFee0;
        uint256 netReceiveAmount1 = obligation1.amountOut - totalFee1;

        ExpectedDifferences memory expectedDifferences = createEmptyExpectedDifferences();
        expectedDifferences.relayerFeeBaseChange = int256(relayerFeeTake1.fee);
        expectedDifferences.relayerFeeQuoteChange = int256(relayerFeeTake0.fee);
        expectedDifferences.protocolFeeBaseChange = int256(protocolFeeTake1.fee);
        expectedDifferences.protocolFeeQuoteChange = int256(protocolFeeTake0.fee);
        expectedDifferences.darkpoolBaseChange = -int256(totalFee1);
        expectedDifferences.darkpoolQuoteChange = -int256(totalFee0);
        checkBalancesBeforeAndAfterSettlement(obligationBundle, bundle0, bundle1, expectedDifferences);

        // 1. Check that the balance nullifiers are spent (first fill only nullifies balance, not intent)
        bool balanceNullifier0Spent = darkpool.nullifierSpent(bundleData0.auth.statement.oldBalanceNullifier);
        bool balanceNullifier1Spent = darkpool.nullifierSpent(bundleData1.auth.statement.oldBalanceNullifier);
        assertTrue(balanceNullifier0Spent, "balance nullifier0 not spent");
        assertTrue(balanceNullifier1Spent, "balance nullifier1 not spent");

        // 2. Check that the Merkle root matches the expected root
        // Compute the commitments to the updated intents and balances
        ExistingBalanceBundle memory outBalanceBundle0 = bundleData0.outputBalanceBundle.decodeExistingBalanceBundle();
        ExistingBalanceBundle memory outBalanceBundle1 = bundleData1.outputBalanceBundle.decodeExistingBalanceBundle();
        BN254.ScalarField intentCommitment0 = bundleData0.computeFullIntentCommitment(hasher);
        BN254.ScalarField intentCommitment1 = bundleData1.computeFullIntentCommitment(hasher);
        BN254.ScalarField balanceCommitment0 = bundleData0.computeFullBalanceCommitment(hasher);
        BN254.ScalarField balanceCommitment1 = bundleData1.computeFullBalanceCommitment(hasher);
        BN254.ScalarField outBalanceCommitment0 = PrivateIntentPrivateBalanceBundleLib
            .computeFullExistingOutputBalanceCommitment(
            netReceiveAmount0, outBalanceBundle0, bundleData0.settlementStatement, hasher
        );
        BN254.ScalarField outBalanceCommitment1 = PrivateIntentPrivateBalanceBundleLib
            .computeFullExistingOutputBalanceCommitment(
            netReceiveAmount1, outBalanceBundle1, bundleData1.settlementStatement, hasher
        );

        // Validate against a single Merkle tree
        MerkleTreeLib.MerkleTreeConfig memory config =
            MerkleTreeLib.MerkleTreeConfig({ storeRoots: false, depth: bundleData0.auth.merkleDepth });
        MerkleTreeLib.initialize(testTree, config);
        testTree.insertLeaf(intentCommitment0, hasher);
        testTree.insertLeaf(balanceCommitment0, hasher);
        testTree.insertLeaf(outBalanceCommitment0, hasher);
        testTree.insertLeaf(intentCommitment1, hasher);
        testTree.insertLeaf(balanceCommitment1, hasher);
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
        RenegadeSettledIntentBundle memory bundleData0 = abi.decode(bundle0.data, (RenegadeSettledIntentBundle));
        RenegadeSettledIntentBundle memory bundleData1 = abi.decode(bundle1.data, (RenegadeSettledIntentBundle));

        // Only the relayer and protocol fee accounts should see erc20 balance updates
        // Obligation 0 is selling the base
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1) =
            abi.decode(obligationBundle.data, (SettlementObligation, SettlementObligation));
        (FeeTake memory relayerFeeTake0, FeeTake memory protocolFeeTake0) = computeMatchFees(obligation0);
        (FeeTake memory relayerFeeTake1, FeeTake memory protocolFeeTake1) = computeMatchFees(obligation1);
        uint256 totalFee0 = relayerFeeTake0.fee + protocolFeeTake0.fee;
        uint256 totalFee1 = relayerFeeTake1.fee + protocolFeeTake1.fee;
        uint256 netReceiveAmount0 = obligation0.amountOut - totalFee0;
        uint256 netReceiveAmount1 = obligation1.amountOut - totalFee1;

        ExpectedDifferences memory expectedDifferences = createEmptyExpectedDifferences();
        expectedDifferences.relayerFeeBaseChange = int256(relayerFeeTake1.fee);
        expectedDifferences.relayerFeeQuoteChange = int256(relayerFeeTake0.fee);
        expectedDifferences.protocolFeeBaseChange = int256(protocolFeeTake1.fee);
        expectedDifferences.protocolFeeQuoteChange = int256(protocolFeeTake0.fee);
        expectedDifferences.darkpoolBaseChange = -int256(totalFee1);
        expectedDifferences.darkpoolQuoteChange = -int256(totalFee0);
        checkBalancesBeforeAndAfterSettlement(obligationBundle, bundle0, bundle1, expectedDifferences);

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
        ExistingBalanceBundle memory outBalanceBundle0 = bundleData0.outputBalanceBundle.decodeExistingBalanceBundle();
        ExistingBalanceBundle memory outBalanceBundle1 = bundleData1.outputBalanceBundle.decodeExistingBalanceBundle();
        BN254.ScalarField intentCommitment0 = bundleData0.computeFullIntentCommitment(hasher);
        BN254.ScalarField intentCommitment1 = bundleData1.computeFullIntentCommitment(hasher);
        BN254.ScalarField balanceCommitment0 = bundleData0.computeFullBalanceCommitment(hasher);
        BN254.ScalarField balanceCommitment1 = bundleData1.computeFullBalanceCommitment(hasher);
        BN254.ScalarField outBalanceCommitment0 = PrivateIntentPrivateBalanceBundleLib
            .computeFullExistingOutputBalanceCommitment(
            netReceiveAmount0, outBalanceBundle0, bundleData0.settlementStatement, hasher
        );
        BN254.ScalarField outBalanceCommitment1 = PrivateIntentPrivateBalanceBundleLib
            .computeFullExistingOutputBalanceCommitment(
            netReceiveAmount1, outBalanceBundle1, bundleData1.settlementStatement, hasher
        );

        // Validate against a single Merkle tree
        MerkleTreeLib.MerkleTreeConfig memory config =
            MerkleTreeLib.MerkleTreeConfig({ storeRoots: false, depth: bundleData0.auth.merkleDepth });
        MerkleTreeLib.initialize(testTree, config);
        testTree.insertLeaf(intentCommitment0, hasher);
        testTree.insertLeaf(balanceCommitment0, hasher);
        testTree.insertLeaf(outBalanceCommitment0, hasher);
        testTree.insertLeaf(intentCommitment1, hasher);
        testTree.insertLeaf(balanceCommitment1, hasher);
        testTree.insertLeaf(outBalanceCommitment1, hasher);

        // Get the root of the tree and check that it's in the Merkle mountain range history
        BN254.ScalarField root = testTree.getRoot();
        bool rootInHistory = darkpool.rootInHistory(root);
        assertTrue(rootInHistory, "root not in history");
    }

    // --- Invalid Test Cases --- //

    /// @notice Test a full match settlement with an invalid proof
    function test_fullMatch_invalidProof() public {
        // Mint to the real verifier darkpool
        uint256 maxAmt = 2 ** DarkpoolConstants.AMOUNT_BITS - 1;
        baseToken.mint(address(darkpoolRealVerifier), maxAmt);
        quoteToken.mint(address(darkpoolRealVerifier), maxAmt);

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
        RenegadeSettledIntentFirstFillBundle memory bundleData0 =
            abi.decode(bundle0.data, (RenegadeSettledIntentFirstFillBundle));
        RenegadeSettledIntentFirstFillBundle memory bundleData2 =
            abi.decode(bundle2.data, (RenegadeSettledIntentFirstFillBundle));
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

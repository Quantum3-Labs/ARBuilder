// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/* solhint-disable func-name-mixedcase */

import { BN254 } from "solidity-bn254/BN254.sol";

import { SettlementBundle } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";
import { ObligationType, ObligationBundle, ObligationLib } from "darkpoolv2-types/settlement/ObligationBundle.sol";
import { SettlementBundleLib } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import {
    PrivateIntentPublicBalanceBundleLib,
    PrivateIntentPublicBalanceFirstFillBundle,
    PrivateIntentPublicBalanceBundle
} from "darkpoolv2-lib/settlement/bundles/PrivateIntentPublicBalanceBundleLib.sol";
import { PrivateIntentSettlementTestUtils } from "./Utils.sol";
import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";
import { MerkleTreeLib } from "renegade-lib/merkle/MerkleTree.sol";
import { NullifierLib } from "renegade-lib/NullifierSet.sol";
import { DarkpoolStateLib } from "darkpoolv2-lib/DarkpoolState.sol";
import { FeeTake } from "darkpoolv2-types/Fee.sol";
import { ExpectedDifferences } from "../SettlementTestUtils.sol";

contract FullMatchTests is PrivateIntentSettlementTestUtils {
    using ObligationLib for ObligationBundle;
    using PrivateIntentPublicBalanceBundleLib for PrivateIntentPublicBalanceBundle;
    using PrivateIntentPublicBalanceBundleLib for PrivateIntentPublicBalanceFirstFillBundle;
    using SettlementBundleLib for SettlementBundle;
    using FixedPointLib for FixedPoint;
    using MerkleTreeLib for MerkleTreeLib.MerkleTree;

    MerkleTreeLib.MerkleTree private testTree;

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
        // Create two settlement obligations
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1,) = createTradeObligations();
        obligationBundle =
            ObligationBundle({ obligationType: ObligationType.PUBLIC, data: abi.encode(obligation0, obligation1) });

        // Create two settlement bundles
        bundle0 = createPrivateIntentSettlementBundle(isFirstFill, obligation0, party0);
        bundle1 = createPrivateIntentSettlementBundle(isFirstFill, obligation1, party1);
        capitalizeParty(party0.addr, obligation0);
        capitalizeParty(party1.addr, obligation1);
    }

    // ---------
    // | Tests |
    // ---------

    // --- Valid Test Cases --- //

    /// @notice Test a basic full match settlement
    function test_fullMatch_twoNativeSettledPrivateIntents() public {
        // Create match data
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(true);
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1) =
            abi.decode(obligationBundle.data, (SettlementObligation, SettlementObligation));

        // Compute fees for both obligations
        (FeeTake memory relayerFeeTake0, FeeTake memory protocolFeeTake0) = computeMatchFees(obligation0);
        (FeeTake memory relayerFeeTake1, FeeTake memory protocolFeeTake1) = computeMatchFees(obligation1);
        uint256 totalFee0 = relayerFeeTake0.fee + protocolFeeTake0.fee;
        uint256 totalFee1 = relayerFeeTake1.fee + protocolFeeTake1.fee;

        // Set up expected differences accounting for fees
        ExpectedDifferences memory expectedDifferences = createEmptyExpectedDifferences();
        expectedDifferences.party0BaseChange = -int256(obligation0.amountIn);
        expectedDifferences.party0QuoteChange = int256(obligation0.amountOut) - int256(totalFee0);
        expectedDifferences.party1BaseChange = int256(obligation1.amountOut) - int256(totalFee1);
        expectedDifferences.party1QuoteChange = -int256(obligation1.amountIn);
        expectedDifferences.relayerFeeBaseChange = int256(relayerFeeTake1.fee);
        expectedDifferences.relayerFeeQuoteChange = int256(relayerFeeTake0.fee);
        expectedDifferences.protocolFeeBaseChange = int256(protocolFeeTake1.fee);
        expectedDifferences.protocolFeeQuoteChange = int256(protocolFeeTake0.fee);
        expectedDifferences.darkpoolBaseChange = 0;
        expectedDifferences.darkpoolQuoteChange = 0;
        checkBalancesBeforeAndAfterSettlement(obligationBundle, bundle0, bundle1, expectedDifferences);
    }

    /// @notice Test a full match settlement that is not the first fill for one intent
    function test_fullMatch_notFirstFill() public {
        // Create match data
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(false);
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1) =
            abi.decode(obligationBundle.data, (SettlementObligation, SettlementObligation));

        // Compute fees for both obligations
        (FeeTake memory relayerFeeTake0, FeeTake memory protocolFeeTake0) = computeMatchFees(obligation0);
        (FeeTake memory relayerFeeTake1, FeeTake memory protocolFeeTake1) = computeMatchFees(obligation1);
        uint256 totalFee0 = relayerFeeTake0.fee + protocolFeeTake0.fee;
        uint256 totalFee1 = relayerFeeTake1.fee + protocolFeeTake1.fee;

        // Set up expected differences accounting for fees
        ExpectedDifferences memory expectedDifferences = createEmptyExpectedDifferences();
        expectedDifferences.party0BaseChange = -int256(obligation0.amountIn);
        expectedDifferences.party0QuoteChange = int256(obligation0.amountOut) - int256(totalFee0);
        expectedDifferences.party1BaseChange = int256(obligation1.amountOut) - int256(totalFee1);
        expectedDifferences.party1QuoteChange = -int256(obligation1.amountIn);
        expectedDifferences.relayerFeeBaseChange = int256(relayerFeeTake1.fee);
        expectedDifferences.relayerFeeQuoteChange = int256(relayerFeeTake0.fee);
        expectedDifferences.protocolFeeBaseChange = int256(protocolFeeTake1.fee);
        expectedDifferences.protocolFeeQuoteChange = int256(protocolFeeTake0.fee);
        expectedDifferences.darkpoolBaseChange = 0;
        expectedDifferences.darkpoolQuoteChange = 0;
        checkBalancesBeforeAndAfterSettlement(obligationBundle, bundle0, bundle1, expectedDifferences);
    }

    /// @notice Check the Merkle mountain range roots after a full match settlement
    function test_fullMatch_merkleRootsAndNullifiers() public {
        // Create match data
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(false);
        PrivateIntentPublicBalanceBundle memory bundleData0 =
            abi.decode(bundle0.data, (PrivateIntentPublicBalanceBundle));
        PrivateIntentPublicBalanceBundle memory bundleData1 =
            abi.decode(bundle1.data, (PrivateIntentPublicBalanceBundle));

        // Settle the match
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);

        // 1. Check that the nullifier are spent
        bool nullifier0Spent = darkpool.nullifierSpent(bundleData0.auth.statement.oldIntentNullifier);
        bool nullifier1Spent = darkpool.nullifierSpent(bundleData1.auth.statement.oldIntentNullifier);
        assertTrue(nullifier0Spent, "nullifier0 not spent");
        assertTrue(nullifier1Spent, "nullifier1 not spent");

        // 2. Check that the Merkle root matches the expected root
        // Compute the commitments to the updated intents
        BN254.ScalarField commitment0 = bundleData0.computeFullIntentCommitment(hasher);
        BN254.ScalarField commitment1 = bundleData1.computeFullIntentCommitment(hasher);

        // Validate against a single Merkle tree
        MerkleTreeLib.MerkleTreeConfig memory config =
            MerkleTreeLib.MerkleTreeConfig({ storeRoots: false, depth: bundleData0.auth.merkleDepth });
        MerkleTreeLib.initialize(testTree, config);
        testTree.insertLeaf(commitment0, hasher);
        testTree.insertLeaf(commitment1, hasher);

        // Get the root of the tree and check that it's in the Merkle mountain range history
        BN254.ScalarField root = testTree.getRoot();
        bool rootInHistory = darkpool.rootInHistory(root);
        assertTrue(rootInHistory, "root not in history");
    }

    /// @notice Check the Merkle mountain range roots after a full match settlement for first fill
    /// @dev For first fill, there are no nullifiers to check - nonces are used instead (tested in
    /// test_fullMatch_intentReplay)
    function test_firstFill_merkleRootsAndNonce() public {
        // Create match data for first fill
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(true);
        PrivateIntentPublicBalanceFirstFillBundle memory bundleData0 =
            abi.decode(bundle0.data, (PrivateIntentPublicBalanceFirstFillBundle));
        PrivateIntentPublicBalanceFirstFillBundle memory bundleData1 =
            abi.decode(bundle1.data, (PrivateIntentPublicBalanceFirstFillBundle));

        // Settle the match
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);

        // Check that the Merkle root matches the expected root
        // Compute the commitments to the updated intents (post-match commitments)
        (, BN254.ScalarField postMatchCommitment0) = bundleData0.computeIntentCommitments(hasher);
        (, BN254.ScalarField postMatchCommitment1) = bundleData1.computeIntentCommitments(hasher);

        // Validate against a single Merkle tree
        MerkleTreeLib.MerkleTreeConfig memory config =
            MerkleTreeLib.MerkleTreeConfig({ storeRoots: false, depth: bundleData0.auth.merkleDepth });
        MerkleTreeLib.initialize(testTree, config);
        testTree.insertLeaf(postMatchCommitment0, hasher);
        testTree.insertLeaf(postMatchCommitment1, hasher);

        // Get the root of the tree and check that it's in the Merkle mountain range history
        BN254.ScalarField root = testTree.getRoot();
        bool rootInHistory = darkpool.rootInHistory(root);
        assertTrue(rootInHistory, "root not in history");
    }

    // --- Invalid Test Cases --- //

    /// @notice Test a full match settlement with a mismatched bundle type
    function test_fullMatch_invalidProof() public {
        // Create match data
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(false);
        vm.expectRevert(IDarkpoolV2.SettlementVerificationFailed.selector);
        darkpoolRealVerifier.settleMatch(obligationBundle, bundle0, bundle1);
    }

    /// @notice Test a replay attack on a user's intent
    function test_fullMatch_intentReplay() public {
        // Create match data
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(true);
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);

        // Try settling the same match again, the intent should be replayed
        vm.expectRevert(DarkpoolStateLib.NonceAlreadySpent.selector);
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);
    }

    /// @notice Test the case in which a nullifier is already spent on a settlement bundle
    function test_fullMatch_nullifierAlreadySpent() public {
        // Create match data and spend the nullifier
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(false);
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);

        // Try settling the same match again, the nullifier should be spent
        vm.expectRevert(NullifierLib.NullifierAlreadySpent.selector);
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);
    }

    /// @notice Test the case in which a permit is revoked before the settlement
    function test_fullMatch_permitRevoked() public {
        // Create match data
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle0, SettlementBundle memory bundle1) =
            _createMatchData(false);
        (SettlementObligation memory obligation0,) =
            abi.decode(obligationBundle.data, (SettlementObligation, SettlementObligation));

        vm.startPrank(party0.addr);
        permit2.approve(
            obligation0.inputToken,
            address(darkpool),
            0,
            /* amount */
            uint48(block.timestamp + 1 days)
        );
        vm.stopPrank();

        // Try settling the match, the permit should be revoked
        vm.expectRevert(abi.encodeWithSignature("InsufficientAllowance(uint256)", 0));
        darkpool.settleMatch(obligationBundle, bundle0, bundle1);
    }
}

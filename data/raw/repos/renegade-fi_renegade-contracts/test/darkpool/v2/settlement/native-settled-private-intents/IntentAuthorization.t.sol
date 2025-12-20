// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

/* solhint-disable func-name-mixedcase */

import { BN254 } from "solidity-bn254/BN254.sol";
import { ObligationBundle, ObligationType } from "darkpoolv2-types/settlement/ObligationBundle.sol";
import { PartyId, SettlementBundle, SettlementBundleLib } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import {
    PrivateIntentPublicBalanceBundleLib,
    PrivateIntentPublicBalanceFirstFillBundle,
    PrivateIntentPublicBalanceBundle
} from "darkpoolv2-lib/settlement/bundles/PrivateIntentPublicBalanceBundleLib.sol";
import {
    SignatureWithNonce,
    PrivateIntentAuthBundleFirstFill,
    PrivateIntentAuthBundle
} from "darkpoolv2-types/settlement/IntentBundle.sol";
import { SettlementContext } from "darkpoolv2-types/settlement/SettlementContext.sol";
import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";
import { SettlementLib } from "darkpoolv2-lib/settlement/SettlementLib.sol";
import { DarkpoolContracts } from "darkpoolv2-contracts/DarkpoolV2.sol";
import { NativeSettledPrivateIntentLib } from "darkpoolv2-lib/settlement/NativeSettledPrivateIntent.sol";
import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";
import { PrivateIntentSettlementTestUtils } from "./Utils.sol";

contract PrivateIntentAuthorizationTest is PrivateIntentSettlementTestUtils {
    using PrivateIntentPublicBalanceBundleLib for PrivateIntentPublicBalanceFirstFillBundle;
    using SettlementBundleLib for SettlementBundle;

    // -----------
    // | Helpers |
    // -----------

    /// @notice Wrapper to convert memory to calldata for library call
    function _executeSettlementBundle(
        ObligationBundle calldata obligationBundle,
        SettlementBundle calldata bundle
    )
        external
        returns (SettlementContext memory)
    {
        SettlementContext memory settlementContext = _createSettlementContext();
        DarkpoolContracts memory contracts = getSettlementContracts();
        SettlementLib.executeSettlementBundle(
            PartyId.PARTY_0, obligationBundle, bundle, settlementContext, contracts, darkpoolState
        );
        return settlementContext;
    }

    /// @notice Helper that accepts memory and calls library with calldata
    function authorizeIntentHelper(
        ObligationBundle memory obligationBundle,
        SettlementBundle memory bundle
    )
        internal
        returns (SettlementContext memory context)
    {
        context = this._executeSettlementBundle(obligationBundle, bundle);
    }

    // ---------
    // | Tests |
    // ---------

    /// @dev Test a basic bundle verification case with a valid bundle
    function test_validSignature() public {
        // Should not revert
        bool isFirstFill = vm.randomBool();
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle) =
            createSamplePrivateIntentBundle(isFirstFill);
        authorizeIntentHelper(obligationBundle, bundle);
    }

    /// @dev Test a bundle verification case with `isFirstFill = false`
    function test_validSignature_notFirstFill() public {
        // When isFirstFill is false, the signature is not checked
        // (because the intent was already validated and inserted into the Merkle tree)
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1,) = createTradeObligations();
        ObligationBundle memory obligationBundle =
            ObligationBundle({ obligationType: ObligationType.PUBLIC, data: abi.encode(obligation0, obligation1) });
        SettlementBundle memory bundle = createPrivateIntentSettlementBundle(
            false,
            /* isFirstFill */
            obligation0,
            intentOwner
        );

        // Should not revert even though we're not checking the signature
        authorizeIntentHelper(obligationBundle, bundle);
    }

    /// @dev Test a bundle verification case with an invalid intent commitment signature
    function test_invalidIntentCommitmentSignature_wrongSigner() public {
        // Create bundle and replace the intent commitment signature with a signature from wrong signer
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle) =
            createSamplePrivateIntentBundle(true /* isFirstFill */ );
        PrivateIntentPublicBalanceFirstFillBundle memory bundleData =
            abi.decode(bundle.data, (PrivateIntentPublicBalanceFirstFillBundle));
        PrivateIntentAuthBundleFirstFill memory authBundle = bundleData.auth;

        // Compute the full intent commitment
        (BN254.ScalarField preMatchIntentCommitment,) = bundleData.computeIntentCommitments(hasher);

        // Sign with wrong signer
        SignatureWithNonce memory wrongSig = signIntentCommitment(preMatchIntentCommitment, wrongSigner.privateKey);
        authBundle.intentSignature = wrongSig;
        bundleData.auth = authBundle;
        bundle.data = abi.encode(bundleData);

        // Should revert with InvalidIntentCommitmentSignature
        vm.expectRevert(IDarkpoolV2.InvalidIntentCommitmentSignature.selector);
        authorizeIntentHelper(obligationBundle, bundle);
    }

    /// @dev Test a bundle verification case with an invalid Merkle depth
    function test_invalidMerkleDepth() public {
        // Create bundle with invalid Merkle depth
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1,) = createTradeObligations();
        ObligationBundle memory obligationBundle =
            ObligationBundle({ obligationType: ObligationType.PUBLIC, data: abi.encode(obligation0, obligation1) });

        // Use an invalid Merkle depth (not the default)
        uint256 invalidDepth = DarkpoolConstants.DEFAULT_MERKLE_DEPTH + 1;
        SettlementBundle memory bundle =
            createPrivateIntentSettlementBundleSubsequentFill(invalidDepth, obligation0, intentOwner);

        // Should revert with InvalidMerkleDepthRequested
        vm.expectRevert(IDarkpoolV2.InvalidMerkleRoot.selector);
        authorizeIntentHelper(obligationBundle, bundle);
    }

    /// @dev Test a bundle verification case with an invalid Merkle root (not in history)
    function test_invalidMerkleRoot() public {
        // Create bundle for subsequent fill (not first fill)
        (ObligationBundle memory obligationBundle, SettlementBundle memory bundle) =
            createSamplePrivateIntentBundle(false /* isFirstFill */ );

        // Decode the bundle data
        PrivateIntentPublicBalanceBundle memory bundleData = abi.decode(bundle.data, (PrivateIntentPublicBalanceBundle));
        PrivateIntentAuthBundle memory authBundle = bundleData.auth;

        // Set the merkle root to a random value
        authBundle.statement.merkleRoot = randomScalar();
        bundleData.auth = authBundle;
        bundle.data = abi.encode(bundleData);

        // Should revert with InvalidMerkleRoot
        vm.expectRevert(IDarkpoolV2.InvalidMerkleRoot.selector);
        authorizeIntentHelper(obligationBundle, bundle);
    }
}

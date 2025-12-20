// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { Vm } from "forge-std/Vm.sol";
import { BN254 } from "solidity-bn254/BN254.sol";
import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";

import { SettlementBundle, SettlementBundleType } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import {
    PrivateIntentPublicBalanceBoundedFirstFillBundle,
    PrivateIntentPublicBalanceBoundedBundle
} from "darkpoolv2-lib/settlement/bundles/PrivateIntentPublicBalanceBundleLib.sol";
import {
    SignatureWithNonce,
    PrivateIntentAuthBundle,
    PrivateIntentAuthBundleFirstFill
} from "darkpoolv2-types/settlement/IntentBundle.sol";
import { BoundedMatchResult, BoundedMatchResultLib } from "darkpoolv2-types/BoundedMatchResult.sol";
import { IntentOnlyBoundedSettlementStatement } from "darkpoolv2-lib/public_inputs/Settlement.sol";
import {
    IntentOnlyValidityStatement,
    IntentOnlyValidityStatementFirstFill
} from "darkpoolv2-lib/public_inputs/ValidityProofs.sol";
import { IntentPublicShare, IntentPublicShareLib } from "darkpoolv2-types/Intent.sol";
import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import { IHasher } from "renegade-lib/interfaces/IHasher.sol";
import { DarkpoolState, DarkpoolStateLib } from "darkpoolv2-lib/DarkpoolState.sol";
import { ExternalMatchTestUtils } from "../Utils.sol";

contract BoundedPrivateIntentTestUtils is ExternalMatchTestUtils {
    using BoundedMatchResultLib for BoundedMatchResult;
    using IntentPublicShareLib for IntentPublicShare;
    using FixedPointLib for FixedPoint;
    using DarkpoolStateLib for DarkpoolState;

    // ---------
    // | Utils |
    // ---------

    // --- Intent Commitment --- //

    /// @dev Compute the full commitment to an intent's shares
    function computeIntentSharesCommitment(
        IntentPublicShare memory intentPublicShare,
        BN254.ScalarField intentPrivateCommitment,
        IHasher _hasher
    )
        internal
        view
        returns (BN254.ScalarField commitment)
    {
        uint256[] memory intentPublicShareScalars = intentPublicShare.scalarSerialize();
        uint256 commitmentHash = _hasher.computeResumableCommitment(intentPublicShareScalars);

        // Compute the full commitment: H(private commitment || public commitment)
        uint256[] memory commitmentInputs = new uint256[](2);
        commitmentInputs[0] = BN254.ScalarField.unwrap(intentPrivateCommitment);
        commitmentInputs[1] = commitmentHash;
        uint256 hashResult = _hasher.spongeHash(commitmentInputs);
        commitment = BN254.ScalarField.wrap(hashResult);
    }

    /// @dev Sign an intent commitment
    function signIntentCommitment(
        BN254.ScalarField intentCommitment,
        uint256 signerPrivateKey
    )
        internal
        returns (SignatureWithNonce memory)
    {
        // Hash the intent commitment with a random nonce
        uint256 nonce = randomUint();
        bytes32 intentCommitmentBytes = bytes32(BN254.ScalarField.unwrap(intentCommitment));
        bytes32 commitmentHash = EfficientHashLib.hash(abi.encode(intentCommitmentBytes));
        bytes32 signatureDigest = EfficientHashLib.hash(commitmentHash, bytes32(nonce));

        // Sign with the private key
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(signerPrivateKey, signatureDigest);
        return SignatureWithNonce({ nonce: nonce, signature: abi.encodePacked(r, s, v) });
    }

    // --- Bounded Settlement Statement --- //

    /// @dev Create a bounded settlement statement for a given bounded match result
    /// @param matchResult The bounded match result to create the statement for
    /// @return statement The bounded settlement statement
    function createBoundedSettlementStatement(BoundedMatchResult memory matchResult)
        internal
        view
        returns (IntentOnlyBoundedSettlementStatement memory statement)
    {
        statement = IntentOnlyBoundedSettlementStatement({
            boundedMatchResult: matchResult,
            externalRelayerFeeRate: relayerFeeRateFixedPoint,
            internalRelayerFeeRate: relayerFeeRateFixedPoint,
            relayerFeeAddress: relayerFeeAddr
        });
    }

    // --- Private Intent Settlement Bundle --- //

    /// @dev Create a complete bounded private intent settlement bundle
    function createBoundedPrivateIntentSettlementBundle(
        bool isFirstFill,
        BoundedMatchResult memory matchResult,
        Vm.Wallet memory owner
    )
        internal
        returns (SettlementBundle memory)
    {
        uint256 merkleDepth = DarkpoolConstants.DEFAULT_MERKLE_DEPTH;
        if (isFirstFill) {
            return createBoundedPrivateIntentBundleFirstFill(merkleDepth, matchResult, owner);
        } else {
            return createBoundedPrivateIntentBundleSubsequent(merkleDepth, matchResult, owner);
        }
    }

    /// @dev Create a bounded private intent settlement bundle for first fill
    function createBoundedPrivateIntentBundleFirstFill(
        uint256 merkleDepth,
        BoundedMatchResult memory matchResult,
        Vm.Wallet memory owner
    )
        internal
        returns (SettlementBundle memory)
    {
        // Create the validity statement
        IntentOnlyValidityStatementFirstFill memory validityStatement = IntentOnlyValidityStatementFirstFill({
            intentOwner: owner.addr,
            intentPrivateCommitment: randomScalar(),
            recoveryId: randomScalar(),
            intentPublicShare: randomIntentPublicShare()
        });

        // Sign the pre-update intent commitment
        BN254.ScalarField intentCommitment = computeIntentSharesCommitment(
            validityStatement.intentPublicShare, validityStatement.intentPrivateCommitment, hasher
        );
        SignatureWithNonce memory intentSignature = signIntentCommitment(intentCommitment, owner.privateKey);

        // Create auth bundle
        PrivateIntentAuthBundleFirstFill memory auth = PrivateIntentAuthBundleFirstFill({
            intentSignature: intentSignature,
            merkleDepth: merkleDepth,
            statement: validityStatement,
            validityProof: createDummyProof()
        });

        // Create bounded settlement statement
        IntentOnlyBoundedSettlementStatement memory settlementStatement = createBoundedSettlementStatement(matchResult);

        // Create the bundle data
        PrivateIntentPublicBalanceBoundedFirstFillBundle memory bundleData =
            PrivateIntentPublicBalanceBoundedFirstFillBundle({
                auth: auth,
                settlementStatement: settlementStatement,
                settlementProof: createDummyProof(),
                authSettlementLinkingProof: createDummyLinkingProof()
            });

        // Encode and return the settlement bundle
        return SettlementBundle({
            isFirstFill: true,
            bundleType: SettlementBundleType.NATIVELY_SETTLED_PRIVATE_INTENT,
            data: abi.encode(bundleData)
        });
    }

    /// @dev Create a bounded private intent settlement bundle for subsequent fills
    function createBoundedPrivateIntentBundleSubsequent(
        uint256 merkleDepth,
        BoundedMatchResult memory matchResult,
        Vm.Wallet memory owner
    )
        internal
        returns (SettlementBundle memory)
    {
        // Get the actual Merkle root from the test state (must be in history for subsequent fills)
        BN254.ScalarField merkleRoot = darkpoolState.getMerkleRoot(merkleDepth);

        // Create the validity statement
        IntentOnlyValidityStatement memory validityStatement = IntentOnlyValidityStatement({
            intentOwner: owner.addr,
            merkleRoot: merkleRoot,
            oldIntentNullifier: randomScalar(),
            newAmountShare: randomScalar(),
            newIntentPartialCommitment: randomPartialCommitment(),
            recoveryId: randomScalar()
        });

        // Create auth bundle (no signature needed for subsequent fills)
        PrivateIntentAuthBundle memory auth = PrivateIntentAuthBundle({
            merkleDepth: merkleDepth, statement: validityStatement, validityProof: createDummyProof()
        });

        // Create bounded settlement statement
        IntentOnlyBoundedSettlementStatement memory settlementStatement = createBoundedSettlementStatement(matchResult);

        // Create the bundle data
        PrivateIntentPublicBalanceBoundedBundle memory bundleData = PrivateIntentPublicBalanceBoundedBundle({
            auth: auth,
            settlementStatement: settlementStatement,
            settlementProof: createDummyProof(),
            authSettlementLinkingProof: createDummyLinkingProof()
        });

        // Encode and return the settlement bundle
        return SettlementBundle({
            isFirstFill: false,
            bundleType: SettlementBundleType.NATIVELY_SETTLED_PRIVATE_INTENT,
            data: abi.encode(bundleData)
        });
    }
}

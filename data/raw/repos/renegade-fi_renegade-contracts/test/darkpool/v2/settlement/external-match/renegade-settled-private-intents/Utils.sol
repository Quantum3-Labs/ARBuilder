// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { Vm } from "forge-std/Vm.sol";
import { BN254 } from "solidity-bn254/BN254.sol";
import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";

import { SettlementBundle, SettlementBundleType } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import {
    SignatureWithNonce,
    RenegadeSettledIntentAuthBundleFirstFill,
    RenegadeSettledIntentAuthBundle
} from "darkpoolv2-types/settlement/IntentBundle.sol";
import {
    RenegadeSettledIntentBoundedFirstFillBundle,
    RenegadeSettledIntentBoundedBundle
} from "darkpoolv2-lib/settlement/bundles/PrivateIntentPrivateBalanceBoundedLib.sol";
import { BoundedMatchResult, BoundedMatchResultLib } from "darkpoolv2-types/BoundedMatchResult.sol";
import { IntentAndBalanceBoundedSettlementStatement } from "darkpoolv2-lib/public_inputs/Settlement.sol";
import {
    IntentAndBalanceValidityStatementFirstFill,
    IntentAndBalanceValidityStatement,
    OutputBalanceValidityStatement
} from "darkpoolv2-lib/public_inputs/ValidityProofs.sol";
import { IntentPreMatchShare } from "darkpoolv2-types/Intent.sol";
import { PostMatchBalanceShare } from "darkpoolv2-types/Balance.sol";
import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import { DarkpoolState, DarkpoolStateLib } from "darkpoolv2-lib/DarkpoolState.sol";
import {
    OutputBalanceBundle,
    OutputBalanceBundleType,
    ExistingBalanceBundle
} from "darkpoolv2-types/settlement/OutputBalanceBundle.sol";
import { ExternalMatchTestUtils } from "../Utils.sol";

contract RenegadeSettledBoundedPrivateIntentTestUtils is ExternalMatchTestUtils {
    using BoundedMatchResultLib for BoundedMatchResult;
    using FixedPointLib for FixedPoint;
    using DarkpoolStateLib for DarkpoolState;

    // ---------
    // | Utils |
    // ---------

    // --- Signatures --- //

    /// @dev Sign the owner signature digest for a renegade settled private intent
    /// @dev The signature is over intentAndAuthorizingAddressCommitment which combines
    /// the intent commitment and the new one-time key hash
    function createOwnerSignature(
        BN254.ScalarField intentAndAuthorizingAddressCommitment,
        uint256 signerPrivateKey
    )
        internal
        returns (SignatureWithNonce memory)
    {
        // Hash the intent and authorizing address commitment with a random nonce
        // This matches getOwnerSignatureDigest which hashes the single commitment
        uint256 nonce = randomUint();
        uint256 commitment = BN254.ScalarField.unwrap(intentAndAuthorizingAddressCommitment);
        bytes32 digest = EfficientHashLib.hash(commitment);
        bytes32 signatureDigest = EfficientHashLib.hash(digest, bytes32(nonce));

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
        returns (IntentAndBalanceBoundedSettlementStatement memory statement)
    {
        PostMatchBalanceShare memory inBalancePublicShares = PostMatchBalanceShare({
            relayerFeeBalance: randomScalar(), protocolFeeBalance: randomScalar(), amount: randomScalar()
        });

        PostMatchBalanceShare memory outBalancePublicShares = PostMatchBalanceShare({
            relayerFeeBalance: randomScalar(), protocolFeeBalance: randomScalar(), amount: randomScalar()
        });

        statement = IntentAndBalanceBoundedSettlementStatement({
            boundedMatchResult: matchResult,
            amountPublicShare: randomScalar(),
            inBalancePublicShares: inBalancePublicShares,
            outBalancePublicShares: outBalancePublicShares,
            externalRelayerFeeRate: relayerFeeRateFixedPoint,
            internalRelayerFeeRate: relayerFeeRateFixedPoint,
            relayerFeeAddress: relayerFeeAddr
        });
    }

    // --- Dummy Data --- //

    /// @dev Create a dummy intent and balance validity statement (first fill)
    function createSampleStatementFirstFill() internal returns (IntentAndBalanceValidityStatementFirstFill memory) {
        IntentPreMatchShare memory intentPublicShare = IntentPreMatchShare({
            inToken: randomScalar(), outToken: randomScalar(), owner: randomScalar(), minPrice: randomScalar()
        });

        BN254.ScalarField merkleRoot = darkpoolState.getMerkleRoot(DarkpoolConstants.DEFAULT_MERKLE_DEPTH);
        return IntentAndBalanceValidityStatementFirstFill({
            merkleRoot: merkleRoot,
            intentAndAuthorizingAddressCommitment: randomScalar(),
            intentPublicShare: intentPublicShare,
            intentPrivateShareCommitment: randomScalar(),
            intentRecoveryId: randomScalar(),
            balancePartialCommitment: randomPartialCommitment(),
            newOneTimeAddressPublicShare: randomScalar(),
            oldBalanceNullifier: randomScalar(),
            balanceRecoveryId: randomScalar(),
            oneTimeAuthorizingAddress: oneTimeOwner.addr
        });
    }

    /// @dev Create a dummy intent and balance validity statement (subsequent fill)
    function createSampleStatement() internal returns (IntentAndBalanceValidityStatement memory) {
        BN254.ScalarField merkleRoot = darkpoolState.getMerkleRoot(DarkpoolConstants.DEFAULT_MERKLE_DEPTH);
        return IntentAndBalanceValidityStatement({
            intentMerkleRoot: merkleRoot,
            oldIntentNullifier: randomScalar(),
            newIntentPartialCommitment: randomPartialCommitment(),
            intentRecoveryId: randomScalar(),
            balanceMerkleRoot: merkleRoot,
            oldBalanceNullifier: randomScalar(),
            balancePartialCommitment: randomPartialCommitment(),
            balanceRecoveryId: randomScalar()
        });
    }

    /// @dev Create a sample output balance bundle
    function createSampleOutputBalanceBundle() internal returns (OutputBalanceBundle memory) {
        BN254.ScalarField merkleRoot = darkpoolState.getMerkleRoot(DarkpoolConstants.DEFAULT_MERKLE_DEPTH);
        OutputBalanceValidityStatement memory statement = OutputBalanceValidityStatement({
            merkleRoot: merkleRoot,
            oldBalanceNullifier: randomScalar(),
            newPartialCommitment: randomPartialCommitment(),
            recoveryId: randomScalar()
        });

        ExistingBalanceBundle memory existingBalanceBundle = ExistingBalanceBundle({ statement: statement });
        return OutputBalanceBundle({
            merkleDepth: DarkpoolConstants.DEFAULT_MERKLE_DEPTH,
            bundleType: OutputBalanceBundleType.EXISTING_BALANCE,
            data: abi.encode(existingBalanceBundle),
            proof: createDummyProof(),
            settlementLinkingProof: createDummyLinkingProof()
        });
    }

    // --- Renegade Settled Bounded Bundle --- //

    /// @dev Create a complete renegade settled bounded private intent settlement bundle
    function createRenegadeSettledBoundedBundle(
        bool isFirstFill,
        BoundedMatchResult memory matchResult,
        Vm.Wallet memory owner
    )
        internal
        returns (SettlementBundle memory)
    {
        uint256 merkleDepth = DarkpoolConstants.DEFAULT_MERKLE_DEPTH;
        if (isFirstFill) {
            return createRenegadeSettledBoundedBundleFirstFill(merkleDepth, matchResult, owner);
        } else {
            return createRenegadeSettledBoundedBundleSubsequent(merkleDepth, matchResult);
        }
    }

    /// @dev Create a renegade settled bounded private intent settlement bundle for first fill
    function createRenegadeSettledBoundedBundleFirstFill(
        uint256 merkleDepth,
        BoundedMatchResult memory matchResult,
        Vm.Wallet memory oneTimeKey
    )
        internal
        returns (SettlementBundle memory)
    {
        // Create the validity statement
        IntentAndBalanceValidityStatementFirstFill memory validityStatement = createSampleStatementFirstFill();
        validityStatement.oneTimeAuthorizingAddress = oneTimeKey.addr;

        // Sign the owner signature digest
        // The signature is over intentAndAuthorizingAddressCommitment which combines
        // the intent commitment and the new one-time key hash
        SignatureWithNonce memory ownerSignature =
            createOwnerSignature(validityStatement.intentAndAuthorizingAddressCommitment, oneTimeKey.privateKey);

        // Create auth bundle
        RenegadeSettledIntentAuthBundleFirstFill memory auth = RenegadeSettledIntentAuthBundleFirstFill({
            merkleDepth: merkleDepth,
            ownerSignature: ownerSignature,
            statement: validityStatement,
            validityProof: createDummyProof()
        });

        // Create bounded settlement statement
        IntentAndBalanceBoundedSettlementStatement memory settlementStatement =
            createBoundedSettlementStatement(matchResult);

        // Create output balance bundle
        OutputBalanceBundle memory outputBalanceBundle = createSampleOutputBalanceBundle();

        // Create the bundle data
        RenegadeSettledIntentBoundedFirstFillBundle memory bundleData = RenegadeSettledIntentBoundedFirstFillBundle({
            auth: auth,
            outputBalanceBundle: outputBalanceBundle,
            settlementStatement: settlementStatement,
            settlementProof: createDummyProof(),
            authSettlementLinkingProof: createDummyLinkingProof()
        });

        // Encode and return the settlement bundle
        return SettlementBundle({
            isFirstFill: true, bundleType: SettlementBundleType.RENEGADE_SETTLED_INTENT, data: abi.encode(bundleData)
        });
    }

    /// @dev Create a renegade settled bounded private intent settlement bundle for subsequent fills
    function createRenegadeSettledBoundedBundleSubsequent(
        uint256 merkleDepth,
        BoundedMatchResult memory matchResult
    )
        internal
        returns (SettlementBundle memory)
    {
        // Get the actual Merkle root from the test state (must be in history for subsequent fills)
        BN254.ScalarField merkleRoot = darkpoolState.getMerkleRoot(merkleDepth);

        // Create the validity statement
        IntentAndBalanceValidityStatement memory validityStatement = createSampleStatement();

        // Create auth bundle (no signature needed for subsequent fills)
        RenegadeSettledIntentAuthBundle memory auth = RenegadeSettledIntentAuthBundle({
            merkleDepth: merkleDepth, statement: validityStatement, validityProof: createDummyProof()
        });

        // Create bounded settlement statement
        IntentAndBalanceBoundedSettlementStatement memory settlementStatement =
            createBoundedSettlementStatement(matchResult);

        // Create output balance bundle
        OutputBalanceBundle memory outputBalanceBundle = createSampleOutputBalanceBundle();

        // Create the bundle data
        RenegadeSettledIntentBoundedBundle memory bundleData = RenegadeSettledIntentBoundedBundle({
            auth: auth,
            outputBalanceBundle: outputBalanceBundle,
            settlementStatement: settlementStatement,
            settlementProof: createDummyProof(),
            authSettlementLinkingProof: createDummyLinkingProof()
        });

        // Encode and return the settlement bundle
        return SettlementBundle({
            isFirstFill: false, bundleType: SettlementBundleType.RENEGADE_SETTLED_INTENT, data: abi.encode(bundleData)
        });
    }
}


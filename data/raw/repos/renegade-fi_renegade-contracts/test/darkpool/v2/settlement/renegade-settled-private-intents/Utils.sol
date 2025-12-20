// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { Vm } from "forge-std/Vm.sol";
import { BN254 } from "solidity-bn254/BN254.sol";
import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";
import { SettlementBundle, SettlementBundleType } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { ObligationBundle, ObligationType, ObligationLib } from "darkpoolv2-types/settlement/ObligationBundle.sol";
import {
    SignatureWithNonce,
    RenegadeSettledIntentAuthBundleFirstFill,
    RenegadeSettledIntentAuthBundle
} from "darkpoolv2-types/settlement/IntentBundle.sol";
import {
    RenegadeSettledIntentFirstFillBundle,
    RenegadeSettledIntentBundle
} from "darkpoolv2-lib/settlement/bundles/PrivateIntentPrivateBalanceBundleLib.sol";
import {
    OutputBalanceBundle,
    OutputBalanceBundleType,
    ExistingBalanceBundle
} from "darkpoolv2-types/settlement/OutputBalanceBundle.sol";
import { SettlementContext, SettlementContextLib } from "darkpoolv2-types/settlement/SettlementContext.sol";
import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import {
    IntentAndBalanceValidityStatementFirstFill,
    IntentAndBalanceValidityStatement,
    OutputBalanceValidityStatement
} from "darkpoolv2-lib/public_inputs/ValidityProofs.sol";
import { IntentPreMatchShare } from "darkpoolv2-types/Intent.sol";
import { IntentAndBalancePublicSettlementStatement } from "darkpoolv2-lib/public_inputs/Settlement.sol";
import { PostMatchBalanceShare } from "darkpoolv2-types/Balance.sol";
import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";
import { SettlementTestUtils } from "../SettlementTestUtils.sol";
import { DarkpoolState, DarkpoolStateLib } from "darkpoolv2-lib/DarkpoolState.sol";

contract RenegadeSettledPrivateIntentTestUtils is SettlementTestUtils {
    using ObligationLib for ObligationBundle;
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

    // --- Dummy Data --- //

    /// @dev Create a dummy `SettlementContext` for the test
    function _createSettlementContext() internal pure virtual returns (SettlementContext memory context) {
        context = SettlementContextLib.newContext(
            0, /* numDeposits */ 2, /* numWithdrawals */ 3, /* verificationCapacity */ 2 /* proofLinkingCapacity */
        );
    }

    /// @dev Create a dummy intent and balance validity statement (first fill)
    function createSampleStatementFirstFill() internal returns (IntentAndBalanceValidityStatementFirstFill memory) {
        IntentPreMatchShare memory intentPublicShare = IntentPreMatchShare({
            inToken: randomScalar(),
            outToken: randomScalar(),
            owner: randomScalar(),
            minPrice: randomScalar()
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

    /// @dev Create a dummy settlement statement for intent and balance public settlement
    function createSampleRenegadeSettlementStatement(SettlementObligation memory obligation)
        internal
        returns (IntentAndBalancePublicSettlementStatement memory)
    {
        PostMatchBalanceShare memory inBalancePublicShares = PostMatchBalanceShare({
            relayerFeeBalance: randomScalar(),
            protocolFeeBalance: randomScalar(),
            amount: randomScalar()
        });

        PostMatchBalanceShare memory outBalancePublicShares = PostMatchBalanceShare({
            relayerFeeBalance: randomScalar(),
            protocolFeeBalance: randomScalar(),
            amount: randomScalar()
        });

        return IntentAndBalancePublicSettlementStatement({
            settlementObligation: obligation,
            amountPublicShare: randomScalar(),
            inBalancePublicShares: inBalancePublicShares,
            outBalancePublicShares: outBalancePublicShares,
            relayerFee: relayerFeeRateFixedPoint,
            relayerFeeRecipient: relayerFeeAddr
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

    /// @dev Helper to create a sample settlement bundle
    function createSampleRenegadeSettledBundle(bool isFirstFill)
        internal
        returns (ObligationBundle memory obligationBundle, SettlementBundle memory bundle)
    {
        // Create obligation
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1,) = createTradeObligations();
        obligationBundle =
            ObligationBundle({ obligationType: ObligationType.PUBLIC, data: abi.encode(obligation0, obligation1) });

        bundle = createRenegadeSettledBundle(isFirstFill, obligation0, oneTimeOwner);
    }

    /// @dev Create a complete settlement bundle given an obligation
    function createRenegadeSettledBundle(
        bool isFirstFill,
        SettlementObligation memory obligation,
        Vm.Wallet memory owner
    )
        internal
        returns (SettlementBundle memory)
    {
        uint256 merkleDepth = DarkpoolConstants.DEFAULT_MERKLE_DEPTH;
        if (isFirstFill) {
            return createRenegadeSettledBundleFirstFill(merkleDepth, obligation, owner);
        } else {
            return createRenegadeSettledBundleSubsequentFill(merkleDepth, obligation);
        }
    }

    /// @dev Create a complete settlement bundle with custom signer for the first fill
    function createRenegadeSettledBundleFirstFill(
        uint256 merkleDepth,
        SettlementObligation memory obligation,
        Vm.Wallet memory oneTimeKey
    )
        internal
        returns (SettlementBundle memory)
    {
        // Create the statement types
        IntentAndBalanceValidityStatementFirstFill memory validityStatement = createSampleStatementFirstFill();
        validityStatement.oneTimeAuthorizingAddress = oneTimeKey.addr;
        IntentAndBalancePublicSettlementStatement memory settlementStatement =
            createSampleRenegadeSettlementStatement(obligation);

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
        OutputBalanceBundle memory outputBalanceBundle = createSampleOutputBalanceBundle();
        RenegadeSettledIntentFirstFillBundle memory bundleData = RenegadeSettledIntentFirstFillBundle({
            auth: auth,
            outputBalanceBundle: outputBalanceBundle,
            settlementStatement: settlementStatement,
            settlementProof: createDummyProof(),
            authSettlementLinkingProof: createDummyLinkingProof()
        });

        // Encode the obligation and bundle
        return SettlementBundle({
            isFirstFill: true,
            bundleType: SettlementBundleType.RENEGADE_SETTLED_INTENT,
            data: abi.encode(bundleData)
        });
    }

    /// @dev Create a complete settlement bundle with custom signer and parameters
    function createRenegadeSettledBundleSubsequentFill(
        uint256 merkleDepth,
        SettlementObligation memory obligation
    )
        internal
        returns (SettlementBundle memory)
    {
        // Create the statement types
        IntentAndBalanceValidityStatement memory validityStatement = createSampleStatement();
        IntentAndBalancePublicSettlementStatement memory settlementStatement =
            createSampleRenegadeSettlementStatement(obligation);

        // Create auth bundle (no signature needed for subsequent fills)
        RenegadeSettledIntentAuthBundle memory auth = RenegadeSettledIntentAuthBundle({
            merkleDepth: merkleDepth,
            statement: validityStatement,
            validityProof: createDummyProof()
        });
        OutputBalanceBundle memory outputBalanceBundle = createSampleOutputBalanceBundle();
        RenegadeSettledIntentBundle memory bundleData = RenegadeSettledIntentBundle({
            auth: auth,
            outputBalanceBundle: outputBalanceBundle,
            settlementStatement: settlementStatement,
            settlementProof: createDummyProof(),
            authSettlementLinkingProof: createDummyLinkingProof()
        });

        // Encode the obligation and bundle
        return SettlementBundle({
            isFirstFill: false,
            bundleType: SettlementBundleType.RENEGADE_SETTLED_INTENT,
            data: abi.encode(bundleData)
        });
    }
}

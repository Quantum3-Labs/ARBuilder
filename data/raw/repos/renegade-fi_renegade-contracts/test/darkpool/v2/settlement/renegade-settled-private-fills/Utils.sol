// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { Vm } from "forge-std/Vm.sol";
import { BN254 } from "solidity-bn254/BN254.sol";
import { DarkpoolV2TestUtils } from "../../DarkpoolV2TestUtils.sol";
import { SettlementBundle, SettlementBundleType } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import {
    RenegadeSettledPrivateFirstFillBundle,
    RenegadeSettledPrivateFillBundle
} from "darkpoolv2-lib/settlement/bundles/RenegadeSettledPrivateFillLib.sol";
import {
    ObligationBundle,
    ObligationType,
    ObligationLib,
    PrivateObligationBundle
} from "darkpoolv2-types/settlement/ObligationBundle.sol";
import {
    SignatureWithNonce,
    RenegadeSettledIntentAuthBundleFirstFill,
    RenegadeSettledIntentAuthBundle
} from "darkpoolv2-types/settlement/IntentBundle.sol";
import { SettlementContext, SettlementContextLib } from "darkpoolv2-types/settlement/SettlementContext.sol";
import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import {
    IntentAndBalanceValidityStatementFirstFill,
    IntentAndBalanceValidityStatement
} from "darkpoolv2-lib/public_inputs/ValidityProofs.sol";
import { IntentPreMatchShare } from "darkpoolv2-types/Intent.sol";
import { IntentAndBalancePrivateSettlementStatement } from "darkpoolv2-lib/public_inputs/Settlement.sol";
import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";
import { PostMatchBalanceShare, PreMatchBalanceShare } from "darkpoolv2-types/Balance.sol";
import { DarkpoolState, DarkpoolStateLib } from "darkpoolv2-lib/DarkpoolState.sol";
import {
    OutputBalanceBundle,
    OutputBalanceBundleType,
    NewBalanceBundle
} from "darkpoolv2-types/settlement/OutputBalanceBundle.sol";
import { NewOutputBalanceValidityStatement } from "darkpoolv2-lib/public_inputs/ValidityProofs.sol";

contract RenegadeSettledPrivateFillTestUtils is DarkpoolV2TestUtils {
    using ObligationLib for ObligationBundle;
    using FixedPointLib for FixedPoint;
    using DarkpoolStateLib for DarkpoolState;

    // ---------
    // | Utils |
    // ---------

    // --- Signatures --- //

    /// @dev Sign the owner signature digest for a renegade settled private fill
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
    function _createSettlementContext() internal pure returns (SettlementContext memory context) {
        context = SettlementContextLib.newContext(
            0, /* numDeposits */ 0, /* numWithdrawals */ 2, /* verificationCapacity */ 2 /* proofLinkingCapacity */
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

    /// @dev Create a dummy output balance bundle (new balance)
    function createOutputBalanceBundle(uint256 merkleDepth) internal returns (OutputBalanceBundle memory) {
        PreMatchBalanceShare memory preMatchBalanceShares = PreMatchBalanceShare({
            mint: randomScalar(),
            owner: randomScalar(),
            relayerFeeRecipient: randomScalar(),
            oneTimeAuthority: randomScalar()
        });

        NewOutputBalanceValidityStatement memory statement = NewOutputBalanceValidityStatement({
            preMatchBalanceShares: preMatchBalanceShares,
            newBalancePartialCommitment: randomPartialCommitment(),
            recoveryId: randomScalar()
        });

        NewBalanceBundle memory bundleData = NewBalanceBundle({ statement: statement });

        return OutputBalanceBundle({
            merkleDepth: merkleDepth,
            bundleType: OutputBalanceBundleType.NEW_BALANCE,
            data: abi.encode(bundleData),
            proof: createDummyProof(),
            settlementLinkingProof: createDummyLinkingProof()
        });
    }

    /// @dev Create a dummy private obligation bundle for a private fill
    function createPrivateObligationBundle() internal returns (PrivateObligationBundle memory) {
        PostMatchBalanceShare memory party0InBalanceShares = randomPostMatchBalanceShare();
        PostMatchBalanceShare memory party0OutBalanceShares = randomPostMatchBalanceShare();
        PostMatchBalanceShare memory party1InBalanceShares = randomPostMatchBalanceShare();
        PostMatchBalanceShare memory party1OutBalanceShares = randomPostMatchBalanceShare();

        FixedPoint memory protocolFee = darkpool.getDefaultProtocolFee();
        IntentAndBalancePrivateSettlementStatement memory statement = IntentAndBalancePrivateSettlementStatement({
            newAmountPublicShare0: randomScalar(),
            newInBalancePublicShares0: party0InBalanceShares,
            newOutBalancePublicShares0: party0OutBalanceShares,
            newAmountPublicShare1: randomScalar(),
            newInBalancePublicShares1: party1InBalanceShares,
            newOutBalancePublicShares1: party1OutBalanceShares,
            relayerFee0: randomFee(),
            relayerFee1: randomFee(),
            protocolFee: protocolFee
        });

        return PrivateObligationBundle({ statement: statement, proof: createDummyProof() });
    }

    /// @dev Helper to create a sample settlement bundle
    function createSampleBundle(bool isFirstFill)
        internal
        returns (ObligationBundle memory obligationBundle, SettlementBundle memory bundle)
    {
        // Create private obligation
        PrivateObligationBundle memory privateObligation = createPrivateObligationBundle();
        obligationBundle =
            ObligationBundle({ obligationType: ObligationType.PRIVATE, data: abi.encode(privateObligation) });

        bundle = createRenegadeSettledPrivateFillBundle(isFirstFill, oneTimeOwner);
    }

    /// @dev Create a complete settlement bundle given an owner
    function createRenegadeSettledPrivateFillBundle(
        bool isFirstFill,
        Vm.Wallet memory owner
    )
        internal
        returns (SettlementBundle memory)
    {
        uint256 merkleDepth = DarkpoolConstants.DEFAULT_MERKLE_DEPTH;
        if (isFirstFill) {
            return createRenegadeSettledPrivateFillBundleFirstFill(merkleDepth, owner);
        } else {
            return createRenegadeSettledPrivateFillBundleSubsequentFill(merkleDepth);
        }
    }

    /// @dev Create a complete settlement bundle for the first fill
    function createRenegadeSettledPrivateFillBundleFirstFill(
        uint256 merkleDepth,
        Vm.Wallet memory oneTimeKey
    )
        internal
        returns (SettlementBundle memory)
    {
        // Create the statement
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

        // Create output balance bundle
        OutputBalanceBundle memory outputBalanceBundle = createOutputBalanceBundle(merkleDepth);
        RenegadeSettledPrivateFirstFillBundle memory bundleData = RenegadeSettledPrivateFirstFillBundle({
            auth: auth,
            outputBalanceBundle: outputBalanceBundle,
            authSettlementLinkingProof: createDummyLinkingProof()
        });

        // Encode the bundle
        return SettlementBundle({
            isFirstFill: true,
            bundleType: SettlementBundleType.RENEGADE_SETTLED_PRIVATE_FILL,
            data: abi.encode(bundleData)
        });
    }

    /// @dev Create a complete settlement bundle for a subsequent fill
    function createRenegadeSettledPrivateFillBundleSubsequentFill(uint256 merkleDepth)
        internal
        returns (SettlementBundle memory)
    {
        // Create the statement
        IntentAndBalanceValidityStatement memory validityStatement = createSampleStatement();

        // Create auth bundle (no signature needed for subsequent fills)
        RenegadeSettledIntentAuthBundle memory auth = RenegadeSettledIntentAuthBundle({
            merkleDepth: merkleDepth,
            statement: validityStatement,
            validityProof: createDummyProof()
        });

        // Create output balance bundle
        OutputBalanceBundle memory outputBalanceBundle = createOutputBalanceBundle(merkleDepth);
        RenegadeSettledPrivateFillBundle memory bundleData = RenegadeSettledPrivateFillBundle({
            auth: auth,
            outputBalanceBundle: outputBalanceBundle,
            authSettlementLinkingProof: createDummyLinkingProof()
        });

        // Encode the bundle
        return SettlementBundle({
            isFirstFill: false,
            bundleType: SettlementBundleType.RENEGADE_SETTLED_PRIVATE_FILL,
            data: abi.encode(bundleData)
        });
    }
}

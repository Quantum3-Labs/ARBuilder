// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { DarkpoolV2TestUtils } from "../../DarkpoolV2TestUtils.sol";
import { Intent } from "darkpoolv2-types/Intent.sol";
import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";
import { SettlementObligation, SettlementObligationLib } from "darkpoolv2-types/Obligation.sol";
import {
    SettlementBundle,
    SettlementBundleType,
    PublicIntentPublicBalanceBundle
} from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { ObligationBundle, ObligationType, ObligationLib } from "darkpoolv2-types/settlement/ObligationBundle.sol";
import {
    SignatureWithNonce,
    PublicIntentAuthBundle,
    PublicIntentPermit,
    PublicIntentPermitLib
} from "darkpoolv2-types/settlement/IntentBundle.sol";
import { SettlementContext, SettlementContextLib } from "darkpoolv2-types/settlement/SettlementContext.sol";
import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { FeeRate } from "darkpoolv2-types/Fee.sol";
import { SettlementTestUtils } from "../SettlementTestUtils.sol";

contract PublicIntentSettlementTestUtils is SettlementTestUtils {
    using ObligationLib for ObligationBundle;
    using PublicIntentPermitLib for PublicIntentPermit;
    using FixedPointLib for FixedPoint;

    // ---------
    // | Utils |
    // ---------

    // --- Signatures --- //

    /// @dev Sign an intent permit
    function signIntentPermit(
        PublicIntentPermit memory permit,
        uint256 signerPrivateKey
    )
        internal
        returns (SignatureWithNonce memory)
    {
        // Sign with the private key
        uint256 nonce = randomUint();
        bytes32 permitHash = permit.computeHash();
        bytes32 signatureDigest = EfficientHashLib.hash(permitHash, bytes32(nonce));

        (uint8 v, bytes32 r, bytes32 s) = vm.sign(signerPrivateKey, signatureDigest);
        return SignatureWithNonce({ nonce: nonce, signature: abi.encodePacked(r, s, v) });
    }

    /// @dev Sign an obligation (memory version)
    function createExecutorSignature(
        FeeRate memory feeRate,
        SettlementObligation memory obligation,
        uint256 signerPrivateKey
    )
        internal
        returns (SignatureWithNonce memory)
    {
        // Use the calldata version via external call for memory-to-calldata conversion
        return this._createExecutorSignatureCalldata(obligation, feeRate, signerPrivateKey);
    }

    /// @dev Sign an obligation (calldata version)
    function _createExecutorSignatureCalldata(
        SettlementObligation memory obligation,
        FeeRate memory feeRate,
        uint256 signerPrivateKey
    )
        external
        returns (SignatureWithNonce memory)
    {
        // Hash the fee with obligation
        bytes memory encoded = abi.encode(feeRate, obligation);
        bytes32 digest = EfficientHashLib.hash(encoded);

        // Sign with the private key
        uint256 nonce = randomUint();
        bytes32 signatureHash = EfficientHashLib.hash(digest, bytes32(nonce));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(signerPrivateKey, signatureHash);
        return SignatureWithNonce({ nonce: nonce, signature: abi.encodePacked(r, s, v) });
    }

    // --- Dummy Data --- //

    /// @dev Create a dummy `SettlementTransfers` list for the test
    function _createSettlementContext() internal pure virtual returns (SettlementContext memory context) {
        context = SettlementContextLib.newContext(
            1, /* numDeposits */ 3, /* numWithdrawals */ 1, /* verificationCapacity */ 1 /* proofLinkingCapacity */
        );
    }

    /// @dev Helper to create a sample settlement bundle
    function createSamplePublicIntentBundle()
        internal
        returns (SettlementBundle memory settlementBundle, ObligationBundle memory obligationBundle)
    {
        (SettlementObligation memory obligation0, SettlementObligation memory obligation1,) = createTradeObligations();
        Intent memory intent0 = createIntentForObligation(obligation0);
        settlementBundle = createPublicIntentSettlementBundle(intent0, obligation0);
        obligationBundle =
            ObligationBundle({ obligationType: ObligationType.PUBLIC, data: abi.encode(obligation0, obligation1) });
    }

    /// @dev Create a complete settlement bundle given an intent and an obligation
    function createPublicIntentSettlementBundle(
        Intent memory intent,
        SettlementObligation memory obligation
    )
        public
        returns (SettlementBundle memory)
    {
        return createPublicIntentSettlementBundleWithSigners(
            intent, obligation, intentOwner.privateKey, executor.privateKey
        );
    }

    /// @dev Create a complete settlement bundle with custom signers
    function createPublicIntentSettlementBundleWithSigners(
        Intent memory intent,
        SettlementObligation memory obligation,
        uint256 intentOwnerPrivateKey,
        uint256 executorPrivateKey
    )
        internal
        returns (SettlementBundle memory)
    {
        // Create the permit and sign it with the owner key
        PublicIntentPermit memory permit = PublicIntentPermit({ intent: intent, executor: executor.addr });
        SignatureWithNonce memory intentSignature = signIntentPermit(permit, intentOwnerPrivateKey);

        // Create relayer fee rate and sign the executor digest with the executor key
        FeeRate memory feeRate = relayerFeeRate();
        SignatureWithNonce memory executorSignature = createExecutorSignature(feeRate, obligation, executorPrivateKey);

        // Create auth bundle
        PublicIntentAuthBundle memory auth = PublicIntentAuthBundle({
            permit: permit,
            intentSignature: intentSignature,
            executorSignature: executorSignature
        });
        PublicIntentPublicBalanceBundle memory bundleData =
            PublicIntentPublicBalanceBundle({ auth: auth, relayerFeeRate: feeRate });

        // Create the complete settlement bundle
        return SettlementBundle({
            isFirstFill: false,
            bundleType: SettlementBundleType.NATIVELY_SETTLED_PUBLIC_INTENT,
            data: abi.encode(bundleData)
        });
    }
}

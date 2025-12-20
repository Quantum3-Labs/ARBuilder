// SPDX-License-Identifier: Apache
/* solhint-disable one-contract-per-file */
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { PublicIntentAuthBundle } from "darkpoolv2-types/settlement/IntentBundle.sol";
import {
    IntentPublicShareLib,
    IntentPublicShare,
    IntentPreMatchShareLib,
    IntentPreMatchShare
} from "darkpoolv2-types/Intent.sol";
import { PostMatchBalanceShare, PostMatchBalanceShareLib } from "darkpoolv2-types/Balance.sol";
import { FeeRate } from "darkpoolv2-types/Fee.sol";
import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";
import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";

// ---------------------------
// | Settlement Bundle Types |
// ---------------------------

/// @notice The party IDs in a trade
enum PartyId {
    PARTY_0,
    PARTY_1
}

/// @notice A settlement bundle for a user
/// @dev This type encapsulates all the data required to validate a user's state elements input to a trade
/// and settle the trade.
struct SettlementBundle {
    /// @dev Whether this is the first fill or subsequent fill
    bool isFirstFill;
    /// @dev The type of settlement bundle
    SettlementBundleType bundleType;
    /// @dev The data validating the settlement bundle
    bytes data;
}

/// @notice The type of settlement bundle
/// @dev Each settlement bundle may be of a different type depending on the privacy configuration of the trade.
/// @dev A settlement bundle contains an intent and a balance capitalizing the intent; each of which may be
/// public or private. This gives us four possible combinations:
/// 1. Public intent and public balance
/// 2. Public intent and private balance
/// 3. Private intent and public balance
/// 4. Private intent and private balance
/// As well, the settlement obligation itself may be public or private. A private obligation only makes sense
/// when two private intent, private balances cross.
///
/// We currently have no use for a private balance with a public intent, so we remove that use case.
/// This leaves us with the following settlement bundle types:
/// 1. *Natively Settled Public Intent*: A public intent with a public (EOA) balance
/// 2. *Natively Settled Private Intent*: A private intent with a public (EOA) balance
/// 3. *Renegade Settled Intent*: A private intent with a private (darkpool) balance
/// 4. *Renegade Settled Private Fill*: A private intent with a private (darkpool) balance settling a private obligation
enum SettlementBundleType {
    NATIVELY_SETTLED_PUBLIC_INTENT,
    NATIVELY_SETTLED_PRIVATE_INTENT,
    RENEGADE_SETTLED_INTENT,
    RENEGADE_SETTLED_PRIVATE_FILL
}

/// @notice The settlement bundle data for a `NATIVELY_SETTLED_PUBLIC_INTENT` bundle
struct PublicIntentPublicBalanceBundle {
    /// @dev The public intent authorization payload with signature attached
    PublicIntentAuthBundle auth;
    /// @dev The relayer's fee take for the match
    FeeRate relayerFeeRate;
}

/// @title Settlement Bundle Library
/// @author Renegade Eng
/// @notice Library for decoding settlement bundle data
library SettlementBundleLib {
    using BN254 for BN254.ScalarField;
    using IntentPublicShareLib for IntentPublicShare;
    using IntentPreMatchShareLib for IntentPreMatchShare;
    using PostMatchBalanceShareLib for PostMatchBalanceShare;

    // --- Context Allocation --- //

    /// @notice Get the number of deposits a settlement bundle will require in order to settle
    /// @param bundle The settlement bundle to get the number of deposits for
    /// @dev If the bundle is natively settled, it will require 1 deposit.
    /// If the bundle is Renegade settled, no deposits are required.
    /// @return The number of deposits required to settle the bundle
    function getNumDeposits(SettlementBundle calldata bundle) internal pure returns (uint256) {
        if (isNativelySettled(bundle)) {
            return 1; // One deposit
        }

        // All balance updates are Merklized
        return 0;
    }

    /// @notice Get the number of withdrawals a settlement bundle will require in order to settle
    /// @param bundle The settlement bundle to get the number of withdrawals for
    /// @dev If the bundle is natively settled, it will require 3 withdrawals; one for the trader and two for the fees.
    /// If the bundle is Renegade settled, no withdrawals are required.
    /// @return The number of withdrawals required to settle the bundle
    function getNumWithdrawals(SettlementBundle calldata bundle) internal pure returns (uint256) {
        if (isNativelySettled(bundle)) {
            return 3; // One withdrawal for the trader and two for the fees
        } else if (bundle.bundleType == SettlementBundleType.RENEGADE_SETTLED_INTENT) {
            // A renegade settled intent with a public fill
            // We pay fees immediately after the match is settled to the fee collection EOAs, this results in two
            // withdrawals
            return 2;
        }

        // All balance updates are Merklized
        return 0;
    }

    /// @notice Get the number of proofs which need to be verified for a settlement bundle
    /// @param bundle The settlement bundle to get the number of proofs for
    /// @return numProofs The number of proofs required to settle the bundle
    function getNumProofs(SettlementBundle calldata bundle) internal pure returns (uint256 numProofs) {
        if (bundle.bundleType == SettlementBundleType.NATIVELY_SETTLED_PUBLIC_INTENT) {
            numProofs = 0;
        } else if (bundle.bundleType == SettlementBundleType.NATIVELY_SETTLED_PRIVATE_INTENT) {
            // Validity proof and a settlement proof
            numProofs = 2;
        } else {
            // Validity proof, output balance validity proof, and a settlement proof
            // Strictly speaking, this over-allocates proof capacity for RENEGADE_SETTLED_PRIVATE_FILL, which has one
            // settlement proof shared between the two parties.
            numProofs = 3;
        }
    }

    /// @notice Get the number of proof linking arguments which need to be verified for a settlement bundle
    /// @param bundle The settlement bundle to get the number of proof linking arguments for
    /// @return numProofLinkingArguments The number of proof linking arguments required to settle the bundle
    function getNumProofLinkingArguments(SettlementBundle calldata bundle)
        internal
        pure
        returns (uint256 numProofLinkingArguments)
    {
        if (bundle.bundleType == SettlementBundleType.NATIVELY_SETTLED_PUBLIC_INTENT) {
            numProofLinkingArguments = 0;
        } else if (bundle.bundleType == SettlementBundleType.NATIVELY_SETTLED_PRIVATE_INTENT) {
            // A natively settled private intent links the intent authorization with the settlement proof
            numProofLinkingArguments = 1;
        } else {
            // A private balance type requires an extra proof linking argument to link the output balance validity proof
            // into the settlement proof
            numProofLinkingArguments = 2;
        }
    }

    // --- Field Access --- //

    /// @notice Return whether a settlement bundle is natively settled; i.e. is
    /// capitalized by an EOA balance
    /// @param bundle The settlement bundle to check
    /// @return Whether the settlement bundle is natively settled
    function isNativelySettled(SettlementBundle calldata bundle) internal pure returns (bool) {
        return bundle.bundleType == SettlementBundleType.NATIVELY_SETTLED_PUBLIC_INTENT
            || bundle.bundleType == SettlementBundleType.NATIVELY_SETTLED_PRIVATE_INTENT;
    }

    // --- Authorization Validation --- //

    /// @notice Compute the digest which the executor must sign for a natively settled public intent bundle
    /// @dev The digest is the hash of the relayer's fee take and the obligation. The executor authorizes both these
    /// values through a signature.
    /// @param bundleData The bundle data to compute the digest for
    /// @param obligation The settlement obligation to compute the digest for
    /// @return digest The digest which the executor must sign
    function computeExecutorDigest(
        PublicIntentPublicBalanceBundle memory bundleData,
        SettlementObligation memory obligation
    )
        internal
        pure
        returns (bytes32 digest)
    {
        // Encode and hash the fee take with the obligation
        bytes memory encoded = abi.encode(bundleData.relayerFeeRate, obligation);
        digest = EfficientHashLib.hash(encoded);
    }

    // --- Bundle Decoding --- //

    /// @notice Decode a public settlement bundle
    /// @param bundle The settlement bundle to decode
    /// @return bundleData The decoded bundle data
    function decodePublicBundleData(SettlementBundle calldata bundle)
        internal
        pure
        returns (PublicIntentPublicBalanceBundle memory bundleData)
    {
        bool validType = !bundle.isFirstFill && bundle.bundleType == SettlementBundleType.NATIVELY_SETTLED_PUBLIC_INTENT;
        require(validType, IDarkpoolV2.InvalidSettlementBundleType());
        bundleData = abi.decode(bundle.data, (PublicIntentPublicBalanceBundle));
    }
}

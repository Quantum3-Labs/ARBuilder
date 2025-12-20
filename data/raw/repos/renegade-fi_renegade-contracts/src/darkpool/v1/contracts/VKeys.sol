// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { VerificationKey, ProofLinkingVK } from "renegade-lib/verifier/Types.sol";
import { VerificationKeys } from "darkpoolv1-lib/VerificationKeys.sol";
import { IVKeys } from "darkpoolv1-interfaces/IVKeys.sol";

/// @title VKeys
/// @author Renegade Eng
/// @notice Implementation of the verification keys in the darkpool
contract VKeys is IVKeys {
    // Individual verification keys
    /// @notice Get the verification keys for `VALID WALLET CREATE`
    /// @return The verification key for `VALID WALLET CREATE`
    function walletCreateKeys() external pure override returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.VALID_WALLET_CREATE_VKEY);
    }

    /// @notice Get the verification keys for `VALID WALLET UPDATE`
    /// @return The verification key for `VALID WALLET UPDATE`
    function walletUpdateKeys() external pure override returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.VALID_WALLET_UPDATE_VKEY);
    }

    /// @notice Get the verification keys for `VALID OFFLINE FEE SETTLEMENT`
    /// @return The verification key for `VALID OFFLINE FEE SETTLEMENT`
    function offlineFeeSettlementKeys() external pure override returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.VALID_OFFLINE_FEE_SETTLEMENT_VKEY);
    }

    /// @notice Get the verification keys for `VALID FEE REDEMPTION`
    /// @return The verification key for `VALID FEE REDEMPTION`
    function feeRedemptionKeys() external pure override returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.VALID_FEE_REDEMPTION_VKEY);
    }

    /// @notice Get the verification keys for `VALID MATCH BUNDLE`
    /// @return commitmentsVk The verification key for `VALID COMMITMENTS`
    /// @return reblindVk The verification key for `VALID REBLIND`
    /// @return settleVk The verification key for `VALID MATCH SETTLE`
    /// @return reblindCommitmentsVk The proof linking key for reblind-commitments
    /// @return commitmentsMatchSettleVk0 The proof linking key for commitments-match-settle (party 0)
    /// @return commitmentsMatchSettleVk1 The proof linking key for commitments-match-settle (party 1)
    function matchBundleKeys()
        external
        pure
        override
        returns (
            VerificationKey memory commitmentsVk,
            VerificationKey memory reblindVk,
            VerificationKey memory settleVk,
            ProofLinkingVK memory reblindCommitmentsVk,
            ProofLinkingVK memory commitmentsMatchSettleVk0,
            ProofLinkingVK memory commitmentsMatchSettleVk1
        )
    {
        commitmentsVk = __deserializeKey(VerificationKeys.VALID_COMMITMENTS_VKEY);
        reblindVk = __deserializeKey(VerificationKeys.VALID_REBLIND_VKEY);
        settleVk = __deserializeKey(VerificationKeys.VALID_MATCH_SETTLE_VKEY);
        reblindCommitmentsVk = __deserializeLinkKey(VerificationKeys.VALID_REBLIND_COMMITMENTS_LINK_VKEY);
        commitmentsMatchSettleVk0 = __deserializeLinkKey(VerificationKeys.VALID_COMMITMENTS_MATCH_SETTLE_LINK0_VKEY);
        commitmentsMatchSettleVk1 = __deserializeLinkKey(VerificationKeys.VALID_COMMITMENTS_MATCH_SETTLE_LINK1_VKEY);
    }

    /// @notice Match bundle with commitments vkeys
    ///
    /// @dev We use the linking vkeys for the match bundle circuit as the `VALID MATCH SETTLE` variants all use
    /// @dev the same link group layouts
    /// @return commitmentsVk The verification key for `VALID COMMITMENTS`
    /// @return reblindVk The verification key for `VALID REBLIND`
    /// @return settleVk The verification key for `VALID MATCH SETTLE WITH COMMITMENTS`
    /// @return reblindCommitmentsVk The proof linking key for reblind-commitments
    /// @return commitmentsMatchSettleVk0 The proof linking key for commitments-match-settle (party 0)
    /// @return commitmentsMatchSettleVk1 The proof linking key for commitments-match-settle (party 1)
    function matchBundleWithCommitmentsKeys()
        external
        pure
        override
        returns (
            VerificationKey memory commitmentsVk,
            VerificationKey memory reblindVk,
            VerificationKey memory settleVk,
            ProofLinkingVK memory reblindCommitmentsVk,
            ProofLinkingVK memory commitmentsMatchSettleVk0,
            ProofLinkingVK memory commitmentsMatchSettleVk1
        )
    {
        commitmentsVk = __deserializeKey(VerificationKeys.VALID_COMMITMENTS_VKEY);
        reblindVk = __deserializeKey(VerificationKeys.VALID_REBLIND_VKEY);
        settleVk = __deserializeKey(VerificationKeys.VALID_MATCH_SETTLE_WITH_COMMITMENTS_VKEY);
        reblindCommitmentsVk = __deserializeLinkKey(VerificationKeys.VALID_REBLIND_COMMITMENTS_LINK_VKEY);
        commitmentsMatchSettleVk0 = __deserializeLinkKey(VerificationKeys.VALID_COMMITMENTS_MATCH_SETTLE_LINK0_VKEY);
        commitmentsMatchSettleVk1 = __deserializeLinkKey(VerificationKeys.VALID_COMMITMENTS_MATCH_SETTLE_LINK1_VKEY);
    }

    /// @notice Get the verification keys for `VALID ATOMIC MATCH BUNDLE`
    /// @return commitmentsVk The verification key for `VALID COMMITMENTS`
    /// @return reblindVk The verification key for `VALID REBLIND`
    /// @return settleVk The verification key for `VALID MATCH SETTLE ATOMIC`
    /// @return reblindCommitmentsVk The proof linking key for reblind-commitments
    /// @return commitmentsMatchSettleVk The proof linking key for commitments-match-settle
    function atomicMatchBundleKeys()
        external
        pure
        override
        returns (
            VerificationKey memory commitmentsVk,
            VerificationKey memory reblindVk,
            VerificationKey memory settleVk,
            ProofLinkingVK memory reblindCommitmentsVk,
            ProofLinkingVK memory commitmentsMatchSettleVk
        )
    {
        commitmentsVk = __deserializeKey(VerificationKeys.VALID_COMMITMENTS_VKEY);
        reblindVk = __deserializeKey(VerificationKeys.VALID_REBLIND_VKEY);
        settleVk = __deserializeKey(VerificationKeys.VALID_MATCH_SETTLE_ATOMIC_VKEY);
        reblindCommitmentsVk = __deserializeLinkKey(VerificationKeys.VALID_REBLIND_COMMITMENTS_LINK_VKEY);
        commitmentsMatchSettleVk = __deserializeLinkKey(VerificationKeys.VALID_COMMITMENTS_MATCH_SETTLE_LINK0_VKEY);
    }

    /// @notice Atomic match bundle with commitments vkeys
    ///
    /// @dev We use the linking vkeys for the atomic match bundle circuit as the `VALID MATCH SETTLE ATOMIC` variants
    /// @dev all use the same link group layouts
    /// @return commitmentsVk The verification key for `VALID COMMITMENTS`
    /// @return reblindVk The verification key for `VALID REBLIND`
    /// @return settleVk The verification key for `VALID MATCH SETTLE ATOMIC WITH COMMITMENTS`
    /// @return reblindCommitmentsVk The proof linking key for reblind-commitments
    /// @return commitmentsMatchSettleVk The proof linking key for commitments-match-settle
    function atomicMatchBundleWithCommitmentsKeys()
        external
        pure
        override
        returns (
            VerificationKey memory commitmentsVk,
            VerificationKey memory reblindVk,
            VerificationKey memory settleVk,
            ProofLinkingVK memory reblindCommitmentsVk,
            ProofLinkingVK memory commitmentsMatchSettleVk
        )
    {
        commitmentsVk = __deserializeKey(VerificationKeys.VALID_COMMITMENTS_VKEY);
        reblindVk = __deserializeKey(VerificationKeys.VALID_REBLIND_VKEY);
        settleVk = __deserializeKey(VerificationKeys.VALID_MATCH_SETTLE_ATOMIC_WITH_COMMITMENTS_VKEY);
        reblindCommitmentsVk = __deserializeLinkKey(VerificationKeys.VALID_REBLIND_COMMITMENTS_LINK_VKEY);
        commitmentsMatchSettleVk = __deserializeLinkKey(VerificationKeys.VALID_COMMITMENTS_MATCH_SETTLE_LINK0_VKEY);
    }

    /// @notice Get the verification keys for `VALID MALLEABLE MATCH BUNDLE`
    /// @return commitmentsVk The verification key for `VALID COMMITMENTS`
    /// @return reblindVk The verification key for `VALID REBLIND`
    /// @return settleVk The verification key for `VALID MALLEABLE MATCH SETTLE ATOMIC`
    /// @return reblindCommitmentsVk The proof linking key for reblind-commitments
    /// @return commitmentsMatchSettleVk The proof linking key for commitments-match-settle
    function malleableMatchBundleKeys()
        external
        pure
        override
        returns (
            VerificationKey memory commitmentsVk,
            VerificationKey memory reblindVk,
            VerificationKey memory settleVk,
            ProofLinkingVK memory reblindCommitmentsVk,
            ProofLinkingVK memory commitmentsMatchSettleVk
        )
    {
        commitmentsVk = __deserializeKey(VerificationKeys.VALID_COMMITMENTS_VKEY);
        reblindVk = __deserializeKey(VerificationKeys.VALID_REBLIND_VKEY);
        settleVk = __deserializeKey(VerificationKeys.VALID_MALLEABLE_MATCH_SETTLE_ATOMIC_VKEY);
        reblindCommitmentsVk = __deserializeLinkKey(VerificationKeys.VALID_REBLIND_COMMITMENTS_LINK_VKEY);
        commitmentsMatchSettleVk = __deserializeLinkKey(VerificationKeys.VALID_COMMITMENTS_MATCH_SETTLE_LINK0_VKEY);
    }

    /// @notice Deserialize a verification key
    /// @param vkeyBytes The bytes of the verification key
    /// @return vk The verification key
    function __deserializeKey(bytes memory vkeyBytes) internal pure returns (VerificationKey memory vk) {
        return abi.decode(vkeyBytes, (VerificationKey));
    }

    /// @notice Deserialize a proof linking verification key from bytes
    /// @param vkeyBytes The bytes of the proof linking verification key
    /// @return vk The deserialized proof linking verification key
    function __deserializeLinkKey(bytes memory vkeyBytes) internal pure returns (ProofLinkingVK memory vk) {
        return abi.decode(vkeyBytes, (ProofLinkingVK));
    }
}

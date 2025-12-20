// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { ProofLinkingVK } from "renegade-lib/verifier/Types.sol";
import { VerificationKeys } from "darkpoolv2-lib/VerificationKeys.sol";

/// @title ProofLinkingVKeys
/// @author Renegade Eng
/// @notice Verification keys for proof linking
contract ProofLinkingVKeys {
    /// @notice Get the verification key for `INTENT ONLY SETTLEMENT`
    /// @return The verification key for `INTENT ONLY SETTLEMENT`
    function intentOnlySettlementLinkingKey() external pure returns (ProofLinkingVK memory) {
        return __deserializeLinkKey(VerificationKeys.INTENT_ONLY_SETTLEMENT_VKEY);
    }

    /// @notice Get the verification key for `INTENT AND BALANCE SETTLEMENT 0`
    /// @return The verification key for `INTENT AND BALANCE SETTLEMENT 0`
    function intentAndBalanceSettlement0LinkingKey() external pure returns (ProofLinkingVK memory) {
        return __deserializeLinkKey(VerificationKeys.INTENT_AND_BALANCE_SETTLEMENT0_VKEY);
    }

    /// @notice Get the verification key for `INTENT AND BALANCE SETTLEMENT 1`
    /// @return The verification key for `INTENT AND BALANCE SETTLEMENT 1`
    function intentAndBalanceSettlement1LinkingKey() external pure returns (ProofLinkingVK memory) {
        return __deserializeLinkKey(VerificationKeys.INTENT_AND_BALANCE_SETTLEMENT1_VKEY);
    }

    /// @notice Get the verification key for `OUTPUT BALANCE SETTLEMENT 0`
    /// @return The verification key for `OUTPUT BALANCE SETTLEMENT 0`
    function outputBalanceSettlement0LinkingKey() external pure returns (ProofLinkingVK memory) {
        return __deserializeLinkKey(VerificationKeys.OUTPUT_BALANCE_SETTLEMENT0_VKEY);
    }

    /// @notice Get the verification key for `OUTPUT BALANCE SETTLEMENT 1`
    /// @return The verification key for `OUTPUT BALANCE SETTLEMENT 1`
    function outputBalanceSettlement1LinkingKey() external pure returns (ProofLinkingVK memory) {
        return __deserializeLinkKey(VerificationKeys.OUTPUT_BALANCE_SETTLEMENT1_VKEY);
    }

    /// @notice Deserialize a proof linking verification key from bytes
    /// @param vkeyBytes The bytes of the proof linking verification key
    /// @return vk The deserialized proof linking verification key
    function __deserializeLinkKey(bytes memory vkeyBytes) internal pure returns (ProofLinkingVK memory vk) {
        return abi.decode(vkeyBytes, (ProofLinkingVK));
    }
}

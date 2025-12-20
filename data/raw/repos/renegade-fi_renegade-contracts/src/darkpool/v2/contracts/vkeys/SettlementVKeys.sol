// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { VerificationKey } from "renegade-lib/verifier/Types.sol";
import { VerificationKeys } from "darkpoolv2-lib/VerificationKeys.sol";

/// @title SettlementVKeys
/// @author Renegade Eng
/// @notice Verification keys for settlement and validity proofs
contract SettlementVKeys {
    /// @notice Get the verification key for `INTENT ONLY FIRST FILL VALIDITY`
    /// @return The verification key for `INTENT ONLY FIRST FILL VALIDITY`
    function intentOnlyFirstFillValidityKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.INTENT_ONLY_FIRST_FILL_VALIDITY_VKEY);
    }

    /// @notice Get the verification key for `INTENT ONLY VALIDITY`
    /// @return The verification key for `INTENT ONLY VALIDITY`
    function intentOnlyValidityKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.INTENT_ONLY_VALIDITY_VKEY);
    }

    /// @notice Get the verification key for `INTENT AND BALANCE FIRST FILL VALIDITY`
    /// @return The verification key for `INTENT AND BALANCE FIRST FILL VALIDITY`
    function intentAndBalanceFirstFillValidityKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.INTENT_AND_BALANCE_FIRST_FILL_VALIDITY_VKEY);
    }

    /// @notice Get the verification key for `INTENT AND BALANCE VALIDITY`
    /// @return The verification key for `INTENT AND BALANCE VALIDITY`
    function intentAndBalanceValidityKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.INTENT_AND_BALANCE_VALIDITY_VKEY);
    }

    /// @notice Get the verification key for `INTENT ONLY PUBLIC SETTLEMENT`
    /// @return The verification key for `INTENT ONLY PUBLIC SETTLEMENT`
    function intentOnlyPublicSettlementKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.INTENT_ONLY_PUBLIC_SETTLEMENT_VKEY);
    }

    /// @notice Get the verification key for `INTENT AND BALANCE PUBLIC SETTLEMENT`
    /// @return The verification key for `INTENT AND BALANCE PUBLIC SETTLEMENT`
    function intentAndBalancePublicSettlementKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.INTENT_AND_BALANCE_PUBLIC_SETTLEMENT_VKEY);
    }

    /// @notice Get the verification key for `INTENT AND BALANCE PRIVATE SETTLEMENT`
    /// @return The verification key for `INTENT AND BALANCE PRIVATE SETTLEMENT`
    function intentAndBalancePrivateSettlementKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.INTENT_AND_BALANCE_PRIVATE_SETTLEMENT_VKEY);
    }

    /// @notice Get the verification key for `OUTPUT BALANCE VALIDITY`
    /// @return The verification key for `OUTPUT BALANCE VALIDITY`
    function outputBalanceValidityKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.OUTPUT_BALANCE_VALIDITY_VKEY);
    }

    /// @notice Get the verification key for `NEW OUTPUT BALANCE VALIDITY`
    /// @return The verification key for `NEW OUTPUT BALANCE VALIDITY`
    function newOutputBalanceValidityKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.NEW_OUTPUT_BALANCE_VALIDITY_VKEY);
    }

    /// @notice Deserialize a verification key
    /// @param vkeyBytes The bytes of the verification key
    /// @return vk The verification key
    function __deserializeKey(bytes memory vkeyBytes) internal pure returns (VerificationKey memory vk) {
        return abi.decode(vkeyBytes, (VerificationKey));
    }
}

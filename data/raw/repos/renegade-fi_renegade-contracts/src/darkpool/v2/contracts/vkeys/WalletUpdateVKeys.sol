// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { VerificationKey } from "renegade-lib/verifier/Types.sol";
import { VerificationKeys } from "darkpoolv2-lib/VerificationKeys.sol";

/// @title WalletUpdateVKeys
/// @author Renegade Eng
/// @notice Verification keys for wallet update operations
contract WalletUpdateVKeys {
    /// @notice Get the verification key for `VALID BALANCE CREATE`
    /// @return The verification key for `VALID BALANCE CREATE`
    function balanceCreateKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.VALID_BALANCE_CREATE_VKEY);
    }

    /// @notice Get the verification key for `VALID DEPOSIT`
    /// @return The verification key for `VALID DEPOSIT`
    function depositKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.VALID_DEPOSIT_VKEY);
    }

    /// @notice Get the verification key for `VALID WITHDRAWAL`
    /// @return The verification key for `VALID WITHDRAWAL`
    function withdrawalKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.VALID_WITHDRAWAL_VKEY);
    }

    /// @notice Get the verification key for `VALID ORDER CANCELLATION`
    /// @return The verification key for `VALID ORDER CANCELLATION`
    function orderCancellationKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.VALID_ORDER_CANCELLATION_VKEY);
    }

    /// @notice Get the verification key for `VALID NOTE REDEMPTION`
    /// @return The verification key for `VALID NOTE REDEMPTION`
    function noteRedemptionKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.VALID_NOTE_REDEMPTION_VKEY);
    }

    /// @notice Get the verification key for `VALID PRIVATE PROTOCOL FEE PAYMENT`
    /// @return The verification key for `VALID PRIVATE PROTOCOL FEE PAYMENT`
    function privateProtocolFeePaymentKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.VALID_PRIVATE_PROTOCOL_FEE_PAYMENT_VKEY);
    }

    /// @notice Get the verification key for `VALID PRIVATE RELAYER FEE PAYMENT`
    /// @return The verification key for `VALID PRIVATE RELAYER FEE PAYMENT`
    function privateRelayerFeePaymentKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.VALID_PRIVATE_RELAYER_FEE_PAYMENT_VKEY);
    }

    /// @notice Get the verification key for `VALID PUBLIC PROTOCOL FEE PAYMENT`
    /// @return The verification key for `VALID PUBLIC PROTOCOL FEE PAYMENT`
    function publicProtocolFeePaymentKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.VALID_PUBLIC_PROTOCOL_FEE_PAYMENT_VKEY);
    }

    /// @notice Get the verification key for `VALID PUBLIC RELAYER FEE PAYMENT`
    /// @return The verification key for `VALID PUBLIC RELAYER FEE PAYMENT`
    function publicRelayerFeePaymentKeys() external pure returns (VerificationKey memory) {
        return __deserializeKey(VerificationKeys.VALID_PUBLIC_RELAYER_FEE_PAYMENT_VKEY);
    }

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

    /// @notice Deserialize a verification key
    /// @param vkeyBytes The bytes of the verification key
    /// @return vk The verification key
    function __deserializeKey(bytes memory vkeyBytes) internal pure returns (VerificationKey memory vk) {
        return abi.decode(vkeyBytes, (VerificationKey));
    }
}

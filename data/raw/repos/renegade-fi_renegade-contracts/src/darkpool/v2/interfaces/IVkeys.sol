// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { VerificationKey, ProofLinkingVK } from "renegade-lib/verifier/Types.sol";

/// @title IVkeys
/// @author Renegade Eng
/// @notice Interface for the verification keys in the darkpool v2
interface IVkeys {
    // ----------------------
    // | State Update VKeys |
    // ----------------------

    /// @notice Get the verification key for `VALID BALANCE CREATE`
    /// @return The verification key for `VALID BALANCE CREATE`
    function balanceCreateKeys() external view returns (VerificationKey memory);
    /// @notice Get the verification key for `VALID DEPOSIT`
    /// @return The verification key for `VALID DEPOSIT`
    function depositKeys() external view returns (VerificationKey memory);
    /// @notice Get the verification key for `VALID WITHDRAWAL`
    /// @return The verification key for `VALID WITHDRAWAL`
    function withdrawalKeys() external view returns (VerificationKey memory);
    /// @notice Get the verification key for `VALID ORDER CANCELLATION`
    /// @return The verification key for `VALID ORDER CANCELLATION`
    function orderCancellationKeys() external view returns (VerificationKey memory);

    // ---------------------
    // | Fee Payment VKeys |
    // ---------------------

    /// @notice Get the verification key for `VALID NOTE REDEMPTION`
    /// @return The verification key for `VALID NOTE REDEMPTION`
    function noteRedemptionKeys() external view returns (VerificationKey memory);
    /// @notice Get the verification key for `VALID PRIVATE PROTOCOL FEE PAYMENT`
    /// @return The verification key for `VALID PRIVATE PROTOCOL FEE PAYMENT`
    function privateProtocolFeePaymentKeys() external view returns (VerificationKey memory);
    /// @notice Get the verification key for `VALID PRIVATE RELAYER FEE PAYMENT`
    /// @return The verification key for `VALID PRIVATE RELAYER FEE PAYMENT`
    function privateRelayerFeePaymentKeys() external view returns (VerificationKey memory);
    /// @notice Get the verification key for `VALID PUBLIC PROTOCOL FEE PAYMENT`
    /// @return The verification key for `VALID PUBLIC PROTOCOL FEE PAYMENT`
    function publicProtocolFeePaymentKeys() external view returns (VerificationKey memory);
    /// @notice Get the verification key for `VALID PUBLIC RELAYER FEE PAYMENT`
    /// @return The verification key for `VALID PUBLIC RELAYER FEE PAYMENT`
    function publicRelayerFeePaymentKeys() external view returns (VerificationKey memory);

    // ------------------------
    // | Validity Proof VKeys |
    // ------------------------

    /// @notice Get the verification key for `INTENT ONLY FIRST FILL VALIDITY`
    /// @return The verification key for `INTENT ONLY FIRST FILL VALIDITY`
    function intentOnlyFirstFillValidityKeys() external view returns (VerificationKey memory);
    /// @notice Get the verification key for `INTENT ONLY VALIDITY`
    /// @return The verification key for `INTENT ONLY VALIDITY`
    function intentOnlyValidityKeys() external view returns (VerificationKey memory);
    /// @notice Get the verification key for `INTENT AND BALANCE FIRST FILL VALIDITY`
    /// @return The verification key for `INTENT AND BALANCE FIRST FILL VALIDITY`
    function intentAndBalanceFirstFillValidityKeys() external view returns (VerificationKey memory);
    /// @notice Get the verification key for `INTENT AND BALANCE VALIDITY`
    /// @return The verification key for `INTENT AND BALANCE VALIDITY`
    function intentAndBalanceValidityKeys() external view returns (VerificationKey memory);
    /// @notice Get the verification key for `OUTPUT BALANCE VALIDITY`
    /// @return The verification key for `OUTPUT BALANCE VALIDITY`
    function outputBalanceValidityKeys() external view returns (VerificationKey memory);
    /// @notice Get the verification key for `NEW OUTPUT BALANCE VALIDITY`
    /// @return The verification key for `NEW OUTPUT BALANCE VALIDITY`
    function newOutputBalanceValidityKeys() external view returns (VerificationKey memory);

    // --------------------
    // | Settlement VKeys |
    // --------------------

    /// @notice Get the verification key for `INTENT ONLY PUBLIC SETTLEMENT`
    /// @return The verification key for `INTENT ONLY PUBLIC SETTLEMENT`
    function intentOnlyPublicSettlementKeys() external view returns (VerificationKey memory);
    /// @notice Get the verification key for `INTENT AND BALANCE PUBLIC SETTLEMENT`
    /// @return The verification key for `INTENT AND BALANCE PUBLIC SETTLEMENT`
    function intentAndBalancePublicSettlementKeys() external view returns (VerificationKey memory);
    /// @notice Get the verification key for `INTENT AND BALANCE PRIVATE SETTLEMENT`
    /// @return The verification key for `INTENT AND BALANCE PRIVATE SETTLEMENT`
    function intentAndBalancePrivateSettlementKeys() external view returns (VerificationKey memory);

    // -----------------------
    // | Proof Linking VKeys |
    // -----------------------

    /// @notice Get the verification key for `INTENT ONLY SETTLEMENT`
    /// @return The verification key for `INTENT ONLY SETTLEMENT`
    function intentOnlySettlementLinkingKey() external view returns (ProofLinkingVK memory);
    /// @notice Get the verification key for `INTENT AND BALANCE SETTLEMENT 0`
    /// @return The verification key for `INTENT AND BALANCE SETTLEMENT 0`
    function intentAndBalanceSettlement0LinkingKey() external view returns (ProofLinkingVK memory);
    /// @notice Get the verification key for `INTENT AND BALANCE SETTLEMENT 1`
    /// @return The verification key for `INTENT AND BALANCE SETTLEMENT 1`
    function intentAndBalanceSettlement1LinkingKey() external view returns (ProofLinkingVK memory);
    /// @notice Get the verification key for `OUTPUT BALANCE SETTLEMENT 0`
    /// @return The verification key for `OUTPUT BALANCE SETTLEMENT 0`
    function outputBalanceSettlement0LinkingKey() external view returns (ProofLinkingVK memory);
    /// @notice Get the verification key for `OUTPUT BALANCE SETTLEMENT 1`
    /// @return The verification key for `OUTPUT BALANCE SETTLEMENT 1`
    function outputBalanceSettlement1LinkingKey() external view returns (ProofLinkingVK memory);
}

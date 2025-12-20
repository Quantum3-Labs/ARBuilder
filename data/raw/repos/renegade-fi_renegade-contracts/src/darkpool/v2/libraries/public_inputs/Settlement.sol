// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { SettlementObligation } from "darkpoolv2-types/Obligation.sol";
import { FixedPoint } from "renegade-lib/FixedPoint.sol";
import { PostMatchBalanceShare } from "darkpoolv2-types/Balance.sol";
import { BoundedMatchResult } from "darkpoolv2-types/BoundedMatchResult.sol";

// --- Settlement Statements --- //
// Settlement proofs verify that:
// 1. A settlement obligation is well capitalized by the balance
// 2. A settlement obligation doesn't violate the intent's constraints
// 3. The shares of the balance and intent are updated correctly
// These proofs are proof-linked into the validity proofs so that they may be
// constrained to share witness elements.

/// @notice A statement for a proof of single-intent only match settlement
/// @dev We only emit the updated public shares for updated fields for efficiency
struct IntentOnlyPublicSettlementStatement {
    /// @dev The settlement obligation
    SettlementObligation obligation;
    /// @dev The relayer fee charged for the match
    FixedPoint relayerFee;
    /// @dev The recipient of the relayer fee
    address relayerFeeRecipient;
}

/// @notice A statement for a proof of single-intent bounded settlement
/// @dev The settlement proof validates that the intent can capitalize the bounded match result.
/// The contract verifies that the calldata bounded match result matches this statement's bounded match result.
struct IntentOnlyBoundedSettlementStatement {
    /// @dev The bounded match result that the intent must be able to capitalize
    BoundedMatchResult boundedMatchResult;
    /// @dev The relayer fee rate charged to the external party
    FixedPoint externalRelayerFeeRate;
    /// @dev The relayer fee rate charged to the internal party
    FixedPoint internalRelayerFeeRate;
    /// @dev The address at which the relayer receives their fee
    address relayerFeeAddress;
}

/// @notice A statement for a proof of intent and balance public settlement
/// @dev The statement type for `INTENT AND BALANCE PUBLIC SETTLEMENT`
/// @dev We leak the public shares so that the contracts can update them directly on-chain
struct IntentAndBalancePublicSettlementStatement {
    /// @dev The settlement obligation for the party
    /// @dev Note that the contract is responsible for validating the constraints
    /// which require only the obligation. For example, bitlengths on the
    /// obligation's in and out amounts
    SettlementObligation settlementObligation;
    /// @dev The leaked pre-update amount public share of the intent
    /// @dev Because this circuit represents a public settlement, we leak the public
    /// share and allow the contracts to update it on-chain.
    BN254.ScalarField amountPublicShare;
    /// @dev The updated public shares of the post-match balance fields for the input
    /// balance.
    /// @dev This value is also leaked from the witness so that the contracts can
    /// update it directly on-chain.
    PostMatchBalanceShare inBalancePublicShares;
    /// @dev The updated public shares of the post-match balance fields for the
    /// output balance
    /// @dev This value is also leaked from the witness so that the contracts can
    /// update it directly on-chain.
    PostMatchBalanceShare outBalancePublicShares;
    /// @dev The relayer fee which is charged for the settlement
    /// @dev We place this field in the statement so that it is included in the
    /// Fiat-Shamir transcript and therefore is not malleable transaction
    /// calldata. This allows the relayer to set the fee and be sure it cannot
    /// be modified by mempool observers.
    FixedPoint relayerFee;
    /// @dev The recipient of the relayer fee
    address relayerFeeRecipient;
}

/// @notice A statement for a proof of intent and balance bounded settlement
/// @dev The statement type for `INTENT AND BALANCE BOUNDED SETTLEMENT`
/// @dev Similar to public settlement but with bounded match result instead of exact obligation
struct IntentAndBalanceBoundedSettlementStatement {
    /// @dev The bounded match result that the intent must be able to capitalize
    BoundedMatchResult boundedMatchResult;
    /// @dev The leaked pre-update amount public share of the intent
    /// @dev Because this circuit represents a public settlement, we leak the public
    /// share and allow the contracts to update it on-chain.
    BN254.ScalarField amountPublicShare;
    /// @dev The updated public shares of the post-match balance fields for the input balance
    PostMatchBalanceShare inBalancePublicShares;
    /// @dev The updated public shares of the post-match balance fields for the output balance
    PostMatchBalanceShare outBalancePublicShares;
    /// @dev The relayer fee rate charged to the external party
    FixedPoint externalRelayerFeeRate;
    /// @dev The relayer fee rate charged to the internal party
    FixedPoint internalRelayerFeeRate;
    /// @dev The address at which the relayer receives their fee
    address relayerFeeAddress;
}

/// @notice A statement for a proof of intent and balance private settlement
/// @dev The statement type for `INTENT AND BALANCE PRIVATE SETTLEMENT`
struct IntentAndBalancePrivateSettlementStatement {
    // --- First Party --- //
    /// @dev The updated public share of the first party's intent amount
    BN254.ScalarField newAmountPublicShare0;
    /// @dev The updated public shares of the first party's input balance
    /// These correspond to the updated:
    /// - Relayer fee
    /// - Protocol fee
    /// - Amount
    PostMatchBalanceShare newInBalancePublicShares0;
    /// @dev The updated public shares of the first party's output balance
    /// These correspond to the updated:
    /// - Relayer fee
    /// - Protocol fee
    /// - Amount
    PostMatchBalanceShare newOutBalancePublicShares0;
    // --- Second Party --- //
    /// @dev The updated public share of the second party's intent amount
    BN254.ScalarField newAmountPublicShare1;
    /// @dev The updated public shares of the second party's input balance
    /// These correspond to the updated:
    /// - Relayer fee
    /// - Protocol fee
    /// - Amount
    PostMatchBalanceShare newInBalancePublicShares1;
    /// @dev The updated public shares of the second party's output balance
    /// These correspond to the updated:
    /// - Relayer fee
    /// - Protocol fee
    /// - Amount
    PostMatchBalanceShare newOutBalancePublicShares1;
    // --- Fees --- //
    /// @dev The relayer fee applied to the first party's match
    FixedPoint relayerFee0;
    /// @dev The relayer fee applied to the second party's match
    FixedPoint relayerFee1;
    /// @dev The protocol fee applied to the match
    /// @dev This is the same for both parties
    FixedPoint protocolFee;
}

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { SignatureWithNonce } from "darkpoolv2-types/settlement/SignatureWithNonce.sol";
import { ElGamalCiphertext } from "renegade-lib/Ciphertext.sol";
import {
    ValidDepositStatement,
    ValidBalanceCreateStatement,
    ValidWithdrawalStatement
} from "darkpoolv2-lib/public_inputs/Transfers.sol";
import {
    ValidPublicProtocolFeePaymentStatement,
    ValidPublicRelayerFeePaymentStatement,
    ValidPrivateProtocolFeePaymentStatement,
    ValidPrivateRelayerFeePaymentStatement,
    ValidNoteRedemptionStatement
} from "darkpoolv2-lib/public_inputs/Fees.sol";
import { ValidOrderCancellationStatement } from "darkpoolv2-lib/public_inputs/OrderCancellation.sol";

import { PlonkProof } from "renegade-lib/verifier/Types.sol";

/// This file stores bundles which package a proof together with its statement (public inputs) and any
/// proof-linking arguments necessary for connecting proofs.

// --- Order Cancellation --- //

struct OrderCancellationProofBundle {
    /// @dev The statement of the order cancellation validity
    ValidOrderCancellationStatement statement;
    /// @dev The proof of the order cancellation validity
    PlonkProof proof;
}

// --- Transfers --- //

/// @notice A validation bundle for creating a new balance with a deposit
struct NewBalanceDepositProofBundle {
    /// @dev The Merkle depth of the balance
    uint256 merkleDepth;
    /// @dev The statement of the new balance deposit validity
    ValidBalanceCreateStatement statement;
    /// @dev The proof of the new balance deposit validity
    PlonkProof proof;
}

/// @notice A validation bundle for depositing into an existing balance
struct DepositProofBundle {
    /// @dev The Merkle depth of the balance
    uint256 merkleDepth;
    /// @dev The statement of the deposit validity
    ValidDepositStatement statement;
    /// @dev The proof of the deposit validity
    PlonkProof proof;
}

/// @notice A validation bundle for withdrawing from a balance
struct WithdrawalProofBundle {
    /// @dev The Merkle depth of the balance
    uint256 merkleDepth;
    /// @dev The statement of the withdrawal validity
    ValidWithdrawalStatement statement;
    /// @dev The proof of the withdrawal validity
    PlonkProof proof;
}

// --- Fees --- //

/// @notice A validation bundle for paying a balance's protocol fee publicly
struct PublicProtocolFeePaymentProofBundle {
    /// @dev The Merkle depth of the balance
    uint256 merkleDepth;
    /// @dev The statement of the public protocol fee payment validity
    ValidPublicProtocolFeePaymentStatement statement;
    /// @dev The proof of the public protocol fee payment validity
    PlonkProof proof;
}

/// @notice A validation bundle for paying a balance's relayer fee publicly
struct PublicRelayerFeePaymentProofBundle {
    /// @dev The Merkle depth of the balance
    uint256 merkleDepth;
    /// @dev The statement of the public relayer fee payment validity
    ValidPublicRelayerFeePaymentStatement statement;
    /// @dev The proof of the public relayer fee payment validity
    PlonkProof proof;
}

/// @notice A validation bundle for paying a balance's protocol fee privately
struct PrivateProtocolFeePaymentProofBundle {
    /// @dev The Merkle depth of the balance
    uint256 merkleDepth;
    /// @dev The statement of the private protocol fee payment validity
    ValidPrivateProtocolFeePaymentStatement statement;
    /// @dev The proof of the private protocol fee payment validity
    PlonkProof proof;
}

/// @notice A validation bundle for paying a balance's relayer fee privately
struct PrivateRelayerFeePaymentProofBundle {
    /// @dev The Merkle depth of the balance
    uint256 merkleDepth;
    /// @dev The note ciphertext
    ElGamalCiphertext noteCiphertext;
    /// @dev A signature by the relayer authorizing the encryption of the note
    SignatureWithNonce relayerCiphertextSignature;
    /// @dev The statement of the private relayer fee payment validity
    ValidPrivateRelayerFeePaymentStatement statement;
    /// @dev The proof of the private relayer fee payment validity
    PlonkProof proof;
}

/// @notice A validation bundle for redeeming a note
struct NoteRedemptionProofBundle {
    /// @dev The statement of the note redemption validity
    ValidNoteRedemptionStatement statement;
    /// @dev The proof of the note redemption validity
    PlonkProof proof;
}

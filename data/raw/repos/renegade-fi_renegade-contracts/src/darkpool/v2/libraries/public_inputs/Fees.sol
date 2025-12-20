// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { Note } from "darkpoolv2-types/Note.sol";
import { ElGamalCiphertext, EncryptionKey } from "renegade-lib/Ciphertext.sol";

// --- Fee Payment Statements --- //

/// @notice A statement proving validity of a public payment of a balance's protocol fee
/// @dev Public here implies that the fee is paid directly to the protocol fee collection address rather than committed
/// through a note
struct ValidPublicProtocolFeePaymentStatement {
    /// @dev The Merkle root to which the old balance opens
    BN254.ScalarField merkleRoot;
    /// @dev The nullifier of the previous balance
    BN254.ScalarField oldBalanceNullifier;
    /// @dev The commitment to the new balance
    BN254.ScalarField newBalanceCommitment;
    /// @dev The new recovery identifier of the balance
    /// @dev This value is emitted as an event for chain indexers to track the balance's update
    BN254.ScalarField recoveryId;
    /// @dev The new encrypted protocol fee balance (public share) of the balance
    BN254.ScalarField newProtocolFeeBalanceShare;
    /// @dev The note which is being created
    Note note;
}

/// @notice A statement proving validity of a public payment of a balance's relayer fee
/// @dev Public here implies that the fee is paid directly to the relayer fee collection address rather than committed
/// through a note
struct ValidPublicRelayerFeePaymentStatement {
    /// @dev The Merkle root to which the old balance opens
    BN254.ScalarField merkleRoot;
    /// @dev The nullifier of the previous balance
    BN254.ScalarField oldBalanceNullifier;
    /// @dev The commitment to the new balance
    BN254.ScalarField newBalanceCommitment;
    /// @dev The new recovery identifier of the balance
    /// @dev This value is emitted as an event for chain indexers to track the balance's update
    BN254.ScalarField recoveryId;
    /// @dev The new encrypted relayer fee balance (public share) of the balance
    BN254.ScalarField newRelayerFeeBalanceShare;
    /// @dev The note which is being created
    Note note;
}

/// @notice A statement proving validity of a private payment of a balance's protocol fee
/// @dev Private here implies that the fee is committed through a note encrypted under the protocol encryption key
struct ValidPrivateProtocolFeePaymentStatement {
    /// @dev The Merkle root to which the old balance opens
    BN254.ScalarField merkleRoot;
    /// @dev The nullifier of the previous balance
    BN254.ScalarField oldBalanceNullifier;
    /// @dev The commitment to the new balance
    BN254.ScalarField newBalanceCommitment;
    /// @dev The new recovery identifier of the balance
    /// @dev This value is emitted as an event for chain indexers to track the balance's update
    BN254.ScalarField recoveryId;
    /// @dev The new encrypted protocol fee balance (public share) of the balance
    BN254.ScalarField newProtocolFeeBalanceShare;
    /// @dev The protocol fee receiver
    address protocolFeeReceiver;
    /// @dev The commitment to the note
    BN254.ScalarField noteCommitment;
    /// @dev The note ciphertext
    /// @dev This will be verified to be encrypted under the protocol key
    ElGamalCiphertext noteCiphertext;
    /// @dev The key under which the note is claimed to be encrypted
    EncryptionKey protocolEncryptionKey;
}

/// @notice A statement proving validity of a private payment of a balance's relayer fee
/// @dev Private here implies that the fee is committed through a note
/// @dev The relayer fee receiver is constrained to be the same as the address on the balance itself.
/// @dev We leak this value in-circuit so that the contracts may check that the fee receiver has signed the note
/// encryption.
struct ValidPrivateRelayerFeePaymentStatement {
    /// @dev The Merkle root to which the old balance opens
    BN254.ScalarField merkleRoot;
    /// @dev The nullifier of the previous balance
    BN254.ScalarField oldBalanceNullifier;
    /// @dev The commitment to the new balance
    BN254.ScalarField newBalanceCommitment;
    /// @dev The new recovery identifier of the balance
    /// @dev This value is emitted as an event for chain indexers to track the balance's update
    BN254.ScalarField recoveryId;
    /// @dev The new encrypted relayer fee balance (public share) of the balance
    BN254.ScalarField newRelayerFeeBalanceShare;
    /// @dev The relayer fee receiver
    /// @dev This is constrained to be the same as the address on the balance itself
    address relayerFeeReceiver;
    /// @dev The commitment to the note
    BN254.ScalarField noteCommitment;
}

/// @notice A statement proving validity of a note redemption
struct ValidNoteRedemptionStatement {
    /// @dev The note being redeemed
    Note note;
    /// @dev The Merkle root to which the note opens
    BN254.ScalarField noteRoot;
    /// @dev The nullifier of the note
    BN254.ScalarField noteNullifier;
}

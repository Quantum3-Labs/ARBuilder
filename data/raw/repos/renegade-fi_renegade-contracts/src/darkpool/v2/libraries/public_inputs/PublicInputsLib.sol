// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { BN254Helpers } from "renegade-lib/verifier/BN254Helpers.sol";
import { VerificationKey } from "renegade-lib/verifier/Types.sol";
import { ValidDepositStatement, ValidBalanceCreateStatement, ValidWithdrawalStatement } from "./Transfers.sol";
import {
    ValidPublicProtocolFeePaymentStatement,
    ValidPublicRelayerFeePaymentStatement,
    ValidPrivateProtocolFeePaymentStatement,
    ValidPrivateRelayerFeePaymentStatement,
    ValidNoteRedemptionStatement
} from "./Fees.sol";
import { ValidOrderCancellationStatement } from "./OrderCancellation.sol";
import {
    IntentOnlyValidityStatementFirstFill,
    IntentOnlyValidityStatement,
    IntentAndBalanceValidityStatementFirstFill,
    IntentAndBalanceValidityStatement,
    NewOutputBalanceValidityStatement,
    OutputBalanceValidityStatement
} from "./ValidityProofs.sol";
import {
    IntentOnlyBoundedSettlementStatement,
    IntentOnlyPublicSettlementStatement,
    IntentAndBalancePublicSettlementStatement,
    IntentAndBalanceBoundedSettlementStatement,
    IntentAndBalancePrivateSettlementStatement
} from "./Settlement.sol";

// -------------------------
// | Public Inputs Library |
// -------------------------

/// @title Public Inputs Library
/// @author Renegade Eng
/// @notice Library for operating on proof public inputs
library PublicInputsLib {
    /// @notice The number of modified balance shares in a match
    uint256 public constant N_MODIFIED_BALANCE_SHARES = 3;
    /// @notice The number of modified intent shares in a match
    uint256 public constant N_MODIFIED_INTENT_SHARES = 1;
    /// @notice The size of the note ciphertext array
    uint256 public constant NOTE_CIPHERTEXT_SIZE = 3;

    /// @notice Serialize the public inputs for a proof of existing balance deposit validity
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(ValidDepositStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 8;
        publicInputs = new BN254.ScalarField[](nPublicInputs);
        publicInputs[0] = BN254.ScalarField.wrap(uint256(uint160(statement.deposit.from)));
        publicInputs[1] = BN254.ScalarField.wrap(uint256(uint160(statement.deposit.token)));
        publicInputs[2] = BN254.ScalarField.wrap(statement.deposit.amount);
        publicInputs[3] = statement.merkleRoot;
        publicInputs[4] = statement.oldBalanceNullifier;
        publicInputs[5] = statement.newBalanceCommitment;
        publicInputs[6] = statement.recoveryId;
        publicInputs[7] = statement.newAmountShare;
    }

    /// @notice Serialize the public inputs for a proof of new balance deposit validity
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(ValidBalanceCreateStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 12;
        publicInputs = new BN254.ScalarField[](nPublicInputs);
        publicInputs[0] = BN254.ScalarField.wrap(uint256(uint160(statement.deposit.from)));
        publicInputs[1] = BN254.ScalarField.wrap(uint256(uint160(statement.deposit.token)));
        publicInputs[2] = BN254.ScalarField.wrap(statement.deposit.amount);
        publicInputs[3] = statement.newBalanceCommitment;
        publicInputs[4] = statement.recoveryId;
        publicInputs[5] = statement.newBalancePublicShares[0];
        publicInputs[6] = statement.newBalancePublicShares[1];
        publicInputs[7] = statement.newBalancePublicShares[2];
        publicInputs[8] = statement.newBalancePublicShares[3];
        publicInputs[9] = statement.newBalancePublicShares[4];
        publicInputs[10] = statement.newBalancePublicShares[5];
        publicInputs[11] = statement.newBalancePublicShares[6];
    }

    /// @notice Serialize the public inputs for a proof of withdrawal validity
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(ValidWithdrawalStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 8;
        publicInputs = new BN254.ScalarField[](nPublicInputs);
        publicInputs[0] = BN254.ScalarField.wrap(uint256(uint160(statement.withdrawal.to)));
        publicInputs[1] = BN254.ScalarField.wrap(uint256(uint160(statement.withdrawal.token)));
        publicInputs[2] = BN254.ScalarField.wrap(statement.withdrawal.amount);
        publicInputs[3] = statement.merkleRoot;
        publicInputs[4] = statement.oldBalanceNullifier;
        publicInputs[5] = statement.newBalanceCommitment;
        publicInputs[6] = statement.recoveryId;
        publicInputs[7] = statement.newAmountShare;
    }

    /// @notice Serialize the public inputs for a proof of order cancellation validity
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(ValidOrderCancellationStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 3;
        publicInputs = new BN254.ScalarField[](nPublicInputs);
        publicInputs[0] = statement.merkleRoot;
        publicInputs[1] = statement.oldIntentNullifier;
        publicInputs[2] = BN254.ScalarField.wrap(uint256(uint160(statement.owner)));
    }

    /// @notice Serialize the public inputs for a proof of public protocol fee payment validity
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(ValidPublicProtocolFeePaymentStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 9;
        publicInputs = new BN254.ScalarField[](nPublicInputs);
        publicInputs[0] = statement.merkleRoot;
        publicInputs[1] = statement.oldBalanceNullifier;
        publicInputs[2] = statement.newBalanceCommitment;
        publicInputs[3] = statement.recoveryId;
        publicInputs[4] = statement.newProtocolFeeBalanceShare;
        // Serialize the note fields
        publicInputs[5] = BN254.ScalarField.wrap(uint256(uint160(statement.note.mint)));
        publicInputs[6] = BN254.ScalarField.wrap(statement.note.amount);
        publicInputs[7] = BN254.ScalarField.wrap(uint256(uint160(statement.note.receiver)));
        publicInputs[8] = statement.note.blinder;
    }

    /// @notice Serialize the public inputs for a proof of public relayer fee payment validity
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(ValidPublicRelayerFeePaymentStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 9;
        publicInputs = new BN254.ScalarField[](nPublicInputs);
        publicInputs[0] = statement.merkleRoot;
        publicInputs[1] = statement.oldBalanceNullifier;
        publicInputs[2] = statement.newBalanceCommitment;
        publicInputs[3] = statement.recoveryId;
        publicInputs[4] = statement.newRelayerFeeBalanceShare;
        // Serialize the note fields
        publicInputs[5] = BN254.ScalarField.wrap(uint256(uint160(statement.note.mint)));
        publicInputs[6] = BN254.ScalarField.wrap(statement.note.amount);
        publicInputs[7] = BN254.ScalarField.wrap(uint256(uint160(statement.note.receiver)));
        publicInputs[8] = statement.note.blinder;
    }

    /// @notice Serialize the public inputs for a proof of private protocol fee payment validity
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(ValidPrivateProtocolFeePaymentStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 14;
        publicInputs = new BN254.ScalarField[](nPublicInputs);
        publicInputs[0] = statement.merkleRoot;
        publicInputs[1] = statement.oldBalanceNullifier;
        publicInputs[2] = statement.newBalanceCommitment;
        publicInputs[3] = statement.recoveryId;
        publicInputs[4] = statement.newProtocolFeeBalanceShare;
        publicInputs[5] = BN254.ScalarField.wrap(uint256(uint160(statement.protocolFeeReceiver)));
        publicInputs[6] = statement.noteCommitment;
        // Serialize the note ciphertext: ephemeral key (x, y) + ciphertext array (3 elements)
        publicInputs[7] = statement.noteCiphertext.ephemeralKey.x;
        publicInputs[8] = statement.noteCiphertext.ephemeralKey.y;
        publicInputs[9] = statement.noteCiphertext.ciphertext[0];
        publicInputs[10] = statement.noteCiphertext.ciphertext[1];
        publicInputs[11] = statement.noteCiphertext.ciphertext[2];
        // Serialize the protocol encryption key
        publicInputs[12] = statement.protocolEncryptionKey.point.x;
        publicInputs[13] = statement.protocolEncryptionKey.point.y;
    }

    /// @notice Serialize the public inputs for a proof of private relayer fee payment validity
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(ValidPrivateRelayerFeePaymentStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 7;
        publicInputs = new BN254.ScalarField[](nPublicInputs);
        publicInputs[0] = statement.merkleRoot;
        publicInputs[1] = statement.oldBalanceNullifier;
        publicInputs[2] = statement.newBalanceCommitment;
        publicInputs[3] = statement.recoveryId;
        publicInputs[4] = statement.newRelayerFeeBalanceShare;
        publicInputs[5] = BN254.ScalarField.wrap(uint256(uint160(statement.relayerFeeReceiver)));
        publicInputs[6] = statement.noteCommitment;
    }

    /// @notice Serialize the public inputs for a proof of note redemption validity
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(ValidNoteRedemptionStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 6;
        publicInputs = new BN254.ScalarField[](nPublicInputs);
        // Serialize the note fields
        publicInputs[0] = BN254.ScalarField.wrap(uint256(uint160(statement.note.mint)));
        publicInputs[1] = BN254.ScalarField.wrap(statement.note.amount);
        publicInputs[2] = BN254.ScalarField.wrap(uint256(uint160(statement.note.receiver)));
        publicInputs[3] = statement.note.blinder;
        // Serialize the note root and nullifier
        publicInputs[4] = statement.noteRoot;
        publicInputs[5] = statement.noteNullifier;
    }

    /// @notice Serialize the public inputs for a proof of intent only validity (first fill)
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(IntentOnlyValidityStatementFirstFill memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 8;
        publicInputs = new BN254.ScalarField[](nPublicInputs);
        publicInputs[0] = BN254.ScalarField.wrap(uint256(uint160(statement.intentOwner)));
        publicInputs[1] = statement.intentPrivateCommitment;
        publicInputs[2] = statement.recoveryId;
        publicInputs[3] = statement.intentPublicShare.inToken;
        publicInputs[4] = statement.intentPublicShare.outToken;
        publicInputs[5] = statement.intentPublicShare.owner;
        publicInputs[6] = statement.intentPublicShare.minPrice;
        publicInputs[7] = statement.intentPublicShare.amountIn;
    }

    /// @notice Serialize the public inputs for a proof
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(IntentOnlyValidityStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 7;
        publicInputs = new BN254.ScalarField[](nPublicInputs);
        publicInputs[0] = BN254.ScalarField.wrap(uint256(uint160(statement.intentOwner)));
        publicInputs[1] = statement.merkleRoot;
        publicInputs[2] = statement.oldIntentNullifier;
        publicInputs[3] = statement.newAmountShare;
        publicInputs[4] = statement.newIntentPartialCommitment.privateCommitment;
        publicInputs[5] = statement.newIntentPartialCommitment.partialPublicCommitment;
        publicInputs[6] = statement.recoveryId;
    }

    /// @notice Serialize the public inputs for a proof of intent and balance validity
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(IntentAndBalanceValidityStatementFirstFill memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 14;
        publicInputs = new BN254.ScalarField[](nPublicInputs);
        publicInputs[0] = statement.merkleRoot;
        publicInputs[1] = statement.intentAndAuthorizingAddressCommitment;
        publicInputs[2] = statement.intentPublicShare.inToken;
        publicInputs[3] = statement.intentPublicShare.outToken;
        publicInputs[4] = statement.intentPublicShare.owner;
        publicInputs[5] = statement.intentPublicShare.minPrice;
        publicInputs[6] = statement.intentPrivateShareCommitment;
        publicInputs[7] = statement.intentRecoveryId;
        publicInputs[8] = statement.balancePartialCommitment.privateCommitment;
        publicInputs[9] = statement.balancePartialCommitment.partialPublicCommitment;
        publicInputs[10] = statement.newOneTimeAddressPublicShare;
        publicInputs[11] = statement.oldBalanceNullifier;
        publicInputs[12] = statement.balanceRecoveryId;
        publicInputs[13] = BN254.ScalarField.wrap(uint256(uint160(statement.oneTimeAuthorizingAddress)));
    }

    /// @notice Serialize the public inputs for a proof of single-intent match settlement
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(IntentOnlyPublicSettlementStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 6;
        publicInputs = new BN254.ScalarField[](nPublicInputs);

        // Add the settlement obligation
        publicInputs[0] = BN254.ScalarField.wrap(uint256(uint160(statement.obligation.inputToken)));
        publicInputs[1] = BN254.ScalarField.wrap(uint256(uint160(statement.obligation.outputToken)));
        publicInputs[2] = BN254.ScalarField.wrap(statement.obligation.amountIn);
        publicInputs[3] = BN254.ScalarField.wrap(statement.obligation.amountOut);
        publicInputs[4] = BN254.ScalarField.wrap(statement.relayerFee.repr);
        publicInputs[5] = BN254.ScalarField.wrap(uint256(uint160(statement.relayerFeeRecipient)));
    }

    /// @notice Serialize the public inputs for a proof of single-intent bounded match settlement
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    /// @dev NOTE: This is a temporary placeholder implementation until the circuits are completed.
    /// The actual circuit public inputs format may differ from this serialization.
    function statementSerialize(IntentOnlyBoundedSettlementStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 11;
        publicInputs = new BN254.ScalarField[](nPublicInputs);

        // Add the bounded match result fields
        publicInputs[0] = BN254.ScalarField.wrap(uint256(uint160(statement.boundedMatchResult.internalPartyInputToken)));
        publicInputs[1] =
            BN254.ScalarField.wrap(uint256(uint160(statement.boundedMatchResult.internalPartyOutputToken)));
        publicInputs[2] = BN254.ScalarField.wrap(statement.boundedMatchResult.price.repr);
        publicInputs[3] = BN254.ScalarField.wrap(statement.boundedMatchResult.minInternalPartyAmountIn);
        publicInputs[4] = BN254.ScalarField.wrap(statement.boundedMatchResult.maxInternalPartyAmountIn);
        publicInputs[5] = BN254.ScalarField.wrap(statement.boundedMatchResult.blockDeadline);

        // Add the fee rates
        publicInputs[6] = BN254.ScalarField.wrap(statement.externalRelayerFeeRate.repr);
        publicInputs[8] = BN254.ScalarField.wrap(statement.internalRelayerFeeRate.repr);

        // Add the relayer fee address
        publicInputs[10] = BN254.ScalarField.wrap(uint256(uint160(statement.relayerFeeAddress)));
    }

    /// @notice Serialize the public inputs for a proof of intent and balance public settlement
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(IntentAndBalancePublicSettlementStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 13;
        publicInputs = new BN254.ScalarField[](nPublicInputs);

        // Add the settlement obligation
        publicInputs[0] = BN254.ScalarField.wrap(uint256(uint160(statement.settlementObligation.inputToken)));
        publicInputs[1] = BN254.ScalarField.wrap(uint256(uint160(statement.settlementObligation.outputToken)));
        publicInputs[2] = BN254.ScalarField.wrap(statement.settlementObligation.amountIn);
        publicInputs[3] = BN254.ScalarField.wrap(statement.settlementObligation.amountOut);

        // Add the leaked pre-update amount public share of the intent
        publicInputs[4] = statement.amountPublicShare;

        // Add the input balance public shares
        publicInputs[5] = statement.inBalancePublicShares.relayerFeeBalance;
        publicInputs[6] = statement.inBalancePublicShares.protocolFeeBalance;
        publicInputs[7] = statement.inBalancePublicShares.amount;

        // Add the output balance public shares
        publicInputs[8] = statement.outBalancePublicShares.relayerFeeBalance;
        publicInputs[9] = statement.outBalancePublicShares.protocolFeeBalance;
        publicInputs[10] = statement.outBalancePublicShares.amount;

        // Add the relayer fee and recipient
        publicInputs[11] = BN254.ScalarField.wrap(statement.relayerFee.repr);
        publicInputs[12] = BN254.ScalarField.wrap(uint256(uint160(statement.relayerFeeRecipient)));
    }

    /// @notice Serialize the public inputs for a proof of intent and balance bounded settlement
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    /// @dev NOTE: This is a temporary placeholder implementation until the circuits are completed.
    /// The actual circuit public inputs format may differ from this serialization.
    function statementSerialize(IntentAndBalanceBoundedSettlementStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 16;
        publicInputs = new BN254.ScalarField[](nPublicInputs);

        // Add the bounded match result fields
        publicInputs[0] = BN254.ScalarField.wrap(uint256(uint160(statement.boundedMatchResult.internalPartyInputToken)));
        publicInputs[1] =
            BN254.ScalarField.wrap(uint256(uint160(statement.boundedMatchResult.internalPartyOutputToken)));
        publicInputs[2] = BN254.ScalarField.wrap(statement.boundedMatchResult.price.repr);
        publicInputs[3] = BN254.ScalarField.wrap(statement.boundedMatchResult.minInternalPartyAmountIn);
        publicInputs[4] = BN254.ScalarField.wrap(statement.boundedMatchResult.maxInternalPartyAmountIn);
        publicInputs[5] = BN254.ScalarField.wrap(statement.boundedMatchResult.blockDeadline);

        // Add the leaked pre-update amount public share of the intent
        publicInputs[6] = statement.amountPublicShare;

        // Add the input balance public shares
        publicInputs[7] = statement.inBalancePublicShares.relayerFeeBalance;
        publicInputs[8] = statement.inBalancePublicShares.protocolFeeBalance;
        publicInputs[9] = statement.inBalancePublicShares.amount;

        // Add the output balance public shares
        publicInputs[10] = statement.outBalancePublicShares.relayerFeeBalance;
        publicInputs[11] = statement.outBalancePublicShares.protocolFeeBalance;
        publicInputs[12] = statement.outBalancePublicShares.amount;

        // Add the fee rates
        publicInputs[13] = BN254.ScalarField.wrap(statement.externalRelayerFeeRate.repr);
        publicInputs[14] = BN254.ScalarField.wrap(statement.internalRelayerFeeRate.repr);

        // Add the relayer fee address
        publicInputs[15] = BN254.ScalarField.wrap(uint256(uint160(statement.relayerFeeAddress)));
    }

    /// @notice Serialize the public inputs for a proof of intent and balance validity
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(IntentAndBalanceValidityStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 10;
        publicInputs = new BN254.ScalarField[](nPublicInputs);
        // Intent fields
        publicInputs[0] = statement.intentMerkleRoot;
        publicInputs[1] = statement.oldIntentNullifier;
        publicInputs[2] = statement.newIntentPartialCommitment.privateCommitment;
        publicInputs[3] = statement.newIntentPartialCommitment.partialPublicCommitment;
        publicInputs[4] = statement.intentRecoveryId;
        // Balance fields
        publicInputs[5] = statement.balanceMerkleRoot;
        publicInputs[6] = statement.oldBalanceNullifier;
        publicInputs[7] = statement.balancePartialCommitment.privateCommitment;
        publicInputs[8] = statement.balancePartialCommitment.partialPublicCommitment;
        publicInputs[9] = statement.balanceRecoveryId;
    }

    /// @notice Serialize the public inputs for a proof of new output balance validity
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(NewOutputBalanceValidityStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 7;
        publicInputs = new BN254.ScalarField[](nPublicInputs);
        // Pre-match balance shares
        publicInputs[0] = statement.preMatchBalanceShares.mint;
        publicInputs[1] = statement.preMatchBalanceShares.owner;
        publicInputs[2] = statement.preMatchBalanceShares.relayerFeeRecipient;
        publicInputs[3] = statement.preMatchBalanceShares.oneTimeAuthority;
        // Partial commitment
        publicInputs[4] = statement.newBalancePartialCommitment.privateCommitment;
        publicInputs[5] = statement.newBalancePartialCommitment.partialPublicCommitment;
        // Recovery ID
        publicInputs[6] = statement.recoveryId;
    }

    /// @notice Serialize the public inputs for a proof of output balance validity
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(OutputBalanceValidityStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 5;
        publicInputs = new BN254.ScalarField[](nPublicInputs);
        publicInputs[0] = statement.merkleRoot;
        publicInputs[1] = statement.oldBalanceNullifier;
        publicInputs[2] = statement.newPartialCommitment.privateCommitment;
        publicInputs[3] = statement.newPartialCommitment.partialPublicCommitment;
        publicInputs[4] = statement.recoveryId;
    }

    /// @notice Serialize the public inputs for a proof of intent and balance private settlement
    /// @param statement The statement to serialize
    /// @return publicInputs The serialized public inputs
    function statementSerialize(IntentAndBalancePrivateSettlementStatement memory statement)
        internal
        pure
        returns (BN254.ScalarField[] memory publicInputs)
    {
        uint256 nPublicInputs = 17;
        publicInputs = new BN254.ScalarField[](nPublicInputs);

        // First party intent amount
        publicInputs[0] = statement.newAmountPublicShare0;

        // First party input balance shares
        publicInputs[1] = statement.newInBalancePublicShares0.relayerFeeBalance;
        publicInputs[2] = statement.newInBalancePublicShares0.protocolFeeBalance;
        publicInputs[3] = statement.newInBalancePublicShares0.amount;

        // First party output balance shares
        publicInputs[4] = statement.newOutBalancePublicShares0.relayerFeeBalance;
        publicInputs[5] = statement.newOutBalancePublicShares0.protocolFeeBalance;
        publicInputs[6] = statement.newOutBalancePublicShares0.amount;

        // Second party intent amount
        publicInputs[7] = statement.newAmountPublicShare1;

        // Second party input balance shares
        publicInputs[8] = statement.newInBalancePublicShares1.relayerFeeBalance;
        publicInputs[9] = statement.newInBalancePublicShares1.protocolFeeBalance;
        publicInputs[10] = statement.newInBalancePublicShares1.amount;

        // Second party output balance shares
        publicInputs[11] = statement.newOutBalancePublicShares1.relayerFeeBalance;
        publicInputs[12] = statement.newOutBalancePublicShares1.protocolFeeBalance;
        publicInputs[13] = statement.newOutBalancePublicShares1.amount;

        // Fees
        publicInputs[14] = BN254.ScalarField.wrap(statement.relayerFee0.repr);
        publicInputs[15] = BN254.ScalarField.wrap(statement.relayerFee1.repr);
        publicInputs[16] = BN254.ScalarField.wrap(statement.protocolFee.repr);
    }

    /// @notice Get a dummy verification key for testing
    /// @return A dummy verification key
    /// @dev TODO: Replace with real verification key
    function dummyVkey() internal pure returns (VerificationKey memory) {
        return VerificationKey({
            n: 0,
            l: 0,
            k: [BN254Helpers.ZERO, BN254Helpers.ZERO, BN254Helpers.ZERO, BN254Helpers.ZERO, BN254Helpers.ZERO],
            qComms: [
                BN254.P1(),
                BN254.P1(),
                BN254.P1(),
                BN254.P1(),
                BN254.P1(),
                BN254.P1(),
                BN254.P1(),
                BN254.P1(),
                BN254.P1(),
                BN254.P1(),
                BN254.P1(),
                BN254.P1(),
                BN254.P1()
            ],
            sigmaComms: [BN254.P1(), BN254.P1(), BN254.P1(), BN254.P1(), BN254.P1()],
            g: BN254.P1(),
            h: BN254.P2(),
            xH: BN254.P2()
        });
    }
}

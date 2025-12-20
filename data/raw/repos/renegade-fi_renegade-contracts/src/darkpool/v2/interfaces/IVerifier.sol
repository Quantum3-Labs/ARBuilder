// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { PlonkProof, VerificationKey, OpeningElements } from "renegade-lib/verifier/Types.sol";

import {
    DepositProofBundle,
    NewBalanceDepositProofBundle,
    OrderCancellationProofBundle,
    WithdrawalProofBundle,
    PublicProtocolFeePaymentProofBundle,
    PublicRelayerFeePaymentProofBundle,
    PrivateProtocolFeePaymentProofBundle,
    PrivateRelayerFeePaymentProofBundle,
    NoteRedemptionProofBundle
} from "darkpoolv2-types/ProofBundles.sol";

/// @title IVerifier
/// @author Renegade Eng
/// @notice Interface for verifying zero-knowledge proofs
interface IVerifier {
    /// @notice Verify a proof of `EXISTING BALANCE DEPOSIT VALIDITY`
    /// @param depositProofBundle The proof bundle for the deposit
    /// @return True if the proof is valid, false otherwise
    function verifyExistingBalanceDepositValidity(DepositProofBundle calldata depositProofBundle)
        external
        view
        returns (bool);

    /// @notice Verify a proof of `NEW BALANCE DEPOSIT VALIDITY`
    /// @param newBalanceProofBundle The proof bundle for the new balance deposit
    /// @return True if the proof is valid, false otherwise
    function verifyNewBalanceDepositValidity(NewBalanceDepositProofBundle calldata newBalanceProofBundle)
        external
        view
        returns (bool);

    /// @notice Verify a proof of `WITHDRAWAL VALIDITY`
    /// @param withdrawalProofBundle The proof bundle for the withdrawal
    /// @return True if the proof is valid, false otherwise
    function verifyWithdrawalValidity(WithdrawalProofBundle calldata withdrawalProofBundle)
        external
        view
        returns (bool);

    /// @notice Verify a proof of `VALID ORDER CANCELLATION`
    /// @param orderCancellationProofBundle The proof bundle for the order cancellation
    /// @return True if the proof is valid, false otherwise
    function verifyOrderCancellationValidity(OrderCancellationProofBundle calldata orderCancellationProofBundle)
        external
        view
        returns (bool);

    /// @notice Verify a proof of `VALID PUBLIC PROTOCOL FEE PAYMENT`
    /// @param proofBundle The proof bundle for the public protocol fee payment
    /// @return True if the proof is valid, false otherwise
    function verifyPublicProtocolFeePaymentValidity(PublicProtocolFeePaymentProofBundle calldata proofBundle)
        external
        view
        returns (bool);

    /// @notice Verify a proof of `VALID PUBLIC RELAYER FEE PAYMENT`
    /// @param proofBundle The proof bundle for the public relayer fee payment
    /// @return True if the proof is valid, false otherwise
    function verifyPublicRelayerFeePaymentValidity(PublicRelayerFeePaymentProofBundle calldata proofBundle)
        external
        view
        returns (bool);

    /// @notice Verify a proof of `VALID PRIVATE PROTOCOL FEE PAYMENT`
    /// @param proofBundle The proof bundle for the private protocol fee payment
    /// @return True if the proof is valid, false otherwise
    function verifyPrivateProtocolFeePaymentValidity(PrivateProtocolFeePaymentProofBundle calldata proofBundle)
        external
        view
        returns (bool);

    /// @notice Verify a proof of `VALID PRIVATE RELAYER FEE PAYMENT`
    /// @param proofBundle The proof bundle for the private relayer fee payment
    /// @return True if the proof is valid, false otherwise
    function verifyPrivateRelayerFeePaymentValidity(PrivateRelayerFeePaymentProofBundle calldata proofBundle)
        external
        view
        returns (bool);

    /// @notice Verify a proof of `VALID NOTE REDEMPTION`
    /// @param proofBundle The proof bundle for the note redemption
    /// @return True if the proof is valid, false otherwise
    function verifyNoteRedemptionValidity(NoteRedemptionProofBundle calldata proofBundle)
        external
        view
        returns (bool);

    /// @notice Verify a batch of proofs
    /// @param proofs The proofs to verify
    /// @param publicInputs The public inputs to the proofs
    /// @param vks The verification keys for the proofs
    /// @param extraOpeningElements The extra opening elements to use in the batch verification
    /// @return True if the proofs are valid, false otherwise
    /// @dev We use this method for settlements which don't have a _specific_ list of proofs to verify
    /// and instead prefer to pass proofs as a batch.
    function batchVerify(
        PlonkProof[] memory proofs,
        BN254.ScalarField[][] memory publicInputs,
        VerificationKey[] memory vks,
        OpeningElements memory extraOpeningElements
    )
        external
        view
        returns (bool);
}

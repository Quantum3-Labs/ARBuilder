// SPDX-License-Identifier: MIT
/* solhint-disable gas-calldata-parameters */
pragma solidity ^0.8.24;

import { IVerifier } from "darkpoolv2-interfaces/IVerifier.sol";

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

/// @title Test Verifier Implementation
/// @author Renegade Eng
/// @notice This is a test implementation of the `IVerifier` interface that always returns true
/// @notice even if verification fails
contract TestVerifierV2 is IVerifier {
    /// @inheritdoc IVerifier
    function verifyExistingBalanceDepositValidity(DepositProofBundle calldata) external pure returns (bool) {
        return true;
    }

    /// @inheritdoc IVerifier
    function verifyNewBalanceDepositValidity(NewBalanceDepositProofBundle calldata) external pure returns (bool) {
        return true;
    }

    /// @inheritdoc IVerifier
    function verifyWithdrawalValidity(WithdrawalProofBundle calldata) external pure returns (bool) {
        return true;
    }

    /// @inheritdoc IVerifier
    function verifyOrderCancellationValidity(OrderCancellationProofBundle calldata) external pure returns (bool) {
        return true;
    }

    /// @inheritdoc IVerifier
    function verifyPublicProtocolFeePaymentValidity(PublicProtocolFeePaymentProofBundle calldata)
        external
        pure
        returns (bool)
    {
        return true;
    }

    /// @inheritdoc IVerifier
    function verifyPublicRelayerFeePaymentValidity(PublicRelayerFeePaymentProofBundle calldata)
        external
        pure
        returns (bool)
    {
        return true;
    }

    /// @inheritdoc IVerifier
    function verifyPrivateProtocolFeePaymentValidity(PrivateProtocolFeePaymentProofBundle calldata)
        external
        pure
        returns (bool)
    {
        return true;
    }

    /// @inheritdoc IVerifier
    function verifyPrivateRelayerFeePaymentValidity(PrivateRelayerFeePaymentProofBundle calldata)
        external
        pure
        returns (bool)
    {
        return true;
    }

    /// @inheritdoc IVerifier
    function verifyNoteRedemptionValidity(NoteRedemptionProofBundle calldata) external pure returns (bool) {
        return true;
    }

    /// @inheritdoc IVerifier
    function batchVerify(
        PlonkProof[] memory,
        BN254.ScalarField[][] memory,
        VerificationKey[] memory,
        OpeningElements memory
    )
        external
        pure
        returns (bool)
    {
        return true;
    }
}

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { IVerifier } from "darkpoolv2-interfaces/IVerifier.sol";
import { IVkeys } from "darkpoolv2-interfaces/IVkeys.sol";

import { BN254 } from "solidity-bn254/BN254.sol";
import { PlonkProof, VerificationKey, OpeningElements } from "renegade-lib/verifier/Types.sol";
import { VerifierCore } from "renegade-lib/verifier/VerifierCore.sol";

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
import { PublicInputsLib } from "darkpoolv2-lib/public_inputs/PublicInputsLib.sol";

/// @title Verifier
/// @author Renegade Eng
/// @notice Implementation of the IVerifier interface for the DarkpoolV2 contract
contract Verifier is IVerifier {
    using PublicInputsLib for ValidDepositStatement;
    using PublicInputsLib for ValidBalanceCreateStatement;
    using PublicInputsLib for ValidWithdrawalStatement;
    using PublicInputsLib for ValidOrderCancellationStatement;
    using PublicInputsLib for ValidPublicProtocolFeePaymentStatement;
    using PublicInputsLib for ValidPublicRelayerFeePaymentStatement;
    using PublicInputsLib for ValidPrivateProtocolFeePaymentStatement;
    using PublicInputsLib for ValidPrivateRelayerFeePaymentStatement;
    using PublicInputsLib for ValidNoteRedemptionStatement;

    /// @notice The verification keys contract
    IVkeys public immutable VKEYS;

    /// @notice Constructor that sets the verification keys contract
    /// @param _vkeys The verification keys contract address
    constructor(IVkeys _vkeys) {
        VKEYS = _vkeys;
    }

    /// @inheritdoc IVerifier
    function verifyExistingBalanceDepositValidity(DepositProofBundle calldata depositProofBundle)
        external
        view
        returns (bool)
    {
        VerificationKey memory vk = VKEYS.depositKeys();
        BN254.ScalarField[] memory publicInputs = depositProofBundle.statement.statementSerialize();
        return VerifierCore.verify(depositProofBundle.proof, publicInputs, vk);
    }

    /// @inheritdoc IVerifier
    function verifyNewBalanceDepositValidity(NewBalanceDepositProofBundle calldata newBalanceProofBundle)
        external
        view
        returns (bool)
    {
        VerificationKey memory vk = VKEYS.balanceCreateKeys();
        BN254.ScalarField[] memory publicInputs = newBalanceProofBundle.statement.statementSerialize();
        return VerifierCore.verify(newBalanceProofBundle.proof, publicInputs, vk);
    }

    /// @inheritdoc IVerifier
    function verifyWithdrawalValidity(WithdrawalProofBundle calldata withdrawalProofBundle)
        external
        view
        returns (bool)
    {
        VerificationKey memory vk = VKEYS.withdrawalKeys();
        BN254.ScalarField[] memory publicInputs = withdrawalProofBundle.statement.statementSerialize();
        return VerifierCore.verify(withdrawalProofBundle.proof, publicInputs, vk);
    }

    /// @inheritdoc IVerifier
    function verifyOrderCancellationValidity(OrderCancellationProofBundle calldata orderCancellationProofBundle)
        external
        view
        returns (bool)
    {
        VerificationKey memory vk = VKEYS.orderCancellationKeys();
        BN254.ScalarField[] memory publicInputs = orderCancellationProofBundle.statement.statementSerialize();
        return VerifierCore.verify(orderCancellationProofBundle.proof, publicInputs, vk);
    }

    /// @inheritdoc IVerifier
    function verifyPublicProtocolFeePaymentValidity(PublicProtocolFeePaymentProofBundle calldata proofBundle)
        external
        view
        returns (bool)
    {
        VerificationKey memory vk = VKEYS.publicProtocolFeePaymentKeys();
        BN254.ScalarField[] memory publicInputs = proofBundle.statement.statementSerialize();
        return VerifierCore.verify(proofBundle.proof, publicInputs, vk);
    }

    /// @inheritdoc IVerifier
    function verifyPublicRelayerFeePaymentValidity(PublicRelayerFeePaymentProofBundle calldata proofBundle)
        external
        view
        returns (bool)
    {
        VerificationKey memory vk = VKEYS.publicRelayerFeePaymentKeys();
        BN254.ScalarField[] memory publicInputs = proofBundle.statement.statementSerialize();
        return VerifierCore.verify(proofBundle.proof, publicInputs, vk);
    }

    /// @inheritdoc IVerifier
    function verifyPrivateProtocolFeePaymentValidity(PrivateProtocolFeePaymentProofBundle calldata proofBundle)
        external
        view
        returns (bool)
    {
        VerificationKey memory vk = VKEYS.privateProtocolFeePaymentKeys();
        BN254.ScalarField[] memory publicInputs = proofBundle.statement.statementSerialize();
        return VerifierCore.verify(proofBundle.proof, publicInputs, vk);
    }

    /// @inheritdoc IVerifier
    function verifyPrivateRelayerFeePaymentValidity(PrivateRelayerFeePaymentProofBundle calldata proofBundle)
        external
        view
        returns (bool)
    {
        VerificationKey memory vk = VKEYS.privateRelayerFeePaymentKeys();
        BN254.ScalarField[] memory publicInputs = proofBundle.statement.statementSerialize();
        return VerifierCore.verify(proofBundle.proof, publicInputs, vk);
    }

    /// @inheritdoc IVerifier
    function verifyNoteRedemptionValidity(NoteRedemptionProofBundle calldata proofBundle)
        external
        view
        returns (bool)
    {
        VerificationKey memory vk = VKEYS.noteRedemptionKeys();
        BN254.ScalarField[] memory publicInputs = proofBundle.statement.statementSerialize();
        return VerifierCore.verify(proofBundle.proof, publicInputs, vk);
    }

    /// @inheritdoc IVerifier
    function batchVerify(
        PlonkProof[] calldata proofs,
        BN254.ScalarField[][] calldata publicInputs,
        VerificationKey[] calldata vks,
        OpeningElements calldata extraOpeningElements
    )
        external
        view
        returns (bool)
    {
        return VerifierCore.batchVerify(proofs, publicInputs, vks, extraOpeningElements);
    }
}

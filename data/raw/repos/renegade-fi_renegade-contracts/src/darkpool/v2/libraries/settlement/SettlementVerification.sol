// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { IVerifier } from "darkpoolv2-interfaces/IVerifier.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";
import { OpeningElements } from "renegade-lib/verifier/Types.sol";
import { ProofLinkingCore } from "renegade-lib/verifier/ProofLinking.sol";
import { SettlementContext, SettlementContextLib } from "darkpoolv2-types/settlement/SettlementContext.sol";

/// @title SettlementVerification
/// @author Renegade Eng
/// @notice Library for verifying settlement proofs
/// @dev Separated from SettlementLib to reduce bytecode size via delegatecall
library SettlementVerification {
    using SettlementContextLib for SettlementContext;

    /// @notice Verify the proofs necessary for settlement
    /// @param settlementContext The settlement context to verify the proofs from
    /// @param verifier The verifier to use for verification
    function verifySettlementProofs(SettlementContext memory settlementContext, IVerifier verifier) public view {
        if (settlementContext.numProofs() == 0) {
            return;
        }

        // Create the extra commitment opening elements implied by the proof linking relation
        OpeningElements memory linkOpenings =
            ProofLinkingCore.createOpeningElements(settlementContext.proofLinkingArguments.instances);

        // Call the core verifier
        bool valid = verifier.batchVerify(
            settlementContext.verifications.proofs,
            settlementContext.verifications.publicInputs,
            settlementContext.verifications.vks,
            linkOpenings
        );

        if (!valid) {
            revert IDarkpoolV2.SettlementVerificationFailed();
        }
    }
}

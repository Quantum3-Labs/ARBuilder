// SPDX-License-Identifier: Apache
pragma solidity ^0.8.24;

/// @title Utils for the PlonK proof linking relation defined here:
/// https://renegade-fi.notion.site/Proof-Linking-PlonK-00964f558b184e4c94b92247f4ebc5d8

import { TranscriptLib, Transcript } from "./Transcript.sol";
import { ProofLinkingInstance, OpeningElements, LinkingProof, ProofLinkingVK } from "./Types.sol";
import { BN254Helpers } from "./BN254Helpers.sol";
import { BN254 } from "solidity-bn254/BN254.sol";

/// @title Utils for the PlonK proof linking relation
/// @author Renegade Eng
/// @notice This library is used to create opening elements for the proof linking relation
library ProofLinkingCore {
    using TranscriptLib for Transcript;

    /* solhint-disable function-max-lines */
    /// @notice Create a set of opening elements for the proof linking relation
    /// @param arguments The proof linking arguments to create opening elements for
    /// @return The opening elements
    function createOpeningElements(ProofLinkingInstance[] memory arguments)
        internal
        view
        returns (OpeningElements memory)
    {
        BN254.G1Point[] memory lhsPoints = new BN254.G1Point[](arguments.length);
        BN254.G1Point[] memory rhsPoints = new BN254.G1Point[](arguments.length);
        BN254.ScalarField[] memory challenges = new BN254.ScalarField[](arguments.length);

        for (uint256 i = 0; i < arguments.length; ++i) {
            BN254.G1Point memory wireComm0 = arguments[i].wireComm0;
            BN254.G1Point memory wireComm1 = arguments[i].wireComm1;
            LinkingProof memory linkingProof = arguments[i].proof;
            ProofLinkingVK memory vk = arguments[i].vk;

            // Compute the opening challenge for the proof linking relation
            BN254.ScalarField challenge =
                computeOpeningChallenge(wireComm0, wireComm1, linkingProof.linkingQuotientPolyComm);

            // Compute the evaluation of the vanishing polynomial over the linking domain
            BN254.ScalarField subdomainVanishingEval = BN254Helpers.ONE;
            BN254.ScalarField subdomainElement = BN254.ScalarField.wrap(
                BN254.powSmall(BN254.ScalarField.unwrap(vk.linkGroupGenerator), vk.linkGroupOffset, BN254.R_MOD)
            );

            // Compute the evaluation of the subdomain vanishing polynomial at the challenge:
            // (x - w_0) * (x - w_1) * ... * (x - w_{n-1})
            for (uint256 j = 0; j < vk.linkGroupSize; ++j) {
                subdomainVanishingEval = BN254.mul(subdomainVanishingEval, BN254.sub(challenge, subdomainElement));
                subdomainElement = BN254.mul(subdomainElement, vk.linkGroupGenerator);
            }

            // Compute a commitment to the polynomial a_1(x) - a_2(x) - Z(challenge) * linkingQuotientPolyComm
            // This polynomial should be zero at the challenge point, so we evaluate an opening at the challenge
            BN254.G1Point memory wireDiffComm = BN254.sub(wireComm0, wireComm1);
            BN254.ScalarField vanishingCoeff = BN254.negate(subdomainVanishingEval);
            BN254.G1Point memory linkingPolyComm =
                BN254.add(wireDiffComm, BN254.scalarMul(linkingProof.linkingQuotientPolyComm, vanishingCoeff));

            // Instead of checking the traditional form of KZG opening, e.g (for opening proof pi):
            //  e(\pi, [x-challenge]_2) ?= e(comm - eval, [1]_2)
            // We manipulate the relation to fit into the existing PlonK opening check:
            //  e(\pi, [x]_2) ?= e(comm - eval + \pi * challenge, [1]_2)
            // The eval should be zero at the challenge point, so this simplifies to:
            //  e(\pi, [x]_2) ?= e(comm + \pi * challenge, [1]_2)
            // Finally, the calling interface expects the right hand side to be negated, so we return:
            //  - (comm + \pi * challenge)
            // for the RHS point
            BN254.G1Point memory lhs = linkingProof.linkingPolyOpening;
            BN254.G1Point memory rhs =
                BN254.add(BN254.scalarMul(linkingProof.linkingPolyOpening, challenge), linkingPolyComm);

            lhsPoints[i] = lhs;
            rhsPoints[i] = BN254.negate(rhs);
            challenges[i] = challenge;
        }

        return OpeningElements({ lhsTerms: lhsPoints, rhsTerms: rhsPoints, lastChallenges: challenges });
    }
    /* solhint-enable function-max-lines */

    /// @notice Compute the proof link opening challenge
    /// @param wireComm0 The commitment to the first wire polynomial
    /// @param wireComm1 The commitment to the second wire polynomial
    /// @param linkingQuotientPolyComm The commitment to the linking quotient polynomial
    /// @return The opening challenge
    function computeOpeningChallenge(
        BN254.G1Point memory wireComm0,
        BN254.G1Point memory wireComm1,
        BN254.G1Point memory linkingQuotientPolyComm
    )
        internal
        pure
        returns (BN254.ScalarField)
    {
        Transcript memory transcript = TranscriptLib.newTranscript();
        transcript.appendPoint(wireComm0);
        transcript.appendPoint(wireComm1);
        transcript.appendPoint(linkingQuotientPolyComm);

        return transcript.getChallenge();
    }
}

// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import { Transcript } from "./Transcript.sol";
import {
    PlonkProof, VerificationKey, Challenges, NUM_WIRE_TYPES, OpeningElements, emptyOpeningElements
} from "./Types.sol";
import { TranscriptLib } from "./Transcript.sol";
import { BN254 } from "solidity-bn254/BN254.sol";
import { BN254Helpers } from "./BN254Helpers.sol";

// -------------
// | Constants |
// -------------

/// @dev The bytes representation of the number of bits in the scalar field (little-endian)
/// @dev Shifted to give a little endian representation
bytes4 constant SCALAR_FIELD_N_BITS = bytes4(uint32(254) << 24);

// ------------
// | Verifier |
// ------------

/// @title A verifier for Plonk proofs
/// @author Renegade Eng
/// @notice This implementation currently follows that outlined in the paper closely:
/// https://eprint.iacr.org/2019/953.pdf
library VerifierCore {
    using TranscriptLib for Transcript;

    /// @notice Thrown when the public input length is invalid
    error InvalidPublicInputLength();

    /// @notice Verify a single plonk proof
    /// @param proof The proof to verify
    /// @param publicInputs The public inputs to the proof
    /// @param vk The verification key for the circuit
    /// @return True if the proof is valid, false otherwise
    function verify(
        PlonkProof memory proof,
        BN254.ScalarField[] memory publicInputs,
        VerificationKey memory vk
    )
        public
        view
        returns (bool)
    {
        PlonkProof[] memory proofArray = new PlonkProof[](1);
        proofArray[0] = proof;

        BN254.ScalarField[][] memory publicInputsArray = new BN254.ScalarField[][](1);
        publicInputsArray[0] = publicInputs;

        VerificationKey[] memory vkArray = new VerificationKey[](1);
        vkArray[0] = vk;

        OpeningElements memory extraOpeningElements = emptyOpeningElements();
        return batchVerify(proofArray, publicInputsArray, vkArray, extraOpeningElements);
    }

    /// @notice Verify a batch of Plonk proofs using the arithmetization defined in `mpc-jellyfish`:
    /// https://github.com/renegade-fi/mpc-jellyfish
    /// @param proofs The proofs to verify
    /// @param publicInputs The public inputs to the proofs
    /// @param vks The verification keys for the circuit
    /// @param extraOpeningElements The extra opening elements to use in the batch verification
    /// @return True if the proofs are valid, false otherwise
    function batchVerify( // solhint-disable-line function-max-lines
        PlonkProof[] memory proofs,
        BN254.ScalarField[][] memory publicInputs,
        VerificationKey[] memory vks,
        OpeningElements memory extraOpeningElements
    )
        public
        view
        returns (bool)
    {
        plonkStep1And2(proofs);
        plonkStep3(publicInputs, vks);
        Challenges[] memory batchChallenges = plonkStep4(proofs, publicInputs, vks);

        // Get the base root of unity for the circuit's evaluation domain
        BN254.ScalarField[] memory lastChallenges = new BN254.ScalarField[](proofs.length);
        BN254.G1Point[] memory lhsTerms = new BN254.G1Point[](proofs.length);
        BN254.G1Point[] memory rhsTerms = new BN254.G1Point[](proofs.length);
        for (uint256 i = 0; i < proofs.length; ++i) {
            PlonkProof memory proof = proofs[i];
            VerificationKey memory vk = vks[i];
            Challenges memory challenges = batchChallenges[i];
            BN254.ScalarField[] memory publicInput = publicInputs[i];

            // Setup the public input polynomial
            BN254.ScalarField omega = BN254Helpers.rootOfUnity(vk.n);
            (BN254.ScalarField vanishingEval, BN254.ScalarField lagrangeEval) = plonkStep5And6(vk.n, challenges.zeta);
            BN254.ScalarField publicInputPolyEval = plonkStep7(vk.n, challenges.zeta, omega, vanishingEval, publicInput);

            // Compute the reduction to a pairing check
            BN254.ScalarField linearizationConstTerm = plonkStep8(
                publicInputPolyEval,
                lagrangeEval,
                challenges.alpha,
                challenges.beta,
                challenges.gamma,
                proof.wireEvals,
                proof.sigmaEvals,
                proof.zBar
            );
            BN254.G1Point memory committedPoly = plonkStep9(lagrangeEval, vanishingEval, challenges, proof, vk);
            BN254.G1Point memory batchCommitment = plonkStep10(committedPoly, challenges, proof, vk);
            BN254.G1Point memory batchEval = plonkStep11(linearizationConstTerm, challenges, proof, vk);

            // Step 12: Batch validate the evaluations
            // LHS of the pairing check: e(w_zeta + wZetaOmega * u, x_h)
            BN254.G1Point memory lhsTerm = BN254.add(proof.wZeta, BN254.scalarMul(proof.wZetaOmega, challenges.u));

            // RHS of the pairing check: e(zeta * w_zeta + u * zeta * omega * wZetaOmega + batchCommitment -
            // batchEval, x_h)
            BN254.G1Point memory rhsTerm = BN254.add(
                BN254.scalarMul(proof.wZeta, challenges.zeta),
                BN254.scalarMul(proof.wZetaOmega, BN254.mul(challenges.u, BN254.mul(challenges.zeta, omega)))
            );
            rhsTerm = BN254.add(rhsTerm, BN254.sub(batchCommitment, batchEval));

            lhsTerms[i] = lhsTerm;
            rhsTerms[i] = BN254.negate(rhsTerm);
            lastChallenges[i] = challenges.u;
        }

        OpeningElements memory openingElements =
            OpeningElements({ lhsTerms: lhsTerms, rhsTerms: rhsTerms, lastChallenges: lastChallenges });
        return verifyBatchOpening(vks[0].h, vks[0].xH, openingElements, extraOpeningElements);
    }

    /// @notice Verify a batch opening of proofs
    /// @param h The base G2 point
    /// @param xH The base G2 point
    /// @param proofOpeningElements The opening elements for the proofs
    /// @param extraOpeningElements The extra opening elements to use in the batch verification
    /// @return True if the batch opening is valid, false otherwise
    function verifyBatchOpening(
        BN254.G2Point memory h,
        BN254.G2Point memory xH,
        OpeningElements memory proofOpeningElements,
        OpeningElements memory extraOpeningElements
    )
        public
        view
        returns (bool)
    {
        uint256 numProofs = proofOpeningElements.lhsTerms.length + extraOpeningElements.lhsTerms.length;

        // Sample a random scalar to parameterize the random linear combination
        // If only one proof is supplied, no randomization is needed
        BN254.ScalarField r = BN254Helpers.ONE;
        if (numProofs > 1) {
            Transcript memory transcript = TranscriptLib.newTranscript();
            transcript.appendScalars(proofOpeningElements.lastChallenges);
            transcript.appendScalars(extraOpeningElements.lastChallenges);
            r = transcript.getChallenge();
        }

        BN254.ScalarField rCurr = r;
        BN254.G1Point memory lhsTerm = proofOpeningElements.lhsTerms[0];
        BN254.G1Point memory rhsTerm = proofOpeningElements.rhsTerms[0];

        // Add the proof opening elements
        for (uint256 i = 1; i < proofOpeningElements.lhsTerms.length; ++i) {
            lhsTerm = BN254.add(lhsTerm, BN254.scalarMul(proofOpeningElements.lhsTerms[i], rCurr));
            rhsTerm = BN254.add(rhsTerm, BN254.scalarMul(proofOpeningElements.rhsTerms[i], rCurr));
            rCurr = BN254.mul(rCurr, r);
        }

        // Add the extra opening elements
        for (uint256 i = 0; i < extraOpeningElements.lhsTerms.length; ++i) {
            lhsTerm = BN254.add(lhsTerm, BN254.scalarMul(extraOpeningElements.lhsTerms[i], rCurr));
            rhsTerm = BN254.add(rhsTerm, BN254.scalarMul(extraOpeningElements.rhsTerms[i], rCurr));
            rCurr = BN254.mul(rCurr, r);
        }

        return BN254.pairingProd2(lhsTerm, xH, rhsTerm, h);
    }

    /// @notice Step 1 and 2 of the plonk verification algorithm
    /// @notice Verify that the G_1 points are on the curve
    /// @param proofs The proofs to verify
    function plonkStep1And2(PlonkProof[] memory proofs) internal pure {
        // Check that the commitments to the wire polynomials are on the curve
        for (uint256 i = 0; i < proofs.length; ++i) {
            PlonkProof memory proof = proofs[i];
            for (uint256 j = 0; j < proof.wireComms.length; ++j) {
                BN254.validateG1Point(proof.wireComms[j]);
            }

            // Check the commitment to the grand product polynomial is on the curve
            BN254.validateG1Point(proof.zComm);

            // Check the commitments to the quotient polynomials are on the curve
            for (uint256 j = 0; j < proof.quotientComms.length; ++j) {
                BN254.validateG1Point(proof.quotientComms[j]);
            }

            // Check that the opening proofs are on the curve
            BN254.validateG1Point(proof.wZeta);
            BN254.validateG1Point(proof.wZetaOmega);

            // Check that each of the evaluations of wire polynomials are in the scalar field
            for (uint256 j = 0; j < proof.wireEvals.length; ++j) {
                BN254.validateScalarField(proof.wireEvals[j]);
            }

            // Check that each of the evaluations of the permutation polynomials are in the scalar field
            for (uint256 j = 0; j < proof.sigmaEvals.length; ++j) {
                BN254.validateScalarField(proof.sigmaEvals[j]);
            }

            // Check that the evaluation of the grand product polynomial is in the scalar field
            BN254.validateScalarField(proof.zBar);
        }
    }

    /// @notice Step 3 of the plonk verification algorithm
    /// @notice Verify that the public inputs to the proof are all in the scalar field
    /// @param publicInputs The public inputs to the proofs
    /// @param vks The verification keys for the circuit
    function plonkStep3(BN254.ScalarField[][] memory publicInputs, VerificationKey[] memory vks) internal pure {
        // Check that the public inputs are all in the scalar field
        for (uint256 i = 0; i < publicInputs.length; ++i) {
            require(publicInputs[i].length == vks[i].l, InvalidPublicInputLength());
            for (uint256 j = 0; j < publicInputs[i].length; ++j) {
                BN254.validateScalarField(publicInputs[i][j]);
            }
        }
    }

    /// @notice Step 4 of the plonk verification algorithm
    /// @notice Compute the challenges from a Fiat-Shamir transcript
    /// @dev matches the transcript implementation from `mpc-jellyfish`
    /// @param proofs The proofs to verify
    /// @param publicInputs The public inputs to the proofs
    /// @param vks The verification keys for the circuit
    /// @return The challenges from the Fiat-Shamir transcript
    function plonkStep4( // solhint-disable-line function-max-lines
        PlonkProof[] memory proofs,
        BN254.ScalarField[][] memory publicInputs,
        VerificationKey[] memory vks
    )
        internal
        pure
        returns (Challenges[] memory)
    {
        Challenges[] memory challengesArray = new Challenges[](proofs.length);

        for (uint256 i = 0; i < proofs.length; ++i) {
            // Create a new transcript
            Transcript memory transcript = TranscriptLib.newTranscript();

            // Append the verification key metadata and public inputs
            bytes memory nBitsBytes = abi.encodePacked(SCALAR_FIELD_N_BITS);
            transcript.appendMessage(nBitsBytes);
            transcript.appendU64(vks[i].n);
            transcript.appendU64(vks[i].l);

            transcript.appendScalars(vks[i].k);
            transcript.appendPoints(vks[i].qComms);
            transcript.appendPoints(vks[i].sigmaComms);
            transcript.appendScalars(publicInputs[i]);

            // Round 1: Append the wire commitments and squeeze the permutation challenges
            transcript.appendPoints(proofs[i].wireComms);

            // Squeeze an unused challenge tau for consistency with the Plookup-enabled prover
            transcript.getChallenge();
            BN254.ScalarField beta = transcript.getChallenge();
            BN254.ScalarField gamma = transcript.getChallenge();

            // Round 2: Append the quotient permutation polynomial commitment and squeeze the quotient challenge
            transcript.appendPoint(proofs[i].zComm);
            BN254.ScalarField alpha = transcript.getChallenge();

            // Round 3: Append the quotient polynomial commitments and squeeze the evaluation challenge
            transcript.appendPoints(proofs[i].quotientComms);
            BN254.ScalarField zeta = transcript.getChallenge();

            // Round 4: Append the wire, permutation, and grand product evals and squeeze the v opening challenge
            transcript.appendScalars(proofs[i].wireEvals);
            transcript.appendScalars(proofs[i].sigmaEvals);
            transcript.appendScalar(proofs[i].zBar);
            BN254.ScalarField v = transcript.getChallenge();

            // Round 5: Append the two opening proof commitments and squeeze the multipoint evaluation challenge
            transcript.appendPoint(proofs[i].wZeta);
            transcript.appendPoint(proofs[i].wZetaOmega);
            BN254.ScalarField u = transcript.getChallenge();

            challengesArray[i] = Challenges({ beta: beta, gamma: gamma, alpha: alpha, zeta: zeta, v: v, u: u });
        }

        return challengesArray;
    }

    /// @notice Plonk step 5 and 6
    /// @dev Step 5: Compute the zero polynomial evaluation
    /// @dev This is (for eval point zeta) zeta^n - 1
    /// @dev Step 6: Compute the first Lagrange basis polynomial evaluated at zeta
    /// @param n The number of gates in the circuit
    /// @param zeta The evaluation challenge from the transcript
    /// @return The evaluation of the zero polynomial at zeta
    /// @return The evaluation of the first Lagrange basis polynomial at zeta
    function plonkStep5And6(
        uint256 n,
        BN254.ScalarField zeta
    )
        internal
        view
        returns (BN254.ScalarField, BN254.ScalarField)
    {
        // Step 5: Compute the zero polynomial evaluation
        uint256 zetaUint = BN254.ScalarField.unwrap(zeta);
        BN254.ScalarField zetaPow = BN254.ScalarField.wrap(BN254.powSmall(zetaUint, n, BN254.R_MOD));
        BN254.ScalarField vanishingEval = BN254.add(zetaPow, BN254Helpers.NEG_ONE);

        // Step 6: Compute the first Lagrange basis polynomial evaluated at zeta
        BN254.ScalarField nScalar = BN254.ScalarField.wrap(uint256(n));
        BN254.ScalarField lagrangeDenom = BN254.add(zeta, BN254Helpers.NEG_ONE);
        lagrangeDenom = BN254.invert(BN254.mul(nScalar, lagrangeDenom));
        BN254.ScalarField lagrangeNum = vanishingEval;
        BN254.ScalarField lagrangeEval = BN254.mul(lagrangeNum, lagrangeDenom);

        return (vanishingEval, lagrangeEval);
    }

    /// @notice Step 7 of the plonk verification algorithm with full struct
    /// @dev Compute the evaluation of the public input polynomial
    /// @dev Over the multiplicative subgroup, each Lagrange basis polynomial L_i(x) takes the form:
    /// @dev L_i(x) = (zeta^n - 1) / n * (zeta - omega^i)
    /// @param n The number of gates in the circuit
    /// @param zeta The evaluation challenge from the transcript
    /// @param omega The omega challenge from the transcript
    /// @param vanishingEval The evaluation of the zero polynomial at zeta
    /// @param publicInputs The public inputs to the proofs
    /// @return The evaluation of the public input polynomial at zeta
    function plonkStep7(
        uint256 n,
        BN254.ScalarField zeta,
        BN254.ScalarField omega,
        BN254.ScalarField vanishingEval,
        BN254.ScalarField[] memory publicInputs
    )
        internal
        view
        returns (BN254.ScalarField)
    {
        BN254.ScalarField nInv = BN254.invert(BN254.ScalarField.wrap(n));
        BN254.ScalarField vanishingDivN = BN254.mul(vanishingEval, nInv);

        BN254.ScalarField result = BN254.ScalarField.wrap(0);
        BN254.ScalarField currOmegaPow = BN254Helpers.ONE;
        for (uint256 i = 0; i < publicInputs.length; ++i) {
            BN254.ScalarField lagrangeNum = BN254.mul(vanishingDivN, currOmegaPow);
            BN254.ScalarField lagrangeDenom = BN254.sub(zeta, currOmegaPow);
            BN254.ScalarField lagrangeEval = BN254.mul(lagrangeNum, BN254.invert(lagrangeDenom));
            currOmegaPow = BN254.mul(currOmegaPow, omega);

            BN254.ScalarField currTerm = BN254.mul(publicInputs[i], lagrangeEval);
            result = BN254.add(result, currTerm);
        }

        return result;
    }

    /// @notice Step 8 of the plonk verification algorithm
    /// @dev Compute the constant term of the linearization polynomial
    /// @param publicInputPolyEval The evaluation of the public input polynomial at zeta
    /// @param lagrange1Eval The evaluation of the first Lagrange basis polynomial at zeta
    /// @param alpha The quotient challenge from the transcript
    /// @param beta The first permutation challenge from the transcript
    /// @param gamma The second permutation challenge from the transcript
    /// @param wireEvals The evaluations of the wire polynomials at zeta
    /// @param sigmaEvals The evaluations of the permutation polynomials at zeta
    /// @param zEval The evaluation of the grand product polynomial at zeta
    /// @return The constant term of the linearization polynomial
    function plonkStep8(
        BN254.ScalarField publicInputPolyEval,
        BN254.ScalarField lagrange1Eval,
        BN254.ScalarField alpha,
        BN254.ScalarField beta,
        BN254.ScalarField gamma,
        BN254.ScalarField[NUM_WIRE_TYPES] memory wireEvals,
        BN254.ScalarField[NUM_WIRE_TYPES - 1] memory sigmaEvals,
        BN254.ScalarField zEval
    )
        internal
        pure
        returns (BN254.ScalarField)
    {
        // Term 1: PI(\zeta)
        BN254.ScalarField res = publicInputPolyEval;

        // Term 2: -L_1(\zeta) * \alpha^2
        BN254.ScalarField term2 = BN254.mul(lagrange1Eval, BN254.mul(alpha, alpha));
        res = BN254.sub(res, term2);

        // Add the terms from the permutation argument
        BN254.ScalarField term3 = BN254.mul(alpha, zEval);
        for (uint256 i = 0; i < wireEvals.length - 1; ++i) {
            BN254.ScalarField wireEval = wireEvals[i];
            BN254.ScalarField sigmaEval = sigmaEvals[i];

            BN254.ScalarField wirePermTerm = BN254.add(wireEval, BN254.mul(beta, sigmaEval));
            wirePermTerm = BN254.add(wirePermTerm, gamma);

            term3 = BN254.mul(term3, wirePermTerm);
        }

        // Add in the final term without the sigma eval
        BN254.ScalarField lastPermTerm = BN254.add(wireEvals[wireEvals.length - 1], gamma);
        term3 = BN254.mul(term3, lastPermTerm);
        res = BN254.sub(res, term3);

        return res;
    }

    /// @notice Step 9 of the plonk verification algorithm
    /// @dev Compute a linearized commitment to the combined polynomial relation
    /// @param lagrange1Eval The evaluation of the first Lagrange basis polynomial at zeta
    /// @param vanishingEval The evaluation of the zero polynomial at zeta
    /// @param challenges The challenges from the transcript
    /// @param proof The proof to verify
    /// @param vk The verification key for the circuit
    /// @return The linearized commitment to the combined polynomial relation
    function plonkStep9(
        BN254.ScalarField lagrange1Eval,
        BN254.ScalarField vanishingEval,
        Challenges memory challenges,
        PlonkProof memory proof,
        VerificationKey memory vk
    )
        internal
        view
        returns (BN254.G1Point memory)
    {
        // Add in the gate constraints
        BN254.G1Point memory res = plonkStep9GateTerm(proof, vk);

        // Add in the permutation argument contribution
        BN254.G1Point memory permTerm = plonkStep9PermutationTerm(lagrange1Eval, challenges, proof, vk);
        res = BN254.add(res, permTerm);

        // Add in the quotient polynomial contribution
        BN254.G1Point memory quotientTerm = plonkStep9QuotientTerm(challenges.zeta, vanishingEval, proof);
        res = BN254.add(res, quotientTerm);
        return res;
    }

    /// @notice Compute the gate constraints contribution to the linearized polynomial relation
    /// @dev The selectors are:
    /// @dev q_lc[0:3], q_mul[0:1], q_hash[0:3], q_out, q_const, q_prod
    /// @param proof The proof to verify
    /// @param vk The verification key for the circuit
    /// @return The gate constraints contribution to the linearized polynomial relation
    function plonkStep9GateTerm(
        PlonkProof memory proof,
        VerificationKey memory vk
    )
        internal
        view
        returns (BN254.G1Point memory)
    {
        BN254.G1Point memory res = BN254.infinity();

        // The first four terms are linear combination gates
        res = BN254.add(res, BN254.scalarMul(vk.qComms[0], proof.wireEvals[0]));
        res = BN254.add(res, BN254.scalarMul(vk.qComms[1], proof.wireEvals[1]));
        res = BN254.add(res, BN254.scalarMul(vk.qComms[2], proof.wireEvals[2]));
        res = BN254.add(res, BN254.scalarMul(vk.qComms[3], proof.wireEvals[3]));

        // The next two terms are multiplication gates
        BN254.ScalarField mul1 = BN254.mul(proof.wireEvals[0], proof.wireEvals[1]);
        BN254.ScalarField mul2 = BN254.mul(proof.wireEvals[2], proof.wireEvals[3]);
        res = BN254.add(res, BN254.scalarMul(vk.qComms[4], mul1));
        res = BN254.add(res, BN254.scalarMul(vk.qComms[5], mul2));

        // The next four terms are hash gates
        BN254.ScalarField hash1 = BN254Helpers.fifthPower(proof.wireEvals[0]);
        BN254.ScalarField hash2 = BN254Helpers.fifthPower(proof.wireEvals[1]);
        BN254.ScalarField hash3 = BN254Helpers.fifthPower(proof.wireEvals[2]);
        BN254.ScalarField hash4 = BN254Helpers.fifthPower(proof.wireEvals[3]);
        res = BN254.add(res, BN254.scalarMul(vk.qComms[6], hash1));
        res = BN254.add(res, BN254.scalarMul(vk.qComms[7], hash2));
        res = BN254.add(res, BN254.scalarMul(vk.qComms[8], hash3));
        res = BN254.add(res, BN254.scalarMul(vk.qComms[9], hash4));

        // The next two gates are the output gate and the constant gate (1)
        BN254.ScalarField negOutput = BN254.negate(proof.wireEvals[4]);
        res = BN254.add(res, BN254.scalarMul(vk.qComms[10], negOutput));
        res = BN254.add(res, vk.qComms[11]); // Omit scalar mul by 1

        // Last we have the elliptic curve gate, the product of all wires
        BN254.ScalarField wireProd = BN254.mul(mul1, mul2);
        wireProd = BN254.mul(wireProd, proof.wireEvals[4]);
        res = BN254.add(res, BN254.scalarMul(vk.qComms[12], wireProd));

        return res;
    }

    /// @notice Compute the permutation argument contribution to the linearized polynomial relation
    /// @param lagrange1Eval The evaluation of the first Lagrange basis polynomial at zeta
    /// @param challenges The challenges from the transcript
    /// @param proof The proof to verify
    /// @param vk The verification key for the circuit
    /// @return The permutation argument contribution to the linearized polynomial relation
    function plonkStep9PermutationTerm(
        BN254.ScalarField lagrange1Eval,
        Challenges memory challenges,
        PlonkProof memory proof,
        VerificationKey memory vk
    )
        internal
        view
        returns (BN254.G1Point memory)
    {
        // The first permutation term, multiplied by the commitment [z]
        BN254.ScalarField betaZeta = BN254.mul(challenges.beta, challenges.zeta);
        BN254.ScalarField coeff = challenges.alpha;
        for (uint256 i = 0; i < NUM_WIRE_TYPES; ++i) {
            BN254.ScalarField betaTerm = BN254.mul(betaZeta, vk.k[i]);
            BN254.ScalarField term = BN254.add(proof.wireEvals[i], betaTerm);
            BN254.ScalarField coeffTerm = BN254.add(term, challenges.gamma);
            coeff = BN254.mul(coeff, coeffTerm);
        }

        BN254.ScalarField lagrangeTerm = BN254.mul(lagrange1Eval, BN254.mul(challenges.alpha, challenges.alpha));
        coeff = BN254.add(coeff, BN254.add(lagrangeTerm, challenges.u));
        BN254.G1Point memory res = BN254.scalarMul(proof.zComm, coeff);

        // The second permutation term, multiplied by the last permutation polynomial's commitment
        BN254.ScalarField coeff2 = BN254.mul(challenges.alpha, BN254.mul(challenges.beta, proof.zBar));
        for (uint256 i = 0; i < NUM_WIRE_TYPES - 1; ++i) {
            BN254.ScalarField term = proof.wireEvals[i];
            term = BN254.add(term, BN254.mul(challenges.beta, proof.sigmaEvals[i]));
            term = BN254.add(term, challenges.gamma);
            coeff2 = BN254.mul(coeff2, term);
        }

        coeff2 = BN254.negate(coeff2);
        BN254.G1Point memory permTerm2 = BN254.scalarMul(vk.sigmaComms[NUM_WIRE_TYPES - 1], coeff2);
        return BN254.add(res, permTerm2);
    }

    /// @notice Compute the quotient polynomial contribution to the linearized polynomial relation
    /// @param zeta The evaluation challenge from the transcript
    /// @param vanishingEval The evaluation of the zero polynomial at zeta
    /// @param proof The proof to verify
    /// @return The quotient polynomial contribution to the linearized polynomial relation
    function plonkStep9QuotientTerm(
        BN254.ScalarField zeta,
        BN254.ScalarField vanishingEval,
        PlonkProof memory proof
    )
        internal
        view
        returns (BN254.G1Point memory)
    {
        // Unlike the plonk paper, Jellyfish uses zeta^(n+2) instead of zeta^n, see:
        // https://github.com/EspressoSystems/jellyfish/blob/main/plonk/src/proof_system/prover.rs#L893
        BN254.ScalarField zetaToNPlus2 = BN254.mul(BN254.add(vanishingEval, BN254Helpers.ONE), BN254.mul(zeta, zeta));

        BN254.ScalarField coeff = BN254.negate(vanishingEval);
        BN254.G1Point memory res = BN254.infinity();
        for (uint256 i = 0; i < NUM_WIRE_TYPES; ++i) {
            res = BN254.add(res, BN254.scalarMul(proof.quotientComms[i], coeff));
            coeff = BN254.mul(coeff, zetaToNPlus2);
        }

        return res;
    }

    /// @notice Step 10 of the plonk verification algorithm
    /// @dev Compute the full polynomial relation
    /// @param aggregatePolyComm The aggregate polynomial commitment
    /// @param challenges The challenges from the transcript
    /// @param proof The proof to verify
    /// @param vk The verification key for the circuit
    /// @return The full polynomial relation
    function plonkStep10(
        BN254.G1Point memory aggregatePolyComm,
        Challenges memory challenges,
        PlonkProof memory proof,
        VerificationKey memory vk
    )
        internal
        view
        returns (BN254.G1Point memory)
    {
        BN254.G1Point memory res = aggregatePolyComm;

        // Add in the wire commitments
        BN254.ScalarField coeff = challenges.v;
        for (uint256 i = 0; i < NUM_WIRE_TYPES; ++i) {
            BN254.G1Point memory term = BN254.scalarMul(proof.wireComms[i], coeff);
            res = BN254.add(res, term);
            coeff = BN254.mul(coeff, challenges.v);
        }

        // Add in the permutation commitments, except the last
        for (uint256 i = 0; i < NUM_WIRE_TYPES - 1; ++i) {
            BN254.G1Point memory term = BN254.scalarMul(vk.sigmaComms[i], coeff);
            res = BN254.add(res, term);
            coeff = BN254.mul(coeff, challenges.v);
        }

        return res;
    }

    /// @notice Step 11 of the plonk verification algorithm
    /// @dev Compute the batch evaluation to compare against the claimed openings
    /// @param linearizationConstTerm The constant term of the linearization polynomial
    /// @param challenges The challenges from the transcript
    /// @param proof The proof to verify
    /// @param vk The verification key for the circuit
    /// @return The batch evaluation
    function plonkStep11(
        BN254.ScalarField linearizationConstTerm,
        Challenges memory challenges,
        PlonkProof memory proof,
        VerificationKey memory vk
    )
        internal
        view
        returns (BN254.G1Point memory)
    {
        BN254.ScalarField resCoeff = BN254.negate(linearizationConstTerm);
        BN254.ScalarField termCoeff = challenges.v;
        for (uint256 i = 0; i < NUM_WIRE_TYPES; ++i) {
            BN254.ScalarField term = BN254.mul(proof.wireEvals[i], termCoeff);
            resCoeff = BN254.add(resCoeff, term);
            termCoeff = BN254.mul(termCoeff, challenges.v);
        }

        for (uint256 i = 0; i < NUM_WIRE_TYPES - 1; ++i) {
            BN254.ScalarField term = BN254.mul(proof.sigmaEvals[i], termCoeff);
            resCoeff = BN254.add(resCoeff, term);
            termCoeff = BN254.mul(termCoeff, challenges.v);
        }

        BN254.ScalarField lastTerm = BN254.mul(proof.zBar, challenges.u);
        resCoeff = BN254.add(resCoeff, lastTerm);

        BN254.G1Point memory res = BN254.scalarMul(vk.g, resCoeff);
        return res;
    }
}

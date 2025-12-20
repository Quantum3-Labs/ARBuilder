// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";

/// @dev The number of wire types in the arithmetization
uint256 constant NUM_WIRE_TYPES = 5;
/// @dev The number of selectors in the arithmetization
uint256 constant NUM_SELECTORS = 13;

/// @title A Plonk proof
/// @notice This matches the Rust implementation from mpc-jellyfish
struct PlonkProof {
    /// @dev The commitments to the wire polynomials
    BN254.G1Point[NUM_WIRE_TYPES] wireComms;
    /// @dev The commitment to the grand product polynomial encoding the permutation argument
    BN254.G1Point zComm;
    /// @dev The commitments to the split quotient polynomials
    BN254.G1Point[NUM_WIRE_TYPES] quotientComms;
    /// @dev The opening proof of evaluations at challenge point `zeta`
    BN254.G1Point wZeta;
    /// @dev The opening proof of evaluations at challenge point `zeta * omega`
    BN254.G1Point wZetaOmega;
    /// @dev The evaluations of the wire polynomials at the challenge point `zeta`
    BN254.ScalarField[NUM_WIRE_TYPES] wireEvals;
    /// @dev The evaluations of the permutation polynomials at the challenge point `zeta`
    BN254.ScalarField[NUM_WIRE_TYPES - 1] sigmaEvals;
    /// @dev The evaluation of the grand product polynomial at the challenge point `zeta * omega`
    BN254.ScalarField zBar;
}

/// @title A proof of a group of linked inputs between two Plonk proofs
struct LinkingProof {
    /// @dev The commitment to the linking quotient polynomial
    BN254.G1Point linkingQuotientPolyComm;
    /// @dev The opening proof of the linking polynomial
    BN254.G1Point linkingPolyOpening;
}

/// @title A Plonk verification key
struct VerificationKey {
    /// The number of gates in the circuit
    uint64 n;
    /// The number of public inputs to the circuit
    uint64 l; // solhint-disable-line use-forbidden-name
    /// The constants used to generate the cosets of the evaluation domain
    BN254.ScalarField[NUM_WIRE_TYPES] k;
    /// The commitments to the selector polynomials
    BN254.G1Point[NUM_SELECTORS] qComms;
    /// The commitments to the permutation polynomials
    BN254.G1Point[NUM_WIRE_TYPES] sigmaComms;
    /// The generator of G1
    BN254.G1Point g;
    /// The generator of G2
    BN254.G2Point h;
    /// The secret evaluation point multiplied by the generator of G2
    BN254.G2Point xH;
}

/// @title A verification key for the proof linking relation
/// forge-lint: disable-next-line(pascal-case-struct)
struct ProofLinkingVK {
    /// @dev The generator of the subdomain over which the linked inputs are defined
    BN254.ScalarField linkGroupGenerator;
    /// @dev The offset into the domain at which the subdomain begins
    uint256 linkGroupOffset;
    /// @dev The number of linked inputs, equivalently the size of the subdomain
    uint256 linkGroupSize;
}

/// @title The public coin challenges used throughout the Plonk protocol
/// @notice These challenges are obtained via a Fiat-Shamir transformation
struct Challenges {
    /// @dev The first permutation challenge, used in round 2 of the prover algorithm
    BN254.ScalarField beta;
    /// @dev The second permutation challenge, used in round 2 of the prover algorithm
    BN254.ScalarField gamma;
    /// @dev The quotient challenge, used in round 3 of the prover algorithm
    BN254.ScalarField alpha;
    /// @dev The evaluation challenge, used in round 4 of the prover algorithm
    BN254.ScalarField zeta;
    /// @dev The opening challenge, used in round 5 of the prover algorithm
    BN254.ScalarField v;
    /// @dev The multipoint evaluation challenge, generated at the end of round 5 of the prover algorithm
    BN254.ScalarField u;
}

/// @title An instance of a proof linking argument
struct ProofLinkingInstance {
    /// @dev The commitment to the first proof's first wire polynomial
    BN254.G1Point wireComm0;
    /// @dev The commitment to the second proof's first wire polynomial
    BN254.G1Point wireComm1;
    /// @dev The linking proof itself
    LinkingProof proof;
    /// @dev The proof linking relation verification key
    ProofLinkingVK vk;
}

/// @title A set of opening elements used in the final pairing product check
struct OpeningElements {
    /// @dev The set of left hand side G1 elements
    BN254.G1Point[] lhsTerms;
    /// @dev The set of right hand side G1 elements
    BN254.G1Point[] rhsTerms;
    /// @dev The last challenge squeezed from each transcript
    BN254.ScalarField[] lastChallenges;
}

/// @notice Create empty opening elements
/// @return An OpeningElements struct with empty arrays
function emptyOpeningElements() pure returns (OpeningElements memory) {
    return OpeningElements({
        lhsTerms: new BN254.G1Point[](0),
        rhsTerms: new BN254.G1Point[](0),
        lastChallenges: new BN254.ScalarField[](0)
    });
}

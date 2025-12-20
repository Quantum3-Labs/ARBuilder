// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import { TestUtils } from "./TestUtils.sol";
import {
    VerificationKey,
    NUM_SELECTORS,
    NUM_WIRE_TYPES,
    PlonkProof,
    ProofLinkingVK,
    ProofLinkingInstance,
    LinkingProof
} from "renegade-lib/verifier/Types.sol";
import { BN254 } from "solidity-bn254/BN254.sol";
import { BN254Helpers } from "renegade-lib/verifier/BN254Helpers.sol";
import { Strings } from "oz-contracts/utils/Strings.sol";

contract VerifierTestUtils is TestUtils {
    // ---------
    // | Mocks |
    // ---------

    /// @dev Creates a mock verification key for testing
    function createMockVerificationKey() internal pure returns (VerificationKey memory) {
        BN254.G1Point memory validPoint = BN254.P1();
        BN254.ScalarField validScalar = BN254.ScalarField.wrap(1);

        // Create arrays for the verification key
        BN254.G1Point[NUM_SELECTORS] memory qComms;
        BN254.G1Point[NUM_WIRE_TYPES] memory sigmaComms;
        BN254.ScalarField[NUM_WIRE_TYPES] memory k;

        // Fill arrays with valid values
        for (uint256 i = 0; i < NUM_SELECTORS; i++) {
            qComms[i] = validPoint;
        }
        for (uint256 i = 0; i < NUM_WIRE_TYPES; i++) {
            sigmaComms[i] = validPoint;
            k[i] = validScalar;
        }

        return VerificationKey({
            n: 8, // Small power of 2 for testing
            l: 3,
            k: k,
            qComms: qComms,
            sigmaComms: sigmaComms,
            g: validPoint,
            h: BN254.P2(),
            xH: BN254.P2()
        });
    }

    // -----------------------------
    // | Reference Implementations |
    // -----------------------------

    /// --- Basic Circuits --- ///

    /// @dev Run the reference implementation to generate a vkey for the mulTwo circuit
    function getMulTwoVkey() internal returns (VerificationKey memory) {
        string[] memory args = new string[](3);
        args[0] = "./test/rust-reference-impls/target/debug/verifier";
        args[1] = "mul-two";
        args[2] = "print-vkey";

        string memory response = runBinaryGetResponse(args);
        return abi.decode(vm.parseBytes(response), (VerificationKey));
    }

    /// @dev Run the reference implementation to generate a proof for the mulTwo circuit
    function getMulTwoProof(uint256 a, uint256 b) internal returns (uint256, PlonkProof memory) {
        uint256 c = mulmod(a, b, PRIME);
        string[] memory args = new string[](6);
        args[0] = "./test/rust-reference-impls/target/debug/verifier";
        args[1] = "mul-two";
        args[2] = "prove";
        args[3] = Strings.toString(a);
        args[4] = Strings.toString(b);
        args[5] = Strings.toString(c);

        string memory response = runBinaryGetResponse(args);
        return (c, abi.decode(vm.parseBytes(response), (PlonkProof)));
    }

    /// @dev Run the reference implementation to generate a vkey for the sumPow circuit
    function getSumPowVkey() internal returns (VerificationKey memory) {
        string[] memory args = new string[](3);
        args[0] = "./test/rust-reference-impls/target/debug/verifier";
        args[1] = "sum-pow";
        args[2] = "print-vkey";

        string memory response = runBinaryGetResponse(args);
        return abi.decode(vm.parseBytes(response), (VerificationKey));
    }

    /// @dev Run the reference implementation to generate a proof for the sumPow circuit
    function getSumPowProof(uint256[10] memory witness) internal returns (BN254.ScalarField, PlonkProof memory) {
        BN254.ScalarField sum = BN254.ScalarField.wrap(0);
        for (uint256 i = 0; i < witness.length; i++) {
            sum = BN254.add(sum, BN254.ScalarField.wrap(witness[i]));
        }
        BN254.ScalarField expected = BN254Helpers.fifthPower(sum);

        string[] memory args = new string[](14);
        args[0] = "./test/rust-reference-impls/target/debug/verifier";
        args[1] = "sum-pow";
        args[2] = "prove";
        for (uint256 i = 0; i < witness.length; i++) {
            args[3 + i] = Strings.toString(witness[i]);
        }
        args[13] = Strings.toString(BN254.ScalarField.unwrap(expected));

        string memory response = runBinaryGetResponse(args);
        return (expected, abi.decode(vm.parseBytes(response), (PlonkProof)));
    }

    /// @dev Run the reference implementation to generate a vkey for the permutation circuit
    function getPermutationVkey() internal returns (VerificationKey memory) {
        string[] memory args = new string[](3);
        args[0] = "./test/rust-reference-impls/target/debug/verifier";
        args[1] = "permutation";
        args[2] = "print-vkey";

        string memory response = runBinaryGetResponse(args);
        return abi.decode(vm.parseBytes(response), (VerificationKey));
    }

    /// @dev Run the reference implementation to generate a proof for the permutation circuit
    function getPermutationProof(
        uint256 randomChallenge,
        uint256[5] memory statement,
        uint256[5] memory witness
    )
        internal
        returns (PlonkProof memory)
    {
        string[] memory args = new string[](17);
        args[0] = "./test/rust-reference-impls/target/debug/verifier";
        args[1] = "permutation";
        args[2] = "prove";
        args[3] = "--random-challenge";
        args[4] = Strings.toString(randomChallenge);

        // Encode statement elements
        args[5] = "--values";
        for (uint256 i = 0; i < statement.length; i++) {
            args[6 + i] = Strings.toString(statement[i]);
        }

        // Encode witness elements
        args[11] = "--permuted-values";
        for (uint256 i = 0; i < witness.length; i++) {
            args[12 + i] = Strings.toString(witness[i]);
        }

        string memory response = runBinaryGetResponse(args);
        return abi.decode(vm.parseBytes(response), (PlonkProof));
    }

    /// @dev Helper function to create a deep copy of a PlonkProof
    function clonePlonkProof(PlonkProof memory original) internal pure returns (PlonkProof memory) {
        BN254.G1Point[NUM_WIRE_TYPES] memory wireComms;
        BN254.G1Point[NUM_WIRE_TYPES] memory quotientComms;
        BN254.ScalarField[NUM_WIRE_TYPES] memory wireEvals;
        BN254.ScalarField[NUM_WIRE_TYPES - 1] memory sigmaEvals;

        // Clone wire commitments
        for (uint256 i = 0; i < NUM_WIRE_TYPES; i++) {
            wireComms[i] = original.wireComms[i];
            quotientComms[i] = original.quotientComms[i];
            wireEvals[i] = original.wireEvals[i];
            if (i < NUM_WIRE_TYPES - 1) {
                sigmaEvals[i] = original.sigmaEvals[i];
            }
        }

        return PlonkProof({
            wireComms: wireComms,
            zComm: original.zComm,
            quotientComms: quotientComms,
            wZeta: original.wZeta,
            wZetaOmega: original.wZetaOmega,
            wireEvals: wireEvals,
            sigmaEvals: sigmaEvals,
            zBar: original.zBar
        });
    }

    /// @dev Helper function to generate a batch of proofs, verification keys, and public inputs
    function generateBatchProofData()
        internal
        returns (PlonkProof[] memory proofs, BN254.ScalarField[][] memory publicInputs, VerificationKey[] memory vks)
    {
        proofs = new PlonkProof[](3);
        vks = new VerificationKey[](3);
        publicInputs = new BN254.ScalarField[][](3);

        // Generate mul-two proof and data
        uint256 a = randomFelt();
        uint256 b = randomFelt();
        (uint256 c, PlonkProof memory mulTwoProof) = getMulTwoProof(a, b);
        proofs[0] = mulTwoProof;
        vks[0] = getMulTwoVkey();
        publicInputs[0] = new BN254.ScalarField[](1);
        publicInputs[0][0] = BN254.ScalarField.wrap(c);

        // Generate sum-pow proof and data
        uint256[10] memory inputs;
        for (uint256 i = 0; i < 10; i++) {
            inputs[i] = randomFelt();
        }
        (BN254.ScalarField sumPow, PlonkProof memory sumPowProof) = getSumPowProof(inputs);
        proofs[1] = sumPowProof;
        vks[1] = getSumPowVkey();
        publicInputs[1] = new BN254.ScalarField[](1);
        publicInputs[1][0] = sumPow;

        // Generate permutation proof and data
        uint256 randomChallenge = randomFelt();
        uint256[5] memory statement;
        uint256[5] memory witness;
        for (uint256 i = 0; i < 5; i++) {
            statement[i] = randomFelt();
            witness[5 - i - 1] = statement[i];
        }
        PlonkProof memory permutationProof = getPermutationProof(randomChallenge, statement, witness);
        proofs[2] = permutationProof;
        vks[2] = getPermutationVkey();
        publicInputs[2] = new BN254.ScalarField[](6);
        publicInputs[2][0] = BN254.ScalarField.wrap(randomChallenge);
        for (uint256 i = 0; i < 5; i++) {
            publicInputs[2][i + 1] = BN254.ScalarField.wrap(statement[i]);
        }

        return (proofs, publicInputs, vks);
    }

    /// --- Proof Linking Circuits --- ///

    /// @dev Run the reference implementation to generate a vkey for the sum proof linking circuit
    function getSumLinkedVkey() internal returns (VerificationKey memory) {
        string[] memory args = new string[](3);
        args[0] = "./test/rust-reference-impls/target/debug/verifier";
        args[1] = "proof-link";
        args[2] = "gen-sum-vk";

        string memory response = runBinaryGetResponse(args);
        return abi.decode(vm.parseBytes(response), (VerificationKey));
    }

    /// @dev Run the reference implementation to generate a vkey for the product proof linking circuit
    function getProductLinkedVkey() internal returns (VerificationKey memory) {
        string[] memory args = new string[](3);
        args[0] = "./test/rust-reference-impls/target/debug/verifier";
        args[1] = "proof-link";
        args[2] = "gen-prod-vk";

        string memory response = runBinaryGetResponse(args);
        return abi.decode(vm.parseBytes(response), (VerificationKey));
    }

    /// @dev Run the reference implementation to generate the proof linking vkey for the two linked circuits
    function getSumProductProofLinkingVk() internal returns (ProofLinkingVK memory) {
        string[] memory args = new string[](3);
        args[0] = "./test/rust-reference-impls/target/debug/verifier";
        args[1] = "proof-link";
        args[2] = "gen-link-vk";

        string memory response = runBinaryGetResponse(args);
        return abi.decode(vm.parseBytes(response), (ProofLinkingVK));
    }

    /// @dev Run the reference implementation to generate proofs of both the sum and product circuits as
    /// well as the proof linking argument
    function getSumProductProofsAndLinkingArgument(
        uint256[5] memory sharedInputs,
        uint256 sumPrivateInput,
        uint256 productPrivateInput
    )
        internal
        returns (
            PlonkProof[] memory proofs,
            BN254.ScalarField[][] memory publicInputs,
            VerificationKey[] memory vks,
            ProofLinkingInstance memory linkingArgument
        )
    {
        // Compute the expected sum and product, these are used as public inputs
        BN254.ScalarField sum = BN254Helpers.ZERO;
        BN254.ScalarField product = BN254Helpers.ONE;
        for (uint256 i = 0; i < 5; i++) {
            sum = BN254.add(sum, BN254.ScalarField.wrap(sharedInputs[i]));
            product = BN254.mul(product, BN254.ScalarField.wrap(sharedInputs[i]));
        }
        sum = BN254.add(sum, BN254.ScalarField.wrap(sumPrivateInput));
        product = BN254.mul(product, BN254.ScalarField.wrap(productPrivateInput));

        // Get the verification keys for the sum and product circuits
        VerificationKey memory sumVkey = getSumLinkedVkey();
        VerificationKey memory productVkey = getProductLinkedVkey();

        // Get the proof linking vkey
        ProofLinkingVK memory linkVkey = getSumProductProofLinkingVk();

        string[] memory args = new string[](13);
        args[0] = "./test/rust-reference-impls/target/debug/verifier";
        args[1] = "proof-link";
        args[2] = "prove";

        // Encode shared inputs
        args[3] = "--shared";
        for (uint256 i = 0; i < sharedInputs.length; i++) {
            args[4 + i] = Strings.toString(sharedInputs[i]);
        }

        // Encode sum private input
        args[9] = "--sum-private";
        args[10] = Strings.toString(sumPrivateInput);

        // Encode product private input
        args[11] = "--prod-private";
        args[12] = Strings.toString(productPrivateInput);

        // Run the binary and decode the output into the return data
        string memory response = runBinaryGetResponse(args);
        (PlonkProof memory sumProof, PlonkProof memory productProof, LinkingProof memory linkProof) =
            abi.decode(vm.parseBytes(response), (PlonkProof, PlonkProof, LinkingProof));

        // Create a linking argument from the linking proof
        ProofLinkingInstance memory linkArg = ProofLinkingInstance({
            wireComm0: sumProof.wireComms[0],
            wireComm1: productProof.wireComms[0],
            proof: linkProof,
            vk: linkVkey
        });

        // Build the return data
        proofs = new PlonkProof[](2);
        proofs[0] = sumProof;
        proofs[1] = productProof;

        publicInputs = new BN254.ScalarField[][](2);
        publicInputs[0] = new BN254.ScalarField[](1);
        publicInputs[0][0] = sum;
        publicInputs[1] = new BN254.ScalarField[](1);
        publicInputs[1][0] = product;

        vks = new VerificationKey[](2);
        vks[0] = sumVkey;
        vks[1] = productVkey;

        return (proofs, publicInputs, vks, linkArg);
    }
}

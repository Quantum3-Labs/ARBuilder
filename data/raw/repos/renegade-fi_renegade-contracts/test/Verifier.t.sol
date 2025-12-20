// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import { TestUtils } from "test-utils/TestUtils.sol";
import { VerifierTestUtils } from "test-utils/VerifierTestUtils.sol";
import { VerifierCore } from "renegade-lib/verifier/VerifierCore.sol";
import {
    PlonkProof,
    NUM_WIRE_TYPES,
    VerificationKey,
    OpeningElements,
    emptyOpeningElements,
    ProofLinkingInstance
} from "renegade-lib/verifier/Types.sol";
import { ProofLinkingCore } from "renegade-lib/verifier/ProofLinking.sol";
import { BN254 } from "solidity-bn254/BN254.sol";

contract VerifierTest is VerifierTestUtils {
    TestUtils public testUtils;

    bytes constant INVALID_G1_POINT = "Bn254: invalid G1 point";
    bytes constant INVALID_SCALAR = "Bn254: invalid scalar field";

    function setUp() public { }

    // --- Invalid Test Cases --- //

    /// @notice Test that the verifier properly validates all proof components in step 1 of Plonk verification
    function testMalformedProof() public {
        // Create a valid scalar and EC point to use as a base
        BN254.G1Point memory validPoint = BN254.P1();
        BN254.G1Point memory invalidPoint = BN254.G1Point({ x: BN254.BaseField.wrap(42), y: BN254.BaseField.wrap(0) });
        BN254.ScalarField validScalar = BN254.ScalarField.wrap(1);
        BN254.ScalarField invalidScalar = BN254.ScalarField.wrap(BN254.R_MOD);

        // Create fixed-size arrays
        BN254.G1Point[NUM_WIRE_TYPES] memory wireComms;
        BN254.G1Point[NUM_WIRE_TYPES] memory quotientComms;
        BN254.ScalarField[NUM_WIRE_TYPES] memory wireEvals;
        BN254.ScalarField[NUM_WIRE_TYPES - 1] memory sigmaEvals;

        // Fill arrays with valid values
        for (uint256 i = 0; i < NUM_WIRE_TYPES; i++) {
            wireComms[i] = validPoint;
            quotientComms[i] = validPoint;
            wireEvals[i] = validScalar;
            if (i < NUM_WIRE_TYPES - 1) {
                sigmaEvals[i] = validScalar;
            }
        }

        // Create a valid proof
        BN254.ScalarField[] memory publicInputs = new BN254.ScalarField[](1);
        publicInputs[0] = validScalar;
        PlonkProof memory proof = PlonkProof({
            wireComms: wireComms,
            zComm: validPoint,
            quotientComms: quotientComms,
            wZeta: validPoint,
            wZetaOmega: validPoint,
            wireEvals: wireEvals,
            sigmaEvals: sigmaEvals,
            zBar: validScalar
        });

        // Create a mock verification key
        VerificationKey memory vk = createMockVerificationKey();

        // Test Case 1: Invalid wire commitment
        uint256 invalidIdx = randomUint(NUM_WIRE_TYPES);
        proof.wireComms[invalidIdx] = invalidPoint;
        vm.expectRevert(INVALID_G1_POINT);
        VerifierCore.verify(proof, publicInputs, vk);
        proof.wireComms[invalidIdx] = validPoint; // Reset

        // Test Case 2: Invalid z commitment
        invalidIdx = randomUint(NUM_WIRE_TYPES);
        proof.zComm = invalidPoint;
        vm.expectRevert(INVALID_G1_POINT);
        VerifierCore.verify(proof, publicInputs, vk);
        proof.zComm = validPoint; // Reset

        // Test Case 3: Invalid quotient commitment
        invalidIdx = randomUint(NUM_WIRE_TYPES);
        proof.quotientComms[invalidIdx] = invalidPoint;
        vm.expectRevert(INVALID_G1_POINT);
        VerifierCore.verify(proof, publicInputs, vk);
        proof.quotientComms[invalidIdx] = validPoint; // Reset

        // Test Case 4: Invalid w_zeta
        invalidIdx = randomUint(NUM_WIRE_TYPES);
        proof.wZeta = invalidPoint;
        vm.expectRevert(INVALID_G1_POINT);
        VerifierCore.verify(proof, publicInputs, vk);
        proof.wZeta = validPoint; // Reset

        // Test Case 5: Invalid wZetaOmega
        invalidIdx = randomUint(NUM_WIRE_TYPES);
        proof.wZetaOmega = invalidPoint;
        vm.expectRevert(INVALID_G1_POINT);
        VerifierCore.verify(proof, publicInputs, vk);
        proof.wZetaOmega = validPoint; // Reset

        // Test Case 6: Invalid wire evaluation
        invalidIdx = randomUint(NUM_WIRE_TYPES);
        proof.wireEvals[invalidIdx] = invalidScalar;
        vm.expectRevert(INVALID_SCALAR);
        VerifierCore.verify(proof, publicInputs, vk);
        proof.wireEvals[invalidIdx] = validScalar; // Reset

        // Test Case 7: Invalid sigma evaluation
        invalidIdx = randomUint(NUM_WIRE_TYPES - 1);
        proof.sigmaEvals[invalidIdx] = invalidScalar;
        vm.expectRevert(INVALID_SCALAR);
        VerifierCore.verify(proof, publicInputs, vk);
        proof.sigmaEvals[invalidIdx] = validScalar; // Reset

        // Test Case 8: Invalid zBar
        invalidIdx = randomUint(NUM_WIRE_TYPES);
        proof.zBar = invalidScalar;
        vm.expectRevert(INVALID_SCALAR);
        VerifierCore.verify(proof, publicInputs, vk);
        proof.zBar = validScalar; // Reset
    }

    /// @notice Test that the verifier properly validates public inputs in step 3 of Plonk verification
    function testInvalidPublicInputs() public {
        // Create a valid scalar and EC point to use as a base
        BN254.G1Point memory validPoint = BN254.P1();
        BN254.ScalarField validScalar = BN254.ScalarField.wrap(1);
        BN254.ScalarField invalidScalar = BN254.ScalarField.wrap(BN254.R_MOD);

        // Create fixed-size arrays for a valid proof
        BN254.G1Point[NUM_WIRE_TYPES] memory wireComms;
        BN254.G1Point[NUM_WIRE_TYPES] memory quotientComms;
        BN254.ScalarField[NUM_WIRE_TYPES] memory wireEvals;
        BN254.ScalarField[NUM_WIRE_TYPES - 1] memory sigmaEvals;

        // Fill arrays with valid values
        for (uint256 i = 0; i < NUM_WIRE_TYPES; i++) {
            wireComms[i] = validPoint;
            quotientComms[i] = validPoint;
            wireEvals[i] = validScalar;
            if (i < NUM_WIRE_TYPES - 1) {
                sigmaEvals[i] = validScalar;
            }
        }

        // Create a valid proof
        PlonkProof memory proof = PlonkProof({
            wireComms: wireComms,
            zComm: validPoint,
            quotientComms: quotientComms,
            wZeta: validPoint,
            wZetaOmega: validPoint,
            wireEvals: wireEvals,
            sigmaEvals: sigmaEvals,
            zBar: validScalar
        });

        // Create a mock verification key
        VerificationKey memory vk = createMockVerificationKey();
        uint256 numPublicInputs = vk.l;

        // Test Case: Invalid public input
        BN254.ScalarField[] memory publicInputs = new BN254.ScalarField[](numPublicInputs);
        for (uint256 i = 0; i < numPublicInputs; i++) {
            publicInputs[i] = validScalar;
        }

        // Try a random position with an invalid scalar
        uint256 invalidIdx = randomUint(numPublicInputs);
        publicInputs[invalidIdx] = invalidScalar;
        vm.expectRevert(INVALID_SCALAR);
        VerifierCore.verify(proof, publicInputs, vk);
    }

    /// @notice Test that a valid proof passes steps 1-3 of Plonk verification
    function testDummyProof() public view {
        // Create a valid scalar and EC point to use as a base
        BN254.G1Point memory validPoint = BN254.P1();
        BN254.ScalarField validScalar = BN254.ScalarField.wrap(1);

        // Create fixed-size arrays for a valid proof
        BN254.G1Point[NUM_WIRE_TYPES] memory wireComms;
        BN254.G1Point[NUM_WIRE_TYPES] memory quotientComms;
        BN254.ScalarField[NUM_WIRE_TYPES] memory wireEvals;
        BN254.ScalarField[NUM_WIRE_TYPES - 1] memory sigmaEvals;

        // Fill arrays with valid values
        for (uint256 i = 0; i < NUM_WIRE_TYPES; i++) {
            wireComms[i] = validPoint;
            quotientComms[i] = validPoint;
            wireEvals[i] = validScalar;
            if (i < NUM_WIRE_TYPES - 1) {
                sigmaEvals[i] = validScalar;
            }
        }

        // Create a valid proof
        PlonkProof memory proof = PlonkProof({
            wireComms: wireComms,
            zComm: validPoint,
            quotientComms: quotientComms,
            wZeta: validPoint,
            wZetaOmega: validPoint,
            wireEvals: wireEvals,
            sigmaEvals: sigmaEvals,
            zBar: validScalar
        });

        // Create a mock verification key
        VerificationKey memory vk = createMockVerificationKey();

        // Create a valid public input
        BN254.ScalarField[] memory publicInputs = new BN254.ScalarField[](vk.l);
        for (uint256 i = 0; i < vk.l; i++) {
            publicInputs[i] = validScalar;
        }

        // This should not revert since we're using valid inputs
        bool res = VerifierCore.verify(proof, publicInputs, vk);
        require(!res, "Proof verification should have failed");
    }

    /// @notice Test a modified proof that should fail verification
    function testModifiedProof() public {
        // First generate the verification key for the circuit
        compileRustBinary("test/rust-reference-impls/verifier/Cargo.toml");
        VerificationKey memory vkey = getMulTwoVkey();

        // Create a proof for the mul-two circuit
        uint256 a = randomFelt();
        uint256 b = randomFelt();
        (uint256 c, PlonkProof memory originalProof) = getMulTwoProof(a, b);

        // Create the public inputs array once
        BN254.ScalarField[] memory publicInputs = new BN254.ScalarField[](1);
        publicInputs[0] = BN254.ScalarField.wrap(c);

        BN254.G1Point memory dummyG1Point = BN254.P1();
        BN254.ScalarField dummyScalar = BN254.ScalarField.wrap(1);

        bool res;

        // Test Case 1: Modify a wire commitment
        {
            uint256 randomIdx = randomUint(NUM_WIRE_TYPES);
            PlonkProof memory proof = clonePlonkProof(originalProof);
            proof.wireComms[randomIdx] = dummyG1Point;
            res = VerifierCore.verify(proof, publicInputs, vkey);
            require(!res, "Proof verification should have failed");
        }

        // Test Case 2: Modify zComm
        {
            PlonkProof memory proof = clonePlonkProof(originalProof);
            proof.zComm = dummyG1Point;
            res = VerifierCore.verify(proof, publicInputs, vkey);
            require(!res, "Proof verification should have failed");
        }

        // Test Case 3: Modify a quotient commitment
        {
            uint256 randomIdx = randomUint(NUM_WIRE_TYPES);
            PlonkProof memory proof = clonePlonkProof(originalProof);
            proof.quotientComms[randomIdx] = dummyG1Point;
            res = VerifierCore.verify(proof, publicInputs, vkey);
            require(!res, "Proof verification should have failed");
        }

        // Test Case 4: Modify wZeta
        {
            PlonkProof memory proof = clonePlonkProof(originalProof);
            proof.wZeta = dummyG1Point;
            res = VerifierCore.verify(proof, publicInputs, vkey);
            require(!res, "Proof verification should have failed");
        }

        // Test Case 5: Modify wZetaOmega
        {
            PlonkProof memory proof = clonePlonkProof(originalProof);
            proof.wZetaOmega = dummyG1Point;
            res = VerifierCore.verify(proof, publicInputs, vkey);
            require(!res, "Proof verification should have failed");
        }

        // Test Case 6: Modify a wire evaluation
        {
            uint256 randomIdx = randomUint(NUM_WIRE_TYPES);
            PlonkProof memory proof = clonePlonkProof(originalProof);
            proof.wireEvals[randomIdx] = dummyScalar;
            res = VerifierCore.verify(proof, publicInputs, vkey);
            require(!res, "Proof verification should have failed");
        }

        // Test Case 7: Modify a sigma evaluation
        {
            uint256 randomIdx = randomUint(NUM_WIRE_TYPES - 1);
            PlonkProof memory proof = clonePlonkProof(originalProof);
            proof.sigmaEvals[randomIdx] = dummyScalar;
            res = VerifierCore.verify(proof, publicInputs, vkey);
            require(!res, "Proof verification should have failed");
        }

        // Test Case 8: Modify zBar
        {
            PlonkProof memory proof = clonePlonkProof(originalProof);
            proof.zBar = dummyScalar;
            res = VerifierCore.verify(proof, publicInputs, vkey);
            require(!res, "Proof verification should have failed");
        }

        // Verify the original proof still works
        res = VerifierCore.verify(originalProof, publicInputs, vkey);
        require(res, "Original proof verification should have succeeded");
    }

    /// @notice Test that batch verification fails if any proof in the batch is invalid
    function testInvalidBatchVerification() public {
        // First generate the verification keys for the circuits
        compileRustBinary("test/rust-reference-impls/verifier/Cargo.toml");

        // Generate batch test data
        (PlonkProof[] memory proofs, BN254.ScalarField[][] memory publicInputs, VerificationKey[] memory vks) =
            generateBatchProofData();

        // Randomly select a proof to modify
        uint256 proofToModify = randomUint(proofs.length);
        PlonkProof memory invalidProof = clonePlonkProof(proofs[proofToModify]);

        // Randomly select which part of the proof to modify
        uint256 modType = randomUint(8);
        BN254.G1Point memory dummyG1Point = BN254.P1();
        BN254.ScalarField dummyScalar = BN254.ScalarField.wrap(1);

        if (modType == 0) {
            // Modify a wire commitment
            uint256 randomIdx = randomUint(NUM_WIRE_TYPES);
            invalidProof.wireComms[randomIdx] = dummyG1Point;
        } else if (modType == 1) {
            // Modify zComm
            invalidProof.zComm = dummyG1Point;
        } else if (modType == 2) {
            // Modify a quotient commitment
            uint256 randomIdx = randomUint(NUM_WIRE_TYPES);
            invalidProof.quotientComms[randomIdx] = dummyG1Point;
        } else if (modType == 3) {
            // Modify wZeta
            invalidProof.wZeta = dummyG1Point;
        } else if (modType == 4) {
            // Modify wZetaOmega
            invalidProof.wZetaOmega = dummyG1Point;
        } else if (modType == 5) {
            // Modify a wire evaluation
            uint256 randomIdx = randomUint(NUM_WIRE_TYPES);
            invalidProof.wireEvals[randomIdx] = dummyScalar;
        } else if (modType == 6) {
            // Modify a sigma evaluation
            uint256 randomIdx = randomUint(NUM_WIRE_TYPES - 1);
            invalidProof.sigmaEvals[randomIdx] = dummyScalar;
        } else {
            // Modify zBar
            invalidProof.zBar = dummyScalar;
        }

        // Replace the selected proof with the invalid one
        proofs[proofToModify] = invalidProof;

        // Verify the batch - should fail
        OpeningElements memory extraOpeningElements = emptyOpeningElements();
        bool res = VerifierCore.batchVerify(proofs, publicInputs, vks, extraOpeningElements);
        require(!res, "Proof verification should have failed");
    }

    /// @notice Test the case in which a public input is modified
    function testModifiedPublicInput() public {
        // First generate the verification keys for the circuits
        compileRustBinary("test/rust-reference-impls/verifier/Cargo.toml");
        VerificationKey memory vkey = getPermutationVkey();

        // Generate data for the permutation circuit
        uint256 randomChallenge = randomFelt();
        uint256[5] memory statement;
        uint256[5] memory witness;
        for (uint256 i = 0; i < 5; i++) {
            statement[i] = randomFelt();
            witness[5 - i - 1] = statement[i];
        }

        // Get the proof and public input
        PlonkProof memory proof = getPermutationProof(randomChallenge, statement, witness);

        // Verify the proof
        BN254.ScalarField[] memory publicInputs = new BN254.ScalarField[](6);
        publicInputs[0] = BN254.ScalarField.wrap(randomChallenge);
        for (uint256 i = 0; i < 5; i++) {
            publicInputs[i + 1] = BN254.ScalarField.wrap(statement[i]);
        }

        // Modify the public input
        uint256 randomIdx = randomUint(publicInputs.length);
        publicInputs[randomIdx] = BN254.ScalarField.wrap(randomFelt());

        // Verify the proof
        bool res = VerifierCore.verify(proof, publicInputs, vkey);
        require(!res, "Proof verification should have failed");
    }

    /// @notice Test the verifier against an invalid proof-linking relation
    function testInvalidProofLinking() public {
        // First generate the verification keys for the circuits
        compileRustBinary("test/rust-reference-impls/verifier/Cargo.toml");

        // Generate the inputs
        uint256[5] memory sharedInputs;
        uint256 sumPrivateInput = randomFelt();
        uint256 productPrivateInput = randomFelt();
        for (uint256 i = 0; i < 5; i++) {
            sharedInputs[i] = randomFelt();
        }

        // Generate the proofs and proof linking argument
        (
            PlonkProof[] memory proofs,
            BN254.ScalarField[][] memory publicInputs,
            VerificationKey[] memory vks,
            ProofLinkingInstance memory linkArg
        ) = getSumProductProofsAndLinkingArgument(sharedInputs, sumPrivateInput, productPrivateInput);

        uint256 modType = randomUint(4);
        BN254.G1Point memory dummyG1Point = randomG1Point();
        if (modType == 0) {
            // Modify the first wire commitment
            linkArg.wireComm0 = dummyG1Point;
        } else if (modType == 1) {
            // Modify the second wire commitment
            linkArg.wireComm1 = dummyG1Point;
        } else if (modType == 2) {
            // Modify the proof linking relation
            linkArg.proof.linkingQuotientPolyComm = dummyG1Point;
        } else {
            // Modify the proof linking relation verification key
            linkArg.proof.linkingPolyOpening = dummyG1Point;
        }

        // Assert that verification fails
        ProofLinkingInstance[] memory linkArgs = new ProofLinkingInstance[](1);
        linkArgs[0] = linkArg;
        OpeningElements memory linkOpeningElements = ProofLinkingCore.createOpeningElements(linkArgs);
        bool res = VerifierCore.batchVerify(proofs, publicInputs, vks, linkOpeningElements);
        require(!res, "Proof verification should have failed");
    }

    // --- Valid Test Cases --- //

    /// @notice Test the verifier against a reference implementation on the mul-two circuit
    function testVerifierMulTwo() public {
        // First generate the verification key for the circuit
        compileRustBinary("test/rust-reference-impls/verifier/Cargo.toml");
        VerificationKey memory vkey = getMulTwoVkey();

        // Generate two random inputs and prove their product
        uint256 a = randomFelt();
        uint256 b = randomFelt();
        (uint256 c, PlonkProof memory proof) = getMulTwoProof(a, b);

        // Verify the proof
        BN254.ScalarField[] memory publicInputs = new BN254.ScalarField[](1);
        publicInputs[0] = BN254.ScalarField.wrap(c);
        bool res = VerifierCore.verify(proof, publicInputs, vkey);
        require(res, "Proof verification should have succeeded");
    }

    /// @notice Test the verifier against a reference implementation on the sum-pow circuit
    function testVerifierSumPow() public {
        uint256 numInputs = 10;

        // First generate the verification key for the circuit
        compileRustBinary("test/rust-reference-impls/verifier/Cargo.toml");
        VerificationKey memory vkey = getSumPowVkey();

        // Generate ten random inputs
        uint256[10] memory inputs;
        for (uint256 i = 0; i < numInputs; i++) {
            inputs[i] = randomFelt();
        }

        // Get the proof and public input
        (BN254.ScalarField sumPow, PlonkProof memory proof) = getSumPowProof(inputs);

        // Verify the proof
        BN254.ScalarField[] memory publicInputs = new BN254.ScalarField[](1);
        publicInputs[0] = sumPow;
        bool res = VerifierCore.verify(proof, publicInputs, vkey);
        require(res, "Proof verification should have succeeded");
    }

    /// @notice Test the verifier against a reference implementation on the permutation circuit
    function testVerifierPermutation() public {
        uint256 N = 5;
        // First generate the verification key for the circuit
        compileRustBinary("test/rust-reference-impls/verifier/Cargo.toml");
        VerificationKey memory vkey = getPermutationVkey();

        // Generate a random statement and witness
        uint256[5] memory statement;
        uint256[5] memory witness;
        for (uint256 i = 0; i < N; i++) {
            uint256 val = randomFelt();
            statement[i] = val;
            witness[N - i - 1] = val; // A simple reverse permutation
        }

        // Get the proof
        uint256 randomChallenge = randomFelt();
        PlonkProof memory proof = getPermutationProof(randomChallenge, statement, witness);

        // Verify the proof
        BN254.ScalarField[] memory publicInputs = new BN254.ScalarField[](N + 1);
        publicInputs[0] = BN254.ScalarField.wrap(randomChallenge);
        for (uint256 i = 0; i < N; i++) {
            publicInputs[i + 1] = BN254.ScalarField.wrap(statement[i]);
        }

        bool res = VerifierCore.verify(proof, publicInputs, vkey);
        require(res, "Proof verification should have succeeded");
    }

    /// @notice Test batch verification against all three circuits
    function testBatchVerification() public {
        // First generate the verification keys for the circuits
        compileRustBinary("test/rust-reference-impls/verifier/Cargo.toml");

        // Generate batch test data
        (PlonkProof[] memory proofs, BN254.ScalarField[][] memory publicInputs, VerificationKey[] memory vks) =
            generateBatchProofData();

        // Verify the batch
        OpeningElements memory extraOpeningElements = emptyOpeningElements();
        bool res = VerifierCore.batchVerify(proofs, publicInputs, vks, extraOpeningElements);
        require(res, "Proof verification should have succeeded");
    }

    /// --- Proof Linking Test Cases --- ///

    /// @notice Test the verifier on a proof-linking relation in addition to the sum and product circuits
    function testSumProductProofLinking() public {
        // First generate the verification keys for the circuits
        compileRustBinary("test/rust-reference-impls/verifier/Cargo.toml");

        // Generate the inputs
        uint256[5] memory sharedInputs;
        uint256 sumPrivateInput = randomFelt();
        uint256 productPrivateInput = randomFelt();
        for (uint256 i = 0; i < 5; i++) {
            sharedInputs[i] = randomFelt();
        }

        // Generate the proofs and proof linking argument
        (
            PlonkProof[] memory proofs,
            BN254.ScalarField[][] memory publicInputs,
            VerificationKey[] memory vks,
            ProofLinkingInstance memory linkArg
        ) = getSumProductProofsAndLinkingArgument(sharedInputs, sumPrivateInput, productPrivateInput);

        // Create extra opening elements for the proof linking relation
        ProofLinkingInstance[] memory linkArgs = new ProofLinkingInstance[](1);
        linkArgs[0] = linkArg;
        OpeningElements memory linkingOpeningElements = ProofLinkingCore.createOpeningElements(linkArgs);

        // Verify the proofs with the extra opening elements
        bool res = VerifierCore.batchVerify(proofs, publicInputs, vks, linkingOpeningElements);
        require(res, "Proof verification should have succeeded");
    }
}

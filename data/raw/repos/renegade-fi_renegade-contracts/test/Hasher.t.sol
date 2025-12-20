// SPDX-License-Identifier: UNLICENSED
// solhint-disable func-name-mixedcase
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { HuffDeployer } from "foundry-huff/HuffDeployer.sol";
import { TestUtils } from "./utils/TestUtils.sol";
import { IHasher } from "renegade-lib/interfaces/IHasher.sol";
import { MerkleTreeLib } from "renegade-lib/merkle/MerkleTree.sol";
import { MerkleZeros } from "renegade-lib/merkle/MerkleZeros.sol";

contract HasherTest is TestUtils {
    using MerkleTreeLib for MerkleTreeLib.MerkleTree;

    /// @dev The Merkle depth
    uint256 public merkleDepth;

    /// @dev The MerklePoseidon contract
    IHasher public hasher;
    MerkleTreeLib.MerkleTree private tree;

    /// @dev Deploy the MerklePoseidon contract
    function setUp() public virtual {
        // Sample a Merkle tree depth to test with
        merkleDepth = randomUint(10, 32);

        hasher = IHasher(HuffDeployer.deploy("libraries/poseidon2/poseidonHasher"));
        MerkleTreeLib.MerkleTreeConfig memory config =
            MerkleTreeLib.MerkleTreeConfig({ storeRoots: true, depth: merkleDepth });
        tree.initialize(config);
    }

    // --- Hasher Contract Tests --- //

    /// @dev Test the hashMerkle function with sequential inserts
    function test_HashMerkle() public {
        uint256 input = randomFelt();
        uint256 idx = randomIdx();
        uint256[] memory sisterLeaves = new uint256[](merkleDepth);
        for (uint256 i = 0; i < merkleDepth; i++) {
            sisterLeaves[i] = randomFelt();
        }
        uint256[] memory results = hasher.merkleHash(idx, input, sisterLeaves);
        assertEq(results.length, merkleDepth + 1, "Expected 32 results");
        uint256[] memory expected = runMerkleReferenceImpl(merkleDepth, idx, input, sisterLeaves);
        assertEq(results[0], input);

        for (uint256 i = 0; i < merkleDepth; i++) {
            assertEq(results[i + 1], expected[i], string(abi.encodePacked("Result mismatch at index ", vm.toString(i))));
        }
    }

    /// @dev Test the spongeHash function
    function test_SpongeHash() public {
        uint256 n = randomUint(1, 10);
        uint256[] memory inputs = new uint256[](n);
        for (uint256 i = 0; i < n; i++) {
            inputs[i] = randomFelt();
        }

        uint256 expected = runSpongeHashReferenceImpl(inputs);
        uint256 result = hasher.spongeHash(inputs);
        assertEq(result, expected, "Sponge hash result does not match reference implementation");
    }

    // --- Resumable Commitment Tests --- //

    /// @dev Test the resumable commitment function with empty inputs array
    function test_ComputeResumableCommitmentEmpty() public {
        uint256[] memory inputs = new uint256[](0);

        uint256 result = hasher.computeResumableCommitment(inputs);
        assertEq(result, 0, "Resumable commitment with empty inputs should return 0");
    }

    /// @dev Test the resumable commitment function with single input
    function test_ComputeResumableCommitmentSingle() public {
        uint256[] memory inputs = new uint256[](1);
        inputs[0] = randomFelt();

        uint256 result = hasher.computeResumableCommitment(inputs);
        uint256 expected = inputs[0];

        assertEq(result, expected, "Resumable commitment with single input does not match expected");
    }

    /// @dev Test the resumable commitment function
    function test_ComputeResumableCommitment() public {
        uint256 nInputs = randomUint(1, 20);
        uint256[] memory inputs = new uint256[](nInputs);
        for (uint256 i = 0; i < nInputs; ++i) {
            inputs[i] = randomFelt();
        }

        uint256 result = hasher.computeResumableCommitment(inputs);

        // Compute the expected result manually
        uint256 expected = inputs[0];
        for (uint256 i = 1; i < inputs.length; ++i) {
            expected = _hashTwo(expected, inputs[i]);
        }

        assertEq(result, expected, "Resumable commitment result does not match expected");
    }

    // --- Merkle Tree Tests --- //

    /// @notice Test that the root and root history are initialized correctly
    function test_rootAfterInitialization() public view {
        // Test that the root is the default zero valued root
        uint256 expectedRoot = MerkleZeros.getZeroValue(merkleDepth);
        uint256 actualRoot = BN254.ScalarField.unwrap(tree.getRoot());
        assertEq(actualRoot, expectedRoot);

        // Test that the zero valued root is in the history
        BN254.ScalarField rootScalar = BN254.ScalarField.wrap(expectedRoot);
        bool expectedInHistory = tree.rootInHistory(rootScalar);
        assertEq(expectedInHistory, true);
    }

    /// @notice Test that the zero valued leaf hashes to the zero valued root
    function test_zeroValueLeafMerkleHash() public view {
        uint256 root = BN254.ScalarField.unwrap(tree.getRoot());

        uint256 currLeaf = MerkleZeros.getZeroValue(0);
        for (uint256 i = 0; i < merkleDepth; i++) {
            uint256[] memory inputs = new uint256[](2);
            inputs[0] = currLeaf;
            inputs[1] = currLeaf;
            currLeaf = hasher.spongeHash(inputs);
        }

        assertEq(currLeaf, root);
    }

    /// @notice Test the root after inserting a leaf
    function test_rootAfterMultiInsert() public {
        uint256 nInserts = randomUint(1, 20);
        uint256[] memory inputs = new uint256[](nInserts);
        for (uint256 i = 0; i < nInserts; i++) {
            inputs[i] = randomFelt();
        }

        // Run the reference implementation
        uint256 expectedRoot = runMerkleRootReferenceImpl(merkleDepth, inputs);

        // Insert into the solidity Merkle tree
        for (uint256 i = 0; i < nInserts; i++) {
            tree.insertLeaf(BN254.ScalarField.wrap(inputs[i]), hasher);
        }

        // Compare the roots
        uint256 actualRoot = BN254.ScalarField.unwrap(tree.getRoot());
        assertEq(actualRoot, expectedRoot);

        // Check the next index on the tree
        assertEq(tree.nextIndex, nInserts);
    }

    /// @notice Test the sibling path after a number of inserts
    /// @dev This is effectively testing the consistency of the sibling path across successive insertions
    function test_siblingPathAfterMultiInsert() public {
        uint256 nInserts = randomUint(1, 20);
        uint256[] memory inputs = new uint256[](nInserts);
        for (uint256 i = 0; i < nInserts; i++) {
            inputs[i] = randomFelt();
        }

        // Insert into the solidity Merkle tree
        for (uint256 i = 0; i < nInserts; i++) {
            tree.insertLeaf(BN254.ScalarField.wrap(inputs[i]), hasher);
        }

        // Now fetch the sibling path, this will be the opening for the next insert
        uint256[] memory siblingPath = new uint256[](merkleDepth);
        for (uint256 i = 0; i < merkleDepth; i++) {
            siblingPath[i] = BN254.ScalarField.unwrap(tree.siblingPath[i]);
        }

        // Insert one more leaf into the tree
        uint256 nextInput = randomFelt();
        tree.insertLeaf(BN254.ScalarField.wrap(nextInput), hasher);

        // Check that the sibling path from the previous insert opens the new leaf to the current root
        uint256 idx = nInserts;
        uint256 expectedRoot = BN254.ScalarField.unwrap(tree.getRoot());
        uint256 openedRoot = nextInput;
        for (uint256 i = 0; i < merkleDepth; i++) {
            uint256[] memory hashTwoInputs = new uint256[](2);
            uint256 ithBit = (idx >> i) & 1;
            if (ithBit == 0) {
                // Left child
                hashTwoInputs[0] = openedRoot;
                hashTwoInputs[1] = siblingPath[i];
            } else {
                // Right child
                hashTwoInputs[0] = siblingPath[i];
                hashTwoInputs[1] = openedRoot;
            }
            openedRoot = hasher.spongeHash(hashTwoInputs);
        }

        assertEq(openedRoot, expectedRoot);
    }

    // --- Helpers --- //

    /// @dev Generate a random index in the Merkle tree
    function randomIdx() internal returns (uint256) {
        return vm.randomUint() % (2 ** merkleDepth);
    }

    /// @dev Helper to run the sponge hash reference implementation
    function runSpongeHashReferenceImpl(uint256[] memory inputs) internal returns (uint256) {
        // First compile the binary
        compileRustBinary("test/rust-reference-impls/merkle/Cargo.toml");

        // Prepare arguments for the binary
        string[] memory args = new string[](inputs.length + 2);
        args[0] = "./test/rust-reference-impls/target/debug/merkle";
        args[1] = "sponge-hash";

        // Pass inputs as space-separated arguments
        for (uint256 i = 0; i < inputs.length; i++) {
            args[i + 2] = vm.toString(inputs[i]);
        }

        // Run binary and parse space-separated array output
        return vm.parseUint(runBinaryGetResponse(args));
    }

    /// @dev Helper to run the reference implementation
    function runMerkleReferenceImpl(
        uint256 depth,
        uint256 idx,
        uint256 input,
        uint256[] memory sisterLeaves
    )
        internal
        returns (uint256[] memory)
    {
        // First compile the binary
        compileRustBinary("test/rust-reference-impls/merkle/Cargo.toml");

        // Prepare arguments for the binary
        uint256 argsLength = 5 + depth; // program name + command + depth + idx + input + depth sister nodes
        string[] memory args = new string[](argsLength);
        args[0] = "./test/rust-reference-impls/target/debug/merkle";
        args[1] = "merkle-hash";
        args[2] = vm.toString(depth);
        args[3] = vm.toString(idx);
        args[4] = vm.toString(input);

        // Pass sister leaves as individual arguments
        for (uint256 i = 0; i < merkleDepth; i++) {
            args[i + 5] = vm.toString(sisterLeaves[i]);
        }

        // Run binary and parse space-separated array output
        uint256[] memory result = runBinaryGetArray(args, " ");
        require(result.length == depth, "Expected depth values");
        return result;
    }

    /// @dev Helper to run the Merkle root reference implementation
    function runMerkleRootReferenceImpl(uint256 depth, uint256[] memory inputs) internal returns (uint256) {
        // First compile the binary
        compileRustBinary("test/rust-reference-impls/merkle/Cargo.toml");

        // Prepare arguments for the binary
        string[] memory args = new string[](inputs.length + 3);
        args[0] = "./test/rust-reference-impls/target/debug/merkle";
        args[1] = "insert-and-get-root";
        args[2] = vm.toString(depth);

        // Pass sister leaves as individual arguments
        for (uint256 i = 0; i < inputs.length; i++) {
            args[i + 3] = vm.toString(inputs[i]);
        }

        // Run binary and parse space-separated array output
        return vm.parseUint(runBinaryGetResponse(args));
    }

    /// @dev Hash two inputs using Poseidon two-to-one hash
    function _hashTwo(uint256 a, uint256 b) internal view returns (uint256) {
        uint256[] memory inputs = new uint256[](2);
        inputs[0] = a;
        inputs[1] = b;
        return hasher.spongeHash(inputs);
    }
}

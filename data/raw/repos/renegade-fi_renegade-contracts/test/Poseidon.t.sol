// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { HuffDeployer } from "foundry-huff/HuffDeployer.sol";
import { TestUtils } from "./utils/TestUtils.sol";

contract PoseidonTest is TestUtils {
    /// @dev The Poseidon main contract
    PoseidonSuite public poseidonSuite;

    /// @dev The round constant used in testing
    uint256 _testRc1 = 0x1337;
    /// @dev The second round constant used in testing
    uint256 _testRc2 = 0x1338;
    /// @dev The third round constant used in testing
    uint256 _testRc3 = 0x1339;

    /// @dev Deploy the PoseidonSuite contract
    function setUp() public {
        poseidonSuite = PoseidonSuite(HuffDeployer.deploy("../test/huff/testPoseidonUtils"));
    }

    /// @dev Test the sbox function applied to a single input
    function testSboxSingle() public {
        uint256 testValue = randomFelt();
        uint256 result = poseidonSuite.testSboxSingle(testValue);

        // Calculate expected x^5 mod p
        uint256 expected = _fifthPower(testValue);
        assertEq(result, expected, "Expected result to match x^5 mod p");
    }

    /// @dev Test the add round constant function applied to a single input
    function testAddRcSingle() public {
        uint256 testValue = randomFelt();
        uint256 result = poseidonSuite.testAddRc(testValue);
        uint256 expected = addmod(testValue, _testRc1, PRIME);
        assertEq(result, expected, "Expected result to match x + RC mod p");
    }

    /// @dev Test the internal MDS function applied to a single input
    /// The internal MDS adds the sum of the elements to each element
    function testInternalMds() public {
        uint256 a = randomFelt();
        uint256 b = randomFelt();
        uint256 c = randomFelt();
        (uint256 a1, uint256 b1, uint256 c1) = poseidonSuite.testInternalMds(a, b, c);

        // Calculate the expected results
        (uint256 expectedA, uint256 expectedB, uint256 expectedC) = _internalMds(a, b, c);
        assertEq(a1, expectedA, "Expected result to match a + sum mod p");
        assertEq(b1, expectedB, "Expected result to match b + sum mod p");
        assertEq(c1, expectedC, "Expected result to match c + sum mod p");
    }

    /// @dev Test the external MDS function applied to a trio of inputs
    function testExternalMds() public {
        uint256 a = randomFelt();
        uint256 b = randomFelt();
        uint256 c = randomFelt();
        (uint256 a1, uint256 b1, uint256 c1) = poseidonSuite.testExternalMds(a, b, c);

        // Calculate the expected results
        (uint256 expectedA, uint256 expectedB, uint256 expectedC) = _externalMds(a, b, c);
        assertEq(a1, expectedA, "Expected result to match a");
        assertEq(b1, expectedB, "Expected result to match b");
        assertEq(c1, expectedC, "Expected result to match c");
    }

    /// @dev Test the external round function applied to a trio of inputs
    function testExternalRound() public {
        uint256 a = randomFelt();
        uint256 b = randomFelt();
        uint256 c = randomFelt();
        (uint256 a1, uint256 b1, uint256 c1) = poseidonSuite.testExternalRound(a, b, c);
        (uint256 expectedA, uint256 expectedB, uint256 expectedC) = _externalRound(a, b, c);
        assertEq(a1, expectedA, "Expected result to match a");
        assertEq(b1, expectedB, "Expected result to match b");
        assertEq(c1, expectedC, "Expected result to match c");
    }

    /// @dev Test the internal round function applied to a trio of inputs
    function testInternalRound() public {
        uint256 a = randomFelt();
        uint256 b = randomFelt();
        uint256 c = randomFelt();
        (uint256 a1, uint256 b1, uint256 c1) = poseidonSuite.testInternalRound(a, b, c);
        (uint256 expectedA, uint256 expectedB, uint256 expectedC) = _internalRound(a, b, c);
        assertEq(a1, expectedA, "Expected result to match a");
        assertEq(b1, expectedB, "Expected result to match b");
        assertEq(c1, expectedC, "Expected result to match c");
    }

    /// @dev Test the full hash function applied to two inputs
    function testFullHash() public {
        uint256 a = randomFelt();
        uint256 b = randomFelt();

        uint256 result = poseidonSuite.testFullHash(a, b);
        uint256 expected = _runReferenceImpl(a, b);
        assertEq(result, expected, "Hash result does not match reference implementation");
    }

    /// @dev Helper to run the reference implementation
    function _runReferenceImpl(uint256 a, uint256 b) internal returns (uint256) {
        // First compile the binary
        compileRustBinary("test/rust-reference-impls/poseidon/Cargo.toml");

        // Now run the binary directly from target/debug
        string[] memory runInputs = new string[](3);
        runInputs[0] = "./test/rust-reference-impls/target/debug/poseidon";
        runInputs[1] = vm.toString(a);
        runInputs[2] = vm.toString(b);

        // Run and parse result
        return vm.parseUint(runBinaryGetResponse(runInputs));
    }

    /// --- Helpers --- ///

    /// @dev Calculate the fifth power of an input
    function _fifthPower(uint256 x) internal pure returns (uint256) {
        uint256 x2 = mulmod(x, x, PRIME);
        uint256 x4 = mulmod(x2, x2, PRIME);
        return mulmod(x, x4, PRIME);
    }

    /// @dev Calculate the result of the internal MDS matrix applied to the inputs
    function _internalMds(uint256 a, uint256 b, uint256 c) internal pure returns (uint256, uint256, uint256) {
        uint256 sum = _sumInputs(a, b, c);
        uint256 a1 = addmod(a, sum, PRIME);
        uint256 b1 = addmod(b, sum, PRIME);
        uint256 c1 = addmod(addmod(c, sum, PRIME), c, PRIME); // c is doubled
        return (a1, b1, c1);
    }

    /// @dev Calculate the result of the external MDS matrix applied to the inputs
    function _externalMds(uint256 a, uint256 b, uint256 c) internal pure returns (uint256, uint256, uint256) {
        uint256 sum = _sumInputs(a, b, c);
        uint256 a1 = addmod(a, sum, PRIME);
        uint256 b1 = addmod(b, sum, PRIME);
        uint256 c1 = addmod(c, sum, PRIME);
        return (a1, b1, c1);
    }

    /// @dev Calculate the result of the external round function applied to the inputs
    function _externalRound(uint256 a, uint256 b, uint256 c) internal view returns (uint256, uint256, uint256) {
        uint256 a1 = addmod(a, _testRc1, PRIME);
        uint256 b1 = addmod(b, _testRc2, PRIME);
        uint256 c1 = addmod(c, _testRc3, PRIME);
        uint256 a2 = _fifthPower(a1);
        uint256 b2 = _fifthPower(b1);
        uint256 c2 = _fifthPower(c1);
        return _externalMds(a2, b2, c2);
    }

    /// @dev Calculate the result of the internal round function applied to the inputs
    function _internalRound(uint256 a, uint256 b, uint256 c) internal view returns (uint256, uint256, uint256) {
        uint256 a1 = addmod(a, _testRc1, PRIME);
        uint256 a2 = _fifthPower(a1);
        return _internalMds(a2, b, c);
    }

    /// @dev Sum the inputs and return the result
    function _sumInputs(uint256 a, uint256 b, uint256 c) internal pure returns (uint256) {
        uint256 sum = addmod(a, b, PRIME);
        sum = addmod(sum, c, PRIME);
        return sum;
    }
}

interface PoseidonSuite {
    function testSboxSingle(uint256) external returns (uint256);
    function testAddRc(uint256) external returns (uint256);
    function testInternalMds(uint256, uint256, uint256) external returns (uint256, uint256, uint256);
    function testExternalMds(uint256, uint256, uint256) external returns (uint256, uint256, uint256);
    function testExternalRound(uint256, uint256, uint256) external returns (uint256, uint256, uint256);
    function testInternalRound(uint256, uint256, uint256) external returns (uint256, uint256, uint256);
    function testFullHash(uint256, uint256) external returns (uint256);
}

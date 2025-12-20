// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import { Test } from "forge-std/Test.sol";
import { Vm } from "forge-std/Vm.sol";
import { BN254 } from "lib/solidity-bn254/src/BN254.sol";
import { DarkpoolConstants } from "darkpoolv1-lib/Constants.sol";

contract TestUtils is Test {
    /// @dev The BN254 field modulus from roundUtils.huff
    uint256 constant PRIME = BN254.R_MOD;
    /// @dev The scalar field modulus for K256
    uint256 constant K256_SCALAR_MOD = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141;

    // --- Assertions --- //

    /// @dev Assert that two BN254 scalar fields are equal
    function assertEq(BN254.ScalarField a, BN254.ScalarField b) internal pure {
        assertEq(BN254.ScalarField.unwrap(a), BN254.ScalarField.unwrap(b));
    }

    // --- Fuzzing Helpers --- //

    /// @dev Generates a random byte
    function randomByte() internal returns (bytes1) {
        return bytes1(uint8(randomFelt() % 256));
    }

    /// @dev Generates a random input modulo the PRIME
    function randomFelt() internal returns (uint256) {
        return vm.randomUint(0, BN254.R_MOD - 1);
    }

    /// @dev Generate a random BN254 scalar field element
    function randomScalar() internal returns (BN254.ScalarField) {
        return BN254.ScalarField.wrap(randomFelt());
    }

    /// @dev Generate a random G1 point
    function randomG1Point() internal returns (BN254.G1Point memory) {
        BN254.ScalarField scalar = BN254.ScalarField.wrap(randomFelt());
        BN254.G1Point memory point = BN254.scalarMul(BN254.P1(), scalar);
        return point;
    }

    /// @dev Generates a random uint256
    function randomUint() internal returns (uint256) {
        return vm.randomUint();
    }

    /// @dev Generates a random input between [0, high)
    function randomUint(uint256 high) internal returns (uint256) {
        return TestUtils.randomUint(0, high);
    }

    /// @dev Generates a random input between [low, high)
    function randomUint(uint256 low, uint256 high) internal returns (uint256) {
        return vm.randomUint(low, high - 1);
    }

    /// @dev Generate a random `Amount` in the renegade system
    /// @dev Amounts are constrained to be in the range [0, 2 ** 100)
    function randomAmount() internal returns (uint256) {
        return randomUint(2 ** 100);
    }

    /// @dev Generate a random set of wallet shares
    function randomWalletShares() internal returns (BN254.ScalarField[] memory) {
        BN254.ScalarField[] memory shares = new BN254.ScalarField[](DarkpoolConstants.N_WALLET_SHARES);
        for (uint256 i = 0; i < DarkpoolConstants.N_WALLET_SHARES; i++) {
            shares[i] = BN254.ScalarField.wrap(randomFelt());
        }
        return shares;
    }

    /// @dev Generate a random ethereum wallet
    function randomEthereumWallet() internal returns (Vm.Wallet memory) {
        uint256 seed = vm.randomUint() % K256_SCALAR_MOD;
        return vm.createWallet(seed);
    }

    // --- FFI Helpers --- //

    /// @dev Helper to compile a Rust binary
    function compileRustBinary(string memory manifestPath) internal virtual {
        string[] memory compileInputs = new string[](5);
        compileInputs[0] = "cargo";
        compileInputs[1] = "+nightly-2025-02-20";
        compileInputs[2] = "build";
        compileInputs[3] = "--quiet";
        compileInputs[4] = string.concat("--manifest-path=", manifestPath);
        vm.ffi(compileInputs);
    }

    /// @dev Helper to run a binary and parse its output as a uint256 array
    function runBinaryGetArray(
        string[] memory args,
        string memory delimiter
    )
        internal
        virtual
        returns (uint256[] memory)
    {
        string memory response = runBinaryGetResponse(args);
        return parseStringToUintArray(response, delimiter);
    }

    /// @dev Helper to run a binary and parse its RES: prefixed output
    function runBinaryGetResponse(string[] memory args) internal virtual returns (string memory) {
        bytes memory res = vm.ffi(args);
        string memory str = string(res);
        // Strip the "RES:" prefix and parse
        // We prefix here to avoid the FFI interface interpreting the output as either raw bytes or a string
        require(
            bytes(str).length > 4 && bytes(str)[0] == "R" && bytes(str)[1] == "E" && bytes(str)[2] == "S"
                && bytes(str)[3] == ":",
            "Invalid output format"
        );

        // Extract everything after "RES:"
        bytes memory result = new bytes(bytes(str).length - 4);
        for (uint256 i = 4; i < bytes(str).length; i++) {
            result[i - 4] = bytes(str)[i];
        }
        return string(result);
    }

    /// @dev Helper to convert bytes to hex string
    function bytesToHexString(bytes memory data) internal pure virtual returns (string memory) {
        bytes memory hexChars = "0123456789abcdef";
        bytes memory result = new bytes(data.length * 2);

        for (uint256 i = 0; i < data.length; i++) {
            result[i * 2] = hexChars[uint8(data[i] >> 4)];
            result[i * 2 + 1] = hexChars[uint8(data[i] & 0x0f)];
        }

        return string(result);
    }

    /// @dev Helper to split a string by a delimiter
    function split(string memory _str, string memory _delim) internal pure virtual returns (string[] memory) {
        bytes memory str = bytes(_str);
        bytes memory delim = bytes(_delim);

        // Count number of delimiters to size array
        uint256 count = 1;
        for (uint256 i = 0; i < str.length; i++) {
            if (str[i] == delim[0]) {
                count++;
            }
        }

        string[] memory parts = new string[](count);
        count = 0;

        // Track start of current part
        uint256 start = 0;

        // Split into parts
        for (uint256 i = 0; i < str.length; i++) {
            if (str[i] == delim[0]) {
                parts[count] = substring(str, start, i);
                start = i + 1;
                count++;
            }
        }
        // Add final part
        parts[count] = substring(str, start, str.length);

        return parts;
    }

    /// @dev Helper to get a substring
    function substring(bytes memory _str, uint256 _start, uint256 _end) internal pure virtual returns (string memory) {
        bytes memory result = new bytes(_end - _start);
        for (uint256 i = _start; i < _end; i++) {
            result[i - _start] = _str[i];
        }
        return string(result);
    }

    /// @dev Helper to parse a string of space-separated numbers into a uint256 array
    function parseStringToUintArray(
        string memory str,
        string memory delimiter
    )
        internal
        virtual
        returns (uint256[] memory)
    {
        string[] memory parts = split(str, delimiter);
        uint256[] memory values = new uint256[](parts.length);
        for (uint256 i = 0; i < parts.length; i++) {
            values[i] = vm.parseUint(parts[i]);
        }
        return values;
    }
}

// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import { TestUtils } from "./utils/TestUtils.sol";
import { BN254 } from "solidity-bn254/BN254.sol";
import { BN254Helpers } from "../src/libraries/verifier/BN254Helpers.sol";

contract BN254HelpersTest is TestUtils {
    struct RootOfUnityTest {
        uint256 powerOfTwo;
        BN254.ScalarField expectedRoot;
    }

    /// @notice Test the root of unity function
    function testRootOfUnity() public pure {
        RootOfUnityTest[] memory testCases = new RootOfUnityTest[](6);

        // Test case for n = 2^1
        testCases[0] = RootOfUnityTest({
            powerOfTwo: 1,
            expectedRoot: BN254.ScalarField.wrap(
                21_888_242_871_839_275_222_246_405_745_257_275_088_548_364_400_416_034_343_698_204_186_575_808_495_616
            )
        });

        // Test case for n = 2
        testCases[1] = RootOfUnityTest({
            powerOfTwo: 2,
            expectedRoot: BN254.ScalarField.wrap(
                21_888_242_871_839_275_217_838_484_774_961_031_246_007_050_428_528_088_939_761_107_053_157_389_710_902
            )
        });

        // Test case for n = 4
        testCases[2] = RootOfUnityTest({
            powerOfTwo: 4,
            expectedRoot: BN254.ScalarField.wrap(
                14_940_766_826_517_323_942_636_479_241_147_756_311_199_852_622_225_275_649_687_664_389_641_784_935_947
            )
        });

        // Test case for n = 8
        testCases[3] = RootOfUnityTest({
            powerOfTwo: 8,
            expectedRoot: BN254.ScalarField.wrap(
                3_478_517_300_119_284_901_893_091_970_156_912_948_790_432_420_133_812_234_316_178_878_452_092_729_974
            )
        });

        // Test case for n = 2^16
        testCases[4] = RootOfUnityTest({
            powerOfTwo: 16,
            expectedRoot: BN254.ScalarField.wrap(
                421_743_594_562_400_382_753_388_642_386_256_516_545_992_082_196_004_333_756_405_989_743_524_594_615
            )
        });

        // Test case for n = 2^20
        testCases[5] = RootOfUnityTest({
            powerOfTwo: 20,
            expectedRoot: BN254.ScalarField.wrap(
                17_220_337_697_351_015_657_950_521_176_323_262_483_320_249_231_368_149_235_373_741_788_599_650_842_711
            )
        });

        // Run test cases
        for (uint256 i = 0; i < testCases.length; i++) {
            RootOfUnityTest memory tc = testCases[i];
            uint256 n = 1 << tc.powerOfTwo; // forge-lint: disable-line(incorrect-shift)
            BN254.ScalarField result = BN254Helpers.rootOfUnity(n);
            assertEq(
                BN254.ScalarField.unwrap(result),
                BN254.ScalarField.unwrap(tc.expectedRoot),
                string.concat("Root of unity test failed for n=", vm.toString(n))
            );
        }
    }
}

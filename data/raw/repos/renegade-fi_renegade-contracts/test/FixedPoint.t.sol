// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/* solhint-disable var-name-mixedcase */
// forge-lint: disable-start(mixed-case-variable)

import { TestUtils } from "./utils/TestUtils.sol";
import { FixedPoint, FixedPointLib } from "../src/libraries/FixedPoint.sol";

contract FixedPointTest is TestUtils {
    using FixedPointLib for FixedPoint;

    uint256 internal constant PRECISION = FixedPointLib.FIXED_POINT_PRECISION_BITS;

    /// @notice Test integer to fixed point conversion
    function testIntegerConversionRoundTrip() public {
        // Wrap a random integer, then convert it back
        uint256 randomInt = randomAmount();
        FixedPoint memory fp = FixedPointLib.integerToFixedPoint(randomInt);
        uint256 result = FixedPointLib.fixedPointToInteger(fp);
        assertEq(result, randomInt);
    }

    /// @notice Test division of two fixed points
    function testDiv() public pure {
        // Test 10 / 2 = 5
        FixedPoint memory fp10 = FixedPointLib.integerToFixedPoint(10);
        FixedPoint memory fp2 = FixedPointLib.integerToFixedPoint(2);
        FixedPoint memory result = FixedPointLib.div(fp10, fp2);
        assertEq(FixedPointLib.fixedPointToInteger(result), 5);

        // Test 100 / 4 = 25
        FixedPoint memory fp100 = FixedPointLib.integerToFixedPoint(100);
        FixedPoint memory fp4 = FixedPointLib.integerToFixedPoint(4);
        result = FixedPointLib.div(fp100, fp4);
        assertEq(FixedPointLib.fixedPointToInteger(result), 25);

        // Test 1 / 2 = 0.5
        FixedPoint memory fp1 = FixedPointLib.integerToFixedPoint(1);
        result = FixedPointLib.div(fp1, fp2);
        // 0.5 in fixed point is 2^62
        assertEq(result.repr, 1 << (PRECISION - 1));
    }

    /// @notice Test division of two integers returning fixed point
    function testDivIntegers() public pure {
        // Test 10 / 2 = 5
        FixedPoint memory result = FixedPointLib.divIntegers(10, 2);
        assertEq(FixedPointLib.fixedPointToInteger(result), 5);

        // Test 100 / 4 = 25
        result = FixedPointLib.divIntegers(100, 4);
        assertEq(FixedPointLib.fixedPointToInteger(result), 25);

        // Test 1 / 2 = 0.5
        result = FixedPointLib.divIntegers(1, 2);
        // 0.5 in fixed point is 2^62
        assertEq(result.repr, 1 << (PRECISION - 1));

        // Test 3 / 2 = 1.5
        result = FixedPointLib.divIntegers(3, 2);
        // 1.5 in fixed point is 2^63 + 2^62
        assertEq(result.repr, (1 << PRECISION) + (1 << (PRECISION - 1)));
    }

    /// @notice Test division of fixed point by integer
    function testDivByInteger() public pure {
        // Test 10 / 2 = 5
        FixedPoint memory fp10 = FixedPointLib.integerToFixedPoint(10);
        FixedPoint memory result = FixedPointLib.divByInteger(fp10, 2);
        assertEq(FixedPointLib.fixedPointToInteger(result), 5);

        // Test 100 / 4 = 25
        FixedPoint memory fp100 = FixedPointLib.integerToFixedPoint(100);
        result = FixedPointLib.divByInteger(fp100, 4);
        assertEq(FixedPointLib.fixedPointToInteger(result), 25);

        // Test truncation: 100 / 3 = 33.333...
        result = FixedPointLib.divByInteger(fp100, 3);
        assertEq(FixedPointLib.fixedPointToInteger(result), 33);
    }

    /// @notice Test multiplication of fixed point by integer
    function testUnsafeFixedPointMul() public pure {
        // Test 5 * 2 = 10
        FixedPoint memory fp5 = FixedPointLib.integerToFixedPoint(5);
        uint256 result = FixedPointLib.unsafeFixedPointMul(fp5, 2);
        assertEq(result, 10);

        // Test 100 * 3 = 300
        FixedPoint memory fp100 = FixedPointLib.integerToFixedPoint(100);
        result = FixedPointLib.unsafeFixedPointMul(fp100, 3);
        assertEq(result, 300);

        // Test 0.5 * 10 = 5
        FixedPoint memory fp0_5 = FixedPoint({ repr: 1 << (PRECISION - 1) });
        result = FixedPointLib.unsafeFixedPointMul(fp0_5, 10);
        assertEq(result, 5);

        // Test 1.5 * 4 = 6
        FixedPoint memory fp1_5 = FixedPoint({ repr: (1 << PRECISION) + (1 << (PRECISION - 1)) });
        result = FixedPointLib.unsafeFixedPointMul(fp1_5, 4);
        assertEq(result, 6);
    }

    /// @notice Test division of integer by fixed point
    function testDivIntegerByFixedPoint() public pure {
        // Test 10 / 2 = 5
        FixedPoint memory fp2 = FixedPointLib.integerToFixedPoint(2);
        uint256 result = FixedPointLib.divIntegerByFixedPoint(10, fp2);
        assertEq(result, 5);

        // Test 100 / 4 = 25
        FixedPoint memory fp4 = FixedPointLib.integerToFixedPoint(4);
        result = FixedPointLib.divIntegerByFixedPoint(100, fp4);
        assertEq(result, 25);

        // Test 10 / 0.5 = 20
        FixedPoint memory fp0_5 = FixedPoint({ repr: 1 << (PRECISION - 1) });
        result = FixedPointLib.divIntegerByFixedPoint(10, fp0_5);
        assertEq(result, 20);

        // Test 100 / 1.5 = 66 (truncated from 66.666...)
        FixedPoint memory fp1_5 = FixedPoint({ repr: (1 << PRECISION) + (1 << (PRECISION - 1)) });
        result = FixedPointLib.divIntegerByFixedPoint(100, fp1_5);
        assertEq(result, 66);

        // Test 50 / 2.5 = 20
        FixedPoint memory fp2_5 = FixedPoint({ repr: (2 << PRECISION) + (1 << (PRECISION - 1)) });
        result = FixedPointLib.divIntegerByFixedPoint(50, fp2_5);
        assertEq(result, 20);
    }

    /// @notice Test edge case: division by 1
    function testDivIntegerByFixedPointDivByOne() public {
        FixedPoint memory fp1 = FixedPointLib.integerToFixedPoint(1);
        uint256 dividend = randomAmount();
        uint256 result = FixedPointLib.divIntegerByFixedPoint(dividend, fp1);
        assertEq(result, dividend);
    }

    /// @notice Test dividing an integer by a fixed point value less than 1
    function testDivIntegerByFixedPointLessThanOne() public {
        FixedPoint memory fp0_5 = FixedPoint({ repr: 1 << (PRECISION - 1) });
        uint256 dividend = randomAmount();
        uint256 result = FixedPointLib.divIntegerByFixedPoint(dividend, fp0_5);
        assertEq(result, dividend * 2);
    }
}

// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import { BN254 } from "solidity-bn254/BN254.sol";

import { DarkpoolV2TestBase } from "./DarkpoolV2TestBase.sol";

contract DarkpoolBasicTest is DarkpoolV2TestBase {
    function setUp() public override {
        super.setUp();
    }

    function test_nullifierSpent() public {
        BN254.ScalarField nullifier = randomScalar();
        bool isSpent = darkpool.nullifierSpent(nullifier);
        assertEq(isSpent, false);
    }
}

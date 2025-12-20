// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import { DarkpoolTestBase } from "./DarkpoolTestBase.sol";
import { IDarkpool } from "darkpoolv1-interfaces/IDarkpool.sol";
import { NullifierLib as NullifierSetLib } from "renegade-lib/NullifierSet.sol";
import { ValidWalletCreateStatement } from "darkpoolv1-lib/PublicInputs.sol";
import { PlonkProof } from "renegade-lib/verifier/Types.sol";

contract CreateWalletTest is DarkpoolTestBase {
    // --- Create Wallet --- //

    /// @notice Test creating a wallet
    function test_createWallet() public {
        (ValidWalletCreateStatement memory statement, PlonkProof memory proof) = createWalletCalldata();
        darkpool.createWallet(statement, proof);
    }

    // --- Invalid Cases --- //

    /// @notice Test creating a wallet with an invalid proof
    function test_createWallet_invalidProof() public {
        (ValidWalletCreateStatement memory statement, PlonkProof memory proof) = createWalletCalldata();
        vm.expectRevert(IDarkpool.VerificationFailed.selector);
        darkpoolRealVerifier.createWallet(statement, proof);
    }

    /// @notice Test creating a wallet with a duplicate public blinder share
    function test_createWallet_duplicateBlinder() public {
        (ValidWalletCreateStatement memory statement, PlonkProof memory proof) = createWalletCalldata();
        darkpool.createWallet(statement, proof);
        vm.expectRevert(NullifierSetLib.NullifierAlreadySpent.selector);
        darkpool.createWallet(statement, proof);
    }
}

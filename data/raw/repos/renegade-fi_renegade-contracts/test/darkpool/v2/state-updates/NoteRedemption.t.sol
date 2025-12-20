// SPDX-License-Identifier: MIT
/* solhint-disable gas-small-strings */
/* solhint-disable func-name-mixedcase */
pragma solidity ^0.8.24;

import { Vm } from "forge-std/Vm.sol";
import { BN254 } from "solidity-bn254/BN254.sol";

import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import { DarkpoolV2TestUtils } from "../DarkpoolV2TestUtils.sol";
import { NoteRedemptionProofBundle } from "darkpoolv2-types/ProofBundles.sol";
import { ValidNoteRedemptionStatement } from "darkpoolv2-lib/public_inputs/Fees.sol";
import { MerkleMountainLib } from "renegade-lib/merkle/MerkleMountain.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";
import { Note } from "darkpoolv2-types/Note.sol";

/// @title NoteRedemptionTest
/// @author Renegade Eng
/// @notice Tests for the note redemption functionality in DarkpoolV2
contract NoteRedemptionTest is DarkpoolV2TestUtils {
    using MerkleMountainLib for MerkleMountainLib.MerkleMountainRange;

    // Test state
    MerkleMountainLib.MerkleMountainRange private testMountain;
    Vm.Wallet private noteReceiver;

    /// @notice Set up the test environment
    function setUp() public override {
        super.setUp();
        // Create a wallet for the note receiver
        noteReceiver = vm.createWallet("note_receiver");
    }

    // -----------
    // | Helpers |
    // -----------

    /// @notice Create a note redemption proof bundle
    /// @param noteRoot The Merkle root for the note
    /// @param receiver The note receiver address
    /// @param token The token address for the note
    /// @param amount The amount for the note
    /// @return proofBundle The created proof bundle
    function createNoteRedemptionProofBundle(
        BN254.ScalarField noteRoot,
        address receiver,
        address token,
        uint256 amount
    )
        internal
        returns (NoteRedemptionProofBundle memory proofBundle)
    {
        BN254.ScalarField noteNullifier = randomScalar();
        Note memory note = Note({ mint: token, amount: amount, receiver: receiver, blinder: randomScalar() });

        ValidNoteRedemptionStatement memory statement =
            ValidNoteRedemptionStatement({ note: note, noteRoot: noteRoot, noteNullifier: noteNullifier });
        proofBundle = NoteRedemptionProofBundle({ statement: statement, proof: createDummyProof() });
    }

    /// @notice Generate random note redemption calldata with valid Merkle root
    /// @return proofBundle The proof bundle for the note redemption
    function generateRandomNoteRedemptionCalldata() internal returns (NoteRedemptionProofBundle memory proofBundle) {
        uint256 amount = randomAmount();
        BN254.ScalarField noteRoot = darkpool.getMerkleRoot(DarkpoolConstants.DEFAULT_MERKLE_DEPTH);
        proofBundle = createNoteRedemptionProofBundle(noteRoot, noteReceiver.addr, address(baseToken), amount);

        // Capitalize the darkpool to have enough tokens for the withdrawal
        baseToken.mint(address(darkpool), amount);
    }

    // ---------
    // | Tests |
    // ---------

    /// @notice Test a successful note redemption
    function test_redeemNote_success() public {
        // Generate test data
        NoteRedemptionProofBundle memory proofBundle = generateRandomNoteRedemptionCalldata();

        // Execute the note redemption and measure balance changes
        uint256 initialBalance = baseToken.balanceOf(proofBundle.statement.note.receiver);
        uint256 darkpoolBalanceBefore = baseToken.balanceOf(address(darkpool));
        darkpool.redeemNote(proofBundle);
        uint256 finalBalance = baseToken.balanceOf(proofBundle.statement.note.receiver);
        uint256 darkpoolBalanceAfter = baseToken.balanceOf(address(darkpool));

        assertEq(
            finalBalance - initialBalance,
            proofBundle.statement.note.amount,
            "Note amount should be transferred to receiver"
        );
        assertEq(
            darkpoolBalanceAfter,
            darkpoolBalanceBefore - proofBundle.statement.note.amount,
            "Darkpool balance should decrease"
        );
    }

    /// @notice Test note redemption with invalid Merkle root
    function test_redeemNote_invalidMerkleRoot_reverts() public {
        // Use a random Merkle root that is NOT in history
        BN254.ScalarField invalidMerkleRoot = randomScalar();
        NoteRedemptionProofBundle memory proofBundle =
            createNoteRedemptionProofBundle(invalidMerkleRoot, noteReceiver.addr, address(baseToken), 100 ether);

        // Should revert due to invalid Merkle root
        vm.expectRevert(IDarkpoolV2.InvalidMerkleRoot.selector);
        darkpool.redeemNote(proofBundle);
    }

    /// @notice Test that double spending the same nullifier fails
    function test_redeemNote_doubleSpend_reverts() public {
        // Generate test data
        NoteRedemptionProofBundle memory proofBundle = generateRandomNoteRedemptionCalldata();

        // Execute the first note redemption
        darkpool.redeemNote(proofBundle);

        // Second attempt with the same nullifier should fail
        vm.expectRevert(IDarkpoolV2.NullifierAlreadySpent.selector);
        darkpool.redeemNote(proofBundle);
    }
}

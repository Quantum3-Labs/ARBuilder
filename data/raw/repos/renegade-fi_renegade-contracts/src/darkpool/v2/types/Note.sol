// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { SimpleTransfer, SimpleTransferType } from "darkpoolv2-types/transfers/SimpleTransfer.sol";

/// @title Note
/// @author Renegade Eng
/// @notice A note allocated into the protocol state by one user transferring to another
struct Note {
    /// @dev The mint (ERC20 address) of the note
    address mint;
    /// @dev The amount of the note
    uint256 amount;
    /// @dev The receiver's EOA address
    address receiver;
    /// @dev The blinder of the note
    BN254.ScalarField blinder;
}

/// @title NoteLib
/// @author Renegade Eng
/// @notice A library for manipulating notes
library NoteLib {
    /// @notice Build a transfer from a note
    /// @param note The note to build the transfer from
    /// @return The transfer
    function buildTransfer(Note memory note) public pure returns (SimpleTransfer memory) {
        return SimpleTransfer({
            account: note.receiver,
            mint: note.mint,
            amount: note.amount,
            transferType: SimpleTransferType.Withdrawal
        });
    }
}

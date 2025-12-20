// SPDX-License-Identifier: MIT
/* solhint-disable one-contract-per-file */
pragma solidity ^0.8.24;

import { SimpleTransfer } from "./SimpleTransfer.sol";

// --------------------
// | Settlement Lists |
// --------------------

/// @notice A list of simple transfers to settle after a match
/// @dev We use this type to allow call-sites to push to this list in
/// a way that feels like a vector in other languages. This allows settlement
/// validation logic to write transfers to this list in a dynamic way.
struct SettlementTransfersList {
    /// @dev The list of simple transfers
    SimpleTransfer[] transfers;
    /// @dev The cursor indicating the next index to push to
    uint256 nextIndex;
}

/// @title Settlement Transfers List Library
/// @author Renegade Eng
/// @notice A library implementing vector-like operations on the settlement transfers list
library SettlementTransfersListLib {
    // --- Errors --- //

    /// @notice Thrown when attempting to push to a list that has reached its capacity
    error TransferListCapacityExceeded();

    // --- Interface --- //

    /// @notice Create a new settlement transfers list
    /// @param capacity The initial capacity of the list
    /// @return The new settlement transfers list
    function newList(uint256 capacity) internal pure returns (SettlementTransfersList memory) {
        return SettlementTransfersList({ transfers: new SimpleTransfer[](capacity), nextIndex: 0 });
    }

    /// @notice Get the length of the list
    /// @param list The list to get the length of
    /// @return The length of the list
    function length(SettlementTransfersList memory list) internal pure returns (uint256) {
        return list.nextIndex;
    }

    /// @notice Push a transfer to the list
    /// @param list The list to push to
    /// @param transfer The transfer to push
    function push(SettlementTransfersList memory list, SimpleTransfer memory transfer) internal pure {
        if (list.nextIndex > list.transfers.length - 1) {
            revert TransferListCapacityExceeded();
        }
        list.transfers[list.nextIndex] = transfer;
        ++list.nextIndex;
    }
}

/// @notice A list of deposits and withdrawals to settle after a match
struct SettlementTransfers {
    /// @dev The list of deposits
    SettlementTransfersList deposits;
    /// @dev The list of withdrawals
    SettlementTransfersList withdrawals;
}

/// @title Settlement Transfers Library
/// @notice A library implementing vector-like semantics for the `SettlementTransfers` type
/// @author Renegade Eng
library SettlementTransfersLib {
    using SettlementTransfersListLib for SettlementTransfersList;

    /// @notice Create a new settlement transfers list
    /// @param numDeposits The initial number of deposits
    /// @param numWithdrawals The initial number of withdrawals
    /// @return The new settlement transfers list
    function newList(uint256 numDeposits, uint256 numWithdrawals) internal pure returns (SettlementTransfers memory) {
        return SettlementTransfers({
            deposits: SettlementTransfersListLib.newList(numDeposits),
            withdrawals: SettlementTransfersListLib.newList(numWithdrawals)
        });
    }

    /// @notice Get the length of the deposits list
    /// @param transfers The transfers to get the length of
    /// @return The length of the deposits list
    function numDeposits(SettlementTransfers memory transfers) internal pure returns (uint256) {
        return transfers.deposits.length();
    }

    /// @notice Get the length of the withdrawals list
    /// @param transfers The transfers to get the length of
    /// @return The length of the withdrawals list
    function numWithdrawals(SettlementTransfers memory transfers) internal pure returns (uint256) {
        return transfers.withdrawals.length();
    }

    /// @notice Push a deposit to the list
    /// @param transfers The transfers to push to
    /// @param deposit The deposit to push
    function pushDeposit(SettlementTransfers memory transfers, SimpleTransfer memory deposit) internal pure {
        SettlementTransfersListLib.push(transfers.deposits, deposit);
    }

    /// @notice Push a withdrawal to the list
    /// @param transfers The transfers to push to
    /// @param withdrawal The withdrawal to push
    function pushWithdrawal(SettlementTransfers memory transfers, SimpleTransfer memory withdrawal) internal pure {
        SettlementTransfersListLib.push(transfers.withdrawals, withdrawal);
    }
}

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {
    MAX_ORDERS as WALLET_MAX_ORDERS,
    MAX_BALANCES as WALLET_MAX_BALANCES,
    NUM_WALLET_SCALARS
} from "darkpoolv1-types/Wallet.sol";

/// @title Darkpool Constants
/// @author Renegade Eng
/// @notice Constants used in the darkpool
library DarkpoolConstants {
    /// @notice The maximum number of orders in a wallet
    uint256 internal constant MAX_ORDERS = WALLET_MAX_ORDERS;
    /// @notice The maximum number of balances in a wallet
    uint256 internal constant MAX_BALANCES = WALLET_MAX_BALANCES;
    /// @notice The number of shares in a wallet
    uint256 internal constant N_WALLET_SHARES = NUM_WALLET_SCALARS;
    /// @notice The depth of the Merkle tree
    uint256 internal constant MERKLE_DEPTH = 32;
    /// @notice The maximum number of leaves in the merkle tree
    uint256 internal constant MAX_MERKLE_LEAVES = 2 ** MERKLE_DEPTH;

    /// @notice The address used for native tokens in trade settlement
    /// @dev This is currently just ETH, but intentionally written abstractly
    address internal constant NATIVE_TOKEN_ADDRESS = 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE;

    /// @notice Check whether an address is the native token address
    /// @param addr The address to check
    /// @return True if the address is the native token address, false otherwise
    function isNativeToken(address addr) public pure returns (bool) {
        return addr == NATIVE_TOKEN_ADDRESS;
    }
}

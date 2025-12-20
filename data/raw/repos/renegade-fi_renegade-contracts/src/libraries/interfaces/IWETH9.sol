// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { IERC20 } from "oz-contracts/token/ERC20/IERC20.sol";

/// @title Interface for WETH9
/// @author Renegade Eng
/// @notice Interface for WETH9
interface IWETH9 is IERC20 {
    /// @notice Deposit ETH and mint WETH
    function deposit() external payable;

    /// @notice Withdraw (burn) WETH and receive ETH
    /// @param amount The amount of WETH to withdraw
    function withdraw(uint256 amount) external;
}

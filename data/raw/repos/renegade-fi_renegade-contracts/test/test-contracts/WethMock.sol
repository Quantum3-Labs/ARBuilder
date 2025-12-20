// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import { MockERC20 } from "solmate/src/test/utils/mocks/MockERC20.sol";
import { SafeTransferLib } from "solmate/src/utils/SafeTransferLib.sol";

/// @title WethMock
/// @notice A mock implementation of WETH9
contract WethMock is MockERC20 {
    constructor() MockERC20("Wrapped Ether", "WETH", 18) { }

    /// @notice Deposit ETH into the contract
    function deposit() external payable {
        mint(msg.sender, msg.value);
    }

    /// @notice Withdraw ETH from the contract
    function withdraw(uint256 amount) external {
        burn(msg.sender, amount);
        SafeTransferLib.safeTransferETH(msg.sender, amount);
    }
}

// SPDX-License-Identifier: MIT
/* solhint-disable one-contract-per-file */
/* solhint-disable gas-small-strings */
pragma solidity ^0.8.24;

import { Script } from "forge-std/Script.sol";
import { console } from "forge-std/console.sol";
import { MockERC20 } from "solmate/src/test/utils/mocks/MockERC20.sol";
import { WethMock } from "../test/test-contracts/WethMock.sol";

/**
 * @title DeployDummyERC20Script
 * @author Renegade Eng
 * @notice Deploy script for the MockERC20 token from solmate
 * @dev Usage: forge script script/DeployDummyErc20.sol --rpc-url <your_rpc_url> --broadcast --sig
 * "run(string,string,uint8)" "TokenName" "TKN" 18
 */
contract DeployDummyERC20Script is Script {
    // Hardcoded initial supply: 1 token with decimal correction
    uint256 private constant _INITIAL_SUPPLY = 10 ** 18;

    /// @notice Deploy a MockERC20 token
    /// @param name The name of the token
    /// @param symbol The symbol of the token
    /// @param decimals The number of decimals for the token
    function run(string memory name, string memory symbol, uint8 decimals) public {
        console.log("Deploying MockERC20 with name: %s, symbol: %s, decimals: %d", name, symbol, decimals);

        vm.startBroadcast();

        // Create the token with constructor params for name, symbol, and decimals
        // Then mint initial supply to the deployer
        MockERC20 token = new MockERC20(name, symbol, decimals);
        token.mint(msg.sender, _INITIAL_SUPPLY);
        console.log("MockERC20 deployed at: %s", address(token));

        vm.stopBroadcast();
    }
}

/**
 * @title DeployWethMockScript
 * @author Renegade Eng
 * @notice Deploy script for the WethMock token
 * @dev Usage: forge script script/DeployDummyErc20.sol --rpc-url <your_rpc_url> --broadcast --sig "deployWeth()"
 */
contract DeployWethMockScript is Script {
    /// @notice Deploy the WethMock contract
    function deployWeth() public {
        console.log("Deploying WethMock");
        vm.startBroadcast();

        // Deploy WethMock
        WethMock weth = new WethMock();
        console.log("WethMock deployed at: %s", address(weth));

        vm.stopBroadcast();
    }
}

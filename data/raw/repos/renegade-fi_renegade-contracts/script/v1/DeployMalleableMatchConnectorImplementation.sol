// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Script } from "forge-std/Script.sol";
import { DeployV1Utils } from "./DeployV1Utils.sol";

/// @title DeployMalleableMatchConnectorImplementationScript
/// @author Renegade Eng
/// @notice Deploys only the MalleableMatchConnector implementation contract for upgrades
contract DeployMalleableMatchConnectorImplementationScript is Script, DeployV1Utils {
    /// @notice Deploy the MalleableMatchConnector implementation contract
    function run() public {
        vm.startBroadcast();
        deployMalleableMatchConnectorImplementation(vm);
        vm.stopBroadcast();
    }
}

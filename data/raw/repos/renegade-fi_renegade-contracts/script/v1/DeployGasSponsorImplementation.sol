// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Script } from "forge-std/Script.sol";
import { DeployV1Utils } from "./DeployV1Utils.sol";

/// @title DeployGasSponsorImplementationScript
/// @author Renegade Eng
/// @notice Deploys only the GasSponsor implementation contract for upgrades
contract DeployGasSponsorImplementationScript is Script, DeployV1Utils {
    /// @notice Deploy the GasSponsor implementation contract
    function run() public {
        vm.startBroadcast();
        deployGasSponsorImplementation(vm);
        vm.stopBroadcast();
    }
}

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/* solhint-disable gas-small-strings */

import { Vm } from "forge-std/Vm.sol";

import { JsonUtils } from "./JsonUtils.sol";

/// @title DeployUtils
/// @author Renegade Eng
/// @notice Deployment utilities for the Renegade darkpool
library DeployUtils {
    /// @dev Path to the deployments JSON file
    string internal constant DEFAULT_DEPLOYMENTS_PATH = "deployments.devnet.json";

    /// @notice Get the deployments path from environment or use default
    /// @param vm The VM to access environment variables
    /// @return The deployments file path
    function getDeploymentsPath(Vm vm) internal view returns (string memory) {
        return vm.envOr("DEPLOYMENTS", DEFAULT_DEPLOYMENTS_PATH);
    }

    /// @notice Deploy the Poseidon2 hasher contract
    /// @param vm The VM to run the commands with
    /// @return The deployed hasher contract address
    function deployHasher(Vm vm) internal returns (address) {
        // Get the bytecode using huffc
        string[] memory inputs = new string[](3);
        inputs[0] = "huffc";
        inputs[1] = "-b";
        inputs[2] = "src/libraries/poseidon2/poseidonHasher.huff";
        bytes memory bytecode = vm.ffi(inputs);

        // Deploy the contract
        address deployedAddress;
        assembly {
            deployedAddress :=
                create(
                    0, // value
                    add(bytecode, 0x20), // bytecode start
                    mload(bytecode) // bytecode length
                )
        }

        // solhint-disable-next-line gas-custom-errors
        require(deployedAddress != address(0), "Hasher deployment failed");
        writeDeployment(vm, "Hasher", deployedAddress);
        return deployedAddress;
    }

    /// @notice Write a deployment address to the deployments.json file
    /// @param vm The VM to run the commands with
    /// @param contractName The name of the contract being deployed
    /// @param contractAddress The address of the deployed contract
    function writeDeployment(Vm vm, string memory contractName, address contractAddress) internal {
        JsonUtils.writeJsonEntry(vm, getDeploymentsPath(vm), contractName, vm.toString(contractAddress));
    }
}

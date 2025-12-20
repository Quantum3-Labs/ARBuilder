// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/* solhint-disable gas-small-strings */

/**
 * @notice This script deploys the MalleableMatchConnector contract behind a proxy
 * Example: forge script script/DeployMalleableMatchConnector.s.sol --rpc-url <rpc-url>
 * --sig "run(address,address)" <admin> <gasSponsorAddress>
 * --broadcast --sender <sender> --unlocked
 */
import { Script } from "forge-std/Script.sol";
import { console } from "forge-std/console.sol";
import { DeployV1Utils } from "./DeployV1Utils.sol";

/// @title DeployMalleableMatchConnectorScript
/// @author Renegade Eng
/// @notice Deployment script for the MalleableMatchConnector contract
contract DeployMalleableMatchConnectorScript is Script, DeployV1Utils {
    /**
     * @notice Deploy the MalleableMatchConnector contract behind a proxy
     * @param admin The admin address - serves as proxy admin
     * @param gasSponsorAddress The address of the gas sponsor contract
     */
    function run(address admin, address gasSponsorAddress) public {
        console.log("Deploying MalleableMatchConnector with parameters:");
        console.log("Admin:", admin);
        console.log("Gas Sponsor Address:", gasSponsorAddress);

        vm.startBroadcast();
        address connectorProxy = deployMalleableMatchConnector(admin, gasSponsorAddress, vm);
        console.log("MalleableMatchConnector deployment complete. Proxy address:", connectorProxy);
        vm.stopBroadcast();
    }
}

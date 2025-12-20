// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/* solhint-disable gas-small-strings */

/**
 * @notice This script deploys the GasSponsor contract behind a proxy
 * Example: forge script script/DeployGasSponsor.s.sol --rpc-url <rpc-url>
 * --sig "run(address,address,address)" <owner> <darkpoolAddress> <authAddress>
 * --broadcast --sender <sender> --unlocked
 */
import { Script } from "forge-std/Script.sol";
import { console } from "forge-std/console.sol";
import { DeployV1Utils } from "./DeployV1Utils.sol";

/// @title DeployGasSponsorScript
/// @author Renegade Eng
/// @notice Deployment script for the GasSponsor contract
contract DeployGasSponsorScript is Script, DeployV1Utils {
    /**
     * @notice Deploy the GasSponsor contract behind a proxy
     * @param owner The owner address - serves as both proxy admin and GasSponsor contract owner
     * @param darkpoolAddress The address of the darkpool proxy contract
     * @param authAddress The public key used to authenticate gas sponsorship
     */
    function run(address owner, address darkpoolAddress, address authAddress) public {
        console.log("Deploying GasSponsor with parameters:");
        console.log("Owner/Admin:", owner);
        console.log("Darkpool Address:", darkpoolAddress);
        console.log("Auth Address:", authAddress);

        vm.startBroadcast();
        address gasSponsorProxy = deployGasSponsor(owner, darkpoolAddress, authAddress, vm);
        console.log("Gas Sponsor deployment complete. Proxy address:", gasSponsorProxy);
        vm.stopBroadcast();
    }
}

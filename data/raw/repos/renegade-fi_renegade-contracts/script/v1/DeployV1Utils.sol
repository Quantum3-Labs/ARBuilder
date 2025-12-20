// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/* solhint-disable gas-small-strings */

import { console } from "forge-std/console.sol";
import { Vm } from "forge-std/Vm.sol";
import { IPermit2 } from "permit2-lib/interfaces/IPermit2.sol";

import { Darkpool } from "darkpoolv1-contracts/Darkpool.sol";
import { DarkpoolProxy } from "darkpoolv1-proxies/DarkpoolProxy.sol";
import { Verifier } from "darkpoolv1-contracts/Verifier.sol";
import { VKeys, IVKeys } from "darkpoolv1-contracts/VKeys.sol";
import { IHasher } from "renegade-lib/interfaces/IHasher.sol";
import { IVerifier } from "darkpoolv1-interfaces/IVerifier.sol";
import { IWETH9 } from "renegade-lib/interfaces/IWETH9.sol";
import { EncryptionKey } from "renegade-lib/Ciphertext.sol";
import { TransferExecutor } from "darkpoolv1-contracts/TransferExecutor.sol";
import { GasSponsor } from "darkpoolv1-contracts/GasSponsor.sol";
import { GasSponsorProxy } from "darkpoolv1-proxies/GasSponsorProxy.sol";
import { MalleableMatchConnector } from "renegade-connectors/MalleableMatchConnector.sol";
import { MalleableMatchConnectorProxy } from "renegade-connectors/MalleableMatchConnectorProxy.sol";
import { DeployUtils } from "../utils/DeployUtils.sol";

/// @title DeployV1Utils
/// @author Renegade Eng
/// @notice Deployment utilities for the Renegade darkpool v1
contract DeployV1Utils {
    /// @notice Deploy the TransferExecutor contract
    /// @param vm The VM to write deployments
    /// @return The deployed TransferExecutor address
    function deployTransferExecutor(Vm vm) internal returns (address) {
        TransferExecutor transferExecutor = new TransferExecutor();
        DeployUtils.writeDeployment(vm, "TransferExecutor", address(transferExecutor));
        return address(transferExecutor);
    }

    /// @notice Deploy the VKeys and Verifier contracts
    /// @param vm The VM to write deployments
    /// @return The deployed VKeys contract
    /// @return The deployed Verifier contract
    function deployVKeysAndVerifier(Vm vm) internal returns (IVKeys, IVerifier) {
        VKeys vkeys = new VKeys();
        IVerifier verifier = new Verifier(vkeys);
        DeployUtils.writeDeployment(vm, "VKeys", address(vkeys));
        DeployUtils.writeDeployment(vm, "Verifier", address(verifier));
        return (vkeys, verifier);
    }

    /// @notice Get the ProxyAdmin address for a TransparentUpgradeableProxy
    /// @param proxy The proxy address
    /// @param vm The VM instance to use for reading storage
    /// @return The admin address
    function getProxyAdmin(address proxy, Vm vm) internal view returns (address) {
        // ERC1967 admin storage slot: 0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103
        bytes32 slot = 0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103;

        // Read the storage from the proxy contract using eth_getStorageAt
        bytes32 adminSlot = vm.load(proxy, slot);
        return address(uint160(uint256(adminSlot)));
    }

    /// @notice Deploy the GasSponsor contract behind a proxy
    /// @param owner The owner address - serves as both proxy admin and GasSponsor contract owner
    /// @param darkpoolAddress The address of the darkpool proxy contract
    /// @param authAddress The public key used to authenticate gas sponsorship
    /// @param vm The VM to run the commands with
    /// @return gasSponsorProxyAddr The deployed GasSponsor proxy address
    function deployGasSponsor(
        address owner,
        address darkpoolAddress,
        address authAddress,
        Vm vm
    )
        internal
        returns (address gasSponsorProxyAddr)
    {
        // Deploy the GasSponsor implementation
        address gasSponsorAddr = deployGasSponsorImplementation(vm);

        // Deploy the GasSponsorProxy
        GasSponsorProxy gasSponsorProxy = new GasSponsorProxy(gasSponsorAddr, owner, darkpoolAddress, authAddress);
        DeployUtils.writeDeployment(vm, "GasSponsorProxy", address(gasSponsorProxy));
        console.log("GasSponsorProxy deployed at:", address(gasSponsorProxy));

        // Extract and save the ProxyAdmin address
        address proxyAdmin = getProxyAdmin(address(gasSponsorProxy), vm);
        DeployUtils.writeDeployment(vm, "GasSponsorProxyAdmin", proxyAdmin);
        console.log("GasSponsorProxyAdmin deployed at:", proxyAdmin);

        return address(gasSponsorProxy);
    }

    /// @notice Deploy only the GasSponsor implementation contract for proxy upgrades
    /// @param vm The VM to write deployments
    /// @return implAddr The deployed implementation address
    function deployGasSponsorImplementation(Vm vm) internal returns (address implAddr) {
        GasSponsor gasSponsor = new GasSponsor();
        DeployUtils.writeDeployment(vm, "GasSponsor", address(gasSponsor));
        console.log("GasSponsor implementation deployed at:", address(gasSponsor));
        return address(gasSponsor);
    }

    /// @notice Deploy core contracts
    /// @param owner The owner address for the darkpool
    /// @param protocolFeeRate The protocol fee rate
    /// @param protocolFeeAddr The address to receive protocol fees
    /// @param protocolFeeKey The encryption key for protocol fees
    /// @param permit2 The Permit2 contract instance
    /// @param weth The WETH9 contract instance
    /// @param vm The VM to run the commands with
    /// @return darkpoolAddr The deployed darkpool proxy address
    function deployCore(
        address owner,
        uint256 protocolFeeRate,
        address protocolFeeAddr,
        EncryptionKey memory protocolFeeKey,
        IPermit2 permit2,
        IWETH9 weth,
        Vm vm
    )
        internal
        returns (address darkpoolAddr)
    {
        // Deploy library contracts for the darkpool
        IHasher hasher = IHasher(DeployUtils.deployHasher(vm));
        (, IVerifier verifier) = deployVKeysAndVerifier(vm);
        address transferExecutor = deployTransferExecutor(vm);

        // Deploy Darkpool with all required parameters
        Darkpool darkpool = new Darkpool();
        DarkpoolProxy darkpoolProxy = new DarkpoolProxy(
            address(darkpool),
            owner,
            protocolFeeRate,
            protocolFeeAddr,
            protocolFeeKey,
            weth,
            hasher,
            verifier,
            permit2,
            transferExecutor
        );

        DeployUtils.writeDeployment(vm, "Darkpool", address(darkpool));
        DeployUtils.writeDeployment(vm, "DarkpoolProxy", address(darkpoolProxy));
        console.log("Darkpool deployed at:", address(darkpoolProxy));

        // Extract and save the ProxyAdmin address
        address proxyAdmin = getProxyAdmin(address(darkpoolProxy), vm);
        DeployUtils.writeDeployment(vm, "ProxyAdmin", proxyAdmin);
        console.log("ProxyAdmin deployed at:", proxyAdmin);

        return address(darkpoolProxy);
    }

    /// @notice Deploy only the Darkpool implementation contract for proxy upgrades
    /// @param vm The VM to write deployments
    /// @return implAddr The deployed implementation address
    function deployDarkpoolImplementation(Vm vm) internal returns (address implAddr) {
        Darkpool darkpool = new Darkpool();
        DeployUtils.writeDeployment(vm, "Darkpool", address(darkpool));
        console.log("Darkpool implementation deployed at:", address(darkpool));
        return address(darkpool);
    }

    /// @notice Deploy the MalleableMatchConnector contract behind a proxy
    /// @param admin The admin address - serves as proxy admin
    /// @param gasSponsorAddress The address of the gas sponsor contract
    /// @param vm The VM to run the commands with
    /// @return connectorProxyAddr The deployed MalleableMatchConnector proxy address
    function deployMalleableMatchConnector(
        address admin,
        address gasSponsorAddress,
        Vm vm
    )
        internal
        returns (address connectorProxyAddr)
    {
        // Deploy the MalleableMatchConnector implementation
        address connectorAddr = deployMalleableMatchConnectorImplementation(vm);

        // Deploy the MalleableMatchConnectorProxy
        MalleableMatchConnectorProxy connectorProxy =
            new MalleableMatchConnectorProxy(connectorAddr, admin, gasSponsorAddress);
        DeployUtils.writeDeployment(vm, "MalleableMatchConnectorProxy", address(connectorProxy));
        console.log("MalleableMatchConnectorProxy deployed at:", address(connectorProxy));

        // Extract and save the ProxyAdmin address
        address proxyAdmin = getProxyAdmin(address(connectorProxy), vm);
        DeployUtils.writeDeployment(vm, "MalleableMatchConnectorProxyAdmin", proxyAdmin);
        console.log("MalleableMatchConnectorProxyAdmin deployed at:", proxyAdmin);

        return address(connectorProxy);
    }

    /// @notice Deploy only the MalleableMatchConnector implementation contract for proxy upgrades
    /// @param vm The VM to write deployments
    /// @return implAddr The deployed implementation address
    function deployMalleableMatchConnectorImplementation(Vm vm) internal returns (address implAddr) {
        MalleableMatchConnector connector = new MalleableMatchConnector();
        DeployUtils.writeDeployment(vm, "MalleableMatchConnector", address(connector));
        console.log("MalleableMatchConnector implementation deployed at:", address(connector));
        return address(connector);
    }
}

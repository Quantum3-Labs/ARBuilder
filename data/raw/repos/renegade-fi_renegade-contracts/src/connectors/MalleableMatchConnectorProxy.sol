// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { TransparentUpgradeableProxy } from "oz-contracts/proxy/transparent/TransparentUpgradeableProxy.sol";
import { MalleableMatchConnector } from "./MalleableMatchConnector.sol";

/// @title MalleableMatchConnectorProxy
/// @author Renegade Eng
/// @notice This contract is a TransparentUpgradeableProxy for the MalleableMatchConnector contract.
/// It simplifies deployment by accepting MalleableMatchConnector-specific initialization parameters
/// and encoding them appropriately.
contract MalleableMatchConnectorProxy is TransparentUpgradeableProxy {
    /// @notice Initializes a TransparentUpgradeableProxy for a MalleableMatchConnector implementation.
    /// @param implementation The MalleableMatchConnector implementation address
    /// @param admin The admin address - serves as ProxyAdmin owner and can manage proxy upgrades
    /// @param gasSponsor The address of the gas sponsor contract
    constructor(
        address implementation,
        address admin,
        address gasSponsor
    )
        payable
        TransparentUpgradeableProxy(
            implementation,
            admin,
            abi.encodeWithSelector(MalleableMatchConnector.initialize.selector, gasSponsor)
        )
    { }
}

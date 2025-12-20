// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { TransparentUpgradeableProxy } from "oz-contracts/proxy/transparent/TransparentUpgradeableProxy.sol";
import { IDarkpoolUniswapExecutor } from "darkpoolv1-interfaces/IDarkpoolUniswapExecutor.sol";

/// @title UniswapXExecutorProxy
/// @author Renegade Eng
/// @notice This contract is a TransparentUpgradeableProxy for the UniswapXExecutor contract.
/// It simplifies deployment by accepting executor-specific initialization parameters
/// and encoding them appropriately.
contract UniswapXExecutorProxy is TransparentUpgradeableProxy {
    /// @notice Initializes a TransparentUpgradeableProxy for a UniswapXExecutor implementation.
    /// @param implementation The UniswapXExecutor implementation address
    /// @param admin The admin address - serves as both ProxyAdmin owner and UniswapXExecutor owner
    /// @param darkpool The darkpool address
    /// @param uniswapXReactor The UniswapX reactor address
    constructor(
        address implementation,
        address admin,
        address darkpool,
        address uniswapXReactor
    )
        payable
        TransparentUpgradeableProxy(
            implementation,
            admin,
            abi.encodeWithSelector(IDarkpoolUniswapExecutor.initialize.selector, admin, darkpool, uniswapXReactor)
        )
    { }
}

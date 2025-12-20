// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { TransparentUpgradeableProxy } from "oz-contracts/proxy/transparent/TransparentUpgradeableProxy.sol";
import { EncryptionKey } from "renegade-lib/Ciphertext.sol";
import { IDarkpool } from "darkpoolv1-interfaces/IDarkpool.sol";
import { IHasher } from "renegade-lib/interfaces/IHasher.sol";
import { IVerifier } from "darkpoolv1-interfaces/IVerifier.sol";
import { IPermit2 } from "permit2-lib/interfaces/IPermit2.sol";
import { IWETH9 } from "renegade-lib/interfaces/IWETH9.sol";

/// @title DarkpoolProxy
/// @author Renegade Eng
/// @notice This contract is a TransparentUpgradeableProxy for the Darkpool contract.
/// It simplifies deployment by accepting Darkpool-specific initialization parameters
/// and encoding them appropriately.
contract DarkpoolProxy is TransparentUpgradeableProxy {
    /// @notice Initializes a TransparentUpgradeableProxy for a Darkpool implementation.
    /// @param implementation The Darkpool implementation address
    /// @param admin The admin address - serves as both ProxyAdmin owner and Darkpool owner
    /// @param protocolFeeRate The protocol fee rate for the darkpool
    /// @param protocolFeeRecipient The address to receive protocol fees
    /// @param protocolFeeKey The encryption key for protocol fees
    /// @param weth The WETH9 contract instance
    /// @param hasher The hasher for the darkpool
    /// @param verifier The verifier for the darkpool
    /// @param permit2 The Permit2 contract instance for handling deposits
    /// @param transferExecutor The TransferExecutor contract address
    constructor(
        address implementation,
        address admin,
        // Darkpool-specific initialization parameters
        uint256 protocolFeeRate,
        address protocolFeeRecipient,
        EncryptionKey memory protocolFeeKey,
        IWETH9 weth,
        IHasher hasher,
        IVerifier verifier,
        IPermit2 permit2,
        address transferExecutor
    )
        payable
        TransparentUpgradeableProxy(
            implementation,
            admin,
            abi.encodeWithSelector(
                IDarkpool.initialize.selector,
                admin, // Use the same admin address for Darkpool owner
                protocolFeeRate,
                protocolFeeRecipient,
                protocolFeeKey,
                weth,
                hasher,
                verifier,
                permit2,
                transferExecutor
            )
        )
    { }
}

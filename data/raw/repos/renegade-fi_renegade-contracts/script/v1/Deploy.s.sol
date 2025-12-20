// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @notice This script must be run with the --ffi flag to enable external commands.
 * Example: forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --sig "run(address,address,address)"
 * <permit2> <weth> <feeRecipient> --ffi --broadcast --sender <sender> --unlocked
 */
import { Script } from "forge-std/Script.sol";

import { BN254 } from "solidity-bn254/BN254.sol";
import { BabyJubJubPoint, EncryptionKey } from "renegade-lib/Ciphertext.sol";
import { IPermit2 } from "permit2-lib/interfaces/IPermit2.sol";
import { IWETH9 } from "renegade-lib/interfaces/IWETH9.sol";
import { DeployV1Utils } from "./DeployV1Utils.sol";

/// @title DeployScript
/// @author Renegade Eng
/// @notice Deployment script for the Renegade darkpool
contract DeployScript is Script, DeployV1Utils {
    /// @notice Deploy the darkpool with the given parameters
    /// @param owner The owner of the darkpool
    /// @param protocolFeeKeyX The X coordinate of the protocol fee encryption key
    /// @param protocolFeeKeyY The Y coordinate of the protocol fee encryption key
    /// @param protocolFeeRate The protocol fee rate
    /// @param protocolFeeAddr The address to receive protocol fees
    /// @param permit2Address The address of the Permit2 contract
    /// @param wethAddress The address of the WETH9 contract
    function run(
        address owner,
        uint256 protocolFeeKeyX,
        uint256 protocolFeeKeyY,
        uint256 protocolFeeRate,
        address protocolFeeAddr,
        address permit2Address,
        address wethAddress
    )
        public
    {
        vm.startBroadcast();
        EncryptionKey memory protocolFeeKey = EncryptionKey({
            point: BabyJubJubPoint({ x: BN254.ScalarField.wrap(protocolFeeKeyX), y: BN254.ScalarField.wrap(protocolFeeKeyY) })
        });

        deployCore(
            owner, protocolFeeRate, protocolFeeAddr, protocolFeeKey, IPermit2(permit2Address), IWETH9(wethAddress), vm
        );
        vm.stopBroadcast();
    }
}

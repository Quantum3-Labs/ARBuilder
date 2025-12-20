// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Script } from "forge-std/Script.sol";
import { console } from "forge-std/console.sol";
import { DeployUtils } from "../utils/DeployUtils.sol";
import { DeployV2Utils } from "./DeployV2Utils.sol";
import { Permit2Utils } from "../utils/Permit2Utils.sol";
import { IWETH9 } from "renegade-lib/interfaces/IWETH9.sol";
import { IPermit2 } from "permit2-lib/interfaces/IPermit2.sol";
import { WethMock } from "test-contracts/WethMock.sol";
import { MockERC20 } from "solmate/src/test/utils/mocks/MockERC20.sol";

import { BN254 } from "solidity-bn254/BN254.sol";
import { EncryptionKey, BabyJubJubPoint } from "renegade-lib/Ciphertext.sol";

/// @title DeployDevScript
/// @author Renegade Eng
/// @notice Development deployment script with mock tokens and Permit2
contract DeployDevScript is Script, DeployV2Utils {
    /// @notice Deploy all contracts for local development
    function run() public {
        // Start broadcast for the actual deployments
        vm.startBroadcast();

        // Deploy Permit2
        IPermit2 permit2 = IPermit2(Permit2Utils.deployPermit2());
        DeployUtils.writeDeployment(vm, "Permit2", address(permit2));
        console.log("Permit2 deployed at:", address(permit2));

        // Deploy two mock ERC20s
        MockERC20 quoteToken = new MockERC20("Quote Token", "QT", 18);
        MockERC20 baseToken = new MockERC20("Base Token", "BT", 18);
        console.log("Quote Token deployed at:", address(quoteToken));
        console.log("Base Token deployed at:", address(baseToken));
        DeployUtils.writeDeployment(vm, "QuoteToken", address(quoteToken));
        DeployUtils.writeDeployment(vm, "BaseToken", address(baseToken));

        // Deploy WETH Mock
        WethMock wethMock = new WethMock();
        IWETH9 weth = IWETH9(address(wethMock));
        vm.deal(address(weth), 1e32);
        console.log("WETH Mock deployed at:", address(weth));
        DeployUtils.writeDeployment(vm, "Weth", address(weth));

        // Use a dummy encryption key
        EncryptionKey memory protocolFeeKey = EncryptionKey({
            point: BabyJubJubPoint({ x: BN254.ScalarField.wrap(uint256(0)), y: BN254.ScalarField.wrap(uint256(1)) })
        });

        // Call the shared deployment logic
        uint256 dummyProtocolFee = 1;
        address dummyExternalFeeRecipient = address(0x42);
        deployCore(
            msg.sender, // Use deployer as owner
            dummyProtocolFee,
            dummyExternalFeeRecipient,
            protocolFeeKey,
            permit2,
            weth,
            vm
        );
        vm.stopBroadcast();
    }
}

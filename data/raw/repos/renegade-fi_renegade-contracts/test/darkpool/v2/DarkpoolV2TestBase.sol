// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { ERC20Mock } from "oz-contracts/mocks/token/ERC20Mock.sol";
import { WethMock } from "test-contracts/WethMock.sol";
import { IWETH9 } from "renegade-lib/interfaces/IWETH9.sol";
import { IPermit2 } from "permit2-lib/interfaces/IPermit2.sol";
import { DeployPermit2 } from "permit2-test/utils/DeployPermit2.sol";
import { TestUtils } from "test-utils/TestUtils.sol";
import { HuffDeployer } from "foundry-huff/HuffDeployer.sol";
import { Vm } from "forge-std/Vm.sol";
import { EncryptionKey, BabyJubJubPoint } from "renegade-lib/Ciphertext.sol";
import { DarkpoolV2 } from "darkpoolv2-contracts/DarkpoolV2.sol";
import { DarkpoolV2Proxy } from "darkpoolv2-proxies/DarkpoolV2Proxy.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";
import { TransferExecutor } from "darkpoolv1-contracts/TransferExecutor.sol";
import { NullifierLib } from "renegade-lib/NullifierSet.sol";
import { IHasher } from "renegade-lib/interfaces/IHasher.sol";
import { IVerifier } from "darkpoolv2-interfaces/IVerifier.sol";
import { Verifier } from "darkpoolv2-contracts/Verifier.sol";
import { IVkeys } from "darkpoolv2-interfaces/IVkeys.sol";
import { VKeys } from "darkpoolv2-contracts/vkeys/VKeys.sol";
import { GasSponsor } from "darkpoolv1-contracts/GasSponsor.sol";
import { GasSponsorProxy } from "darkpoolv1-proxies/GasSponsorProxy.sol";
import { IGasSponsor } from "darkpoolv1-interfaces/IGasSponsor.sol";

import { FixedPoint, FixedPointLib } from "renegade-lib/FixedPoint.sol";
import { TestVerifierV2 } from "test-contracts/TestVerifierV2.sol";
import { DarkpoolContracts } from "darkpoolv2-contracts/DarkpoolV2.sol";
import { DarkpoolV2 } from "darkpoolv2-contracts/DarkpoolV2.sol";

// solhint-disable-next-line max-states-count
contract DarkpoolV2TestBase is TestUtils {
    using NullifierLib for NullifierLib.NullifierSet;
    using FixedPointLib for FixedPoint;

    /// @notice The protocol fee rate used for testing
    /// @dev This is the fixed point representation of 0.0001 (1bp)
    /// @dev computed as `floor(0.0001 * 2 ** 63)`
    uint256 public constant TEST_PROTOCOL_FEE = 922_337_203_685_477;

    IDarkpoolV2 public darkpool;
    /// @dev A separate instance of the darkpool contract without a verifier mock
    IDarkpoolV2 public darkpoolRealVerifier;
    IHasher public hasher;
    IVkeys public vkeys;
    NullifierLib.NullifierSet private testNullifierSet;
    IPermit2 public permit2;
    ERC20Mock public quoteToken;
    ERC20Mock public baseToken;
    WethMock public weth;
    TransferExecutor public transferExecutor;
    /// @dev Gas sponsor contract (points to the darkpool with disabled verification)
    IGasSponsor public gasSponsor;

    address public protocolFeeAddr;
    address public relayerFeeAddr;
    FixedPoint public relayerFeeRateFixedPoint;
    address public darkpoolOwner;
    address public gasSponsorOwner;
    address public gasSponsorAuthAddress;
    /// @dev Private key for the gas sponsor auth address
    uint256 public gasSponsorAuthPrivateKey;

    // Implementation contracts (for reference)
    DarkpoolV2 public darkpoolImpl;
    DarkpoolV2 public darkpoolRealVerifierImpl;
    GasSponsor public gasSponsorImpl;

    function setUp() public virtual {
        deployTokens();
        deployDarkpool();
        deployGasSponsor();
    }

    /**
     * @dev Deploys the ERC20 tokens and funds the WETH contract
     */
    function deployTokens() internal {
        // Deploy a Permit2 instance for testing
        DeployPermit2 permit2Deployer = new DeployPermit2();
        permit2 = IPermit2(permit2Deployer.deployPermit2());

        // Deploy mock tokens for testing
        quoteToken = new ERC20Mock();
        baseToken = new ERC20Mock();
        weth = new WethMock();

        // Capitalize the weth contract
        vm.deal(address(weth), 100_000_000_000_000 ether);
    }

    /**
     * @dev Deploys the darkpool and all its dependencies
     */
    function deployDarkpool() internal {
        // Deploy the darkpool implementation contracts
        hasher = IHasher(HuffDeployer.deploy("libraries/poseidon2/poseidonHasher"));
        IVerifier verifier = new TestVerifierV2();
        vkeys = new VKeys();
        IVerifier realVerifier = new Verifier(vkeys);
        EncryptionKey memory protocolFeeKey = randomEncryptionKey();

        // Deploy TransferExecutor
        transferExecutor = new TransferExecutor();

        // Set admin and protocol fee addresses
        darkpoolOwner = vm.randomAddress();
        protocolFeeAddr = vm.randomAddress();
        relayerFeeAddr = vm.randomAddress();

        // Deploy implementation contracts
        darkpoolImpl = new DarkpoolV2();
        darkpoolRealVerifierImpl = new DarkpoolV2();
        relayerFeeRateFixedPoint = randomFee();

        // Deploy the darkpool with a fake verifier
        DarkpoolV2Proxy darkpoolProxy = new DarkpoolV2Proxy(
            address(darkpoolImpl),
            darkpoolOwner,
            TEST_PROTOCOL_FEE,
            protocolFeeAddr,
            protocolFeeKey,
            IWETH9(address(weth)),
            hasher,
            vkeys,
            verifier,
            permit2,
            address(transferExecutor)
        );
        darkpool = IDarkpoolV2(address(darkpoolProxy));

        // Deploy the darkpool with the real verifier
        DarkpoolV2Proxy darkpoolRealVerifierProxy = new DarkpoolV2Proxy(
            address(darkpoolRealVerifierImpl),
            darkpoolOwner,
            TEST_PROTOCOL_FEE,
            protocolFeeAddr,
            protocolFeeKey,
            IWETH9(address(weth)),
            hasher,
            vkeys,
            realVerifier,
            permit2,
            address(transferExecutor)
        );
        darkpoolRealVerifier = IDarkpoolV2(address(darkpoolRealVerifierProxy));
    }

    /**
     * @dev Deploys the gas sponsor contract pointing to the darkpool with disabled verification
     */
    function deployGasSponsor() internal {
        // Set gas sponsor owner
        gasSponsorOwner = vm.randomAddress();

        // Create a wallet for gas sponsor auth with a known private key
        Vm.Wallet memory wallet = vm.createWallet("gas_sponsor_auth");
        gasSponsorAuthPrivateKey = wallet.privateKey;
        gasSponsorAuthAddress = wallet.addr;

        // Deploy gas sponsor implementation contract
        gasSponsorImpl = new GasSponsor();

        // Deploy gas sponsor proxy, pointing to the darkpool with disabled verification
        GasSponsorProxy gasSponsorProxy = new GasSponsorProxy(
            address(gasSponsorImpl),
            gasSponsorOwner,
            address(darkpool), // Point to the darkpool with test verifier
            gasSponsorAuthAddress
        );
        gasSponsor = IGasSponsor(address(gasSponsorProxy));

        // Fund the gas sponsor with some ETH for gas refunds
        vm.deal(address(gasSponsor), 10 ether);
    }

    // -----------
    // | Helpers |
    // -----------

    // --- Fuzzing Helpers --- //

    /// @notice Generate a random encryption key
    /// @dev For our purposes, this key does not need to be on the curve,
    /// @dev no curve arithmetic is performed on it
    function randomEncryptionKey() internal returns (EncryptionKey memory key) {
        key = EncryptionKey({ point: BabyJubJubPoint({ x: randomScalar(), y: randomScalar() }) });
    }

    /// @notice Generate a random fee
    function randomFee() internal returns (FixedPoint memory fee) {
        uint256 minRepr = 0;
        uint256 maxRepr = 2 ** FixedPointLib.FIXED_POINT_PRECISION_BITS / 100; // 1%
        FixedPoint memory min = FixedPointLib.wrap(minRepr);
        FixedPoint memory max = FixedPointLib.wrap(maxRepr);
        fee = randomFixedPoint(min, max);
    }

    /// @notice Generate a random fixed point between two fixed point values
    /// @dev This is inclusive of the bounds, so [min, max]
    /// @param min The minimum fixed point value
    /// @param max The maximum fixed point value
    /// @return result The random fixed point value
    function randomFixedPoint(
        FixedPoint memory min,
        FixedPoint memory max
    )
        internal
        returns (FixedPoint memory result)
    {
        uint256 minRepr = min.repr;
        uint256 maxRepr = max.repr;
        uint256 randomRepr = vm.randomUint(minRepr, maxRepr);
        result = FixedPointLib.wrap(randomRepr);
    }

    // --- Signatures --- //

    /// @dev Creates a signature for gas sponsorship using the stored private key
    /// @param nonce The nonce to use for the signature
    /// @param refundAddress The refund address
    /// @param refundAmount The refund amount
    /// @return signature The signed sponsorship payload
    function signGasSponsorshipPayload(
        uint256 nonce,
        address refundAddress,
        uint256 refundAmount
    )
        internal
        view
        returns (bytes memory)
    {
        // Create message hash directly from encoded tuple (same as in GasSponsor._assertSponsorshipSignature)
        bytes32 messageHash = keccak256(abi.encode(nonce, refundAddress, refundAmount));

        // Sign the message hash with the private key
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(gasSponsorAuthPrivateKey, messageHash);
        return abi.encodePacked(r, s, v);
    }

    // --- Balances --- //

    /// @dev Get the base and quote token amounts for an address
    function baseQuoteBalances(address addr) public view returns (uint256 baseAmt, uint256 quoteAmt) {
        baseAmt = baseToken.balanceOf(addr);
        quoteAmt = quoteToken.balanceOf(addr);
    }

    /// @dev Get the base and quote token amounts for an address as an int256
    function baseQuoteBalancesSigned(address addr) public view returns (int256 baseAmt, int256 quoteAmt) {
        (uint256 baseAmtUint, uint256 quoteAmtUint) = baseQuoteBalances(addr);
        baseAmt = int256(baseAmtUint);
        quoteAmt = int256(quoteAmtUint);
    }

    /// @dev Get the weth and quote token balances for an address
    function wethQuoteBalances(address addr) public view returns (uint256 wethAmt, uint256 quoteAmt) {
        wethAmt = weth.balanceOf(addr);
        quoteAmt = quoteToken.balanceOf(addr);
    }

    /// @dev Get the ether and quote token balances for an address
    function etherQuoteBalances(address addr) public view returns (uint256 etherAmt, uint256 quoteAmt) {
        etherAmt = addr.balance;
        quoteAmt = quoteToken.balanceOf(addr);
    }

    /// @notice Create a DarkpoolContracts struct from the test's contract instances
    /// @param verifier The verifier to use (if not provided, uses the darkpool's verifier)
    function getSettlementContracts(IVerifier verifier) public view returns (DarkpoolContracts memory contracts) {
        contracts = DarkpoolContracts({
            hasher: hasher,
            verifier: verifier,
            weth: IWETH9(address(weth)),
            permit2: permit2,
            vkeys: vkeys
        });
    }

    /// @notice Create a DarkpoolContracts struct using the darkpool's verifier
    function getSettlementContracts() public view returns (DarkpoolContracts memory contracts) {
        DarkpoolV2 darkpoolImpl = DarkpoolV2(address(darkpool));
        contracts = getSettlementContracts(darkpoolImpl.verifier());
    }
}

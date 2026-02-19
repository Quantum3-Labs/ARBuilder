"""
Oracle templates for Chainlink integration.
These templates provide scaffolding for oracle-connected dApps on Arbitrum.

Templates:
- Price Feed: Chainlink price oracle integration
- VRF: Verifiable Random Function for randomness
- Automation: Chainlink Keepers/Automation
- Functions: Chainlink Functions for off-chain compute
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class OracleTemplate:
    """A curated oracle template."""

    name: str
    description: str
    oracle_type: str  # "price_feed" | "vrf" | "automation" | "functions"
    features: List[str]
    solidity_code: str
    stylus_code: Optional[str]  # Stylus equivalent if available
    frontend_hook: str  # React hook for frontend integration
    dependencies: Dict[str, str]
    networks: Dict[str, dict]  # Network-specific addresses


# Chainlink Price Feed Template
PRICE_FEED_TEMPLATE = OracleTemplate(
    name="Chainlink Price Feed",
    description="Get real-time price data from Chainlink oracles",
    oracle_type="price_feed",
    features=[
        "Real-time prices",
        "Multiple pairs",
        "Decimal handling",
        "Staleness checks",
    ],
    solidity_code='''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

/**
 * @title PriceFeedConsumer
 * @notice Get the latest price from Chainlink Price Feeds
 */
contract PriceFeedConsumer {
    AggregatorV3Interface internal priceFeed;

    // Arbitrum Sepolia ETH/USD: 0xd30e2101a97dcbAeBCBC04F14C3f624E67A35165
    // Arbitrum One ETH/USD: 0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612
    constructor(address _priceFeed) {
        priceFeed = AggregatorV3Interface(_priceFeed);
    }

    /**
     * @notice Returns the latest price
     */
    function getLatestPrice() public view returns (int256) {
        (
            /* uint80 roundID */,
            int256 price,
            /* uint256 startedAt */,
            /* uint256 timeStamp */,
            /* uint80 answeredInRound */
        ) = priceFeed.latestRoundData();
        return price;
    }

    /**
     * @notice Returns the price with staleness check
     * @param maxStaleness Maximum allowed time since last update (seconds)
     */
    function getLatestPriceWithStalenessCheck(uint256 maxStaleness)
        public
        view
        returns (int256 price, bool isStale)
    {
        (
            /* uint80 roundID */,
            int256 answer,
            /* uint256 startedAt */,
            uint256 updatedAt,
            /* uint80 answeredInRound */
        ) = priceFeed.latestRoundData();

        isStale = (block.timestamp - updatedAt) > maxStaleness;
        return (answer, isStale);
    }

    /**
     * @notice Returns the number of decimals for the price feed
     */
    function getDecimals() public view returns (uint8) {
        return priceFeed.decimals();
    }

    /**
     * @notice Returns the description of the price feed
     */
    function getDescription() public view returns (string memory) {
        return priceFeed.description();
    }
}
''',
    stylus_code='''#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]
extern crate alloc;

use alloc::vec::Vec;
use stylus_sdk::{
    alloy_primitives::{Address, I256, U256},
    call::RawCall,
    prelude::*,
};

// Chainlink AggregatorV3Interface function selectors
const LATEST_ROUND_DATA_SELECTOR: [u8; 4] = [0xfe, 0xaf, 0x96, 0x8c]; // latestRoundData()
const DECIMALS_SELECTOR: [u8; 4] = [0x31, 0x3c, 0xe5, 0x67]; // decimals()

sol_storage! {
    #[entrypoint]
    pub struct PriceFeedConsumer {
        address price_feed;
    }
}

#[public]
impl PriceFeedConsumer {
    /// Initialize with price feed address
    pub fn initialize(&mut self, price_feed: Address) {
        self.price_feed.set(price_feed);
    }

    /// Get the latest price from Chainlink
    pub fn get_latest_price(&self) -> Result<I256, Vec<u8>> {
        let feed_address = self.price_feed.get();

        // Call latestRoundData() on the price feed
        let result = RawCall::new()
            .call(feed_address, &LATEST_ROUND_DATA_SELECTOR)?;

        // Decode the response (skip roundId, get price at offset 32)
        if result.len() >= 64 {
            let price_bytes: [u8; 32] = result[32..64].try_into().unwrap_or([0u8; 32]);
            Ok(I256::from_be_bytes(price_bytes))
        } else {
            Err(b"Invalid response".to_vec())
        }
    }

    /// Get decimals from the price feed
    pub fn get_decimals(&self) -> Result<u8, Vec<u8>> {
        let feed_address = self.price_feed.get();

        let result = RawCall::new()
            .call(feed_address, &DECIMALS_SELECTOR)?;

        if !result.is_empty() {
            Ok(result[result.len() - 1])
        } else {
            Err(b"Invalid response".to_vec())
        }
    }
}
''',
    frontend_hook='''"use client";

import { useReadContract } from 'wagmi';
import { formatUnits } from 'viem';

const PRICE_FEED_ABI = [
  {
    name: 'latestRoundData',
    type: 'function',
    stateMutability: 'view',
    inputs: [],
    outputs: [
      { name: 'roundId', type: 'uint80' },
      { name: 'answer', type: 'int256' },
      { name: 'startedAt', type: 'uint256' },
      { name: 'updatedAt', type: 'uint256' },
      { name: 'answeredInRound', type: 'uint80' },
    ],
  },
  {
    name: 'decimals',
    type: 'function',
    stateMutability: 'view',
    inputs: [],
    outputs: [{ name: '', type: 'uint8' }],
  },
] as const;

// Chainlink Price Feed addresses on Arbitrum
const PRICE_FEEDS = {
  'ETH/USD': {
    arbitrum: '0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612',
    arbitrumSepolia: '0xd30e2101a97dcbAeBCBC04F14C3f624E67A35165',
  },
  'BTC/USD': {
    arbitrum: '0x6ce185860a4963106506C203335A583Af172E1b5',
    arbitrumSepolia: '0x56a43EB56Da12C0dc1D972ACb089c06a5dEF8e69',
  },
} as const;

interface UsePriceFeedOptions {
  pair: keyof typeof PRICE_FEEDS;
  network?: 'arbitrum' | 'arbitrumSepolia';
  refetchInterval?: number;
}

export function usePriceFeed({
  pair,
  network = 'arbitrumSepolia',
  refetchInterval = 30000,
}: UsePriceFeedOptions) {
  const feedAddress = PRICE_FEEDS[pair][network] as `0x${string}`;

  const { data: roundData, isLoading, error } = useReadContract({
    address: feedAddress,
    abi: PRICE_FEED_ABI,
    functionName: 'latestRoundData',
    query: { refetchInterval },
  });

  const { data: decimals } = useReadContract({
    address: feedAddress,
    abi: PRICE_FEED_ABI,
    functionName: 'decimals',
  });

  const price = roundData
    ? parseFloat(formatUnits(BigInt(roundData[1].toString()), decimals || 8))
    : null;

  const updatedAt = roundData ? new Date(Number(roundData[3]) * 1000) : null;

  return {
    price,
    decimals: decimals ? Number(decimals) : 8,
    updatedAt,
    isLoading,
    error,
  };
}
''',
    dependencies={
        "@chainlink/contracts": "^1.1.0",
    },
    networks={
        "arbitrum": {
            "ETH/USD": "0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612",
            "BTC/USD": "0x6ce185860a4963106506C203335A583Af172E1b5",
            "LINK/USD": "0x86E53CF1B870786351Da77A57575e79CB55812CB",
        },
        "arbitrumSepolia": {
            "ETH/USD": "0xd30e2101a97dcbAeBCBC04F14C3f624E67A35165",
            "BTC/USD": "0x56a43EB56Da12C0dc1D972ACb089c06a5dEF8e69",
        },
    },
)


# Chainlink VRF Template
VRF_TEMPLATE = OracleTemplate(
    name="Chainlink VRF",
    description="Verifiable Random Function for provably fair randomness",
    oracle_type="vrf",
    features=[
        "Provable randomness",
        "Subscription model",
        "Multiple random words",
        "Callback pattern",
    ],
    solidity_code='''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@chainlink/contracts/src/v0.8/vrf/dev/VRFConsumerBaseV2Plus.sol";
import "@chainlink/contracts/src/v0.8/vrf/dev/libraries/VRFV2PlusClient.sol";

/**
 * @title VRFConsumer
 * @notice Request verifiable random numbers from Chainlink VRF
 */
contract VRFConsumer is VRFConsumerBaseV2Plus {
    // Arbitrum Sepolia VRF Coordinator
    // address constant VRF_COORDINATOR = 0x5CE8D5A2BC84beb22a398CCA51996F7930313D61;

    uint256 public s_subscriptionId;
    bytes32 public s_keyHash;

    // Request tracking
    mapping(uint256 => address) public s_requestIdToSender;
    mapping(address => uint256[]) public s_userRandomWords;

    // VRF configuration
    uint32 constant CALLBACK_GAS_LIMIT = 100000;
    uint16 constant REQUEST_CONFIRMATIONS = 3;
    uint32 constant NUM_WORDS = 1;

    event RandomnessRequested(uint256 indexed requestId, address indexed requester);
    event RandomnessFulfilled(uint256 indexed requestId, uint256[] randomWords);

    constructor(
        address vrfCoordinator,
        uint256 subscriptionId,
        bytes32 keyHash
    ) VRFConsumerBaseV2Plus(vrfCoordinator) {
        s_subscriptionId = subscriptionId;
        s_keyHash = keyHash;
    }

    /**
     * @notice Request random words
     * @return requestId The ID of the VRF request
     */
    function requestRandomWords() external returns (uint256 requestId) {
        requestId = s_vrfCoordinator.requestRandomWords(
            VRFV2PlusClient.RandomWordsRequest({
                keyHash: s_keyHash,
                subId: s_subscriptionId,
                requestConfirmations: REQUEST_CONFIRMATIONS,
                callbackGasLimit: CALLBACK_GAS_LIMIT,
                numWords: NUM_WORDS,
                extraArgs: VRFV2PlusClient._argsToBytes(
                    VRFV2PlusClient.ExtraArgsV1({nativePayment: false})
                )
            })
        );

        s_requestIdToSender[requestId] = msg.sender;
        emit RandomnessRequested(requestId, msg.sender);
    }

    /**
     * @notice Callback function called by VRF Coordinator
     */
    function fulfillRandomWords(
        uint256 requestId,
        uint256[] calldata randomWords
    ) internal override {
        address requester = s_requestIdToSender[requestId];
        s_userRandomWords[requester] = randomWords;
        emit RandomnessFulfilled(requestId, randomWords);
    }

    /**
     * @notice Get random words for a user
     */
    function getRandomWords(address user) external view returns (uint256[] memory) {
        return s_userRandomWords[user];
    }

    /**
     * @notice Get a random number in range [0, max)
     */
    function getRandomInRange(address user, uint256 max) external view returns (uint256) {
        uint256[] memory words = s_userRandomWords[user];
        require(words.length > 0, "No random words");
        return words[0] % max;
    }
}
''',
    stylus_code=None,  # VRF requires complex callback pattern, Solidity recommended
    frontend_hook='''"use client";

import { useState } from 'react';
import { useWriteContract, useWaitForTransactionReceipt, useReadContract } from 'wagmi';
import { parseAbi } from 'viem';

const VRF_ABI = parseAbi([
  'function requestRandomWords() external returns (uint256)',
  'function getRandomWords(address user) external view returns (uint256[])',
  'function getRandomInRange(address user, uint256 max) external view returns (uint256)',
  'event RandomnessRequested(uint256 indexed requestId, address indexed requester)',
  'event RandomnessFulfilled(uint256 indexed requestId, uint256[] randomWords)',
]);

interface UseVRFOptions {
  contractAddress: `0x${string}`;
  userAddress?: `0x${string}`;
}

export function useVRF({ contractAddress, userAddress }: UseVRFOptions) {
  const [requestId, setRequestId] = useState<bigint | null>(null);

  const { writeContract, data: hash, isPending } = useWriteContract();
  const { isLoading: isConfirming } = useWaitForTransactionReceipt({ hash });

  const { data: randomWords, refetch: refetchRandomWords } = useReadContract({
    address: contractAddress,
    abi: VRF_ABI,
    functionName: 'getRandomWords',
    args: userAddress ? [userAddress] : undefined,
    query: { enabled: !!userAddress },
  });

  const requestRandomness = () => {
    writeContract({
      address: contractAddress,
      abi: VRF_ABI,
      functionName: 'requestRandomWords',
    });
  };

  return {
    requestRandomness,
    randomWords: randomWords as bigint[] | undefined,
    refetchRandomWords,
    isPending,
    isConfirming,
    isWaitingForFulfillment: isConfirming,
    hash,
  };
}
''',
    dependencies={
        "@chainlink/contracts": "^1.1.0",
    },
    networks={
        "arbitrum": {
            "coordinator": "0x41034678D6C633D8a95c75e1138A360a28bA15d1",
            "keyHash": "0x72d2b016bb5b62912afea355ebf33b91319f828738b111b723b78696b9847b63",
        },
        "arbitrumSepolia": {
            "coordinator": "0x5CE8D5A2BC84beb22a398CCA51996F7930313D61",
            "keyHash": "0x1770bdc7eec7771f7ba4ffd640f34260d7f095b79c92d34a5b2551d6f6cfd2be",
        },
    },
)


# Chainlink Automation Template
AUTOMATION_TEMPLATE = OracleTemplate(
    name="Chainlink Automation",
    description="Automate smart contract functions with Chainlink Keepers",
    oracle_type="automation",
    features=[
        "Time-based triggers",
        "Condition-based triggers",
        "Custom logic",
        "Gas optimization",
    ],
    solidity_code='''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@chainlink/contracts/src/v0.8/automation/interfaces/AutomationCompatibleInterface.sol";

/**
 * @title AutomationConsumer
 * @notice Contract compatible with Chainlink Automation
 */
contract AutomationConsumer is AutomationCompatibleInterface {
    uint256 public counter;
    uint256 public lastTimestamp;
    uint256 public immutable interval;

    event CounterIncremented(uint256 indexed newCounter, uint256 timestamp);

    constructor(uint256 updateInterval) {
        interval = updateInterval;
        lastTimestamp = block.timestamp;
    }

    /**
     * @notice Checks if upkeep is needed
     * @dev Called by Chainlink Automation nodes
     */
    function checkUpkeep(bytes calldata /* checkData */)
        external
        view
        override
        returns (bool upkeepNeeded, bytes memory performData)
    {
        upkeepNeeded = (block.timestamp - lastTimestamp) > interval;
        performData = "";
    }

    /**
     * @notice Performs the upkeep
     * @dev Called by Chainlink Automation when checkUpkeep returns true
     */
    function performUpkeep(bytes calldata /* performData */) external override {
        if ((block.timestamp - lastTimestamp) > interval) {
            lastTimestamp = block.timestamp;
            counter = counter + 1;
            emit CounterIncremented(counter, block.timestamp);
        }
    }

    /**
     * @notice Get time until next upkeep
     */
    function getTimeUntilUpkeep() external view returns (uint256) {
        uint256 timePassed = block.timestamp - lastTimestamp;
        if (timePassed >= interval) {
            return 0;
        }
        return interval - timePassed;
    }
}

/**
 * @title ConditionBasedAutomation
 * @notice Example of condition-based automation
 */
contract ConditionBasedAutomation is AutomationCompatibleInterface {
    uint256 public balance;
    uint256 public threshold;
    address public owner;

    event BalanceReset(uint256 previousBalance, uint256 timestamp);

    constructor(uint256 _threshold) {
        threshold = _threshold;
        owner = msg.sender;
    }

    function deposit() external payable {
        balance += msg.value;
    }

    function checkUpkeep(bytes calldata /* checkData */)
        external
        view
        override
        returns (bool upkeepNeeded, bytes memory performData)
    {
        upkeepNeeded = balance >= threshold;
        performData = "";
    }

    function performUpkeep(bytes calldata /* performData */) external override {
        if (balance >= threshold) {
            uint256 previousBalance = balance;
            balance = 0;
            payable(owner).transfer(previousBalance);
            emit BalanceReset(previousBalance, block.timestamp);
        }
    }
}
''',
    stylus_code='''#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]
extern crate alloc;

use alloc::vec::Vec;
use stylus_sdk::{
    alloy_primitives::U256,
    prelude::*,
};

sol_storage! {
    #[entrypoint]
    pub struct AutomationConsumer {
        uint256 counter;
        uint256 last_timestamp;
        uint256 interval;
    }
}

#[public]
impl AutomationConsumer {
    /// Initialize the automation consumer
    pub fn initialize(&mut self, update_interval: U256) {
        self.interval.set(update_interval);
        self.last_timestamp.set(U256::from(self.vm().block_timestamp()));
    }

    /// Check if upkeep is needed (called off-chain by Automation nodes)
    pub fn check_upkeep(&self) -> (bool, Vec<u8>) {
        let current_time = U256::from(self.vm().block_timestamp());
        let last_time = self.last_timestamp.get();
        let interval = self.interval.get();

        let upkeep_needed = current_time - last_time > interval;
        (upkeep_needed, Vec::new())
    }

    /// Perform the upkeep (called by Automation when check_upkeep returns true)
    pub fn perform_upkeep(&mut self) {
        let current_time = U256::from(self.vm().block_timestamp());
        let last_time = self.last_timestamp.get();
        let interval = self.interval.get();

        if current_time - last_time > interval {
            self.last_timestamp.set(current_time);
            let counter = self.counter.get();
            self.counter.set(counter + U256::from(1));
        }
    }

    /// Get current counter value
    pub fn counter(&self) -> U256 {
        self.counter.get()
    }

    /// Get time until next upkeep
    pub fn get_time_until_upkeep(&self) -> U256 {
        let current_time = U256::from(self.vm().block_timestamp());
        let last_time = self.last_timestamp.get();
        let interval = self.interval.get();
        let time_passed = current_time - last_time;

        if time_passed >= interval {
            U256::ZERO
        } else {
            interval - time_passed
        }
    }
}
''',
    frontend_hook='''"use client";

import { useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { parseAbi } from 'viem';

const AUTOMATION_ABI = parseAbi([
  'function counter() view returns (uint256)',
  'function lastTimestamp() view returns (uint256)',
  'function interval() view returns (uint256)',
  'function getTimeUntilUpkeep() view returns (uint256)',
  'function checkUpkeep(bytes) view returns (bool, bytes)',
  'function performUpkeep(bytes)',
]);

interface UseAutomationOptions {
  contractAddress: `0x${string}`;
  refetchInterval?: number;
}

export function useAutomation({
  contractAddress,
  refetchInterval = 5000,
}: UseAutomationOptions) {
  const { data: counter } = useReadContract({
    address: contractAddress,
    abi: AUTOMATION_ABI,
    functionName: 'counter',
    query: { refetchInterval },
  });

  const { data: timeUntilUpkeep } = useReadContract({
    address: contractAddress,
    abi: AUTOMATION_ABI,
    functionName: 'getTimeUntilUpkeep',
    query: { refetchInterval },
  });

  const { data: checkResult } = useReadContract({
    address: contractAddress,
    abi: AUTOMATION_ABI,
    functionName: 'checkUpkeep',
    args: ['0x'],
    query: { refetchInterval },
  });

  const { writeContract, data: hash, isPending } = useWriteContract();
  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({ hash });

  const manualUpkeep = () => {
    writeContract({
      address: contractAddress,
      abi: AUTOMATION_ABI,
      functionName: 'performUpkeep',
      args: ['0x'],
    });
  };

  return {
    counter: counter as bigint | undefined,
    timeUntilUpkeep: timeUntilUpkeep as bigint | undefined,
    upkeepNeeded: checkResult ? (checkResult as [boolean, string])[0] : false,
    manualUpkeep,
    isPending,
    isConfirming,
    isSuccess,
  };
}
''',
    dependencies={
        "@chainlink/contracts": "^1.1.0",
    },
    networks={
        "arbitrum": {
            "registry": "0x37D9dC70bfcd8BC77Ec2858836B923c560E891D1",
            "registrar": "0x8194399B3f11c3e0A4Eb95A0a7b42dB7F9c2A0B3",
        },
        "arbitrumSepolia": {
            "registry": "0x1a80D5a50b7cfD8Eb1e8Cf4A1A7bC98E4d66aE0b",
            "registrar": "0x5E8Db42F1E5D4D09b97a3dE6aee69aE8A0d61b1A",
        },
    },
)


# Chainlink Functions Template
FUNCTIONS_TEMPLATE = OracleTemplate(
    name="Chainlink Functions",
    description="Execute custom JavaScript on Chainlink's decentralized oracle network",
    oracle_type="functions",
    features=[
        "Custom JavaScript",
        "API requests",
        "Off-chain compute",
        "Decentralized execution",
    ],
    solidity_code='''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {FunctionsClient} from "@chainlink/contracts/src/v0.8/functions/v1_0_0/FunctionsClient.sol";
import {FunctionsRequest} from "@chainlink/contracts/src/v0.8/functions/v1_0_0/libraries/FunctionsRequest.sol";

/**
 * @title FunctionsConsumer
 * @notice Execute custom JavaScript using Chainlink Functions
 */
contract FunctionsConsumer is FunctionsClient {
    using FunctionsRequest for FunctionsRequest.Request;

    bytes32 public s_lastRequestId;
    bytes public s_lastResponse;
    bytes public s_lastError;

    uint64 public s_subscriptionId;
    bytes32 public s_donId;

    event Response(bytes32 indexed requestId, bytes response, bytes err);

    constructor(
        address router,
        uint64 subscriptionId,
        bytes32 donId
    ) FunctionsClient(router) {
        s_subscriptionId = subscriptionId;
        s_donId = donId;
    }

    /**
     * @notice Execute a JavaScript function
     * @param source The JavaScript source code
     * @param args Arguments to pass to the function
     * @param gasLimit Callback gas limit
     */
    function executeRequest(
        string calldata source,
        string[] calldata args,
        uint32 gasLimit
    ) external returns (bytes32 requestId) {
        FunctionsRequest.Request memory req;
        req.initializeRequestForInlineJavaScript(source);
        if (args.length > 0) {
            req.setArgs(args);
        }

        s_lastRequestId = _sendRequest(
            req.encodeCBOR(),
            s_subscriptionId,
            gasLimit,
            s_donId
        );

        return s_lastRequestId;
    }

    /**
     * @notice Callback function for fulfilled requests
     */
    function fulfillRequest(
        bytes32 requestId,
        bytes memory response,
        bytes memory err
    ) internal override {
        s_lastResponse = response;
        s_lastError = err;
        emit Response(requestId, response, err);
    }

    /**
     * @notice Get the last response
     */
    function getLastResponse() external view returns (bytes memory) {
        return s_lastResponse;
    }

    /**
     * @notice Get the last error
     */
    function getLastError() external view returns (bytes memory) {
        return s_lastError;
    }
}
''',
    stylus_code=None,  # Functions requires complex callback pattern
    frontend_hook='''"use client";

import { useState } from 'react';
import { useWriteContract, useWaitForTransactionReceipt, useReadContract } from 'wagmi';
import { parseAbi, toHex, fromHex } from 'viem';

const FUNCTIONS_ABI = parseAbi([
  'function executeRequest(string source, string[] args, uint32 gasLimit) returns (bytes32)',
  'function getLastResponse() view returns (bytes)',
  'function getLastError() view returns (bytes)',
  's_lastRequestId() view returns (bytes32)',
]);

// Example JavaScript source for Chainlink Functions
const EXAMPLE_SOURCE = `
const apiResponse = await Functions.makeHttpRequest({
  url: "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
});

if (apiResponse.error) {
  throw Error("Request failed");
}

const price = apiResponse.data.ethereum.usd;
return Functions.encodeUint256(Math.round(price * 100));
`;

interface UseFunctionsOptions {
  contractAddress: `0x${string}`;
}

export function useFunctions({ contractAddress }: UseFunctionsOptions) {
  const [source, setSource] = useState(EXAMPLE_SOURCE);

  const { writeContract, data: hash, isPending } = useWriteContract();
  const { isLoading: isConfirming } = useWaitForTransactionReceipt({ hash });

  const { data: lastResponse, refetch: refetchResponse } = useReadContract({
    address: contractAddress,
    abi: FUNCTIONS_ABI,
    functionName: 'getLastResponse',
  });

  const { data: lastError } = useReadContract({
    address: contractAddress,
    abi: FUNCTIONS_ABI,
    functionName: 'getLastError',
  });

  const executeRequest = (customSource?: string, args: string[] = []) => {
    writeContract({
      address: contractAddress,
      abi: FUNCTIONS_ABI,
      functionName: 'executeRequest',
      args: [customSource || source, args, 300000],
    });
  };

  // Decode response as string or number
  const decodedResponse = lastResponse
    ? fromHex(lastResponse as `0x${string}`, 'string')
    : null;

  return {
    source,
    setSource,
    executeRequest,
    lastResponse: decodedResponse,
    lastError: lastError ? fromHex(lastError as `0x${string}`, 'string') : null,
    isPending,
    isConfirming,
    refetchResponse,
    EXAMPLE_SOURCE,
  };
}
''',
    dependencies={
        "@chainlink/contracts": "^1.1.0",
    },
    networks={
        "arbitrum": {
            "router": "0x97083E831F8F0638855e2A515c90EdCF158DF238",
            "donId": "0x66756e2d617262697472756d2d6d61696e6e65742d3100000000000000000000",
        },
        "arbitrumSepolia": {
            "router": "0x234a5fb5Bd614a7AA2FfAB244D603Ab0e5C3C12a",
            "donId": "0x66756e2d617262697472756d2d7365706f6c69612d3100000000000000000000",
        },
    },
)


# All templates indexed by type
ORACLE_TEMPLATES = {
    "price_feed": PRICE_FEED_TEMPLATE,
    "vrf": VRF_TEMPLATE,
    "automation": AUTOMATION_TEMPLATE,
    "functions": FUNCTIONS_TEMPLATE,
}


def select_oracle_template(prompt: str) -> OracleTemplate:
    """Select the best oracle template based on prompt keywords."""
    lower_prompt = prompt.lower()

    if any(kw in lower_prompt for kw in ["price", "feed", "eth/usd", "btc/usd", "oracle"]):
        return PRICE_FEED_TEMPLATE

    if any(kw in lower_prompt for kw in ["random", "vrf", "lottery", "fair", "dice"]):
        return VRF_TEMPLATE

    if any(kw in lower_prompt for kw in ["automat", "keeper", "upkeep", "scheduled", "cron"]):
        return AUTOMATION_TEMPLATE

    if any(kw in lower_prompt for kw in ["function", "api", "http", "javascript", "compute"]):
        return FUNCTIONS_TEMPLATE

    return PRICE_FEED_TEMPLATE


def get_oracle_template(oracle_type: str) -> Optional[OracleTemplate]:
    """Get a specific oracle template by type."""
    return ORACLE_TEMPLATES.get(oracle_type)


def list_oracle_templates() -> List[OracleTemplate]:
    """List all available oracle templates."""
    return [
        PRICE_FEED_TEMPLATE,
        VRF_TEMPLATE,
        AUTOMATION_TEMPLATE,
        FUNCTIONS_TEMPLATE,
    ]

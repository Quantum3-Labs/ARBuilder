"""
Oracle Coding Rules Resource.

Provides coding guidelines and patterns for Chainlink oracle integration
on Arbitrum.
"""

ORACLE_CODING_RULES = {
    "name": "Oracle Coding Rules",
    "version": "1.0.0",
    "description": "Guidelines for integrating Chainlink oracles on Arbitrum",

    "chainlink_products": {
        "price_feeds": {
            "description": "Real-time price data from decentralized oracles",
            "use_cases": ["DeFi pricing", "Collateral valuation", "Token swaps"],
            "update_frequency": "Heartbeat or deviation-based (typically 1%)",
        },
        "vrf": {
            "description": "Verifiable Random Function for provable randomness",
            "use_cases": ["Gaming", "NFT minting", "Lotteries", "Fair selection"],
            "version": "V2.5",
        },
        "automation": {
            "description": "Decentralized contract automation (formerly Keepers)",
            "use_cases": ["Scheduled tasks", "Condition-based triggers", "Liquidations"],
            "payment": "LINK token for upkeep",
        },
        "functions": {
            "description": "Custom JavaScript execution on Chainlink DON",
            "use_cases": ["API calls", "Off-chain computation", "Data aggregation"],
            "version": "1.0",
        },
    },

    "arbitrum_addresses": {
        "arbitrum_one": {
            "price_feeds": {
                "ETH/USD": "0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612",
                "BTC/USD": "0x6ce185860a4963106506C203335A583Af172E1b5",
                "LINK/USD": "0x86E53CF1B870786351Da77A57575e79CB55812CB",
                "USDC/USD": "0x50834F3163758fcC1Df9973b6e91f0F0F0434aD3",
            },
            "vrf_coordinator": "0x41034678D6C633D8a95c75e1138A360a28bA15d1",
            "automation_registry": "0x37D9dC70bfcd8BC77Ec2858836B923c560E891D1",
            "functions_router": "0x97083E831F8F0638855e2A515c90EdCF158DF238",
        },
        "arbitrum_sepolia": {
            "price_feeds": {
                "ETH/USD": "0xd30e2101a97dcbAeBCBC04F14C3f624E67A35165",
                "BTC/USD": "0x56a43EB56Da12C0dc1D972ACb089c06a5dEF8e69",
            },
            "vrf_coordinator": "0x5CE8D5A2BC84beb22a398CCA51996F7930313D61",
            "functions_router": "0x234a5fb5Bd614a7AA2FfAB244D603Ab0e5C3C12a",
        },
    },

    "patterns": {
        "price_feed": {
            "solidity": '''interface AggregatorV3Interface {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
    function decimals() external view returns (uint8);
}

contract PriceConsumer {
    AggregatorV3Interface internal priceFeed;

    constructor(address _priceFeed) {
        priceFeed = AggregatorV3Interface(_priceFeed);
    }

    function getLatestPrice() public view returns (int256) {
        (,int256 price,,,) = priceFeed.latestRoundData();
        return price;
    }

    function getLatestPriceWithStalenessCheck(uint256 maxAge)
        public view returns (int256 price, bool isStale)
    {
        (,price,,uint256 updatedAt,) = priceFeed.latestRoundData();
        isStale = block.timestamp - updatedAt > maxAge;
    }
}''',
            "staleness_check": "Always check updatedAt to detect stale data",
            "decimals": "Most USD feeds use 8 decimals, check with decimals()",
        },

        "vrf_v2_5": {
            "subscription_model": '''// 1. Create subscription at vrf.chain.link
// 2. Fund with LINK tokens
// 3. Add consumer contract
// 4. Request randomness

contract VRFConsumer is VRFConsumerBaseV2Plus {
    uint256 public s_subscriptionId;
    bytes32 public s_keyHash;

    constructor(address coordinator, uint256 subId, bytes32 keyHash)
        VRFConsumerBaseV2Plus(coordinator)
    {
        s_subscriptionId = subId;
        s_keyHash = keyHash;
    }

    function requestRandomness() external returns (uint256 requestId) {
        requestId = s_vrfCoordinator.requestRandomWords(
            VRFV2PlusClient.RandomWordsRequest({
                keyHash: s_keyHash,
                subId: s_subscriptionId,
                requestConfirmations: 3,
                callbackGasLimit: 100000,
                numWords: 1,
                extraArgs: VRFV2PlusClient._argsToBytes(
                    VRFV2PlusClient.ExtraArgsV1({nativePayment: false})
                )
            })
        );
    }

    function fulfillRandomWords(
        uint256 requestId,
        uint256[] calldata randomWords
    ) internal override {
        // Use randomWords[0] for your logic
        // randomWords[0] % 100 for 0-99 range
    }
}''',
            "gas_limit": "Set callbackGasLimit based on fulfillRandomWords complexity",
            "confirmations": "More confirmations = more security, more latency",
        },

        "automation": {
            "time_based": '''contract TimeBasedAutomation is AutomationCompatibleInterface {
    uint256 public lastTimestamp;
    uint256 public interval;

    constructor(uint256 _interval) {
        interval = _interval;
        lastTimestamp = block.timestamp;
    }

    function checkUpkeep(bytes calldata)
        external view override
        returns (bool upkeepNeeded, bytes memory)
    {
        upkeepNeeded = (block.timestamp - lastTimestamp) > interval;
    }

    function performUpkeep(bytes calldata) external override {
        if ((block.timestamp - lastTimestamp) > interval) {
            lastTimestamp = block.timestamp;
            // Your automated logic here
        }
    }
}''',
            "condition_based": '''contract ConditionBasedAutomation is AutomationCompatibleInterface {
    uint256 public threshold;

    function checkUpkeep(bytes calldata)
        external view override
        returns (bool upkeepNeeded, bytes memory performData)
    {
        upkeepNeeded = someCondition();
        performData = abi.encode(additionalData);
    }

    function performUpkeep(bytes calldata performData) external override {
        // Decode performData if needed
        // Execute your logic
    }
}''',
            "registration": "Register at automation.chain.link",
        },

        "functions": {
            "basic_request": '''contract FunctionsConsumer is FunctionsClient {
    bytes32 public s_lastRequestId;
    bytes public s_lastResponse;

    function executeRequest(
        string calldata source,
        string[] calldata args,
        uint32 gasLimit
    ) external returns (bytes32) {
        FunctionsRequest.Request memory req;
        req.initializeRequestForInlineJavaScript(source);
        if (args.length > 0) {
            req.setArgs(args);
        }

        s_lastRequestId = _sendRequest(
            req.encodeCBOR(),
            subscriptionId,
            gasLimit,
            donId
        );
        return s_lastRequestId;
    }

    function fulfillRequest(
        bytes32 requestId,
        bytes memory response,
        bytes memory err
    ) internal override {
        s_lastResponse = response;
        // Decode response: uint256(bytes32(response))
    }
}''',
            "javascript_source": '''// Example: Fetch price from API
const response = await Functions.makeHttpRequest({
  url: "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
});

if (response.error) {
  throw Error("Request failed");
}

const price = response.data.ethereum.usd;
return Functions.encodeUint256(Math.round(price * 100));''',
        },
    },

    "best_practices": {
        "price_feeds": [
            "Always check for stale data with updatedAt",
            "Handle negative prices for some assets",
            "Use correct decimals for calculations",
            "Consider price deviation thresholds",
        ],
        "vrf": [
            "Store requestId to match with fulfillment",
            "Set appropriate callbackGasLimit",
            "Use randomness for fairness, not security",
            "Don't rely on randomness before fulfillment",
        ],
        "automation": [
            "Make checkUpkeep gas-efficient (view function)",
            "Validate conditions again in performUpkeep",
            "Handle failed upkeeps gracefully",
            "Monitor upkeep balance",
        ],
        "functions": [
            "Keep JavaScript source simple",
            "Handle API failures gracefully",
            "Use secrets for API keys",
            "Test locally with simulator first",
        ],
    },

    "security": {
        "price_manipulation": [
            "Use TWAP for large trades",
            "Check deviation from expected range",
            "Monitor for flash loan attacks",
        ],
        "vrf_security": [
            "Don't reveal random seed before reveal",
            "Use commit-reveal for high-stakes applications",
            "Verify callback comes from coordinator",
        ],
        "automation_security": [
            "Restrict performUpkeep to Automation registry",
            "Validate state before execution",
            "Implement reentrancy guards",
        ],
    },

    "dependencies": {
        "@chainlink/contracts": "^1.1.0",
    },

    "documentation": {
        "price_feeds": "https://docs.chain.link/data-feeds/price-feeds",
        "vrf": "https://docs.chain.link/vrf",
        "automation": "https://docs.chain.link/chainlink-automation",
        "functions": "https://docs.chain.link/chainlink-functions",
    },
}

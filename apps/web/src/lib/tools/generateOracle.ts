/**
 * Generate Chainlink oracle integration code (M3 tool)
 */

type OracleType = "price_feed" | "vrf" | "automation" | "functions";
type Network = "arbitrum-one" | "arbitrum-sepolia";

interface GenerateOracleArgs {
  oracleType: OracleType;
  network?: Network;
  feeds?: string[];
}

interface GenerateOracleResult {
  files: Record<string, string>;
  dependencies: Record<string, string>;
  addresses: Record<string, string>;
  setupInstructions: string[];
}

// Chainlink addresses on Arbitrum
const ADDRESSES: Record<Network, Record<string, Record<string, string>>> = {
  "arbitrum-one": {
    price_feeds: {
      "ETH/USD": "0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612",
      "BTC/USD": "0x6ce185860a4963106506C203335A583Af172E1b5",
      "LINK/USD": "0x86E53CF1B870786351Da77A57575e79CB55812CB",
      "USDC/USD": "0x50834F3163758fcC1Df9973b6e91f0F0F0434aD3",
      "ARB/USD": "0xb2A824043730FE05F3DA2efaFa1CBbe83fa548D6",
    },
    vrf: {
      coordinator: "0x41034678D6C633D8a95c75e1138A360a28bA15d1",
      keyHash: "0x72d2b016bb5b62912afea355ebf33b91319f828738b111b723b78696b9847b63",
    },
    automation: {
      registry: "0x37D9dC70bfcd8BC77Ec2858836B923c560E891D1",
    },
    functions: {
      router: "0x97083E831F8F0638855e2A515c90EdCF158DF238",
      donId: "0x66756e2d617262697472756d2d6d61696e6e65742d3100000000000000000000",
    },
  },
  "arbitrum-sepolia": {
    price_feeds: {
      "ETH/USD": "0xd30e2101a97dcbAeBCBC04F14C3f624E67A35165",
      "BTC/USD": "0x56a43EB56Da12C0dc1D972ACb089c06a5dEF8e69",
      "LINK/USD": "0x0FB99723Aee6f420beAD13e6bBB79b7E6F034298",
    },
    vrf: {
      coordinator: "0x5CE8D5A2BC84beb22a398CCA51996F7930313D61",
      keyHash: "0x1770bdc7eec7771f7ba4ffd640f34260d7f095b79c92d34a5b2551d6f6cfd2be",
    },
    automation: {
      registry: "0x54Bd93Ce1d6E1F55F6B09b7e8a5f3A2D6B4b7e7B",
    },
    functions: {
      router: "0x234a5fb5Bd614a7AA2FfAB244D603Ab0e5C3C12a",
      donId: "0x66756e2d617262697472756d2d7365706f6c69612d3100000000000000000000",
    },
  },
};

// Price Feed Contract
const PRICE_FEED_CONTRACT = `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface AggregatorV3Interface {
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

    /**
     * Returns the latest price with staleness check
     */
    function getLatestPrice() public view returns (int256 price, bool isStale) {
        (, price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        // Consider stale if not updated in 1 hour
        isStale = block.timestamp - updatedAt > 3600;
    }

    /**
     * Returns price scaled to 18 decimals
     */
    function getScaledPrice() public view returns (uint256) {
        (, int256 price, , , ) = priceFeed.latestRoundData();
        uint8 decimals = priceFeed.decimals();
        // Scale to 18 decimals
        return uint256(price) * 10 ** (18 - decimals);
    }
}
`;

// VRF Contract
const VRF_CONTRACT = `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {VRFConsumerBaseV2Plus} from "@chainlink/contracts/src/v0.8/vrf/dev/VRFConsumerBaseV2Plus.sol";
import {VRFV2PlusClient} from "@chainlink/contracts/src/v0.8/vrf/dev/libraries/VRFV2PlusClient.sol";

contract VRFConsumer is VRFConsumerBaseV2Plus {
    uint256 public s_subscriptionId;
    bytes32 public s_keyHash;

    // Mapping from requestId to random result
    mapping(uint256 => uint256[]) public s_randomWords;
    mapping(uint256 => bool) public s_requestFulfilled;

    event RandomnessRequested(uint256 indexed requestId);
    event RandomnessFulfilled(uint256 indexed requestId, uint256[] randomWords);

    constructor(
        address coordinator,
        uint256 subscriptionId,
        bytes32 keyHash
    ) VRFConsumerBaseV2Plus(coordinator) {
        s_subscriptionId = subscriptionId;
        s_keyHash = keyHash;
    }

    /**
     * Request random words
     * @param numWords Number of random words to request (max 500)
     */
    function requestRandomWords(uint32 numWords) external returns (uint256 requestId) {
        requestId = s_vrfCoordinator.requestRandomWords(
            VRFV2PlusClient.RandomWordsRequest({
                keyHash: s_keyHash,
                subId: s_subscriptionId,
                requestConfirmations: 3,
                callbackGasLimit: 100000,
                numWords: numWords,
                extraArgs: VRFV2PlusClient._argsToBytes(
                    VRFV2PlusClient.ExtraArgsV1({nativePayment: false})
                )
            })
        );

        emit RandomnessRequested(requestId);
    }

    /**
     * Callback function for VRF Coordinator
     */
    function fulfillRandomWords(
        uint256 requestId,
        uint256[] calldata randomWords
    ) internal override {
        s_randomWords[requestId] = randomWords;
        s_requestFulfilled[requestId] = true;

        emit RandomnessFulfilled(requestId, randomWords);
    }

    /**
     * Get random number in range [0, max)
     */
    function getRandomInRange(uint256 requestId, uint256 index, uint256 max)
        external view returns (uint256)
    {
        require(s_requestFulfilled[requestId], "Request not fulfilled");
        require(index < s_randomWords[requestId].length, "Index out of bounds");
        return s_randomWords[requestId][index] % max;
    }
}
`;

// Automation Contract
const AUTOMATION_CONTRACT = `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {AutomationCompatibleInterface} from "@chainlink/contracts/src/v0.8/automation/AutomationCompatible.sol";

contract AutomatedContract is AutomationCompatibleInterface {
    uint256 public lastTimestamp;
    uint256 public interval;
    uint256 public counter;

    event UpkeepPerformed(uint256 indexed counter, uint256 timestamp);

    constructor(uint256 _interval) {
        interval = _interval;
        lastTimestamp = block.timestamp;
    }

    /**
     * Check if upkeep is needed
     * Called off-chain by Chainlink Automation nodes
     */
    function checkUpkeep(bytes calldata /* checkData */)
        external view override
        returns (bool upkeepNeeded, bytes memory performData)
    {
        upkeepNeeded = (block.timestamp - lastTimestamp) > interval;
        performData = "";
    }

    /**
     * Perform the upkeep
     * Called on-chain when checkUpkeep returns true
     */
    function performUpkeep(bytes calldata /* performData */) external override {
        // Re-validate to prevent malicious calls
        if ((block.timestamp - lastTimestamp) > interval) {
            lastTimestamp = block.timestamp;
            counter++;

            // Add your automated logic here
            emit UpkeepPerformed(counter, block.timestamp);
        }
    }

    /**
     * Update interval (only for demonstration)
     */
    function setInterval(uint256 _interval) external {
        interval = _interval;
    }
}
`;

// Functions Contract
const FUNCTIONS_CONTRACT = `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {FunctionsClient} from "@chainlink/contracts/src/v0.8/functions/v1_0_0/FunctionsClient.sol";
import {FunctionsRequest} from "@chainlink/contracts/src/v0.8/functions/v1_0_0/libraries/FunctionsRequest.sol";

contract FunctionsConsumer is FunctionsClient {
    using FunctionsRequest for FunctionsRequest.Request;

    bytes32 public s_lastRequestId;
    bytes public s_lastResponse;
    bytes public s_lastError;

    uint64 public subscriptionId;
    bytes32 public donId;

    event ResponseReceived(bytes32 indexed requestId, bytes response, bytes err);

    constructor(address router, uint64 _subscriptionId, bytes32 _donId)
        FunctionsClient(router)
    {
        subscriptionId = _subscriptionId;
        donId = _donId;
    }

    /**
     * Execute a JavaScript function
     * @param source JavaScript source code to execute
     * @param args Arguments to pass to the function
     */
    function executeRequest(
        string calldata source,
        string[] calldata args
    ) external returns (bytes32 requestId) {
        FunctionsRequest.Request memory req;
        req.initializeRequestForInlineJavaScript(source);

        if (args.length > 0) {
            req.setArgs(args);
        }

        s_lastRequestId = _sendRequest(
            req.encodeCBOR(),
            subscriptionId,
            300000, // gas limit
            donId
        );

        return s_lastRequestId;
    }

    /**
     * Callback function for Chainlink Functions
     */
    function fulfillRequest(
        bytes32 requestId,
        bytes memory response,
        bytes memory err
    ) internal override {
        s_lastResponse = response;
        s_lastError = err;

        emit ResponseReceived(requestId, response, err);
    }

    /**
     * Decode response as uint256
     */
    function getResponseAsUint() external view returns (uint256) {
        return abi.decode(s_lastResponse, (uint256));
    }
}
`;

// JavaScript source for Functions example
const FUNCTIONS_JS_SOURCE = `// Example: Fetch price from CoinGecko API
const coinId = args[0] || "ethereum";

const response = await Functions.makeHttpRequest({
  url: \`https://api.coingecko.com/api/v3/simple/price?ids=\${coinId}&vs_currencies=usd\`,
});

if (response.error) {
  throw Error("Request failed");
}

const price = response.data[coinId].usd;
// Return price scaled by 100 (2 decimal places)
return Functions.encodeUint256(Math.round(price * 100));
`;

export function generateOracle(args: GenerateOracleArgs): GenerateOracleResult {
  const { oracleType, network = "arbitrum-sepolia", feeds = ["ETH/USD"] } = args;

  const files: Record<string, string> = {};
  const addresses: Record<string, string> = {};
  const networkAddresses = ADDRESSES[network];

  switch (oracleType) {
    case "price_feed": {
      files["contracts/PriceConsumer.sol"] = PRICE_FEED_CONTRACT;

      // Add deployment script
      const feedAddresses = feeds
        .map((feed) => networkAddresses.price_feeds[feed])
        .filter(Boolean);

      files["scripts/deploy.ts"] = `import { ethers } from "hardhat";

async function main() {
  // Price feed addresses on ${network}
  const feeds = ${JSON.stringify(
    feeds.reduce((acc, feed) => {
      acc[feed] = networkAddresses.price_feeds[feed] || "0x...";
      return acc;
    }, {} as Record<string, string>),
    null,
    2
  )};

  const PriceConsumer = await ethers.getContractFactory("PriceConsumer");

  for (const [name, address] of Object.entries(feeds)) {
    const consumer = await PriceConsumer.deploy(address);
    await consumer.waitForDeployment();
    console.log(\`PriceConsumer for \${name} deployed to:\`, await consumer.getAddress());
  }
}

main().catch(console.error);
`;

      Object.assign(addresses, networkAddresses.price_feeds);
      break;
    }

    case "vrf": {
      files["contracts/VRFConsumer.sol"] = VRF_CONTRACT;

      files["scripts/deploy.ts"] = `import { ethers } from "hardhat";

async function main() {
  // VRF Coordinator on ${network}
  const coordinator = "${networkAddresses.vrf.coordinator}";
  const keyHash = "${networkAddresses.vrf.keyHash}";

  // Replace with your subscription ID
  const subscriptionId = 1; // Get from vrf.chain.link

  const VRFConsumer = await ethers.getContractFactory("VRFConsumer");
  const consumer = await VRFConsumer.deploy(coordinator, subscriptionId, keyHash);
  await consumer.waitForDeployment();

  console.log("VRFConsumer deployed to:", await consumer.getAddress());
  console.log("\\nNext steps:");
  console.log("1. Go to vrf.chain.link");
  console.log("2. Create a subscription or use existing one");
  console.log("3. Fund subscription with LINK");
  console.log("4. Add this contract as a consumer");
}

main().catch(console.error);
`;

      Object.assign(addresses, networkAddresses.vrf);
      break;
    }

    case "automation": {
      files["contracts/AutomatedContract.sol"] = AUTOMATION_CONTRACT;

      files["scripts/deploy.ts"] = `import { ethers } from "hardhat";

async function main() {
  // Interval in seconds (e.g., 1 hour = 3600)
  const interval = 3600;

  const AutomatedContract = await ethers.getContractFactory("AutomatedContract");
  const contract = await AutomatedContract.deploy(interval);
  await contract.waitForDeployment();

  console.log("AutomatedContract deployed to:", await contract.getAddress());
  console.log("\\nNext steps:");
  console.log("1. Go to automation.chain.link");
  console.log("2. Register new upkeep");
  console.log("3. Select 'Custom logic' trigger");
  console.log("4. Enter contract address:", await contract.getAddress());
  console.log("5. Fund upkeep with LINK");
}

main().catch(console.error);
`;

      Object.assign(addresses, networkAddresses.automation);
      break;
    }

    case "functions": {
      files["contracts/FunctionsConsumer.sol"] = FUNCTIONS_CONTRACT;
      files["scripts/source.js"] = FUNCTIONS_JS_SOURCE;

      files["scripts/deploy.ts"] = `import { ethers } from "hardhat";

async function main() {
  // Functions Router on ${network}
  const router = "${networkAddresses.functions.router}";
  const donId = "${networkAddresses.functions.donId}";

  // Replace with your subscription ID
  const subscriptionId = 1; // Get from functions.chain.link

  const FunctionsConsumer = await ethers.getContractFactory("FunctionsConsumer");
  const consumer = await FunctionsConsumer.deploy(router, subscriptionId, donId);
  await consumer.waitForDeployment();

  console.log("FunctionsConsumer deployed to:", await consumer.getAddress());
  console.log("\\nNext steps:");
  console.log("1. Go to functions.chain.link");
  console.log("2. Create a subscription");
  console.log("3. Fund subscription with LINK");
  console.log("4. Add this contract as a consumer");
  console.log("5. Use scripts/source.js as your JavaScript source");
}

main().catch(console.error);
`;

      Object.assign(addresses, networkAddresses.functions);
      break;
    }
  }

  // Add hardhat config
  files["hardhat.config.ts"] = `import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import "dotenv/config";

const config: HardhatUserConfig = {
  solidity: "0.8.19",
  networks: {
    arbitrumSepolia: {
      url: "https://sepolia-rollup.arbitrum.io/rpc",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
    },
    arbitrumOne: {
      url: "https://arb1.arbitrum.io/rpc",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
    },
  },
};

export default config;
`;

  // Add package.json
  files["package.json"] = JSON.stringify(
    {
      name: "arbbuilder-oracle",
      version: "1.0.0",
      scripts: {
        compile: "hardhat compile",
        deploy: `hardhat run scripts/deploy.ts --network ${network.replace("-", "")}`,
        test: "hardhat test",
      },
      devDependencies: {
        "@nomicfoundation/hardhat-toolbox": "^4.0.0",
        hardhat: "^2.19.0",
        "@chainlink/contracts": "^1.1.0",
        dotenv: "^16.0.0",
      },
    },
    null,
    2
  );

  // Add .env.example
  files[".env.example"] = `PRIVATE_KEY=your-private-key-without-0x-prefix
`;

  return {
    files,
    dependencies: {
      "@chainlink/contracts": "^1.1.0",
      hardhat: "^2.19.0",
      "@nomicfoundation/hardhat-toolbox": "^4.0.0",
    },
    addresses,
    setupInstructions: [
      "1. Install dependencies: npm install",
      "2. Copy .env.example to .env and add your private key",
      "3. Compile contracts: npm run compile",
      `4. Deploy to ${network}: npm run deploy`,
      `5. Follow the console instructions for Chainlink ${oracleType} setup`,
    ],
  };
}

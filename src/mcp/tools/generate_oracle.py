"""
Generate Chainlink oracle integration code.

Supports:
- Price Feed: Real-time price data from Chainlink oracles
- VRF: Verifiable Random Function for provably fair randomness
- Automation: Chainlink Keepers for automated contract execution
- Functions: Custom JavaScript execution on Chainlink DON
"""

import json
from typing import Any, Optional

from .base import BaseTool
from ...templates.oracle_templates import (
    OracleTemplate,
    select_oracle_template,
    get_oracle_template,
    list_oracle_templates,
    PRICE_FEED_TEMPLATE,
    VRF_TEMPLATE,
    AUTOMATION_TEMPLATE,
    FUNCTIONS_TEMPLATE,
)
# Removed: agentic_rag import (template-based generation)


class GenerateOracleTool(BaseTool):
    """Generate Chainlink oracle integration code."""

    name = "generate_oracle"
    description = """Generate Chainlink oracle integration code for Arbitrum dApps.

Supports:
- Price Feed: Real-time price data (ETH/USD, BTC/USD, etc.)
- VRF: Verifiable Random Function for provably fair randomness
- Automation: Chainlink Keepers for automated contract execution
- Functions: Custom JavaScript execution on Chainlink's DON

Generates both Solidity contracts and frontend integration hooks."""

    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Description of the oracle functionality needed",
            },
            "oracle_type": {
                "type": "string",
                "enum": ["price_feed", "vrf", "automation", "functions"],
                "description": "Type of Chainlink oracle to integrate",
            },
            "network": {
                "type": "string",
                "enum": ["arbitrum", "arbitrumSepolia"],
                "description": "Network to deploy on",
                "default": "arbitrumSepolia",
            },
            "price_pairs": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Price pairs to include (e.g., ['ETH/USD', 'BTC/USD'])",
            },
            "include_stylus": {
                "type": "boolean",
                "description": "Include Stylus (Rust) implementation if available",
                "default": False,
            },
            "include_frontend": {
                "type": "boolean",
                "description": "Include frontend React hooks",
                "default": True,
            },
        },
        "required": ["prompt"],
    }

    def __init__(self, vectordb=None):
        """Initialize with optional vector database for context."""
        super().__init__()
        self.vectordb = vectordb

    def execute(self, **kwargs) -> dict[str, Any]:
        """Generate oracle integration code based on the request."""
        prompt = kwargs.get("prompt", "")
        oracle_type = kwargs.get("oracle_type")
        network = kwargs.get("network", "arbitrumSepolia")
        price_pairs = kwargs.get("price_pairs", ["ETH/USD"])
        include_stylus = kwargs.get("include_stylus", False)
        include_frontend = kwargs.get("include_frontend", True)

        # Validate inputs
        if not prompt:
            return {"error": "prompt is required"}

        # Select template
        if oracle_type:
            template = get_oracle_template(oracle_type)
            if not template:
                return {"error": f"Unknown oracle_type: {oracle_type}"}
        else:
            template = select_oracle_template(prompt)

        # Context retrieval (template-based generation doesn't require RAG)
        context = []

        # Build files
        files = {}

        # Add Solidity contract
        files["contracts/OracleConsumer.sol"] = self._customize_solidity(
            template, network, price_pairs
        )

        # Add Stylus implementation if available and requested
        if include_stylus and template.stylus_code:
            files["contracts/src/lib.rs"] = template.stylus_code

        # Add frontend hook if requested
        if include_frontend:
            files["src/hooks/useOracle.ts"] = template.frontend_hook

        # Add deployment script
        files["scripts/deploy.ts"] = self._generate_deploy_script(template, network)

        # Add Hardhat scaffold files
        files["hardhat.config.ts"] = self._generate_hardhat_config()
        files["package.json"] = self._generate_package_json(template, network)
        files[".env.example"] = "PRIVATE_KEY=your-private-key-without-0x-prefix\n"

        # Build response
        result = {
            "template_used": template.name,
            "oracle_type": template.oracle_type,
            "files": files,
            "dependencies": template.dependencies,
            "network_config": template.networks.get(network, {}),
            "features": template.features,
            "setup_instructions": self._get_setup_instructions(template, network),
        }

        if context:
            result["references"] = [
                {
                    "source": c.get("metadata", {}).get("source", "Unknown"),
                    "relevance": c.get("distance", 0),
                }
                for c in context[:3]
            ]

        return result

    def _customize_solidity(
        self,
        template: OracleTemplate,
        network: str,
        price_pairs: list[str],
    ) -> str:
        """Customize Solidity contract for the network."""
        code = template.solidity_code

        # Add network-specific addresses as comments
        network_config = template.networks.get(network, {})
        if network_config:
            address_comments = "// Network addresses:\n"
            for key, value in network_config.items():
                address_comments += f"// {key}: {value}\n"
            code = code.replace(
                "contract ",
                address_comments + "\ncontract ",
                1,
            )

        return code

    def _generate_deploy_script(self, template: OracleTemplate, network: str) -> str:
        """Generate Hardhat deployment script."""
        network_config = template.networks.get(network, {})

        if template.oracle_type == "price_feed":
            feed_address = network_config.get("ETH/USD", "0x...")
            return f'''import {{ ethers }} from "hardhat";

async function main() {{
  const priceFeedAddress = "{feed_address}";

  const PriceFeedConsumer = await ethers.getContractFactory("PriceFeedConsumer");
  const consumer = await PriceFeedConsumer.deploy(priceFeedAddress);

  await consumer.waitForDeployment();
  console.log("PriceFeedConsumer deployed to:", await consumer.getAddress());

  // Test the price feed
  const price = await consumer.getLatestPrice();
  console.log("Current ETH/USD price:", price.toString());
}}

main().catch((error) => {{
  console.error(error);
  process.exitCode = 1;
}});
'''

        elif template.oracle_type == "vrf":
            coordinator = network_config.get("coordinator", "0x...")
            key_hash = network_config.get("keyHash", "0x...")
            return f'''import {{ ethers }} from "hardhat";

async function main() {{
  const vrfCoordinator = "{coordinator}";
  const keyHash = "{key_hash}";
  const subscriptionId = 0; // Replace with your subscription ID

  const VRFConsumer = await ethers.getContractFactory("VRFConsumer");
  const consumer = await VRFConsumer.deploy(vrfCoordinator, subscriptionId, keyHash);

  await consumer.waitForDeployment();
  console.log("VRFConsumer deployed to:", await consumer.getAddress());

  // Note: Add this contract as a consumer to your VRF subscription
  console.log("Remember to add this contract as a consumer in the VRF Subscription Manager");
}}

main().catch((error) => {{
  console.error(error);
  process.exitCode = 1;
}});
'''

        elif template.oracle_type == "automation":
            return '''import { ethers } from "hardhat";

async function main() {
  const updateInterval = 60; // 60 seconds

  const AutomationConsumer = await ethers.getContractFactory("AutomationConsumer");
  const consumer = await AutomationConsumer.deploy(updateInterval);

  await consumer.waitForDeployment();
  console.log("AutomationConsumer deployed to:", await consumer.getAddress());

  // Note: Register this contract with Chainlink Automation
  console.log("Register at: https://automation.chain.link/");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
'''

        elif template.oracle_type == "functions":
            router = network_config.get("router", "0x...")
            don_id = network_config.get("donId", "0x...")
            return f'''import {{ ethers }} from "hardhat";

async function main() {{
  const router = "{router}";
  const donId = "{don_id}";
  const subscriptionId = 0; // Replace with your subscription ID

  const FunctionsConsumer = await ethers.getContractFactory("FunctionsConsumer");
  const consumer = await FunctionsConsumer.deploy(router, subscriptionId, donId);

  await consumer.waitForDeployment();
  console.log("FunctionsConsumer deployed to:", await consumer.getAddress());

  // Note: Add this contract as a consumer to your Functions subscription
  console.log("Manage subscriptions at: https://functions.chain.link/");
}}

main().catch((error) => {{
  console.error(error);
  process.exitCode = 1;
}});
'''

        return "// Deploy script not available for this oracle type"

    def _generate_hardhat_config(self) -> str:
        """Generate Hardhat configuration with Arbitrum network settings."""
        return '''import { HardhatUserConfig } from "hardhat/config";
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
'''

    def _generate_package_json(self, template: OracleTemplate, network: str) -> str:
        """Generate package.json with Hardhat and Chainlink dependencies."""
        network_flag = "arbitrumSepolia" if network == "arbitrumSepolia" else "arbitrumOne"
        pkg = {
            "name": "arbbuilder-oracle",
            "version": "1.0.0",
            "scripts": {
                "compile": "hardhat compile",
                "deploy": f"hardhat run scripts/deploy.ts --network {network_flag}",
                "test": "hardhat test",
            },
            "devDependencies": {
                "@nomicfoundation/hardhat-toolbox": "^4.0.0",
                "hardhat": "^2.19.0",
                "@chainlink/contracts": "^1.1.0",
                "dotenv": "^16.0.0",
            },
        }
        return json.dumps(pkg, indent=2)

    def _get_setup_instructions(self, template: OracleTemplate, network: str) -> list[str]:
        """Get setup instructions for the oracle."""
        base_instructions = [
            "1. Install dependencies: npm install @chainlink/contracts",
            "2. Add Hardhat: npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox",
            "3. Configure hardhat.config.ts with Arbitrum network",
        ]

        if template.oracle_type == "price_feed":
            base_instructions.extend([
                "4. Deploy the contract: npx hardhat run scripts/deploy.ts --network arbitrumSepolia",
                "5. The contract will automatically fetch prices from Chainlink",
                "6. Find more price feeds at: https://docs.chain.link/data-feeds/price-feeds/addresses",
            ])

        elif template.oracle_type == "vrf":
            base_instructions.extend([
                "4. Create a VRF subscription at: https://vrf.chain.link/",
                "5. Fund your subscription with LINK tokens",
                "6. Deploy the contract with your subscription ID",
                "7. Add the deployed contract as a consumer in the subscription",
            ])

        elif template.oracle_type == "automation":
            base_instructions.extend([
                "4. Deploy the contract: npx hardhat run scripts/deploy.ts --network arbitrumSepolia",
                "5. Register at: https://automation.chain.link/",
                "6. Fund the upkeep with LINK tokens",
                "7. The contract will be called automatically when conditions are met",
            ])

        elif template.oracle_type == "functions":
            base_instructions.extend([
                "4. Create a Functions subscription at: https://functions.chain.link/",
                "5. Fund your subscription with LINK tokens",
                "6. Deploy the contract with your subscription ID and DON ID",
                "7. Add the deployed contract as a consumer",
                "8. Write your JavaScript source code for off-chain computation",
            ])

        return base_instructions

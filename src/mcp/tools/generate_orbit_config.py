"""
Generate Orbit chain configuration code.

Supports:
- Chain configuration (prepareChainConfig)
- AnyTrust DAC keyset setup
- Custom gas token configuration
"""

from typing import Any

from ...templates.orbit_templates import (
    ORBIT_DEPENDENCIES,
    PARENT_CHAIN_RPCS,
    get_orbit_template,
)
from .base import BaseTool
from .generate_stylus_code import TEMPLATE_DISCLAIMER


class GenerateOrbitConfigTool(BaseTool):
    """Generate Orbit chain configuration scripts."""

    name = "generate_orbit_config"
    description = """Generate configuration code for Orbit chain deployment.

Supports:
- Chain configuration with prepareChainConfig()
- AnyTrust DAC keyset management
- Custom gas token setup

Generates TypeScript scripts using @arbitrum/orbit-sdk."""

    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Description of the configuration needed",
            },
            "chain_id": {
                "type": "integer",
                "description": "Chain ID for the new Orbit chain",
                "default": 412346,
            },
            "owner": {
                "type": "string",
                "description": "Initial chain owner address (0x...)",
            },
            "is_anytrust": {
                "type": "boolean",
                "description": "Whether this is an AnyTrust chain (vs Rollup)",
                "default": False,
            },
            "native_token": {
                "type": "string",
                "description": "Custom gas token address (ERC20) for custom gas token chains",
            },
            "parent_chain": {
                "type": "string",
                "enum": [
                    "arbitrum-one",
                    "arbitrum-sepolia",
                    "ethereum-mainnet",
                    "ethereum-sepolia",
                ],
                "description": "Parent chain for the Orbit chain",
                "default": "arbitrum-sepolia",
            },
        },
        "required": ["prompt"],
    }

    def __init__(self, vectordb=None):
        """Initialize with optional vector database."""
        self.vectordb = vectordb

    def execute(self, **kwargs) -> dict[str, Any]:
        """Generate Orbit chain configuration code."""
        prompt = kwargs.get("prompt", "")
        chain_id = kwargs.get("chain_id", 412346)
        owner = kwargs.get("owner", "0x0000000000000000000000000000000000000000")
        is_anytrust = kwargs.get("is_anytrust", False)
        native_token = kwargs.get("native_token")
        parent_chain = kwargs.get("parent_chain", "arbitrum-sepolia")

        if not prompt:
            return {"error": "prompt is required"}

        # Select template based on prompt keywords
        lower_prompt = prompt.lower()

        if native_token or "gas token" in lower_prompt or "native token" in lower_prompt:
            template = get_orbit_template("custom_gas_token")
        elif is_anytrust or "anytrust" in lower_prompt or "dac" in lower_prompt:
            template = get_orbit_template("anytrust_config")
        else:
            template = get_orbit_template("chain_config")

        if not template:
            template = get_orbit_template("chain_config")

        # Get parent chain info
        parent_rpc = PARENT_CHAIN_RPCS.get(parent_chain, PARENT_CHAIN_RPCS["arbitrum-sepolia"])
        parent_chain_id = self._get_parent_chain_id(parent_chain)
        parent_chain_name = parent_chain.replace("-", " ").title()

        # Substitute parameters
        code = template.code
        code = code.replace("{chain_id}", str(chain_id))
        code = code.replace("{owner}", owner)
        code = code.replace("{is_anytrust}", "true" if is_anytrust else "false")
        code = code.replace("{parent_chain_id}", str(parent_chain_id))
        code = code.replace("{parent_chain_name}", parent_chain_name)
        code = code.replace("{parent_chain_rpc}", parent_rpc)

        if native_token:
            code = code.replace("{native_token}", native_token)
            code = code.replace(
                "{validators_array}",
                "[account.address] as `0x${string}`[]",
            )
            code = code.replace(
                "{batch_posters_array}",
                "[account.address] as `0x${string}`[]",
            )

        # Build files dict
        files = {}
        if template.template_type == "config" and template.name == "Orbit Chain Config":
            files["scripts/prepare-chain-config.ts"] = code
        elif "anytrust" in template.name.lower():
            files["scripts/configure-anytrust.ts"] = code
        elif "gas token" in template.name.lower():
            files["scripts/deploy-custom-gas-token.ts"] = code
        else:
            files["scripts/configure.ts"] = code

        # Add .env.example
        files[".env.example"] = self._generate_env_example(parent_rpc, chain_id)

        result = {
            "template_used": template.name,
            "template_type": template.template_type,
            "files": files,
            "dependencies": ORBIT_DEPENDENCIES,
            "parent_chain": {
                "name": parent_chain,
                "chain_id": parent_chain_id,
                "rpc": parent_rpc,
            },
            "chain_config": {
                "chain_id": chain_id,
                "owner": owner,
                "is_anytrust": is_anytrust,
                "native_token": native_token,
            },
            "setup_instructions": [
                "1. Install dependencies: npm install",
                "2. Copy .env.example to .env and fill in your private key",
                f"3. Run the script: npx tsx {list(files.keys())[0]}",
            ],
            "disclaimer": TEMPLATE_DISCLAIMER,
        }

        return result

    @staticmethod
    def _get_parent_chain_id(parent_chain: str) -> int:
        """Get chain ID for the parent chain."""
        chain_ids = {
            "ethereum-mainnet": 1,
            "ethereum-sepolia": 11155111,
            "arbitrum-one": 42161,
            "arbitrum-sepolia": 421614,
        }
        return chain_ids.get(parent_chain, 421614)

    @staticmethod
    def _generate_env_example(parent_rpc: str, chain_id: int) -> str:
        """Generate .env.example file."""
        return f"""# Deployer private key (with 0x prefix)
DEPLOYER_PRIVATE_KEY=0x...

# Parent chain RPC URL
PARENT_CHAIN_RPC={parent_rpc}

# Chain configuration
CHAIN_ID={chain_id}
"""

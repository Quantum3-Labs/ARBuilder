"""
Generate Orbit chain deployment code.

Supports:
- Rollup deployment (createRollup)
- Token bridge deployment (createTokenBridge)
- Full deployment (rollup + token bridge)
"""

from typing import Any

from ...templates.orbit_templates import (
    ORBIT_DEPENDENCIES,
    PARENT_CHAIN_RPCS,
    get_orbit_template,
)
from .base import BaseTool
from .generate_stylus_code import TEMPLATE_DISCLAIMER

# Known RollupCreator contract addresses from @arbitrum/orbit-sdk
ROLLUP_CREATOR_ADDRESSES = {
    "v2.1": {
        1: "0x8c88430658a03497D13cDff7684D37b15aA2F3e1",       # Ethereum Mainnet
        42161: "0x79607f00e61E6d7C0E6330bd7E9c4AC320D50FC9",   # Arbitrum One
        421614: "0xd2Ec8376B1dF436fAb18120E416d3F2BeC61275b",  # Arbitrum Sepolia
        11155111: "0xfb774eA8A92ae528A596c8D90CBCF1bdBC4Cee79", # Ethereum Sepolia
    },
    "v3.1": {
        1: "0x43698080f40dB54DEE6871540037b8AB8fD0AB44",       # Ethereum Mainnet
        42161: "0xB90e53fd945Cd28Ec4728cBfB566981dD571eB8b",   # Arbitrum One
        421614: "0x5F45675AC8DDF7d45713b2c7D191B287475C16cF",  # Arbitrum Sepolia
        11155111: "0x687Bc1D23390875a868Db158DA1cDC8998E31640", # Ethereum Sepolia
    },
}


class GenerateOrbitDeploymentTool(BaseTool):
    """Generate Orbit chain deployment scripts."""

    name = "generate_orbit_deployment"
    description = """Generate deployment code for Orbit chains.

Supports:
- Rollup deployment with createRollup()
- Token bridge deployment with createTokenBridge()
- Full deployment (rollup + token bridge in sequence)

Configures validators, batch posters, native tokens, and rollup versions.
Generates TypeScript scripts using @arbitrum/orbit-sdk."""

    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Description of the deployment requirements",
            },
            "deployment_type": {
                "type": "string",
                "enum": ["rollup", "token_bridge", "full"],
                "description": "Type of deployment to generate",
                "default": "rollup",
            },
            "validators": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Validator addresses for the rollup",
            },
            "batch_posters": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Batch poster addresses",
            },
            "native_token": {
                "type": "string",
                "description": "Custom gas token address (for custom gas token chains)",
            },
            "parent_chain": {
                "type": "string",
                "enum": [
                    "arbitrum-one",
                    "arbitrum-sepolia",
                    "ethereum-mainnet",
                    "ethereum-sepolia",
                ],
                "description": "Parent chain for deployment",
                "default": "arbitrum-sepolia",
            },
            "rollup_version": {
                "type": "string",
                "enum": ["v2.1", "v3.1"],
                "description": "Rollup version to deploy",
                "default": "v3.1",
            },
            "chain_id": {
                "type": "integer",
                "description": "Chain ID for the new Orbit chain",
                "default": 412346,
            },
            "is_anytrust": {
                "type": "boolean",
                "description": "Whether to deploy as AnyTrust chain",
                "default": False,
            },
            "rollup_address": {
                "type": "string",
                "description": "Existing rollup address (for token_bridge deployment)",
            },
        },
        "required": ["prompt"],
    }

    def __init__(self, vectordb=None):
        """Initialize with optional vector database."""
        self.vectordb = vectordb

    def execute(self, **kwargs) -> dict[str, Any]:
        """Generate Orbit chain deployment code."""
        prompt = kwargs.get("prompt", "")
        deployment_type = kwargs.get("deployment_type", "rollup")
        validators = kwargs.get("validators", [])
        batch_posters = kwargs.get("batch_posters", [])
        native_token = kwargs.get("native_token")
        parent_chain = kwargs.get("parent_chain", "arbitrum-sepolia")
        rollup_version = kwargs.get("rollup_version", "v3.1")
        chain_id = kwargs.get("chain_id", 412346)
        is_anytrust = kwargs.get("is_anytrust", False)
        rollup_address = kwargs.get("rollup_address", "0x0000000000000000000000000000000000000000")

        if not prompt:
            return {"error": "prompt is required"}

        # Get parent chain info
        parent_rpc = PARENT_CHAIN_RPCS.get(parent_chain, PARENT_CHAIN_RPCS["arbitrum-sepolia"])
        parent_chain_id = self._get_parent_chain_id(parent_chain)
        parent_chain_name = parent_chain.replace("-", " ").title()

        # Format validator/batch poster arrays
        validators_str = self._format_address_array(validators)
        batch_posters_str = self._format_address_array(batch_posters)

        files = {}

        # Generate rollup deployment
        if deployment_type in ("rollup", "full"):
            rollup_template = get_orbit_template("deploy_rollup")
            if rollup_template:
                code = rollup_template.code
                code = self._substitute_params(
                    code,
                    chain_id=chain_id,
                    parent_chain_id=parent_chain_id,
                    parent_chain_name=parent_chain_name,
                    is_anytrust=is_anytrust,
                    validators_str=validators_str,
                    batch_posters_str=batch_posters_str,
                    native_token=native_token,
                )
                # Look up the known RollupCreator address for this version + parent chain
                version_addresses = ROLLUP_CREATOR_ADDRESSES.get(
                    rollup_version, ROLLUP_CREATOR_ADDRESSES["v3.1"]
                )
                rollup_creator_address = version_addresses.get(
                    parent_chain_id, "0x0000000000000000000000000000000000000000"
                )

                # Apply version-specific modifications
                version_label = "v2.1 / classic" if rollup_version == "v2.1" else "v3.1 / BoLD"
                code = code.replace(
                    "console.log('Deploying Orbit chain...');",
                    f"console.log('Deploying Orbit chain ({version_label})...');\n"
                    f"  console.log('  RollupCreator: {rollup_creator_address}');",
                )
                if rollup_version == "v2.1":
                    code = code.replace(
                        "  // Deploy rollup\n",
                        f"  // Deploy rollup — v2.1 uses classic challenge protocol\n"
                        f"  // RollupCreator: {rollup_creator_address}\n"
                        "  // baseStake = 0.1 ETH, stakeToken = ETH (default)\n",
                    )
                    code = code.replace(
                        "    walletClient,\n  }});",
                        "    parentChainPublicClient: publicClient,\n"
                        "    // v2.1: classic challenge protocol (stable, non-BoLD)\n"
                        "    rollupCreatorVersion: 'v2.1',\n"
                        "  }});",
                    )
                    code = code.replace(
                        "console.log('\\nRollup deployed successfully!');",
                        "console.log('\\nRollup deployed successfully! (v2.1 classic)');\n"
                        "  console.log('\\nv2.1 validator config:');\n"
                        "  console.log('  Base stake: 0.1 ETH (default)');\n"
                        "  console.log('  Stake token: ETH');",
                    )
                else:
                    code = code.replace(
                        "  // Deploy rollup\n",
                        f"  // Deploy rollup — v3.1 uses BoLD challenge protocol\n"
                        f"  // RollupCreator: {rollup_creator_address}\n",
                    )
                    code = code.replace(
                        "    walletClient,\n  }});",
                        "    parentChainPublicClient: publicClient,\n"
                        "    // v3.1: BoLD challenge protocol (default)\n"
                        "    rollupCreatorVersion: 'v3.1',\n"
                        "  }});",
                    )
                    code = code.replace(
                        "console.log('\\nRollup deployed successfully!');",
                        "console.log('\\nRollup deployed successfully! (v3.1 BoLD)');",
                    )
                files["scripts/deploy-rollup.ts"] = code

        # Generate token bridge deployment
        if deployment_type in ("token_bridge", "full"):
            bridge_template = get_orbit_template("deploy_token_bridge")
            if bridge_template:
                code = bridge_template.code
                code = code.replace("{chain_id}", str(chain_id))
                code = code.replace("{chain_name}", f"orbit-chain-{chain_id}")
                code = code.replace("{parent_chain_id}", str(parent_chain_id))
                code = code.replace("{parent_chain_name}", parent_chain_name)
                code = code.replace("{rollup_address}", rollup_address)
                files["scripts/deploy-token-bridge.ts"] = code

        # Add .env.example
        env_vars = [
            "DEPLOYER_PRIVATE_KEY=0x...",
            f"PARENT_CHAIN_RPC={parent_rpc}",
        ]
        if rollup_version == "v2.1":
            env_vars.append("# Using v2.1 RollupCreator (classic challenge protocol)")
        if deployment_type in ("token_bridge", "full"):
            env_vars.append("ORBIT_CHAIN_RPC=http://localhost:8449")
        files[".env.example"] = "\n".join(env_vars) + "\n"

        # Build response
        result = {
            "template_used": f"deploy_{deployment_type}",
            "deployment_type": deployment_type,
            "rollup_version": rollup_version,
            "files": files,
            "dependencies": ORBIT_DEPENDENCIES,
            "parent_chain": {
                "name": parent_chain,
                "chain_id": parent_chain_id,
                "rpc": parent_rpc,
            },
            "chain_config": {
                "chain_id": chain_id,
                "is_anytrust": is_anytrust,
                "native_token": native_token,
                "validators": validators,
                "batch_posters": batch_posters,
            },
            "setup_instructions": self._get_setup_instructions(deployment_type),
            "notes": self._get_notes(deployment_type, native_token, is_anytrust, rollup_version),
            "disclaimer": TEMPLATE_DISCLAIMER,
        }

        return result

    def _substitute_params(
        self,
        code: str,
        chain_id: int,
        parent_chain_id: int,
        parent_chain_name: str,
        is_anytrust: bool,
        validators_str: str,
        batch_posters_str: str,
        native_token: str | None,
    ) -> str:
        """Substitute template parameters in code."""
        code = code.replace("{chain_id}", str(chain_id))
        code = code.replace("{parent_chain_id}", str(parent_chain_id))
        code = code.replace("{parent_chain_name}", parent_chain_name)
        code = code.replace("{is_anytrust}", "true" if is_anytrust else "false")
        code = code.replace("{validators_array}", validators_str)
        code = code.replace("{batch_posters_array}", batch_posters_str)

        if native_token:
            code = code.replace(
                "{native_token_line}",
                f"\n      nativeToken: '{native_token}' as `0x${{string}}`,",
            )
        else:
            code = code.replace("{native_token_line}", "")

        return code

    @staticmethod
    def _format_address_array(addresses: list[str]) -> str:
        """Format a list of addresses as a TypeScript array literal."""
        if not addresses:
            return "[account.address] as `0x${string}`[]"
        formatted = ", ".join(f"'{addr}' as `0x${{string}}`" for addr in addresses)
        return f"[{formatted}]"

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
    def _get_setup_instructions(deployment_type: str) -> list[str]:
        """Get setup instructions for the deployment type."""
        instructions = [
            "1. Install dependencies: npm install",
            "2. Copy .env.example to .env and configure",
            "3. Ensure deployer account has sufficient funds on parent chain",
        ]

        if deployment_type == "rollup":
            instructions.append("4. Run: npx tsx scripts/deploy-rollup.ts")
            instructions.append("5. Save the output contract addresses for next steps")
        elif deployment_type == "token_bridge":
            instructions.append("4. Update ORBIT_CHAIN_RPC and rollup address in the script")
            instructions.append("5. Run: npx tsx scripts/deploy-token-bridge.ts")
        elif deployment_type == "full":
            instructions.append("4. Run: npx tsx scripts/deploy-rollup.ts")
            instructions.append("5. Start the Orbit chain node with the rollup contracts")
            instructions.append("6. Update ORBIT_CHAIN_RPC and rollup address")
            instructions.append("7. Run: npx tsx scripts/deploy-token-bridge.ts")

        return instructions

    @staticmethod
    def _get_notes(
        deployment_type: str, native_token: str | None, is_anytrust: bool,
        rollup_version: str = "v3.1",
    ) -> list[str]:
        """Get deployment notes."""
        notes = [
            "Deployment requires significant gas — ensure sufficient funds",
            "Save all contract addresses from deployment output",
        ]

        if rollup_version == "v2.1":
            notes.append("v2.1 (classic): baseStake = 0.1 ETH, classic challenge protocol")
            notes.append("v2.1 uses the classic RollupCreator via rollupCreatorVersion: 'v2.1'")
        else:
            notes.append("v3.1 (BoLD): uses assertion staking with bounded liquidity delay challenge protocol")

        if native_token:
            notes.append(
                "Custom gas token requires ERC20 approval before deployment"
            )
            notes.append(
                "The native token must be deployed on the parent chain"
            )

        if is_anytrust:
            notes.append(
                "AnyTrust chains require DAC keyset configuration after deployment"
            )

        if deployment_type == "full":
            notes.append(
                "Token bridge deployment requires the Orbit chain to be running"
            )

        return notes

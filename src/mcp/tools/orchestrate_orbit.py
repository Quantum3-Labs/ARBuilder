"""
Orchestrate full Orbit chain deployment project scaffold.

This tool coordinates the generation of a complete Orbit chain
deployment project by combining templates for:
1. Chain configuration
2. Rollup deployment
3. Token bridge deployment
4. Validator management
5. Node configuration
6. Project scaffold (package.json, scripts, etc.)
"""

from typing import Any

from ...templates.orbit_templates import (
    ORBIT_DEPENDENCIES,
    PARENT_CHAIN_RPCS,
    generate_docker_compose,
    get_orbit_template,
    validate_template_output,
)
from .base import BaseTool
from .generate_stylus_code import TEMPLATE_DISCLAIMER


class OrchestrateOrbitTool(BaseTool):
    """Orchestrate generation of complete Orbit chain deployment projects."""

    name = "orchestrate_orbit"
    description = """Scaffold a complete Orbit chain deployment project.

Generates a production-ready project with all scripts needed to:
- Configure and deploy a new Orbit chain (Rollup or AnyTrust)
- Deploy token bridge contracts
- Configure validators and batch posters
- Generate Nitro node configuration
- Set up AnyTrust DAC (if applicable)

Includes package.json, tsconfig.json, .env.example, setup.sh, and deploy.sh."""

    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Description of the Orbit chain project",
            },
            "chain_name": {
                "type": "string",
                "description": "Name for the Orbit chain",
                "default": "my-orbit-chain",
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
            "native_token": {
                "type": "string",
                "description": "Custom gas token address (ERC20)",
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
            "validators": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Validator addresses",
            },
            "batch_posters": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Batch poster addresses",
            },
        },
        "required": ["prompt"],
    }

    def __init__(self, vectordb=None):
        """Initialize with optional vector database."""
        super().__init__()
        self.vectordb = vectordb

    def execute(self, **kwargs) -> dict[str, Any]:
        """Generate a complete Orbit chain deployment project."""
        prompt = kwargs.get("prompt", "")
        chain_name = kwargs.get("chain_name", "my-orbit-chain")
        chain_id = kwargs.get("chain_id", 412346)
        is_anytrust = kwargs.get("is_anytrust", False)
        native_token = kwargs.get("native_token")
        parent_chain = kwargs.get("parent_chain", "arbitrum-sepolia")
        validators = kwargs.get("validators", [])
        batch_posters = kwargs.get("batch_posters", [])

        if not prompt:
            return {"error": "prompt is required"}

        # Get parent chain info
        parent_rpc = PARENT_CHAIN_RPCS.get(
            parent_chain, PARENT_CHAIN_RPCS["arbitrum-sepolia"]
        )
        parent_chain_id = self._get_parent_chain_id(parent_chain)
        parent_chain_name = parent_chain.replace("-", " ").title()

        # Format addresses
        validators_str = self._format_address_array(validators)
        batch_posters_str = self._format_address_array(batch_posters)

        # Build project files
        files = {}

        # 1. Chain config script
        config_template = get_orbit_template("chain_config")
        if config_template:
            code = config_template.code
            code = code.replace("{chain_id}", str(chain_id))
            code = code.replace("{owner}", "0x0000000000000000000000000000000000000000")
            code = code.replace("{is_anytrust}", "true" if is_anytrust else "false")
            files["scripts/prepare-chain-config.ts"] = validate_template_output(
                code, "prepare-chain-config"
            )

        # 2. Deploy rollup script
        rollup_template = get_orbit_template("deploy_rollup")
        if rollup_template:
            code = rollup_template.code
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
            files["scripts/deploy-rollup.ts"] = validate_template_output(
                code, "deploy-rollup"
            )

        # 3. Token bridge script
        bridge_template = get_orbit_template("deploy_token_bridge")
        if bridge_template:
            code = bridge_template.code
            code = code.replace("{chain_id}", str(chain_id))
            code = code.replace("{chain_name}", chain_name)
            code = code.replace("{parent_chain_id}", str(parent_chain_id))
            code = code.replace("{parent_chain_name}", parent_chain_name)
            code = code.replace(
                "{rollup_address}",
                "0x0000000000000000000000000000000000000000",
            )
            files["scripts/deploy-token-bridge.ts"] = validate_template_output(
                code, "deploy-token-bridge"
            )

        # 4. Validator management script
        validator_template = get_orbit_template("validator_management")
        if validator_template:
            code = validator_template.code
            code = code.replace("{parent_chain_id}", str(parent_chain_id))
            code = code.replace("{parent_chain_name}", parent_chain_name)
            code = code.replace(
                "{rollup_address}",
                "0x0000000000000000000000000000000000000000",
            )
            code = code.replace(
                "{sequencer_inbox}",
                "0x0000000000000000000000000000000000000000",
            )
            code = code.replace("{addresses_array}", validators_str)
            files["scripts/manage-validators.ts"] = validate_template_output(
                code, "manage-validators"
            )

        # 5. Node config script
        node_template = get_orbit_template("node_config")
        if node_template:
            code = node_template.code
            code = code.replace("{chain_id}", str(chain_id))
            code = code.replace("{chain_name}", chain_name)
            code = code.replace("{parent_chain_id}", str(parent_chain_id))
            code = code.replace("{parent_chain_name}", parent_chain_name)
            # Set parentChainIsArbitrum based on parent chain type
            parent_is_arbitrum = parent_chain_id in (42161, 421614)
            code = code.replace(
                "{parent_chain_is_arbitrum}",
                "true" if parent_is_arbitrum else "false",
            )
            files["scripts/prepare-node-config.ts"] = validate_template_output(
                code, "prepare-node-config"
            )

        # 6. AnyTrust keyset config (if applicable)
        if is_anytrust:
            anytrust_template = get_orbit_template("anytrust_config")
            if anytrust_template:
                code = anytrust_template.code
                code = code.replace("{parent_chain_id}", str(parent_chain_id))
                code = code.replace("{parent_chain_name}", parent_chain_name)
                files["scripts/configure-anytrust.ts"] = validate_template_output(
                    code, "configure-anytrust"
                )

        # 7. Orchestration scaffold files
        orchestration_template = get_orbit_template("orchestration")
        if orchestration_template:
            for filename, content in orchestration_template.files.items():
                content = content.replace("{project_name}", chain_name)
                content = content.replace("{chain_id}", str(chain_id))
                content = content.replace("{chain_name}", chain_name)
                content = content.replace("{parent_chain_rpc}", parent_rpc)
                files[filename] = content

        # 8. Docker compose
        files["docker-compose.yml"] = generate_docker_compose(
            chain_name, chain_id, parent_chain_id, is_anytrust
        )

        # 9. README
        files["README.md"] = self._generate_readme(
            chain_name, chain_id, is_anytrust, native_token, parent_chain
        )

        # Build project structure description
        project_structure = {
            "scripts/": [
                "prepare-chain-config.ts",
                "deploy-rollup.ts",
                "deploy-token-bridge.ts",
                "manage-validators.ts",
                "prepare-node-config.ts",
            ],
            "root": [
                "package.json",
                "tsconfig.json",
                ".env.example",
                "setup.sh",
                "deploy.sh",
                "docker-compose.yml",
                "README.md",
            ],
        }
        if is_anytrust:
            project_structure["scripts/"].append("configure-anytrust.ts")

        result = {
            "name": chain_name,
            "description": prompt,
            "files": files,
            "project_structure": project_structure,
            "dependencies": ORBIT_DEPENDENCIES,
            "chain_config": {
                "chain_id": chain_id,
                "chain_name": chain_name,
                "is_anytrust": is_anytrust,
                "native_token": native_token,
                "parent_chain": parent_chain,
                "parent_chain_id": parent_chain_id,
                "parent_rpc": parent_rpc,
            },
            "validators": validators,
            "batch_posters": batch_posters,
            "setup_instructions": [
                "1. Run: bash setup.sh",
                "2. Edit .env with DEPLOYER_PRIVATE_KEY"
                " (and optionally separate BATCH_POSTER/VALIDATOR keys)",
                *(
                    [
                        "3. Deploy or obtain your ERC-20 gas token on the parent chain",
                        "4. Run: npx tsx scripts/approve-token.ts"
                        " (approve token for RollupCreator)",
                        "5. Run: npm run config:chain",
                        "6. Run: npm run deploy:rollup (output saved to deployment.json)",
                        "7. Run: npm run config:node (reads deployment.json)",
                        "8. Start Nitro node: docker-compose up -d",
                        "9. Run: npm run deploy:token-bridge (reads deployment.json)",
                    ]
                    if native_token
                    else [
                        "3. Run: npm run config:chain",
                        "4. Run: npm run deploy:rollup (output saved to deployment.json)",
                        "5. Run: npm run config:node (reads deployment.json)",
                        "6. Start Nitro node: docker-compose up -d",
                        "7. Run: npm run deploy:token-bridge (reads deployment.json)",
                    ]
                ),
            ],
            "development_workflow": self._generate_workflow(is_anytrust),
            "disclaimer": TEMPLATE_DISCLAIMER,
        }

        return result

    @staticmethod
    def _format_address_array(addresses: list[str]) -> str:
        """Format a list of addresses as a TypeScript array literal."""
        if not addresses:
            return "[account.address] as `0x${string}`[]"
        formatted = ", ".join(
            f"'{addr}' as `0x${{string}}`" for addr in addresses
        )
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
    def _generate_readme(
        chain_name: str,
        chain_id: int,
        is_anytrust: bool,
        native_token: str | None,
        parent_chain: str,
    ) -> str:
        """Generate README.md for the project."""
        chain_type = "AnyTrust" if is_anytrust else "Rollup"
        gas_token = f"Custom ({native_token})" if native_token else "ETH"

        return f"""# {chain_name.replace('-', ' ').title()}

> Orbit {chain_type} chain deployment project

## Configuration

| Parameter | Value |
|-----------|-------|
| Chain ID | {chain_id} |
| Chain Type | {chain_type} |
| Gas Token | {gas_token} |
| Parent Chain | {parent_chain} |

## Quick Start

```bash
# 1. Install dependencies
bash setup.sh

# 2. Configure environment
# Edit .env with your DEPLOYER_PRIVATE_KEY and other settings

# 3. Deploy everything
bash deploy.sh
```

## Step-by-Step Deployment

```bash
# 1. Prepare chain configuration
npm run config:chain

# 2. Deploy rollup contracts
npm run deploy:rollup

# 3. Start your Nitro node (see docs)
# Use the contract addresses from step 2

# 4. Deploy token bridge
npm run deploy:token-bridge

# 5. Generate node configuration
npm run config:node

# 6. Manage validators
npm run manage:validators
```

## Project Structure

```
{chain_name}/
  scripts/
    prepare-chain-config.ts   # Chain configuration
    deploy-rollup.ts          # Rollup contract deployment
    deploy-token-bridge.ts    # Token bridge deployment
    manage-validators.ts      # Validator/batch poster management
    prepare-node-config.ts    # Nitro node configuration
  package.json
  tsconfig.json
  .env.example
  setup.sh
  deploy.sh
```

## References

- [Orbit Chain Documentation](https://docs.arbitrum.io/launch-orbit-chain/orbit-gentle-introduction)
- [Orbit SDK Reference](https://github.com/OffchainLabs/arbitrum-orbit-sdk)
- [Nitro Node Setup](https://docs.arbitrum.io/run-arbitrum-node/run-full-node)

---
Built with [ARBuilder](https://github.com/arbbuilder)
"""

    @staticmethod
    def _generate_workflow(is_anytrust: bool) -> dict:
        """Generate development workflow guide."""
        steps = [
            {
                "step": 1,
                "component": "Chain Configuration",
                "actions": [
                    "Run setup.sh to install dependencies",
                    "Edit .env with deployer key and parent chain RPC",
                    "Run npm run config:chain to prepare configuration",
                ],
            },
            {
                "step": 2,
                "component": "Rollup Deployment",
                "actions": [
                    "Run npm run deploy:rollup",
                    "Save all contract addresses from output",
                    "Fund the rollup contracts if needed",
                ],
            },
            {
                "step": 3,
                "component": "Node Setup",
                "actions": [
                    "Run npm run config:node to generate nodeConfig.json (reads deployment.json)",
                    "Start Nitro node: docker-compose up -d",
                    "Verify node is syncing with parent chain",
                ],
            },
            {
                "step": 4,
                "component": "Token Bridge",
                "actions": [
                    "Update ORBIT_CHAIN_RPC in .env",
                    "Run npm run deploy:token-bridge",
                    "Verify bridge contracts on both chains",
                ],
            },
        ]

        if is_anytrust:
            steps.append({
                "step": 5,
                "component": "AnyTrust DAC Setup",
                "actions": [
                    "Generate BLS keys: docker run --rm"
                    " -v $(pwd)/das-keys:/keys"
                    " offchainlabs/nitro-node:v3.9.4-7f582c3"
                    " datool keygen --dir /keys",
                    "Configure DAC member BLS keys in the keyset script",
                    "Run npm run configure:anytrust",
                    "Verify keyset is active on SequencerInbox",
                ],
            })

        return {
            "steps": steps,
            "tips": [
                "Deploy to testnet (Arbitrum Sepolia) before mainnet",
                "Ensure deployer has sufficient ETH on parent chain",
                "Save all deployment output — contract addresses are needed for node config",
                "Use a multi-sig for chain owner in production",
                "Monitor validator and batch poster uptime",
            ],
        }

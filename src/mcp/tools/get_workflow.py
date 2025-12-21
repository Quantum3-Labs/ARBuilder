"""
Get Workflow Tool.

Returns structured workflow information for build, deploy, and test operations.
This tool enables AI IDEs to understand the exact commands and steps needed
for Stylus development without executing them directly.
"""

from typing import Optional
from .base import BaseTool, ToolResult
from ..resources import BUILD_WORKFLOW, DEPLOY_WORKFLOW, TEST_WORKFLOW, NETWORK_CONFIGS, STYLUS_CLI_RESOURCE


class GetWorkflowTool(BaseTool):
    """
    Retrieves structured workflow information for Stylus development tasks.

    This tool returns step-by-step instructions, commands, and configurations
    that the AI IDE can use to guide users through build/deploy/test workflows.
    """

    name = "get_workflow"
    description = """Get structured workflow information for Stylus development.

    Returns step-by-step commands and instructions for:
    - Building Stylus contracts (cargo stylus check, build)
    - Deploying to Arbitrum networks (deployment workflow)
    - Testing contracts (unit tests, integration tests)
    - CLI command reference (cargo-stylus commands)
    - Network configurations (RPC endpoints, chain IDs)

    The AI IDE uses this to understand what commands to suggest to users.
    """

    input_schema = {
        "type": "object",
        "properties": {
            "workflow_type": {
                "type": "string",
                "enum": ["build", "deploy", "test", "cli_reference", "networks", "all"],
                "description": "Type of workflow information to retrieve",
            },
            "network": {
                "type": "string",
                "enum": ["arbitrum_sepolia", "arbitrum_one", "arbitrum_nova", "local"],
                "description": "Target network (for deploy workflow)",
            },
            "include_troubleshooting": {
                "type": "boolean",
                "default": True,
                "description": "Include common errors and solutions",
            },
        },
        "required": ["workflow_type"],
    }

    def execute(
        self,
        workflow_type: str,
        network: Optional[str] = "arbitrum_sepolia",
        include_troubleshooting: bool = True,
        **kwargs
    ) -> dict:
        """
        Execute the workflow retrieval.

        Args:
            workflow_type: Type of workflow (build, deploy, test, cli_reference, networks, all)
            network: Target network for deploy workflow
            include_troubleshooting: Whether to include error solutions

        Returns:
            Structured workflow information with commands and steps
        """
        result = {
            "workflow_type": workflow_type,
            "network": network if workflow_type == "deploy" else None,
        }

        if workflow_type == "build" or workflow_type == "all":
            result["build"] = self._get_build_workflow(include_troubleshooting)

        if workflow_type == "deploy" or workflow_type == "all":
            result["deploy"] = self._get_deploy_workflow(network, include_troubleshooting)

        if workflow_type == "test" or workflow_type == "all":
            result["test"] = self._get_test_workflow(include_troubleshooting)

        if workflow_type == "cli_reference" or workflow_type == "all":
            result["cli_reference"] = self._get_cli_reference()

        if workflow_type == "networks" or workflow_type == "all":
            result["networks"] = self._get_network_configs()

        return result

    def _get_build_workflow(self, include_troubleshooting: bool) -> dict:
        """Get build workflow with commands."""
        workflow = {
            "name": BUILD_WORKFLOW["name"],
            "description": BUILD_WORKFLOW["description"],
            "prerequisites": BUILD_WORKFLOW["prerequisites"],
            "steps": BUILD_WORKFLOW["steps"],
            "optimization_tips": BUILD_WORKFLOW["optimization_tips"],
            "sample_cargo_toml": BUILD_WORKFLOW["sample_cargo_toml"],
            "quick_commands": {
                "build_debug": "cargo build --target wasm32-unknown-unknown",
                "build_release": "cargo build --release --target wasm32-unknown-unknown",
                "check": "cargo stylus check",
                "export_abi": "cargo stylus export-abi",
            },
        }

        if not include_troubleshooting:
            # Remove error handling from steps
            for step in workflow["steps"]:
                step.pop("common_errors", None)

        return workflow

    def _get_deploy_workflow(self, network: str, include_troubleshooting: bool) -> dict:
        """Get deploy workflow for specific network."""
        network_config = NETWORK_CONFIGS["networks"].get(
            network,
            NETWORK_CONFIGS["networks"]["arbitrum_sepolia"]
        )

        rpc_url = network_config["rpc_endpoints"]["primary"]
        explorer_url = network_config["explorer"]["url"]

        workflow = {
            "name": DEPLOY_WORKFLOW["name"],
            "description": DEPLOY_WORKFLOW["description"],
            "target_network": network_config,
            "prerequisites": DEPLOY_WORKFLOW["prerequisites"],
            "steps": DEPLOY_WORKFLOW["steps"],
            "post_deployment": DEPLOY_WORKFLOW["post_deployment"],
            "quick_commands": {
                "prepare_key": "echo 'YOUR_PRIVATE_KEY' > key.txt && chmod 600 key.txt",
                "check_balance": f"cast balance YOUR_ADDRESS --rpc-url {rpc_url}",
                "estimate_gas": f"cargo stylus deploy --estimate-gas --private-key-path=./key.txt --endpoint={rpc_url}",
                "deploy": f"cargo stylus deploy --private-key-path=./key.txt --endpoint={rpc_url}",
                "verify": f"cargo stylus verify --deployment-tx TX_HASH --endpoint={rpc_url}",
                "call_contract": f"cast call CONTRACT_ADDRESS 'functionName()' --rpc-url {rpc_url}",
                "send_tx": f"cast send CONTRACT_ADDRESS 'functionName()' --private-key-path=./key.txt --rpc-url {rpc_url}",
            },
            "explorer_url": explorer_url,
            "security_checklist": [
                "Private key NOT in git repository",
                "key.txt has 600 permissions",
                "Contract tested on testnet first",
                "Sufficient ETH for gas fees",
            ],
        }

        if include_troubleshooting:
            workflow["common_issues"] = DEPLOY_WORKFLOW["common_issues"]

        return workflow

    def _get_test_workflow(self, include_troubleshooting: bool) -> dict:
        """Get test workflow with commands."""
        workflow = {
            "name": TEST_WORKFLOW["name"],
            "description": TEST_WORKFLOW["description"],
            "test_types": TEST_WORKFLOW["test_types"],
            "steps": TEST_WORKFLOW["steps"],
            "foundry_integration": TEST_WORKFLOW["foundry_integration"],
            "quick_commands": {
                "run_all_tests": "cargo test",
                "run_with_output": "cargo test -- --nocapture",
                "run_specific": "cargo test test_function_name",
                "run_ignored": "cargo test -- --ignored",
                "foundry_test": "forge test --fork-url RPC_URL",
                "replay_tx": "cargo stylus replay --tx TX_HASH --endpoint RPC_URL",
            },
        }

        if include_troubleshooting:
            workflow["debugging"] = TEST_WORKFLOW["debugging"]

        return workflow

    def _get_cli_reference(self) -> dict:
        """Get cargo-stylus CLI reference."""
        return {
            "tool": STYLUS_CLI_RESOURCE["tool"],
            "version": STYLUS_CLI_RESOURCE["version"],
            "installation": STYLUS_CLI_RESOURCE["installation"],
            "commands": STYLUS_CLI_RESOURCE["commands"],
            "environment_variables": STYLUS_CLI_RESOURCE["environment_variables"],
            "cargo_toml_config": STYLUS_CLI_RESOURCE["cargo_toml_config"],
            "troubleshooting": STYLUS_CLI_RESOURCE["troubleshooting"],
        }

    def _get_network_configs(self) -> dict:
        """Get network configurations."""
        return {
            "networks": NETWORK_CONFIGS["networks"],
            "local_development": NETWORK_CONFIGS["local_development"],
            "gas_estimation": NETWORK_CONFIGS["gas_estimation"],
            "common_rpc_methods": NETWORK_CONFIGS["common_rpc_methods"],
        }

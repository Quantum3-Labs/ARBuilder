"""
MCP Resources for ARBuilder.

Resources are read-only knowledge endpoints that get injected into the AI IDE's context.
They provide static knowledge about Stylus development workflows, CLI commands, and configurations.
"""

from .stylus_cli import STYLUS_CLI_RESOURCE
from .workflows import BUILD_WORKFLOW, DEPLOY_WORKFLOW, TEST_WORKFLOW
from .networks import NETWORK_CONFIGS

# All available resources
RESOURCES = {
    "stylus://cli/commands": {
        "name": "Stylus CLI Commands",
        "description": "Complete reference for cargo-stylus CLI commands and options",
        "mimeType": "application/json",
        "content": STYLUS_CLI_RESOURCE,
    },
    "stylus://workflows/build": {
        "name": "Build Workflow",
        "description": "Step-by-step workflow for building Stylus contracts",
        "mimeType": "application/json",
        "content": BUILD_WORKFLOW,
    },
    "stylus://workflows/deploy": {
        "name": "Deploy Workflow",
        "description": "Step-by-step workflow for deploying Stylus contracts",
        "mimeType": "application/json",
        "content": DEPLOY_WORKFLOW,
    },
    "stylus://workflows/test": {
        "name": "Test Workflow",
        "description": "Step-by-step workflow for testing Stylus contracts",
        "mimeType": "application/json",
        "content": TEST_WORKFLOW,
    },
    "stylus://config/networks": {
        "name": "Network Configurations",
        "description": "Arbitrum network endpoints and chain configurations",
        "mimeType": "application/json",
        "content": NETWORK_CONFIGS,
    },
}

__all__ = ["RESOURCES", "STYLUS_CLI_RESOURCE", "BUILD_WORKFLOW", "DEPLOY_WORKFLOW", "TEST_WORKFLOW", "NETWORK_CONFIGS"]

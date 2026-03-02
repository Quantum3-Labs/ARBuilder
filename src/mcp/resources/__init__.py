"""
MCP Resources for ARBuilder.

Resources are read-only knowledge endpoints that get injected into the AI IDE's context.
They provide static knowledge about Stylus development workflows, CLI commands, and configurations.

Resources organized by milestone:
- M1: Stylus (CLI, workflows, networks, coding rules)
- M2: Arbitrum SDK (SDK rules)
- M3: Full dApp Builder (backend, frontend, indexer, oracle rules)
- M4: Orbit Chain (orbit rules)
"""

from .stylus_cli import STYLUS_CLI_RESOURCE
from .workflows import BUILD_WORKFLOW, DEPLOY_WORKFLOW, TEST_WORKFLOW
from .networks import NETWORK_CONFIGS
from .coding_rules import STYLUS_CODING_RULES
from .sdk_rules import SDK_CODING_RULES
from .backend_rules import BACKEND_CODING_RULES
from .frontend_rules import FRONTEND_CODING_RULES
from .indexer_rules import INDEXER_CODING_RULES
from .oracle_rules import ORACLE_CODING_RULES
from .orbit_rules import ORBIT_RULES

# All available resources
RESOURCES = {
    # M1: Stylus Resources
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
    "stylus://rules/coding": {
        "name": "Stylus Coding Rules",
        "description": "Coding guidelines and patterns for Stylus smart contracts",
        "mimeType": "application/json",
        "content": STYLUS_CODING_RULES,
    },
    # M2: Arbitrum SDK Resources
    "arbitrum://rules/sdk": {
        "name": "Arbitrum SDK Rules",
        "description": "Coding guidelines for Arbitrum SDK bridging and messaging",
        "mimeType": "application/json",
        "content": SDK_CODING_RULES,
    },
    # M3: Full dApp Builder Resources
    "dapp://rules/backend": {
        "name": "Backend Coding Rules",
        "description": "Guidelines for NestJS/Express Web3 backend development",
        "mimeType": "application/json",
        "content": BACKEND_CODING_RULES,
    },
    "dapp://rules/frontend": {
        "name": "Frontend Coding Rules",
        "description": "Guidelines for Next.js + wagmi + RainbowKit frontend development",
        "mimeType": "application/json",
        "content": FRONTEND_CODING_RULES,
    },
    "dapp://rules/indexer": {
        "name": "Indexer Coding Rules",
        "description": "Guidelines for The Graph subgraph development",
        "mimeType": "application/json",
        "content": INDEXER_CODING_RULES,
    },
    "dapp://rules/oracle": {
        "name": "Oracle Coding Rules",
        "description": "Guidelines for Chainlink oracle integration",
        "mimeType": "application/json",
        "content": ORACLE_CODING_RULES,
    },
    # M4: Orbit Chain Resources
    "orbit://rules/chain": {
        "name": "Orbit Chain Rules",
        "description": "Rules and constraints for Arbitrum Orbit chain deployment and configuration",
        "mimeType": "application/json",
        "content": ORBIT_RULES,
    },
}

__all__ = [
    "RESOURCES",
    # M1: Stylus
    "STYLUS_CLI_RESOURCE",
    "BUILD_WORKFLOW",
    "DEPLOY_WORKFLOW",
    "TEST_WORKFLOW",
    "NETWORK_CONFIGS",
    "STYLUS_CODING_RULES",
    # M2: SDK
    "SDK_CODING_RULES",
    # M3: dApp Builder
    "BACKEND_CODING_RULES",
    "FRONTEND_CODING_RULES",
    "INDEXER_CODING_RULES",
    "ORACLE_CODING_RULES",
    # M4: Orbit Chain
    "ORBIT_RULES",
]

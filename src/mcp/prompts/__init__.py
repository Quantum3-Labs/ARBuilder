"""
MCP Prompts for ARBuilder.

Prompts are reusable templates that guide the AI through specific workflows.
They can be parameterized and combined with resources for context-aware assistance.
"""

from .workflows import (
    BUILD_CONTRACT_PROMPT,
    DEPLOY_CONTRACT_PROMPT,
    DEBUG_ERROR_PROMPT,
    OPTIMIZE_GAS_PROMPT,
    GENERATE_CONTRACT_PROMPT,
)

# All available prompts
PROMPTS = {
    "build-contract": {
        "name": "Build Contract",
        "description": "Step-by-step guidance for building a Stylus contract",
        "arguments": [
            {
                "name": "project_path",
                "description": "Path to the Stylus project directory",
                "required": False,
            },
            {
                "name": "release_mode",
                "description": "Whether to build in release mode (default: true)",
                "required": False,
            },
        ],
        "template": BUILD_CONTRACT_PROMPT,
    },
    "deploy-contract": {
        "name": "Deploy Contract",
        "description": "Step-by-step guidance for deploying a Stylus contract",
        "arguments": [
            {
                "name": "network",
                "description": "Target network (arbitrum_sepolia, arbitrum_one, arbitrum_nova)",
                "required": True,
            },
            {
                "name": "key_method",
                "description": "How to provide private key (file, env, hardware)",
                "required": False,
            },
        ],
        "template": DEPLOY_CONTRACT_PROMPT,
    },
    "debug-error": {
        "name": "Debug Error",
        "description": "Diagnose and fix Stylus development errors",
        "arguments": [
            {
                "name": "error_message",
                "description": "The error message or stack trace",
                "required": True,
            },
            {
                "name": "context",
                "description": "Additional context (command run, code snippet)",
                "required": False,
            },
        ],
        "template": DEBUG_ERROR_PROMPT,
    },
    "optimize-gas": {
        "name": "Optimize Gas",
        "description": "Optimize contract for gas efficiency and size",
        "arguments": [
            {
                "name": "contract_code",
                "description": "The contract code to optimize",
                "required": True,
            },
            {
                "name": "focus",
                "description": "Focus area: size, compute, storage, or all",
                "required": False,
            },
        ],
        "template": OPTIMIZE_GAS_PROMPT,
    },
    "generate-contract": {
        "name": "Generate Contract",
        "description": "Generate a new Stylus contract from requirements",
        "arguments": [
            {
                "name": "description",
                "description": "Natural language description of the contract",
                "required": True,
            },
            {
                "name": "contract_type",
                "description": "Type: token, nft, defi, utility, governance",
                "required": False,
            },
            {
                "name": "include_tests",
                "description": "Whether to generate tests (default: true)",
                "required": False,
            },
        ],
        "template": GENERATE_CONTRACT_PROMPT,
    },
}

__all__ = ["PROMPTS", "BUILD_CONTRACT_PROMPT", "DEPLOY_CONTRACT_PROMPT", "DEBUG_ERROR_PROMPT", "OPTIMIZE_GAS_PROMPT", "GENERATE_CONTRACT_PROMPT"]

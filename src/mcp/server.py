"""
MCP Server for ARBuilder.

Exposes Stylus development tools, resources, and prompts via the Model Context Protocol.

MCP Capabilities:
- Tools: 12 development tools (M1: 5 Stylus, M2: 3 Arbitrum SDK, M3: 4 dApp builder)
- Resources: Static knowledge (CLI commands, network configs, workflows)
- Prompts: Reusable workflow templates
"""

import json
import sys
from typing import Any

# M1: Stylus Tools
from .tools import (
    # M1: Stylus Tools
    GetStylusContextTool,
    GenerateStylusCodeTool,
    AskStylusTool,
    GenerateTestsTool,
    GetWorkflowTool,
    # M2: Arbitrum SDK Tools
    GenerateBridgeCodeTool,
    GenerateMessagingCodeTool,
    AskBridgingTool,
    # M3: dApp Builder Tools
    GenerateBackendTool,
    GenerateFrontendTool,
    GenerateIndexerTool,
    GenerateDappTool,
)

from .resources import RESOURCES
from .prompts import PROMPTS


# Tool definitions for MCP
TOOL_DEFINITIONS = [
    {
        "name": "get_stylus_context",
        "description": "Retrieve relevant Stylus documentation and code examples from the knowledge base. Use this to find examples, patterns, and documentation for Stylus development.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (concept, function name, or code pattern)",
                },
                "n_results": {
                    "type": "integer",
                    "description": "Number of results to return (1-20, default: 5)",
                    "default": 5,
                },
                "content_type": {
                    "type": "string",
                    "enum": ["all", "docs", "code"],
                    "description": "Filter by content type (default: all)",
                    "default": "all",
                },
                "rerank": {
                    "type": "boolean",
                    "description": "Whether to rerank results for relevance (default: true)",
                    "default": True,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "generate_stylus_code",
        "description": "Generate Stylus/Rust smart contract code based on requirements. Uses RAG context to provide relevant examples.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Description of the code to generate",
                },
                "context_query": {
                    "type": "string",
                    "description": "Optional query to retrieve additional context",
                },
                "contract_type": {
                    "type": "string",
                    "enum": ["erc20", "erc721", "erc1155", "custom"],
                    "description": "Type of contract to generate",
                },
                "include_tests": {
                    "type": "boolean",
                    "description": "Whether to include unit tests (default: false)",
                    "default": False,
                },
                "temperature": {
                    "type": "number",
                    "description": "Generation temperature 0-1 (default: 0.2)",
                    "default": 0.2,
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "ask_stylus",
        "description": "Ask questions about Stylus development, get concept explanations, or debug code issues.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to answer",
                },
                "code_context": {
                    "type": "string",
                    "description": "Optional code snippet for context (e.g., for debugging)",
                },
                "question_type": {
                    "type": "string",
                    "enum": ["concept", "debugging", "comparison", "howto", "general"],
                    "description": "Type of question for optimized response (default: general)",
                    "default": "general",
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "generate_tests",
        "description": "Generate test cases for Stylus smart contracts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "contract_code": {
                    "type": "string",
                    "description": "The contract code to generate tests for",
                },
                "test_framework": {
                    "type": "string",
                    "enum": ["rust_native", "foundry", "hardhat"],
                    "description": "Test framework to use (default: rust_native)",
                    "default": "rust_native",
                },
                "test_types": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["unit", "integration", "fuzz"]},
                    "description": "Types of tests to generate (default: [\"unit\"])",
                    "default": ["unit"],
                },
                "coverage_focus": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific functions to focus on",
                },
            },
            "required": ["contract_code"],
        },
    },
    {
        "name": "get_workflow",
        "description": "Get structured workflow information for Stylus development. Returns step-by-step commands for build, deploy, test operations. Use this when the user needs guidance on development workflows.",
        "inputSchema": {
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
                    "description": "Target network for deploy workflow (default: arbitrum_sepolia)",
                    "default": "arbitrum_sepolia",
                },
                "include_troubleshooting": {
                    "type": "boolean",
                    "description": "Include common errors and solutions (default: true)",
                    "default": True,
                },
            },
            "required": ["workflow_type"],
        },
    },
    # M2: Arbitrum SDK Tools
    {
        "name": "generate_bridge_code",
        "description": "Generate TypeScript code for Arbitrum asset bridging using the Arbitrum SDK. Supports ETH/ERC20 bridging L1<->L2 and L1->L3.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "bridge_type": {
                    "type": "string",
                    "enum": ["eth_deposit", "eth_deposit_to", "eth_withdraw",
                             "erc20_deposit", "erc20_withdraw",
                             "eth_l1_l3", "erc20_l1_l3"],
                    "description": "Type of bridging operation to generate code for",
                },
                "amount": {
                    "type": "string",
                    "description": "Amount to bridge (in ETH or token units)",
                    "default": "0.1",
                },
                "token_address": {
                    "type": "string",
                    "description": "L1 token address (required for erc20 operations)",
                },
                "destination_address": {
                    "type": "string",
                    "description": "Destination address (for deposit_to operations)",
                },
            },
            "required": ["bridge_type"],
        },
    },
    {
        "name": "generate_messaging_code",
        "description": "Generate TypeScript code for Arbitrum cross-chain messaging. Supports L1->L2 retryable tickets and L2->L1 messages.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message_type": {
                    "type": "string",
                    "enum": ["l1_to_l2", "l2_to_l1", "l2_to_l1_claim", "check_status"],
                    "description": "Type of messaging operation to generate code for",
                },
                "include_example": {
                    "type": "boolean",
                    "description": "Include example usage with sample contract call",
                    "default": True,
                },
            },
            "required": ["message_type"],
        },
    },
    {
        "name": "ask_bridging",
        "description": "Answer questions about Arbitrum bridging and cross-chain messaging patterns.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Question about Arbitrum bridging or messaging",
                },
                "include_code_example": {
                    "type": "boolean",
                    "description": "Include a code example in the answer if relevant",
                    "default": False,
                },
            },
            "required": ["question"],
        },
    },
    # M3: dApp Builder Tools
    {
        "name": "generate_backend",
        "description": "Generate NestJS or Express backend code with Web3 integration for Arbitrum dApps.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Description of the backend to generate",
                },
                "framework": {
                    "type": "string",
                    "enum": ["nestjs", "express"],
                    "description": "Backend framework to use (default: nestjs)",
                    "default": "nestjs",
                },
                "features": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["auth", "database", "web3", "api"]},
                    "description": "Features to include (default: [api, web3])",
                    "default": ["api", "web3"],
                },
                "contract_abi": {
                    "type": "string",
                    "description": "Optional contract ABI for generating typed interactions",
                },
                "database": {
                    "type": "string",
                    "enum": ["postgresql", "mongodb", "none"],
                    "description": "Database to use (default: postgresql)",
                    "default": "postgresql",
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "generate_frontend",
        "description": "Generate Next.js frontend with wallet integration (wagmi, viem, RainbowKit) for Arbitrum dApps.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Description of the frontend to generate",
                },
                "wallet_kit": {
                    "type": "string",
                    "enum": ["rainbowkit", "connectkit", "web3modal"],
                    "description": "Wallet connection kit to use (default: rainbowkit)",
                    "default": "rainbowkit",
                },
                "ui_library": {
                    "type": "string",
                    "enum": ["daisyui", "shadcn", "none"],
                    "description": "UI component library (default: daisyui)",
                    "default": "daisyui",
                },
                "features": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["wallet", "contract-read", "contract-write", "tx-history"]},
                    "description": "Features to include",
                    "default": ["wallet", "contract-read"],
                },
                "contract_abi": {
                    "type": "string",
                    "description": "Optional contract ABI for typed hooks",
                },
                "networks": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["arbitrum_one", "arbitrum_sepolia"]},
                    "description": "Networks to support",
                    "default": ["arbitrum_one", "arbitrum_sepolia"],
                },
                "app_name": {
                    "type": "string",
                    "description": "Name of the application",
                    "default": "My dApp",
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "generate_indexer",
        "description": "Generate The Graph subgraph for indexing Arbitrum smart contract events.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Description of what to index",
                },
                "contract_address": {
                    "type": "string",
                    "description": "Deployed contract address",
                },
                "contract_abi": {
                    "type": "string",
                    "description": "Contract ABI with events to index",
                },
                "contract_name": {
                    "type": "string",
                    "description": "Name of the contract",
                    "default": "Contract",
                },
                "network": {
                    "type": "string",
                    "enum": ["arbitrum-one", "arbitrum-sepolia"],
                    "description": "Network to deploy to (default: arbitrum-one)",
                    "default": "arbitrum-one",
                },
                "entities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Entity names to track",
                },
                "start_block": {
                    "type": "integer",
                    "description": "Block number to start indexing from",
                    "default": 0,
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "generate_dapp",
        "description": "Orchestrate full-stack dApp generation combining contract, backend, frontend, and indexer.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Full dApp description",
                },
                "name": {
                    "type": "string",
                    "description": "Project name",
                    "default": "my-dapp",
                },
                "include": {
                    "type": "object",
                    "properties": {
                        "contract": {"type": "boolean", "default": True},
                        "backend": {"type": "boolean", "default": True},
                        "frontend": {"type": "boolean", "default": True},
                        "indexer": {"type": "boolean", "default": False},
                    },
                    "description": "Components to include in generation",
                },
                "contract_type": {
                    "type": "string",
                    "enum": ["erc20", "erc721", "erc1155", "custom"],
                    "description": "Type of contract to generate",
                    "default": "custom",
                },
                "backend_framework": {
                    "type": "string",
                    "enum": ["nestjs", "express"],
                    "default": "nestjs",
                },
                "wallet_kit": {
                    "type": "string",
                    "enum": ["rainbowkit", "connectkit", "web3modal"],
                    "default": "rainbowkit",
                },
                "ui_library": {
                    "type": "string",
                    "enum": ["daisyui", "shadcn"],
                    "default": "daisyui",
                },
                "network": {
                    "type": "string",
                    "enum": ["arbitrum-one", "arbitrum-sepolia"],
                    "default": "arbitrum-sepolia",
                },
            },
            "required": ["prompt"],
        },
    },
]


class MCPServer:
    """
    MCP Server for ARBuilder tools.

    Handles tool registration, resource access, prompt templates, and execution.

    Capabilities:
    - tools/list, tools/call: 12 development tools (M1: 5 Stylus, M2: 3 SDK, M3: 4 dApp)
    - resources/list, resources/read: Static knowledge injection
    - prompts/list, prompts/get: Workflow templates
    """

    def __init__(self):
        """Initialize the server and tools."""
        # Initialize shared context tool
        self.context_tool = GetStylusContextTool()

        # Initialize all tools
        self.tools = {
            # M1: Stylus Tools
            "get_stylus_context": self.context_tool,
            "generate_stylus_code": GenerateStylusCodeTool(context_tool=self.context_tool),
            "ask_stylus": AskStylusTool(context_tool=self.context_tool),
            "generate_tests": GenerateTestsTool(),
            "get_workflow": GetWorkflowTool(),
            # M2: Arbitrum SDK Tools
            "generate_bridge_code": GenerateBridgeCodeTool(context_tool=self.context_tool),
            "generate_messaging_code": GenerateMessagingCodeTool(context_tool=self.context_tool),
            "ask_bridging": AskBridgingTool(context_tool=self.context_tool),
            # M3: dApp Builder Tools
            "generate_backend": GenerateBackendTool(context_tool=self.context_tool),
            "generate_frontend": GenerateFrontendTool(context_tool=self.context_tool),
            "generate_indexer": GenerateIndexerTool(context_tool=self.context_tool),
            "generate_dapp": GenerateDappTool(context_tool=self.context_tool),
        }

        # Resources are static knowledge
        self.resources = RESOURCES

        # Prompts are workflow templates
        self.prompts = PROMPTS

    def get_tool_definitions(self) -> list[dict]:
        """Get MCP tool definitions."""
        return TOOL_DEFINITIONS

    def get_resource_list(self) -> list[dict]:
        """Get list of available resources."""
        return [
            {
                "uri": uri,
                "name": resource["name"],
                "description": resource["description"],
                "mimeType": resource["mimeType"],
            }
            for uri, resource in self.resources.items()
        ]

    def get_resource(self, uri: str) -> dict:
        """Get a specific resource by URI."""
        if uri not in self.resources:
            return {"error": f"Resource not found: {uri}"}

        resource = self.resources[uri]
        return {
            "uri": uri,
            "mimeType": resource["mimeType"],
            "contents": [
                {
                    "uri": uri,
                    "mimeType": resource["mimeType"],
                    "text": json.dumps(resource["content"], indent=2),
                }
            ],
        }

    def get_prompt_list(self) -> list[dict]:
        """Get list of available prompts."""
        return [
            {
                "name": name,
                "description": prompt["description"],
                "arguments": prompt["arguments"],
            }
            for name, prompt in self.prompts.items()
        ]

    def get_prompt(self, name: str, arguments: dict = None) -> dict:
        """Get a specific prompt with arguments filled in."""
        if name not in self.prompts:
            return {"error": f"Prompt not found: {name}"}

        prompt = self.prompts[name]
        template = prompt["template"]

        # Fill in arguments
        if arguments:
            for arg_name, arg_value in arguments.items():
                template = template.replace(f"{{{arg_name}}}", str(arg_value))

        return {
            "description": prompt["description"],
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": template,
                    },
                }
            ],
        }

    def execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Returns:
            Tool result as dictionary.
        """
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}

        # Validate required parameters
        tool_def = next((t for t in TOOL_DEFINITIONS if t["name"] == tool_name), None)
        if tool_def:
            required_params = tool_def.get("inputSchema", {}).get("required", [])
            missing_params = [p for p in required_params if p not in arguments]
            if missing_params:
                return {"error": f"Missing required parameter(s): {', '.join(missing_params)}"}

        tool = self.tools[tool_name]
        try:
            return tool.execute(**arguments)
        except TypeError as e:
            # Catch any remaining parameter errors
            return {"error": f"Invalid parameters: {str(e)}"}

    def handle_request(self, request: dict) -> dict:
        """
        Handle an MCP request.

        Args:
            request: MCP request dictionary.

        Returns:
            MCP response dictionary.
        """
        method = request.get("method", "")

        # Initialize response
        if method == "initialize":
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                },
                "serverInfo": {
                    "name": "arbbuilder",
                    "version": "0.2.0",
                },
            }

        # Tools
        elif method == "tools/list":
            return {
                "tools": self.get_tool_definitions(),
            }

        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})

            result = self.execute_tool(tool_name, arguments)

            # Format as MCP response
            if "error" in result:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: {result['error']}",
                        }
                    ],
                    "isError": True,
                }

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2),
                    }
                ],
            }

        # Resources
        elif method == "resources/list":
            return {
                "resources": self.get_resource_list(),
            }

        elif method == "resources/read":
            params = request.get("params", {})
            uri = params.get("uri", "")
            return self.get_resource(uri)

        # Prompts
        elif method == "prompts/list":
            return {
                "prompts": self.get_prompt_list(),
            }

        elif method == "prompts/get":
            params = request.get("params", {})
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            return self.get_prompt(name, arguments)

        else:
            return {"error": f"Unknown method: {method}"}

    def run_stdio(self):
        """Run server in stdio mode for MCP."""
        print("ARBuilder MCP Server started", file=sys.stderr)
        print("Capabilities: 12 tools (M1: 5 Stylus, M2: 3 SDK, M3: 4 dApp), 5 resources, 5 prompts", file=sys.stderr)

        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                request_id = request.get("id")
                result = self.handle_request(request)

                # Wrap response in JSON-RPC 2.0 format
                if "error" in result and isinstance(result.get("error"), str):
                    # Convert simple error to JSON-RPC error format
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32600,
                            "message": result["error"],
                        },
                    }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": result,
                    }

                print(json.dumps(response))
                sys.stdout.flush()
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}",
                    },
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}",
                    },
                }
                print(json.dumps(error_response))
                sys.stdout.flush()


def main():
    """Entry point for MCP server."""
    server = MCPServer()
    server.run_stdio()


if __name__ == "__main__":
    main()

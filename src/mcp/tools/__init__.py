"""
MCP Tools for ARBuilder.

M1: Stylus Tools (6):
1. get_stylus_context - RAG retrieval for docs and code
2. generate_stylus_code - Code generation
3. ask_stylus - Q&A and debugging
4. generate_tests - Test generation
5. get_workflow - Build/deploy/test workflow guidance
6. validate_stylus_code - Compile-check with cargo check (Docker)

M2: Arbitrum SDK Tools (3):
7. generate_bridge_code - ETH/ERC20 bridging code generation
8. generate_messaging_code - Cross-chain messaging code
9. ask_bridging - Q&A for bridging patterns

M3: Full dApp Builder Tools (5):
10. generate_backend - NestJS/Express backend generation
11. generate_frontend - Next.js + wagmi + RainbowKit frontend
12. generate_indexer - The Graph subgraph generation
13. generate_oracle - Chainlink oracle integration
14. orchestrate_dapp - Full dApp scaffolding coordinator
"""

from .ask_bridging import AskBridgingTool
from .ask_stylus import AskStylusTool
from .base import BaseTool, ToolResult

# M3: Full dApp Builder Tools
from .generate_backend import GenerateBackendTool

# M2: Arbitrum SDK Tools
from .generate_bridge_code import GenerateBridgeCodeTool
from .generate_frontend import GenerateFrontendTool
from .generate_indexer import GenerateIndexerTool
from .generate_messaging_code import GenerateMessagingCodeTool
from .generate_oracle import GenerateOracleTool
from .generate_stylus_code import GenerateStylusCodeTool
from .generate_tests import GenerateTestsTool

# M1: Stylus Tools
from .get_stylus_context import GetStylusContextTool
from .get_workflow import GetWorkflowTool
from .orchestrate_dapp import OrchestrateDappTool
from .validate_stylus_code import ValidateStylusCodeTool

__all__ = [
    # Base
    "BaseTool",
    "ToolResult",
    # M1: Stylus
    "GetStylusContextTool",
    "GenerateStylusCodeTool",
    "AskStylusTool",
    "GenerateTestsTool",
    "GetWorkflowTool",
    "ValidateStylusCodeTool",
    # M2: Arbitrum SDK
    "GenerateBridgeCodeTool",
    "GenerateMessagingCodeTool",
    "AskBridgingTool",
    # M3: Full dApp Builder
    "GenerateBackendTool",
    "GenerateFrontendTool",
    "GenerateIndexerTool",
    "GenerateOracleTool",
    "OrchestrateDappTool",
]

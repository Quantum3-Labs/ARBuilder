"""
MCP Tools for ARBuilder.

M1: Stylus Tools (5):
1. get_stylus_context - RAG retrieval for docs and code
2. generate_stylus_code - Stylus contract code generation
3. ask_stylus - Q&A and debugging
4. generate_tests - Test generation
5. get_workflow - Build/deploy/test workflow guidance

M2: Arbitrum SDK Tools (3):
6. generate_bridge_code - ETH/ERC20 bridging code generation
7. generate_messaging_code - Cross-chain messaging code
8. ask_bridging - Q&A for bridging patterns

M3: Full dApp Builder Tools (4):
9. generate_backend - NestJS/Express backend generation
10. generate_frontend - Next.js frontend with wallet integration
11. generate_indexer - The Graph subgraph generation
12. generate_dapp - Full-stack dApp orchestration
"""

from .base import BaseTool, ToolResult

# M1: Stylus Tools
from .get_stylus_context import GetStylusContextTool
from .generate_stylus_code import GenerateStylusCodeTool
from .ask_stylus import AskStylusTool
from .generate_tests import GenerateTestsTool
from .get_workflow import GetWorkflowTool

# M2: Arbitrum SDK Tools
from .generate_bridge_code import GenerateBridgeCodeTool
from .generate_messaging_code import GenerateMessagingCodeTool
from .ask_bridging import AskBridgingTool

# M3: Full dApp Builder Tools
from .generate_backend import GenerateBackendTool
from .generate_frontend import GenerateFrontendTool
from .generate_indexer import GenerateIndexerTool
from .generate_dapp import GenerateDappTool

__all__ = [
    # Base
    "BaseTool",
    "ToolResult",
    # M1: Stylus Tools
    "GetStylusContextTool",
    "GenerateStylusCodeTool",
    "AskStylusTool",
    "GenerateTestsTool",
    "GetWorkflowTool",
    # M2: Arbitrum SDK Tools
    "GenerateBridgeCodeTool",
    "GenerateMessagingCodeTool",
    "AskBridgingTool",
    # M3: dApp Builder Tools
    "GenerateBackendTool",
    "GenerateFrontendTool",
    "GenerateIndexerTool",
    "GenerateDappTool",
]

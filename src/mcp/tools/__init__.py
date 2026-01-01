"""
MCP Tools for ARBuilder.

M1: Stylus Tools (5):
1. get_stylus_context - RAG retrieval for docs and code
2. generate_stylus_code - Code generation
3. ask_stylus - Q&A and debugging
4. generate_tests - Test generation
5. get_workflow - Build/deploy/test workflow guidance

M2: Arbitrum SDK Tools (3):
6. generate_bridge_code - ETH/ERC20 bridging code generation
7. generate_messaging_code - Cross-chain messaging code
8. ask_bridging - Q&A for bridging patterns
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
    # M2: Arbitrum SDK
    "GenerateBridgeCodeTool",
    "GenerateMessagingCodeTool",
    "AskBridgingTool",
]

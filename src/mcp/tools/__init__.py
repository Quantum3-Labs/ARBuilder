"""
MCP Tools for ARBuilder.

Provides 4 main tools for Stylus smart contract development:
1. get_stylus_context - RAG retrieval for docs and code
2. generate_stylus_code - Code generation
3. ask_stylus - Q&A and debugging
4. generate_tests - Test generation
"""

from .base import BaseTool, ToolResult
from .get_stylus_context import GetStylusContextTool
from .generate_stylus_code import GenerateStylusCodeTool
from .ask_stylus import AskStylusTool
from .generate_tests import GenerateTestsTool

__all__ = [
    "BaseTool",
    "ToolResult",
    "GetStylusContextTool",
    "GenerateStylusCodeTool",
    "AskStylusTool",
    "GenerateTestsTool",
]

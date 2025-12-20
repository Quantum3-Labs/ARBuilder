"""
Pytest configuration for MCP tools tests.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


@pytest.fixture(scope="session")
def tools():
    """
    Provide tool implementations for testing.

    Uses actual implementations if available, falls back to mocks.
    """
    try:
        from src.mcp.tools import (
            GetStylusContextTool,
            GenerateStylusCodeTool,
            AskStylusTool,
            GenerateTestsTool,
        )

        # Create shared context tool
        context_tool = GetStylusContextTool()

        return {
            "get_stylus_context": context_tool,
            "generate_stylus_code": GenerateStylusCodeTool(context_tool=context_tool),
            "ask_stylus": AskStylusTool(context_tool=context_tool),
            "generate_tests": GenerateTestsTool(),
        }
    except ImportError as e:
        print(f"Warning: Could not import tools, using mocks: {e}")
        return _create_mock_tools()


def _create_mock_tools():
    """Create mock tool implementations for testing without API access."""

    class MockGetStylusContextTool:
        def execute(self, **kwargs):
            query = kwargs.get("query", "")
            if not query:
                return {"error": "Query is required and cannot be empty"}
            return {
                "contexts": [],
                "total_results": 0,
                "query": query,
            }

    class MockGenerateStylusCodeTool:
        def execute(self, **kwargs):
            prompt = kwargs.get("prompt", "")
            if not prompt:
                return {"error": "Prompt is required and cannot be empty"}
            return {
                "code": "",
                "explanation": "",
                "dependencies": [],
                "warnings": [],
                "context_used": [],
            }

    class MockAskStylusTool:
        def execute(self, **kwargs):
            question = kwargs.get("question", "")
            if not question:
                return {"error": "Question is required and cannot be empty"}
            return {
                "answer": "",
                "code_examples": [],
                "references": [],
                "follow_up_questions": [],
            }

    class MockGenerateTestsTool:
        def execute(self, **kwargs):
            contract_code = kwargs.get("contract_code", "")
            if not contract_code:
                return {"error": "Contract code is required and cannot be empty"}
            return {
                "tests": "",
                "test_summary": {
                    "total_tests": 0,
                    "unit_tests": 0,
                    "integration_tests": 0,
                    "fuzz_tests": 0,
                },
                "coverage_estimate": {
                    "functions_covered": [],
                    "functions_not_covered": [],
                    "edge_cases": [],
                },
                "setup_instructions": "",
            }

    return {
        "get_stylus_context": MockGetStylusContextTool(),
        "generate_stylus_code": MockGenerateStylusCodeTool(),
        "ask_stylus": MockAskStylusTool(),
        "generate_tests": MockGenerateTestsTool(),
    }


@pytest.fixture(scope="session")
def get_stylus_context_tool(tools):
    """Provide get_stylus_context tool instance."""
    return tools["get_stylus_context"]


@pytest.fixture(scope="session")
def generate_stylus_code_tool(tools):
    """Provide generate_stylus_code tool instance."""
    return tools["generate_stylus_code"]


@pytest.fixture(scope="session")
def ask_stylus_tool(tools):
    """Provide ask_stylus tool instance."""
    return tools["ask_stylus"]


@pytest.fixture(scope="session")
def generate_tests_tool(tools):
    """Provide generate_tests tool instance."""
    return tools["generate_tests"]


@pytest.fixture
def vectordb():
    """Provide VectorDB instance for context retrieval tests."""
    from src.embeddings.vectordb import VectorDB
    return VectorDB(collection_name="arbbuilder")


@pytest.fixture
def embedding_client():
    """Provide embedding client for tests."""
    from src.embeddings.embedder import EmbeddingClient
    return EmbeddingClient()

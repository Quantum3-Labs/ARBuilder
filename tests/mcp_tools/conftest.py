"""
Pytest configuration for MCP tools tests.
"""

import sys
from pathlib import Path

import pytest

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
            AskStylusTool,
            GenerateStylusCodeTool,
            GenerateTestsTool,
            GetStylusContextTool,
        )

        # Create shared context tool
        context_tool = GetStylusContextTool()

        return {
            "get_stylus_context": context_tool,
            "generate_stylus_code": GenerateStylusCodeTool(context_tool=context_tool),
            "ask_stylus": AskStylusTool(context_tool=context_tool),
            "generate_tests": GenerateTestsTool(),
        }
    except (ImportError, ValueError) as e:
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


# ============================================================================
# M3 Tool Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def m3_tools():
    """
    Provide M3 tool implementations for testing.

    Uses actual implementations if available, falls back to mocks.
    """
    try:
        from src.mcp.tools import (
            GenerateBackendTool,
            GenerateFrontendTool,
            GenerateIndexerTool,
            GenerateOracleTool,
            OrchestrateDappTool,
        )

        return {
            "generate_backend": GenerateBackendTool(),
            "generate_frontend": GenerateFrontendTool(),
            "generate_indexer": GenerateIndexerTool(),
            "generate_oracle": GenerateOracleTool(),
            "orchestrate_dapp": OrchestrateDappTool(),
        }
    except (ImportError, ValueError) as e:
        print(f"Warning: Could not import M3 tools, using mocks: {e}")
        return _create_mock_m3_tools()


def _create_mock_m3_tools():
    """Create mock M3 tool implementations for testing without API access."""

    class MockGenerateBackendTool:
        def execute(self, **kwargs):
            return {
                "files": {"src/app.module.ts": "// mock"},
                "dependencies": {"nestjs": "^10.0.0"},
                "env_vars": ["DATABASE_URL"],
            }

    class MockGenerateFrontendTool:
        def execute(self, **kwargs):
            return {
                "files": {"src/app/page.tsx": "// mock"},
                "dependencies": {"wagmi": "^2.0.0"},
                "env_vars": ["NEXT_PUBLIC_CONTRACT_ADDRESS"],
            }

    class MockGenerateIndexerTool:
        def execute(self, **kwargs):
            return {
                "files": {"subgraph.yaml": "# mock", "schema.graphql": "# mock"},
                "dependencies": {"@graphprotocol/graph-cli": "^0.71.0"},
            }

    class MockGenerateOracleTool:
        def execute(self, **kwargs):
            return {
                "files": {"contracts/PriceFeed.sol": "// mock"},
                "dependencies": {"@chainlink/contracts": "^1.1.0"},
            }

    class MockOrchestrateDappTool:
        def execute(self, **kwargs):
            return {
                "project": "my-dapp",
                "files": {},
                "components": kwargs.get("components", ["contract", "frontend"]),
            }

    return {
        "generate_backend": MockGenerateBackendTool(),
        "generate_frontend": MockGenerateFrontendTool(),
        "generate_indexer": MockGenerateIndexerTool(),
        "generate_oracle": MockGenerateOracleTool(),
        "orchestrate_dapp": MockOrchestrateDappTool(),
    }


@pytest.fixture(scope="session")
def generate_backend_tool(m3_tools):
    """Provide generate_backend tool instance."""
    return m3_tools["generate_backend"]


@pytest.fixture(scope="session")
def generate_frontend_tool(m3_tools):
    """Provide generate_frontend tool instance."""
    return m3_tools["generate_frontend"]


@pytest.fixture(scope="session")
def generate_indexer_tool(m3_tools):
    """Provide generate_indexer tool instance."""
    return m3_tools["generate_indexer"]


@pytest.fixture(scope="session")
def generate_oracle_tool(m3_tools):
    """Provide generate_oracle tool instance."""
    return m3_tools["generate_oracle"]


@pytest.fixture(scope="session")
def orchestrate_dapp_tool(m3_tools):
    """Provide orchestrate_dapp tool instance."""
    return m3_tools["orchestrate_dapp"]


# ============================================================================
# M4 Orbit Tool Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def m4_tools():
    """
    Provide M4 Orbit tool implementations for testing.

    M4 tools are template-based and do not require API keys.
    Falls back to mocks if imports fail.
    """
    try:
        from src.mcp.tools import (
            AskOrbitTool,
            GenerateOrbitConfigTool,
            GenerateOrbitDeploymentTool,
            GenerateValidatorSetupTool,
            OrchestrateOrbitTool,
        )

        return {
            "generate_orbit_config": GenerateOrbitConfigTool(),
            "generate_orbit_deployment": GenerateOrbitDeploymentTool(),
            "generate_validator_setup": GenerateValidatorSetupTool(),
            "ask_orbit": AskOrbitTool(),
            "orchestrate_orbit": OrchestrateOrbitTool(),
        }
    except (ImportError, ValueError) as e:
        print(f"Warning: Could not import M4 tools, using mocks: {e}")
        return _create_mock_m4_tools()


def _create_mock_m4_tools():
    """Create mock M4 tool implementations for testing without imports."""

    class MockGenerateOrbitConfigTool:
        def execute(self, **kwargs):
            return {
                "files": {"scripts/prepare-chain-config.ts": "// mock"},
                "dependencies": {"viem": "^1.20.0"},
                "chain_config": {"chain_id": kwargs.get("chain_id", 412346)},
                "template_used": "chain_config",
            }

    class MockGenerateOrbitDeploymentTool:
        def execute(self, **kwargs):
            return {
                "files": {"scripts/deploy-rollup.ts": "// mock"},
                "dependencies": {"viem": "^1.20.0"},
                "deployment_type": kwargs.get("deployment_type", "rollup"),
            }

    class MockGenerateValidatorSetupTool:
        def execute(self, **kwargs):
            return {
                "files": {"scripts/manage-validators.ts": "// mock"},
                "action": kwargs.get("action", "list"),
                "target": kwargs.get("target", "validator"),
            }

    class MockAskOrbitTool:
        def execute(self, **kwargs):
            return {
                "answer": "Orbit chains are L2/L3 chains built on Arbitrum technology.",
                "topics": ["general"],
                "references": ["https://docs.arbitrum.io/launch-orbit-chain/orbit-gentle-introduction"],
            }

    class MockOrchestrateOrbitTool:
        def execute(self, **kwargs):
            return {
                "files": {
                    "package.json": "{}",
                    "docker-compose.yml": "# mock",
                    "README.md": "# mock",
                    "scripts/deploy-rollup.ts": "// mock",
                    "scripts/prepare-chain-config.ts": "// mock",
                },
                "dependencies": {"viem": "^1.20.0"},
                "setup_instructions": ["Step 1: Install deps"],
            }

    return {
        "generate_orbit_config": MockGenerateOrbitConfigTool(),
        "generate_orbit_deployment": MockGenerateOrbitDeploymentTool(),
        "generate_validator_setup": MockGenerateValidatorSetupTool(),
        "ask_orbit": MockAskOrbitTool(),
        "orchestrate_orbit": MockOrchestrateOrbitTool(),
    }


@pytest.fixture(scope="session")
def generate_orbit_config_tool(m4_tools):
    """Provide generate_orbit_config tool instance."""
    return m4_tools["generate_orbit_config"]


@pytest.fixture(scope="session")
def generate_orbit_deployment_tool(m4_tools):
    """Provide generate_orbit_deployment tool instance."""
    return m4_tools["generate_orbit_deployment"]


@pytest.fixture(scope="session")
def generate_validator_setup_tool(m4_tools):
    """Provide generate_validator_setup tool instance."""
    return m4_tools["generate_validator_setup"]


@pytest.fixture(scope="session")
def ask_orbit_tool(m4_tools):
    """Provide ask_orbit tool instance."""
    return m4_tools["ask_orbit"]


@pytest.fixture(scope="session")
def orchestrate_orbit_tool(m4_tools):
    """Provide orchestrate_orbit tool instance."""
    return m4_tools["orchestrate_orbit"]

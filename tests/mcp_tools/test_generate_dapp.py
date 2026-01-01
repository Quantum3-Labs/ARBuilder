"""
Test cases for generate_dapp MCP tool.

Tests full-stack dApp generation orchestrating all components.
"""

import pytest
import re


GENERATE_DAPP_TEST_CASES = [
    # ===== Full Stack Generation (P0) =====
    {
        "id": "dapp_fullstack_001",
        "name": "Full Stack: complete dApp with all components",
        "input": {
            "prompt": "Create a token staking dApp where users can stake tokens and earn rewards",
            "name": "staking-dapp",
            "include": {
                "contract": True,
                "backend": True,
                "frontend": True,
                "indexer": False,
            },
        },
        "expected": {
            "has_components": ["contract", "backend", "frontend"],
            "has_root_files": True,
            "has_integration_guide": True,
            "has_project_structure": True,
        },
        "priority": "P0",
        "category": "fullstack",
    },
    {
        "id": "dapp_fullstack_002",
        "name": "Full Stack: NFT marketplace",
        "input": {
            "prompt": "Create an NFT marketplace with minting, listing, and buying functionality",
            "name": "nft-marketplace",
            "contract_type": "erc721",
            "include": {
                "contract": True,
                "backend": True,
                "frontend": True,
                "indexer": True,
            },
        },
        "expected": {
            "has_components": ["contract", "backend", "frontend", "indexer"],
            "has_integration_guide": True,
        },
        "priority": "P0",
        "category": "fullstack",
    },

    # ===== Contract + Frontend Only (P0) =====
    {
        "id": "dapp_partial_001",
        "name": "Partial: contract and frontend only",
        "input": {
            "prompt": "Create a simple voting dApp",
            "name": "voting-app",
            "include": {
                "contract": True,
                "backend": False,
                "frontend": True,
                "indexer": False,
            },
        },
        "expected": {
            "has_components": ["contract", "frontend"],
            "missing_components": ["backend", "indexer"],
        },
        "priority": "P0",
        "category": "partial",
    },
    {
        "id": "dapp_partial_002",
        "name": "Partial: backend only",
        "input": {
            "prompt": "Create a backend service for managing user profiles",
            "name": "user-service",
            "include": {
                "contract": False,
                "backend": True,
                "frontend": False,
                "indexer": False,
            },
        },
        "expected": {
            "has_components": ["backend"],
            "missing_components": ["contract", "frontend", "indexer"],
        },
        "priority": "P1",
        "category": "partial",
    },

    # ===== Project Structure (P0) =====
    {
        "id": "dapp_structure_001",
        "name": "Structure: monorepo layout",
        "input": {
            "prompt": "Create a DeFi lending dApp",
            "name": "lending-protocol",
            "include": {
                "contract": True,
                "backend": True,
                "frontend": True,
            },
        },
        "expected": {
            "has_project_structure": True,
            "structure_contains": ["contracts", "backend", "frontend", "package.json"],
        },
        "priority": "P0",
        "category": "structure",
    },

    # ===== Configuration (P0) =====
    {
        "id": "dapp_config_001",
        "name": "Config: network configuration",
        "input": {
            "prompt": "Create a token bridge dApp for Arbitrum",
            "name": "bridge-dapp",
            "network": "arbitrum-sepolia",
        },
        "expected": {
            "has_root_files": True,
            "root_files_contain": ["NETWORK", "arbitrum"],
        },
        "priority": "P0",
        "category": "config",
    },
    {
        "id": "dapp_config_002",
        "name": "Config: framework selection",
        "input": {
            "prompt": "Create a gaming dApp",
            "name": "game-dapp",
            "backend_framework": "express",
            "wallet_kit": "rainbowkit",
            "ui_library": "daisyui",
        },
        "expected": {
            "has_components": ["backend", "frontend"],
        },
        "priority": "P1",
        "category": "config",
    },

    # ===== Integration Guide (P0) =====
    {
        "id": "dapp_guide_001",
        "name": "Guide: deployment instructions",
        "input": {
            "prompt": "Create a governance dApp for a DAO",
            "name": "dao-governance",
            "include": {
                "contract": True,
                "backend": True,
                "frontend": True,
            },
        },
        "expected": {
            "has_integration_guide": True,
            "guide_contains": ["deploy", "npm", "install"],
        },
        "priority": "P0",
        "category": "guide",
    },

    # ===== Contract Types (P1) =====
    {
        "id": "dapp_contract_001",
        "name": "Contract: ERC20 token dApp",
        "input": {
            "prompt": "Create a token distribution dApp",
            "name": "token-dist",
            "contract_type": "erc20",
        },
        "expected": {
            "has_components": ["contract"],
            "plan_has_keywords": ["token", "erc20"],
        },
        "priority": "P1",
        "category": "contract_type",
    },
    {
        "id": "dapp_contract_002",
        "name": "Contract: ERC721 NFT dApp",
        "input": {
            "prompt": "Create an NFT collection dApp",
            "name": "nft-collection",
            "contract_type": "erc721",
        },
        "expected": {
            "has_components": ["contract"],
            "plan_has_keywords": ["nft", "erc721"],
        },
        "priority": "P1",
        "category": "contract_type",
    },

    # ===== Error Handling (P0) =====
    {
        "id": "dapp_error_001",
        "name": "Error: empty prompt",
        "input": {
            "prompt": "",
            "name": "test-dapp",
        },
        "expected": {
            "should_error": True,
            "error_contains": "prompt",
        },
        "priority": "P0",
        "category": "error_handling",
    },

    # ===== Complex Scenarios (P1) =====
    {
        "id": "dapp_complex_001",
        "name": "Complex: full DEX with indexer",
        "input": {
            "prompt": "Create a decentralized exchange with liquidity pools, swapping, and LP tokens",
            "name": "dex-app",
            "include": {
                "contract": True,
                "backend": True,
                "frontend": True,
                "indexer": True,
            },
        },
        "expected": {
            "has_components": ["contract", "backend", "frontend", "indexer"],
            "has_integration_guide": True,
        },
        "priority": "P1",
        "category": "complex",
    },
]


class TestGenerateDapp:
    """Test suite for generate_dapp orchestration tool."""

    @pytest.fixture
    def tool(self):
        """Initialize the tool for testing."""
        from src.mcp.tools import GenerateDappTool
        return GenerateDappTool()

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GENERATE_DAPP_TEST_CASES if tc["priority"] == "P0"],
        ids=lambda tc: tc["id"],
    )
    def test_p0_cases(self, tool, test_case):
        """Test P0 (critical) test cases."""
        result = tool.execute(**test_case["input"])
        self._validate_result(result, test_case["expected"])

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GENERATE_DAPP_TEST_CASES if tc["priority"] == "P1"],
        ids=lambda tc: tc["id"],
    )
    def test_p1_cases(self, tool, test_case):
        """Test P1 (important) test cases."""
        result = tool.execute(**test_case["input"])
        self._validate_result(result, test_case["expected"])

    def _validate_result(self, result: dict, expected: dict):
        """Validate result against expected criteria."""
        # Check for expected errors
        if expected.get("should_error"):
            assert "error" in result, f"Expected error but got: {result}"
            if "error_contains" in expected:
                assert expected["error_contains"] in result["error"].lower()
            return

        # Should not have errors if not expected
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

        components = result.get("components", {})

        # Check for expected components
        if "has_components" in expected:
            for component in expected["has_components"]:
                assert component in components, f"Missing component: {component}"
                comp_data = components[component]
                if component != "plan":
                    assert "files" in comp_data or "path" in comp_data, \
                        f"Component {component} has no files"

        # Check for missing components
        if "missing_components" in expected:
            for component in expected["missing_components"]:
                assert component not in components or components[component] is None, \
                    f"Unexpected component present: {component}"

        # Check root files
        if expected.get("has_root_files"):
            root_files = components.get("root_files", [])
            assert len(root_files) > 0, "No root files generated"

            if "root_files_contain" in expected:
                all_content = "\n".join(f.get("content", "") for f in root_files)
                for keyword in expected["root_files_contain"]:
                    assert keyword.lower() in all_content.lower(), \
                        f"Root files missing keyword: {keyword}"

        # Check integration guide
        if expected.get("has_integration_guide"):
            guide = components.get("integration_guide", "")
            assert guide, "No integration guide generated"

            if "guide_contains" in expected:
                guide_lower = guide.lower()
                for keyword in expected["guide_contains"]:
                    assert keyword.lower() in guide_lower, \
                        f"Guide missing keyword: {keyword}"

        # Check project structure
        if expected.get("has_project_structure"):
            structure = result.get("project_structure", "")
            assert structure, "No project structure generated"

            if "structure_contains" in expected:
                structure_lower = structure.lower()
                for item in expected["structure_contains"]:
                    assert item.lower() in structure_lower, \
                        f"Structure missing: {item}"

        # Check plan keywords
        if "plan_has_keywords" in expected:
            plan = components.get("plan", {})
            plan_str = str(plan).lower()
            for keyword in expected["plan_has_keywords"]:
                assert keyword.lower() in plan_str, \
                    f"Plan missing keyword: {keyword}"


def analyze_dapp_quality(result: dict) -> dict:
    """Analyze generated dApp quality metrics."""
    components = result.get("components", {})

    # Count total files
    total_files = 0
    for comp_name, comp_data in components.items():
        if isinstance(comp_data, dict) and "files" in comp_data:
            total_files += len(comp_data["files"])

    return {
        "component_count": len([c for c in components if c not in ["plan", "root_files", "integration_guide"]]),
        "total_files": total_files,
        "has_contract": "contract" in components,
        "has_backend": "backend" in components,
        "has_frontend": "frontend" in components,
        "has_indexer": "indexer" in components,
        "has_integration_guide": bool(components.get("integration_guide")),
        "has_project_structure": bool(result.get("project_structure")),
        "project_name": result.get("name", ""),
    }


# Quick smoke test for development
def run_quick_test():
    """Run a quick smoke test for the generate_dapp tool."""
    from src.mcp.tools import GenerateDappTool

    tool = GenerateDappTool()
    result = tool.execute(
        prompt="Create a simple token staking dApp",
        name="quick-test",
        include={
            "contract": True,
            "backend": True,
            "frontend": True,
            "indexer": False,
        },
    )

    print("=== Quick Test Results ===")
    print(f"Name: {result.get('name')}")
    print(f"Components: {list(result.get('components', {}).keys())}")
    print(f"Warnings: {result.get('warnings', [])}")
    print(f"Structure:\n{result.get('project_structure', 'N/A')}")

    quality = analyze_dapp_quality(result)
    print(f"\nQuality Metrics: {quality}")

    return result


if __name__ == "__main__":
    run_quick_test()

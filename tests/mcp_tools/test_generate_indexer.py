"""
Test cases for generate_indexer MCP tool.

Tests The Graph subgraph generation for indexing smart contract events.
"""

import pytest
import re


GENERATE_INDEXER_TEST_CASES = [
    # ===== Basic Subgraph Generation (P0) =====
    {
        "id": "indexer_basic_001",
        "name": "Basic: ERC20 transfer events",
        "input": {
            "prompt": "Create a subgraph to index Transfer events from an ERC20 token",
            "contract_name": "Token",
            "network": "arbitrum-one",
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"specVersion",
                r"dataSources",
                r"Transfer",
            ],
            "file_types": ["yaml", "graphql", "ts"],
        },
        "priority": "P0",
        "category": "basic",
    },
    {
        "id": "indexer_basic_002",
        "name": "Basic: NFT ownership tracking",
        "input": {
            "prompt": "Create a subgraph to track NFT ownership and transfers",
            "contract_name": "NFT",
            "network": "arbitrum-sepolia",
            "entities": ["Token", "Owner", "Transfer"],
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"type\s+Token\s+@entity",
                r"type\s+Owner\s+@entity",
            ],
            "must_have_keywords": ["owner", "token"],
        },
        "priority": "P0",
        "category": "basic",
    },

    # ===== Schema Generation (P0) =====
    {
        "id": "indexer_schema_001",
        "name": "Schema: entity with relationships",
        "input": {
            "prompt": "Create a subgraph for a DEX with pools, swaps, and liquidity",
            "contract_name": "DEX",
            "entities": ["Pool", "Swap", "LiquidityPosition"],
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"@entity",
                r"ID!",
                r"BigInt|Bytes|String",
            ],
        },
        "priority": "P0",
        "category": "schema",
    },
    {
        "id": "indexer_schema_002",
        "name": "Schema: derived fields",
        "input": {
            "prompt": "Create entities for a marketplace with items and their sale history",
            "entities": ["Item", "Sale"],
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"type\s+\w+\s+@entity",
            ],
        },
        "priority": "P1",
        "category": "schema",
    },

    # ===== Mapping Generation (P0) =====
    {
        "id": "indexer_mapping_001",
        "name": "Mapping: event handlers",
        "input": {
            "prompt": "Create handlers for Mint and Burn events",
            "contract_name": "Token",
            "contract_abi": '[{"type":"event","name":"Mint","inputs":[{"name":"to","type":"address"},{"name":"amount","type":"uint256"}]},{"type":"event","name":"Burn","inputs":[{"name":"from","type":"address"},{"name":"amount","type":"uint256"}]}]',
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"export\s+function\s+handle",
                r"event\.params",
                r"\.save\(\)",
            ],
        },
        "priority": "P0",
        "category": "mapping",
    },
    {
        "id": "indexer_mapping_002",
        "name": "Mapping: entity loading and saving",
        "input": {
            "prompt": "Create a handler that loads or creates an entity and updates it",
            "contract_name": "Contract",
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"\.load\(|new\s+\w+\(",
                r"\.save\(\)",
            ],
        },
        "priority": "P0",
        "category": "mapping",
    },

    # ===== Network Configuration (P0) =====
    {
        "id": "indexer_network_001",
        "name": "Network: Arbitrum One config",
        "input": {
            "prompt": "Create a subgraph for Arbitrum One mainnet",
            "contract_name": "Contract",
            "contract_address": "0x1234567890123456789012345678901234567890",
            "network": "arbitrum-one",
            "start_block": 100000000,
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"network:\s*arbitrum-one",
                r"startBlock:\s*100000000",
                r"address:\s*\"0x1234",
            ],
        },
        "priority": "P0",
        "category": "network",
    },
    {
        "id": "indexer_network_002",
        "name": "Network: Arbitrum Sepolia config",
        "input": {
            "prompt": "Create a subgraph for Arbitrum Sepolia testnet",
            "network": "arbitrum-sepolia",
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"network:\s*arbitrum-sepolia",
            ],
        },
        "priority": "P0",
        "category": "network",
    },

    # ===== ABI Integration (P1) =====
    {
        "id": "indexer_abi_001",
        "name": "ABI: parse events from ABI",
        "input": {
            "prompt": "Create a subgraph based on this contract ABI",
            "contract_name": "MyContract",
            "contract_abi": '[{"type":"event","name":"Transfer","inputs":[{"name":"from","type":"address","indexed":true},{"name":"to","type":"address","indexed":true},{"name":"value","type":"uint256"}]}]',
        },
        "expected": {
            "has_files": True,
            "events_found": ["Transfer"],
        },
        "priority": "P1",
        "category": "abi",
    },

    # ===== Error Handling (P0) =====
    {
        "id": "indexer_error_001",
        "name": "Error: empty prompt",
        "input": {
            "prompt": "",
        },
        "expected": {
            "should_error": True,
            "error_contains": "prompt",
        },
        "priority": "P0",
        "category": "error_handling",
    },
    {
        "id": "indexer_error_002",
        "name": "Error: invalid network defaults",
        "input": {
            "prompt": "Create a subgraph",
            "network": "invalid-network",
        },
        "expected": {
            "should_warn": True,
            "has_files": True,
        },
        "priority": "P1",
        "category": "error_handling",
    },

    # ===== Complex Scenarios (P1) =====
    {
        "id": "indexer_complex_001",
        "name": "Complex: full AMM subgraph",
        "input": {
            "prompt": "Create a subgraph for an AMM DEX with pools, swaps, liquidity adds/removes, and daily statistics",
            "contract_name": "AMM",
            "entities": ["Pool", "Swap", "Mint", "Burn", "DailyPoolData"],
        },
        "expected": {
            "has_files": True,
            "must_have_keywords": ["pool", "swap"],
        },
        "priority": "P1",
        "category": "complex",
    },
]


class TestGenerateIndexer:
    """Test suite for generate_indexer tool."""

    @pytest.fixture
    def tool(self):
        """Initialize the tool for testing."""
        from src.mcp.tools import GenerateIndexerTool
        return GenerateIndexerTool()

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GENERATE_INDEXER_TEST_CASES if tc["priority"] == "P0"],
        ids=lambda tc: tc["id"],
    )
    def test_p0_cases(self, tool, test_case):
        """Test P0 (critical) test cases."""
        result = tool.execute(**test_case["input"])
        self._validate_result(result, test_case["expected"])

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GENERATE_INDEXER_TEST_CASES if tc["priority"] == "P1"],
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

        # Check for warnings
        if expected.get("should_warn"):
            assert "warnings" in result and len(result["warnings"]) > 0

        # Check files were generated
        if expected.get("has_files"):
            files = result.get("files", [])
            assert len(files) > 0, "No files generated"

            # Combine all file contents for pattern matching
            all_content = "\n".join(f.get("content", "") for f in files)
            all_paths = [f.get("path", "") for f in files]

            # Check file types
            if "file_types" in expected:
                for file_type in expected["file_types"]:
                    has_type = any(p.endswith(f".{file_type}") for p in all_paths)
                    assert has_type, f"Missing file type: .{file_type}"

            # Check must-have patterns
            if "must_have_patterns" in expected:
                for pattern in expected["must_have_patterns"]:
                    assert re.search(pattern, all_content, re.IGNORECASE), \
                        f"Missing pattern: {pattern}"

            # Check must-have keywords
            if "must_have_keywords" in expected:
                content_lower = all_content.lower()
                for keyword in expected["must_have_keywords"]:
                    assert keyword.lower() in content_lower, \
                        f"Missing keyword: {keyword}"

        # Check events found
        if "events_found" in expected:
            events = result.get("events_found", [])
            for event in expected["events_found"]:
                assert event in events, f"Event not found: {event}"


def analyze_indexer_quality(result: dict) -> dict:
    """Analyze generated indexer code quality metrics."""
    files = result.get("files", [])
    all_content = "\n".join(f.get("content", "") for f in files)

    return {
        "file_count": len(files),
        "has_manifest": any("subgraph.yaml" in f.get("path", "") for f in files),
        "has_schema": any("schema.graphql" in f.get("path", "") for f in files),
        "has_mapping": any("mapping.ts" in f.get("path", "") for f in files),
        "entity_count": len(re.findall(r"type\s+\w+\s+@entity", all_content)),
        "handler_count": len(re.findall(r"export\s+function\s+handle\w+", all_content)),
        "has_save_calls": bool(re.search(r"\.save\(\)", all_content)),
        "has_load_calls": bool(re.search(r"\.load\(", all_content)),
        "uses_bigint": bool(re.search(r"BigInt", all_content)),
    }

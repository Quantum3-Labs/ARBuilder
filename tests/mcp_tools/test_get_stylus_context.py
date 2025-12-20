"""
Test cases for get_stylus_context MCP tool.

Tests retrieval quality, filtering, and response format.
"""

import pytest
from typing import Optional


# Test case definitions
GET_CONTEXT_TEST_CASES = [
    # ===== Basic Keyword Search (P0) =====
    {
        "id": "ctx_basic_001",
        "name": "Basic keyword: sol_storage macro",
        "input": {
            "query": "sol_storage macro",
            "n_results": 5,
        },
        "expected": {
            "min_results": 1,
            "must_contain_keywords": ["sol_storage", "macro"],
            "content_type": "code",
            "relevance_threshold": 0.5,
        },
        "priority": "P0",
        "category": "basic_search",
    },
    {
        "id": "ctx_basic_002",
        "name": "Basic keyword: entrypoint",
        "input": {
            "query": "#[entrypoint] attribute",
            "n_results": 5,
        },
        "expected": {
            "min_results": 1,
            "must_contain_keywords": ["entrypoint"],
            "relevance_threshold": 0.5,
        },
        "priority": "P0",
        "category": "basic_search",
    },
    {
        "id": "ctx_basic_003",
        "name": "Basic keyword: StorageVec",
        "input": {
            "query": "StorageVec usage",
            "n_results": 5,
        },
        "expected": {
            "min_results": 1,
            "must_contain_keywords": ["StorageVec", "storage"],
            "relevance_threshold": 0.5,
        },
        "priority": "P0",
        "category": "basic_search",
    },

    # ===== Semantic Search (P0) =====
    {
        "id": "ctx_semantic_001",
        "name": "Semantic: token implementation",
        "input": {
            "query": "How to create a fungible token",
            "n_results": 5,
        },
        "expected": {
            "min_results": 1,
            "should_contain_keywords": ["erc20", "token", "transfer", "balance"],
            "relevance_threshold": 0.4,
        },
        "priority": "P0",
        "category": "semantic_search",
    },
    {
        "id": "ctx_semantic_002",
        "name": "Semantic: state persistence",
        "input": {
            "query": "How to persist data between contract calls",
            "n_results": 5,
        },
        "expected": {
            "min_results": 1,
            "should_contain_keywords": ["storage", "state", "persist"],
            "relevance_threshold": 0.4,
        },
        "priority": "P0",
        "category": "semantic_search",
    },
    {
        "id": "ctx_semantic_003",
        "name": "Semantic: gas efficiency",
        "input": {
            "query": "Making contracts more gas efficient",
            "n_results": 5,
        },
        "expected": {
            "min_results": 1,
            "should_contain_keywords": ["gas", "efficient", "wasm", "optimize"],
            "relevance_threshold": 0.3,
        },
        "priority": "P0",
        "category": "semantic_search",
    },

    # ===== Code Snippet Retrieval (P0) =====
    {
        "id": "ctx_code_001",
        "name": "Code: ERC20 implementation",
        "input": {
            "query": "ERC20 token contract Stylus",
            "n_results": 5,
            "content_type": "code",
        },
        "expected": {
            "min_results": 1,
            "must_contain_keywords": ["fn", "transfer"],
            "should_contain_patterns": [r"pub\s+fn", r"impl\s+"],
            "content_type": "code",
            "relevance_threshold": 0.5,
        },
        "priority": "P0",
        "category": "code_retrieval",
    },
    {
        "id": "ctx_code_002",
        "name": "Code: contract entrypoint",
        "input": {
            "query": "Stylus contract main entrypoint example",
            "n_results": 5,
            "content_type": "code",
        },
        "expected": {
            "min_results": 1,
            "should_contain_patterns": [r"#\[entrypoint\]", r"pub\s+struct"],
            "content_type": "code",
            "relevance_threshold": 0.5,
        },
        "priority": "P0",
        "category": "code_retrieval",
    },
    {
        "id": "ctx_code_003",
        "name": "Code: storage mapping",
        "input": {
            "query": "StorageMap address to uint256",
            "n_results": 5,
            "content_type": "code",
        },
        "expected": {
            "min_results": 1,
            "must_contain_keywords": ["StorageMap"],
            "content_type": "code",
            "relevance_threshold": 0.5,
        },
        "priority": "P0",
        "category": "code_retrieval",
    },

    # ===== Documentation Retrieval (P0) =====
    {
        "id": "ctx_docs_001",
        "name": "Docs: Stylus overview",
        "input": {
            "query": "What is Stylus and how does it work",
            "n_results": 5,
            "content_type": "docs",
        },
        "expected": {
            "min_results": 1,
            "should_contain_keywords": ["stylus", "arbitrum", "wasm", "rust"],
            "content_type": "docs",
            "relevance_threshold": 0.4,
        },
        "priority": "P0",
        "category": "docs_retrieval",
    },
    {
        "id": "ctx_docs_002",
        "name": "Docs: deployment guide",
        "input": {
            "query": "How to deploy a Stylus contract to testnet",
            "n_results": 5,
            "content_type": "docs",
        },
        "expected": {
            "min_results": 1,
            "should_contain_keywords": ["deploy", "testnet", "cargo"],
            "content_type": "docs",
            "relevance_threshold": 0.4,
        },
        "priority": "P0",
        "category": "docs_retrieval",
    },

    # ===== Filtering (P1) =====
    {
        "id": "ctx_filter_001",
        "name": "Filter: code only",
        "input": {
            "query": "transfer function",
            "n_results": 10,
            "content_type": "code",
        },
        "expected": {
            "min_results": 1,
            "all_results_type": "code",
        },
        "priority": "P1",
        "category": "filtering",
    },
    {
        "id": "ctx_filter_002",
        "name": "Filter: docs only",
        "input": {
            "query": "Stylus SDK features",
            "n_results": 10,
            "content_type": "docs",
        },
        "expected": {
            "min_results": 1,
            "all_results_type": "docs",
        },
        "priority": "P1",
        "category": "filtering",
    },

    # ===== Reranking (P1) =====
    {
        "id": "ctx_rerank_001",
        "name": "Reranking: improves relevance",
        "input": {
            "query": "OpenZeppelin ERC20 implementation in Stylus",
            "n_results": 5,
            "rerank": True,
        },
        "expected": {
            "min_results": 1,
            "top_result_keywords": ["openzeppelin", "erc20"],
            "relevance_threshold": 0.6,
        },
        "priority": "P1",
        "category": "reranking",
    },
    {
        "id": "ctx_rerank_002",
        "name": "Reranking: specific function",
        "input": {
            "query": "balance_of function implementation",
            "n_results": 5,
            "rerank": True,
        },
        "expected": {
            "min_results": 1,
            "top_result_keywords": ["balance"],
            "should_contain_patterns": [r"balance(_of)?"],
            "relevance_threshold": 0.6,
        },
        "priority": "P1",
        "category": "reranking",
    },

    # ===== Edge Cases =====
    {
        "id": "ctx_edge_001",
        "name": "Edge: empty query handling",
        "input": {
            "query": "",
            "n_results": 5,
        },
        "expected": {
            "should_error": True,
            "error_contains": "query",
        },
        "priority": "P0",
        "category": "edge_cases",
    },
    {
        "id": "ctx_edge_002",
        "name": "Edge: very long query",
        "input": {
            "query": "How do I create a Stylus smart contract that implements an ERC20 token with custom transfer logic that checks if the sender has sufficient balance and also emits events for tracking " * 10,
            "n_results": 5,
        },
        "expected": {
            "min_results": 1,
            "should_contain_keywords": ["erc20", "token", "transfer"],
        },
        "priority": "P1",
        "category": "edge_cases",
    },
    {
        "id": "ctx_edge_003",
        "name": "Edge: n_results boundary (max)",
        "input": {
            "query": "Stylus contracts",
            "n_results": 20,
        },
        "expected": {
            "max_results": 20,
        },
        "priority": "P1",
        "category": "edge_cases",
    },
    {
        "id": "ctx_edge_004",
        "name": "Edge: no matching results",
        "input": {
            "query": "xyznonexistent12345",
            "n_results": 5,
        },
        "expected": {
            "min_results": 0,
            "should_return_empty_or_low_relevance": True,
        },
        "priority": "P1",
        "category": "edge_cases",
    },
]


class TestGetStylusContext:
    """Test suite for get_stylus_context tool."""

    @pytest.fixture
    def tool(self):
        """Initialize the tool for testing."""
        # Placeholder - will be implemented with actual tool
        from src.mcp.tools import GetStylusContextTool
        return GetStylusContextTool()

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GET_CONTEXT_TEST_CASES if tc["priority"] == "P0"],
        ids=lambda tc: tc["id"],
    )
    def test_p0_cases(self, tool, test_case):
        """Test P0 (critical) test cases."""
        result = tool.execute(**test_case["input"])
        self._validate_result(result, test_case["expected"])

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GET_CONTEXT_TEST_CASES if tc["priority"] == "P1"],
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
            assert "error" in result
            if "error_contains" in expected:
                assert expected["error_contains"] in result["error"].lower()
            return

        # Check minimum results
        if "min_results" in expected:
            assert len(result.get("contexts", [])) >= expected["min_results"]

        # Check maximum results
        if "max_results" in expected:
            assert len(result.get("contexts", [])) <= expected["max_results"]

        # Check must-contain keywords (all must be present)
        if "must_contain_keywords" in expected:
            all_content = " ".join(
                ctx["content"].lower() for ctx in result.get("contexts", [])
            )
            for keyword in expected["must_contain_keywords"]:
                assert keyword.lower() in all_content, f"Missing keyword: {keyword}"

        # Check should-contain keywords (at least one must be present)
        if "should_contain_keywords" in expected:
            all_content = " ".join(
                ctx["content"].lower() for ctx in result.get("contexts", [])
            )
            found = any(
                kw.lower() in all_content
                for kw in expected["should_contain_keywords"]
            )
            assert found, f"None of keywords found: {expected['should_contain_keywords']}"

        # Check content type filtering
        if "all_results_type" in expected:
            for ctx in result.get("contexts", []):
                assert ctx["type"] == expected["all_results_type"]

        # Check relevance threshold
        if "relevance_threshold" in expected and result.get("contexts"):
            top_score = result["contexts"][0].get("relevance_score", 0)
            assert top_score >= expected["relevance_threshold"]


# Benchmark metrics collection
def collect_benchmark_metrics(test_results: list[dict]) -> dict:
    """Collect and aggregate benchmark metrics from test results."""
    metrics = {
        "total_tests": len(test_results),
        "passed": sum(1 for r in test_results if r["passed"]),
        "failed": sum(1 for r in test_results if not r["passed"]),
        "by_category": {},
        "by_priority": {},
        "avg_latency_ms": 0,
        "recall_at_5": 0,
    }

    # Group by category
    for result in test_results:
        cat = result["category"]
        if cat not in metrics["by_category"]:
            metrics["by_category"][cat] = {"passed": 0, "failed": 0}
        if result["passed"]:
            metrics["by_category"][cat]["passed"] += 1
        else:
            metrics["by_category"][cat]["failed"] += 1

    # Group by priority
    for result in test_results:
        prio = result["priority"]
        if prio not in metrics["by_priority"]:
            metrics["by_priority"][prio] = {"passed": 0, "failed": 0}
        if result["passed"]:
            metrics["by_priority"][prio]["passed"] += 1
        else:
            metrics["by_priority"][prio]["failed"] += 1

    # Calculate averages
    latencies = [r["latency_ms"] for r in test_results if "latency_ms" in r]
    if latencies:
        metrics["avg_latency_ms"] = sum(latencies) / len(latencies)

    return metrics

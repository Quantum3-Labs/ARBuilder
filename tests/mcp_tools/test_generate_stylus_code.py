"""
Test cases for generate_stylus_code MCP tool.

Tests code generation quality, syntax validity, and pattern correctness.
"""

import pytest
import re
from typing import Optional


# Test case definitions
GENERATE_CODE_TEST_CASES = [
    # ===== Basic Contract Generation (P0) =====
    {
        "id": "gen_basic_001",
        "name": "Basic: simple counter contract",
        "input": {
            "prompt": "Create a simple counter contract with increment and get_count functions",
        },
        "expected": {
            "must_have_patterns": [
                r"#\[entrypoint\]",
                r"sol_storage!",
                r"pub\s+fn\s+increment",
                r"pub\s+fn\s+get_count",
            ],
            "must_have_keywords": ["struct", "impl"],
            "syntax_valid": True,
        },
        "priority": "P0",
        "category": "basic_generation",
    },
    {
        "id": "gen_basic_002",
        "name": "Basic: hello world contract",
        "input": {
            "prompt": "Create a basic Stylus hello world contract that returns a greeting",
        },
        "expected": {
            "must_have_patterns": [
                r"#\[entrypoint\]",
                r"sol_storage!",
            ],
            "must_have_keywords": ["fn", "String"],
            "syntax_valid": True,
        },
        "priority": "P0",
        "category": "basic_generation",
    },
    {
        "id": "gen_basic_003",
        "name": "Basic: storage contract",
        "input": {
            "prompt": "Create a contract that stores and retrieves a single uint256 value",
        },
        "expected": {
            "must_have_patterns": [
                r"sol_storage!",
                r"StorageU256|U256",
                r"pub\s+fn\s+set",
                r"pub\s+fn\s+get",
            ],
            "syntax_valid": True,
        },
        "priority": "P0",
        "category": "basic_generation",
    },

    # ===== ERC20 Implementation (P0) =====
    {
        "id": "gen_erc20_001",
        "name": "ERC20: basic token",
        "input": {
            "prompt": "Create an ERC20 token contract with transfer, balanceOf, and totalSupply",
            "contract_type": "erc20",
        },
        "expected": {
            "must_have_patterns": [
                r"fn\s+transfer",
                r"fn\s+balance_of|balanceOf",
                r"fn\s+total_supply|totalSupply",
                r"StorageMap",
            ],
            "must_have_keywords": ["address", "u256", "mapping"],
            "syntax_valid": True,
        },
        "priority": "P0",
        "category": "erc20",
    },
    {
        "id": "gen_erc20_002",
        "name": "ERC20: with approve and transferFrom",
        "input": {
            "prompt": "Create an ERC20 token with approve and transferFrom functions for allowances",
            "contract_type": "erc20",
        },
        "expected": {
            "must_have_patterns": [
                r"fn\s+approve",
                r"fn\s+transfer_from|transferFrom",
                r"allowance|Allowance",
            ],
            "syntax_valid": True,
        },
        "priority": "P0",
        "category": "erc20",
    },

    # ===== Storage Patterns (P0) =====
    {
        "id": "gen_storage_001",
        "name": "Storage: vector usage",
        "input": {
            "prompt": "Create a contract that manages a list of addresses using StorageVec",
        },
        "expected": {
            "must_have_patterns": [
                r"StorageVec",
                r"sol_storage!",
            ],
            "must_have_keywords": ["push", "get", "len"],
            "syntax_valid": True,
        },
        "priority": "P0",
        "category": "storage",
    },
    {
        "id": "gen_storage_002",
        "name": "Storage: nested mapping",
        "input": {
            "prompt": "Create a contract with a nested mapping from address to address to uint256",
        },
        "expected": {
            "must_have_patterns": [
                r"StorageMap.*StorageMap|mapping.*mapping",
            ],
            "syntax_valid": True,
        },
        "priority": "P0",
        "category": "storage",
    },

    # ===== Error Handling (P0) =====
    {
        "id": "gen_error_001",
        "name": "Error: custom errors",
        "input": {
            "prompt": "Create a contract with custom error types for insufficient balance and unauthorized access",
        },
        "expected": {
            "should_have_patterns": [
                r"enum\s+\w*Error|Error\s*{",
                r"Result<|Err\(",
            ],
            "syntax_valid": True,
        },
        "priority": "P0",
        "category": "error_handling",
    },
    {
        "id": "gen_error_002",
        "name": "Error: require-like checks",
        "input": {
            "prompt": "Create a function that checks if caller has sufficient balance and reverts if not",
        },
        "expected": {
            "should_have_patterns": [
                r"if\s+.*<|assert!|require!",
                r"return\s+Err|panic!",
            ],
            "syntax_valid": True,
        },
        "priority": "P0",
        "category": "error_handling",
    },

    # ===== ERC721 Implementation (P1) =====
    {
        "id": "gen_erc721_001",
        "name": "ERC721: basic NFT",
        "input": {
            "prompt": "Create a basic ERC721 NFT contract with mint and transfer functions",
            "contract_type": "erc721",
        },
        "expected": {
            "must_have_patterns": [
                r"fn\s+mint",
                r"fn\s+transfer|transfer_from",
                r"owner_of|ownerOf",
            ],
            "must_have_keywords": ["token_id", "address"],
            "syntax_valid": True,
        },
        "priority": "P1",
        "category": "erc721",
    },

    # ===== Events/Logging (P1) =====
    {
        "id": "gen_events_001",
        "name": "Events: transfer event",
        "input": {
            "prompt": "Create an ERC20 token that emits Transfer events on every transfer",
        },
        "expected": {
            "should_have_patterns": [
                r"evm::log|emit|event|Event",
                r"Transfer",
            ],
            "syntax_valid": True,
        },
        "priority": "P1",
        "category": "events",
    },

    # ===== Access Control (P1) =====
    {
        "id": "gen_access_001",
        "name": "Access: owner only",
        "input": {
            "prompt": "Create a contract with an owner and a function that can only be called by the owner",
        },
        "expected": {
            "must_have_patterns": [
                r"owner|Owner",
                r"msg::sender|caller",
            ],
            "should_have_patterns": [
                r"only_owner|onlyOwner|require.*owner",
            ],
            "syntax_valid": True,
        },
        "priority": "P1",
        "category": "access_control",
    },
    {
        "id": "gen_access_002",
        "name": "Access: role-based",
        "input": {
            "prompt": "Create a contract with role-based access control (admin and user roles)",
        },
        "expected": {
            "must_have_patterns": [
                r"role|Role|ADMIN|admin",
            ],
            "should_have_patterns": [
                r"has_role|hasRole|grant|revoke",
            ],
            "syntax_valid": True,
        },
        "priority": "P1",
        "category": "access_control",
    },

    # ===== With Context Query (P1) =====
    {
        "id": "gen_context_001",
        "name": "Context: use retrieved examples",
        "input": {
            "prompt": "Create an ERC20 token similar to OpenZeppelin implementation",
            "context_query": "OpenZeppelin ERC20 Stylus implementation",
        },
        "expected": {
            "must_have_keywords": ["fn", "transfer"],
            "context_used": True,
            "syntax_valid": True,
        },
        "priority": "P1",
        "category": "context_usage",
    },

    # ===== Temperature Control =====
    {
        "id": "gen_temp_001",
        "name": "Temperature: low (deterministic)",
        "input": {
            "prompt": "Create a simple getter function that returns a stored value",
            "temperature": 0.1,
        },
        "expected": {
            "syntax_valid": True,
            "deterministic": True,  # Running twice should give similar results
        },
        "priority": "P1",
        "category": "temperature",
    },

    # ===== Edge Cases =====
    {
        "id": "gen_edge_001",
        "name": "Edge: empty prompt",
        "input": {
            "prompt": "",
        },
        "expected": {
            "should_error": True,
            "error_contains": "prompt",
        },
        "priority": "P0",
        "category": "edge_cases",
    },
    {
        "id": "gen_edge_002",
        "name": "Edge: non-Stylus request",
        "input": {
            "prompt": "Create a Python web server",
        },
        "expected": {
            "should_warn": True,
            "warn_contains": "stylus",
        },
        "priority": "P1",
        "category": "edge_cases",
    },
    {
        "id": "gen_edge_003",
        "name": "Edge: very complex request",
        "input": {
            "prompt": "Create a full DEX with AMM, liquidity pools, swapping, LP tokens, and fee distribution",
        },
        "expected": {
            "syntax_valid": True,
            "should_have_structure": True,  # Should at least provide basic structure
        },
        "priority": "P1",
        "category": "edge_cases",
    },
]


class TestGenerateStylusCode:
    """Test suite for generate_stylus_code tool."""

    @pytest.fixture
    def tool(self):
        """Initialize the tool for testing."""
        from src.mcp.tools import GenerateStylusCodeTool
        return GenerateStylusCodeTool()

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GENERATE_CODE_TEST_CASES if tc["priority"] == "P0"],
        ids=lambda tc: tc["id"],
    )
    def test_p0_cases(self, tool, test_case):
        """Test P0 (critical) test cases."""
        result = tool.execute(**test_case["input"])
        self._validate_result(result, test_case["expected"])

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GENERATE_CODE_TEST_CASES if tc["priority"] == "P1"],
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

        # Check for warnings
        if expected.get("should_warn"):
            assert "warnings" in result and len(result["warnings"]) > 0
            if "warn_contains" in expected:
                warn_text = " ".join(result["warnings"]).lower()
                assert expected["warn_contains"] in warn_text

        code = result.get("code", "")

        # Check syntax validity
        if expected.get("syntax_valid"):
            # Basic Rust syntax checks
            assert self._is_valid_rust_syntax(code), "Invalid Rust syntax"

        # Check must-have patterns (all must match)
        if "must_have_patterns" in expected:
            for pattern in expected["must_have_patterns"]:
                assert re.search(pattern, code, re.IGNORECASE), \
                    f"Missing pattern: {pattern}"

        # Check should-have patterns (at least one must match)
        if "should_have_patterns" in expected:
            found = any(
                re.search(p, code, re.IGNORECASE)
                for p in expected["should_have_patterns"]
            )
            assert found, f"None of patterns found: {expected['should_have_patterns']}"

        # Check must-have keywords
        if "must_have_keywords" in expected:
            code_lower = code.lower()
            for keyword in expected["must_have_keywords"]:
                assert keyword.lower() in code_lower, f"Missing keyword: {keyword}"

        # Check context usage
        if expected.get("context_used"):
            assert "context_used" in result and len(result["context_used"]) > 0

    def _is_valid_rust_syntax(self, code: str) -> bool:
        """
        Basic Rust syntax validation.

        For comprehensive validation, this should invoke rustfmt or cargo check.
        Here we do basic structural checks.
        """
        if not code.strip():
            return False

        # Check for balanced braces
        if code.count("{") != code.count("}"):
            return False

        # Check for balanced parentheses
        if code.count("(") != code.count(")"):
            return False

        # Check for common Stylus patterns
        has_struct = "struct" in code.lower()
        has_fn = "fn " in code
        has_impl = "impl" in code.lower()

        # Should have at least struct and fn
        return has_struct or has_fn


# Code quality metrics
def analyze_code_quality(code: str) -> dict:
    """Analyze generated code quality metrics."""
    return {
        "line_count": len(code.split("\n")),
        "has_entrypoint": bool(re.search(r"#\[entrypoint\]", code)),
        "has_sol_storage": bool(re.search(r"sol_storage!", code)),
        "has_error_handling": bool(re.search(r"Result<|Err\(|panic!", code)),
        "has_documentation": bool(re.search(r"///|/\*\*", code)),
        "has_events": bool(re.search(r"evm::log|emit|Event", code)),
        "function_count": len(re.findall(r"fn\s+\w+", code)),
        "uses_storage_types": bool(re.search(
            r"StorageVec|StorageMap|StorageU256|StorageAddress", code
        )),
    }

"""
Test cases for generate_tests MCP tool.

Tests test generation quality, coverage, and validity.
"""

import pytest
import re
from typing import Optional


# Sample contract code for testing
SAMPLE_COUNTER_CONTRACT = """
use stylus_sdk::prelude::*;
use stylus_sdk::alloy_primitives::U256;

sol_storage! {
    #[entrypoint]
    pub struct Counter {
        uint256 count;
    }
}

#[external]
impl Counter {
    pub fn get_count(&self) -> U256 {
        self.count.get()
    }

    pub fn increment(&mut self) {
        let current = self.count.get();
        self.count.set(current + U256::from(1));
    }

    pub fn decrement(&mut self) {
        let current = self.count.get();
        if current > U256::ZERO {
            self.count.set(current - U256::from(1));
        }
    }

    pub fn set_count(&mut self, value: U256) {
        self.count.set(value);
    }
}
"""

SAMPLE_ERC20_CONTRACT = """
use stylus_sdk::prelude::*;
use stylus_sdk::alloy_primitives::{Address, U256};

sol_storage! {
    #[entrypoint]
    pub struct Token {
        mapping(address => uint256) balances;
        mapping(address => mapping(address => uint256)) allowances;
        uint256 total_supply;
        string name;
        string symbol;
    }
}

#[external]
impl Token {
    pub fn balance_of(&self, account: Address) -> U256 {
        self.balances.get(account)
    }

    pub fn transfer(&mut self, to: Address, amount: U256) -> bool {
        let sender = msg::sender();
        let sender_balance = self.balances.get(sender);
        if sender_balance < amount {
            return false;
        }
        self.balances.insert(sender, sender_balance - amount);
        let to_balance = self.balances.get(to);
        self.balances.insert(to, to_balance + amount);
        true
    }

    pub fn approve(&mut self, spender: Address, amount: U256) -> bool {
        let sender = msg::sender();
        self.allowances.setter(sender).insert(spender, amount);
        true
    }

    pub fn transfer_from(&mut self, from: Address, to: Address, amount: U256) -> bool {
        let sender = msg::sender();
        let allowance = self.allowances.getter(from).get(sender);
        if allowance < amount {
            return false;
        }
        let from_balance = self.balances.get(from);
        if from_balance < amount {
            return false;
        }
        self.allowances.setter(from).insert(sender, allowance - amount);
        self.balances.insert(from, from_balance - amount);
        let to_balance = self.balances.get(to);
        self.balances.insert(to, to_balance + amount);
        true
    }
}
"""


# Test case definitions
GENERATE_TESTS_TEST_CASES = [
    # ===== Unit Test Generation (P0) =====
    {
        "id": "test_unit_001",
        "name": "Unit: simple counter tests",
        "input": {
            "contract_code": SAMPLE_COUNTER_CONTRACT,
            "test_types": ["unit"],
        },
        "expected": {
            "must_have_patterns": [
                r"#\[test\]",
                r"fn\s+test_",
            ],
            "should_test_functions": ["get_count", "increment", "decrement", "set_count"],
            "min_test_count": 3,
            "syntax_valid": True,
        },
        "priority": "P0",
        "category": "unit_tests",
    },
    {
        "id": "test_unit_002",
        "name": "Unit: ERC20 basic tests",
        "input": {
            "contract_code": SAMPLE_ERC20_CONTRACT,
            "test_types": ["unit"],
        },
        "expected": {
            "must_have_patterns": [
                r"#\[test\]",
                r"fn\s+test_",
            ],
            "should_test_functions": ["balance_of", "transfer"],
            "min_test_count": 4,
            "syntax_valid": True,
        },
        "priority": "P0",
        "category": "unit_tests",
    },

    # ===== Happy Path Tests (P0) =====
    {
        "id": "test_happy_001",
        "name": "Happy path: counter operations",
        "input": {
            "contract_code": SAMPLE_COUNTER_CONTRACT,
            "test_types": ["unit"],
        },
        "expected": {
            "should_have_happy_path_tests": True,
            "happy_path_scenarios": [
                "initial value is zero",
                "increment increases count",
                "can set specific value",
            ],
        },
        "priority": "P0",
        "category": "happy_path",
    },
    {
        "id": "test_happy_002",
        "name": "Happy path: successful transfer",
        "input": {
            "contract_code": SAMPLE_ERC20_CONTRACT,
            "test_types": ["unit"],
            "coverage_focus": ["transfer"],
        },
        "expected": {
            "should_test_functions": ["transfer"],
            "should_have_assertion_patterns": [
                r"assert",
                r"balance",
            ],
        },
        "priority": "P0",
        "category": "happy_path",
    },

    # ===== Error Case Tests (P0) =====
    {
        "id": "test_error_001",
        "name": "Error: counter underflow",
        "input": {
            "contract_code": SAMPLE_COUNTER_CONTRACT,
            "test_types": ["unit"],
        },
        "expected": {
            "should_test_error_cases": True,
            "error_scenarios": ["decrement when zero"],
        },
        "priority": "P0",
        "category": "error_cases",
    },
    {
        "id": "test_error_002",
        "name": "Error: insufficient balance transfer",
        "input": {
            "contract_code": SAMPLE_ERC20_CONTRACT,
            "test_types": ["unit"],
        },
        "expected": {
            "should_test_error_cases": True,
            "error_scenarios": ["transfer more than balance"],
            "should_have_patterns": [
                r"insufficient|balance|fail|false",
            ],
        },
        "priority": "P0",
        "category": "error_cases",
    },
    {
        "id": "test_error_003",
        "name": "Error: unauthorized transfer_from",
        "input": {
            "contract_code": SAMPLE_ERC20_CONTRACT,
            "test_types": ["unit"],
            "coverage_focus": ["transfer_from"],
        },
        "expected": {
            "should_test_error_cases": True,
            "error_scenarios": ["transfer without approval"],
        },
        "priority": "P0",
        "category": "error_cases",
    },

    # ===== Edge Case Tests (P1) =====
    {
        "id": "test_edge_001",
        "name": "Edge: zero value operations",
        "input": {
            "contract_code": SAMPLE_ERC20_CONTRACT,
            "test_types": ["unit"],
        },
        "expected": {
            "should_test_edge_cases": True,
            "edge_scenarios": ["transfer zero", "zero balance"],
        },
        "priority": "P1",
        "category": "edge_cases",
    },
    {
        "id": "test_edge_002",
        "name": "Edge: max value operations",
        "input": {
            "contract_code": SAMPLE_COUNTER_CONTRACT,
            "test_types": ["unit"],
        },
        "expected": {
            "should_test_edge_cases": True,
            "edge_scenarios": ["large numbers", "boundary"],
        },
        "priority": "P1",
        "category": "edge_cases",
    },
    {
        "id": "test_edge_003",
        "name": "Edge: self transfer",
        "input": {
            "contract_code": SAMPLE_ERC20_CONTRACT,
            "test_types": ["unit"],
            "coverage_focus": ["transfer"],
        },
        "expected": {
            "should_consider_scenario": "transfer to self",
        },
        "priority": "P1",
        "category": "edge_cases",
    },

    # ===== Test Framework Selection =====
    {
        "id": "test_framework_001",
        "name": "Framework: Rust native tests",
        "input": {
            "contract_code": SAMPLE_COUNTER_CONTRACT,
            "test_framework": "rust_native",
        },
        "expected": {
            "must_have_patterns": [
                r"#\[cfg\(test\)\]",
                r"mod\s+tests",
                r"#\[test\]",
            ],
            "must_not_have_patterns": [
                r"forge|foundry|hardhat",
            ],
        },
        "priority": "P0",
        "category": "framework",
    },
    {
        "id": "test_framework_002",
        "name": "Framework: Foundry tests",
        "input": {
            "contract_code": SAMPLE_COUNTER_CONTRACT,
            "test_framework": "foundry",
        },
        "expected": {
            "should_have_patterns": [
                r"test|Test",
                r"function|contract",
            ],
            "language": "solidity",
        },
        "priority": "P1",
        "category": "framework",
    },

    # ===== Coverage Focus =====
    {
        "id": "test_focus_001",
        "name": "Focus: specific function only",
        "input": {
            "contract_code": SAMPLE_ERC20_CONTRACT,
            "test_types": ["unit"],
            "coverage_focus": ["approve"],
        },
        "expected": {
            "must_test_functions": ["approve"],
            "primary_focus": "approve",
        },
        "priority": "P1",
        "category": "coverage_focus",
    },
    {
        "id": "test_focus_002",
        "name": "Focus: multiple specific functions",
        "input": {
            "contract_code": SAMPLE_ERC20_CONTRACT,
            "test_types": ["unit"],
            "coverage_focus": ["transfer", "transfer_from"],
        },
        "expected": {
            "must_test_functions": ["transfer", "transfer_from"],
        },
        "priority": "P1",
        "category": "coverage_focus",
    },

    # ===== Fuzz Tests (P2) =====
    {
        "id": "test_fuzz_001",
        "name": "Fuzz: property-based tests",
        "input": {
            "contract_code": SAMPLE_ERC20_CONTRACT,
            "test_types": ["fuzz"],
        },
        "expected": {
            "should_have_patterns": [
                r"proptest|quickcheck|fuzz|arbitrary",
            ],
            "should_test_properties": [
                "total supply conservation",
                "balance consistency",
            ],
        },
        "priority": "P2",
        "category": "fuzz_tests",
    },

    # ===== Test Summary =====
    {
        "id": "test_summary_001",
        "name": "Summary: complete test summary",
        "input": {
            "contract_code": SAMPLE_COUNTER_CONTRACT,
            "test_types": ["unit"],
        },
        "expected": {
            "should_have_summary": True,
            "summary_includes": ["total_tests", "functions_covered"],
        },
        "priority": "P0",
        "category": "summary",
    },

    # ===== Setup Instructions =====
    {
        "id": "test_setup_001",
        "name": "Setup: provide run instructions",
        "input": {
            "contract_code": SAMPLE_COUNTER_CONTRACT,
            "test_framework": "rust_native",
        },
        "expected": {
            "should_have_setup_instructions": True,
            "setup_mentions": ["cargo", "test"],
        },
        "priority": "P1",
        "category": "setup",
    },

    # ===== Edge Cases =====
    {
        "id": "test_input_edge_001",
        "name": "Input Edge: empty contract",
        "input": {
            "contract_code": "",
        },
        "expected": {
            "should_error": True,
            "error_contains": "contract",
        },
        "priority": "P0",
        "category": "input_edge",
    },
    {
        "id": "test_input_edge_002",
        "name": "Input Edge: invalid contract syntax",
        "input": {
            "contract_code": "this is not valid rust code {{{",
        },
        "expected": {
            "should_error_or_warn": True,
        },
        "priority": "P1",
        "category": "input_edge",
    },
    {
        "id": "test_input_edge_003",
        "name": "Input Edge: contract with no functions",
        "input": {
            "contract_code": """
sol_storage! {
    #[entrypoint]
    pub struct Empty {
        uint256 value;
    }
}
""",
        },
        "expected": {
            "should_handle_gracefully": True,
            "min_test_count": 0,
        },
        "priority": "P1",
        "category": "input_edge",
    },
]


class TestGenerateTests:
    """Test suite for generate_tests tool."""

    @pytest.fixture
    def tool(self):
        """Initialize the tool for testing."""
        from src.mcp.tools import GenerateTestsTool
        return GenerateTestsTool()

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GENERATE_TESTS_TEST_CASES if tc["priority"] == "P0"],
        ids=lambda tc: tc["id"],
    )
    def test_p0_cases(self, tool, test_case):
        """Test P0 (critical) test cases."""
        result = tool.execute(**test_case["input"])
        self._validate_result(result, test_case["expected"])

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GENERATE_TESTS_TEST_CASES if tc["priority"] == "P1"],
        ids=lambda tc: tc["id"],
    )
    def test_p1_cases(self, tool, test_case):
        """Test P1 (important) test cases."""
        result = tool.execute(**test_case["input"])
        self._validate_result(result, test_case["expected"])

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GENERATE_TESTS_TEST_CASES if tc["priority"] == "P2"],
        ids=lambda tc: tc["id"],
    )
    def test_p2_cases(self, tool, test_case):
        """Test P2 (nice-to-have) test cases."""
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

        # Check for error or warning
        if expected.get("should_error_or_warn"):
            has_issue = "error" in result or (
                "warnings" in result and len(result.get("warnings", [])) > 0
            )
            assert has_issue, "Expected error or warning"
            return

        # Check for graceful handling
        if expected.get("should_handle_gracefully"):
            assert "error" not in result or result.get("tests", "") != ""

        tests = result.get("tests", "")

        # Check syntax validity
        if expected.get("syntax_valid"):
            assert self._is_valid_test_syntax(tests), "Invalid test syntax"

        # Check must-have patterns
        if "must_have_patterns" in expected:
            for pattern in expected["must_have_patterns"]:
                assert re.search(pattern, tests, re.IGNORECASE), \
                    f"Missing pattern: {pattern}"

        # Check must-not-have patterns
        if "must_not_have_patterns" in expected:
            for pattern in expected["must_not_have_patterns"]:
                assert not re.search(pattern, tests, re.IGNORECASE), \
                    f"Should not have pattern: {pattern}"

        # Check should-have patterns
        if "should_have_patterns" in expected:
            found = any(
                re.search(p, tests, re.IGNORECASE)
                for p in expected["should_have_patterns"]
            )
            assert found, f"None of patterns found: {expected['should_have_patterns']}"

        # Check minimum test count
        if "min_test_count" in expected:
            test_count = len(re.findall(r"#\[test\]|fn\s+test_", tests))
            assert test_count >= expected["min_test_count"], \
                f"Too few tests: {test_count} < {expected['min_test_count']}"

        # Check should test functions
        if "should_test_functions" in expected:
            tests_lower = tests.lower()
            for func in expected["should_test_functions"]:
                func_lower = func.lower().replace("_", "")
                # Allow some flexibility in naming
                found = (
                    func.lower() in tests_lower or
                    func_lower in tests_lower.replace("_", "")
                )
                assert found, f"Function not tested: {func}"

        # Check for test summary
        if expected.get("should_have_summary"):
            assert "test_summary" in result
            if "summary_includes" in expected:
                summary = result["test_summary"]
                for key in expected["summary_includes"]:
                    assert key in summary, f"Summary missing: {key}"

        # Check for setup instructions
        if expected.get("should_have_setup_instructions"):
            assert "setup_instructions" in result
            setup = result["setup_instructions"].lower()
            if "setup_mentions" in expected:
                for mention in expected["setup_mentions"]:
                    assert mention.lower() in setup, \
                        f"Setup missing mention: {mention}"

    def _is_valid_test_syntax(self, tests: str) -> bool:
        """Basic test syntax validation."""
        if not tests.strip():
            return False

        # Check for balanced braces
        if tests.count("{") != tests.count("}"):
            return False

        # Check for test markers
        has_test_attr = "#[test]" in tests or "fn test_" in tests
        return has_test_attr


# Test generation metrics
def analyze_test_coverage(result: dict, contract_code: str) -> dict:
    """Analyze test coverage metrics."""
    tests = result.get("tests", "")

    # Extract function names from contract
    contract_functions = set(re.findall(r"pub\s+fn\s+(\w+)", contract_code))

    # Extract tested functions from tests
    tested_functions = set()
    test_names = re.findall(r"fn\s+test_(\w+)", tests)
    for test_name in test_names:
        # Try to match test name to function
        for func in contract_functions:
            if func.lower() in test_name.lower():
                tested_functions.add(func)

    coverage = len(tested_functions) / len(contract_functions) if contract_functions else 0

    return {
        "contract_functions": list(contract_functions),
        "tested_functions": list(tested_functions),
        "untested_functions": list(contract_functions - tested_functions),
        "coverage_percentage": coverage * 100,
        "total_tests": len(re.findall(r"#\[test\]", tests)),
        "has_error_tests": bool(re.search(r"error|fail|panic|revert", tests, re.I)),
        "has_edge_case_tests": bool(re.search(r"zero|max|min|boundary|edge", tests, re.I)),
    }

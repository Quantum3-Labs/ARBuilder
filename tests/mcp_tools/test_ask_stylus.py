"""
Test cases for ask_stylus MCP tool.

Tests Q&A quality, debugging help, and explanation accuracy.
"""

import pytest
from typing import Optional


# Test case definitions
ASK_STYLUS_TEST_CASES = [
    # ===== Concept Explanation (P0) =====
    {
        "id": "ask_concept_001",
        "name": "Concept: What is Stylus",
        "input": {
            "question": "What is Arbitrum Stylus?",
            "question_type": "concept",
        },
        "expected": {
            "answer_contains": ["arbitrum", "wasm", "rust"],
            "answer_min_length": 100,
            "should_have_references": True,
        },
        "priority": "P0",
        "category": "concept",
    },
    {
        "id": "ask_concept_002",
        "name": "Concept: sol_storage macro",
        "input": {
            "question": "What does the sol_storage! macro do in Stylus?",
            "question_type": "concept",
        },
        "expected": {
            "answer_contains": ["storage", "macro", "state"],
            "answer_min_length": 80,
        },
        "priority": "P0",
        "category": "concept",
    },
    {
        "id": "ask_concept_003",
        "name": "Concept: entrypoint attribute",
        "input": {
            "question": "What is the purpose of #[entrypoint] in Stylus contracts?",
            "question_type": "concept",
        },
        "expected": {
            "answer_contains": ["entry", "contract", "function"],
            "answer_min_length": 80,
        },
        "priority": "P0",
        "category": "concept",
    },
    {
        "id": "ask_concept_004",
        "name": "Concept: Gas efficiency",
        "input": {
            "question": "Why is Stylus more gas efficient than Solidity?",
            "question_type": "concept",
        },
        "expected": {
            "answer_contains": ["gas", "wasm"],
            "should_contain_one_of": ["efficient", "cheaper", "faster"],
            "answer_min_length": 100,
        },
        "priority": "P0",
        "category": "concept",
    },

    # ===== Code Debugging (P0) =====
    {
        "id": "ask_debug_001",
        "name": "Debug: missing entrypoint",
        "input": {
            "question": "Why won't this contract compile?",
            "code_context": """
use stylus_sdk::prelude::*;

sol_storage! {
    pub struct Counter {
        uint256 count;
    }
}

impl Counter {
    pub fn increment(&mut self) {
        self.count.set(self.count.get() + U256::from(1));
    }
}
""",
            "question_type": "debugging",
        },
        "expected": {
            "answer_contains": ["entrypoint"],
            "should_identify_issue": True,
            "should_provide_fix": True,
        },
        "priority": "P0",
        "category": "debugging",
    },
    {
        "id": "ask_debug_002",
        "name": "Debug: incorrect storage access",
        "input": {
            "question": "This code panics at runtime, what's wrong?",
            "code_context": """
sol_storage! {
    pub struct Vault {
        mapping(address => uint256) balances;
    }
}

impl Vault {
    pub fn withdraw(&mut self) {
        let sender = msg::sender();
        let balance = self.balances.get(sender);
        // Bug: unchecked subtraction
        self.balances.insert(sender, balance - U256::from(100));
    }
}
""",
            "question_type": "debugging",
        },
        "expected": {
            "should_identify_issue": True,
            "answer_should_mention": ["overflow", "underflow", "checked", "balance"],
        },
        "priority": "P0",
        "category": "debugging",
    },
    {
        "id": "ask_debug_003",
        "name": "Debug: type mismatch",
        "input": {
            "question": "I'm getting a type error with this transfer function",
            "code_context": """
pub fn transfer(&mut self, to: Address, amount: u64) {
    let sender = msg::sender();
    let sender_balance = self.balances.get(sender); // Returns U256
    self.balances.insert(sender, sender_balance - amount); // Error here
}
""",
            "question_type": "debugging",
        },
        "expected": {
            "answer_should_mention": ["u256", "u64", "type", "convert"],
            "should_provide_fix": True,
        },
        "priority": "P0",
        "category": "debugging",
    },

    # ===== Best Practice Guidance (P0) =====
    {
        "id": "ask_best_001",
        "name": "Best practice: storage patterns",
        "input": {
            "question": "What's the best way to store a list of users in Stylus?",
            "question_type": "howto",
        },
        "expected": {
            "answer_contains": ["storagevec", "storage"],
            "should_have_code_example": True,
        },
        "priority": "P0",
        "category": "best_practice",
    },
    {
        "id": "ask_best_002",
        "name": "Best practice: error handling",
        "input": {
            "question": "What's the recommended way to handle errors in Stylus?",
            "question_type": "howto",
        },
        "expected": {
            "answer_should_mention": ["result", "error", "custom"],
            "should_have_code_example": True,
        },
        "priority": "P0",
        "category": "best_practice",
    },
    {
        "id": "ask_best_003",
        "name": "Best practice: access control",
        "input": {
            "question": "How should I implement owner-only functions in Stylus?",
            "question_type": "howto",
        },
        "expected": {
            "answer_should_mention": ["owner", "msg::sender", "check"],
            "should_have_code_example": True,
        },
        "priority": "P0",
        "category": "best_practice",
    },

    # ===== Comparison: Stylus vs Solidity (P1) =====
    {
        "id": "ask_compare_001",
        "name": "Compare: Stylus vs Solidity storage",
        "input": {
            "question": "How does storage work differently in Stylus compared to Solidity?",
            "question_type": "comparison",
        },
        "expected": {
            "answer_contains": ["stylus", "solidity"],
            "answer_should_mention": ["sol_storage", "storage"],
            "answer_min_length": 150,
        },
        "priority": "P1",
        "category": "comparison",
    },
    {
        "id": "ask_compare_002",
        "name": "Compare: function visibility",
        "input": {
            "question": "How do public/private functions differ between Stylus and Solidity?",
            "question_type": "comparison",
        },
        "expected": {
            "answer_should_mention": ["pub", "public", "external"],
            "answer_min_length": 100,
        },
        "priority": "P1",
        "category": "comparison",
    },

    # ===== Architecture Advice (P1) =====
    {
        "id": "ask_arch_001",
        "name": "Architecture: multi-contract system",
        "input": {
            "question": "How should I structure a multi-contract DeFi protocol in Stylus?",
            "question_type": "general",
        },
        "expected": {
            "answer_should_mention": ["contract", "call", "interface"],
            "answer_min_length": 150,
        },
        "priority": "P1",
        "category": "architecture",
    },
    {
        "id": "ask_arch_002",
        "name": "Architecture: upgradeable contracts",
        "input": {
            "question": "Can Stylus contracts be upgradeable? How?",
            "question_type": "general",
        },
        "expected": {
            "answer_should_mention": ["proxy", "upgrade"],
            "answer_min_length": 100,
        },
        "priority": "P1",
        "category": "architecture",
    },

    # ===== How-to Questions (P0) =====
    {
        "id": "ask_howto_001",
        "name": "How-to: deploy to testnet",
        "input": {
            "question": "How do I deploy a Stylus contract to Arbitrum Sepolia?",
            "question_type": "howto",
        },
        "expected": {
            "answer_contains": ["cargo", "stylus", "deploy"],
            "answer_should_mention": ["testnet", "sepolia", "rpc"],
            "answer_min_length": 100,
        },
        "priority": "P0",
        "category": "howto",
    },
    {
        "id": "ask_howto_002",
        "name": "How-to: emit events",
        "input": {
            "question": "How do I emit events in a Stylus contract?",
            "question_type": "howto",
        },
        "expected": {
            "answer_should_mention": ["evm", "log", "event"],
            "should_have_code_example": True,
        },
        "priority": "P0",
        "category": "howto",
    },
    {
        "id": "ask_howto_003",
        "name": "How-to: call other contracts",
        "input": {
            "question": "How do I call another contract from my Stylus contract?",
            "question_type": "howto",
        },
        "expected": {
            "answer_should_mention": ["call", "address", "interface"],
            "should_have_code_example": True,
        },
        "priority": "P0",
        "category": "howto",
    },

    # ===== Follow-up Questions =====
    {
        "id": "ask_followup_001",
        "name": "Follow-up: suggest related topics",
        "input": {
            "question": "What is StorageMap in Stylus?",
            "question_type": "concept",
        },
        "expected": {
            "should_have_follow_up_questions": True,
            "follow_up_topics": ["StorageVec", "storage", "sol_storage"],
        },
        "priority": "P1",
        "category": "follow_up",
    },

    # ===== Edge Cases =====
    {
        "id": "ask_edge_001",
        "name": "Edge: empty question",
        "input": {
            "question": "",
        },
        "expected": {
            "should_error": True,
            "error_contains": "question",
        },
        "priority": "P0",
        "category": "edge_cases",
    },
    {
        "id": "ask_edge_002",
        "name": "Edge: off-topic question",
        "input": {
            "question": "What's the weather like today?",
        },
        "expected": {
            "should_redirect": True,
            "redirect_message_contains": "stylus",
        },
        "priority": "P1",
        "category": "edge_cases",
    },
    {
        "id": "ask_edge_003",
        "name": "Edge: ambiguous question",
        "input": {
            "question": "How do I use storage?",
        },
        "expected": {
            "answer_min_length": 50,
            "should_ask_for_clarification_or_provide_general": True,
        },
        "priority": "P1",
        "category": "edge_cases",
    },
]


class TestAskStylus:
    """Test suite for ask_stylus tool."""

    @pytest.fixture
    def tool(self):
        """Initialize the tool for testing."""
        from src.mcp.tools import AskStylusTool
        return AskStylusTool()

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in ASK_STYLUS_TEST_CASES if tc["priority"] == "P0"],
        ids=lambda tc: tc["id"],
    )
    def test_p0_cases(self, tool, test_case):
        """Test P0 (critical) test cases."""
        result = tool.execute(**test_case["input"])
        self._validate_result(result, test_case["expected"])

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in ASK_STYLUS_TEST_CASES if tc["priority"] == "P1"],
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

        answer = result.get("answer", "")

        # Check answer contains keywords
        if "answer_contains" in expected:
            answer_lower = answer.lower()
            for keyword in expected["answer_contains"]:
                assert keyword.lower() in answer_lower, \
                    f"Answer missing keyword: {keyword}"

        # Check answer should mention (at least one)
        if "answer_should_mention" in expected:
            answer_lower = answer.lower()
            found = any(
                kw.lower() in answer_lower
                for kw in expected["answer_should_mention"]
            )
            assert found, \
                f"Answer doesn't mention any of: {expected['answer_should_mention']}"

        # Check should contain one of
        if "should_contain_one_of" in expected:
            answer_lower = answer.lower()
            found = any(
                kw.lower() in answer_lower
                for kw in expected["should_contain_one_of"]
            )
            assert found, \
                f"Answer doesn't contain any of: {expected['should_contain_one_of']}"

        # Check minimum length
        if "answer_min_length" in expected:
            assert len(answer) >= expected["answer_min_length"], \
                f"Answer too short: {len(answer)} < {expected['answer_min_length']}"

        # Check for code examples
        if expected.get("should_have_code_example"):
            has_code = (
                "code_examples" in result and len(result["code_examples"]) > 0
            ) or "```" in answer or "fn " in answer
            assert has_code, "Missing code example"

        # Check for references
        if expected.get("should_have_references"):
            assert "references" in result and len(result["references"]) > 0

        # Check for follow-up questions
        if expected.get("should_have_follow_up_questions"):
            assert (
                "follow_up_questions" in result
                and len(result["follow_up_questions"]) > 0
            )

        # Check debugging results
        if expected.get("should_identify_issue"):
            # Answer should be substantive enough to identify an issue
            assert len(answer) > 50, "Answer too short to identify issue"

        if expected.get("should_provide_fix"):
            # Should have code or clear fix instruction
            has_fix = "```" in answer or "fix" in answer.lower() or "should" in answer.lower()
            assert has_fix, "Missing fix suggestion"


# Answer quality metrics
def analyze_answer_quality(result: dict) -> dict:
    """Analyze the quality of an answer."""
    answer = result.get("answer", "")
    return {
        "length": len(answer),
        "word_count": len(answer.split()),
        "has_code_examples": (
            len(result.get("code_examples", [])) > 0 or "```" in answer
        ),
        "has_references": len(result.get("references", [])) > 0,
        "has_follow_ups": len(result.get("follow_up_questions", [])) > 0,
        "paragraph_count": answer.count("\n\n") + 1,
        "mentions_stylus": "stylus" in answer.lower(),
        "mentions_rust": "rust" in answer.lower(),
    }

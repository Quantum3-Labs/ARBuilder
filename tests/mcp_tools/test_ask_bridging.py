"""
Tests for ask_bridging tool.
"""

import pytest
from src.mcp.tools.ask_bridging import AskBridgingTool


class TestAskBridgingTool:
    """Test the ask_bridging tool."""

    @pytest.fixture
    def tool(self):
        return AskBridgingTool()

    def test_eth_deposit_question(self, tool):
        """Test question about ETH deposits."""
        result = tool.execute(question="How do I deposit ETH to Arbitrum?")

        assert "error" not in result
        assert "answer" in result
        assert "eth_deposit" in result["topics"]

    def test_eth_withdraw_question(self, tool):
        """Test question about ETH withdrawals."""
        result = tool.execute(question="How do I withdraw ETH from L2 to L1?")

        assert "error" not in result
        assert "eth_withdraw" in result["topics"]

    def test_token_deposit_question(self, tool):
        """Test question about token deposits."""
        result = tool.execute(question="How do I bridge ERC20 tokens to Arbitrum?")

        assert "error" not in result
        assert "erc20_deposit" in result["topics"]

    def test_retryable_question(self, tool):
        """Test question about retryable tickets."""
        result = tool.execute(question="What are retryable tickets?")

        assert "error" not in result
        assert "retryable_tickets" in result["topics"]

    def test_l2_to_l1_messaging(self, tool):
        """Test question about L2 to L1 messaging."""
        result = tool.execute(question="How do I send a message from L2 to L1?")

        assert "error" not in result
        assert "l2_to_l1_messaging" in result["topics"]

    def test_l3_bridging(self, tool):
        """Test question about L3/Orbit bridging."""
        result = tool.execute(question="How do I bridge to an L3 Orbit chain?")

        assert "error" not in result
        assert "l1_l3_bridging" in result["topics"]

    def test_timing_question(self, tool):
        """Test question about bridge timing."""
        result = tool.execute(question="How long does a withdrawal take?")

        assert "error" not in result
        # Should mention withdrawals since that's what takes time
        assert any("withdraw" in t for t in result["topics"]) or \
               any("l2_to_l1" in t for t in result["topics"])

    def test_empty_question_error(self, tool):
        """Test error on empty question."""
        result = tool.execute(question="")
        assert "error" in result

    def test_references_included(self, tool):
        """Test that references are included."""
        result = tool.execute(question="How do I deposit ETH?")

        assert "references" in result
        assert len(result["references"]) > 0
        assert any("arbitrum.io" in r for r in result["references"])

    def test_code_example_optional(self, tool):
        """Test code example inclusion."""
        result = tool.execute(
            question="How do I deposit ETH?",
            include_code_example=True
        )

        assert "code_example" in result
        assert "EthBridger" in result["code_example"] or "deposit" in result["code_example"]

    def test_generic_question(self, tool):
        """Test generic/unmatched question."""
        result = tool.execute(question="What is Arbitrum?")

        assert "error" not in result
        assert "answer" in result
        # Should still provide overview information
        assert "Bridging Overview" in result["answer"] or len(result["answer"]) > 100

    def test_gas_token_question(self, tool):
        """Test question about custom gas tokens."""
        result = tool.execute(question="How do custom gas tokens work for L3?")

        assert "error" not in result
        assert "custom_gas_token" in result["topics"]

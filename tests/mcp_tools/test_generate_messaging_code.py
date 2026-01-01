"""
Tests for generate_messaging_code tool.
"""

import pytest
from src.mcp.tools.generate_messaging_code import GenerateMessagingCodeTool


class TestGenerateMessagingCodeTool:
    """Test the generate_messaging_code tool."""

    @pytest.fixture
    def tool(self):
        return GenerateMessagingCodeTool()

    def test_l1_to_l2_message(self, tool):
        """Test L1 -> L2 messaging code generation."""
        result = tool.execute(message_type="l1_to_l2")

        assert "error" not in result
        assert "code" in result
        assert "ParentToChildMessageCreator" in result["code"]
        assert "retryable" in result["code"].lower()
        assert "gasLimit" in result["code"]

    def test_l2_to_l1_message(self, tool):
        """Test L2 -> L1 messaging code generation."""
        result = tool.execute(message_type="l2_to_l1")

        assert "error" not in result
        assert "ArbSys" in result["code"] or "ARB_SYS" in result["code"]
        assert "sendTxToL1" in result["code"]
        assert "7 day" in " ".join(result["notes"]).lower()

    def test_l2_to_l1_claim(self, tool):
        """Test L2 -> L1 claim code generation."""
        result = tool.execute(message_type="l2_to_l1_claim")

        assert "error" not in result
        assert "ChildToParentMessage" in result["code"]
        assert "execute" in result["code"]
        assert "CONFIRMED" in result["code"]

    def test_check_status(self, tool):
        """Test message status check code generation."""
        result = tool.execute(message_type="check_status")

        assert "error" not in result
        assert "ParentToChildMessageStatus" in result["code"]
        assert "ChildToParentMessageStatus" in result["code"]
        assert "REDEEMED" in result["code"]

    def test_missing_message_type(self, tool):
        """Test error on missing message_type."""
        result = tool.execute()
        assert "error" in result
        assert "message_type" in result["error"]

    def test_unknown_message_type(self, tool):
        """Test error on unknown message_type."""
        result = tool.execute(message_type="invalid")
        assert "error" in result
        assert "Unknown" in result["error"]

    def test_dependencies_included(self, tool):
        """Test that dependencies are correctly specified."""
        result = tool.execute(message_type="l1_to_l2")

        assert "dependencies" in result
        assert "ethers" in result["dependencies"]
        assert "@arbitrum/sdk" in result["dependencies"]

    def test_env_vars_included(self, tool):
        """Test that required env vars are listed."""
        result = tool.execute(message_type="l1_to_l2")

        assert "env_vars" in result
        assert "L1_RPC_URL" in result["env_vars"]
        assert "L2_RPC_URL" in result["env_vars"]

    def test_related_types_included(self, tool):
        """Test that related types/enums are included."""
        result = tool.execute(message_type="check_status")

        assert "related_types" in result
        assert "ParentToChildMessageStatus" in result["related_types"]
        assert "ChildToParentMessageStatus" in result["related_types"]

    def test_l1_to_l2_notes_mention_retryable(self, tool):
        """Test L1->L2 notes explain retryable tickets."""
        result = tool.execute(message_type="l1_to_l2")

        notes_text = " ".join(result["notes"]).lower()
        assert "retryable" in notes_text

    def test_l2_to_l1_notes_mention_challenge(self, tool):
        """Test L2->L1 notes explain challenge period."""
        result = tool.execute(message_type="l2_to_l1")

        notes_text = " ".join(result["notes"]).lower()
        assert "challenge" in notes_text or "7 day" in notes_text

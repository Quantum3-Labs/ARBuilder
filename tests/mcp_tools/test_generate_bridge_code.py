"""
Tests for generate_bridge_code tool.
"""

import pytest
from src.mcp.tools.generate_bridge_code import GenerateBridgeCodeTool


class TestGenerateBridgeCodeTool:
    """Test the generate_bridge_code tool."""

    @pytest.fixture
    def tool(self):
        return GenerateBridgeCodeTool()

    def test_eth_deposit(self, tool):
        """Test ETH deposit code generation."""
        result = tool.execute(bridge_type="eth_deposit", amount="0.5")

        assert "error" not in result
        assert "code" in result
        assert "EthBridger" in result["code"]
        assert "deposit" in result["code"]
        assert "0.5" in result["code"]
        assert result["bridge_type"] == "eth_deposit"
        assert "@arbitrum/sdk" in result["dependencies"]

    def test_eth_deposit_to(self, tool):
        """Test ETH deposit to different address."""
        result = tool.execute(
            bridge_type="eth_deposit_to",
            amount="1.0",
            destination_address="0x1234"
        )

        assert "error" not in result
        assert "depositTo" in result["code"]
        assert "destinationAddress" in result["code"]

    def test_eth_withdraw(self, tool):
        """Test ETH withdrawal code generation."""
        result = tool.execute(bridge_type="eth_withdraw", amount="0.1")

        assert "error" not in result
        assert "withdraw" in result["code"]
        assert "childSigner" in result["code"]
        assert "7 day" in " ".join(result["notes"]).lower()

    def test_erc20_deposit(self, tool):
        """Test ERC20 deposit code generation."""
        result = tool.execute(
            bridge_type="erc20_deposit",
            token_address="0xTokenAddress"
        )

        assert "error" not in result
        assert "Erc20Bridger" in result["code"]
        assert "approveToken" in result["code"]
        assert "deposit" in result["code"]

    def test_erc20_withdraw(self, tool):
        """Test ERC20 withdrawal code generation."""
        result = tool.execute(
            bridge_type="erc20_withdraw",
            token_address="0xTokenAddress"
        )

        assert "error" not in result
        assert "withdraw" in result["code"]
        assert "getChildErc20Address" in result["code"]

    def test_eth_l1_l3(self, tool):
        """Test L1 -> L3 ETH bridging code generation."""
        result = tool.execute(bridge_type="eth_l1_l3", amount="0.2")

        assert "error" not in result
        assert "EthL1L3Bridger" in result["code"]
        assert "L3_RPC_URL" in result["env_vars"]
        assert "double retryable" in " ".join(result["notes"]).lower()

    def test_erc20_l1_l3(self, tool):
        """Test L1 -> L3 ERC20 bridging code generation."""
        result = tool.execute(
            bridge_type="erc20_l1_l3",
            token_address="0xTokenAddress"
        )

        assert "error" not in result
        assert "Erc20L1L3Bridger" in result["code"]
        assert "approveGasToken" in result["code"]

    def test_missing_bridge_type(self, tool):
        """Test error on missing bridge_type."""
        result = tool.execute()
        assert "error" in result
        assert "bridge_type" in result["error"]

    def test_unknown_bridge_type(self, tool):
        """Test error on unknown bridge_type."""
        result = tool.execute(bridge_type="invalid_type")
        assert "error" in result
        assert "Unknown" in result["error"]

    def test_dependencies_included(self, tool):
        """Test that dependencies are correctly specified."""
        result = tool.execute(bridge_type="eth_deposit")

        assert "dependencies" in result
        assert "ethers" in result["dependencies"]
        assert "@arbitrum/sdk" in result["dependencies"]

    def test_env_vars_included(self, tool):
        """Test that required env vars are listed."""
        result = tool.execute(bridge_type="eth_deposit")

        assert "env_vars" in result
        assert "L1_RPC_URL" in result["env_vars"]
        assert "L2_RPC_URL" in result["env_vars"]
        assert "PRIVATE_KEY" in result["env_vars"]

    def test_notes_for_deposits(self, tool):
        """Test that deposit notes mention confirmation time."""
        result = tool.execute(bridge_type="eth_deposit")

        notes_text = " ".join(result["notes"]).lower()
        assert "10-15 minutes" in notes_text or "confirm" in notes_text

    def test_notes_for_withdrawals(self, tool):
        """Test that withdrawal notes mention challenge period."""
        result = tool.execute(bridge_type="eth_withdraw")

        notes_text = " ".join(result["notes"]).lower()
        assert "7 day" in notes_text or "challenge" in notes_text

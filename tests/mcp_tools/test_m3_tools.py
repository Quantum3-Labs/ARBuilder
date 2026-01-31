"""
Tests for Milestone 3 (Full dApp Builder) MCP tools.

Tests the following tools:
- generate_backend: NestJS/Express backend generation
- generate_frontend: Next.js + wagmi frontend generation
- generate_indexer: The Graph subgraph generation
- generate_oracle: Chainlink integration generation
- orchestrate_dapp: Full dApp scaffolding
"""

import json
import subprocess
import tempfile
import shutil
from pathlib import Path

import pytest


class MCPClient:
    """Simple MCP client for testing."""

    def __init__(self):
        self.server_cmd = ["uv", "run", "python", "-m", "src.mcp.server"]

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Call a tool via MCP."""
        request = {
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments}
        }

        result = subprocess.run(
            self.server_cmd,
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0 and not result.stdout:
            raise RuntimeError(f"MCP server error: {result.stderr}")

        response = json.loads(result.stdout.strip())

        if response.get("isError"):
            return {"error": response["content"][0]["text"]}

        content_text = response["content"][0]["text"]
        return json.loads(content_text)


# ============================================================================
# generate_backend Tests
# ============================================================================

class TestGenerateBackend:
    """Tests for the generate_backend tool."""

    @pytest.fixture
    def client(self):
        return MCPClient()

    def test_nestjs_backend_basic(self, client):
        """Test basic NestJS backend generation."""
        result = client.call_tool("generate_backend", {
            "prompt": "Create a backend for a token staking dApp",
            "framework": "nestjs"
        })

        assert "error" not in result, f"Generation failed: {result.get('error')}"
        assert "files" in result
        assert "dependencies" in result
        assert "package.json" in result["files"] or any("package.json" in f for f in result["files"])

    def test_nestjs_with_contract_abi(self, client):
        """Test NestJS backend with contract ABI."""
        abi = [
            {"type": "function", "name": "stake", "inputs": [{"name": "amount", "type": "uint256"}]},
            {"type": "function", "name": "unstake", "inputs": []},
            {"type": "function", "name": "getStake", "inputs": [], "outputs": [{"name": "", "type": "uint256"}]}
        ]

        result = client.call_tool("generate_backend", {
            "prompt": "Create a staking backend",
            "framework": "nestjs",
            "contract_abi": json.dumps(abi)
        })

        assert "error" not in result
        assert "files" in result
        # Should have generated service files for contract interaction
        files_str = str(result["files"])
        assert "viem" in files_str or "contract" in files_str.lower()

    def test_express_backend(self, client):
        """Test Express backend generation."""
        result = client.call_tool("generate_backend", {
            "prompt": "Create a simple API for NFT metadata",
            "framework": "express"
        })

        assert "error" not in result
        assert "files" in result
        assert "dependencies" in result
        # Express should be in dependencies
        deps_str = str(result["dependencies"])
        assert "express" in deps_str.lower()

    def test_backend_with_features(self, client):
        """Test backend with specific features."""
        result = client.call_tool("generate_backend", {
            "prompt": "Create a DeFi backend with swap tracking",
            "framework": "nestjs",
            "features": ["websocket", "caching"]
        })

        assert "error" not in result
        assert "files" in result


# ============================================================================
# generate_frontend Tests
# ============================================================================

class TestGenerateFrontend:
    """Tests for the generate_frontend tool."""

    @pytest.fixture
    def client(self):
        return MCPClient()

    def test_nextjs_frontend_basic(self, client):
        """Test basic Next.js frontend generation."""
        result = client.call_tool("generate_frontend", {
            "prompt": "Create a token dashboard frontend"
        })

        assert "error" not in result, f"Generation failed: {result.get('error')}"
        assert "files" in result
        assert "dependencies" in result
        # Should include wagmi/viem
        deps_str = str(result["dependencies"])
        assert "wagmi" in deps_str.lower() or "viem" in deps_str.lower()

    def test_frontend_with_contract_abi(self, client):
        """Test frontend with contract ABI generates hooks."""
        abi = [
            {"type": "function", "name": "balanceOf", "inputs": [{"name": "account", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view"},
            {"type": "function", "name": "transfer", "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], "outputs": [{"name": "", "type": "bool"}]}
        ]

        result = client.call_tool("generate_frontend", {
            "prompt": "Create a token interface",
            "contract_abi": json.dumps(abi)
        })

        assert "error" not in result
        assert "files" in result
        # Should have hook files
        files_str = str(result["files"])
        assert "hook" in files_str.lower() or "use" in files_str.lower()

    def test_frontend_with_ui_framework(self, client):
        """Test frontend with DaisyUI."""
        result = client.call_tool("generate_frontend", {
            "prompt": "Create a staking dashboard",
            "ui_framework": "daisyui"
        })

        assert "error" not in result
        assert "files" in result
        deps_str = str(result["dependencies"])
        assert "daisyui" in deps_str.lower() or "tailwind" in deps_str.lower()

    def test_frontend_dashboard_template(self, client):
        """Test contract dashboard template."""
        result = client.call_tool("generate_frontend", {
            "prompt": "Create an admin dashboard for my contract",
            "template": "dashboard"
        })

        assert "error" not in result
        assert "files" in result


# ============================================================================
# generate_indexer Tests
# ============================================================================

class TestGenerateIndexer:
    """Tests for the generate_indexer tool."""

    @pytest.fixture
    def client(self):
        return MCPClient()

    def test_erc20_subgraph(self, client):
        """Test ERC20 subgraph generation."""
        result = client.call_tool("generate_indexer", {
            "contract_address": "0x912CE59144191C1204E64559FE8253a0e49E6548",
            "subgraph_type": "erc20"
        })

        assert "error" not in result, f"Generation failed: {result.get('error')}"
        assert "files" in result
        # Should have subgraph.yaml, schema.graphql, mapping files
        files_str = str(result["files"])
        assert "subgraph" in files_str.lower() or "schema" in files_str.lower()

    def test_erc721_subgraph(self, client):
        """Test ERC721 subgraph generation."""
        result = client.call_tool("generate_indexer", {
            "contract_address": "0x1234567890123456789012345678901234567890",
            "subgraph_type": "erc721"
        })

        assert "error" not in result
        assert "files" in result

    def test_custom_subgraph_with_events(self, client):
        """Test custom subgraph with specific events."""
        result = client.call_tool("generate_indexer", {
            "contract_address": "0x1234567890123456789012345678901234567890",
            "subgraph_type": "custom",
            "events": ["Staked(address indexed user, uint256 amount)", "Unstaked(address indexed user, uint256 amount)"]
        })

        assert "error" not in result
        assert "files" in result
        # Should handle custom events
        files_str = str(result["files"])
        assert "staked" in files_str.lower() or "handler" in files_str.lower()

    def test_subgraph_with_abi(self, client):
        """Test subgraph generation with ABI."""
        abi = [
            {"type": "event", "name": "Transfer", "inputs": [{"indexed": True, "name": "from", "type": "address"}, {"indexed": True, "name": "to", "type": "address"}, {"indexed": False, "name": "value", "type": "uint256"}]}
        ]

        result = client.call_tool("generate_indexer", {
            "contract_address": "0x1234567890123456789012345678901234567890",
            "abi": json.dumps(abi)
        })

        assert "error" not in result
        assert "files" in result


# ============================================================================
# generate_oracle Tests
# ============================================================================

class TestGenerateOracle:
    """Tests for the generate_oracle tool."""

    @pytest.fixture
    def client(self):
        return MCPClient()

    def test_price_feed(self, client):
        """Test Chainlink price feed generation."""
        result = client.call_tool("generate_oracle", {
            "oracle_type": "price_feed",
            "network": "arbitrum-sepolia"
        })

        assert "error" not in result, f"Generation failed: {result.get('error')}"
        assert "files" in result
        # Should have Solidity contract
        files_str = str(result["files"])
        assert "sol" in files_str.lower() or "contract" in files_str.lower()

    def test_price_feed_with_feeds(self, client):
        """Test price feed with specific feeds."""
        result = client.call_tool("generate_oracle", {
            "oracle_type": "price_feed",
            "network": "arbitrum-one",
            "feeds": ["ETH/USD", "BTC/USD"]
        })

        assert "error" not in result
        assert "files" in result

    def test_vrf_randomness(self, client):
        """Test Chainlink VRF generation."""
        result = client.call_tool("generate_oracle", {
            "oracle_type": "vrf",
            "network": "arbitrum-sepolia"
        })

        assert "error" not in result
        assert "files" in result
        files_str = str(result["files"])
        # Should have VRF-related code
        assert "vrf" in files_str.lower() or "random" in files_str.lower()

    def test_automation(self, client):
        """Test Chainlink Automation generation."""
        result = client.call_tool("generate_oracle", {
            "oracle_type": "automation",
            "network": "arbitrum-one"
        })

        assert "error" not in result
        assert "files" in result
        files_str = str(result["files"])
        assert "automation" in files_str.lower() or "upkeep" in files_str.lower()

    def test_functions(self, client):
        """Test Chainlink Functions generation."""
        result = client.call_tool("generate_oracle", {
            "oracle_type": "functions",
            "network": "arbitrum-sepolia"
        })

        assert "error" not in result
        assert "files" in result


# ============================================================================
# orchestrate_dapp Tests
# ============================================================================

class TestOrchestrateDapp:
    """Tests for the orchestrate_dapp tool."""

    @pytest.fixture
    def client(self):
        return MCPClient()

    def test_full_dapp_scaffolding(self, client):
        """Test full dApp scaffolding with all components."""
        result = client.call_tool("orchestrate_dapp", {
            "prompt": "Create a token staking dApp",
            "components": ["contract", "backend", "frontend"],
            "network": "arbitrum-sepolia"
        })

        assert "error" not in result, f"Generation failed: {result.get('error')}"
        assert "project" in result or "files" in result
        # Should have generated multiple components
        result_str = str(result)
        assert "backend" in result_str.lower() or "frontend" in result_str.lower()

    def test_dapp_with_indexer(self, client):
        """Test dApp with indexer component."""
        result = client.call_tool("orchestrate_dapp", {
            "prompt": "Create an NFT marketplace",
            "components": ["contract", "frontend", "indexer"],
            "network": "arbitrum-one"
        })

        assert "error" not in result
        # Should have indexer/subgraph files
        result_str = str(result)
        assert "subgraph" in result_str.lower() or "indexer" in result_str.lower() or "files" in result

    def test_dapp_with_oracle(self, client):
        """Test dApp with oracle component."""
        result = client.call_tool("orchestrate_dapp", {
            "prompt": "Create a prediction market",
            "components": ["contract", "frontend", "oracle"],
            "network": "arbitrum-sepolia"
        })

        assert "error" not in result
        result_str = str(result)
        assert "oracle" in result_str.lower() or "chainlink" in result_str.lower() or "files" in result

    def test_minimal_dapp(self, client):
        """Test minimal dApp with just contract and frontend."""
        result = client.call_tool("orchestrate_dapp", {
            "prompt": "Create a simple voting contract",
            "components": ["contract", "frontend"]
        })

        assert "error" not in result
        assert "project" in result or "files" in result


# ============================================================================
# Integration Tests
# ============================================================================

class TestM3Integration:
    """Integration tests for M3 tools working together."""

    @pytest.fixture
    def client(self):
        return MCPClient()

    @pytest.mark.slow
    def test_contract_to_frontend_flow(self, client):
        """Test generating frontend from contract ABI."""
        # First, generate a contract (using existing M1 tool)
        contract_result = client.call_tool("generate_stylus_code", {
            "prompt": "Create a simple ERC20 token with mint and burn"
        })

        assert "error" not in contract_result
        assert "code" in contract_result

        # Then generate frontend for it
        frontend_result = client.call_tool("generate_frontend", {
            "prompt": "Create interface for ERC20 token with mint, burn, transfer"
        })

        assert "error" not in frontend_result
        assert "files" in frontend_result

    @pytest.mark.slow
    def test_contract_to_indexer_flow(self, client):
        """Test generating indexer from contract."""
        # Generate indexer for a token contract
        result = client.call_tool("generate_indexer", {
            "contract_address": "0x912CE59144191C1204E64559FE8253a0e49E6548",
            "subgraph_type": "erc20"
        })

        assert "error" not in result
        assert "files" in result


# ============================================================================
# Quick Test Runner
# ============================================================================

def run_quick_m3_test():
    """Run a quick M3 end-to-end test."""
    print("=== M3 End-to-End Test ===\n")

    client = MCPClient()

    # Test 1: generate_backend
    print("1. Testing generate_backend...")
    result = client.call_tool("generate_backend", {
        "prompt": "Create a token API backend",
        "framework": "nestjs"
    })
    assert "files" in result, f"Failed: {result}"
    print(f"   ✓ Generated {len(result['files'])} files")

    # Test 2: generate_frontend
    print("\n2. Testing generate_frontend...")
    result = client.call_tool("generate_frontend", {
        "prompt": "Create a token dashboard"
    })
    assert "files" in result, f"Failed: {result}"
    print(f"   ✓ Generated {len(result['files'])} files")

    # Test 3: generate_indexer
    print("\n3. Testing generate_indexer...")
    result = client.call_tool("generate_indexer", {
        "contract_address": "0x912CE59144191C1204E64559FE8253a0e49E6548",
        "subgraph_type": "erc20"
    })
    assert "files" in result, f"Failed: {result}"
    print(f"   ✓ Generated subgraph files")

    # Test 4: generate_oracle
    print("\n4. Testing generate_oracle...")
    result = client.call_tool("generate_oracle", {
        "oracle_type": "price_feed",
        "network": "arbitrum-sepolia"
    })
    assert "files" in result, f"Failed: {result}"
    print(f"   ✓ Generated oracle integration files")

    # Test 5: orchestrate_dapp
    print("\n5. Testing orchestrate_dapp...")
    result = client.call_tool("orchestrate_dapp", {
        "prompt": "Create a staking dApp",
        "components": ["contract", "frontend", "backend"]
    })
    assert "project" in result or "files" in result, f"Failed: {result}"
    print(f"   ✓ Generated full dApp scaffold")

    print("\n=== All M3 tests passed! ===")
    return True


if __name__ == "__main__":
    run_quick_m3_test()

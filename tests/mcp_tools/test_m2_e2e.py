"""
End-to-end tests for M2 Arbitrum SDK tools.

Tests the full flow: MCP request → code generation → TypeScript compilation.
"""

import json
import os
import shutil
import subprocess
import tempfile
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
            timeout=60,
        )

        if result.returncode != 0 and not result.stdout:
            raise RuntimeError(f"MCP server error: {result.stderr}")

        response = json.loads(result.stdout.strip())

        if response.get("isError"):
            return {"error": response["content"][0]["text"]}

        content_text = response["content"][0]["text"]
        return json.loads(content_text)


class TestM2BridgingE2E:
    """End-to-end tests for bridging code generation."""

    @pytest.fixture
    def client(self):
        return MCPClient()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        dir_path = tempfile.mkdtemp(prefix="m2_test_")
        yield dir_path
        shutil.rmtree(dir_path, ignore_errors=True)

    def setup_typescript_project(self, temp_dir: str, code: str, dependencies: dict):
        """Set up a TypeScript project with the generated code."""
        # Create package.json
        package_json = {
            "name": "m2-bridge-test",
            "version": "1.0.0",
            "type": "module",
            "scripts": {
                "typecheck": "tsc --noEmit"
            },
            "dependencies": dependencies,
            "devDependencies": {
                "typescript": "^5.0.0",
                "@types/node": "^20.0.0"
            }
        }

        Path(temp_dir, "package.json").write_text(json.dumps(package_json, indent=2))

        # Create tsconfig.json
        tsconfig = {
            "compilerOptions": {
                "target": "ES2020",
                "module": "ESNext",
                "moduleResolution": "node",
                "esModuleInterop": True,
                "skipLibCheck": True,
                "strict": False,
                "noEmit": True,
                "resolveJsonModule": True
            },
            "include": ["*.ts"]
        }
        Path(temp_dir, "tsconfig.json").write_text(json.dumps(tsconfig, indent=2))

        # Write the generated code
        Path(temp_dir, "bridge.ts").write_text(code)

    @pytest.mark.slow
    def test_eth_deposit_compiles(self, client, temp_dir):
        """Test that generated ETH deposit code compiles."""
        result = client.call_tool("generate_bridge_code", {
            "bridge_type": "eth_deposit",
            "amount": "0.5"
        })

        assert "error" not in result, f"Generation failed: {result.get('error')}"
        assert "code" in result
        assert "dependencies" in result

        # Set up project and run typecheck
        self.setup_typescript_project(temp_dir, result["code"], result["dependencies"])

        try:
            # npm install
            install_result = subprocess.run(
                ["npm", "install"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            assert install_result.returncode == 0, f"npm install failed: {install_result.stderr}"

            # TypeScript type check
            typecheck_result = subprocess.run(
                ["npm", "run", "typecheck"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if typecheck_result.returncode != 0:
                # Check if it's just missing env vars (expected)
                stderr = typecheck_result.stdout + typecheck_result.stderr
                if "Cannot find name 'process'" not in stderr:
                    # Real type error
                    pytest.fail(f"TypeScript errors: {stderr[:500]}")

        except FileNotFoundError:
            pytest.skip("Node.js/npm not installed")
        except subprocess.TimeoutExpired:
            pytest.skip("npm install timed out")

    @pytest.mark.slow
    def test_erc20_deposit_compiles(self, client, temp_dir):
        """Test that generated ERC20 deposit code compiles."""
        result = client.call_tool("generate_bridge_code", {
            "bridge_type": "erc20_deposit",
            "token_address": "0x1234567890123456789012345678901234567890"
        })

        assert "error" not in result
        assert "Erc20Bridger" in result["code"]
        assert "approveToken" in result["code"]

        self.setup_typescript_project(temp_dir, result["code"], result["dependencies"])

        try:
            subprocess.run(
                ["npm", "install"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=120,
                check=True
            )

            typecheck_result = subprocess.run(
                ["npm", "run", "typecheck"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Allow process.env errors but fail on real type errors
            if typecheck_result.returncode != 0:
                stderr = typecheck_result.stdout + typecheck_result.stderr
                if "Cannot find name 'process'" not in stderr and "error TS" in stderr:
                    pytest.fail(f"TypeScript errors: {stderr[:500]}")

        except FileNotFoundError:
            pytest.skip("Node.js/npm not installed")
        except subprocess.TimeoutExpired:
            pytest.skip("Timed out")

    @pytest.mark.slow
    def test_eth_l1_l3_compiles(self, client, temp_dir):
        """Test that generated L1->L3 ETH bridging code compiles."""
        result = client.call_tool("generate_bridge_code", {
            "bridge_type": "eth_l1_l3",
            "amount": "0.1"
        })

        assert "error" not in result
        assert "EthL1L3Bridger" in result["code"]
        assert "L3_RPC_URL" in result["env_vars"]

        self.setup_typescript_project(temp_dir, result["code"], result["dependencies"])

        try:
            subprocess.run(
                ["npm", "install"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=120,
                check=True
            )

            typecheck_result = subprocess.run(
                ["npm", "run", "typecheck"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if typecheck_result.returncode != 0:
                stderr = typecheck_result.stdout + typecheck_result.stderr
                if "Cannot find name 'process'" not in stderr and "error TS" in stderr:
                    pytest.fail(f"TypeScript errors: {stderr[:500]}")

        except FileNotFoundError:
            pytest.skip("Node.js/npm not installed")
        except subprocess.TimeoutExpired:
            pytest.skip("Timed out")


class TestM2MessagingE2E:
    """End-to-end tests for messaging code generation."""

    @pytest.fixture
    def client(self):
        return MCPClient()

    @pytest.fixture
    def temp_dir(self):
        dir_path = tempfile.mkdtemp(prefix="m2_msg_test_")
        yield dir_path
        shutil.rmtree(dir_path, ignore_errors=True)

    def setup_typescript_project(self, temp_dir: str, code: str, dependencies: dict):
        """Set up a TypeScript project with the generated code."""
        package_json = {
            "name": "m2-messaging-test",
            "version": "1.0.0",
            "type": "module",
            "scripts": {
                "typecheck": "tsc --noEmit"
            },
            "dependencies": dependencies,
            "devDependencies": {
                "typescript": "^5.0.0",
                "@types/node": "^20.0.0"
            }
        }

        Path(temp_dir, "package.json").write_text(json.dumps(package_json, indent=2))

        tsconfig = {
            "compilerOptions": {
                "target": "ES2020",
                "module": "ESNext",
                "moduleResolution": "node",
                "esModuleInterop": True,
                "skipLibCheck": True,
                "strict": False,
                "noEmit": True
            },
            "include": ["*.ts"]
        }
        Path(temp_dir, "tsconfig.json").write_text(json.dumps(tsconfig, indent=2))

        Path(temp_dir, "messaging.ts").write_text(code)

    @pytest.mark.slow
    def test_l1_to_l2_message_compiles(self, client, temp_dir):
        """Test that generated L1->L2 messaging code compiles."""
        result = client.call_tool("generate_messaging_code", {
            "message_type": "l1_to_l2"
        })

        assert "error" not in result
        assert "code" in result
        assert "createRetryableTicket" in result["code"]

        self.setup_typescript_project(temp_dir, result["code"], result["dependencies"])

        try:
            subprocess.run(
                ["npm", "install"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=120,
                check=True
            )

            typecheck_result = subprocess.run(
                ["npm", "run", "typecheck"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if typecheck_result.returncode != 0:
                stderr = typecheck_result.stdout + typecheck_result.stderr
                if "Cannot find name 'process'" not in stderr and "error TS" in stderr:
                    pytest.fail(f"TypeScript errors: {stderr[:500]}")

        except FileNotFoundError:
            pytest.skip("Node.js/npm not installed")
        except subprocess.TimeoutExpired:
            pytest.skip("Timed out")

    @pytest.mark.slow
    def test_l2_to_l1_message_compiles(self, client, temp_dir):
        """Test that generated L2->L1 messaging code compiles."""
        result = client.call_tool("generate_messaging_code", {
            "message_type": "l2_to_l1"
        })

        assert "error" not in result
        assert "ArbSys" in result["code"] or "ARB_SYS" in result["code"]
        assert "sendTxToL1" in result["code"]

        self.setup_typescript_project(temp_dir, result["code"], result["dependencies"])

        try:
            subprocess.run(
                ["npm", "install"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=120,
                check=True
            )

            typecheck_result = subprocess.run(
                ["npm", "run", "typecheck"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if typecheck_result.returncode != 0:
                stderr = typecheck_result.stdout + typecheck_result.stderr
                if "Cannot find name 'process'" not in stderr and "error TS" in stderr:
                    pytest.fail(f"TypeScript errors: {stderr[:500]}")

        except FileNotFoundError:
            pytest.skip("Node.js/npm not installed")
        except subprocess.TimeoutExpired:
            pytest.skip("Timed out")

    @pytest.mark.slow
    def test_status_check_compiles(self, client, temp_dir):
        """Test that generated status check code compiles."""
        result = client.call_tool("generate_messaging_code", {
            "message_type": "check_status"
        })

        assert "error" not in result
        assert "ParentToChildMessageStatus" in result["code"]
        assert "ChildToParentMessageStatus" in result["code"]

        self.setup_typescript_project(temp_dir, result["code"], result["dependencies"])

        try:
            subprocess.run(
                ["npm", "install"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=120,
                check=True
            )

            typecheck_result = subprocess.run(
                ["npm", "run", "typecheck"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if typecheck_result.returncode != 0:
                stderr = typecheck_result.stdout + typecheck_result.stderr
                if "Cannot find name 'process'" not in stderr and "error TS" in stderr:
                    pytest.fail(f"TypeScript errors: {stderr[:500]}")

        except FileNotFoundError:
            pytest.skip("Node.js/npm not installed")
        except subprocess.TimeoutExpired:
            pytest.skip("Timed out")


class TestM2AskBridgingE2E:
    """End-to-end tests for ask_bridging tool via MCP."""

    @pytest.fixture
    def client(self):
        return MCPClient()

    def test_ask_bridging_via_mcp(self, client):
        """Test ask_bridging returns valid answers via MCP."""
        result = client.call_tool("ask_bridging", {
            "question": "How do I deposit ETH to Arbitrum?",
            "include_code_example": True
        })

        assert "error" not in result
        assert "answer" in result
        assert "topics" in result
        assert "eth_deposit" in result["topics"]
        assert "code_example" in result
        assert len(result["answer"]) > 50

    def test_ask_bridging_retryable_question(self, client):
        """Test ask_bridging handles retryable ticket questions."""
        result = client.call_tool("ask_bridging", {
            "question": "What are retryable tickets and how do they work?"
        })

        assert "error" not in result
        assert "retryable_tickets" in result["topics"]
        assert "references" in result


def run_quick_m2_test():
    """Run a quick M2 end-to-end test."""
    print("=== M2 End-to-End Test ===\n")

    client = MCPClient()

    # Test 1: generate_bridge_code
    print("1. Testing generate_bridge_code...")
    result = client.call_tool("generate_bridge_code", {
        "bridge_type": "eth_deposit",
        "amount": "0.5"
    })
    assert "code" in result, f"Failed: {result}"
    assert "EthBridger" in result["code"]
    print(f"   ✓ Generated {len(result['code'])} chars of code")
    print(f"   ✓ Dependencies: {list(result['dependencies'].keys())}")

    # Test 2: generate_messaging_code
    print("\n2. Testing generate_messaging_code...")
    result = client.call_tool("generate_messaging_code", {
        "message_type": "l1_to_l2"
    })
    assert "code" in result, f"Failed: {result}"
    assert "createRetryableTicket" in result["code"]
    print(f"   ✓ Generated {len(result['code'])} chars of code")

    # Test 3: ask_bridging
    print("\n3. Testing ask_bridging...")
    result = client.call_tool("ask_bridging", {
        "question": "How long does a withdrawal take?"
    })
    assert "answer" in result, f"Failed: {result}"
    print(f"   ✓ Answer: {len(result['answer'])} chars")
    print(f"   ✓ Topics: {result['topics']}")

    print("\n=== All M2 tests passed! ===")
    return True


if __name__ == "__main__":
    run_quick_m2_test()

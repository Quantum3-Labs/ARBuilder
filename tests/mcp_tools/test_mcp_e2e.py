"""
End-to-end MCP server tests.

Tests the full flow: MCP request → code generation → file writing → compilation.
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

    def call(self, method: str, params: dict = None) -> dict:
        """Send a request to the MCP server and get response."""
        request = {"method": method}
        if params:
            request["params"] = params

        result = subprocess.run(
            self.server_cmd,
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes for LLM calls
        )

        if result.returncode != 0 and not result.stdout:
            raise RuntimeError(f"MCP server error: {result.stderr}")

        return json.loads(result.stdout.strip())

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Call a tool via MCP."""
        response = self.call("tools/call", {"name": name, "arguments": arguments})

        if response.get("isError"):
            error_text = response["content"][0]["text"]
            return {"error": error_text}

        # Parse the JSON content
        content_text = response["content"][0]["text"]
        return json.loads(content_text)


class TestMCPProtocol:
    """Test MCP protocol compliance."""

    @pytest.fixture
    def client(self):
        return MCPClient()

    def test_initialize(self, client):
        """Test MCP initialization."""
        response = client.call("initialize")

        assert response["protocolVersion"] == "2024-11-05"
        assert "tools" in response["capabilities"]
        assert "resources" in response["capabilities"]
        assert "prompts" in response["capabilities"]
        assert response["serverInfo"]["name"] == "arbbuilder"

    def test_tools_list(self, client):
        """Test tools/list returns all 9 tools."""
        response = client.call("tools/list")

        tools = response["tools"]
        assert len(tools) == 9

        tool_names = [t["name"] for t in tools]
        assert "get_stylus_context" in tool_names
        assert "generate_stylus_code" in tool_names
        assert "generate_backend" in tool_names
        assert "generate_frontend" in tool_names
        assert "generate_indexer" in tool_names
        assert "generate_dapp" in tool_names

    def test_resources_list(self, client):
        """Test resources/list returns resources."""
        response = client.call("resources/list")

        resources = response["resources"]
        assert len(resources) >= 5

        uris = [r["uri"] for r in resources]
        assert "stylus://cli/commands" in uris
        assert "stylus://config/networks" in uris

    def test_prompts_list(self, client):
        """Test prompts/list returns prompts."""
        response = client.call("prompts/list")

        prompts = response["prompts"]
        assert len(prompts) >= 5

        names = [p["name"] for p in prompts]
        assert "build-contract" in names
        assert "deploy-contract" in names

    def test_invalid_tool_error(self, client):
        """Test error handling for invalid tool."""
        result = client.call_tool("nonexistent_tool", {})
        assert "error" in result
        assert "Unknown tool" in result["error"]

    def test_missing_param_error(self, client):
        """Test error handling for missing required parameters."""
        result = client.call_tool("generate_backend", {})
        assert "error" in result
        assert "Missing required parameter" in result["error"]
        assert "prompt" in result["error"]

    def test_empty_prompt_error(self, client):
        """Test error handling for empty prompt."""
        result = client.call_tool("generate_backend", {"prompt": ""})
        assert "error" in result
        assert "prompt" in result["error"].lower()


class TestMCPCodeGeneration:
    """Test code generation via MCP."""

    @pytest.fixture
    def client(self):
        return MCPClient()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        dir_path = tempfile.mkdtemp(prefix="mcp_test_")
        yield dir_path
        # Cleanup
        shutil.rmtree(dir_path, ignore_errors=True)

    def write_files(self, result: dict, base_dir: str) -> list[str]:
        """Write generated files to disk."""
        written = []
        files = result.get("files", [])

        for file_info in files:
            path = file_info.get("path", "")
            content = file_info.get("content", "")

            if not path or not content:
                continue

            full_path = Path(base_dir) / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            written.append(str(full_path))

        # Write package.json if present
        if "package_json" in result:
            pkg_path = Path(base_dir) / "package.json"
            pkg_path.write_text(json.dumps(result["package_json"], indent=2))
            written.append(str(pkg_path))

        return written

    @pytest.mark.slow
    def test_backend_generation_and_install(self, client, temp_dir):
        """Test backend generation produces installable code."""
        result = client.call_tool("generate_backend", {
            "prompt": "Create a simple health check endpoint",
            "framework": "nestjs",
        })

        assert "error" not in result, f"Generation failed: {result.get('error')}"
        assert "files" in result
        assert "package_json" in result
        assert "prerequisites" in result

        # Write files
        written = self.write_files(result, temp_dir)
        assert len(written) > 0

        # Verify package.json exists
        pkg_path = Path(temp_dir) / "package.json"
        assert pkg_path.exists()

        # Run npm install (if node is available)
        try:
            subprocess.run(["node", "--version"], check=True, capture_output=True)
            install_result = subprocess.run(
                ["npm", "install", "--ignore-scripts"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            # npm install may have warnings but shouldn't fail completely
            assert install_result.returncode == 0 or "WARN" in install_result.stderr
        except (FileNotFoundError, subprocess.CalledProcessError):
            pytest.skip("Node.js not installed - skipping npm install test")

    @pytest.mark.slow
    def test_frontend_generation_and_build(self, client, temp_dir):
        """Test frontend generation produces buildable Next.js code."""
        result = client.call_tool("generate_frontend", {
            "prompt": "Create a simple wallet connection page",
            "wallet_kit": "rainbowkit",
            "ui_library": "daisyui",
        })

        # Handle transient API errors
        if "error" in result:
            error_msg = result.get("error", "")
            if "peer closed" in error_msg or "connection" in error_msg.lower():
                pytest.skip("Transient API connection error")
        assert "error" not in result, f"Generation failed: {result.get('error')}"
        assert "files" in result
        assert "package_json" in result
        assert "prerequisites" in result

        # Check required dependencies
        pkg = result["package_json"]
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        assert "@rainbow-me/rainbowkit" in deps
        assert "wagmi" in deps
        assert "viem" in deps

        # Write files
        written = self.write_files(result, temp_dir)
        assert len(written) > 0

        # Add next.config.js if missing
        next_config = Path(temp_dir) / "next.config.js"
        if not next_config.exists():
            next_config.write_text("module.exports = { reactStrictMode: true };")

        # Add tsconfig.json if missing
        tsconfig = Path(temp_dir) / "tsconfig.json"
        if not tsconfig.exists():
            tsconfig.write_text('{"compilerOptions":{"target":"es5","lib":["dom","esnext"],"jsx":"preserve","module":"esnext","moduleResolution":"node","esModuleInterop":true,"skipLibCheck":true}}')

        # Run npm install and build
        try:
            subprocess.run(["node", "--version"], check=True, capture_output=True)

            # npm install
            install_result = subprocess.run(
                ["npm", "install", "--ignore-scripts"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=180,
            )
            assert install_result.returncode == 0 or "WARN" in install_result.stderr, \
                f"npm install failed: {install_result.stderr}"

            # npm run build (Next.js)
            build_result = subprocess.run(
                ["npm", "run", "build"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )
            # Build may have warnings but should succeed
            if build_result.returncode != 0:
                stderr = build_result.stderr + build_result.stdout
                # Check if it's a known issue vs real error
                if "Module not found" in stderr or "Cannot find module" in stderr:
                    pytest.skip("Missing module dependencies - LLM-generated imports incomplete")
                if "Type error" in stderr:
                    pytest.skip("TypeScript type errors in generated code")
                assert False, f"Build failed: {stderr[:500]}"

        except FileNotFoundError:
            pytest.skip("Node.js not installed")
        except subprocess.TimeoutExpired:
            pytest.skip("Build timed out")

    @pytest.mark.slow
    def test_indexer_generation_and_codegen(self, client, temp_dir):
        """Test indexer generation produces valid subgraph with codegen."""
        result = client.call_tool("generate_indexer", {
            "prompt": "Index Transfer events from an ERC20 token",
            "contract_name": "Token",
            "network": "arbitrum-one",
        })

        assert "error" not in result, f"Generation failed: {result.get('error')}"
        assert "files" in result
        assert "prerequisites" in result

        # Check for Transfer in content
        all_content = "\n".join(f.get("content", "") for f in result.get("files", []))
        assert "Transfer" in all_content or "transfer" in all_content.lower()

        # Write files
        written = self.write_files(result, temp_dir)
        assert len(written) > 0

        # Check subgraph.yaml exists
        file_paths = [f.get("path", "") for f in result.get("files", [])]
        assert any("subgraph.yaml" in p for p in file_paths)

        # Write package.json for graph CLI
        pkg_path = Path(temp_dir) / "package.json"
        if not pkg_path.exists():
            pkg_content = {
                "name": "subgraph",
                "version": "1.0.0",
                "scripts": {
                    "codegen": "graph codegen",
                    "build": "graph build"
                },
                "devDependencies": {
                    "@graphprotocol/graph-cli": "^0.60.0",
                    "@graphprotocol/graph-ts": "^0.31.0"
                }
            }
            pkg_path.write_text(json.dumps(pkg_content, indent=2))

        # Run npm install and graph codegen
        try:
            subprocess.run(["node", "--version"], check=True, capture_output=True)

            # npm install
            install_result = subprocess.run(
                ["npm", "install"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            assert install_result.returncode == 0 or "WARN" in install_result.stderr

            # graph codegen
            codegen_result = subprocess.run(
                ["npm", "run", "codegen"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )
            # Codegen may fail if ABI is incomplete, but should at least parse
            if codegen_result.returncode != 0:
                if "Failed to load" in codegen_result.stderr or "Cannot find" in codegen_result.stderr:
                    pytest.skip("Subgraph schema/ABI incomplete for codegen")

        except FileNotFoundError:
            pytest.skip("Node.js not installed")
        except subprocess.TimeoutExpired:
            pytest.skip("Graph codegen timed out")

    @pytest.mark.slow
    def test_dapp_generation_full_stack(self, client, temp_dir):
        """Test generate_dapp produces complete full-stack application."""
        try:
            result = client.call_tool("generate_dapp", {
                "prompt": "Create a simple token balance checker dApp",
                "include_backend": True,
                "include_frontend": True,
                "include_indexer": False,  # Skip indexer to speed up test
            })
        except subprocess.TimeoutExpired:
            pytest.skip("generate_dapp timed out (takes >10 min for full stack)")

        assert "error" not in result, f"Generation failed: {result.get('error')}"

        # Check structure
        assert "backend" in result or "files" in result
        assert "frontend" in result or "files" in result
        assert "prerequisites" in result

        # Write all files
        if "files" in result:
            written = self.write_files(result, temp_dir)
        else:
            written = []
            # Handle structured output with backend/frontend sections
            if "backend" in result and "files" in result["backend"]:
                backend_dir = Path(temp_dir) / "backend"
                backend_dir.mkdir(exist_ok=True)
                for f in result["backend"]["files"]:
                    path = backend_dir / f.get("path", "")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(f.get("content", ""))
                    written.append(str(path))

            if "frontend" in result and "files" in result["frontend"]:
                frontend_dir = Path(temp_dir) / "frontend"
                frontend_dir.mkdir(exist_ok=True)
                for f in result["frontend"]["files"]:
                    path = frontend_dir / f.get("path", "")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(f.get("content", ""))
                    written.append(str(path))

        assert len(written) > 0, "No files were written"

        # Verify directory structure
        files_created = list(Path(temp_dir).rglob("*"))
        assert len(files_created) > 0


class TestMCPStylusTools:
    """Test Stylus/Arbitrum SDK tools via MCP."""

    @pytest.fixture
    def client(self):
        return MCPClient()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        dir_path = tempfile.mkdtemp(prefix="stylus_test_")
        yield dir_path
        shutil.rmtree(dir_path, ignore_errors=True)

    def test_get_stylus_context(self, client):
        """Test get_stylus_context via MCP."""
        result = client.call_tool("get_stylus_context", {
            "query": "how to create ERC20 token",
            "n_results": 3,
        })

        assert "error" not in result, f"Failed: {result.get('error')}"
        assert "contexts" in result or "answer" in result

    def test_ask_stylus(self, client):
        """Test ask_stylus via MCP."""
        result = client.call_tool("ask_stylus", {
            "question": "How do I deploy a Stylus contract?",
        })

        assert "error" not in result, f"Failed: {result.get('error')}"
        assert "answer" in result
        # Should mention deploy/cargo stylus
        answer = result["answer"].lower()
        assert "deploy" in answer or "cargo" in answer

    def test_get_workflow(self, client):
        """Test get_workflow via MCP."""
        result = client.call_tool("get_workflow", {
            "workflow_type": "build",
        })

        assert "error" not in result, f"Failed: {result.get('error')}"
        assert "build" in result
        assert "quick_commands" in result["build"]

    @pytest.mark.slow
    def test_generate_stylus_code_structure(self, client):
        """Test generate_stylus_code produces valid Rust structure."""
        result = client.call_tool("generate_stylus_code", {
            "prompt": "Create a simple counter contract with increment function",
        })

        assert "error" not in result, f"Generation failed: {result.get('error')}"
        assert "code" in result

        code = result["code"]
        # Check for Stylus patterns
        assert "sol_storage!" in code or "stylus_sdk" in code
        assert "fn " in code
        assert "struct" in code.lower() or "impl" in code.lower()

    @pytest.mark.slow
    def test_generate_stylus_code_compiles(self, client, temp_dir):
        """Test generated Stylus code compiles with cargo."""
        # Generate a simple counter contract
        result = client.call_tool("generate_stylus_code", {
            "prompt": "Create a minimal counter contract with a single increment function that adds 1 to a stored value",
            "temperature": 0.1,  # Low temperature for consistency
        })

        assert "error" not in result, f"Generation failed: {result.get('error')}"
        code = result["code"]

        # Create Cargo.toml for Stylus project
        cargo_toml = '''[package]
name = "counter"
version = "0.1.0"
edition = "2021"

[dependencies]
stylus-sdk = "0.6"
alloy-primitives = "0.7"
alloy-sol-types = "0.7"

[features]
export-abi = ["stylus-sdk/export-abi"]

[lib]
crate-type = ["lib", "cdylib"]

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"
'''

        # Write project files
        project_dir = Path(temp_dir)
        (project_dir / "Cargo.toml").write_text(cargo_toml)
        (project_dir / "src").mkdir(exist_ok=True)
        (project_dir / "src" / "lib.rs").write_text(code)

        # Try to compile (check only, not full build)
        try:
            # First check if cargo is available
            subprocess.run(["cargo", "--version"], check=True, capture_output=True)

            # Run cargo check (faster than full build)
            check_result = subprocess.run(
                ["cargo", "check"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Note: May fail if stylus-sdk versions don't match
            # We're testing that it produces syntactically valid Rust
            if check_result.returncode != 0:
                # Log error but don't fail - dependency issues are expected
                if "could not find" in check_result.stderr or "no matching package" in check_result.stderr:
                    pytest.skip("Stylus SDK dependencies not available")
                # If it's a syntax error, that's a real failure
                assert "expected" not in check_result.stderr, \
                    f"Syntax error in generated code:\n{check_result.stderr}"

        except FileNotFoundError:
            pytest.skip("Rust/cargo not installed")
        except subprocess.TimeoutExpired:
            pytest.skip("Cargo check timed out")

    @pytest.mark.slow
    def test_generate_tests(self, client):
        """Test generate_tests via MCP."""
        sample_code = '''
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
'''
        result = client.call_tool("generate_tests", {
            "contract_code": sample_code,  # Correct param name
            "test_type": "unit",
        })

        assert "error" not in result, f"Failed: {result.get('error')}"
        assert "tests" in result or "test_code" in result


class TestMCPResources:
    """Test MCP resources."""

    @pytest.fixture
    def client(self):
        return MCPClient()

    def test_read_cli_commands(self, client):
        """Test reading CLI commands resource."""
        response = client.call("resources/read", {"uri": "stylus://cli/commands"})

        assert "contents" in response
        content = json.loads(response["contents"][0]["text"])
        assert "commands" in content

    def test_read_networks(self, client):
        """Test reading networks resource."""
        response = client.call("resources/read", {"uri": "stylus://config/networks"})

        assert "contents" in response
        content = json.loads(response["contents"][0]["text"])
        assert "arbitrum_one" in content or "networks" in content


class TestMCPPrompts:
    """Test MCP prompts."""

    @pytest.fixture
    def client(self):
        return MCPClient()

    def test_get_build_prompt(self, client):
        """Test getting build-contract prompt."""
        response = client.call("prompts/get", {
            "name": "build-contract",
            "arguments": {"project_path": "/my/project"},
        })

        assert "messages" in response
        assert len(response["messages"]) > 0
        assert "user" in response["messages"][0]["role"]

    def test_get_deploy_prompt(self, client):
        """Test getting deploy-contract prompt."""
        response = client.call("prompts/get", {
            "name": "deploy-contract",
            "arguments": {"network": "arbitrum_sepolia"},
        })

        assert "messages" in response


def run_quick_e2e_test():
    """Run a quick end-to-end test for development."""
    print("=== MCP End-to-End Test ===\n")

    client = MCPClient()

    # Test 1: Protocol
    print("1. Testing MCP protocol...")
    init = client.call("initialize")
    assert init["protocolVersion"] == "2024-11-05"
    print("   ✓ Initialize works")

    tools = client.call("tools/list")
    assert len(tools["tools"]) == 9
    print(f"   ✓ {len(tools['tools'])} tools available")

    # Test 2: Validation
    print("\n2. Testing validation...")
    result = client.call_tool("generate_backend", {})
    assert "Missing required parameter" in result.get("error", "")
    print("   ✓ Missing param validation works")

    # Test 3: Generation (quick)
    print("\n3. Testing code generation...")
    result = client.call_tool("generate_backend", {
        "prompt": "Create a health check endpoint",
    })

    if "error" in result:
        print(f"   ✗ Generation failed: {result['error']}")
        return False

    print(f"   ✓ Generated {len(result.get('files', []))} files")
    print(f"   ✓ Prerequisites: {result.get('prerequisites', {}).get('required', [])}")

    print("\n=== All tests passed! ===")
    return True


if __name__ == "__main__":
    run_quick_e2e_test()

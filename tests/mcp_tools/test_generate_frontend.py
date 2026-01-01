"""
Test cases for generate_frontend MCP tool.

Tests frontend code generation for Next.js with wallet integration.
"""

import pytest
import re


GENERATE_FRONTEND_TEST_CASES = [
    # ===== Next.js with RainbowKit (P0) =====
    {
        "id": "frontend_rainbowkit_001",
        "name": "RainbowKit: basic wallet connection",
        "input": {
            "prompt": "Create a Next.js app with wallet connection using RainbowKit",
            "wallet_kit": "rainbowkit",
            "ui_library": "daisyui",
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"RainbowKitProvider|@rainbow-me/rainbowkit",
                r"WagmiProvider|wagmi",
                r"ConnectButton",
            ],
            "must_have_keywords": ["use client", "provider"],
            "has_package_json": True,
            "package_has_deps": ["@rainbow-me/rainbowkit", "wagmi", "viem"],
        },
        "priority": "P0",
        "category": "rainbowkit",
    },
    {
        "id": "frontend_rainbowkit_002",
        "name": "RainbowKit: with contract read",
        "input": {
            "prompt": "Create a page that displays the user's token balance from a contract",
            "wallet_kit": "rainbowkit",
            "features": ["wallet", "contract-read"],
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"useReadContract|useContractRead",
                r"useAccount",
            ],
        },
        "priority": "P0",
        "category": "rainbowkit",
    },

    # ===== wagmi Hooks (P0) =====
    {
        "id": "frontend_wagmi_001",
        "name": "wagmi: useAccount hook",
        "input": {
            "prompt": "Create a component that shows connected wallet address and balance",
            "wallet_kit": "rainbowkit",
            "features": ["wallet"],
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"useAccount",
                r"address|isConnected",
            ],
        },
        "priority": "P0",
        "category": "wagmi",
    },
    {
        "id": "frontend_wagmi_002",
        "name": "wagmi: contract write with transaction",
        "input": {
            "prompt": "Create a form to mint NFTs with transaction confirmation",
            "wallet_kit": "rainbowkit",
            "features": ["wallet", "contract-write"],
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"useWriteContract|useContractWrite",
                r"useWaitForTransactionReceipt|waitForTransaction",
            ],
            "must_have_keywords": ["mint", "transaction"],
        },
        "priority": "P0",
        "category": "wagmi",
    },

    # ===== DaisyUI Components (P0) =====
    {
        "id": "frontend_daisyui_001",
        "name": "DaisyUI: button and card components",
        "input": {
            "prompt": "Create a token transfer form with input field, button, and card layout",
            "wallet_kit": "rainbowkit",
            "ui_library": "daisyui",
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"btn|btn-primary|btn-secondary",
                r"card|input|form-control",
            ],
        },
        "priority": "P0",
        "category": "daisyui",
    },
    {
        "id": "frontend_daisyui_002",
        "name": "DaisyUI: dark theme support",
        "input": {
            "prompt": "Create a navbar with theme toggle for dark/light mode",
            "ui_library": "daisyui",
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"data-theme|theme",
                r"navbar",
            ],
        },
        "priority": "P1",
        "category": "daisyui",
    },

    # ===== Network Configuration (P0) =====
    {
        "id": "frontend_network_001",
        "name": "Network: Arbitrum chain config",
        "input": {
            "prompt": "Create a dApp configured for Arbitrum One and Arbitrum Sepolia",
            "wallet_kit": "rainbowkit",
            "networks": ["arbitrum_one", "arbitrum_sepolia"],
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"arbitrum|arbitrumSepolia",
                r"chains|chain",
            ],
        },
        "priority": "P0",
        "category": "network",
    },

    # ===== App Router Structure (P0) =====
    {
        "id": "frontend_structure_001",
        "name": "Structure: Next.js App Router layout",
        "input": {
            "prompt": "Create a Next.js app with proper layout, providers, and a homepage",
            "wallet_kit": "rainbowkit",
        },
        "expected": {
            "has_files": True,
            "file_paths_contain": ["layout", "provider", "page"],
            "must_have_patterns": [
                r"export\s+default\s+function",
                r"children",
            ],
        },
        "priority": "P0",
        "category": "structure",
    },

    # ===== Contract Hooks (P1) =====
    {
        "id": "frontend_hooks_001",
        "name": "Hooks: custom contract hook",
        "input": {
            "prompt": "Create a custom hook for interacting with an ERC20 token",
            "wallet_kit": "rainbowkit",
            "features": ["contract-read", "contract-write"],
            "contract_abi": '[{"type":"function","name":"transfer","inputs":[{"name":"to","type":"address"},{"name":"amount","type":"uint256"}]}]',
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"function\s+use\w+|const\s+use\w+",
                r"parseAbi|abi",
            ],
        },
        "priority": "P1",
        "category": "hooks",
    },

    # ===== Error Handling (P0) =====
    {
        "id": "frontend_error_001",
        "name": "Error: empty prompt",
        "input": {
            "prompt": "",
            "wallet_kit": "rainbowkit",
        },
        "expected": {
            "should_error": True,
            "error_contains": "prompt",
        },
        "priority": "P0",
        "category": "error_handling",
    },
    {
        "id": "frontend_error_002",
        "name": "Error: invalid wallet kit defaults",
        "input": {
            "prompt": "Create a wallet connection page",
            "wallet_kit": "invalid_kit",
        },
        "expected": {
            "should_warn": True,
            "has_files": True,  # Should still generate with default
        },
        "priority": "P1",
        "category": "error_handling",
    },

    # ===== Complex Scenarios (P1) =====
    {
        "id": "frontend_complex_001",
        "name": "Complex: NFT gallery with minting",
        "input": {
            "prompt": "Create an NFT gallery page that displays owned NFTs and allows minting new ones",
            "wallet_kit": "rainbowkit",
            "ui_library": "daisyui",
            "features": ["wallet", "contract-read", "contract-write"],
        },
        "expected": {
            "has_files": True,
            "must_have_keywords": ["nft", "mint", "gallery"],
        },
        "priority": "P1",
        "category": "complex",
    },
    {
        "id": "frontend_complex_002",
        "name": "Complex: token swap interface",
        "input": {
            "prompt": "Create a token swap interface with input/output token selection and swap button",
            "wallet_kit": "rainbowkit",
            "ui_library": "daisyui",
        },
        "expected": {
            "has_files": True,
            "must_have_keywords": ["swap", "token"],
        },
        "priority": "P1",
        "category": "complex",
    },
]


class TestGenerateFrontend:
    """Test suite for generate_frontend tool."""

    @pytest.fixture
    def tool(self):
        """Initialize the tool for testing."""
        from src.mcp.tools import GenerateFrontendTool
        return GenerateFrontendTool()

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GENERATE_FRONTEND_TEST_CASES if tc["priority"] == "P0"],
        ids=lambda tc: tc["id"],
    )
    def test_p0_cases(self, tool, test_case):
        """Test P0 (critical) test cases."""
        result = tool.execute(**test_case["input"])
        self._validate_result(result, test_case["expected"])

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GENERATE_FRONTEND_TEST_CASES if tc["priority"] == "P1"],
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
            assert "error" in result, f"Expected error but got: {result}"
            if "error_contains" in expected:
                assert expected["error_contains"] in result["error"].lower()
            return

        # Should not have errors if not expected
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

        # Check for warnings
        if expected.get("should_warn"):
            assert "warnings" in result and len(result["warnings"]) > 0

        # Check files were generated
        if expected.get("has_files"):
            files = result.get("files", [])
            assert len(files) > 0, "No files generated"

            # Combine all file contents for pattern matching
            all_content = "\n".join(f.get("content", "") for f in files)
            all_paths = [f.get("path", "") for f in files]

            # Check file paths contain expected elements
            if "file_paths_contain" in expected:
                paths_lower = " ".join(all_paths).lower()
                for expected_path in expected["file_paths_contain"]:
                    assert expected_path.lower() in paths_lower, \
                        f"Missing file path containing: {expected_path}"

            # Check must-have patterns
            if "must_have_patterns" in expected:
                for pattern in expected["must_have_patterns"]:
                    assert re.search(pattern, all_content, re.IGNORECASE), \
                        f"Missing pattern: {pattern}"

            # Check must-have keywords
            if "must_have_keywords" in expected:
                content_lower = all_content.lower()
                for keyword in expected["must_have_keywords"]:
                    assert keyword.lower() in content_lower, \
                        f"Missing keyword: {keyword}"

        # Check package.json
        if expected.get("has_package_json"):
            package_json = result.get("package_json", {})
            assert package_json, "No package.json generated"

            if "package_has_deps" in expected:
                deps = package_json.get("dependencies", {})
                dev_deps = package_json.get("devDependencies", {})
                all_deps = {**deps, **dev_deps}

                for dep in expected["package_has_deps"]:
                    assert dep in all_deps, f"Missing dependency: {dep}"


def analyze_frontend_quality(result: dict) -> dict:
    """Analyze generated frontend code quality metrics."""
    files = result.get("files", [])
    all_content = "\n".join(f.get("content", "") for f in files)

    return {
        "file_count": len(files),
        "total_lines": len(all_content.split("\n")),
        "has_wallet_integration": bool(re.search(r"wagmi|useAccount|ConnectButton", all_content, re.I)),
        "has_client_directive": bool(re.search(r"use client", all_content)),
        "has_typescript": bool(re.search(r":\s*(React\.|string|number|boolean)", all_content)),
        "has_tailwind": bool(re.search(r"className=", all_content)),
        "has_daisyui": bool(re.search(r"btn|card|modal|navbar", all_content)),
        "component_count": len(re.findall(r"function\s+\w+\s*\(|const\s+\w+\s*=\s*\(", all_content)),
        "hook_count": len(re.findall(r"use[A-Z]\w+", all_content)),
    }

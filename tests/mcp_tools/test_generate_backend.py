"""
Test cases for generate_backend MCP tool.

Tests backend code generation for NestJS and Express with Web3 integration.
"""

import pytest
import re


GENERATE_BACKEND_TEST_CASES = [
    # ===== NestJS Generation (P0) =====
    {
        "id": "backend_nestjs_001",
        "name": "NestJS: basic API with Web3",
        "input": {
            "prompt": "Create a NestJS backend with a token balance endpoint that reads from an ERC20 contract",
            "framework": "nestjs",
            "features": ["api", "web3"],
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"@Controller|@Injectable|@Module",
                r"viem|ethers",
                r"class\s+\w+Service",
            ],
            "must_have_keywords": ["import", "export", "async"],
            "has_package_json": True,
            "package_has_deps": ["@nestjs/common", "viem"],
        },
        "priority": "P0",
        "category": "nestjs",
    },
    {
        "id": "backend_nestjs_002",
        "name": "NestJS: with PostgreSQL database",
        "input": {
            "prompt": "Create a backend to store user wallet addresses and transaction history",
            "framework": "nestjs",
            "features": ["api", "web3", "database"],
            "database": "postgresql",
        },
        "expected": {
            "has_files": True,
            "must_have_keywords": ["prisma", "database"],
            "package_has_deps": ["@prisma/client"],
        },
        "priority": "P0",
        "category": "nestjs",
    },
    {
        "id": "backend_nestjs_003",
        "name": "NestJS: contract interaction service",
        "input": {
            "prompt": "Create a service that mints NFTs by calling a smart contract",
            "framework": "nestjs",
            "features": ["web3"],
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"writeContract|sendTransaction",
                r"async\s+\w*mint",
            ],
        },
        "priority": "P0",
        "category": "nestjs",
    },

    # ===== Express Generation (P0) =====
    {
        "id": "backend_express_001",
        "name": "Express: basic API with Web3",
        "input": {
            "prompt": "Create an Express backend with endpoints to read token balances",
            "framework": "express",
            "features": ["api", "web3"],
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"express\(\)|Router\(\)",
                r"app\.get|router\.get",
                r"viem|ethers",
            ],
            "has_package_json": True,
            "package_has_deps": ["express", "viem"],
        },
        "priority": "P0",
        "category": "express",
    },
    {
        "id": "backend_express_002",
        "name": "Express: middleware and routes",
        "input": {
            "prompt": "Create an Express API with authentication middleware for protected endpoints",
            "framework": "express",
            "features": ["api", "auth"],
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"middleware|Middleware",
                r"req,\s*res|request,\s*response",
            ],
            "must_have_keywords": ["jwt", "auth", "token"],
        },
        "priority": "P0",
        "category": "express",
    },

    # ===== Web3 Integration (P0) =====
    {
        "id": "backend_web3_001",
        "name": "Web3: viem client setup",
        "input": {
            "prompt": "Create a Web3 service for Arbitrum with read and write capabilities",
            "framework": "nestjs",
            "features": ["web3"],
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"createPublicClient|createWalletClient",
                r"arbitrum|arbitrumSepolia",
                r"http\(",
            ],
        },
        "priority": "P0",
        "category": "web3",
    },
    {
        "id": "backend_web3_002",
        "name": "Web3: contract ABI integration",
        "input": {
            "prompt": "Create a service to interact with an ERC20 token contract",
            "framework": "nestjs",
            "features": ["web3"],
            "contract_abi": '[{"type":"function","name":"balanceOf","inputs":[{"name":"account","type":"address"}],"outputs":[{"type":"uint256"}]}]',
        },
        "expected": {
            "has_files": True,
            "must_have_patterns": [
                r"balanceOf|balance_of",
                r"address|Address",
            ],
        },
        "priority": "P0",
        "category": "web3",
    },

    # ===== Error Handling (P1) =====
    {
        "id": "backend_error_001",
        "name": "Error: empty prompt",
        "input": {
            "prompt": "",
            "framework": "nestjs",
        },
        "expected": {
            "should_error": True,
            "error_contains": "prompt",
        },
        "priority": "P0",
        "category": "error_handling",
    },
    {
        "id": "backend_error_002",
        "name": "Error: invalid framework defaults to nestjs",
        "input": {
            "prompt": "Create a backend API",
            "framework": "invalid_framework",
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
        "id": "backend_complex_001",
        "name": "Complex: full CRUD API",
        "input": {
            "prompt": "Create a complete CRUD API for managing NFT metadata with PostgreSQL storage",
            "framework": "nestjs",
            "features": ["api", "web3", "database"],
            "database": "postgresql",
        },
        "expected": {
            "has_files": True,
            "must_have_keywords": ["create", "get", "update", "delete"],
        },
        "priority": "P1",
        "category": "complex",
    },
]


class TestGenerateBackend:
    """Test suite for generate_backend tool."""

    @pytest.fixture
    def tool(self):
        """Initialize the tool for testing."""
        from src.mcp.tools import GenerateBackendTool
        return GenerateBackendTool()

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GENERATE_BACKEND_TEST_CASES if tc["priority"] == "P0"],
        ids=lambda tc: tc["id"],
    )
    def test_p0_cases(self, tool, test_case):
        """Test P0 (critical) test cases."""
        result = tool.execute(**test_case["input"])
        self._validate_result(result, test_case["expected"])

    @pytest.mark.parametrize(
        "test_case",
        [tc for tc in GENERATE_BACKEND_TEST_CASES if tc["priority"] == "P1"],
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


def analyze_backend_quality(result: dict) -> dict:
    """Analyze generated backend code quality metrics."""
    files = result.get("files", [])
    all_content = "\n".join(f.get("content", "") for f in files)

    return {
        "file_count": len(files),
        "total_lines": len(all_content.split("\n")),
        "has_web3_service": bool(re.search(r"web3|Web3|viem|ethers", all_content, re.I)),
        "has_error_handling": bool(re.search(r"try\s*{|catch\s*\(|throw", all_content)),
        "has_typescript": bool(re.search(r":\s*(string|number|boolean|Promise)", all_content)),
        "has_async_await": bool(re.search(r"async\s+\w+|await\s+", all_content)),
        "has_env_config": bool(re.search(r"process\.env|ConfigService", all_content)),
        "controller_count": len(re.findall(r"@Controller|router\.", all_content, re.I)),
        "service_count": len(re.findall(r"@Injectable|Service", all_content)),
    }

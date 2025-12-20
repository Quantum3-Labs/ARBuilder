"""
generate_tests MCP Tool.

Generates test cases for Stylus smart contracts.
"""

import re
from typing import Optional

from .base import BaseTool


SYSTEM_PROMPT = """You are an expert at writing tests for Stylus smart contracts. You write comprehensive, well-structured tests that cover:

1. Happy path scenarios (normal operation)
2. Error cases (invalid inputs, unauthorized access)
3. Edge cases (zero values, max values, boundary conditions)
4. State transitions (before/after comparisons)

For Rust native tests:
- Use #[cfg(test)] module
- Use #[test] attribute for test functions
- Use assert!, assert_eq!, assert_ne! macros
- Mock contract state appropriately
- Test each public function
- Include descriptive test names

Test naming convention: test_<function>_<scenario>
Example: test_transfer_insufficient_balance

Best practices:
- One assertion per test when possible
- Descriptive error messages in assertions
- Test both success and failure paths
- Consider reentrancy and other security tests
"""

FOUNDRY_TEMPLATE = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

contract {contract_name}Test is Test {{
    // Contract instance
    // Add setup and tests here
}}
"""


class GenerateTestsTool(BaseTool):
    """
    Generates test cases for Stylus smart contracts.

    Supports Rust native tests and Foundry tests.
    """

    def execute(
        self,
        contract_code: str,
        test_framework: str = "rust_native",
        test_types: Optional[list[str]] = None,
        coverage_focus: Optional[list[str]] = None,
        **kwargs,
    ) -> dict:
        """
        Generate tests for a Stylus contract.

        Args:
            contract_code: The contract code to generate tests for.
            test_framework: Test framework (rust_native, foundry, hardhat).
            test_types: Types of tests (unit, integration, fuzz).
            coverage_focus: Specific functions to focus on.

        Returns:
            Dict with tests, test_summary, coverage_estimate, setup_instructions.
        """
        # Validate input
        if not contract_code or not contract_code.strip():
            return {"error": "Contract code is required and cannot be empty"}

        contract_code = contract_code.strip()
        test_types = test_types or ["unit"]

        # Validate contract has basic structure
        if not self._is_valid_contract(contract_code):
            return {
                "error": "Invalid contract code. Please provide valid Stylus/Rust code with struct and impl blocks.",
                "warnings": ["Could not parse contract structure"],
            }

        try:
            # Extract contract info
            contract_info = self._analyze_contract(contract_code)

            # Filter functions if coverage_focus specified
            if coverage_focus:
                contract_info["functions"] = [
                    f for f in contract_info["functions"]
                    if any(focus.lower() in f["name"].lower() for focus in coverage_focus)
                ]

            # Generate tests based on framework
            if test_framework == "foundry":
                tests = self._generate_foundry_tests(contract_info)
                setup = self._get_foundry_setup()
            else:
                tests = self._generate_rust_tests(contract_info, test_types)
                setup = self._get_rust_setup()

            # Generate summary
            test_summary = self._generate_summary(tests, test_types)

            # Generate coverage estimate
            coverage_estimate = self._estimate_coverage(contract_info, tests)

            return {
                "tests": tests,
                "test_summary": test_summary,
                "coverage_estimate": coverage_estimate,
                "setup_instructions": setup,
            }

        except Exception as e:
            return {"error": f"Test generation failed: {str(e)}"}

    def _is_valid_contract(self, code: str) -> bool:
        """Check if code has basic contract structure."""
        # Very basic validation
        has_struct = "struct" in code.lower()
        has_fn = "fn " in code
        return has_struct or has_fn

    def _analyze_contract(self, code: str) -> dict:
        """Analyze contract to extract structure."""
        info = {
            "name": "Contract",
            "functions": [],
            "storage_fields": [],
        }

        # Extract struct name
        struct_match = re.search(r"pub\s+struct\s+(\w+)", code)
        if struct_match:
            info["name"] = struct_match.group(1)

        # Extract public functions
        fn_pattern = r"pub\s+fn\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^{]+))?"
        for match in re.finditer(fn_pattern, code):
            fn_name = match.group(1)
            params = match.group(2).strip()
            return_type = match.group(3).strip() if match.group(3) else "void"

            # Parse parameters
            param_list = []
            if params and params != "&self" and params != "&mut self":
                for p in params.split(","):
                    p = p.strip()
                    if p and p not in ["&self", "&mut self"]:
                        param_list.append(p)

            # Determine if mutating
            is_mut = "&mut self" in params

            info["functions"].append({
                "name": fn_name,
                "params": param_list,
                "return_type": return_type.strip(),
                "is_mut": is_mut,
            })

        # Extract storage fields from sol_storage! macro
        storage_pattern = r"sol_storage!\s*\{[\s\S]*?\}"
        storage_match = re.search(storage_pattern, code)
        if storage_match:
            storage_block = storage_match.group(0)
            # Simple field extraction
            field_pattern = r"(\w+)\s+(\w+);"
            for field_match in re.finditer(field_pattern, storage_block):
                info["storage_fields"].append({
                    "type": field_match.group(1),
                    "name": field_match.group(2),
                })

        return info

    def _generate_rust_tests(self, contract_info: dict, test_types: list[str]) -> str:
        """Generate Rust native tests."""
        parts = []

        # Test module header
        parts.append("#[cfg(test)]")
        parts.append("mod tests {")
        parts.append("    use super::*;")
        parts.append("")

        # Helper function to create contract instance
        parts.append("    fn setup() -> {} {{".format(contract_info["name"]))
        parts.append("        // Initialize contract for testing")
        parts.append("        {}::default()".format(contract_info["name"]))
        parts.append("    }")
        parts.append("")

        # Generate tests for each function
        for fn in contract_info["functions"]:
            fn_tests = self._generate_function_tests(fn, contract_info["name"], test_types)
            parts.extend(fn_tests)

        parts.append("}")

        return "\n".join(parts)

    def _generate_function_tests(
        self,
        fn: dict,
        contract_name: str,
        test_types: list[str],
    ) -> list[str]:
        """Generate tests for a single function."""
        tests = []
        fn_name = fn["name"]

        # Skip internal functions
        if fn_name.startswith("_"):
            return tests

        # Unit tests
        if "unit" in test_types:
            # Happy path test
            tests.append(f"    #[test]")
            tests.append(f"    fn test_{fn_name}_success() {{")
            tests.append(f"        let {'mut ' if fn['is_mut'] else ''}contract = setup();")
            tests.append(f"        // TODO: Setup test preconditions")
            tests.append(f"        ")

            if fn["params"]:
                params_str = ", ".join([f"/* {p} */" for p in fn["params"]])
                tests.append(f"        // Call: contract.{fn_name}({params_str});")
            else:
                tests.append(f"        // Call: contract.{fn_name}();")

            tests.append(f"        ")
            tests.append(f"        // TODO: Assert expected outcomes")
            tests.append(f"        // assert_eq!(result, expected);")
            tests.append(f"    }}")
            tests.append("")

            # Error case test if function might fail
            if fn["is_mut"] or "Result" in fn["return_type"] or fn["params"]:
                tests.append(f"    #[test]")
                tests.append(f"    fn test_{fn_name}_error_case() {{")
                tests.append(f"        let {'mut ' if fn['is_mut'] else ''}contract = setup();")
                tests.append(f"        // TODO: Setup conditions that should cause failure")
                tests.append(f"        ")
                tests.append(f"        // TODO: Assert error is returned or state unchanged")
                tests.append(f"    }}")
                tests.append("")

        # Edge case tests
        if "unit" in test_types and fn["params"]:
            tests.append(f"    #[test]")
            tests.append(f"    fn test_{fn_name}_edge_cases() {{")
            tests.append(f"        let {'mut ' if fn['is_mut'] else ''}contract = setup();")
            tests.append(f"        ")
            tests.append(f"        // Test with zero values")
            tests.append(f"        // Test with max values")
            tests.append(f"        // Test with boundary conditions")
            tests.append(f"    }}")
            tests.append("")

        # Fuzz tests
        if "fuzz" in test_types:
            tests.append(f"    // Fuzz test for {fn_name}")
            tests.append(f"    // #[test]")
            tests.append(f"    // fn test_{fn_name}_fuzz() {{")
            tests.append(f"    //     use proptest::prelude::*;")
            tests.append(f"    //     proptest!(|(input: /* type */)| {{")
            tests.append(f"    //         // Test property invariants")
            tests.append(f"    //     }});")
            tests.append(f"    // }}")
            tests.append("")

        return tests

    def _generate_foundry_tests(self, contract_info: dict) -> str:
        """Generate Foundry/Solidity tests."""
        contract_name = contract_info["name"]

        parts = [
            "// SPDX-License-Identifier: MIT",
            "pragma solidity ^0.8.0;",
            "",
            'import "forge-std/Test.sol";',
            "",
            f"interface I{contract_name} {{",
        ]

        # Add interface functions
        for fn in contract_info["functions"]:
            # Convert to Solidity signature
            sol_params = self._rust_to_sol_params(fn["params"])
            sol_return = self._rust_to_sol_type(fn["return_type"])
            view_modifier = " view" if not fn["is_mut"] else ""

            parts.append(f"    function {fn['name']}({sol_params}) external{view_modifier} returns ({sol_return});")

        parts.append("}")
        parts.append("")
        parts.append(f"contract {contract_name}Test is Test {{")
        parts.append(f"    I{contract_name} public contractInstance;")
        parts.append("")
        parts.append("    function setUp() public {")
        parts.append("        // Deploy or get contract address")
        parts.append("        // contractInstance = I{}(address);".format(contract_name))
        parts.append("    }")
        parts.append("")

        # Generate test functions
        for fn in contract_info["functions"]:
            parts.append(f"    function test_{fn['name']}_Success() public {{")
            parts.append("        // Arrange")
            parts.append("        // Act")
            parts.append("        // Assert")
            parts.append("    }")
            parts.append("")

        parts.append("}")

        return "\n".join(parts)

    def _rust_to_sol_params(self, params: list[str]) -> str:
        """Convert Rust params to Solidity."""
        if not params:
            return ""

        sol_params = []
        for p in params:
            # Simple conversion
            if "Address" in p or "address" in p:
                sol_params.append("address")
            elif "U256" in p or "uint256" in p:
                sol_params.append("uint256")
            elif "bool" in p:
                sol_params.append("bool")
            else:
                sol_params.append("bytes memory")

        return ", ".join(sol_params)

    def _rust_to_sol_type(self, rust_type: str) -> str:
        """Convert Rust return type to Solidity."""
        if "bool" in rust_type.lower():
            return "bool"
        elif "U256" in rust_type or "uint" in rust_type.lower():
            return "uint256"
        elif "Address" in rust_type:
            return "address"
        elif "String" in rust_type:
            return "string memory"
        elif "void" in rust_type or not rust_type:
            return ""
        else:
            return "bytes memory"

    def _generate_summary(self, tests: str, test_types: list[str]) -> dict:
        """Generate test summary."""
        test_count = tests.count("#[test]")
        if "#[test]" not in tests:
            # Foundry tests
            test_count = tests.count("function test_")

        return {
            "total_tests": test_count,
            "unit_tests": test_count if "unit" in test_types else 0,
            "integration_tests": 0,  # Not generated yet
            "fuzz_tests": tests.count("proptest") if "fuzz" in test_types else 0,
        }

    def _estimate_coverage(self, contract_info: dict, tests: str) -> dict:
        """Estimate test coverage."""
        all_functions = [f["name"] for f in contract_info["functions"]]

        covered = []
        not_covered = []

        for fn_name in all_functions:
            if f"test_{fn_name}" in tests:
                covered.append(fn_name)
            else:
                not_covered.append(fn_name)

        edge_cases = []
        if "_edge_cases" in tests or "_error" in tests:
            edge_cases.append("Error conditions")
        if "zero" in tests.lower():
            edge_cases.append("Zero value handling")
        if "max" in tests.lower():
            edge_cases.append("Maximum value handling")

        return {
            "functions_covered": covered,
            "functions_not_covered": not_covered,
            "edge_cases": edge_cases,
        }

    def _get_rust_setup(self) -> str:
        """Get Rust test setup instructions."""
        return """# Running Rust Tests

1. Ensure your Cargo.toml has test dependencies:
```toml
[dev-dependencies]
# Add any test dependencies
```

2. Run tests:
```bash
cargo test
```

3. Run with output:
```bash
cargo test -- --nocapture
```

4. Run specific test:
```bash
cargo test test_function_name
```
"""

    def _get_foundry_setup(self) -> str:
        """Get Foundry test setup instructions."""
        return """# Running Foundry Tests

1. Install Foundry:
```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

2. Initialize project (if needed):
```bash
forge init
```

3. Run tests:
```bash
forge test
```

4. Run with verbosity:
```bash
forge test -vvv
```

5. Run specific test:
```bash
forge test --match-test test_function_name
```
"""

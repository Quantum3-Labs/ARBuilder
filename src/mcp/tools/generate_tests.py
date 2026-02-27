"""
generate_tests MCP Tool.

Generates test cases for Stylus smart contracts using LLM.
"""

import logging
import re
from typing import Optional

from .base import BaseTool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_RUST = """\
You are a Stylus testing expert for SDK 0.10.0.
Generate comprehensive tests for the provided contract.
Framework: Rust native #[test] with stylus-test

For Rust native tests (stylus-sdk 0.10.0):
- Use #[cfg(test)] module with `use super::*;` and `use stylus_sdk::testing::*;`
- SETUP: `let vm = TestVM::default(); let mut contract = MyContract::from(&vm);`
  Do NOT use MyContract::default() — it does not exist in SDK 0.10.0.
- Use vm.set_sender(addr) to set msg.sender for tests
- Use vm.set_value(amount) to set msg.value for payable tests
- Use vm.set_block_timestamp(ts) to set block.timestamp
- Use #[test] attribute for test functions
- Use assert!, assert_eq!, assert_ne! macros with descriptive messages
- Test each public function

Test naming convention: test_<function>_<scenario>
Example: test_transfer_insufficient_balance

Best practices:
- One assertion per test when possible
- Descriptive error messages in assertions
- Test both success and failure paths
- Consider reentrancy and other security tests

STORAGE ACCESS: ALWAYS use .get() to read: `self.field.get()` NOT `self.field`. \
Use .set() to write. For mappings: `self.map.get(key)` and \
`self.map.setter(key).set(val)`.

EVENT CHECKING: Use `vm.get_emitted_logs()` to get emitted events. \
Do NOT use `vm.logs()` — it does not exist. \
The return type is `Vec<(Vec<B256>, Vec<u8>)>` where each tuple is (topics, data). \
Do NOT use a `Log` type or `.data` field — these don't exist in stylus-test. \
Example: `let logs = vm.get_emitted_logs(); assert_eq!(logs.len(), 1);`

ZERO CONSTANTS: Use `U256::ZERO`, `Address::ZERO` (uppercase). \
Do NOT use `U256::zero()` or `Address::zero()` — they don't exist.

Cargo.toml needs:
[dev-dependencies]
stylus-sdk = { version = "0.10.0", features = ["stylus-test"] }

IMPORTANT — TEST COMPILATION:
- Run tests with `--target` flag (tests run on host, not WASM): \
`cargo test --target=x86_64-unknown-linux-gnu` (Linux) or \
`cargo test --target=aarch64-apple-darwin` (macOS Apple Silicon)
- Do NOT run `cargo test` without `--target` — it compiles for \
wasm32-unknown-unknown which cannot run unit tests
- If you get alloy-consensus or alloy-* version conflicts, add \
`[patch.crates-io]` or pin alloy versions in workspace Cargo.toml

Return ONLY the test code inside a ```rust code block. No explanations."""

SYSTEM_PROMPT_FOUNDRY = """\
You are a Stylus testing expert.
Generate comprehensive Foundry/Solidity tests for the provided Stylus contract.
Framework: Foundry Solidity tests

- Create a Solidity interface matching the contract ABI (use camelCase function names)
- Use forge-std Test contract
- Mock contract deployment
- Test all public functions with happy path, error cases, and edge cases
- Use assert functions from forge-std

Return ONLY the test code inside a ```solidity code block. No explanations."""


class GenerateTestsTool(BaseTool):
    """
    Generates test cases for Stylus smart contracts using LLM.

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
            test_framework: Test framework (rust_native, foundry).
            test_types: Types of tests (unit, integration, fuzz).
            coverage_focus: Specific functions to focus on.

        Returns:
            Dict with tests, test_summary, coverage_estimate,
            setup_instructions.
        """
        if not contract_code or not contract_code.strip():
            return {"error": "Contract code is required and cannot be empty"}

        contract_code = contract_code.strip()
        test_types = test_types or ["unit"]

        if not self._is_valid_contract(contract_code):
            return {
                "error": (
                    "Invalid contract code. Please provide valid"
                    " Stylus/Rust code with struct and impl blocks."
                ),
                "warnings": ["Could not parse contract structure"],
            }

        try:
            # Build LLM prompt
            system_prompt = (
                SYSTEM_PROMPT_FOUNDRY
                if test_framework == "foundry"
                else SYSTEM_PROMPT_RUST
            )

            focus_hint = ""
            if coverage_focus:
                focus_hint = (
                    "\n\nFocus test coverage on these functions: "
                    + ", ".join(coverage_focus)
                )

            type_hint = ""
            if "fuzz" in test_types:
                type_hint += (
                    "\n\nInclude fuzz/property-based tests using proptest."
                )
            if "integration" in test_types:
                type_hint += (
                    "\n\nInclude integration tests that test"
                    " multi-function workflows."
                )

            user_prompt = (
                f"Generate tests for this contract:"
                f"\n\n```rust\n{contract_code}\n```"
                f"{focus_hint}{type_hint}"
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = self._call_llm(
                messages=messages,
                temperature=0.2,
                max_tokens=8192,
            )

            # Extract test code from code block
            lang = "solidity" if test_framework == "foundry" else "rust"
            pattern = rf"```(?:{lang})\n([\s\S]*?)```"
            test_match = re.search(pattern, response)
            tests = test_match.group(1).strip() if test_match else response

            # Analyze contract for coverage stats
            contract_info = self._analyze_contract(contract_code)

            # Setup instructions
            setup = (
                self._get_foundry_setup()
                if test_framework == "foundry"
                else self._get_rust_setup()
            )

            # Analyze generated tests
            test_summary = self._generate_summary(tests, test_types)
            coverage_estimate = self._estimate_coverage(
                contract_info, tests
            )

            return {
                "tests": tests,
                "test_summary": test_summary,
                "coverage_estimate": coverage_estimate,
                "setup_instructions": setup,
            }

        except Exception as e:
            logger.exception("Test generation failed")
            return {"error": f"Test generation failed: {str(e)}"}

    def _is_valid_contract(self, code: str) -> bool:
        """Check if code has basic contract structure."""
        has_struct = "struct" in code.lower()
        has_fn = "fn " in code
        return has_struct or has_fn

    def _analyze_contract(self, code: str) -> dict:
        """Analyze contract to extract structure."""
        info: dict = {
            "name": "Contract",
            "functions": [],
            "storage_fields": [],
        }

        struct_match = re.search(r"pub\s+struct\s+(\w+)", code)
        if struct_match:
            info["name"] = struct_match.group(1)

        fn_pattern = (
            r"pub\s+fn\s+(\w+)\s*\(([^)]*)\)"
            r"(?:\s*->\s*([^{]+))?"
        )
        for match in re.finditer(fn_pattern, code):
            fn_name = match.group(1)
            params = match.group(2).strip()
            return_type = (
                match.group(3).strip() if match.group(3) else "void"
            )

            param_list = []
            if params and params not in ("&self", "&mut self"):
                for p in params.split(","):
                    p = p.strip()
                    if p and p not in ["&self", "&mut self"]:
                        param_list.append(p)

            is_mut = "&mut self" in params

            info["functions"].append({
                "name": fn_name,
                "params": param_list,
                "return_type": return_type.strip(),
                "is_mut": is_mut,
            })

        storage_pattern = r"sol_storage!\s*\{[\s\S]*?\}"
        storage_match = re.search(storage_pattern, code)
        if storage_match:
            storage_block = storage_match.group(0)
            field_pattern = r"(\w+)\s+(\w+);"
            for field_match in re.finditer(
                field_pattern, storage_block
            ):
                info["storage_fields"].append({
                    "type": field_match.group(1),
                    "name": field_match.group(2),
                })

        return info

    def _generate_summary(self, tests: str, test_types: list[str]) -> dict:
        """Generate test summary."""
        rust_count = len(re.findall(r"#\[test\]", tests))
        foundry_count = len(re.findall(r"function test_", tests))
        test_count = rust_count or foundry_count
        fuzz_count = tests.count("proptest") if "fuzz" in test_types else 0

        return {
            "total_tests": test_count,
            "unit_tests": test_count - fuzz_count,
            "integration_tests": 0,
            "fuzz_tests": fuzz_count,
        }

    def _estimate_coverage(self, contract_info: dict, tests: str) -> dict:
        """Estimate test coverage."""
        all_functions = [f["name"] for f in contract_info["functions"]]

        covered = []
        not_covered = []
        tests_lower = tests.lower()

        for fn_name in all_functions:
            if fn_name.lower() in tests_lower:
                covered.append(fn_name)
            else:
                not_covered.append(fn_name)

        edge_cases = []
        if "zero" in tests_lower or "0" in tests:
            edge_cases.append("Zero values")
        if "overflow" in tests_lower:
            edge_cases.append("Overflow handling")
        if "underflow" in tests_lower:
            edge_cases.append("Underflow handling")
        if "error" in tests_lower or "Err" in tests:
            edge_cases.append("Error conditions")
        if "empty" in tests_lower:
            edge_cases.append("Empty inputs")

        return {
            "functions_covered": covered,
            "functions_not_covered": not_covered,
            "edge_cases": edge_cases,
        }

    def _get_rust_setup(self) -> str:
        """Get Rust test setup instructions."""
        return """# Running Rust Tests (stylus-sdk 0.10.0)

1. Ensure your Cargo.toml has test dependencies:
```toml
[dev-dependencies]
stylus-sdk = { version = "0.10.0", features = ["stylus-test"] }
```

2. Run tests (use --target to run on host, not WASM):
```bash
cargo test --target=x86_64-unknown-linux-gnu
```
Or on macOS:
```bash
cargo test --target=aarch64-apple-darwin
```

3. Run with output:
```bash
cargo test --target=x86_64-unknown-linux-gnu -- --nocapture
```

4. Run specific test:
```bash
cargo test --target=x86_64-unknown-linux-gnu test_function_name
```

Note: The --target flag is needed because Stylus contracts compile to
wasm32-unknown-unknown by default (via rust-toolchain.toml), but tests
must run on the host platform. TestVM simulates the Stylus environment.
"""

    def _get_foundry_setup(self) -> str:
        """Get Foundry test setup instructions."""
        return """# Running Foundry Tests

1. Install Foundry:
```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

2. Export ABI:
```bash
cargo stylus export-abi > abi.json
```

3. Create test file in `test/` directory

4. Run tests:
```bash
forge test --fork-url <RPC_URL>
```

5. Run with verbosity:
```bash
forge test -vvv
```

6. Run specific test:
```bash
forge test --match-test test_function_name
```
"""

"""
generate_stylus_code MCP Tool.

Generates Stylus/Rust smart contract code based on user requirements.
Supports version-aware code generation for different stylus-sdk versions.
"""

import re
from typing import Optional

from .base import BaseTool
from .get_stylus_context import GetStylusContextTool

# Import version manager - handle gracefully if not available
try:
    from src.utils.version_manager import (
        get_main_version,
        get_minimum_version,
        is_version_deprecated,
        get_version_patterns,
        get_alloy_primitives_version,
        get_alloy_sol_types_version,
        detect_version_from_cargo_toml,
        get_deprecation_warning,
    )
    HAS_VERSION_MANAGER = True
except ImportError:
    HAS_VERSION_MANAGER = False
    # Fallback defaults
    def get_main_version(): return "0.9.0"
    def get_minimum_version(): return "0.8.0"
    def is_version_deprecated(v): return False
    def get_version_patterns(v): return {
        "attributes": ["#[public]"],
        "error_handling": "Result<T, Vec<u8>>",
        "cfg_attr": '#![cfg_attr(not(feature = "export-abi"), no_main)]'
    }
    def get_alloy_primitives_version(v): return "0.9.2"
    def get_alloy_sol_types_version(v): return "0.9.2"
    def detect_version_from_cargo_toml(c): return None
    def get_deprecation_warning(v): return None


def get_system_prompt(target_version: str) -> str:
    """Generate version-aware system prompt."""
    patterns = get_version_patterns(target_version)
    alloy_version = get_alloy_primitives_version(target_version)
    main_attr = patterns.get("attributes", ["#[public]"])[0]
    error_handling = patterns.get("error_handling", "Result<T, Vec<u8>>")
    cfg_attr = patterns.get("cfg_attr", '#![cfg_attr(not(feature = "export-abi"), no_main)]')

    return f"""You are an expert Stylus smart contract developer. You write high-quality Rust code for Arbitrum Stylus contracts.

Target SDK Version: stylus-sdk {target_version}

Key Stylus patterns for v{target_version}:
1. Use `sol_storage!` macro for state storage
2. Use `#[entrypoint]` attribute on the main contract struct
3. Use `{main_attr}` for public functions
4. Use Stylus SDK types: `StorageVec`, `StorageMap`, `StorageU256`, `StorageAddress`, etc.
5. Use `msg::sender()` to get the caller address
6. Handle errors with {error_handling}
7. Include {cfg_attr}
8. Follow Rust naming conventions (snake_case for functions, PascalCase for types)

Dependencies for v{target_version}:
- stylus-sdk = "{target_version}"
- alloy-primitives = "{alloy_version}"

When generating code:
- Generate complete, compilable Rust code
- Include all necessary imports
- Add helpful comments for complex logic
- Use proper error handling
- Follow security best practices (check for overflows, validate inputs)
"""


# Legacy prompt for backwards compatibility
SYSTEM_PROMPT = get_system_prompt(get_main_version())

CONTRACT_TEMPLATES = {
    "erc20": """use stylus_sdk::prelude::*;
use stylus_sdk::alloy_primitives::{Address, U256};
use stylus_sdk::msg;

sol_storage! {
    #[entrypoint]
    pub struct Token {
        mapping(address => uint256) balances;
        mapping(address => mapping(address => uint256)) allowances;
        uint256 total_supply;
    }
}

#[external]
impl Token {
    // ERC20 implementation
}
""",
    "erc721": """use stylus_sdk::prelude::*;
use stylus_sdk::alloy_primitives::{Address, U256};
use stylus_sdk::msg;

sol_storage! {
    #[entrypoint]
    pub struct NFT {
        mapping(uint256 => address) owners;
        mapping(address => uint256) balances;
        mapping(uint256 => address) token_approvals;
        mapping(address => mapping(address => bool)) operator_approvals;
        uint256 next_token_id;
    }
}

#[external]
impl NFT {
    // ERC721 implementation
}
""",
}


class GenerateStylusCodeTool(BaseTool):
    """
    Generates Stylus smart contract code.

    Uses RAG context to inform code generation with relevant examples.
    """

    def __init__(
        self,
        context_tool: Optional[GetStylusContextTool] = None,
        **kwargs,
    ):
        """
        Initialize the tool.

        Args:
            context_tool: GetStylusContextTool for retrieving examples.
        """
        super().__init__(**kwargs)
        self.context_tool = context_tool or GetStylusContextTool(**kwargs)

    def execute(
        self,
        prompt: str,
        context_query: Optional[str] = None,
        contract_type: Optional[str] = None,
        include_tests: bool = False,
        temperature: float = 0.2,
        target_version: Optional[str] = None,
        cargo_toml: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """
        Generate Stylus smart contract code.

        Args:
            prompt: Description of the code to generate.
            context_query: Optional query to retrieve context.
            contract_type: Type of contract (erc20, erc721, erc1155, custom).
            include_tests: Whether to include unit tests.
            temperature: Generation temperature (0-1).
            target_version: Target stylus-sdk version (default: main version).
            cargo_toml: Optional Cargo.toml content for automatic version detection.

        Returns:
            Dict with code, explanation, dependencies, warnings, context_used, target_version.
        """
        # Validate input
        if not prompt or not prompt.strip():
            return {"error": "Prompt is required and cannot be empty"}

        prompt = prompt.strip()
        warnings = []

        # Version detection/selection logic
        if cargo_toml:
            detected_version = detect_version_from_cargo_toml(cargo_toml)
            if detected_version:
                target_version = detected_version
                deprecation_warning = get_deprecation_warning(detected_version)
                if deprecation_warning:
                    warnings.append(deprecation_warning)

        # Default to main version if not specified
        if not target_version:
            target_version = get_main_version()

        # Check if request is Stylus-related
        stylus_keywords = ["stylus", "rust", "contract", "token", "erc", "storage", "arbitrum"]
        if not any(kw in prompt.lower() for kw in stylus_keywords):
            warnings.append("This request may not be related to Stylus. Results may vary.")

        try:
            # Retrieve relevant context
            context_used = []
            context_text = ""

            query = context_query or prompt
            context_result = self.context_tool.execute(
                query=query,
                n_results=5,
                content_type="code",
                rerank=True,
            )

            if "contexts" in context_result:
                for ctx in context_result["contexts"]:
                    context_used.append({
                        "source": ctx["source"],
                        "relevance": ctx["relevance_score"],
                    })
                    context_text += f"\n--- Example from {ctx['source']} ---\n{ctx['content'][:1500]}\n"

            # Build generation prompt
            user_prompt = self._build_prompt(
                prompt=prompt,
                contract_type=contract_type,
                context_text=context_text,
                include_tests=include_tests,
            )

            # Generate code with version-aware system prompt
            system_prompt = get_system_prompt(target_version)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = self._call_llm(
                messages=messages,
                temperature=temperature,
                max_tokens=4096,
            )

            # Parse response
            code, explanation = self._parse_response(response)

            # Extract dependencies with correct versions
            dependencies = self._extract_dependencies(code, target_version)

            # Validate code
            validation_warnings = self._validate_code(code)
            warnings.extend(validation_warnings)

            return {
                "code": code,
                "explanation": explanation,
                "dependencies": dependencies,
                "warnings": warnings if warnings else [],
                "context_used": context_used,
                "target_version": target_version,
            }

        except Exception as e:
            return {"error": f"Code generation failed: {str(e)}"}

    def _build_prompt(
        self,
        prompt: str,
        contract_type: Optional[str],
        context_text: str,
        include_tests: bool,
    ) -> str:
        """Build the generation prompt."""
        parts = []

        # Add template hint if contract type specified
        if contract_type and contract_type in CONTRACT_TEMPLATES:
            parts.append(f"Base your implementation on this {contract_type.upper()} template structure:")
            parts.append(f"```rust\n{CONTRACT_TEMPLATES[contract_type]}\n```")
            parts.append("")

        # Add context if available
        if context_text:
            parts.append("Here are some relevant code examples for reference:")
            parts.append(context_text)
            parts.append("")

        # Add main request
        parts.append(f"Generate Stylus smart contract code for the following requirement:")
        parts.append(f"\n{prompt}\n")

        # Add test request if needed
        if include_tests:
            parts.append("\nAlso include unit tests for the main functionality using Rust's #[test] attribute.")

        parts.append("\nProvide:")
        parts.append("1. Complete, compilable Rust code with all imports")
        parts.append("2. A brief explanation of the implementation")
        parts.append("\nFormat your response with the code in a ```rust code block, followed by an explanation.")

        return "\n".join(parts)

    def _parse_response(self, response: str) -> tuple[str, str]:
        """Parse code and explanation from LLM response."""
        code = ""
        explanation = ""

        # Extract code blocks
        code_pattern = r"```(?:rust)?\s*([\s\S]*?)```"
        matches = re.findall(code_pattern, response)

        if matches:
            # Combine all code blocks
            code = "\n\n".join(match.strip() for match in matches)

            # Get explanation (text after last code block)
            last_block_end = response.rfind("```")
            if last_block_end != -1:
                explanation = response[last_block_end + 3:].strip()

        if not code:
            # No code blocks found, treat whole response as code
            code = response.strip()

        if not explanation:
            explanation = "Generated Stylus smart contract code based on the provided requirements."

        return code, explanation

    def _extract_dependencies(self, code: str, target_version: str) -> list[dict]:
        """Extract Cargo dependencies from code with correct versions for target SDK."""
        dependencies = []

        # Get version-appropriate dependency versions
        alloy_primitives_ver = get_alloy_primitives_version(target_version)
        alloy_sol_types_ver = get_alloy_sol_types_version(target_version)

        # Check for common Stylus dependencies
        if "stylus_sdk" in code or "stylus-sdk" in code:
            dependencies.append({
                "name": "stylus-sdk",
                "version": target_version,
            })

        if "alloy_primitives" in code or "alloy-primitives" in code:
            dependencies.append({
                "name": "alloy-primitives",
                "version": alloy_primitives_ver,
            })

        if "alloy_sol_types" in code or "alloy-sol-types" in code:
            dependencies.append({
                "name": "alloy-sol-types",
                "version": alloy_sol_types_ver,
            })

        return dependencies

    def _validate_code(self, code: str) -> list[str]:
        """Validate generated code and return warnings."""
        warnings = []

        # Check for basic Stylus patterns
        if "sol_storage!" not in code:
            warnings.append("Code may be missing sol_storage! macro for state storage")

        if "#[entrypoint]" not in code:
            warnings.append("Code may be missing #[entrypoint] attribute")

        # Check for balanced braces
        if code.count("{") != code.count("}"):
            warnings.append("Unbalanced curly braces detected")

        if code.count("(") != code.count(")"):
            warnings.append("Unbalanced parentheses detected")

        # Check for common security issues
        if "- " in code and "checked_sub" not in code.lower():
            warnings.append("Potential unchecked subtraction - consider using checked_sub")

        return warnings

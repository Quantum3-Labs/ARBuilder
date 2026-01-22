"""
generate_stylus_code MCP Tool.

Generates Stylus/Rust smart contract code based on user requirements.
Uses verified working templates as the foundation to ensure compilable output.

Key improvement: Instead of generating from scratch, this tool customizes
curated templates from official Stylus examples.
"""

import re
from typing import Optional

from .base import BaseTool
from .get_stylus_context import GetStylusContextTool

# Import templates
try:
    from src.templates.stylus_templates import (
        StylusTemplate,
        select_template,
        get_template,
    )
    HAS_TEMPLATES = True
except ImportError:
    HAS_TEMPLATES = False
    StylusTemplate = None
    select_template = None
    get_template = None

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
    def get_alloy_primitives_version(v): return "=0.8.20"
    def get_alloy_sol_types_version(v): return "=0.8.20"
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


def get_template_system_prompt(template: "StylusTemplate", target_version: str) -> str:
    """Generate system prompt for template-based generation."""
    alloy_version = get_alloy_primitives_version(target_version)

    return f"""You are an expert Stylus (Rust) smart contract developer for Arbitrum.

CRITICAL: You are customizing a WORKING template. The template below compiles and deploys correctly.
Your job is to MODIFY this template to match the user's requirements while keeping the EXACT structure intact.

Base Template: {template.name}
Template Description: {template.description}
Template Features: {', '.join(template.features)}

Target SDK Version: stylus-sdk {target_version}
Alloy Primitives: {alloy_version}

ABSOLUTE RULES - NEVER VIOLATE THESE:
1. KEEP the EXACT first 4 lines: #![cfg_attr...], #![cfg_attr...], #[macro_use], extern crate alloc;
2. KEEP all use statements from the template - you may ADD more but NEVER remove
3. There must be EXACTLY ONE sol_storage! block - NEVER create empty sol_storage! blocks
4. KEEP the #[entrypoint] attribute inside sol_storage!
5. KEEP the #[public] attribute on the impl block
6. NEVER add "use alloy_sol_types::sol;" - it's already available via stylus_sdk::prelude::*
7. If adding events/errors with sol! macro, they must be BEFORE sol_storage!
8. KEEP the Cargo.toml [profile.release] section exactly as provided

WHAT YOU MAY DO:
- Add/modify storage fields inside sol_storage!
- Add/modify functions inside the #[public] impl block
- Add events using sol! {{ event EventName(...); }} BEFORE sol_storage!
- Add error types using sol! {{ error ErrorName(...); }} BEFORE sol_storage!
- Add internal helper functions (without #[public])

IMPORTS - USE THESE PATTERNS:
- Types from stylus_sdk::alloy_primitives::{{Address, U256, U8, ...}}
- sol! macro is available from stylus_sdk::prelude::*
- For events: evm::log(EventName {{ field1, field2 }})
- For errors: return Err(ErrorName {{ ... }}.abi_encode())

Output format:
1. Brief explanation of changes (1-2 sentences)
2. Complete lib.rs in a ```rust code block
3. Cargo.toml in a ```toml code block (only if dependencies changed)"""


# Legacy templates for backwards compatibility (when templates module not available)
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

#[public]
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

#[public]
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
        Generate Stylus smart contract code using template-based generation.

        Args:
            prompt: Description of the code to generate.
            context_query: Optional query to retrieve context.
            contract_type: Type of contract (token, defi, utility, custom).
            include_tests: Whether to include unit tests.
            temperature: Generation temperature (0-1).
            target_version: Target stylus-sdk version (default: main version).
            cargo_toml: Optional Cargo.toml content for automatic version detection.

        Returns:
            Dict with code, cargo_toml, explanation, dependencies, warnings,
            context_used, target_version, template_used.
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

        try:
            # Select appropriate template
            template = None
            template_name = "legacy"

            if HAS_TEMPLATES and select_template:
                template = select_template(contract_type or "utility", prompt)
                template_name = template.name

            # Retrieve relevant context for additional patterns
            context_used = []
            context_text = ""

            query = context_query or prompt
            context_result = self.context_tool.execute(
                query=query,
                n_results=3,  # Reduced since we have a template as base
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
            if template:
                # Use template-based generation
                user_prompt = self._build_template_prompt(
                    prompt=prompt,
                    template=template,
                    context_text=context_text,
                    include_tests=include_tests,
                )
                system_prompt = get_template_system_prompt(template, target_version)
            else:
                # Fallback to legacy generation
                user_prompt = self._build_prompt(
                    prompt=prompt,
                    contract_type=contract_type,
                    context_text=context_text,
                    include_tests=include_tests,
                )
                system_prompt = get_system_prompt(target_version)

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = self._call_llm(
                messages=messages,
                temperature=temperature,
                max_tokens=8192,  # Allow longer output for complete contracts
            )

            # Parse response
            code, cargo_toml_output, explanation = self._parse_template_response(
                response, template
            )

            # Extract dependencies with correct versions
            dependencies = self._extract_dependencies(code, target_version)

            # Validate code
            validation_warnings = self._validate_code(code)
            warnings.extend(validation_warnings)

            return {
                "code": code,
                "cargo_toml": cargo_toml_output,
                "explanation": explanation,
                "dependencies": dependencies,
                "warnings": warnings if warnings else [],
                "context_used": context_used,
                "target_version": target_version,
                "template_used": template_name,
            }

        except Exception as e:
            return {"error": f"Code generation failed: {str(e)}"}

    def _build_template_prompt(
        self,
        prompt: str,
        template: "StylusTemplate",
        context_text: str,
        include_tests: bool,
    ) -> str:
        """Build prompt for template-based generation."""
        parts = [
            "BASE TEMPLATE (lib.rs):",
            f"```rust\n{template.lib_rs}\n```",
            "",
            "BASE TEMPLATE (Cargo.toml):",
            f"```toml\n{template.cargo_toml}\n```",
            "",
        ]

        if context_text:
            parts.append("ADDITIONAL PATTERNS FROM DOCUMENTATION:")
            parts.append(context_text)
            parts.append("")

        parts.append("USER REQUEST:")
        parts.append(prompt)
        parts.append("")

        if include_tests:
            parts.append("Keep the #[cfg(test)] module and update the tests to match the new functionality.")
        else:
            parts.append("You may remove the #[cfg(test)] module if not needed.")

        parts.append("")
        parts.append("Please customize the template to implement the user's request. Keep the working structure intact.")

        return "\n".join(parts)

    def _build_prompt(
        self,
        prompt: str,
        contract_type: Optional[str],
        context_text: str,
        include_tests: bool,
    ) -> str:
        """Build the generation prompt (legacy fallback)."""
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
        """Parse code and explanation from LLM response (legacy)."""
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

    def _parse_template_response(
        self, response: str, template: Optional["StylusTemplate"]
    ) -> tuple[str, str, str]:
        """Parse code, cargo.toml, and explanation from template-based response."""
        code = ""
        cargo_toml = ""
        explanation = ""

        # Extract rust code blocks
        rust_pattern = r"```rust\s*([\s\S]*?)```"
        rust_matches = re.findall(rust_pattern, response)

        if rust_matches:
            code = rust_matches[0].strip()

        # Extract toml code blocks
        toml_pattern = r"```toml\s*([\s\S]*?)```"
        toml_matches = re.findall(toml_pattern, response)

        if toml_matches:
            cargo_toml = toml_matches[0].strip()
        elif template:
            # Use template's cargo.toml if not provided
            cargo_toml = template.cargo_toml

        # Extract explanation (text before first code block or after last)
        explanation_parts = response.split("```")
        if explanation_parts:
            # First part before any code block
            first_part = explanation_parts[0].strip()
            if first_part:
                explanation = first_part
            elif len(explanation_parts) > 1:
                # Try last part after all code blocks
                last_part = explanation_parts[-1].strip()
                if last_part:
                    explanation = last_part

        if not code:
            code = response.strip()

        if not explanation:
            explanation = "Contract customized based on your requirements."

        # Apply fixes for common LLM mistakes
        code = self._fix_code(code, template)
        if template:
            cargo_toml = self._fix_cargo_toml(cargo_toml, template, template.sdk_version)

        return code, cargo_toml, explanation

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

    def _fix_code(self, code: str, template: Optional["StylusTemplate"]) -> str:
        """Fix common LLM mistakes in generated code."""
        fixed = code

        # Fix 1: Remove empty sol_storage! blocks
        fixed = re.sub(r'sol_storage!\s*\{\s*\}', '', fixed)

        # Fix 2: Ensure proper cfg_attr if missing
        if "#![cfg_attr(not(any(test" not in fixed:
            if template:
                template_start = template.lib_rs.split("extern crate alloc")[0]
                if not fixed.startswith("#![cfg_attr"):
                    fixed = template_start + fixed

        # Fix 3: Ensure extern crate alloc if missing
        if "extern crate alloc" not in fixed:
            fixed = re.sub(
                r'^(#!\[cfg_attr.*\n)+',
                r'\g<0>#[macro_use]\nextern crate alloc;\n\n',
                fixed,
                flags=re.MULTILINE
            )

        # Fix 4: Remove incorrect imports (sol! is in prelude)
        fixed = re.sub(r'use alloy_sol_types::sol;\n?', '', fixed)
        fixed = re.sub(r'use stylus_sdk::alloy_sol_types::sol;\n?', '', fixed)

        # Fix 5: Ensure alloc::vec::Vec import if Vec is used
        if "Vec<u8>" in fixed and "use alloc::vec::Vec" not in fixed:
            fixed = re.sub(
                r'(extern crate alloc;)',
                r'\1\n\nuse alloc::vec::Vec;',
                fixed
            )

        # Fix 6: Ensure there's exactly one sol_storage! block with #[entrypoint]
        sol_storage_count = len(re.findall(r'sol_storage!\s*\{', fixed))
        if sol_storage_count == 0 and template:
            # If no sol_storage! block, the code is likely broken - use template
            return template.lib_rs

        # Fix 7: Ensure #[entrypoint] is inside sol_storage! if missing
        if "#[entrypoint]" not in fixed:
            fixed = re.sub(
                r'sol_storage!\s*\{\s*(\n?\s*pub struct)',
                r'sol_storage! {\n    #[entrypoint]\1',
                fixed
            )

        return fixed

    def _fix_cargo_toml(self, cargo: str, template: Optional["StylusTemplate"], target_version: str) -> str:
        """Fix common LLM mistakes in generated Cargo.toml."""
        fixed = cargo

        # Ensure correct stylus-sdk version
        fixed = re.sub(
            r'stylus-sdk\s*=\s*"[^"]+"',
            f'stylus-sdk = "{target_version}"',
            fixed
        )

        # Ensure alloy-primitives uses exact version pin
        if 'alloy-primitives = "=' not in fixed:
            fixed = re.sub(
                r'alloy-primitives\s*=\s*"([^"=][^"]*)"',
                r'alloy-primitives = "=\1"',
                fixed
            )

        # Ensure alloy-sol-types uses exact version pin
        if 'alloy-sol-types = "=' not in fixed:
            fixed = re.sub(
                r'alloy-sol-types\s*=\s*"([^"=][^"]*)"',
                r'alloy-sol-types = "=\1"',
                fixed
            )

        # Ensure [profile.release] section exists
        if "[profile.release]" not in fixed:
            fixed += """

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s" """

        # Ensure [lib] section exists with cdylib
        if 'crate-type = ["lib", "cdylib"]' not in fixed:
            if "[lib]" not in fixed:
                fixed = re.sub(
                    r'\[features\]',
                    '[lib]\ncrate-type = ["lib", "cdylib"]\n\n[features]',
                    fixed
                )

        return fixed

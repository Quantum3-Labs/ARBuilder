"""
generate_stylus_code MCP Tool.

Generates Stylus/Rust smart contract code based on user requirements.
Uses verified working templates as the foundation to ensure compilable output.

Key improvement: Instead of generating from scratch, this tool customizes
curated templates from official Stylus examples.
"""

import logging
import re
from typing import Optional

from .base import BaseTool
from .get_stylus_context import GetStylusContextTool

logger = logging.getLogger(__name__)

TEMPLATE_DISCLAIMER = (
    "This generated code is a starting entrypoint — a working foundation for you to build upon. "
    "Review, customize, and extend it to match your specific requirements before deploying."
)

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

# Import compiler verifier - handle gracefully if not available
try:
    from src.utils.compiler_verifier import (
        CompilerVerifier,
        format_errors_for_llm,
    )
    HAS_COMPILER = True
except ImportError:
    HAS_COMPILER = False
    CompilerVerifier = None

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
    def get_main_version(): return "0.10.0"
    def get_minimum_version(): return "0.8.0"
    def is_version_deprecated(v): return False
    def get_version_patterns(v): return {
        "attributes": ["#[public]"],
        "error_handling": "Result<T, Vec<u8>>",
        "cfg_attr": '#![cfg_attr(not(feature = "export-abi"), no_main)]',
        "sender": "self.vm().msg_sender()",
    }
    def get_alloy_primitives_version(v): return "1.0.1"
    def get_alloy_sol_types_version(v): return "1.0.1"
    def detect_version_from_cargo_toml(c): return None
    def get_deprecation_warning(v): return None


def get_system_prompt(target_version: str) -> str:
    """Generate version-aware system prompt."""
    patterns = get_version_patterns(target_version)
    alloy_version = get_alloy_primitives_version(target_version)
    main_attr = patterns.get("attributes", ["#[public]"])[0]
    error_handling = patterns.get("error_handling", "Result<T, Vec<u8>>")
    cfg_attr = patterns.get("cfg_attr", '#![cfg_attr(not(feature = "export-abi"), no_main)]')

    sender_pattern = patterns.get("sender", "self.vm().msg_sender()")

    return f"""You are an expert Stylus smart contract developer. You write high-quality Rust code for Arbitrum Stylus contracts.

Target SDK Version: stylus-sdk {target_version}

Key Stylus patterns for v{target_version}:
1. Use `sol_storage!` macro for state storage
2. Use `#[entrypoint]` attribute on the main contract struct
3. Use `{main_attr}` for public functions
4. Use Stylus SDK types: `StorageVec`, `StorageMap`, `StorageU256`, `StorageAddress`, etc.
5. Use `{sender_pattern}` to get the caller address
6. Use `self.vm().msg_value()` to get sent ETH value
7. Use `self.vm().log(Event {{ ... }})` to emit events (NOT evm::log)
8. Handle errors with {error_handling}
9. Include {cfg_attr}
10. Follow Rust naming conventions (snake_case for functions, PascalCase for types)
11. For ETH transfers: use transfer_eth(self, to, amount) from stylus_sdk::call::transfer (NOT evm::transfer_eth)
12. For error types: define with sol! {{ error MyError(...); }}, wrap in enum with #[derive(SolidityError)]
13. For .abi_encode() on errors: import SolError via use alloy_sol_types::SolError;
14. Avoid chained .setter() borrows — get value with .get() first, then .setter().set() separately
15. Do NOT use `use stylus_sdk::evm` — the evm module was removed in 0.10.0
16. Do NOT use `use stylus_sdk::msg` — use self.vm().msg_sender(), self.vm().msg_value()
17. ALWAYS include `use alloc::vec;` (the module) alongside `use alloc::vec::Vec;` — sol_storage! needs it
18. For ETH transfers via RawCall: `unsafe {{ let _ = RawCall::new_with_value(self.vm(), amount).call(to, &[]); }}` — requires self.vm() as first arg and unsafe block
19. uint8 in sol_storage! maps to Uint<8,1> not native u8 — prefer uint256 unless uint8 is specifically needed
20. Package name in Cargo.toml MUST use underscores (e.g., "my_contract") — hyphens prevent cargo-stylus from finding the WASM file
21. A src/main.rs is REQUIRED — cargo stylus deploy uses `cargo run` to check for constructors
22. The correct ABI export function in 0.10.0 is `print_from_args()` (NOT `print_abi()`)
23. crate-type in [lib] must be ["lib", "cdylib"] — "lib" is needed for bin target linking

Dependencies for v{target_version}:
- stylus-sdk = "{target_version}"
- alloy-primitives = "{alloy_version}"

Required project files (SDK 0.10.0+):
- Stylus.toml with [workspace], [workspace.networks], and [contract] sections
- rust-toolchain.toml with channel = "1.88.0"
- src/main.rs with print_from_args() for ABI export

When generating code:
- Generate complete, compilable Rust code
- Include all necessary imports including `use alloc::vec;`
- Add helpful comments for complex logic
- Use proper error handling
- Follow security best practices (check for overflows, validate inputs)
- Do NOT use deprecated msg::sender(), msg::value(), or evm::log() — use self.vm() methods
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
6. The sol! macro is available via prelude — do NOT add standalone "use alloy_sol_types::sol;". BUT if using .abi_encode() on errors, MUST import SolError: use alloy_sol_types::SolError; (or combined: alloy_sol_types::{{sol, SolError}})
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
- For events: self.vm().log(EventName {{ field1, field2 }}) (NOT evm::log)
- For caller: self.vm().msg_sender() (NOT msg::sender())
- For errors: return Err(ErrorName {{ ... }}.abi_encode())

Output format:
1. Brief explanation of changes (1-2 sentences)
2. Complete lib.rs in a ```rust code block

IMPORTANT: Do NOT output Cargo.toml - the template's Cargo.toml will be used as-is."""


# Legacy templates for backwards compatibility (when templates module not available)
CONTRACT_TEMPLATES = {
    "erc20": """use stylus_sdk::prelude::*;
use stylus_sdk::alloy_primitives::{Address, U256};


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

    MAX_COMPILE_ATTEMPTS = 2

    def __init__(
        self,
        context_tool: Optional[GetStylusContextTool] = None,
        compiler_verifier: Optional["CompilerVerifier"] = None,
        **kwargs,
    ):
        """
        Initialize the tool.

        Args:
            context_tool: GetStylusContextTool for retrieving examples.
            compiler_verifier: Optional CompilerVerifier for Docker-based cargo check.
        """
        super().__init__(**kwargs)
        self.context_tool = context_tool or GetStylusContextTool(**kwargs)
        if compiler_verifier is not None:
            self.compiler = compiler_verifier
        elif HAS_COMPILER and CompilerVerifier is not None:
            self.compiler = CompilerVerifier()
        else:
            self.compiler = None

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
                category_boosts=None,  # Use default Stylus-focused boosts
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

            # Compile-verify-fix loop (if Docker available)
            compile_verified = False
            compile_attempts = 0

            if self.compiler and self.compiler.is_available() and cargo_toml_output:
                for attempt in range(self.MAX_COMPILE_ATTEMPTS):
                    compile_attempts = attempt + 1
                    logger.info(f"Compile check attempt {compile_attempts}")

                    result = self.compiler.verify(code, cargo_toml_output)

                    if result.skipped:
                        logger.info(f"Compile check skipped: {result.skip_reason}")
                        break

                    if result.success:
                        compile_verified = True
                        logger.info("Compile check passed")
                        break

                    # Build fix prompt with structured errors
                    actual_errors = [e for e in result.errors if e.level == "error"]
                    if not actual_errors:
                        compile_verified = True
                        break

                    error_text = format_errors_for_llm(actual_errors, code)
                    fix_prompt = self._build_fix_prompt(code, error_text)

                    fix_messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": fix_prompt},
                    ]

                    fix_response = self._call_llm(
                        messages=fix_messages,
                        temperature=0.1,
                        max_tokens=8192,
                    )

                    # Parse fixed code
                    fixed_code, _, _ = self._parse_template_response(
                        fix_response, template
                    )
                    if fixed_code and fixed_code != code:
                        code = fixed_code
                    else:
                        warnings.append(
                            f"Compile fix attempt {compile_attempts} did not produce different code"
                        )
                        break

            # Extract dependencies with correct versions
            dependencies = self._extract_dependencies(code, target_version)

            # Validate code
            validation_warnings = self._validate_code(code)
            warnings.extend(validation_warnings)

            # Derive project name from prompt and fix Cargo.toml/main.rs references
            main_rs_output = template.main_rs if template else ""
            stylus_toml_output = template.stylus_toml if template else ""
            rust_toolchain_toml_output = template.rust_toolchain_toml if template else ""

            if cargo_toml_output:
                project_name = self._derive_project_name(prompt)
                # Fix package name (use underscores for cargo-stylus compatibility)
                cargo_toml_output = re.sub(
                    r'name\s*=\s*"[^"]+"',
                    f'name = "{project_name}"',
                    cargo_toml_output,
                )
                # Fix main.rs crate reference (print_from_args uses crate name)
                if main_rs_output:
                    main_rs_output = re.sub(
                        r'(\w+)::print_from_args\b',
                        f'{project_name}::print_from_args',
                        main_rs_output,
                    )

            return {
                "code": code,
                "cargo_toml": cargo_toml_output,
                "main_rs": main_rs_output,
                "stylus_toml": stylus_toml_output,
                "rust_toolchain_toml": rust_toolchain_toml_output,
                "explanation": explanation,
                "dependencies": dependencies,
                "warnings": warnings if warnings else [],
                "context_used": context_used,
                "target_version": target_version,
                "template_used": template_name,
                "compile_verified": compile_verified,
                "compile_attempts": compile_attempts,
                "disclaimer": TEMPLATE_DISCLAIMER,
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

        # ALWAYS use template's Cargo.toml - don't trust LLM-generated Cargo.toml
        # LLM often makes typos (alloy-sol_types) or misses deps (ruint)
        if template:
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

        # Apply fixes for common LLM mistakes in code only
        # Cargo.toml comes directly from template, no fixes needed
        code = self._fix_code(code, template)

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

        # Fix 2: Ensure proper cfg_attr — must use (not(any(test, feature = "export-abi")))
        # Fix wrong patterns like (not(any(feature = "export-abi", test)))
        if "#![cfg_attr(not(any(test" not in fixed:
            if template:
                template_start = template.lib_rs.split("extern crate alloc")[0]
                if not fixed.startswith("#![cfg_attr"):
                    fixed = template_start + fixed
                else:
                    # Replace wrong cfg_attr patterns with correct ones
                    fixed = re.sub(
                        r'#!\[cfg_attr\(not\(any\(feature\s*=\s*"export-abi",\s*test\)\),\s*no_std\)\]',
                        '#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]',
                        fixed,
                    )
                    fixed = re.sub(
                        r'#!\[cfg_attr\(not\(test\),\s*no_main\)\]',
                        '#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]',
                        fixed,
                    )

        # Fix 3: Ensure extern crate alloc if missing
        if "extern crate alloc" not in fixed:
            fixed = re.sub(
                r'^(#!\[cfg_attr.*\n)+',
                r'\g<0>#[macro_use]\nextern crate alloc;\n\n',
                fixed,
                flags=re.MULTILINE
            )

        # Fix 4: Remove standalone sol! imports (sol! is in prelude)
        # Only remove the standalone import — preserve combined imports like {sol, SolError}
        fixed = re.sub(r'^use alloy_sol_types::sol;\s*$', '', fixed, flags=re.MULTILINE)
        fixed = re.sub(r'^use stylus_sdk::alloy_sol_types::sol;\s*$', '', fixed, flags=re.MULTILINE)

        # Fix 5: Handle Vec imports - avoid duplicates
        # If we have both "use alloc::vec::Vec" and "use alloc::{...vec::Vec...}", remove the standalone
        if "use alloc::vec::Vec;" in fixed and "use alloc::{" in fixed and "vec::Vec" in fixed:
            fixed = re.sub(r'use alloc::vec::Vec;\n?', '', fixed)
        # If Vec<u8> is used but no import, add it
        if "Vec<u8>" in fixed and "alloc::vec::Vec" not in fixed and "alloc::{" not in fixed:
            fixed = re.sub(
                r'(extern crate alloc;)',
                r'\1\n\nuse alloc::vec::Vec;',
                fixed
            )

        # Fix 6: Ensure use alloc::vec; is present (sol_storage! needs vec module)
        if "use alloc::vec;" not in fixed and "use alloc::{" not in fixed:
            # Add use alloc::vec; after extern crate alloc
            fixed = re.sub(
                r'(extern crate alloc;\s*\n)',
                r'\1\nuse alloc::{vec, vec::Vec};\n',
                fixed,
            )
        elif "use alloc::vec::Vec;" in fixed and "use alloc::vec;" not in fixed and "alloc::{" not in fixed:
            # Has Vec but not vec module — replace with combined import
            fixed = fixed.replace(
                "use alloc::vec::Vec;",
                "use alloc::{vec, vec::Vec};"
            )

        # Fix 7: Ensure there's exactly one sol_storage! block with #[entrypoint]
        sol_storage_count = len(re.findall(r'sol_storage!\s*\{', fixed))
        if sol_storage_count == 0 and template:
            # If no sol_storage! block, the code is likely broken - use template
            return template.lib_rs

        # Fix 8: Ensure #[entrypoint] is inside sol_storage! if missing
        if "#[entrypoint]" not in fixed:
            fixed = re.sub(
                r'sol_storage!\s*\{\s*(\n?\s*pub struct)',
                r'sol_storage! {\n    #[entrypoint]\1',
                fixed
            )

        return fixed

    @staticmethod
    def _derive_project_name(prompt: str) -> str:
        """Derive a snake_case project name from the user prompt."""
        stop_words = {"a", "an", "the", "for", "with", "and", "or", "that", "this", "create", "build", "make", "generate", "implement"}
        words = [w.lower() for w in re.findall(r'[a-zA-Z]+', prompt) if w.lower() not in stop_words]
        name_words = words[:3] if words else ["stylus", "contract"]
        return "_".join(name_words)

    def _build_fix_prompt(self, code: str, error_text: str) -> str:
        """Build a prompt asking the LLM to fix compilation errors.

        Args:
            code: Current lib.rs code that failed to compile.
            error_text: Formatted error details from format_errors_for_llm().

        Returns:
            Prompt string for the LLM.
        """
        return f"""The following Stylus contract code has compilation errors. Fix ONLY the errors — do not change the contract's functionality or structure.

CURRENT CODE:
```rust
{code}
```

COMPILATION ERRORS:
{error_text}

Fix the code and return the complete, corrected lib.rs in a ```rust code block.
Keep the exact same structure and functionality. Only fix the compilation errors."""

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

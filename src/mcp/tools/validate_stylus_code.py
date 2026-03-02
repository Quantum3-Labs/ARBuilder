"""
MCP Tool: validate_stylus_code

Compile-checks Stylus Rust code via Docker-based cargo check and returns
structured errors with Stylus-specific fix guidance.

This tool exposes the CompilerVerifier as a standalone MCP tool so the
client LLM can validate generated code and iterate on fixes.
"""

import logging
from typing import Optional

from .base import BaseTool

logger = logging.getLogger(__name__)

# Default Cargo.toml when none is provided
DEFAULT_CARGO_TOML = """\
[package]
name = "stylus_contract"
version = "0.1.0"
edition = "2021"

[dependencies]
stylus-sdk = "0.10.0"
alloy-primitives = "1.0.1"
alloy-sol-types = "1.0.1"

[dev-dependencies]
stylus-sdk = { version = "0.10.0", features = ["stylus-test"] }

[features]
export-abi = ["stylus-sdk/export-abi"]

[lib]
crate-type = ["lib", "cdylib"]

[[bin]]
name = "stylus_contract"
path = "src/main.rs"

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"
"""


class ValidateStylusCodeTool(BaseTool):
    """Validate Stylus Rust code by running cargo check via Docker.

    Returns structured compilation errors with Stylus-specific fix guidance
    that maps error codes to common SDK pitfalls and their solutions.
    """

    def __init__(self, **kwargs):
        # BaseTool requires an API key but this tool doesn't call LLMs.
        # Pass a dummy key if none is configured.
        import os
        if not os.getenv("OPENROUTER_API_KEY"):
            os.environ["OPENROUTER_API_KEY"] = "not-needed-for-validation"
        super().__init__(**kwargs)

        # Lazy-import to avoid hard dependency on Docker
        try:
            from src.utils.compiler_verifier import CompilerVerifier
            self.compiler = CompilerVerifier()
        except Exception:
            self.compiler = None

    def execute(
        self,
        code: str,
        cargo_toml: Optional[str] = None,
        main_rs: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """Validate Stylus code by compiling with cargo check.

        Args:
            code: lib.rs source code to validate.
            cargo_toml: Cargo.toml content (uses default if omitted).
            main_rs: main.rs content (uses minimal stub if omitted).

        Returns:
            Dict with valid, errors, warnings, fix_guidance, and raw_output.
        """
        error = self._validate_required({"code": code}, ["code"])
        if error:
            return {"error": error}

        if self.compiler is None or not self.compiler.is_available():
            return {
                "valid": None,
                "errors": [],
                "warnings": [],
                "fix_guidance": "",
                "raw_output": "",
                "skipped": True,
                "skip_reason": (
                    "Docker not available or arbbuilder-verify image "
                    "not found. Install Docker and build the verify "
                    "image to enable compilation checks."
                ),
            }

        # Use defaults if not provided
        if not cargo_toml:
            cargo_toml = DEFAULT_CARGO_TOML

        # Run cargo check
        result = self.compiler.verify(code, cargo_toml)

        if result.skipped:
            return {
                "valid": None,
                "errors": [],
                "warnings": [],
                "fix_guidance": "",
                "raw_output": "",
                "skipped": True,
                "skip_reason": result.skip_reason or "Verification skipped",
            }

        # Separate errors from warnings
        errors = [e for e in result.errors if e.level == "error"]
        warnings = [e for e in result.errors if e.level == "warning"]

        # Build fix guidance from error codes
        from src.utils.compiler_verifier import format_fix_guidance
        guidance = format_fix_guidance(errors)

        return {
            "valid": result.success,
            "errors": [
                {
                    "code": e.code,
                    "message": e.message,
                    "line": e.line,
                    "column": e.column,
                    "suggestion": e.suggestion,
                }
                for e in errors
            ],
            "warnings": [
                {
                    "code": e.code,
                    "message": e.message,
                    "line": e.line,
                    "column": e.column,
                    "suggestion": e.suggestion,
                }
                for e in warnings
            ],
            "fix_guidance": guidance,
            "raw_output": result.raw_output,
            "skipped": False,
        }

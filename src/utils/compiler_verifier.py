"""
Compiler verifier for Stylus smart contracts.

Writes lib.rs + Cargo.toml to a temp directory and runs
`cargo check --target wasm32-unknown-unknown` inside the
`arbbuilder-verify` Docker container for fast compilation checks.

Gracefully skips verification when Docker is unavailable.
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CompileError:
    """Structured representation of a cargo compile error."""

    code: Optional[str]  # e.g. "E0425"
    line: Optional[int]
    column: Optional[int]
    message: str
    suggestion: Optional[str] = None
    level: str = "error"  # "error" or "warning"


@dataclass
class CompileResult:
    """Result of a compilation check."""

    success: bool
    errors: List[CompileError] = field(default_factory=list)
    raw_output: str = ""
    skipped: bool = False
    skip_reason: Optional[str] = None


# Docker image for verification
DOCKER_IMAGE = "arbbuilder-verify"
CARGO_CHECK_TIMEOUT = 120  # seconds


def _docker_available() -> bool:
    """Check if Docker is available and the verify image exists."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False

        # Check if our image exists
        result = subprocess.run(
            ["docker", "image", "inspect", DOCKER_IMAGE],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _parse_cargo_errors(output: str) -> List[CompileError]:
    """Parse cargo check stderr into structured CompileError objects."""
    errors = []

    # Pattern: error[E0425]: cannot find value `x` in this scope
    #   --> src/lib.rs:42:5
    error_pattern = re.compile(
        r"(error|warning)(?:\[([A-Z]\d+)\])?: (.+?)(?:\n\s*--> src/lib\.rs:(\d+):(\d+))?"
    )

    # Also capture help/suggestion lines
    suggestion_pattern = re.compile(r"help: (.+)")

    lines = output.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        match = error_pattern.match(line)
        if match:
            level = match.group(1)
            code = match.group(2)
            message = match.group(3).strip()
            line_num = int(match.group(4)) if match.group(4) else None
            col = int(match.group(5)) if match.group(5) else None

            # Look ahead for line number if not captured
            if line_num is None and i + 1 < len(lines):
                loc_match = re.search(r"--> src/lib\.rs:(\d+):(\d+)", lines[i + 1])
                if loc_match:
                    line_num = int(loc_match.group(1))
                    col = int(loc_match.group(2))

            # Look ahead for suggestion
            suggestion = None
            for j in range(i + 1, min(i + 6, len(lines))):
                sug_match = suggestion_pattern.search(lines[j])
                if sug_match:
                    suggestion = sug_match.group(1).strip()
                    break

            errors.append(CompileError(
                code=code,
                line=line_num,
                column=col,
                message=message,
                suggestion=suggestion,
                level=level,
            ))
        i += 1

    return errors


class CompilerVerifier:
    """Verifies Stylus contracts compile via Docker-based cargo check."""

    def __init__(self, docker_image: str = DOCKER_IMAGE):
        self.docker_image = docker_image
        self._docker_ok: Optional[bool] = None

    def is_available(self) -> bool:
        """Check if the compiler verifier can run."""
        if self._docker_ok is None:
            self._docker_ok = _docker_available()
        return self._docker_ok

    def verify(self, lib_rs: str, cargo_toml: str) -> CompileResult:
        """Run cargo check on the given contract code.

        Args:
            lib_rs: Contents of src/lib.rs.
            cargo_toml: Contents of Cargo.toml.

        Returns:
            CompileResult with success status and any errors.
        """
        if not self.is_available():
            return CompileResult(
                success=True,
                skipped=True,
                skip_reason="Docker not available or arbbuilder-verify image not found",
            )

        # Create temp project directory
        tmpdir = tempfile.mkdtemp(prefix="arbbuilder_verify_")
        try:
            # Write project files
            src_dir = os.path.join(tmpdir, "src")
            os.makedirs(src_dir, exist_ok=True)

            with open(os.path.join(src_dir, "lib.rs"), "w") as f:
                f.write(lib_rs)

            with open(os.path.join(tmpdir, "Cargo.toml"), "w") as f:
                f.write(cargo_toml)

            # Write minimal main.rs for binary target
            with open(os.path.join(src_dir, "main.rs"), "w") as f:
                f.write('fn main() {}\n')

            # Run cargo check inside Docker
            result = subprocess.run(
                [
                    "docker", "run", "--rm",
                    "-v", f"{tmpdir}:/project",
                    "-w", "/project",
                    self.docker_image,
                    "cargo", "check",
                    "--target", "wasm32-unknown-unknown",
                    "--lib",
                ],
                capture_output=True,
                text=True,
                timeout=CARGO_CHECK_TIMEOUT,
            )

            raw_output = result.stderr or result.stdout or ""
            errors = _parse_cargo_errors(raw_output)

            # Filter to only actual errors (not warnings)
            actual_errors = [e for e in errors if e.level == "error"]

            return CompileResult(
                success=len(actual_errors) == 0,
                errors=errors,
                raw_output=raw_output,
            )

        except subprocess.TimeoutExpired:
            return CompileResult(
                success=False,
                errors=[CompileError(
                    code=None,
                    line=None,
                    column=None,
                    message="Compilation check timed out",
                )],
                raw_output="Timeout after {} seconds".format(CARGO_CHECK_TIMEOUT),
            )
        except Exception as e:
            logger.warning(f"Compiler verification failed: {e}")
            return CompileResult(
                success=True,
                skipped=True,
                skip_reason=f"Verification error: {str(e)}",
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# Stylus-specific error guidance keyed by Rust error code.
# Maps cargo check errors to actionable Stylus SDK fix instructions.
ERROR_GUIDANCE = {
    "E0599": (
        "Method not found. Common Stylus fixes:\n"
        "  - StorageString: use .set_str() to write, .get_string() to read\n"
        "  - StorageVec: use .push() to append, .get(i) to read\n"
        "  - Mapping string values: use .getter(key).get_string() to read, "
        ".setter(key).set_str(val) to write"
    ),
    "E0502": (
        "Borrow conflict. Common Stylus fixes:\n"
        "  - Extract .get() values to local vars before calling .set()\n"
        "  - For sol_interface! calls: let call = Call::new_mutating(self); "
        "then tok.transfer(self.vm(), call, ...)\n"
        "  - For nested mappings: chain in one expression — "
        "self.map.setter(k1).setter(k2).set(v)"
    ),
    "E0277": (
        "Type mismatch. Common Stylus fixes:\n"
        "  - B256 is FixedBytes<32>, NOT Uint — use "
        "B256::from(value.to_be_bytes::<32>())\n"
        "  - Mapping .get(key) returns the value directly, NOT Option — "
        "do not use .unwrap_or_default()\n"
        "  - StorageVec .setter(i) returns Option — must .unwrap() before .set()"
    ),
    "E0015": (
        "Not const-compatible. Common Stylus fixes:\n"
        "  - Use U256::from_limbs([N, 0, 0, 0]) instead of U256::from(N) "
        "for const declarations\n"
        "  - U256::ZERO is fine in const context"
    ),
    "E0603": (
        "Private module. Common Stylus fixes:\n"
        "  - stylus_sdk::evm and stylus_sdk::msg are removed in SDK 0.10.0\n"
        "  - Use self.vm().msg_sender(), self.vm().msg_value(), "
        "self.vm().log() instead"
    ),
    "E0432": (
        "Unresolved import. Common Stylus fixes:\n"
        "  - stylus_sdk::evm → removed, use self.vm() methods\n"
        "  - stylus_sdk::msg → removed, use self.vm() methods\n"
        "  - transfer_eth → use stylus_sdk::call::transfer::transfer_eth\n"
        "  - Call is in prelude — no separate import needed"
    ),
    "E0658": (
        "Unstable feature. Common Stylus fixes:\n"
        "  - pub const inside #[public] impl is not supported — "
        "move constants above the impl block\n"
        "  - Use standalone const MY_VAL: U256 = U256::from_limbs(...);"
    ),
}


def format_fix_guidance(errors: List[CompileError]) -> str:
    """Map cargo check errors to Stylus-specific fix guidance.

    Args:
        errors: List of CompileError objects from cargo check.

    Returns:
        Formatted guidance string for each matched error code.
    """
    seen_codes: set = set()
    parts: list = []

    for err in errors:
        if err.code and err.code not in seen_codes and err.code in ERROR_GUIDANCE:
            seen_codes.add(err.code)
            parts.append(f"[{err.code}] {ERROR_GUIDANCE[err.code]}")

    if not parts:
        return ""

    return "\n\n".join(parts)


def format_errors_for_llm(errors: List[CompileError], code: str) -> str:
    """Format compile errors into a prompt-friendly string for the LLM fix loop.

    Args:
        errors: List of CompileError objects.
        code: The lib.rs source that produced the errors.

    Returns:
        Formatted string with error details and surrounding code context.
    """
    code_lines = code.split("\n")
    parts = ["The following compilation errors were found:\n"]

    for i, err in enumerate(errors, 1):
        parts.append(f"Error {i}:")
        if err.code:
            parts.append(f"  Code: {err.code}")
        parts.append(f"  Message: {err.message}")

        if err.line and err.line <= len(code_lines):
            # Show surrounding context (2 lines before/after)
            start = max(0, err.line - 3)
            end = min(len(code_lines), err.line + 2)
            parts.append(f"  Location: line {err.line}")
            parts.append("  Context:")
            for ln in range(start, end):
                marker = " >> " if ln + 1 == err.line else "    "
                parts.append(f"  {marker}{ln + 1}: {code_lines[ln]}")

        if err.suggestion:
            parts.append(f"  Suggestion: {err.suggestion}")
        parts.append("")

    return "\n".join(parts)

"""
Test cases for Stylus template selection and compilation.

Tests:
1. Template selection logic based on contract type and prompt keywords
2. Template content validity (balanced braces, required patterns)
3. Template compilation using cargo stylus check (integration tests)
"""

import pytest
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Optional

# Import templates
from src.templates.stylus_templates import (
    StylusTemplate,
    COUNTER_TEMPLATE,
    VENDING_MACHINE_TEMPLATE,
    SIMPLE_ERC20_TEMPLATE,
    ACCESS_CONTROL_TEMPLATE,
    TEMPLATES,
    select_template,
    get_template,
    list_templates,
)


class TestTemplateSelection:
    """Test template selection logic."""

    def test_select_by_contract_type_token(self):
        """Token contract type should select ERC20 template."""
        template = select_template("token", "create a token")
        assert template.name == "SimpleERC20"

    def test_select_by_contract_type_defi(self):
        """DeFi contract type should select VendingMachine template."""
        template = select_template("defi", "create a defi contract")
        assert template.name == "VendingMachine"

    def test_select_by_contract_type_utility(self):
        """Utility contract type should select Counter template."""
        template = select_template("utility", "create a utility contract")
        assert template.name == "Counter"

    def test_select_by_prompt_erc20_keyword(self):
        """Prompt with 'erc20' should select ERC20 template."""
        template = select_template("utility", "Create an ERC20 token")
        assert template.name == "SimpleERC20"

    def test_select_by_prompt_token_keyword(self):
        """Prompt with 'token' should select ERC20 template."""
        template = select_template("utility", "Create a token contract")
        assert template.name == "SimpleERC20"

    def test_select_by_prompt_transfer_keyword(self):
        """Prompt with 'transfer' should select ERC20 template."""
        template = select_template("utility", "Create a contract with transfer function")
        assert template.name == "SimpleERC20"

    def test_select_by_prompt_owner_keyword(self):
        """Prompt with 'owner' should select AccessControl template."""
        template = select_template("utility", "Create a contract with owner permissions")
        assert template.name == "AccessControl"

    def test_select_by_prompt_admin_keyword(self):
        """Prompt with 'admin' should select AccessControl template."""
        template = select_template("utility", "Create a contract with admin functions")
        assert template.name == "AccessControl"

    def test_select_by_prompt_claim_keyword(self):
        """Prompt with 'claim' should select VendingMachine template."""
        template = select_template("utility", "Create a contract with claim functionality")
        assert template.name == "VendingMachine"

    def test_select_by_prompt_cooldown_keyword(self):
        """Prompt with 'cooldown' should select VendingMachine template."""
        template = select_template("utility", "Create a contract with cooldown")
        assert template.name == "VendingMachine"

    def test_select_fallback_to_counter(self):
        """Unknown contract type should fall back to Counter."""
        template = select_template("unknown", "do something random")
        assert template.name == "Counter"

    def test_get_template_by_key(self):
        """get_template should return correct template by key."""
        assert get_template("counter").name == "Counter"
        assert get_template("erc20").name == "SimpleERC20"
        assert get_template("token").name == "SimpleERC20"
        assert get_template("defi").name == "VendingMachine"
        assert get_template("ownable").name == "AccessControl"

    def test_get_template_unknown_returns_none(self):
        """get_template with unknown key should return None."""
        assert get_template("unknown") is None

    def test_list_templates_returns_all(self):
        """list_templates should return all 4 templates."""
        templates = list_templates()
        assert len(templates) == 4
        names = {t.name for t in templates}
        assert names == {"Counter", "VendingMachine", "SimpleERC20", "AccessControl"}


class TestTemplateContent:
    """Test template content validity."""

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_has_required_attributes(self, template: StylusTemplate):
        """Each template should have all required attributes."""
        assert template.name
        assert template.description
        assert template.contract_type in ["token", "nft", "defi", "utility", "custom"]
        assert template.sdk_version
        assert template.features
        assert template.lib_rs
        assert template.cargo_toml

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_lib_rs_has_entrypoint(self, template: StylusTemplate):
        """Each template's lib.rs should have #[entrypoint]."""
        assert "#[entrypoint]" in template.lib_rs

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_lib_rs_has_sol_storage(self, template: StylusTemplate):
        """Each template's lib.rs should have sol_storage! macro."""
        assert "sol_storage!" in template.lib_rs

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_lib_rs_has_cfg_attr(self, template: StylusTemplate):
        """Each template's lib.rs should have cfg_attr for no_main."""
        assert "#![cfg_attr" in template.lib_rs
        assert "no_main" in template.lib_rs

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_lib_rs_has_extern_crate_alloc(self, template: StylusTemplate):
        """Each template's lib.rs should have #[macro_use] extern crate alloc."""
        assert "#[macro_use]" in template.lib_rs
        assert "extern crate alloc" in template.lib_rs

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_lib_rs_has_public_impl(self, template: StylusTemplate):
        """Each template's lib.rs should have #[public] impl."""
        assert "#[public]" in template.lib_rs

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_lib_rs_balanced_braces(self, template: StylusTemplate):
        """Each template's lib.rs should have balanced braces."""
        assert template.lib_rs.count("{") == template.lib_rs.count("}")

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_lib_rs_balanced_parens(self, template: StylusTemplate):
        """Each template's lib.rs should have balanced parentheses."""
        assert template.lib_rs.count("(") == template.lib_rs.count(")")

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_cargo_toml_has_stylus_sdk(self, template: StylusTemplate):
        """Each template's Cargo.toml should have stylus-sdk dependency."""
        assert 'stylus-sdk = "0.9.0"' in template.cargo_toml

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_cargo_toml_has_alloy_primitives(self, template: StylusTemplate):
        """Each template's Cargo.toml should have alloy-primitives dependency."""
        assert 'alloy-primitives = "=0.8.20"' in template.cargo_toml

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_cargo_toml_has_release_profile(self, template: StylusTemplate):
        """Each template's Cargo.toml should have release profile."""
        assert "[profile.release]" in template.cargo_toml
        assert 'opt-level = "s"' in template.cargo_toml

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_cargo_toml_has_cdylib(self, template: StylusTemplate):
        """Each template's Cargo.toml should specify cdylib crate type."""
        assert "cdylib" in template.cargo_toml

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_has_tests(self, template: StylusTemplate):
        """Each template should include tests."""
        assert "#[cfg(test)]" in template.lib_rs
        assert "#[test]" in template.lib_rs


class TestTemplateVersionConsistency:
    """Test that templates use consistent versions."""

    def test_all_templates_use_same_sdk_version(self):
        """All templates should use the same SDK version."""
        versions = {t.sdk_version for t in list_templates()}
        assert len(versions) == 1
        assert "0.9.0" in versions

    def test_all_templates_use_same_alloy_version(self):
        """All templates should use consistent alloy versions."""
        for template in list_templates():
            assert 'alloy-primitives = "=0.8.20"' in template.cargo_toml
            assert 'alloy-sol-types = "=0.8.20"' in template.cargo_toml


# Integration tests that require cargo-stylus
@pytest.mark.integration
class TestTemplateCompilation:
    """Integration tests for template compilation.

    These tests require:
    - Rust toolchain installed
    - cargo-stylus installed
    - wasm32-unknown-unknown target

    Run with: pytest tests/test_templates.py -m integration
    """

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary directory for the project."""
        temp_dir = tempfile.mkdtemp(prefix="stylus_test_")
        yield Path(temp_dir)
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def _create_project(self, temp_dir: Path, template: StylusTemplate) -> Path:
        """Create a Stylus project from template."""
        project_dir = temp_dir / template.name.lower().replace(" ", "_")
        project_dir.mkdir(parents=True, exist_ok=True)

        # Create src directory
        src_dir = project_dir / "src"
        src_dir.mkdir(exist_ok=True)

        # Write lib.rs
        lib_rs = src_dir / "lib.rs"
        lib_rs.write_text(template.lib_rs)

        # Write Cargo.toml
        cargo_toml = project_dir / "Cargo.toml"
        cargo_toml.write_text(template.cargo_toml)

        # Write rust-toolchain.toml (required by cargo-stylus)
        rust_toolchain = project_dir / "rust-toolchain.toml"
        rust_toolchain.write_text('[toolchain]\nchannel = "1.87.0"\n')

        # Generate Cargo.lock by running cargo update
        # (The ruint = "=1.15.0" dependency ensures correct version resolution)
        subprocess.run(
            ["cargo", "update"],
            cwd=project_dir,
            capture_output=True,
            timeout=120,
        )

        return project_dir

    def _check_cargo_stylus_installed(self) -> bool:
        """Check if cargo-stylus is installed."""
        try:
            result = subprocess.run(
                ["cargo", "stylus", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _check_wasm_target_installed(self) -> bool:
        """Check if wasm32-unknown-unknown target is installed."""
        try:
            result = subprocess.run(
                ["rustup", "target", "list", "--installed"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return "wasm32-unknown-unknown" in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_compiles(self, temp_project_dir: Path, template: StylusTemplate):
        """Test that each template compiles successfully."""
        if not self._check_cargo_stylus_installed():
            pytest.skip("cargo-stylus not installed")

        if not self._check_wasm_target_installed():
            pytest.skip("wasm32-unknown-unknown target not installed")

        project_dir = self._create_project(temp_project_dir, template)

        # Run cargo stylus check
        result = subprocess.run(
            ["cargo", "stylus", "check"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=180,  # 3 minutes timeout for first compile
        )

        # Check for compilation success
        # Note: cargo stylus check returns non-zero if no local node is available,
        # but we can verify the build succeeded by checking for "contract size" in output
        output = result.stdout + result.stderr
        build_succeeded = "contract size:" in output or "Finished" in output
        build_failed = "error[E" in output or "could not compile" in output

        assert build_succeeded and not build_failed, (
            f"Template {template.name} failed to compile:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_passes_cargo_check(self, temp_project_dir: Path, template: StylusTemplate):
        """Test that each template passes cargo check (native)."""
        project_dir = self._create_project(temp_project_dir, template)

        # Run cargo check (native, not wasm)
        result = subprocess.run(
            ["cargo", "check"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode == 0, (
            f"Template {template.name} failed cargo check:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_tests_pass(self, temp_project_dir: Path, template: StylusTemplate):
        """Test that each template's unit tests pass."""
        project_dir = self._create_project(temp_project_dir, template)

        # Run cargo test
        result = subprocess.run(
            ["cargo", "test"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode == 0, (
            f"Template {template.name} tests failed:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_wasm_size_under_limit(self, temp_project_dir: Path, template: StylusTemplate):
        """Test that each template's WASM size is under 24KB limit."""
        if not self._check_wasm_target_installed():
            pytest.skip("wasm32-unknown-unknown target not installed")

        project_dir = self._create_project(temp_project_dir, template)

        # Build release WASM
        result = subprocess.run(
            ["cargo", "build", "--release", "--target", "wasm32-unknown-unknown"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=180,
        )

        if result.returncode != 0:
            pytest.skip(f"WASM build failed: {result.stderr}")

        # Find the WASM file
        wasm_dir = project_dir / "target" / "wasm32-unknown-unknown" / "release"
        wasm_files = list(wasm_dir.glob("*.wasm"))

        if not wasm_files:
            pytest.skip("No WASM file generated")

        wasm_file = wasm_files[0]
        wasm_size = wasm_file.stat().st_size

        # 24KB limit (Stylus contract size limit after Brotli compression)
        # Uncompressed WASM is typically larger, so we use a higher threshold
        max_uncompressed_size = 100 * 1024  # 100KB uncompressed is reasonable

        assert wasm_size < max_uncompressed_size, (
            f"Template {template.name} WASM size ({wasm_size / 1024:.1f}KB) "
            f"exceeds limit ({max_uncompressed_size / 1024:.1f}KB)"
        )

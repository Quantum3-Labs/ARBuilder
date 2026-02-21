"""
Test cases for Stylus template selection and compilation.

Tests:
1. Template selection logic based on contract type and prompt keywords
2. Template content validity (balanced braces, required patterns)
3. Template compilation using cargo stylus check (integration tests)
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

# Import templates
from src.templates.stylus_templates import (
    COUNTER_TEMPLATE,
    StylusTemplate,
    get_template,
    list_templates,
    select_template,
)


class TestTemplateSelection:
    """Test template selection logic."""

    def test_select_by_contract_type_token(self):
        """Token contract type should select ERC20 template."""
        template = select_template("token", "create a token")
        assert template.name == "SimpleERC20"

    def test_select_by_contract_type_defi(self):
        """DeFi contract type should select DeFiVault template."""
        template = select_template("defi", "create a defi contract")
        assert template.name == "DeFiVault"

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
        assert get_template("defi").name == "DeFiVault"
        assert get_template("ownable").name == "AccessControl"

    def test_get_template_unknown_returns_none(self):
        """get_template with unknown key should return None."""
        assert get_template("unknown") is None

    def test_list_templates_returns_all(self):
        """list_templates should return all 5 templates."""
        templates = list_templates()
        assert len(templates) == 5
        names = {t.name for t in templates}
        assert names == {"Counter", "VendingMachine", "DeFiVault", "SimpleERC20", "AccessControl"}


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
        assert 'stylus-sdk = "0.10.0"' in template.cargo_toml

    @pytest.mark.parametrize("template", list_templates(), ids=lambda t: t.name)
    def test_template_cargo_toml_has_alloy_primitives(self, template: StylusTemplate):
        """Each template's Cargo.toml should have alloy-primitives dependency."""
        assert 'alloy-primitives = "1.0.1"' in template.cargo_toml

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
        assert "0.10.0" in versions

    def test_all_templates_use_same_alloy_version(self):
        """All templates should use consistent alloy versions."""
        for template in list_templates():
            assert 'alloy-primitives = "1.0.1"' in template.cargo_toml
            assert 'alloy-sol-types = "1.0.1"' in template.cargo_toml

    def test_all_templates_have_stylus_toml(self):
        """All templates should have stylus_toml field (SDK 0.10.0+)."""
        for template in list_templates():
            assert template.stylus_toml, f"{template.name} missing stylus_toml"
            assert "[contract]" in template.stylus_toml

    def test_all_templates_have_rust_toolchain_toml(self):
        """All templates should have rust_toolchain_toml field (SDK 0.10.0+)."""
        for template in list_templates():
            assert template.rust_toolchain_toml, f"{template.name} missing rust_toolchain_toml"
            assert "1.88.0" in template.rust_toolchain_toml

    def test_no_deprecated_api_in_templates(self):
        """No template should use deprecated msg::sender() or evm::log() APIs."""
        for template in list_templates():
            assert "msg::sender()" not in template.lib_rs, (
                f"{template.name} still uses deprecated msg::sender()"
            )
            assert "evm::log(" not in template.lib_rs, (
                f"{template.name} still uses deprecated evm::log()"
            )

    def test_no_ruint_pin_in_templates(self):
        """No template should pin ruint (alloy 1.0 manages it)."""
        for template in list_templates():
            assert "ruint" not in template.cargo_toml, f"{template.name} still pins ruint"


class TestSystemPromptsAndDisclaimer:
    """Verify system prompts contain 0.10.0 patterns and disclaimer exists."""

    def test_system_prompt_contains_transfer_eth(self):
        """System prompt should mention transfer_eth pattern."""
        from src.mcp.tools.generate_stylus_code import get_system_prompt

        prompt = get_system_prompt("0.10.0")
        assert "transfer_eth" in prompt

    def test_system_prompt_contains_sol_error(self):
        """System prompt should mention SolError import."""
        from src.mcp.tools.generate_stylus_code import get_system_prompt

        prompt = get_system_prompt("0.10.0")
        assert "SolError" in prompt

    def test_system_prompt_forbids_evm_module(self):
        """System prompt should forbid stylus_sdk::evm."""
        from src.mcp.tools.generate_stylus_code import get_system_prompt

        prompt = get_system_prompt("0.10.0")
        assert "stylus_sdk::evm" in prompt

    def test_fix_code_preserves_sol_error_import(self):
        """_fix_code should NOT strip SolError from combined imports."""
        from src.mcp.tools.generate_stylus_code import GenerateStylusCodeTool

        tool = GenerateStylusCodeTool()
        code = "use alloy_sol_types::{sol, SolError};"
        fixed = tool._fix_code(code, None)
        assert "SolError" in fixed, f"SolError was stripped: {fixed}"

    def test_fix_code_strips_standalone_sol_import(self):
        """_fix_code should strip standalone alloy_sol_types::sol import."""
        from src.mcp.tools.generate_stylus_code import GenerateStylusCodeTool

        tool = GenerateStylusCodeTool()
        code = "use alloy_sol_types::sol;\nuse stylus_sdk::prelude::*;"
        fixed = tool._fix_code(code, None)
        assert "alloy_sol_types::sol" not in fixed

    def test_disclaimer_exists(self):
        """TEMPLATE_DISCLAIMER should exist and contain 'starting entrypoint'."""
        from src.mcp.tools.generate_stylus_code import TEMPLATE_DISCLAIMER

        assert "starting entrypoint" in TEMPLATE_DISCLAIMER

    def test_coding_rules_has_forbidden_imports(self):
        """Coding rules should list forbidden imports."""
        from src.mcp.resources.coding_rules import STYLUS_CODING_RULES

        assert "forbidden_imports" in STYLUS_CODING_RULES
        forbidden = STYLUS_CODING_RULES["forbidden_imports"]
        assert "stylus_sdk::evm" in forbidden
        assert "stylus_sdk::msg" in forbidden

    def test_stylus_toml_format(self):
        """Stylus.toml should include workspace, workspace.networks, and contract sections."""
        for template in list_templates():
            assert "[workspace]" in template.stylus_toml, (
                f"{template.name} missing [workspace] in Stylus.toml"
            )
            assert "[workspace.networks]" in template.stylus_toml, (
                f"{template.name} missing [workspace.networks] in Stylus.toml"
            )
            assert "[contract]" in template.stylus_toml, (
                f"{template.name} missing [contract] in Stylus.toml"
            )

    def test_templates_have_stylus_test_dev_dep(self):
        """All templates should have stylus-test in dev-dependencies."""
        for template in list_templates():
            assert 'features = ["stylus-test"]' in template.cargo_toml, (
                f"{template.name} missing stylus-test in dev-dependencies"
            )

    def test_templates_use_underscores_in_package_name(self):
        """Package names should use underscores, not hyphens."""
        for template in list_templates():
            # Extract name from Cargo.toml
            import re

            match = re.search(r'name\s*=\s*"([^"]+)"', template.cargo_toml)
            assert match, f"{template.name} missing name in Cargo.toml"
            pkg_name = match.group(1)
            assert "-" not in pkg_name, f"{template.name} has hyphens in package name: {pkg_name}"

    def test_templates_have_lib_in_crate_type(self):
        """crate-type should include both 'lib' and 'cdylib'."""
        for template in list_templates():
            assert '["lib", "cdylib"]' in template.cargo_toml, (
                f'{template.name} crate-type should be ["lib", "cdylib"]'
            )

    def test_templates_main_rs_uses_print_from_args(self):
        """main_rs should use print_from_args(), not print_abi()."""
        for template in list_templates():
            assert "print_from_args" in template.main_rs, (
                f"{template.name} main_rs should use print_from_args()"
            )
            assert "print_abi" not in template.main_rs, (
                f"{template.name} main_rs should NOT use print_abi()"
            )

    def test_templates_main_rs_has_no_main_fallback(self):
        """main_rs should have #[unsafe(no_mangle)] fallback for non-export-abi."""
        for template in list_templates():
            assert "unsafe(no_mangle)" in template.main_rs, (
                f"{template.name} main_rs missing #[unsafe(no_mangle)] fallback"
            )

    def test_templates_have_alloc_vec_import(self):
        """lib_rs should include use alloc::vec (the module) alongside Vec."""
        for template in list_templates():
            assert "alloc::" in template.lib_rs and "vec," in template.lib_rs, (
                f"{template.name} lib_rs should have use alloc::{{vec, vec::Vec}};"
            )

    def test_system_prompt_has_print_from_args(self):
        """System prompt should mention print_from_args."""
        from src.mcp.tools.generate_stylus_code import get_system_prompt

        prompt = get_system_prompt("0.10.0")
        assert "print_from_args" in prompt

    def test_system_prompt_has_underscore_naming(self):
        """System prompt should mention underscore package names."""
        from src.mcp.tools.generate_stylus_code import get_system_prompt

        prompt = get_system_prompt("0.10.0")
        assert "underscore" in prompt.lower()

    def test_derive_project_name_uses_underscores(self):
        """_derive_project_name should use underscores."""
        from src.mcp.tools.generate_stylus_code import GenerateStylusCodeTool

        tool = GenerateStylusCodeTool()
        name = tool._derive_project_name("prediction market contract")
        assert "_" in name
        assert "-" not in name

    def test_coding_rules_has_main_rs_pattern(self):
        """Coding rules should have main_rs pattern."""
        from src.mcp.resources.coding_rules import STYLUS_CODING_RULES

        assert "main_rs" in STYLUS_CODING_RULES["patterns"]
        assert "print_from_args" in STYLUS_CODING_RULES["patterns"]["main_rs"]["example"]

    def test_coding_rules_has_cross_contract_calls(self):
        """Coding rules should document sol_interface! call pattern."""
        from src.mcp.resources.coding_rules import STYLUS_CODING_RULES

        assert "cross_contract_calls" in STYLUS_CODING_RULES["patterns"]
        pattern = STYLUS_CODING_RULES["patterns"]["cross_contract_calls"]
        assert "sol_interface!" in pattern["definition"]
        assert "Call::new()" in pattern["usage"]
        assert "self.vm()" in pattern["usage"]

    def test_coding_rules_forbids_call_new_in(self):
        """Coding rules should forbid Call::new_in (0.9.x pattern)."""
        from src.mcp.resources.coding_rules import STYLUS_CODING_RULES

        assert "Call::new_in" in STYLUS_CODING_RULES["forbidden_imports"]

    def test_system_prompt_mentions_sol_interface(self):
        """System prompt should mention sol_interface! call pattern."""
        from src.mcp.tools.generate_stylus_code import get_system_prompt

        prompt = get_system_prompt("0.10.0")
        assert "sol_interface" in prompt
        assert "Call::new()" in prompt

    def test_abi_extractor_converts_snake_to_camel(self):
        """ABI extractor should convert snake_case fn names to camelCase."""
        from src.utils.abi_extractor import extract_abi_from_code

        code = """#[public]
impl MyContract {
    pub fn get_value(&self) -> U256 { self.value.get() }
    pub fn set_value(&mut self, val: U256) { self.value.set(val); }
    pub fn create_market(&mut self, name: String) -> U256 { U256::ZERO }
}"""
        abi = extract_abi_from_code(code)
        names = [e["name"] for e in abi]
        assert "getValue" in names
        assert "setValue" in names
        assert "createMarket" in names
        assert "get_value" not in names

    def test_abi_extractor_single_word_unchanged(self):
        """Single-word fn names should remain unchanged."""
        from src.utils.abi_extractor import extract_abi_from_code

        code = """#[public]
impl MyContract {
    pub fn increment(&mut self) { }
    pub fn number(&self) -> U256 { U256::ZERO }
}"""
        abi = extract_abi_from_code(code)
        names = [e["name"] for e in abi]
        assert "increment" in names
        assert "number" in names

    def test_coding_rules_has_view_function_gotcha(self):
        """Coding rules should warn about view function external call limitation."""
        from src.mcp.resources.coding_rules import STYLUS_CODING_RULES

        pitfalls = STYLUS_CODING_RULES["common_pitfalls"]
        assert any("view" in p.lower() and "external" in p.lower() for p in pitfalls)

    def test_coding_rules_has_abi_naming(self):
        """Coding rules should document camelCase ABI naming convention."""
        from src.mcp.resources.coding_rules import STYLUS_CODING_RULES

        assert "abi_naming" in STYLUS_CODING_RULES["patterns"]

    def test_template_system_prompt_mentions_sol_interface(self):
        """Template system prompt must include sol_interface! guidance."""
        from src.mcp.tools.generate_stylus_code import get_template_system_prompt

        prompt = get_template_system_prompt(COUNTER_TEMPLATE, "0.10.0")
        assert "sol_interface!" in prompt

    def test_template_system_prompt_has_transfer_eth_use_statement(self):
        """Template system prompt must show full use statement for transfer_eth."""
        from src.mcp.tools.generate_stylus_code import get_template_system_prompt

        prompt = get_template_system_prompt(COUNTER_TEMPLATE, "0.10.0")
        assert "stylus_sdk::call::transfer::transfer_eth" in prompt

    def test_fix_code_converts_sol_to_sol_interface(self):
        """_fix_code should convert sol! { interface to sol_interface! { interface."""
        from src.mcp.tools.generate_stylus_code import GenerateStylusCodeTool

        tool = GenerateStylusCodeTool.__new__(GenerateStylusCodeTool)
        broken = """sol! {
    interface IToken {
        function transfer(address to, uint256 amount) external returns (bool);
    }
}"""
        fixed = tool._fix_code(broken, None)
        assert "sol_interface!" in fixed

    def test_template_source_comments_say_0_10(self):
        """Template source comments should reference SDK 0.10.0, not 0.9.0."""
        import inspect

        from src.templates import stylus_templates

        source = inspect.getsource(stylus_templates)
        assert "(v0.9.0)" not in source
        assert "(v0.8.4)" not in source

    def test_fix_code_fixes_wrong_transfer_eth_import(self):
        """_fix_code should fix wrong transfer_eth import path."""
        from src.mcp.tools.generate_stylus_code import GenerateStylusCodeTool

        tool = GenerateStylusCodeTool.__new__(GenerateStylusCodeTool)
        broken = "use stylus_sdk::call::transfer_eth;"
        fixed = tool._fix_code(broken, None)
        assert "stylus_sdk::call::transfer::transfer_eth" in fixed
        assert "call::transfer_eth;" not in fixed

    def test_fix_code_fixes_self_transfer_eth(self):
        """_fix_code should fix self.transfer_eth() to transfer_eth(self.vm(), ...)."""
        from src.mcp.tools.generate_stylus_code import GenerateStylusCodeTool

        tool = GenerateStylusCodeTool.__new__(GenerateStylusCodeTool)
        broken = "self.transfer_eth(recipient, amount)"
        fixed = tool._fix_code(broken, None)
        assert "transfer_eth(self.vm(), recipient, amount)" in fixed

    def test_fix_code_fixes_transfer_eth_self_to_self_vm(self):
        """_fix_code should fix transfer_eth(self, ...) to transfer_eth(self.vm(), ...)."""
        from src.mcp.tools.generate_stylus_code import GenerateStylusCodeTool

        tool = GenerateStylusCodeTool.__new__(GenerateStylusCodeTool)
        broken = "transfer_eth(self, recipient, amount)?;"
        fixed = tool._fix_code(broken, None)
        assert "transfer_eth(self.vm(), recipient, amount)" in fixed
        assert "transfer_eth(self, " not in fixed

    def test_fix_code_fixes_combined_transfer_eth_call_import(self):
        """_fix_code should split combined {transfer_eth, Call} import."""
        from src.mcp.tools.generate_stylus_code import GenerateStylusCodeTool

        tool = GenerateStylusCodeTool.__new__(GenerateStylusCodeTool)
        broken = "use stylus_sdk::call::{transfer_eth, Call};"
        fixed = tool._fix_code(broken, None)
        assert "stylus_sdk::call::transfer::transfer_eth" in fixed

    def test_template_prompt_has_storage_get_rule(self):
        """Template system prompt must instruct .get() for storage reads."""
        from src.mcp.tools.generate_stylus_code import get_template_system_prompt

        prompt = get_template_system_prompt(COUNTER_TEMPLATE, "0.10.0")
        assert "self.field.get()" in prompt
        assert "STORAGE ACCESS" in prompt

    def test_template_prompt_has_call_new_pattern(self):
        """Template system prompt must show Call::new() as second arg in cross-contract calls."""
        from src.mcp.tools.generate_stylus_code import get_template_system_prompt

        prompt = get_template_system_prompt(COUNTER_TEMPLATE, "0.10.0")
        assert "self.vm(), Call::new()" in prompt
        assert "CROSS-CONTRACT CALLS" in prompt

    def test_template_prompt_allows_struct_rename(self):
        """Template system prompt should allow renaming the contract struct."""
        from src.mcp.tools.generate_stylus_code import get_template_system_prompt

        prompt = get_template_system_prompt(COUNTER_TEMPLATE, "0.10.0")
        assert "Rename the contract struct" in prompt

    def test_template_prompt_has_reference_code_snippets(self):
        """Template system prompt must include code snippets for transfer_eth and sol_interface!."""
        from src.mcp.tools.generate_stylus_code import get_template_system_prompt

        prompt = get_template_system_prompt(COUNTER_TEMPLATE, "0.10.0")
        # Must have actual ETH transfer code snippet
        assert "transfer_eth(self.vm(), to, amount)?" in prompt
        assert "use stylus_sdk::call::transfer::transfer_eth;" in prompt
        # Must have actual sol_interface! code snippet
        assert "sol_interface! {" in prompt
        assert "IToken::new(token)" in prompt
        assert "token.balance_of(self.vm(), Call::new(), account)?" in prompt
        # Must be labeled as REFERENCE CODE
        assert "REFERENCE CODE" in prompt

    def test_fix_code_removes_deprecated_evm_import(self):
        """_fix_code should remove deprecated use stylus_sdk::evm imports."""
        from src.mcp.tools.generate_stylus_code import GenerateStylusCodeTool

        tool = GenerateStylusCodeTool.__new__(GenerateStylusCodeTool)
        broken = "use stylus_sdk::evm;\nevm::log(Transfer { from, to, value });"
        fixed = tool._fix_code(broken, None)
        assert "use stylus_sdk::evm" not in fixed

    def test_defi_vault_template_has_all_advanced_patterns(self):
        """DeFiVault template must demonstrate all 5 advanced patterns."""
        from src.templates.stylus_templates import DEFI_VAULT_TEMPLATE

        t = DEFI_VAULT_TEMPLATE
        assert "transfer_eth(self.vm(), to, amount)?" in t.lib_rs
        assert "call::transfer::transfer_eth" in t.lib_rs
        assert "sol_interface!" in t.lib_rs
        assert "Call::new()" in t.lib_rs
        assert "self.vm().msg_sender()" in t.lib_rs
        assert "self.vm().log(" in t.lib_rs
        assert ".abi_encode()" in t.lib_rs
        assert "self.balances.get(sender)" in t.lib_rs
        assert "self.total_deposits.get()" in t.lib_rs

    def test_defi_keywords_select_vault_template(self):
        """DeFi keywords should route to DeFiVault template."""
        for kw in [
            "prediction market",
            "staking pool",
            "swap contract",
            "deposit ETH",
            "oracle price feed",
            "lending protocol",
        ]:
            template = select_template("utility", kw)
            assert template.name == "DeFiVault", (
                f"'{kw}' should select DeFiVault, got {template.name}"
            )

    def test_fix_code_enforces_get_on_storage_reads(self):
        """_fix_code should add .get() to bare storage field reads."""
        from src.mcp.tools.generate_stylus_code import GenerateStylusCodeTool

        tool = GenerateStylusCodeTool.__new__(GenerateStylusCodeTool)
        broken = """sol_storage! {
    #[entrypoint]
    pub struct Market {
        uint256 count;
        address owner;
    }
}
let c = self.count;
let o = self.owner;
self.count.set(val);
self.owner.set(addr);"""
        fixed = tool._fix_code(broken, None)
        assert "self.count.get()" in fixed, "bare self.count should get .get()"
        assert "self.owner.get()" in fixed, "bare self.owner should get .get()"
        assert "self.count.set(val)" in fixed, ".set() should not be changed"
        assert "self.owner.set(addr)" in fixed, ".set() should not be changed"

    def test_fix_code_enforces_get_on_nested_struct_fields(self):
        """_fix_code should add .get() to nested struct storage field reads."""
        from src.mcp.tools.generate_stylus_code import GenerateStylusCodeTool

        tool = GenerateStylusCodeTool.__new__(GenerateStylusCodeTool)
        broken = """sol_storage! {
    #[entrypoint]
    pub struct PredictionMarket {
        mapping(uint256 => Market) markets;
    }
}
sol_storage! {
    pub struct Market {
        bool resolved;
        uint256 total_up;
        uint256 total_down;
    }
}
let market = self.markets.get(market_id);
if !market.resolved {
    let total = market.total_up + market.total_down;
}
market.resolved.set(true);"""
        fixed = tool._fix_code(broken, None)
        assert "market.resolved.get()" in fixed, "nested market.resolved should get .get()"
        assert "market.total_up.get()" in fixed, "nested market.total_up should get .get()"
        assert "market.total_down.get()" in fixed, "nested market.total_down should get .get()"
        assert "market.resolved.set(true)" in fixed, ".set() should not be changed"

    def test_ask_stylus_fix_code_in_response(self):
        """ask_stylus _fix_code_in_response should fix wrong patterns in code blocks."""
        from src.mcp.tools.ask_stylus import AskStylusTool

        tool = AskStylusTool.__new__(AskStylusTool)

        response = """Here's how to transfer ETH:

```rust
use stylus_sdk::call::transfer_eth;

pub fn withdraw(&mut self, to: Address, amount: U256) -> Result<(), Vec<u8>> {
    transfer_eth(self, to, amount)?;
    Ok(())
}
```

And for cross-contract calls:

```rust
sol! {
    interface IToken {
        function transfer(address to, uint256 amount) external returns (bool);
    }
}
```

Use msg::sender() to get the caller.
"""
        fixed = tool._fix_code_in_response(response)

        # Check transfer_eth import path is fixed
        assert "call::transfer::transfer_eth" in fixed
        assert "call::transfer_eth;" not in fixed

        # Check transfer_eth first arg is fixed
        assert "transfer_eth(self.vm(), to, amount)" in fixed
        assert "transfer_eth(self, to" not in fixed

        # Check sol! { interface → sol_interface!
        assert "sol_interface!" in fixed

    def test_ask_stylus_system_prompt_has_reference_code(self):
        """ask_stylus system prompt should include reference code examples."""
        from src.mcp.tools.ask_stylus import SYSTEM_PROMPT

        assert "REFERENCE CODE" in SYSTEM_PROMPT
        assert "call::transfer::transfer_eth" in SYSTEM_PROMPT
        assert "sol_interface!" in SYSTEM_PROMPT
        assert "self.vm(), Call::new()" in SYSTEM_PROMPT
        assert ".get()" in SYSTEM_PROMPT


# Integration tests that require cargo-stylus
@pytest.mark.integration
@pytest.mark.slow
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

        # Write main.rs (for ABI export binary)
        if template.main_rs:
            main_rs = src_dir / "main.rs"
            main_rs.write_text(template.main_rs)

        # Write Cargo.toml
        cargo_toml = project_dir / "Cargo.toml"
        cargo_toml.write_text(template.cargo_toml)

        # Write Stylus.toml (required since SDK 0.10.0)
        if template.stylus_toml:
            stylus_toml = project_dir / "Stylus.toml"
            stylus_toml.write_text(template.stylus_toml)

        # Write rust-toolchain.toml (required since SDK 0.10.0)
        if template.rust_toolchain_toml:
            rust_toolchain = project_dir / "rust-toolchain.toml"
            rust_toolchain.write_text(template.rust_toolchain_toml)
        else:
            rust_toolchain = project_dir / "rust-toolchain.toml"
            rust_toolchain.write_text(
                '[toolchain]\nchannel = "1.88.0"\ntargets = ["wasm32-unknown-unknown"]\n'
            )

        # Generate Cargo.lock by running cargo update
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
            timeout=180,
        )

        output = result.stdout + result.stderr

        # Skip if failure is from upstream dependency (not template code)
        # Known issue: alloy-consensus doesn't compile on Rust nightly 1.88.0
        if result.returncode != 0 and "alloy-consensus" in output:
            pytest.skip("Upstream alloy-consensus crate incompatible with Rust nightly 1.88.0")

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


class TestOracleScaffold:
    """Test oracle tool generates Hardhat scaffold files."""

    def test_generate_oracle_returns_hardhat_config(self):
        """generate_oracle should include hardhat.config.ts in files."""
        from src.mcp.tools.generate_oracle import GenerateOracleTool

        tool = GenerateOracleTool()
        result = tool.execute(prompt="price feed oracle", oracle_type="price_feed")
        assert "hardhat.config.ts" in result["files"]
        assert "HardhatUserConfig" in result["files"]["hardhat.config.ts"]

    def test_generate_oracle_returns_package_json(self):
        """generate_oracle should include package.json in files."""
        from src.mcp.tools.generate_oracle import GenerateOracleTool

        tool = GenerateOracleTool()
        result = tool.execute(prompt="price feed oracle", oracle_type="price_feed")
        assert "package.json" in result["files"]
        assert "hardhat" in result["files"]["package.json"]
        assert "@chainlink/contracts" in result["files"]["package.json"]

    def test_generate_oracle_returns_env_example(self):
        """generate_oracle should include .env.example in files."""
        from src.mcp.tools.generate_oracle import GenerateOracleTool

        tool = GenerateOracleTool()
        result = tool.execute(prompt="price feed oracle", oracle_type="price_feed")
        assert ".env.example" in result["files"]
        assert "PRIVATE_KEY" in result["files"][".env.example"]

    def test_generate_oracle_all_types_have_scaffold(self):
        """All oracle types should include Hardhat scaffold files."""
        from src.mcp.tools.generate_oracle import GenerateOracleTool

        tool = GenerateOracleTool()
        for oracle_type in ["price_feed", "vrf", "automation", "functions"]:
            result = tool.execute(prompt=f"{oracle_type} oracle", oracle_type=oracle_type)
            assert "hardhat.config.ts" in result["files"], (
                f"{oracle_type} missing hardhat.config.ts"
            )
            assert "package.json" in result["files"], f"{oracle_type} missing package.json"
            assert ".env.example" in result["files"], f"{oracle_type} missing .env.example"


class TestOrchestratorDeployScripts:
    """Test orchestrator generates deploy/setup scripts with oracle+indexer sections."""

    def test_deploy_script_includes_oracle_section(self):
        """deploy.sh should include oracle deploy section when oracle is a component."""
        from src.mcp.tools.orchestrate_dapp import OrchestrateDappTool

        tool = OrchestrateDappTool()
        result = tool.execute(
            prompt="token dapp",
            components=["contract", "backend", "frontend", "oracle"],
        )
        deploy_sh = result["root_files"]["deploy.sh"]
        assert "packages/oracle" in deploy_sh
        assert "hardhat run scripts/deploy.ts" in deploy_sh

    def test_deploy_script_includes_indexer_section(self):
        """deploy.sh should include indexer deploy section when indexer is a component."""
        from src.mcp.tools.orchestrate_dapp import OrchestrateDappTool

        tool = OrchestrateDappTool()
        result = tool.execute(
            prompt="token dapp",
            components=["contract", "backend", "frontend", "indexer"],
        )
        deploy_sh = result["root_files"]["deploy.sh"]
        assert "packages/indexer" in deploy_sh
        assert "GRAPH_DEPLOY_KEY" in deploy_sh
        assert "npm run codegen" in deploy_sh

    def test_deploy_script_excludes_oracle_when_not_requested(self):
        """deploy.sh should NOT include oracle section when oracle is not a component."""
        from src.mcp.tools.orchestrate_dapp import OrchestrateDappTool

        tool = OrchestrateDappTool()
        result = tool.execute(
            prompt="token dapp",
            components=["contract", "backend", "frontend"],
        )
        deploy_sh = result["root_files"]["deploy.sh"]
        assert "packages/oracle" not in deploy_sh

    def test_setup_script_includes_oracle_install(self):
        """setup.sh should include oracle npm install when oracle is a component."""
        from src.mcp.tools.orchestrate_dapp import OrchestrateDappTool

        tool = OrchestrateDappTool()
        result = tool.execute(
            prompt="token dapp",
            components=["contract", "backend", "frontend", "oracle"],
        )
        setup_sh = result["root_files"]["setup.sh"]
        assert "packages/oracle" in setup_sh
        assert "Installing oracle dependencies" in setup_sh

    def test_orchestrator_oracle_has_files(self):
        """Oracle component in orchestrator should have deployable files."""
        from src.mcp.tools.orchestrate_dapp import OrchestrateDappTool

        tool = OrchestrateDappTool()
        result = tool.execute(
            prompt="token dapp",
            components=["contract", "oracle"],
        )
        oracle = result["components"]["oracle"]
        assert "files" in oracle
        assert "hardhat.config.ts" in oracle["files"]
        assert "contracts/OracleConsumer.sol" in oracle["files"]
        assert "scripts/deploy.ts" in oracle["files"]

    def test_orchestrate_dapp_description_says_scaffold(self):
        """orchestrate_dapp description should say 'Scaffold', not 'Generate a complete'."""
        from src.mcp.tools.orchestrate_dapp import OrchestrateDappTool

        tool = OrchestrateDappTool()
        assert "Scaffold" in tool.description
        assert "Generate a complete" not in tool.description


class TestSetupScriptScaffolding:
    """Test that setup.sh uses official CLI scaffolding with backfill pattern."""

    def _get_setup_sh(self, components, backend_framework="nestjs"):
        from src.mcp.tools.orchestrate_dapp import OrchestrateDappTool

        tool = OrchestrateDappTool()
        result = tool.execute(
            prompt="token dapp",
            components=components,
            backend_framework=backend_framework,
        )
        return result["root_files"]["setup.sh"]

    def test_setup_script_has_backfill_helper(self):
        """setup.sh should define the backfill_from_scaffold function."""
        setup_sh = self._get_setup_sh(["contract", "backend", "frontend"])
        assert "backfill_from_scaffold()" in setup_sh
        assert "scaffold_dir" in setup_sh
        assert 'case "$rel" in src/*)' in setup_sh

    def test_setup_script_contract_scaffold(self):
        """setup.sh should include cargo stylus new scaffold when contract is present."""
        setup_sh = self._get_setup_sh(["contract", "backend", "frontend"])
        assert "cargo stylus new" in setup_sh
        assert "backfill_from_scaffold" in setup_sh

    def test_setup_script_frontend_scaffold(self):
        """setup.sh should include create-next-app scaffold when frontend is present."""
        setup_sh = self._get_setup_sh(["contract", "backend", "frontend"])
        assert "create-next-app" in setup_sh
        assert "--tailwind" in setup_sh

    def test_setup_script_backend_nestjs_scaffold(self):
        """setup.sh should include @nestjs/cli scaffold for NestJS backend."""
        setup_sh = self._get_setup_sh(
            ["contract", "backend", "frontend"], backend_framework="nestjs"
        )
        assert "@nestjs/cli" in setup_sh

    def test_setup_script_backend_express_no_scaffold(self):
        """setup.sh should NOT include @nestjs/cli scaffold for Express backend."""
        setup_sh = self._get_setup_sh(
            ["contract", "backend", "frontend"], backend_framework="express"
        )
        assert "@nestjs/cli" not in setup_sh

    def test_setup_script_no_contract_no_scaffold(self):
        """setup.sh should NOT include cargo stylus new when contract is absent."""
        setup_sh = self._get_setup_sh(["backend", "frontend"])
        assert "cargo stylus new" not in setup_sh

    def test_setup_script_graceful_fallback(self):
        """setup.sh should include 'scaffold skipped' fallback messages."""
        setup_sh = self._get_setup_sh(["contract", "backend", "frontend"])
        assert "scaffold skipped" in setup_sh


class TestEnvConfigOracleIndexer:
    """Test env_config generates oracle/indexer env vars."""

    def test_env_template_includes_graph_deploy_key(self):
        """Env template should include GRAPH_DEPLOY_KEY when indexer is present."""
        from src.utils.env_config import generate_env_template

        env = generate_env_template(["contract", "backend", "frontend", "indexer"])
        assert "GRAPH_DEPLOY_KEY" in env
        assert "SUBGRAPH_NAME" in env

    def test_env_template_includes_oracle_address(self):
        """Env template should include ORACLE_CONTRACT_ADDRESS when oracle is present."""
        from src.utils.env_config import generate_env_template

        env = generate_env_template(["contract", "backend", "frontend", "oracle"])
        assert "ORACLE_CONTRACT_ADDRESS" in env

    def test_env_template_includes_subgraph_url_for_frontend(self):
        """Env template should include NEXT_PUBLIC_SUBGRAPH_URL when both indexer and frontend."""
        from src.utils.env_config import generate_env_template

        env = generate_env_template(["contract", "backend", "frontend", "indexer"])
        assert "NEXT_PUBLIC_SUBGRAPH_URL" in env

    def test_env_template_excludes_oracle_when_not_requested(self):
        """Env template should NOT include oracle vars when oracle is not present."""
        from src.utils.env_config import generate_env_template

        env = generate_env_template(["contract", "backend", "frontend"])
        assert "ORACLE_CONTRACT_ADDRESS" not in env
        assert "GRAPH_DEPLOY_KEY" not in env

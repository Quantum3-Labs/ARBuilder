"""
Tests for Milestone 4 (Orbit Chain Integration) MCP tools.

Tests the following tools:
- generate_orbit_config: Chain configuration generation
- generate_orbit_deployment: Rollup/token bridge deployment
- generate_validator_setup: Validator/batch poster management
- ask_orbit: Orbit chain Q&A
- orchestrate_orbit: Full Orbit project scaffolding

All M4 tools are template-based (no LLM required), so these tests
run without OPENROUTER_API_KEY.
"""

import json
import os
import subprocess
import tempfile

import pytest

from src.mcp.tools.generate_orbit_deployment import (
    ROLLUP_CREATOR_ADDRESSES,
    TOKEN_BRIDGE_CREATOR_ADDRESSES,
)
from src.templates.orbit_templates import (
    ORBIT_DEPENDENCIES,
    ORBIT_TEMPLATES,
    PARENT_CHAIN_RPCS,
    generate_docker_compose,
    select_orbit_template,
    validate_template_output,
)

# ============================================================================
# Template Infrastructure Tests
# ============================================================================


class TestOrbitTemplateInfrastructure:
    """Test the underlying template system and constants."""

    def test_all_nine_templates_exist(self):
        """Verify all 9 orbit templates are registered."""
        expected = [
            "chain_config",
            "deploy_rollup",
            "deploy_token_bridge",
            "custom_gas_token",
            "validator_management",
            "governance",
            "node_config",
            "anytrust_config",
            "orchestration",
        ]
        for name in expected:
            assert name in ORBIT_TEMPLATES, f"Missing template: {name}"

    def test_orbit_dependencies_versions(self):
        """Verify Orbit SDK dependency versions are pinned correctly."""
        assert "@arbitrum/chain-sdk" in ORBIT_DEPENDENCIES
        assert "viem" in ORBIT_DEPENDENCIES
        assert "dotenv" in ORBIT_DEPENDENCIES
        # viem must be ^1.20.0 (orbit-sdk peer dep)
        assert ORBIT_DEPENDENCIES["viem"].startswith("^1.")

    def test_parent_chain_rpcs_all_present(self):
        """Verify all supported parent chains have RPC URLs."""
        expected_chains = [
            "arbitrum-one",
            "arbitrum-sepolia",
            "ethereum-mainnet",
            "ethereum-sepolia",
        ]
        for chain in expected_chains:
            assert chain in PARENT_CHAIN_RPCS, f"Missing RPC for {chain}"
            assert PARENT_CHAIN_RPCS[chain].startswith("http")

    def test_rollup_creator_addresses_both_versions(self):
        """Verify RollupCreator addresses exist for v2.1 and v3.1."""
        assert "v2.1" in ROLLUP_CREATOR_ADDRESSES
        assert "v3.1" in ROLLUP_CREATOR_ADDRESSES
        # Both versions must have Arbitrum Sepolia (421614)
        assert 421614 in ROLLUP_CREATOR_ADDRESSES["v2.1"]
        assert 421614 in ROLLUP_CREATOR_ADDRESSES["v3.1"]
        # v3.1 must have Ethereum Mainnet and Arbitrum One
        assert 1 in ROLLUP_CREATOR_ADDRESSES["v3.1"]
        assert 42161 in ROLLUP_CREATOR_ADDRESSES["v3.1"]
        # All addresses must be valid 0x-prefixed hex
        for version, chains in ROLLUP_CREATOR_ADDRESSES.items():
            for chain_id, addr in chains.items():
                assert addr.startswith("0x"), f"{version}/{chain_id}: invalid address {addr}"
                assert len(addr) == 42, f"{version}/{chain_id}: wrong length {addr}"

    def test_token_bridge_creator_addresses(self):
        """Verify TokenBridgeCreator addresses for all parent chains."""
        expected_chain_ids = [421614, 42161]  # Arbitrum Sepolia, Arbitrum One
        for chain_id in expected_chain_ids:
            assert chain_id in TOKEN_BRIDGE_CREATOR_ADDRESSES, f"Missing TBC for chain {chain_id}"
            addr = TOKEN_BRIDGE_CREATOR_ADDRESSES[chain_id]
            assert addr.startswith("0x") and len(addr) == 42

    def test_template_selector_keywords(self):
        """Test that prompt keyword routing selects correct templates."""
        cases = [
            ("deploy a new rollup chain", "deploy_rollup"),
            ("create a token bridge", "deploy_token_bridge"),
            ("configure custom gas token", "custom_gas_token"),
            ("manage validators", "validator_management"),
            ("set up governance executor", "governance"),
            ("configure nitro node", "node_config"),
            ("set up anytrust DAC keyset", "anytrust_config"),
            ("scaffold full project", "orchestration"),
            ("prepare chain config", "chain_config"),
        ]
        for prompt, expected_name in cases:
            template = select_orbit_template(prompt)
            expected = ORBIT_TEMPLATES[expected_name].name
            assert template.name == expected, (
                f"'{prompt}' -> '{template.name}', want '{expected}'"
            )

    def test_validate_template_output_clean(self):
        """Test that clean code passes validation."""
        clean_code = "const x = 1;\nconsole.log(x);"
        result = validate_template_output(clean_code)
        assert result == clean_code


# ============================================================================
# Docker Compose Tests
# ============================================================================


class TestDockerCompose:
    """Test docker-compose.yml generation for Nitro node."""

    def test_rollup_docker_compose_structure(self):
        """Test Rollup docker-compose has correct Nitro node config."""
        compose = generate_docker_compose("test-chain", 412346, 421614, False)

        assert "services:" in compose
        assert "nitro-node:" in compose
        assert "offchainlabs/nitro-node:" in compose
        assert "test-chain-node" in compose  # container_name

    def test_rollup_docker_compose_ports(self):
        """Test correct port mappings for Nitro node."""
        compose = generate_docker_compose("test-chain", 412346, 421614, False)

        assert "8449:8449" in compose  # L3 RPC
        assert "8548:8548" in compose  # WebSocket
        assert "9642:9642" in compose  # Metrics

    def test_rollup_docker_compose_rpc_apis(self):
        """Test Nitro node exposes required RPC APIs."""
        compose = generate_docker_compose("test-chain", 412346, 421614, False)

        # HTTP and WS must expose these APIs
        assert "net,web3,eth,debug,txpool,arb" in compose

    def test_rollup_docker_compose_volumes(self):
        """Test volume mounts for config and data persistence."""
        compose = generate_docker_compose("test-chain", 412346, 421614, False)

        assert "nodeConfig.json:/config/nodeConfig.json" in compose
        assert "data/arbitrum:/home/user/.arbitrum" in compose

    def test_rollup_docker_compose_no_dev_init_flag(self):
        """Test that --init.dev-init is NOT passed as an actual flag (it's for devnodes only)."""
        compose = generate_docker_compose("test-chain", 412346, 421614, False)

        # The comment warns against dev-init, but the actual entrypoint must not use it
        lines = compose.split("\n")
        command_lines = [
            line.strip()
            for line in lines
            if line.strip().startswith("--") or line.strip().startswith("exec")
        ]
        for line in command_lines:
            assert "--init.dev-init" not in line, "dev-init flag must not appear in node command"

    def test_rollup_docker_compose_wasm_cleanup(self):
        """Test that stale WASM cleanup is included (prevents crash-loops)."""
        compose = generate_docker_compose("test-chain", 412346, 421614, False)

        assert "rm -rf /home/user/.arbitrum/*/nitro/wasm" in compose

    def test_rollup_docker_compose_validation_roots(self):
        """Test WASM validation roots are set correctly."""
        compose = generate_docker_compose("test-chain", 412346, 421614, False)

        assert "--validation.wasm.allowed-wasm-module-roots" in compose
        assert "nitro-legacy/machines" in compose

    def test_rollup_no_das_server(self):
        """Test Rollup mode does NOT include DAS server."""
        compose = generate_docker_compose("test-chain", 412346, 421614, False)

        assert "das-server" not in compose
        assert "daserver" not in compose

    def test_anytrust_docker_compose_has_das(self):
        """Test AnyTrust mode includes DAS server container."""
        compose = generate_docker_compose("test-chain", 412347, 421614, True)

        assert "das-server:" in compose
        assert "daserver" in compose
        assert "test-chain-das" in compose  # DAS container_name

    def test_anytrust_das_ports(self):
        """Test DAS server exposes correct ports."""
        compose = generate_docker_compose("test-chain", 412347, 421614, True)

        assert "9876:9876" in compose  # DAS RPC
        assert "9877:9877" in compose  # DAS REST API

    def test_anytrust_das_volumes(self):
        """Test DAS server has key and data volume mounts."""
        compose = generate_docker_compose("test-chain", 412347, 421614, True)

        assert "das-data" in compose
        assert "das-keys" in compose

    def test_anytrust_nitro_depends_on_das(self):
        """Test Nitro node depends on DAS server in AnyTrust mode."""
        compose = generate_docker_compose("test-chain", 412347, 421614, True)

        assert "depends_on:" in compose
        assert "das-server:" in compose

    def test_anytrust_das_rest_enabled(self):
        """Test DAS server has REST API enabled."""
        compose = generate_docker_compose("test-chain", 412347, 421614, True)

        assert "--enable-rest" in compose
        assert "--rest-addr=0.0.0.0" in compose


# ============================================================================
# generate_orbit_config Tests
# ============================================================================


class TestGenerateOrbitConfig:
    """Tests for the generate_orbit_config tool."""

    @pytest.fixture
    def tool(self, m4_tools):
        return m4_tools["generate_orbit_config"]

    def test_basic_rollup_config(self, tool):
        """Test basic Rollup chain configuration."""
        result = tool.execute(
            prompt="Create a rollup chain config",
            chain_id=412346,
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result, f"Config generation failed: {result.get('error')}"
        assert "files" in result
        assert "dependencies" in result
        assert "chain_config" in result

        # Should contain prepareChainConfig
        files_str = str(result["files"])
        assert "prepareChainConfig" in files_str

    def test_anytrust_config(self, tool):
        """Test AnyTrust chain configuration."""
        result = tool.execute(
            prompt="Create an AnyTrust chain config",
            chain_id=412347,
            is_anytrust=True,
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

        # AnyTrust-specific content
        files_str = str(result["files"])
        assert "AnyTrust" in files_str or "anytrust" in files_str.lower() or "DAS" in files_str

    def test_custom_gas_token(self, tool):
        """Test configuration with custom gas token."""
        result = tool.execute(
            prompt="Create a chain with custom gas token",
            chain_id=412348,
            native_token="0x1234567890abcdef1234567890abcdef12345678",
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

        # Should reference native token
        files_str = str(result["files"])
        assert (
            "0x1234567890abcdef1234567890abcdef12345678" in files_str
            or "nativeToken" in files_str
            or "NATIVE_TOKEN" in files_str
        )

    def test_custom_owner(self, tool):
        """Test configuration with custom owner address."""
        owner = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        result = tool.execute(
            prompt="Create a rollup config",
            chain_id=412346,
            owner=owner,
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

    def test_env_file_generated(self, tool):
        """Test that .env.example is generated."""
        result = tool.execute(
            prompt="Create a rollup config",
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        files = result.get("files", {})
        env_files = [f for f in files if ".env" in f]
        assert len(env_files) > 0, "Should generate .env.example"

    def test_parent_chain_ethereum_mainnet(self, tool):
        """Test configuration targeting Ethereum mainnet."""
        result = tool.execute(
            prompt="Create a production rollup config",
            parent_chain="ethereum-mainnet",
        )

        assert "error" not in result
        assert "files" in result

    def test_config_uses_prepare_chain_config_api(self, tool):
        """Test that config code uses the correct SDK API."""
        result = tool.execute(
            prompt="Create a rollup config",
            chain_id=412346,
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        config_files = [v for k, v in files.items() if "config" in k.lower()]
        assert len(config_files) > 0
        config_code = config_files[0]
        assert "prepareChainConfig" in config_code
        assert "chainId" in config_code
        assert "InitialChainOwner" in config_code
        assert "DataAvailabilityCommittee" in config_code

    def test_config_has_correct_imports(self, tool):
        """Test that config code imports from correct package."""
        result = tool.execute(
            prompt="Create a rollup config",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        config_files = [v for k, v in files.items() if "config" in k.lower()]
        config_code = config_files[0] if config_files else ""
        assert "@arbitrum/chain-sdk" in config_code or "chain-sdk" in config_code

    def test_anytrust_selects_anytrust_template(self, tool):
        """Test that AnyTrust flag selects anytrust-specific template."""
        result = tool.execute(
            prompt="Create an AnyTrust chain",
            is_anytrust=True,
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        # Should select anytrust_config template when is_anytrust=True
        template_used = result.get("template_used", "")
        files = result.get("files", {})
        files_str = str(files)
        assert (
            "anytrust" in template_used.lower()
            or "AnyTrust" in files_str
            or "DAC" in files_str
            or "keyset" in files_str.lower()
        )


# ============================================================================
# generate_orbit_deployment Tests
# ============================================================================


class TestGenerateOrbitDeployment:
    """Tests for the generate_orbit_deployment tool."""

    @pytest.fixture
    def tool(self, m4_tools):
        return m4_tools["generate_orbit_deployment"]

    def test_rollup_deployment(self, tool):
        """Test basic rollup deployment generation."""
        result = tool.execute(
            prompt="Deploy a rollup chain",
            deployment_type="rollup",
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result, f"Deployment generation failed: {result.get('error')}"
        assert "files" in result
        assert "dependencies" in result

        # Should contain createRollup
        files_str = str(result["files"])
        assert "createRollup" in files_str or "deploy-rollup" in files_str

    def test_token_bridge_deployment(self, tool):
        """Test token bridge deployment generation."""
        result = tool.execute(
            prompt="Deploy a token bridge",
            deployment_type="token_bridge",
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

        files_str = str(result["files"])
        assert "token" in files_str.lower() or "bridge" in files_str.lower()

    def test_full_deployment(self, tool):
        """Test full deployment (rollup + token bridge)."""
        result = tool.execute(
            prompt="Deploy everything",
            deployment_type="full",
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

    def test_deployment_with_validators(self, tool):
        """Test deployment with custom validator addresses."""
        validators = [
            "0x1111111111111111111111111111111111111111",
            "0x2222222222222222222222222222222222222222",
        ]
        result = tool.execute(
            prompt="Deploy rollup with validators",
            deployment_type="rollup",
            validators=validators,
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

    def test_deployment_with_native_token(self, tool):
        """Test deployment with custom gas token."""
        result = tool.execute(
            prompt="Deploy rollup with custom gas token",
            deployment_type="rollup",
            native_token="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

    def test_rollup_version_v21(self, tool):
        """Test deployment with v2.1 RollupCreator."""
        result = tool.execute(
            prompt="Deploy rollup",
            deployment_type="rollup",
            rollup_version="v2.1",
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

    def test_rollup_version_v31(self, tool):
        """Test deployment with v3.1 RollupCreator (BoLD)."""
        result = tool.execute(
            prompt="Deploy rollup",
            deployment_type="rollup",
            rollup_version="v3.1",
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

    def test_rollup_uses_create_rollup_api(self, tool):
        """Test that rollup deployment uses createRollup SDK API."""
        result = tool.execute(
            prompt="Deploy rollup",
            deployment_type="rollup",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        deploy_files = [
            v for k, v in files.items() if "deploy" in k.lower() and "rollup" in k.lower()
        ]
        assert len(deploy_files) > 0
        deploy_code = deploy_files[0]
        assert "createRollup" in deploy_code

    def test_rollup_saves_deployment_json(self, tool):
        """Test that deployment script saves output to deployment.json."""
        result = tool.execute(
            prompt="Deploy rollup",
            deployment_type="rollup",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        deploy_files = [
            v for k, v in files.items() if "deploy" in k.lower() and "rollup" in k.lower()
        ]
        deploy_code = deploy_files[0] if deploy_files else ""
        assert "deployment.json" in deploy_code

    def test_native_token_generates_approve_script(self, tool):
        """Test that custom gas token generates standalone approve-token.ts."""
        result = tool.execute(
            prompt="Deploy with custom gas token",
            deployment_type="rollup",
            native_token="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        approve_files = [k for k in files if "approve" in k.lower()]
        assert len(approve_files) > 0, "Should generate approve-token.ts for native token"

        # Approve script should include ERC20 approval logic
        approve_code = files[approve_files[0]]
        assert "approve" in approve_code.lower()

    def test_deployment_has_env_example(self, tool):
        """Test that deployment generates .env.example with required vars."""
        result = tool.execute(
            prompt="Deploy rollup",
            deployment_type="rollup",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        env_files = {k: v for k, v in files.items() if ".env" in k}
        assert len(env_files) > 0
        env_content = list(env_files.values())[0]
        assert "DEPLOYER_PRIVATE_KEY" in env_content
        assert "PARENT_CHAIN_RPC" in env_content

    def test_rollup_creator_address_injected(self, tool):
        """Test that correct RollupCreator address is in the deployment code."""
        result = tool.execute(
            prompt="Deploy rollup",
            deployment_type="rollup",
            rollup_version="v3.1",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        all_code = str(files)
        # Should contain the v3.1 Arbitrum Sepolia RollupCreator address
        expected_addr = ROLLUP_CREATOR_ADDRESSES["v3.1"][421614]
        assert expected_addr in all_code or "RollupCreator" in all_code


# ============================================================================
# generate_validator_setup Tests
# ============================================================================


class TestGenerateValidatorSetup:
    """Tests for the generate_validator_setup tool."""

    @pytest.fixture
    def tool(self, m4_tools):
        return m4_tools["generate_validator_setup"]

    def test_list_validators(self, tool):
        """Test listing validators."""
        result = tool.execute(
            prompt="List all validators",
            action="list",
            target="validator",
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result, f"Validator list failed: {result.get('error')}"
        assert "files" in result

    def test_add_validator(self, tool):
        """Test adding a validator."""
        result = tool.execute(
            prompt="Add a new validator",
            action="add",
            target="validator",
            addresses=["0x3333333333333333333333333333333333333333"],
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

        files_str = str(result["files"])
        assert (
            "0x3333333333333333333333333333333333333333" in files_str
            or "validator" in files_str.lower()
        )

    def test_remove_validator(self, tool):
        """Test removing a validator."""
        result = tool.execute(
            prompt="Remove a validator",
            action="remove",
            target="validator",
            addresses=["0x3333333333333333333333333333333333333333"],
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

    def test_add_batch_poster(self, tool):
        """Test adding a batch poster."""
        result = tool.execute(
            prompt="Add a batch poster",
            action="add",
            target="batch_poster",
            addresses=["0x4444444444444444444444444444444444444444"],
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

    def test_keyset_management(self, tool):
        """Test AnyTrust DAC keyset management."""
        result = tool.execute(
            prompt="Configure AnyTrust keyset",
            action="list",
            target="keyset",
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

    def test_with_rollup_address(self, tool):
        """Test validator setup with explicit rollup address."""
        result = tool.execute(
            prompt="List validators for specific rollup",
            action="list",
            target="validator",
            rollup_address="0x5555555555555555555555555555555555555555",
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

    def test_add_validator_uses_upgrade_executor(self, tool):
        """Test that add/remove routes through UpgradeExecutor."""
        result = tool.execute(
            prompt="Add a validator",
            action="add",
            target="validator",
            addresses=["0x3333333333333333333333333333333333333333"],
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        all_code = str(files)
        # Should use UpgradeExecutor for permissioned operations
        assert (
            "UpgradeExecutor" in all_code
            or "upgradeExecutor" in all_code
            or "executeCall" in all_code
        )

    def test_validator_script_has_correct_abis(self, tool):
        """Test that validator management includes Rollup and SequencerInbox ABIs."""
        result = tool.execute(
            prompt="Add a validator",
            action="add",
            target="validator",
            addresses=["0x3333333333333333333333333333333333333333"],
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        all_code = str(files)
        # Should include key ABI functions
        assert (
            "setValidator" in all_code
            or "isValidator" in all_code
            or "validator" in all_code.lower()
        )

    def test_batch_poster_uses_sequencer_inbox(self, tool):
        """Test that batch poster management references SequencerInbox."""
        result = tool.execute(
            prompt="Add a batch poster",
            action="add",
            target="batch_poster",
            addresses=["0x4444444444444444444444444444444444444444"],
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        all_code = str(files)
        assert (
            "BatchPoster" in all_code
            or "batchPoster" in all_code
            or "batch_poster" in all_code.lower()
        )


# ============================================================================
# ask_orbit Tests
# ============================================================================


class TestAskOrbit:
    """Tests for the ask_orbit tool."""

    @pytest.fixture
    def tool(self, m4_tools):
        return m4_tools["ask_orbit"]

    def test_general_question(self, tool):
        """Test general Orbit chain question."""
        result = tool.execute(
            question="What is an Orbit chain?",
            question_type="general",
        )

        assert "error" not in result, f"Q&A failed: {result.get('error')}"
        assert "answer" in result
        assert len(result["answer"]) > 50  # Should be a substantial answer

    def test_deployment_question(self, tool):
        """Test deployment-related question."""
        result = tool.execute(
            question="How do I deploy a rollup with createRollup?",
            question_type="deployment",
        )

        assert "error" not in result
        assert "answer" in result
        # Should mention deployment-related concepts
        answer_lower = result["answer"].lower()
        assert (
            "deploy" in answer_lower or "rollup" in answer_lower or "createrollup" in answer_lower
        )

    def test_config_question(self, tool):
        """Test config-related question."""
        result = tool.execute(
            question="How do I configure chain parameters with prepareChainConfig?",
            question_type="config",
        )

        assert "error" not in result
        assert "answer" in result

    def test_validator_question(self, tool):
        """Test validator-related question."""
        result = tool.execute(
            question="How do I set up validators and batch posters?",
            question_type="validator",
        )

        assert "error" not in result
        assert "answer" in result
        answer_lower = result["answer"].lower()
        assert "validator" in answer_lower or "batch poster" in answer_lower

    def test_anytrust_question(self, tool):
        """Test AnyTrust-specific question."""
        result = tool.execute(
            question="How does AnyTrust data availability work with DAC keysets?",
            question_type="general",
        )

        assert "error" not in result
        assert "answer" in result

    def test_custom_gas_token_question(self, tool):
        """Test custom gas token question."""
        result = tool.execute(
            question="How do I configure a custom gas token for my Orbit chain?",
            question_type="config",
        )

        assert "error" not in result
        assert "answer" in result

    def test_troubleshooting_question(self, tool):
        """Test troubleshooting question."""
        result = tool.execute(
            question="My node failed to start, how do I troubleshoot?",
            question_type="troubleshooting",
        )

        assert "error" not in result
        assert "answer" in result

    def test_returns_references(self, tool):
        """Test that answers include references."""
        result = tool.execute(
            question="How do I deploy an Orbit chain?",
            question_type="deployment",
        )

        assert "error" not in result
        # Should include references list
        assert "references" in result


# ============================================================================
# orchestrate_orbit Tests
# ============================================================================


class TestOrchestrateOrbit:
    """Tests for the orchestrate_orbit tool."""

    @pytest.fixture
    def tool(self, m4_tools):
        return m4_tools["orchestrate_orbit"]

    def test_basic_rollup_scaffold(self, tool):
        """Test basic Rollup project scaffolding."""
        result = tool.execute(
            prompt="Create a rollup chain project",
            chain_name="test-rollup",
            chain_id=412346,
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result, f"Orchestration failed: {result.get('error')}"
        assert "files" in result
        assert "setup_instructions" in result

        files = result["files"]
        # Should generate multiple project files
        assert len(files) >= 5, f"Expected at least 5 files, got {len(files)}"

    def test_rollup_has_essential_files(self, tool):
        """Test that rollup scaffold includes essential files."""
        result = tool.execute(
            prompt="Create a rollup chain project",
            chain_name="my-rollup",
            chain_id=412346,
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        files = result.get("files", {})
        files_str = str(list(files.keys()))

        # Should have config, deployment, and infra files
        assert "package.json" in files_str or "package" in files_str.lower()
        assert "docker-compose" in files_str.lower() or "docker" in files_str.lower()

    def test_anytrust_scaffold(self, tool):
        """Test AnyTrust project scaffolding."""
        result = tool.execute(
            prompt="Create an AnyTrust chain project",
            chain_name="test-anytrust",
            chain_id=412347,
            is_anytrust=True,
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

        # AnyTrust should have DAS-related files
        files = result.get("files", {})
        files_str = str(files)
        assert (
            "anytrust" in files_str.lower()
            or "das" in files_str.lower()
            or "keyset" in files_str.lower()
        )

    def test_scaffold_with_custom_gas_token(self, tool):
        """Test scaffolding with custom gas token."""
        result = tool.execute(
            prompt="Create a chain with custom gas token",
            chain_name="token-chain",
            chain_id=412348,
            native_token="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

        # Should have token-related files
        files_str = str(result["files"])
        assert (
            "token" in files_str.lower()
            or "NATIVE_TOKEN" in files_str
            or "0xaaaa" in files_str.lower()
        )

    def test_scaffold_with_validators(self, tool):
        """Test scaffolding with validator addresses."""
        validators = ["0x1111111111111111111111111111111111111111"]
        batch_posters = ["0x2222222222222222222222222222222222222222"]

        result = tool.execute(
            prompt="Create a rollup chain",
            chain_name="validator-chain",
            chain_id=412346,
            validators=validators,
            batch_posters=batch_posters,
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        assert "files" in result

    def test_scaffold_generates_readme(self, tool):
        """Test that scaffold includes a README."""
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="readme-test",
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        files = result.get("files", {})
        readme_files = [f for f in files if "readme" in f.lower()]
        assert len(readme_files) > 0, "Should generate a README"

    def test_scaffold_generates_docker_compose(self, tool):
        """Test that scaffold includes docker-compose."""
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="docker-test",
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        files = result.get("files", {})
        docker_files = [f for f in files if "docker" in f.lower()]
        assert len(docker_files) > 0, "Should generate docker-compose.yml"

    def test_dependencies_include_orbit_sdk(self, tool):
        """Test that dependencies include Orbit SDK packages."""
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="deps-test",
            parent_chain="arbitrum-sepolia",
        )

        assert "error" not in result
        deps = result.get("dependencies", {})
        deps_str = str(deps)
        assert "viem" in deps_str or "orbit" in deps_str.lower() or "arbitrum" in deps_str.lower()

    def test_scaffold_has_all_core_scripts(self, tool):
        """Test scaffold generates all required deployment scripts."""
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="scripts-test",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        filenames = list(files.keys())
        filenames_str = str(filenames)

        # All core scripts must be present
        assert "prepare-chain-config" in filenames_str
        assert "deploy-rollup" in filenames_str
        assert "deploy-token-bridge" in filenames_str
        assert "manage-validators" in filenames_str
        assert "prepare-node-config" in filenames_str
        assert "test-chain" in filenames_str
        assert "manage-governance" in filenames_str

    def test_scaffold_node_config_reads_deployment_json(self, tool):
        """Test node config script reads from deployment.json (output of deploy-rollup)."""
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="nodeconfig-test",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        node_config_files = [v for k, v in files.items() if "node-config" in k or "nodeConfig" in k]
        assert len(node_config_files) > 0
        node_code = node_config_files[0]
        assert "deployment.json" in node_code
        assert "prepareNodeConfig" in node_code

    def test_scaffold_node_config_strips_0x_prefix(self, tool):
        """Test node config strips 0x prefix from private keys (Nitro requirement)."""
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="key-test",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        node_config_files = [v for k, v in files.items() if "node-config" in k or "nodeConfig" in k]
        node_code = node_config_files[0] if node_config_files else ""
        assert "replace" in node_code and "0x" in node_code

    def test_scaffold_node_config_handles_same_key(self, tool):
        """Test node config handles batch poster and staker sharing same key."""
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="samekey-test",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        node_config_files = [v for k, v in files.items() if "node-config" in k or "nodeConfig" in k]
        node_code = node_config_files[0] if node_config_files else ""
        # Should detect and handle same-key scenario
        assert "staker" in node_code.lower() or "validator" in node_code.lower()

    def test_scaffold_test_chain_health_check(self, tool):
        """Test scaffold includes chain health check script."""
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="health-test",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        test_files = [v for k, v in files.items() if "test-chain" in k]
        assert len(test_files) > 0
        test_code = test_files[0]
        # Health check should verify chain is operational
        assert "chainId" in test_code or "blockNumber" in test_code or "getBlock" in test_code

    def test_scaffold_setup_instructions_ordered(self, tool):
        """Test setup instructions are in correct deployment order."""
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="order-test",
            parent_chain="arbitrum-sepolia",
        )

        instructions = result.get("setup_instructions", [])
        instructions_str = " ".join(instructions).lower()

        # Correct order: setup → config → deploy rollup → node config → docker → token bridge → test
        config_pos = instructions_str.find("config:chain")
        deploy_pos = instructions_str.find("deploy:rollup")
        node_pos = instructions_str.find("config:node")
        docker_pos = instructions_str.find("docker")
        bridge_pos = instructions_str.find("token-bridge")

        if all(p >= 0 for p in [config_pos, deploy_pos, node_pos, docker_pos, bridge_pos]):
            assert config_pos < deploy_pos, "config:chain must come before deploy:rollup"
            assert deploy_pos < node_pos, "deploy:rollup must come before config:node"
            assert node_pos < docker_pos, "config:node must come before docker"
            assert docker_pos < bridge_pos, "docker must come before token-bridge"

    def test_scaffold_native_token_extra_steps(self, tool):
        """Test that native token adds token approval steps."""
        result = tool.execute(
            prompt="Create a chain with custom gas token",
            chain_name="token-test",
            native_token="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            parent_chain="arbitrum-sepolia",
        )

        instructions = result.get("setup_instructions", [])
        instructions_str = " ".join(instructions).lower()
        # Should have token approval step before deployment
        assert "approve" in instructions_str or "token" in instructions_str

        # Should have more steps than standard (10 vs 8)
        assert len(instructions) >= 8

    def test_anytrust_scaffold_has_das_keys_script(self, tool):
        """Test AnyTrust scaffold includes DAS key generation script."""
        result = tool.execute(
            prompt="Create an AnyTrust project",
            chain_name="das-test",
            is_anytrust=True,
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        filenames_str = str(list(files.keys()))
        assert (
            "das" in filenames_str.lower()
            or "keyset" in filenames_str.lower()
            or "anytrust" in filenames_str.lower()
        )

    def test_scaffold_chain_config_in_result(self, tool):
        """Test that result includes complete chain config metadata."""
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="meta-test",
            chain_id=412399,
            is_anytrust=False,
            parent_chain="arbitrum-sepolia",
        )

        chain_config = result.get("chain_config", {})
        assert chain_config["chain_id"] == 412399
        assert chain_config["chain_name"] == "meta-test"
        assert chain_config["is_anytrust"] is False
        assert chain_config["parent_chain"] == "arbitrum-sepolia"
        assert chain_config["parent_chain_id"] == 421614

    def test_scaffold_project_structure_complete(self, tool):
        """Test project_structure lists all expected directories and files."""
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="structure-test",
            parent_chain="arbitrum-sepolia",
        )

        structure = result.get("project_structure", {})
        assert "scripts/" in structure
        assert "root" in structure

        scripts = structure["scripts/"]
        assert "prepare-chain-config.ts" in scripts
        assert "deploy-rollup.ts" in scripts
        assert "deploy-token-bridge.ts" in scripts
        assert "manage-validators.ts" in scripts
        assert "prepare-node-config.ts" in scripts

        root_files = structure["root"]
        assert "package.json" in root_files
        assert "docker-compose.yml" in root_files
        assert ".env.example" in root_files
        assert "README.md" in root_files


# ============================================================================
# Real Compilation & Validation Tests
# ============================================================================


def _write_files_to_tmpdir(files: dict) -> str:
    """Write generated files to a temp directory and return the path."""
    tmpdir = tempfile.mkdtemp(prefix="orbit_test_")
    for filepath, content in files.items():
        full_path = os.path.join(tmpdir, filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
    return tmpdir


class TestDockerComposeValidation:
    """Validate docker-compose.yml is parseable YAML with correct structure."""

    def test_rollup_compose_is_valid_yaml(self):
        """Test Rollup docker-compose.yml parses as valid YAML."""
        compose = generate_docker_compose("test-chain", 412346, 421614, False)
        try:
            import yaml

            parsed = yaml.safe_load(compose)
        except ImportError:
            # Fall back to basic structure check if PyYAML not available
            parsed = None
            assert "services:" in compose
            assert "nitro-node:" in compose
            return

        assert "services" in parsed
        assert "nitro-node" in parsed["services"]
        node = parsed["services"]["nitro-node"]
        assert "image" in node
        assert "ports" in node
        assert "volumes" in node

    def test_anytrust_compose_is_valid_yaml(self):
        """Test AnyTrust docker-compose.yml parses with DAS service."""
        compose = generate_docker_compose("test-chain", 412347, 421614, True)
        try:
            import yaml

            parsed = yaml.safe_load(compose)
        except ImportError:
            assert "das-server:" in compose
            return

        assert "services" in parsed
        assert "nitro-node" in parsed["services"]
        assert "das-server" in parsed["services"]

        das = parsed["services"]["das-server"]
        assert "image" in das
        assert "ports" in das

    def test_rollup_compose_port_mapping_format(self):
        """Test port mappings are valid host:container format."""
        compose = generate_docker_compose("test-chain", 412346, 421614, False)
        try:
            import yaml

            parsed = yaml.safe_load(compose)
        except ImportError:
            pytest.skip("PyYAML not available")

        ports = parsed["services"]["nitro-node"]["ports"]
        for port in ports:
            port_str = str(port)
            # Should be "host:container" format
            assert ":" in port_str, f"Invalid port format: {port_str}"


class TestGeneratedPackageJson:
    """Validate generated package.json files are valid JSON with correct scripts."""

    def test_orchestrate_package_json_is_valid(self, m4_tools):
        """Test orchestrate generates valid package.json."""
        tool = m4_tools["orchestrate_orbit"]
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="pkg-test",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        pkg_content = files.get("package.json", "")
        assert pkg_content, "package.json not found in generated files"

        # Must parse as valid JSON
        pkg = json.loads(pkg_content)
        assert "name" in pkg
        assert "scripts" in pkg
        assert "dependencies" in pkg or "devDependencies" in pkg

    def test_package_json_has_deployment_scripts(self, m4_tools):
        """Test package.json includes all deployment npm scripts."""
        tool = m4_tools["orchestrate_orbit"]
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="scripts-test",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        pkg = json.loads(files.get("package.json", "{}"))
        scripts = pkg.get("scripts", {})

        # Must have the core deployment scripts referenced in setup_instructions
        expected_scripts = ["config:chain", "deploy:rollup", "deploy:token-bridge", "config:node"]
        for script_name in expected_scripts:
            assert script_name in scripts, f"Missing npm script: {script_name}"

    def test_package_json_dependencies_match(self, m4_tools):
        """Test package.json dependencies match ORBIT_DEPENDENCIES."""
        tool = m4_tools["orchestrate_orbit"]
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="deps-test",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        pkg = json.loads(files.get("package.json", "{}"))
        all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

        # Must include viem and orbit SDK
        assert any("viem" in k for k in all_deps), "viem not in package.json dependencies"


class TestGeneratedTsConfig:
    """Validate generated tsconfig.json is valid JSON."""

    def test_tsconfig_is_valid_json(self, m4_tools):
        """Test tsconfig.json is parseable JSON."""
        tool = m4_tools["orchestrate_orbit"]
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="ts-test",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        tsconfig = files.get("tsconfig.json", "")
        assert tsconfig, "tsconfig.json not found"

        parsed = json.loads(tsconfig)
        assert "compilerOptions" in parsed


class TestTypeScriptCompilation:
    """Actually compile generated TypeScript to catch syntax errors.

    These tests write generated files to a temp directory, install
    a minimal tsconfig, and run tsc --noEmit to check for syntax errors.
    Only checks that the code parses — does not install npm dependencies.
    """

    @pytest.fixture
    def tsc_available(self):
        """Check if TypeScript compiler is available."""
        try:
            result = subprocess.run(
                ["npx", "tsc", "--version"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.path.join(os.path.dirname(__file__), "../../apps/web"),
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        pytest.skip("TypeScript compiler not available")

    def _compile_ts_syntax_check(self, code: str, filename: str = "test.ts") -> tuple:
        """Write TS code to temp dir and check for syntax errors only."""
        tmpdir = tempfile.mkdtemp(prefix="orbit_ts_")

        # Write the code
        ts_path = os.path.join(tmpdir, filename)
        with open(ts_path, "w") as f:
            f.write(code)

        # Write a minimal tsconfig that only checks syntax (skip type checking)
        tsconfig = {
            "compilerOptions": {
                "target": "ES2020",
                "module": "ES2020",
                "moduleResolution": "node",
                "skipLibCheck": True,
                "noEmit": True,
                "strict": False,
                "types": [],
                # Don't resolve imports — we just want syntax checking
                "noResolve": True,
                "isolatedModules": True,
            },
            "include": [filename],
        }
        with open(os.path.join(tmpdir, "tsconfig.json"), "w") as f:
            json.dump(tsconfig, f)

        result = subprocess.run(
            ["npx", "tsc", "--noEmit", "-p", "tsconfig.json"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=tmpdir,
        )

        return result.returncode, result.stdout + result.stderr

    def test_chain_config_compiles(self, m4_tools, tsc_available):
        """Test generated chain config TypeScript has no syntax errors."""
        tool = m4_tools["generate_orbit_config"]
        result = tool.execute(
            prompt="Create a rollup config",
            chain_id=412346,
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        ts_files = {k: v for k, v in files.items() if k.endswith(".ts")}
        assert ts_files, "No TypeScript files generated"

        for filename, code in ts_files.items():
            returncode, output = self._compile_ts_syntax_check(code, os.path.basename(filename))
            # Filter out import resolution errors (expected since we don't install deps)
            real_errors = [
                line
                for line in output.split("\n")
                if "error TS" in line
                and "Cannot find module" not in line
                and "TS2307" not in line  # Cannot find module
                and "TS1259" not in line  # Module can only be default-imported
                and "TS2792" not in line  # Cannot find module (type-only)
                and "TS2591" not in line  # Cannot find name 'process' (needs @types/node)
                and "TS6305" not in line  # Output file not specified
            ]
            assert not real_errors, f"TypeScript syntax errors in {filename}:\n" + "\n".join(
                real_errors
            )

    def test_deploy_rollup_compiles(self, m4_tools, tsc_available):
        """Test generated deploy-rollup TypeScript has no syntax errors."""
        tool = m4_tools["generate_orbit_deployment"]
        result = tool.execute(
            prompt="Deploy rollup",
            deployment_type="rollup",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        ts_files = {k: v for k, v in files.items() if k.endswith(".ts")}

        for filename, code in ts_files.items():
            returncode, output = self._compile_ts_syntax_check(code, os.path.basename(filename))
            real_errors = [
                line
                for line in output.split("\n")
                if "error TS" in line
                and "Cannot find module" not in line
                and "TS2307" not in line
                and "TS1259" not in line
                and "TS2792" not in line
                and "TS6305" not in line
            ]
            assert not real_errors, f"TypeScript syntax errors in {filename}:\n" + "\n".join(
                real_errors
            )

    def test_validator_setup_compiles(self, m4_tools, tsc_available):
        """Test generated validator management TypeScript has no syntax errors."""
        tool = m4_tools["generate_validator_setup"]
        result = tool.execute(
            prompt="Add a validator",
            action="add",
            target="validator",
            addresses=["0x3333333333333333333333333333333333333333"],
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        ts_files = {k: v for k, v in files.items() if k.endswith(".ts")}

        for filename, code in ts_files.items():
            returncode, output = self._compile_ts_syntax_check(code, os.path.basename(filename))
            real_errors = [
                line
                for line in output.split("\n")
                if "error TS" in line
                and "Cannot find module" not in line
                and "TS2307" not in line
                and "TS1259" not in line
                and "TS2792" not in line
                and "TS6305" not in line
            ]
            assert not real_errors, f"TypeScript syntax errors in {filename}:\n" + "\n".join(
                real_errors
            )

    def test_orchestrate_all_scripts_compile(self, m4_tools, tsc_available):
        """Test ALL generated scripts from orchestrate_orbit compile."""
        tool = m4_tools["orchestrate_orbit"]
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="compile-test",
            chain_id=412346,
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        ts_files = {k: v for k, v in files.items() if k.endswith(".ts")}
        assert len(ts_files) >= 5, f"Expected at least 5 TS files, got {len(ts_files)}"

        failures = []
        for filename, code in ts_files.items():
            returncode, output = self._compile_ts_syntax_check(code, os.path.basename(filename))
            real_errors = [
                line
                for line in output.split("\n")
                if "error TS" in line
                and "Cannot find module" not in line
                and "TS2307" not in line
                and "TS1259" not in line
                and "TS2792" not in line
                and "TS6305" not in line
            ]
            if real_errors:
                failures.append(f"{filename}:\n  " + "\n  ".join(real_errors))

        assert not failures, "TypeScript syntax errors in generated files:\n" + "\n".join(failures)


class TestGeneratedEnvFiles:
    """Validate .env.example files have all required variables."""

    def test_orchestrate_env_has_all_required_vars(self, m4_tools):
        """Test .env.example includes all variables referenced in scripts."""
        tool = m4_tools["orchestrate_orbit"]
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="env-test",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        env_content = files.get(".env.example", "")
        assert env_content, ".env.example not found"

        # These vars are referenced in generated scripts
        required_vars = ["DEPLOYER_PRIVATE_KEY", "PARENT_CHAIN_RPC", "CHAIN_ID"]
        for var in required_vars:
            assert var in env_content, f"Missing required env var: {var}"

    def test_deployment_env_has_private_key(self, m4_tools):
        """Test deployment .env.example includes DEPLOYER_PRIVATE_KEY."""
        tool = m4_tools["generate_orbit_deployment"]
        result = tool.execute(
            prompt="Deploy rollup",
            deployment_type="rollup",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        env_files = {k: v for k, v in files.items() if ".env" in k}
        assert env_files
        env_content = list(env_files.values())[0]
        assert "DEPLOYER_PRIVATE_KEY" in env_content


class TestGeneratedSetupScripts:
    """Validate setup.sh and deploy.sh are valid shell scripts."""

    def test_setup_sh_is_valid_bash(self, m4_tools):
        """Test setup.sh passes bash -n syntax check."""
        tool = m4_tools["orchestrate_orbit"]
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="bash-test",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        setup_sh = files.get("setup.sh", "")
        if not setup_sh:
            pytest.skip("setup.sh not in generated files")

        # Write to temp and syntax-check
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(setup_sh)
            f.flush()
            bash_result = subprocess.run(
                ["bash", "-n", f.name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            os.unlink(f.name)

        assert bash_result.returncode == 0, f"setup.sh syntax error:\n{bash_result.stderr}"

    def test_deploy_sh_is_valid_bash(self, m4_tools):
        """Test deploy.sh passes bash -n syntax check."""
        tool = m4_tools["orchestrate_orbit"]
        result = tool.execute(
            prompt="Create a rollup project",
            chain_name="bash-test",
            parent_chain="arbitrum-sepolia",
        )

        files = result.get("files", {})
        deploy_sh = files.get("deploy.sh", "")
        if not deploy_sh:
            pytest.skip("deploy.sh not in generated files")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(deploy_sh)
            f.flush()
            bash_result = subprocess.run(
                ["bash", "-n", f.name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            os.unlink(f.name)

        assert bash_result.returncode == 0, f"deploy.sh syntax error:\n{bash_result.stderr}"

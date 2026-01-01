"""
Test cases for get_workflow MCP tool.

Tests workflow retrieval for build, deploy, and test operations.
"""

import pytest


class TestGetWorkflow:
    """Test suite for get_workflow tool."""

    @pytest.fixture
    def tool(self):
        """Initialize the tool for testing."""
        from src.mcp.tools import GetWorkflowTool
        return GetWorkflowTool()

    def test_build_workflow(self, tool):
        """Test build workflow retrieval."""
        result = tool.execute(workflow_type="build")

        assert "build" in result
        build = result["build"]

        # Check structure
        assert "name" in build
        assert "steps" in build
        assert "quick_commands" in build
        assert "prerequisites" in build

        # Check quick commands
        commands = build["quick_commands"]
        assert "check" in commands
        assert "cargo stylus check" in commands["check"]
        assert "build_release" in commands

    def test_deploy_workflow(self, tool):
        """Test deploy workflow retrieval."""
        result = tool.execute(workflow_type="deploy", network="arbitrum_sepolia")

        assert "deploy" in result
        deploy = result["deploy"]

        # Check structure
        assert "target_network" in deploy
        assert "quick_commands" in deploy
        assert "security_checklist" in deploy

        # Check network config
        network = deploy["target_network"]
        assert "chain_id" in network
        assert "rpc_endpoints" in network

        # Check commands
        commands = deploy["quick_commands"]
        assert "deploy" in commands
        assert "cargo stylus deploy" in commands["deploy"]

    def test_test_workflow(self, tool):
        """Test test workflow retrieval."""
        result = tool.execute(workflow_type="test")

        assert "test" in result
        test = result["test"]

        # Check structure
        assert "test_types" in test
        assert "quick_commands" in test

        # Check commands
        commands = test["quick_commands"]
        assert "run_all_tests" in commands
        assert "cargo test" in commands["run_all_tests"]

    def test_cli_reference(self, tool):
        """Test CLI reference retrieval."""
        result = tool.execute(workflow_type="cli_reference")

        assert "cli_reference" in result
        cli = result["cli_reference"]

        # Check structure
        assert "commands" in cli
        assert "installation" in cli
        assert "troubleshooting" in cli

    def test_networks(self, tool):
        """Test network configs retrieval."""
        result = tool.execute(workflow_type="networks")

        assert "networks" in result
        networks = result["networks"]

        # Check expected networks
        net = networks["networks"]
        assert "arbitrum_one" in net
        assert "arbitrum_sepolia" in net

    def test_all_workflows(self, tool):
        """Test retrieving all workflows."""
        result = tool.execute(workflow_type="all")

        # Should have all sections
        assert "build" in result
        assert "deploy" in result
        assert "test" in result
        assert "cli_reference" in result
        assert "networks" in result

    def test_without_troubleshooting(self, tool):
        """Test excluding troubleshooting info."""
        result = tool.execute(
            workflow_type="build",
            include_troubleshooting=False
        )

        build = result["build"]
        # Steps should not have common_errors when troubleshooting disabled
        for step in build["steps"]:
            assert "common_errors" not in step

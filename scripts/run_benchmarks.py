#!/usr/bin/env python3
"""
Script to run MCP tools benchmarks.

Usage:
    python scripts/run_benchmarks.py                    # Run all benchmarks
    python scripts/run_benchmarks.py --priority P0     # Run only P0 tests
    python scripts/run_benchmarks.py --tool get_stylus_context  # Run single tool
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tests"))


def create_tools():
    """
    Create tool instances.

    This will import the actual tool implementations once they are built.
    For now, returns mock implementations.
    """
    try:
        # Try to import actual implementations
        from src.mcp.tools import (
            GetStylusContextTool,
            GenerateStylusCodeTool,
            AskStylusTool,
            GenerateTestsTool,
        )
        return {
            "get_stylus_context": GetStylusContextTool(),
            "generate_stylus_code": GenerateStylusCodeTool(),
            "ask_stylus": AskStylusTool(),
            "generate_tests": GenerateTestsTool(),
        }
    except ImportError:
        # Fall back to mock implementations
        print("Warning: Using mock tool implementations")
        from mcp_tools.conftest import mock_tools
        # Create mock fixture manually
        class MockFixture:
            def __init__(self):
                self._tools = None

            @property
            def tools(self):
                if self._tools is None:
                    # Inline mock implementations
                    class MockGetStylusContextTool:
                        def execute(self, **kwargs):
                            return {
                                "contexts": [],
                                "total_results": 0,
                                "query": kwargs.get("query", ""),
                            }

                    class MockGenerateStylusCodeTool:
                        def execute(self, **kwargs):
                            return {
                                "code": "",
                                "explanation": "",
                                "dependencies": [],
                                "warnings": [],
                                "context_used": [],
                            }

                    class MockAskStylusTool:
                        def execute(self, **kwargs):
                            return {
                                "answer": "",
                                "code_examples": [],
                                "references": [],
                                "follow_up_questions": [],
                            }

                    class MockGenerateTestsTool:
                        def execute(self, **kwargs):
                            return {
                                "tests": "",
                                "test_summary": {
                                    "total_tests": 0,
                                    "unit_tests": 0,
                                },
                                "coverage_estimate": {},
                                "setup_instructions": "",
                            }

                    self._tools = {
                        "get_stylus_context": MockGetStylusContextTool(),
                        "generate_stylus_code": MockGenerateStylusCodeTool(),
                        "ask_stylus": MockAskStylusTool(),
                        "generate_tests": MockGenerateTestsTool(),
                    }
                return self._tools

        return MockFixture().tools


def main():
    parser = argparse.ArgumentParser(description="Run MCP tools benchmarks")
    parser.add_argument(
        "--priority",
        type=str,
        choices=["P0", "P1", "P2"],
        nargs="+",
        help="Filter by priority level(s)",
    )
    parser.add_argument(
        "--tool",
        type=str,
        choices=["get_stylus_context", "generate_stylus_code", "ask_stylus", "generate_tests"],
        help="Run benchmarks for a specific tool only",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmark_results",
        help="Output directory for benchmark reports",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed output",
    )

    args = parser.parse_args()

    # Create tools
    tools = create_tools()

    # Filter tools if specified
    if args.tool:
        tools = {args.tool: tools[args.tool]}

    # Run benchmarks
    from mcp_tools.benchmark import run_benchmarks, print_report_summary

    output_dir = Path(args.output_dir)
    report = run_benchmarks(
        tools=tools,
        priorities=args.priority,
        output_dir=output_dir,
    )

    if not args.quiet:
        print_report_summary(report)

    # Return exit code based on pass rate
    if report.overall_pass_rate < 0.9:
        print(f"\n❌ Benchmark FAILED: Pass rate {report.overall_pass_rate:.1%} < 90%")
        sys.exit(1)
    else:
        print(f"\n✅ Benchmark PASSED: Pass rate {report.overall_pass_rate:.1%}")
        sys.exit(0)


if __name__ == "__main__":
    main()

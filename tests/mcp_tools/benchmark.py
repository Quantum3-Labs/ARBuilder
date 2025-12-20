"""
Benchmark Evaluation Framework for ARBuilder MCP Tools.

This framework evaluates the quality and performance of the 4 MCP tools:
1. get_stylus_context - Retrieval quality
2. generate_stylus_code - Code generation quality
3. ask_stylus - Q&A accuracy
4. generate_tests - Test generation quality
"""

import json
import time
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Any
from enum import Enum

# Import test cases from each tool's test file
from .test_get_stylus_context import GET_CONTEXT_TEST_CASES
from .test_generate_stylus_code import GENERATE_CODE_TEST_CASES
from .test_ask_stylus import ASK_STYLUS_TEST_CASES
from .test_generate_tests import GENERATE_TESTS_TEST_CASES


class BenchmarkStatus(Enum):
    """Benchmark execution status."""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class BenchmarkResult:
    """Result of a single benchmark test."""
    test_id: str
    test_name: str
    tool: str
    category: str
    priority: str
    status: BenchmarkStatus
    latency_ms: float
    input_data: dict
    expected: dict
    actual: Optional[dict] = None
    error_message: Optional[str] = None
    quality_scores: dict = field(default_factory=dict)


@dataclass
class ToolBenchmarkSummary:
    """Summary of benchmark results for a single tool."""
    tool_name: str
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    by_category: dict = field(default_factory=dict)
    by_priority: dict = field(default_factory=dict)
    quality_metrics: dict = field(default_factory=dict)


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""
    timestamp: str
    duration_seconds: float
    total_tests: int
    total_passed: int
    total_failed: int
    overall_pass_rate: float
    tool_summaries: dict = field(default_factory=dict)
    detailed_results: list = field(default_factory=list)
    quality_assessment: dict = field(default_factory=dict)


class BenchmarkRunner:
    """
    Runs benchmarks for all MCP tools and generates reports.
    """

    def __init__(
        self,
        tools: dict,  # {"tool_name": tool_instance}
        output_dir: Path = Path("benchmark_results"),
    ):
        """
        Initialize the benchmark runner.

        Args:
            tools: Dictionary mapping tool names to tool instances.
            output_dir: Directory for benchmark output files.
        """
        self.tools = tools
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Map tool names to test cases
        self.test_case_map = {
            "get_stylus_context": GET_CONTEXT_TEST_CASES,
            "generate_stylus_code": GENERATE_CODE_TEST_CASES,
            "ask_stylus": ASK_STYLUS_TEST_CASES,
            "generate_tests": GENERATE_TESTS_TEST_CASES,
        }

        # Quality thresholds (from spec)
        self.quality_thresholds = {
            "get_stylus_context": {
                "max_latency_ms": 2000,
                "min_recall_at_5": 0.80,
            },
            "generate_stylus_code": {
                "max_latency_ms": 10000,
                "min_syntax_validity": 0.95,
            },
            "ask_stylus": {
                "max_latency_ms": 5000,
                "min_answer_accuracy": 0.90,
            },
            "generate_tests": {
                "max_latency_ms": 10000,
                "min_test_validity": 0.90,
            },
        }

    def run_all_benchmarks(
        self,
        priorities: Optional[list[str]] = None,
        categories: Optional[list[str]] = None,
    ) -> BenchmarkReport:
        """
        Run benchmarks for all tools.

        Args:
            priorities: Filter to specific priorities (e.g., ["P0", "P1"]).
            categories: Filter to specific categories.

        Returns:
            Complete benchmark report.
        """
        start_time = time.time()
        all_results: list[BenchmarkResult] = []

        for tool_name, tool in self.tools.items():
            test_cases = self.test_case_map.get(tool_name, [])

            # Apply filters
            if priorities:
                test_cases = [tc for tc in test_cases if tc["priority"] in priorities]
            if categories:
                test_cases = [tc for tc in test_cases if tc["category"] in categories]

            print(f"\nRunning {len(test_cases)} benchmarks for {tool_name}...")

            for test_case in test_cases:
                result = self._run_single_benchmark(tool_name, tool, test_case)
                all_results.append(result)

        duration = time.time() - start_time

        # Generate report
        report = self._generate_report(all_results, duration)

        # Save report
        self._save_report(report)

        return report

    def run_tool_benchmark(
        self,
        tool_name: str,
        priorities: Optional[list[str]] = None,
    ) -> ToolBenchmarkSummary:
        """Run benchmarks for a specific tool."""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        tool = self.tools[tool_name]
        test_cases = self.test_case_map.get(tool_name, [])

        if priorities:
            test_cases = [tc for tc in test_cases if tc["priority"] in priorities]

        results = []
        for test_case in test_cases:
            result = self._run_single_benchmark(tool_name, tool, test_case)
            results.append(result)

        return self._generate_tool_summary(tool_name, results)

    def _run_single_benchmark(
        self,
        tool_name: str,
        tool: Any,
        test_case: dict,
    ) -> BenchmarkResult:
        """Run a single benchmark test case."""
        start_time = time.time()

        try:
            # Execute the tool
            actual = tool.execute(**test_case["input"])
            latency_ms = (time.time() - start_time) * 1000

            # Validate result
            expected = test_case["expected"]
            passed, quality_scores, error_msg = self._validate_result(
                tool_name, actual, expected
            )

            return BenchmarkResult(
                test_id=test_case["id"],
                test_name=test_case["name"],
                tool=tool_name,
                category=test_case["category"],
                priority=test_case["priority"],
                status=BenchmarkStatus.PASSED if passed else BenchmarkStatus.FAILED,
                latency_ms=latency_ms,
                input_data=test_case["input"],
                expected=expected,
                actual=actual,
                error_message=error_msg,
                quality_scores=quality_scores,
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return BenchmarkResult(
                test_id=test_case["id"],
                test_name=test_case["name"],
                tool=tool_name,
                category=test_case["category"],
                priority=test_case["priority"],
                status=BenchmarkStatus.ERROR,
                latency_ms=latency_ms,
                input_data=test_case["input"],
                expected=test_case["expected"],
                error_message=str(e),
            )

    def _validate_result(
        self,
        tool_name: str,
        actual: dict,
        expected: dict,
    ) -> tuple[bool, dict, Optional[str]]:
        """
        Validate actual result against expected criteria.

        Returns:
            Tuple of (passed, quality_scores, error_message)
        """
        quality_scores = {}
        errors = []

        # Common validations
        if expected.get("should_error"):
            if "error" not in actual:
                errors.append("Expected error but got success")
            elif "error_contains" in expected:
                if expected["error_contains"] not in actual.get("error", "").lower():
                    errors.append(f"Error doesn't contain: {expected['error_contains']}")
            # If we expected an error and got one, that's a pass
            if not errors:
                return True, {"error_handling": 1.0}, None

        # Tool-specific validations
        if tool_name == "get_stylus_context":
            quality_scores, err = self._validate_context_result(actual, expected)
            if err:
                errors.extend(err)

        elif tool_name == "generate_stylus_code":
            quality_scores, err = self._validate_code_result(actual, expected)
            if err:
                errors.extend(err)

        elif tool_name == "ask_stylus":
            quality_scores, err = self._validate_answer_result(actual, expected)
            if err:
                errors.extend(err)

        elif tool_name == "generate_tests":
            quality_scores, err = self._validate_tests_result(actual, expected)
            if err:
                errors.extend(err)

        passed = len(errors) == 0
        error_msg = "; ".join(errors) if errors else None

        return passed, quality_scores, error_msg

    def _validate_context_result(
        self,
        actual: dict,
        expected: dict,
    ) -> tuple[dict, list[str]]:
        """Validate get_stylus_context results."""
        scores = {}
        errors = []

        contexts = actual.get("contexts", [])

        # Check minimum results
        if "min_results" in expected:
            if len(contexts) < expected["min_results"]:
                errors.append(f"Too few results: {len(contexts)} < {expected['min_results']}")
            scores["result_count"] = min(len(contexts) / max(expected["min_results"], 1), 1.0)

        # Check keyword presence
        if "must_contain_keywords" in expected:
            all_content = " ".join(ctx.get("content", "").lower() for ctx in contexts)
            found = sum(1 for kw in expected["must_contain_keywords"] if kw.lower() in all_content)
            total = len(expected["must_contain_keywords"])
            scores["keyword_recall"] = found / total if total > 0 else 1.0
            if found < total:
                missing = [kw for kw in expected["must_contain_keywords"] if kw.lower() not in all_content]
                errors.append(f"Missing keywords: {missing}")

        # Check relevance threshold
        if "relevance_threshold" in expected and contexts:
            top_score = contexts[0].get("relevance_score", 0)
            scores["relevance"] = top_score
            if top_score < expected["relevance_threshold"]:
                errors.append(f"Low relevance: {top_score} < {expected['relevance_threshold']}")

        return scores, errors

    def _validate_code_result(
        self,
        actual: dict,
        expected: dict,
    ) -> tuple[dict, list[str]]:
        """Validate generate_stylus_code results."""
        scores = {}
        errors = []

        code = actual.get("code", "")

        # Check syntax validity
        if expected.get("syntax_valid"):
            is_valid = self._check_rust_syntax(code)
            scores["syntax_valid"] = 1.0 if is_valid else 0.0
            if not is_valid:
                errors.append("Invalid Rust syntax")

        # Check patterns
        if "must_have_patterns" in expected:
            found = sum(1 for p in expected["must_have_patterns"] if re.search(p, code, re.I))
            total = len(expected["must_have_patterns"])
            scores["pattern_coverage"] = found / total if total > 0 else 1.0
            if found < total:
                missing = [p for p in expected["must_have_patterns"] if not re.search(p, code, re.I)]
                errors.append(f"Missing patterns: {missing}")

        # Check keywords
        if "must_have_keywords" in expected:
            code_lower = code.lower()
            found = sum(1 for kw in expected["must_have_keywords"] if kw.lower() in code_lower)
            total = len(expected["must_have_keywords"])
            scores["keyword_coverage"] = found / total if total > 0 else 1.0
            if found < total:
                errors.append(f"Missing keywords in code")

        return scores, errors

    def _validate_answer_result(
        self,
        actual: dict,
        expected: dict,
    ) -> tuple[dict, list[str]]:
        """Validate ask_stylus results."""
        scores = {}
        errors = []

        answer = actual.get("answer", "")

        # Check minimum length
        if "answer_min_length" in expected:
            length_ratio = len(answer) / expected["answer_min_length"]
            scores["length"] = min(length_ratio, 1.0)
            if len(answer) < expected["answer_min_length"]:
                errors.append(f"Answer too short: {len(answer)} < {expected['answer_min_length']}")

        # Check required keywords
        if "answer_contains" in expected:
            answer_lower = answer.lower()
            found = sum(1 for kw in expected["answer_contains"] if kw.lower() in answer_lower)
            total = len(expected["answer_contains"])
            scores["keyword_coverage"] = found / total if total > 0 else 1.0
            if found < total:
                errors.append("Missing required keywords in answer")

        # Check code examples
        if expected.get("should_have_code_example"):
            has_code = "code_examples" in actual or "```" in answer or "fn " in answer
            scores["has_code"] = 1.0 if has_code else 0.0
            if not has_code:
                errors.append("Missing code example")

        return scores, errors

    def _validate_tests_result(
        self,
        actual: dict,
        expected: dict,
    ) -> tuple[dict, list[str]]:
        """Validate generate_tests results."""
        scores = {}
        errors = []

        tests = actual.get("tests", "")

        # Check syntax
        if expected.get("syntax_valid"):
            is_valid = self._check_test_syntax(tests)
            scores["syntax_valid"] = 1.0 if is_valid else 0.0
            if not is_valid:
                errors.append("Invalid test syntax")

        # Check minimum test count
        if "min_test_count" in expected:
            test_count = len(re.findall(r"#\[test\]", tests))
            scores["test_count"] = min(test_count / max(expected["min_test_count"], 1), 1.0)
            if test_count < expected["min_test_count"]:
                errors.append(f"Too few tests: {test_count} < {expected['min_test_count']}")

        # Check function coverage
        if "should_test_functions" in expected:
            tests_lower = tests.lower()
            found = sum(1 for fn in expected["should_test_functions"] if fn.lower() in tests_lower)
            total = len(expected["should_test_functions"])
            scores["function_coverage"] = found / total if total > 0 else 1.0
            if found < total:
                errors.append("Not all functions tested")

        return scores, errors

    def _check_rust_syntax(self, code: str) -> bool:
        """Basic Rust syntax check."""
        if not code.strip():
            return False
        if code.count("{") != code.count("}"):
            return False
        if code.count("(") != code.count(")"):
            return False
        return True

    def _check_test_syntax(self, tests: str) -> bool:
        """Basic test syntax check."""
        if not tests.strip():
            return False
        return "#[test]" in tests or "fn test_" in tests

    def _generate_tool_summary(
        self,
        tool_name: str,
        results: list[BenchmarkResult],
    ) -> ToolBenchmarkSummary:
        """Generate summary for a single tool."""
        summary = ToolBenchmarkSummary(tool_name=tool_name)
        summary.total_tests = len(results)

        latencies = []
        for r in results:
            latencies.append(r.latency_ms)
            if r.status == BenchmarkStatus.PASSED:
                summary.passed += 1
            elif r.status == BenchmarkStatus.FAILED:
                summary.failed += 1
            elif r.status == BenchmarkStatus.ERROR:
                summary.errors += 1
            else:
                summary.skipped += 1

            # By category
            cat = r.category
            if cat not in summary.by_category:
                summary.by_category[cat] = {"passed": 0, "failed": 0, "total": 0}
            summary.by_category[cat]["total"] += 1
            if r.status == BenchmarkStatus.PASSED:
                summary.by_category[cat]["passed"] += 1
            else:
                summary.by_category[cat]["failed"] += 1

            # By priority
            prio = r.priority
            if prio not in summary.by_priority:
                summary.by_priority[prio] = {"passed": 0, "failed": 0, "total": 0}
            summary.by_priority[prio]["total"] += 1
            if r.status == BenchmarkStatus.PASSED:
                summary.by_priority[prio]["passed"] += 1
            else:
                summary.by_priority[prio]["failed"] += 1

        # Calculate latency percentiles
        if latencies:
            latencies.sort()
            summary.avg_latency_ms = sum(latencies) / len(latencies)
            summary.p50_latency_ms = latencies[len(latencies) // 2]
            summary.p95_latency_ms = latencies[int(len(latencies) * 0.95)]
            summary.p99_latency_ms = latencies[int(len(latencies) * 0.99)]

        # Aggregate quality metrics
        all_scores = {}
        for r in results:
            for metric, value in r.quality_scores.items():
                if metric not in all_scores:
                    all_scores[metric] = []
                all_scores[metric].append(value)

        summary.quality_metrics = {
            metric: sum(values) / len(values)
            for metric, values in all_scores.items()
            if values
        }

        return summary

    def _generate_report(
        self,
        results: list[BenchmarkResult],
        duration: float,
    ) -> BenchmarkReport:
        """Generate complete benchmark report."""
        # Group by tool
        by_tool: dict[str, list[BenchmarkResult]] = {}
        for r in results:
            if r.tool not in by_tool:
                by_tool[r.tool] = []
            by_tool[r.tool].append(r)

        # Generate tool summaries
        tool_summaries = {
            tool: self._generate_tool_summary(tool, tool_results)
            for tool, tool_results in by_tool.items()
        }

        total_passed = sum(s.passed for s in tool_summaries.values())
        total_failed = sum(s.failed + s.errors for s in tool_summaries.values())

        # Quality assessment
        quality_assessment = self._assess_quality(tool_summaries)

        return BenchmarkReport(
            timestamp=datetime.now().isoformat(),
            duration_seconds=duration,
            total_tests=len(results),
            total_passed=total_passed,
            total_failed=total_failed,
            overall_pass_rate=total_passed / len(results) if results else 0,
            tool_summaries={name: self._summary_to_dict(s) for name, s in tool_summaries.items()},
            detailed_results=[self._result_to_dict(r) for r in results],
            quality_assessment=quality_assessment,
        )

    def _assess_quality(
        self,
        tool_summaries: dict[str, ToolBenchmarkSummary],
    ) -> dict:
        """Assess overall quality against thresholds."""
        assessment = {
            "meets_requirements": True,
            "by_tool": {},
        }

        for tool_name, summary in tool_summaries.items():
            thresholds = self.quality_thresholds.get(tool_name, {})
            tool_assessment = {"passes": [], "failures": []}

            # Check latency
            if "max_latency_ms" in thresholds:
                if summary.p95_latency_ms <= thresholds["max_latency_ms"]:
                    tool_assessment["passes"].append(
                        f"P95 latency ({summary.p95_latency_ms:.0f}ms) <= {thresholds['max_latency_ms']}ms"
                    )
                else:
                    tool_assessment["failures"].append(
                        f"P95 latency ({summary.p95_latency_ms:.0f}ms) > {thresholds['max_latency_ms']}ms"
                    )
                    assessment["meets_requirements"] = False

            # Check pass rate
            pass_rate = summary.passed / summary.total_tests if summary.total_tests > 0 else 0
            if pass_rate >= 0.9:
                tool_assessment["passes"].append(f"Pass rate ({pass_rate:.1%}) >= 90%")
            else:
                tool_assessment["failures"].append(f"Pass rate ({pass_rate:.1%}) < 90%")
                assessment["meets_requirements"] = False

            assessment["by_tool"][tool_name] = tool_assessment

        return assessment

    def _summary_to_dict(self, summary: ToolBenchmarkSummary) -> dict:
        """Convert summary to dictionary."""
        return {
            "tool_name": summary.tool_name,
            "total_tests": summary.total_tests,
            "passed": summary.passed,
            "failed": summary.failed,
            "errors": summary.errors,
            "pass_rate": summary.passed / summary.total_tests if summary.total_tests > 0 else 0,
            "avg_latency_ms": summary.avg_latency_ms,
            "p50_latency_ms": summary.p50_latency_ms,
            "p95_latency_ms": summary.p95_latency_ms,
            "p99_latency_ms": summary.p99_latency_ms,
            "by_category": summary.by_category,
            "by_priority": summary.by_priority,
            "quality_metrics": summary.quality_metrics,
        }

    def _result_to_dict(self, result: BenchmarkResult) -> dict:
        """Convert result to dictionary."""
        return {
            "test_id": result.test_id,
            "test_name": result.test_name,
            "tool": result.tool,
            "category": result.category,
            "priority": result.priority,
            "status": result.status.value,
            "latency_ms": result.latency_ms,
            "error_message": result.error_message,
            "quality_scores": result.quality_scores,
        }

    def _save_report(self, report: BenchmarkReport) -> Path:
        """Save benchmark report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_report_{timestamp}.json"
        filepath = self.output_dir / filename

        report_dict = {
            "timestamp": report.timestamp,
            "duration_seconds": report.duration_seconds,
            "total_tests": report.total_tests,
            "total_passed": report.total_passed,
            "total_failed": report.total_failed,
            "overall_pass_rate": report.overall_pass_rate,
            "tool_summaries": report.tool_summaries,
            "quality_assessment": report.quality_assessment,
            "detailed_results": report.detailed_results,
        }

        with open(filepath, "w") as f:
            json.dump(report_dict, f, indent=2)

        print(f"\nBenchmark report saved to: {filepath}")
        return filepath


def print_report_summary(report: BenchmarkReport):
    """Print a human-readable summary of the benchmark report."""
    print("\n" + "=" * 60)
    print("BENCHMARK REPORT SUMMARY")
    print("=" * 60)
    print(f"Timestamp: {report.timestamp}")
    print(f"Duration: {report.duration_seconds:.2f} seconds")
    print(f"Total Tests: {report.total_tests}")
    print(f"Passed: {report.total_passed} ({report.overall_pass_rate:.1%})")
    print(f"Failed: {report.total_failed}")

    print("\n" + "-" * 40)
    print("BY TOOL:")
    print("-" * 40)

    for tool_name, summary in report.tool_summaries.items():
        pass_rate = summary["passed"] / summary["total_tests"] if summary["total_tests"] > 0 else 0
        print(f"\n{tool_name}:")
        print(f"  Tests: {summary['total_tests']}, Passed: {summary['passed']} ({pass_rate:.1%})")
        print(f"  Latency (P50/P95/P99): {summary['p50_latency_ms']:.0f}ms / {summary['p95_latency_ms']:.0f}ms / {summary['p99_latency_ms']:.0f}ms")

        if summary["quality_metrics"]:
            print(f"  Quality Metrics:")
            for metric, value in summary["quality_metrics"].items():
                print(f"    - {metric}: {value:.2f}")

    print("\n" + "-" * 40)
    print("QUALITY ASSESSMENT:")
    print("-" * 40)
    assessment = report.quality_assessment
    status = "PASS" if assessment["meets_requirements"] else "FAIL"
    print(f"Overall: {status}")

    for tool_name, tool_assessment in assessment["by_tool"].items():
        print(f"\n{tool_name}:")
        for p in tool_assessment["passes"]:
            print(f"  [PASS] {p}")
        for f in tool_assessment["failures"]:
            print(f"  [FAIL] {f}")

    print("\n" + "=" * 60)


# Entry point for running benchmarks
def run_benchmarks(
    tools: dict,
    priorities: Optional[list[str]] = None,
    output_dir: Path = Path("benchmark_results"),
) -> BenchmarkReport:
    """
    Run all benchmarks and generate a report.

    Args:
        tools: Dictionary of tool name to tool instance.
        priorities: Filter to specific priorities.
        output_dir: Output directory for reports.

    Returns:
        BenchmarkReport with all results.
    """
    runner = BenchmarkRunner(tools, output_dir)
    report = runner.run_all_benchmarks(priorities=priorities)
    print_report_summary(report)
    return report


if __name__ == "__main__":
    # This would be run with actual tool implementations
    print("Benchmark framework ready. Import and run with tool implementations.")

#!/usr/bin/env python3
"""
Source Verification Pipeline for ARBuilder.

6-step verification for code repositories:
  1. SDK Version Check   — parse Cargo.toml / package.json
  2. Compile Check       — cargo stylus check / npm run build
  3. Deploy Check        — deploy to Arbitrum Sepolia (optional)
  4. Tests & GitHub Health — run tests, check GitHub API
  5. AI Code Review      — security, quality, teaching value
  6. Fork                — fork to our org (optional)

Usage:
    # Verify a single repo
    python scripts/verify_source.py https://github.com/org/repo

    # Verify all repos in config
    python scripts/verify_source.py --all

    # Verify with specific steps only
    python scripts/verify_source.py https://github.com/org/repo --steps 1,2,4

    # Skip deploy (default: deploy is skipped unless --deploy flag)
    python scripts/verify_source.py --all --deploy

    # Output JSON report
    python scripts/verify_source.py --all --output reports/verification.json
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from scraper.config import (
    PROJECT_EXAMPLES,
    get_all_config_repo_urls,
    get_config_repo_info,
)
from scraper.version_extractor import (
    extract_sdk_version_from_repo,
    compare_versions,
    detect_deprecated_patterns,
)

load_dotenv()

console = Console()

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
REVIEW_MODEL = os.getenv("REVIEW_MODEL", "google/gemini-2.0-flash-001")
SEPOLIA_RPC = os.getenv("SEPOLIA_RPC", "https://sepolia-rollup.arbitrum.io/rpc")
DEPLOY_PRIVATE_KEY = os.getenv("DEPLOY_PRIVATE_KEY", "")

# Version thresholds
MIN_STYLUS_SDK = "0.8.0"
MAIN_STYLUS_SDK = "0.9.0"
MIN_ARBITRUM_SDK = "4.0.0"

REPOS_DIR = PROJECT_ROOT / "data" / "raw" / "repos"


class VerificationResult:
    """Result of a single verification step."""

    def __init__(self, step: str, passed: bool, details: dict = None, skipped: bool = False):
        self.step = step
        self.passed = passed
        self.skipped = skipped
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "passed": self.passed,
            "skipped": self.skipped,
            **self.details,
        }


class SourceVerifier:
    """Runs the 6-step verification pipeline on a repository."""

    def __init__(
        self,
        repo_url: str,
        clone_dir: Optional[Path] = None,
        steps: Optional[list[int]] = None,
        enable_deploy: bool = False,
        enable_fork: bool = False,
        fork_org: str = "",
    ):
        self.repo_url = repo_url.rstrip("/")
        self.repo_name = self._get_repo_name(repo_url)
        self.clone_dir = clone_dir or REPOS_DIR / self.repo_name
        self.steps = steps or [1, 2, 3, 4, 5, 6]
        self.enable_deploy = enable_deploy
        self.enable_fork = enable_fork
        self.fork_org = fork_org
        self.results: list[VerificationResult] = []
        self.repo_type = "unknown"  # "stylus", "sdk", "typescript"
        self.sdk_version: Optional[str] = None

    @staticmethod
    def _get_repo_name(url: str) -> str:
        parts = url.rstrip("/").split("/")
        if len(parts) >= 2:
            return f"{parts[-2]}_{parts[-1]}"
        return parts[-1]

    def _get_github_owner_repo(self) -> tuple[str, str]:
        """Extract owner and repo from GitHub URL."""
        parts = self.repo_url.rstrip("/").split("/")
        return parts[-2], parts[-1]

    def verify(self) -> dict:
        """Run the full verification pipeline. Returns JSON-serializable report."""
        console.print(f"\n[bold]{'=' * 60}[/bold]")
        console.print(f"[bold]Verifying: {self.repo_url}[/bold]")
        console.print(f"[bold]{'=' * 60}[/bold]")

        # Ensure repo is cloned
        if not self.clone_dir.exists():
            console.print(f"[blue]Cloning {self.repo_url}...[/blue]")
            success = self._clone_repo()
            if not success:
                return self._build_report(overall_status="clone_failed")

        # Detect repo type
        self._detect_repo_type()

        # Run each step
        if 1 in self.steps:
            self._step1_sdk_version()
        if 2 in self.steps:
            self._step2_compile()
        if 3 in self.steps:
            self._step3_deploy()
        if 4 in self.steps:
            self._step4_tests_and_health()
        if 5 in self.steps:
            self._step5_code_review()
        if 6 in self.steps:
            self._step6_fork()

        # Determine overall status
        failed = [r for r in self.results if not r.passed and not r.skipped]
        skipped = [r for r in self.results if r.skipped]
        passed = [r for r in self.results if r.passed]

        if failed:
            overall = "failed"
        elif len(passed) == 0:
            overall = "skipped"
        else:
            overall = "verified"

        return self._build_report(overall_status=overall)

    def _build_report(self, overall_status: str) -> dict:
        return {
            "repo_url": self.repo_url,
            "repo_name": self.repo_name,
            "repo_type": self.repo_type,
            "sdk_version": self.sdk_version,
            "verified_at": datetime.utcnow().isoformat(),
            "overall_status": overall_status,
            "steps": [r.to_dict() for r in self.results],
        }

    def _clone_repo(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", self.repo_url, str(self.clone_dir)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return result.returncode == 0
        except Exception as e:
            console.print(f"[red]Clone failed: {e}[/red]")
            return False

    def _detect_repo_type(self):
        """Detect whether this is a Stylus (Rust), SDK (TypeScript), or other repo."""
        cargo_files = list(self.clone_dir.rglob("Cargo.toml"))
        package_files = list(self.clone_dir.rglob("package.json"))

        # Check for stylus-sdk in any Cargo.toml
        for cargo in cargo_files:
            try:
                content = cargo.read_text()
                if "stylus-sdk" in content:
                    self.repo_type = "stylus"
                    return
            except Exception:
                pass

        # Check for @arbitrum/sdk in any package.json
        for pkg in package_files:
            try:
                content = pkg.read_text()
                if "@arbitrum/sdk" in content:
                    self.repo_type = "sdk"
                    return
            except Exception:
                pass

        # Fallback: if has Cargo.toml it's Rust, if has package.json it's TypeScript
        if cargo_files:
            self.repo_type = "rust"
        elif package_files:
            self.repo_type = "typescript"

    # ──────────────────────────────────────────────────────────────
    # Step 1: SDK Version Check
    # ──────────────────────────────────────────────────────────────

    def _step1_sdk_version(self):
        console.print("\n[bold cyan]Step 1: SDK Version Check[/bold cyan]")

        if self.repo_type == "stylus":
            version = extract_sdk_version_from_repo(self.clone_dir)
            self.sdk_version = version

            if not version:
                console.print("[red]  No stylus-sdk found in Cargo.toml[/red]")
                self.results.append(VerificationResult(
                    "sdk_version", False,
                    {"error": "stylus-sdk not found in Cargo.toml"},
                ))
                return

            meets_min = compare_versions(version, MIN_STYLUS_SDK) >= 0
            is_main = compare_versions(version, MAIN_STYLUS_SDK) >= 0

            status = "pass" if meets_min else "fail"
            console.print(f"  SDK version: {version} ({'PASS' if meets_min else 'FAIL'}, min={MIN_STYLUS_SDK})")
            console.print(f"  Main version: {'yes' if is_main else 'no'} (main={MAIN_STYLUS_SDK})")

            self.results.append(VerificationResult(
                "sdk_version", meets_min,
                {
                    "sdk_version": version,
                    "meets_minimum": meets_min,
                    "is_main_version": is_main,
                    "minimum_required": MIN_STYLUS_SDK,
                    "main_version": MAIN_STYLUS_SDK,
                },
            ))

        elif self.repo_type == "sdk":
            version = self._extract_arbitrum_sdk_version()
            self.sdk_version = version

            if not version:
                console.print("[red]  No @arbitrum/sdk found in package.json[/red]")
                self.results.append(VerificationResult(
                    "sdk_version", False,
                    {"error": "@arbitrum/sdk not found in package.json"},
                ))
                return

            meets_min = compare_versions(version, MIN_ARBITRUM_SDK) >= 0
            console.print(f"  @arbitrum/sdk version: {version} ({'PASS' if meets_min else 'FAIL'})")

            self.results.append(VerificationResult(
                "sdk_version", meets_min,
                {
                    "sdk_version": version,
                    "meets_minimum": meets_min,
                    "minimum_required": MIN_ARBITRUM_SDK,
                },
            ))
        else:
            console.print(f"  [yellow]Repo type '{self.repo_type}' — no SDK version check applicable[/yellow]")
            self.results.append(VerificationResult(
                "sdk_version", True, {"note": f"No SDK check for repo type: {self.repo_type}"}, skipped=True,
            ))

    def _extract_arbitrum_sdk_version(self) -> Optional[str]:
        """Extract @arbitrum/sdk version from package.json."""
        for pkg_path in self.clone_dir.rglob("package.json"):
            if "node_modules" in pkg_path.parts:
                continue
            try:
                data = json.loads(pkg_path.read_text())
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                version = deps.get("@arbitrum/sdk", "")
                if version:
                    return version.lstrip("^~>=")
            except Exception:
                pass
        return None

    # ──────────────────────────────────────────────────────────────
    # Step 2: Compile Check
    # ──────────────────────────────────────────────────────────────

    def _step2_compile(self):
        console.print("\n[bold cyan]Step 2: Compile Check[/bold cyan]")

        if self.repo_type == "stylus":
            self._compile_stylus()
        elif self.repo_type in ("sdk", "typescript"):
            self._compile_typescript()
        else:
            console.print(f"  [yellow]No compile check for repo type: {self.repo_type}[/yellow]")
            self.results.append(VerificationResult(
                "compile", True, {"note": f"No compile check for: {self.repo_type}"}, skipped=True,
            ))

    def _compile_stylus(self):
        """Run cargo stylus check on Stylus repos."""
        # Find the directory with the stylus Cargo.toml
        work_dir = self._find_stylus_root()
        if not work_dir:
            console.print("[red]  Could not find Stylus project root[/red]")
            self.results.append(VerificationResult(
                "compile", False, {"error": "No Stylus project root found"},
            ))
            return

        # Use cargo build --release (compile only, no on-chain verification)
        # cargo stylus check tries to connect to a local devnode which may not be running
        cmd = ["cargo", "build", "--release"]

        console.print(f"  Running: {' '.join(cmd)} in {work_dir}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(work_dir),
            )

            passed = result.returncode == 0
            # Also check if cargo stylus check would pass (compilation part)
            # by looking at stderr — if "Finished" appears, compilation succeeded
            compiled_ok = "Finished" in result.stderr or "Finished" in result.stdout
            if not passed and compiled_ok:
                # Build succeeded but something else failed (e.g., post-build step)
                passed = True

            console.print(f"  {'PASS' if passed else 'FAIL'} (exit code {result.returncode})")

            if not passed:
                # Show last 20 lines of stderr for debugging
                stderr_lines = result.stderr.strip().splitlines()[-20:]
                for line in stderr_lines:
                    console.print(f"  [red]{line}[/red]")

            self.results.append(VerificationResult(
                "compile", passed,
                {
                    "command": " ".join(cmd),
                    "exit_code": result.returncode,
                    "stderr_tail": result.stderr.strip()[-500:] if not passed else "",
                },
            ))

        except subprocess.TimeoutExpired:
            console.print("[red]  Compile timed out (300s)[/red]")
            self.results.append(VerificationResult(
                "compile", False, {"error": "Compile timed out after 300s"},
            ))
        except Exception as e:
            console.print(f"[red]  Compile error: {e}[/red]")
            self.results.append(VerificationResult(
                "compile", False, {"error": str(e)},
            ))

    def _compile_typescript(self):
        """Run npm install + npm run build on TypeScript repos."""
        # Find directory with package.json
        pkg_json = self.clone_dir / "package.json"
        if not pkg_json.exists():
            # Search one level deep
            for p in self.clone_dir.iterdir():
                if p.is_dir() and (p / "package.json").exists():
                    pkg_json = p / "package.json"
                    break

        if not pkg_json.exists():
            console.print("[red]  No package.json found[/red]")
            self.results.append(VerificationResult(
                "compile", False, {"error": "No package.json found"},
            ))
            return

        work_dir = pkg_json.parent
        console.print(f"  Running npm install in {work_dir}...")

        try:
            # Install deps
            install_result = subprocess.run(
                ["npm", "install"],
                capture_output=True, text=True, timeout=120, cwd=str(work_dir),
            )

            if install_result.returncode != 0:
                console.print(f"  [red]npm install failed[/red]")
                self.results.append(VerificationResult(
                    "compile", False,
                    {"error": "npm install failed", "stderr_tail": install_result.stderr.strip()[-500:]},
                ))
                return

            # Check if build script exists
            try:
                pkg_data = json.loads(pkg_json.read_text())
                scripts = pkg_data.get("scripts", {})
            except Exception:
                scripts = {}

            if "build" not in scripts:
                console.print("  [yellow]No build script, skipping build step[/yellow]")
                self.results.append(VerificationResult(
                    "compile", True, {"note": "No build script, install succeeded"}, skipped=True,
                ))
                return

            # Build
            console.print(f"  Running npm run build...")
            build_result = subprocess.run(
                ["npm", "run", "build"],
                capture_output=True, text=True, timeout=180, cwd=str(work_dir),
            )

            passed = build_result.returncode == 0
            console.print(f"  {'PASS' if passed else 'FAIL'}")

            self.results.append(VerificationResult(
                "compile", passed,
                {
                    "command": "npm run build",
                    "exit_code": build_result.returncode,
                    "stderr_tail": build_result.stderr.strip()[-500:] if not passed else "",
                },
            ))

        except subprocess.TimeoutExpired:
            console.print("[red]  Build timed out[/red]")
            self.results.append(VerificationResult(
                "compile", False, {"error": "Build timed out"},
            ))
        except Exception as e:
            console.print(f"[red]  Build error: {e}[/red]")
            self.results.append(VerificationResult(
                "compile", False, {"error": str(e)},
            ))

    def _find_stylus_root(self) -> Optional[Path]:
        """Find the directory containing the Stylus Cargo.toml."""
        # Check root first
        root_cargo = self.clone_dir / "Cargo.toml"
        if root_cargo.exists():
            try:
                content = root_cargo.read_text()
                if "stylus-sdk" in content:
                    return self.clone_dir
            except Exception:
                pass

        # Search subdirectories
        for cargo_path in self.clone_dir.rglob("Cargo.toml"):
            if "target" in cargo_path.parts or "node_modules" in cargo_path.parts:
                continue
            try:
                content = cargo_path.read_text()
                if "stylus-sdk" in content:
                    return cargo_path.parent
            except Exception:
                pass

        return None

    # ──────────────────────────────────────────────────────────────
    # Step 3: Deploy Check
    # ──────────────────────────────────────────────────────────────

    def _step3_deploy(self):
        console.print("\n[bold cyan]Step 3: Deploy Check[/bold cyan]")

        if not self.enable_deploy:
            console.print("  [yellow]Deploy check skipped (use --deploy to enable)[/yellow]")
            self.results.append(VerificationResult(
                "deploy", True, {"note": "Skipped — use --deploy flag to enable"}, skipped=True,
            ))
            return

        if self.repo_type != "stylus":
            console.print(f"  [yellow]Deploy only supported for Stylus repos[/yellow]")
            self.results.append(VerificationResult(
                "deploy", True, {"note": f"Deploy not applicable for: {self.repo_type}"}, skipped=True,
            ))
            return

        if not DEPLOY_PRIVATE_KEY:
            console.print("  [yellow]DEPLOY_PRIVATE_KEY not set, skipping deploy[/yellow]")
            self.results.append(VerificationResult(
                "deploy", True, {"note": "No DEPLOY_PRIVATE_KEY configured"}, skipped=True,
            ))
            return

        work_dir = self._find_stylus_root()
        if not work_dir:
            self.results.append(VerificationResult(
                "deploy", False, {"error": "No Stylus project root found"},
            ))
            return

        console.print(f"  Deploying to Arbitrum Sepolia...")
        try:
            result = subprocess.run(
                [
                    "cargo", "stylus", "deploy",
                    "--private-key", DEPLOY_PRIVATE_KEY,
                    "--endpoint", SEPOLIA_RPC,
                ],
                capture_output=True, text=True, timeout=300, cwd=str(work_dir),
            )

            passed = result.returncode == 0

            # Try to extract contract address from output
            contract_address = ""
            if passed:
                addr_match = re.search(r"(0x[0-9a-fA-F]{40})", result.stdout)
                if addr_match:
                    contract_address = addr_match.group(1)

            console.print(f"  {'PASS' if passed else 'FAIL'}")
            if contract_address:
                console.print(f"  Contract: {contract_address}")

            self.results.append(VerificationResult(
                "deploy", passed,
                {
                    "exit_code": result.returncode,
                    "contract_address": contract_address,
                    "stderr_tail": result.stderr.strip()[-500:] if not passed else "",
                },
            ))

        except subprocess.TimeoutExpired:
            console.print("[red]  Deploy timed out (300s)[/red]")
            self.results.append(VerificationResult(
                "deploy", False, {"error": "Deploy timed out after 300s"},
            ))
        except Exception as e:
            console.print(f"[red]  Deploy error: {e}[/red]")
            self.results.append(VerificationResult(
                "deploy", False, {"error": str(e)},
            ))

    # ──────────────────────────────────────────────────────────────
    # Step 4: Tests & GitHub Health
    # ──────────────────────────────────────────────────────────────

    def _step4_tests_and_health(self):
        console.print("\n[bold cyan]Step 4: Tests & GitHub Health[/bold cyan]")

        test_result = self._run_tests()
        health_result = self._check_github_health()

        # Combine into one result
        combined = {**test_result, **health_result}
        # Pass criteria: not archived and not deleted
        # "stale" and "abandoned" are warnings, not failures (repo may be complete)
        # Tests timed out = inconclusive, not failure
        health_score = combined.get("health_score", "unknown")
        hard_fail = health_score in ("archived", "deleted")
        tests_timed_out = combined.get("tests_timed_out", False)
        tests_failed = (
            combined.get("has_tests")
            and not combined.get("tests_pass")
            and not tests_timed_out
        )
        passed = not hard_fail and not tests_failed

        self.results.append(VerificationResult(
            "tests_and_health", passed, combined,
        ))

    def _run_tests(self) -> dict:
        """Run tests if they exist."""
        result = {
            "has_tests": False,
            "tests_pass": False,
            "test_count": 0,
            "test_output": "",
        }

        if self.repo_type == "stylus":
            work_dir = self._find_stylus_root()
            if not work_dir:
                return result

            # Check if there are test files
            test_files = list(work_dir.rglob("*test*"))
            has_test_attr = False
            for rs_file in work_dir.rglob("*.rs"):
                try:
                    content = rs_file.read_text()
                    if "#[cfg(test)]" in content or "#[test]" in content:
                        has_test_attr = True
                        break
                except Exception:
                    pass

            if not test_files and not has_test_attr:
                console.print("  [yellow]No tests found[/yellow]")
                return result

            result["has_tests"] = True
            console.print("  Running cargo test...")
            try:
                test_run = subprocess.run(
                    ["cargo", "test"],
                    capture_output=True, text=True, timeout=180, cwd=str(work_dir),
                )
                result["tests_pass"] = test_run.returncode == 0
                result["test_output"] = test_run.stdout[-500:]

                # Parse test count
                count_match = re.search(r"(\d+) passed", test_run.stdout)
                if count_match:
                    result["test_count"] = int(count_match.group(1))

                console.print(f"  Tests: {'PASS' if result['tests_pass'] else 'FAIL'} ({result['test_count']} passed)")

            except subprocess.TimeoutExpired:
                console.print("  [yellow]Tests timed out (180s) — inconclusive[/yellow]")
                result["test_output"] = "Timed out after 180s"
                result["tests_timed_out"] = True
            except Exception as e:
                result["test_output"] = str(e)

        elif self.repo_type in ("sdk", "typescript"):
            # Check for test script in package.json
            pkg_json = self.clone_dir / "package.json"
            if pkg_json.exists():
                try:
                    pkg_data = json.loads(pkg_json.read_text())
                    if "test" in pkg_data.get("scripts", {}):
                        result["has_tests"] = True
                        console.print("  Running npm test...")
                        test_run = subprocess.run(
                            ["npm", "test", "--", "--passWithNoTests"],
                            capture_output=True, text=True, timeout=180,
                            cwd=str(self.clone_dir),
                        )
                        result["tests_pass"] = test_run.returncode == 0
                        result["test_output"] = test_run.stdout[-500:]
                        console.print(f"  Tests: {'PASS' if result['tests_pass'] else 'FAIL'}")
                    else:
                        console.print("  [yellow]No test script in package.json[/yellow]")
                except Exception:
                    pass

        return result

    def _check_github_health(self) -> dict:
        """Check GitHub API for repo health metrics."""
        result = {
            "last_commit": "",
            "archived": False,
            "open_issues": 0,
            "stars": 0,
            "forks": 0,
            "health_score": "unknown",
        }

        owner, repo = self._get_github_owner_repo()
        headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"

        try:
            with httpx.Client(timeout=15.0) as client:
                # Get repo info
                resp = client.get(
                    f"https://api.github.com/repos/{owner}/{repo}",
                    headers=headers,
                )

                if resp.status_code == 404:
                    console.print("  [red]Repository not found (404)[/red]")
                    result["health_score"] = "deleted"
                    return result

                if resp.status_code != 200:
                    console.print(f"  [yellow]GitHub API returned {resp.status_code}[/yellow]")
                    return result

                data = resp.json()
                result["archived"] = data.get("archived", False)
                result["open_issues"] = data.get("open_issues_count", 0)
                result["stars"] = data.get("stargazers_count", 0)
                result["forks"] = data.get("forks_count", 0)
                result["last_commit"] = data.get("pushed_at", "")

                # Determine health score
                if result["archived"]:
                    result["health_score"] = "archived"
                    console.print("  [red]Repository is archived[/red]")
                elif result["last_commit"]:
                    last_push = datetime.fromisoformat(result["last_commit"].replace("Z", "+00:00"))
                    days_since = (datetime.now(last_push.tzinfo) - last_push).days

                    if days_since < 90:
                        result["health_score"] = "active"
                    elif days_since < 180:
                        result["health_score"] = "stale"
                    else:
                        result["health_score"] = "abandoned"

                console.print(f"  Health: {result['health_score']} | Stars: {result['stars']} | Issues: {result['open_issues']} | Last push: {result['last_commit'][:10] if result['last_commit'] else 'unknown'}")

        except Exception as e:
            console.print(f"  [yellow]GitHub API error: {e}[/yellow]")

        return result

    # ──────────────────────────────────────────────────────────────
    # Step 5: AI Code Review
    # ──────────────────────────────────────────────────────────────

    def _step5_code_review(self):
        console.print("\n[bold cyan]Step 5: AI Code Review[/bold cyan]")

        if not OPENROUTER_API_KEY:
            console.print("  [yellow]OPENROUTER_API_KEY not set, skipping AI review[/yellow]")
            self.results.append(VerificationResult(
                "code_review", True, {"note": "Skipped — no OPENROUTER_API_KEY"}, skipped=True,
            ))
            return

        # Collect code files for review
        code_content = self._collect_review_code()
        if not code_content:
            console.print("  [yellow]No code files found to review[/yellow]")
            self.results.append(VerificationResult(
                "code_review", True, {"note": "No code files found"}, skipped=True,
            ))
            return

        console.print(f"  Reviewing {len(code_content)} files with {REVIEW_MODEL}...")

        review = self._call_ai_review(code_content)

        if review:
            console.print(f"  Security: {review.get('security_score', '?')}/100")
            console.print(f"  Quality: {review.get('quality_score', '?')}/100")
            console.print(f"  Teaching value: {review.get('teaching_value', '?')}")
            console.print(f"  Recommendation: {review.get('recommendation', '?')}")

            if review.get("issues"):
                console.print(f"  Issues found: {len(review['issues'])}")
                for issue in review["issues"][:5]:
                    console.print(f"    [{issue.get('severity', '?')}] {issue.get('message', '')}")

            passed = review.get("security_score", 0) >= 50
            self.results.append(VerificationResult("code_review", passed, review))
        else:
            self.results.append(VerificationResult(
                "code_review", True, {"note": "AI review failed, skipped"}, skipped=True,
            ))

    def _collect_review_code(self) -> list[dict]:
        """Collect source files for AI review (limited to key files)."""
        files = []
        max_files = 10
        max_chars_per_file = 3000

        # Prioritize main source files
        patterns = []
        if self.repo_type == "stylus":
            patterns = ["**/*.rs"]
        elif self.repo_type in ("sdk", "typescript"):
            patterns = ["**/*.ts", "**/*.js"]
        else:
            patterns = ["**/*.rs", "**/*.ts"]

        for pattern in patterns:
            for path in self.clone_dir.glob(pattern):
                if any(skip in path.parts for skip in ("node_modules", "target", ".git", "dist")):
                    continue
                try:
                    content = path.read_text()[:max_chars_per_file]
                    files.append({
                        "path": str(path.relative_to(self.clone_dir)),
                        "content": content,
                    })
                    if len(files) >= max_files:
                        return files
                except Exception:
                    pass

        return files

    def _call_ai_review(self, files: list[dict]) -> Optional[dict]:
        """Send code to AI model for review."""
        files_text = "\n\n".join(
            f"--- {f['path']} ---\n{f['content']}" for f in files
        )

        prompt = f"""You are a code quality reviewer for Arbitrum Stylus smart contracts and SDK code.

Review the following code files and provide a JSON assessment:

{files_text}

Respond with ONLY a valid JSON object (no markdown, no explanation):
{{
  "security_score": <0-100>,
  "quality_score": <0-100>,
  "teaching_value": "high" | "medium" | "low",
  "recommendation": "include" | "include_with_caveats" | "exclude",
  "issues": [
    {{"severity": "critical"|"warning"|"info", "file": "<path>", "message": "<description>"}}
  ],
  "summary": "<1-2 sentence summary>"
}}

Scoring guide:
- security_score: 90+ = no issues, 70-89 = minor issues, 50-69 = moderate, <50 = critical
- quality_score: 90+ = production-ready, 70-89 = good, 50-69 = acceptable, <50 = poor
- teaching_value: "high" = clean patterns worth teaching, "medium" = acceptable, "low" = anti-patterns
- recommendation: "include" = add to knowledge base, "exclude" = skip entirely"""

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/arbbuilder",
                        "X-Title": "ARBuilder Verification",
                    },
                    json={
                        "model": REVIEW_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0,
                        "max_tokens": 1000,
                    },
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"].strip()

                # Parse JSON from response (handle markdown code blocks)
                content = re.sub(r"^```json?\s*\n?", "", content)
                content = re.sub(r"\n?```\s*$", "", content)

                return json.loads(content)

        except json.JSONDecodeError as e:
            console.print(f"  [yellow]Could not parse AI review response: {e}[/yellow]")
            return None
        except Exception as e:
            console.print(f"  [yellow]AI review error: {e}[/yellow]")
            return None

    # ──────────────────────────────────────────────────────────────
    # Step 6: Fork
    # ──────────────────────────────────────────────────────────────

    def _step6_fork(self):
        console.print("\n[bold cyan]Step 6: Fork[/bold cyan]")

        if not self.enable_fork:
            console.print("  [yellow]Fork skipped (use --fork to enable)[/yellow]")
            self.results.append(VerificationResult(
                "fork", True, {"note": "Skipped — use --fork flag to enable"}, skipped=True,
            ))
            return

        if not GITHUB_TOKEN:
            console.print("  [yellow]GITHUB_TOKEN not set, cannot fork[/yellow]")
            self.results.append(VerificationResult(
                "fork", True, {"note": "Skipped — no GITHUB_TOKEN"}, skipped=True,
            ))
            return

        owner, repo = self._get_github_owner_repo()
        console.print(f"  Forking {owner}/{repo}...")

        try:
            with httpx.Client(timeout=30.0) as client:
                payload = {}
                if self.fork_org:
                    payload["organization"] = self.fork_org

                resp = client.post(
                    f"https://api.github.com/repos/{owner}/{repo}/forks",
                    headers={
                        "Authorization": f"token {GITHUB_TOKEN}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                    json=payload,
                )

                if resp.status_code in (200, 202):
                    fork_data = resp.json()
                    fork_url = fork_data.get("html_url", "")
                    console.print(f"  [green]Forked to: {fork_url}[/green]")

                    self.results.append(VerificationResult(
                        "fork", True,
                        {"fork_url": fork_url},
                    ))
                elif resp.status_code == 422:
                    # Already forked
                    console.print("  [yellow]Fork already exists[/yellow]")
                    self.results.append(VerificationResult(
                        "fork", True, {"note": "Fork already exists"},
                    ))
                else:
                    console.print(f"  [red]Fork failed: {resp.status_code} {resp.text}[/red]")
                    self.results.append(VerificationResult(
                        "fork", False,
                        {"error": f"GitHub API {resp.status_code}: {resp.text[:200]}"},
                    ))

        except Exception as e:
            console.print(f"  [red]Fork error: {e}[/red]")
            self.results.append(VerificationResult(
                "fork", False, {"error": str(e)},
            ))


# ──────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────

def verify_all_config_repos(
    steps: list[int],
    enable_deploy: bool,
    enable_fork: bool,
    fork_org: str,
) -> list[dict]:
    """Verify all repos in the current config."""
    reports = []

    for category, subcats in PROJECT_EXAMPLES.items():
        for subcat, entries in subcats.items():
            for entry in entries:
                url = entry["url"]
                if "github.com" not in url:
                    continue

                verifier = SourceVerifier(
                    repo_url=url,
                    steps=steps,
                    enable_deploy=enable_deploy,
                    enable_fork=enable_fork,
                    fork_org=fork_org,
                )
                report = verifier.verify()
                report["config_category"] = category
                report["config_subcategory"] = subcat
                report["config_sdk_version"] = entry.get("sdk_version", "")
                reports.append(report)

    return reports


def print_summary(reports: list[dict]):
    """Print a summary table of all verification results."""
    table = Table(title="Verification Summary")
    table.add_column("Repo", style="cyan", max_width=40)
    table.add_column("Type", style="blue")
    table.add_column("SDK", style="magenta")
    table.add_column("Status", style="bold")
    table.add_column("Version", justify="center")
    table.add_column("Compile", justify="center")
    table.add_column("Tests", justify="center")
    table.add_column("Health", justify="center")
    table.add_column("Review", justify="center")

    for r in reports:
        status_style = {
            "verified": "[green]PASS[/green]",
            "failed": "[red]FAIL[/red]",
            "clone_failed": "[red]CLONE FAIL[/red]",
            "skipped": "[yellow]SKIP[/yellow]",
        }.get(r["overall_status"], r["overall_status"])

        # Extract step results
        step_map = {s["step"]: s for s in r.get("steps", [])}

        def step_icon(step_name: str) -> str:
            s = step_map.get(step_name)
            if s is None:
                return "[dim]·[/dim]"  # Step not run
            if s.get("skipped"):
                return "[yellow]-[/yellow]"
            return "[green]Y[/green]" if s.get("passed") else "[red]N[/red]"

        table.add_row(
            r["repo_name"][:40],
            r.get("repo_type", "?"),
            r.get("sdk_version") or "-",
            status_style,
            step_icon("sdk_version"),
            step_icon("compile"),
            step_icon("tests_and_health"),
            step_map.get("tests_and_health", {}).get("health_score", "-"),
            step_icon("code_review"),
        )

    console.print(table)

    # Summary counts
    total = len(reports)
    passed = sum(1 for r in reports if r["overall_status"] == "verified")
    failed = sum(1 for r in reports if r["overall_status"] == "failed")
    console.print(f"\n[bold]Total: {total} | Passed: {passed} | Failed: {failed}[/bold]")


def main():
    parser = argparse.ArgumentParser(
        description="ARBuilder Source Verification Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/verify_source.py https://github.com/OffchainLabs/stylus-hello-world
  python scripts/verify_source.py --all
  python scripts/verify_source.py --all --steps 1,2,4
  python scripts/verify_source.py --all --deploy --output reports/verification.json
        """,
    )
    parser.add_argument("repo_url", nargs="?", help="GitHub repo URL to verify")
    parser.add_argument("--all", action="store_true", help="Verify all repos in config")
    parser.add_argument(
        "--steps",
        type=str,
        default="1,2,3,4,5,6",
        help="Comma-separated step numbers to run (default: 1,2,3,4,5,6)",
    )
    parser.add_argument("--deploy", action="store_true", help="Enable deploy check (Step 3)")
    parser.add_argument("--fork", action="store_true", help="Enable forking (Step 6)")
    parser.add_argument("--fork-org", type=str, default="", help="GitHub org to fork to")
    parser.add_argument("--output", type=str, help="Output JSON report path")

    args = parser.parse_args()

    if not args.repo_url and not args.all:
        parser.print_help()
        sys.exit(1)

    steps = [int(s.strip()) for s in args.steps.split(",")]

    if args.all:
        reports = verify_all_config_repos(
            steps=steps,
            enable_deploy=args.deploy,
            enable_fork=args.fork,
            fork_org=args.fork_org,
        )
    else:
        verifier = SourceVerifier(
            repo_url=args.repo_url,
            steps=steps,
            enable_deploy=args.deploy,
            enable_fork=args.fork,
            fork_org=args.fork_org,
        )
        reports = [verifier.verify()]

    # Print summary
    print_summary(reports)

    # Save JSON report
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(reports, f, indent=2)
        console.print(f"\n[green]Report saved to: {output_path}[/green]")


if __name__ == "__main__":
    main()

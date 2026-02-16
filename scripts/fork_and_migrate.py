#!/usr/bin/env python3
"""
Fork & Migrate Script for ARBuilder.

Automates forking community/production Stylus repos under ARBuilder-Forks
and migrating them to SDK 0.10.0. Produces high-quality, human-verifiable
0.10.0 code for the RAG pipeline.

Usage:
    # Migrate all repos
    python scripts/fork_and_migrate.py --all

    # Migrate specific repo
    python scripts/fork_and_migrate.py --repo OffchainLabs/stylus-hello-world

    # Dry run (show what would be changed, no fork/push)
    python scripts/fork_and_migrate.py --all --dry-run

    # Skip compile verification
    python scripts/fork_and_migrate.py --all --skip-verify

    # Re-verify already-forked repos (useful after manual fixes)
    python scripts/fork_and_migrate.py --all --verify-only
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.table import Table

from scraper.config import PROJECT_EXAMPLES
from scraper.version_extractor import extract_sdk_version_from_repo
from src.utils.version_manager import (
    apply_version_transforms,
    get_cargo_deps_for_version,
    get_main_version,
    compare_versions,
)

console = Console()

# Organization to fork repos into
FORK_ORG = "ARBuilder-Forks"

# Local directory for fork clones
FORKS_DIR = PROJECT_ROOT / "data" / "raw" / "forks"

# Target SDK version for migration
TARGET_VERSION = get_main_version()

# Target repos: all Stylus repos from config
TARGET_REPOS = []
for _subcat, entries in PROJECT_EXAMPLES.get("stylus", {}).items():
    for entry in entries:
        url = entry["url"]
        # Extract owner/repo from GitHub URL
        parts = url.rstrip("/").split("/")
        if len(parts) >= 2:
            owner_repo = f"{parts[-2]}/{parts[-1]}"
            TARGET_REPOS.append({
                "owner_repo": owner_repo,
                "url": url,
                "sdk_version": entry.get("sdk_version", ""),
                "category": _subcat,
            })

# Required files for SDK 0.10.0
STYLUS_TOML_CONTENT = '[workspace]\n\n[workspace.networks]\n\n[contract]\n'
RUST_TOOLCHAIN_CONTENT = '[toolchain]\nchannel = "1.88.0"\ntargets = ["wasm32-unknown-unknown"]\n'


def _generate_main_rs(crate_name: str) -> str:
    """Generate src/main.rs for SDK 0.10.0."""
    return f'''#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]

#[cfg(not(any(test, feature = "export-abi")))]
#[unsafe(no_mangle)]
pub extern "C" fn main() {{}}

#[cfg(feature = "export-abi")]
fn main() {{
    {crate_name}::print_from_args();
}}
'''


def _run_cmd(cmd: list[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    try:
        return subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            check=check, timeout=120,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="Timeout")
    except subprocess.CalledProcessError as e:
        return e


def fork_exists(owner_repo: str) -> bool:
    """Check if fork already exists in the target org."""
    repo_name = owner_repo.split("/")[-1]
    result = _run_cmd(
        ["gh", "repo", "view", f"{FORK_ORG}/{repo_name}", "--json", "name"],
        check=False,
    )
    return result.returncode == 0


def create_fork(owner_repo: str) -> bool:
    """Fork a repo to the target org."""
    result = _run_cmd(
        ["gh", "repo", "fork", owner_repo, "--org", FORK_ORG, "--clone=false"],
        check=False,
    )
    if result.returncode != 0:
        console.print(f"  [red]Fork failed: {result.stderr.strip()}[/red]")
        return False
    console.print(f"  [green]Forked {owner_repo} → {FORK_ORG}[/green]")
    return True


def clone_fork(owner_repo: str) -> Optional[Path]:
    """Clone the fork locally."""
    repo_name = owner_repo.split("/")[-1]
    clone_dir = FORKS_DIR / repo_name

    if clone_dir.exists():
        console.print(f"  [yellow]Clone already exists: {clone_dir}[/yellow]")
        # Pull latest
        _run_cmd(["git", "pull"], cwd=clone_dir, check=False)
        return clone_dir

    FORKS_DIR.mkdir(parents=True, exist_ok=True)
    result = _run_cmd(
        ["gh", "repo", "clone", f"{FORK_ORG}/{repo_name}", str(clone_dir)],
        check=False,
    )
    if result.returncode != 0:
        console.print(f"  [red]Clone failed: {result.stderr.strip()}[/red]")
        return None
    return clone_dir


def migrate_rust_files(repo_dir: Path, from_version: str, dry_run: bool = False) -> list[str]:
    """Migrate all .rs files in the repo to SDK 0.10.0.

    Returns list of changed file paths (relative to repo_dir).
    """
    changed = []
    for rs_file in repo_dir.rglob("*.rs"):
        # Skip target/ and .git/ directories
        rel = rs_file.relative_to(repo_dir)
        if any(part in ("target", ".git") for part in rel.parts):
            continue

        original = rs_file.read_text(encoding="utf-8", errors="replace")
        transformed = apply_version_transforms(original, from_version, TARGET_VERSION)

        if transformed != original:
            changed.append(str(rel))
            if not dry_run:
                rs_file.write_text(transformed, encoding="utf-8")

    return changed


def update_cargo_toml(repo_dir: Path, dry_run: bool = False) -> list[str]:
    """Update Cargo.toml files with SDK 0.10.0 deps.

    Returns list of changed Cargo.toml paths.
    """
    deps = get_cargo_deps_for_version(TARGET_VERSION)
    changed = []

    for cargo_file in repo_dir.rglob("Cargo.toml"):
        rel = cargo_file.relative_to(repo_dir)
        if any(part in ("target", ".git") for part in rel.parts):
            continue

        content = cargo_file.read_text(encoding="utf-8", errors="replace")
        original = content

        # Only update Cargo.toml files that have stylus-sdk dependency
        if "stylus-sdk" not in content:
            continue

        # Update stylus-sdk version (simple and complex formats)
        content = re.sub(
            r'(stylus-sdk\s*=\s*(?:\{[^}]*version\s*=\s*)")([^"]+)(")',
            rf'\g<1>{deps["stylus_sdk"]}\3',
            content,
        )
        content = re.sub(
            r'(stylus-sdk\s*=\s*")([^"]+)(")',
            rf'\g<1>{deps["stylus_sdk"]}\3',
            content,
        )

        # Update alloy-primitives
        content = re.sub(
            r'(alloy-primitives\s*=\s*")([^"]+)(")',
            rf'\g<1>{deps["alloy_primitives"]}\3',
            content,
        )

        # Update alloy-sol-types
        content = re.sub(
            r'(alloy-sol-types\s*=\s*")([^"]+)(")',
            rf'\g<1>{deps["alloy_sol_types"]}\3',
            content,
        )

        # Ensure crate-type includes "lib"
        if 'crate-type = ["cdylib"]' in content:
            content = content.replace(
                'crate-type = ["cdylib"]',
                'crate-type = ["lib", "cdylib"]',
            )

        # Fix package name: hyphens → underscores
        name_match = re.search(r'\[package\].*?name\s*=\s*"([^"]+)"', content, re.DOTALL)
        if name_match:
            pkg_name = name_match.group(1)
            if "-" in pkg_name:
                new_name = pkg_name.replace("-", "_")
                content = content.replace(f'name = "{pkg_name}"', f'name = "{new_name}"')

        if content != original:
            changed.append(str(rel))
            if not dry_run:
                cargo_file.write_text(content, encoding="utf-8")

    return changed


def add_required_files(repo_dir: Path, dry_run: bool = False) -> list[str]:
    """Add Stylus.toml, rust-toolchain.toml, src/main.rs if missing.

    Returns list of added file paths.
    """
    added = []

    # Find the project root (directory containing Cargo.toml with stylus-sdk)
    project_roots = []
    for cargo_file in repo_dir.rglob("Cargo.toml"):
        rel = cargo_file.relative_to(repo_dir)
        if any(part in ("target", ".git") for part in rel.parts):
            continue
        content = cargo_file.read_text(encoding="utf-8", errors="replace")
        if "stylus-sdk" in content:
            project_roots.append(cargo_file.parent)

    for project_root in project_roots:
        rel_root = project_root.relative_to(repo_dir)
        prefix = str(rel_root) + "/" if str(rel_root) != "." else ""

        # Stylus.toml
        stylus_toml = project_root / "Stylus.toml"
        if not stylus_toml.exists():
            added.append(f"{prefix}Stylus.toml")
            if not dry_run:
                stylus_toml.write_text(STYLUS_TOML_CONTENT, encoding="utf-8")

        # rust-toolchain.toml — always overwrite to ensure correct version
        rust_toolchain = project_root / "rust-toolchain.toml"
        existing_content = rust_toolchain.read_text(encoding="utf-8") if rust_toolchain.exists() else ""
        if existing_content.strip() != RUST_TOOLCHAIN_CONTENT.strip():
            added.append(f"{prefix}rust-toolchain.toml")
            if not dry_run:
                rust_toolchain.write_text(RUST_TOOLCHAIN_CONTENT, encoding="utf-8")

        # src/main.rs
        main_rs = project_root / "src" / "main.rs"
        if not main_rs.exists():
            # Derive crate name from Cargo.toml
            cargo_content = (project_root / "Cargo.toml").read_text(encoding="utf-8", errors="replace")
            name_match = re.search(r'name\s*=\s*"([^"]+)"', cargo_content)
            crate_name = name_match.group(1).replace("-", "_") if name_match else "contract"

            added.append(f"{prefix}src/main.rs")
            if not dry_run:
                main_rs.parent.mkdir(parents=True, exist_ok=True)
                main_rs.write_text(_generate_main_rs(crate_name), encoding="utf-8")

    return added


def apply_fix_code_patterns(repo_dir: Path) -> int:
    """Apply _fix_code-style regex patterns to all .rs files.

    Returns number of files fixed.
    """
    fixed_count = 0
    for rs_file in repo_dir.rglob("*.rs"):
        rel = rs_file.relative_to(repo_dir)
        if any(part in ("target", ".git") for part in rel.parts):
            continue

        content = rs_file.read_text(encoding="utf-8", errors="replace")
        original = content

        # Remove duplicate/standalone alloc::vec imports before adding combined one
        content = re.sub(r'^use alloc::vec::Vec;\s*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^use alloc::vec;\s*\n', '', content, flags=re.MULTILINE)

        # Ensure alloc::{vec, vec::Vec} import (skip if already has combined alloc import)
        if "use alloc::{vec" not in content and "use alloc::{string" not in content:
            if "extern crate alloc" in content:
                content = re.sub(
                    r'(extern crate alloc;\s*\n)',
                    r'\1\nuse alloc::{vec, vec::Vec};\n',
                    content,
                )

        # Remove deprecated evm/msg imports (should already be done by transforms but ensure)
        content = re.sub(r'^use stylus_sdk::evm.*;\s*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^use stylus_sdk::msg.*;\s*\n', '', content, flags=re.MULTILINE)

        # Fix cfg_attr patterns
        if "#![cfg_attr(not(any(test" not in content and "#![cfg_attr" in content:
            content = re.sub(
                r'#!\[cfg_attr\(not\(any\(feature\s*=\s*"export-abi",\s*test\)\),\s*no_std\)\]',
                '#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]',
                content,
            )
            content = re.sub(
                r'#!\[cfg_attr\(not\(test\),\s*no_main\)\]',
                '#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]',
                content,
            )

        if content != original:
            rs_file.write_text(content, encoding="utf-8")
            fixed_count += 1

    return fixed_count


def verify_repo(repo_dir: Path) -> dict:
    """Run verification checks on a migrated repo.

    Returns dict with verification results.
    """
    results = {
        "sdk_version_check": None,
        "compile_check": None,
        "test_check": None,
    }

    # Step 1: SDK version check
    detected = extract_sdk_version_from_repo(repo_dir)
    if detected and compare_versions(detected, TARGET_VERSION) >= 0:
        results["sdk_version_check"] = {"passed": True, "version": detected}
    else:
        results["sdk_version_check"] = {"passed": False, "version": detected}

    # Step 2: Compile check (try cargo build, fall back to cargo check)
    # Find project directories with Cargo.toml containing stylus-sdk
    for cargo_file in repo_dir.rglob("Cargo.toml"):
        rel = cargo_file.relative_to(repo_dir)
        if any(part in ("target", ".git") for part in rel.parts):
            continue
        cargo_content = cargo_file.read_text(encoding="utf-8", errors="replace")
        if "stylus-sdk" not in cargo_content:
            continue

        project_dir = cargo_file.parent
        result = _run_cmd(
            ["cargo", "check", "--lib"],
            cwd=project_dir,
            check=False,
        )
        results["compile_check"] = {
            "passed": result.returncode == 0,
            "stdout": result.stdout[:500] if result.stdout else "",
            "stderr": result.stderr[:1000] if result.stderr else "",
        }
        break

    # Step 3: Test check (soft-fail)
    for cargo_file in repo_dir.rglob("Cargo.toml"):
        rel = cargo_file.relative_to(repo_dir)
        if any(part in ("target", ".git") for part in rel.parts):
            continue
        cargo_content = cargo_file.read_text(encoding="utf-8", errors="replace")
        if "stylus-sdk" not in cargo_content:
            continue

        project_dir = cargo_file.parent
        result = _run_cmd(
            ["cargo", "test"],
            cwd=project_dir,
            check=False,
        )
        results["test_check"] = {
            "passed": result.returncode == 0,
            "stdout": result.stdout[:500] if result.stdout else "",
            "stderr": result.stderr[:500] if result.stderr else "",
        }
        break

    return results


def commit_and_push(repo_dir: Path) -> bool:
    """Commit changes and push to the fork."""
    _run_cmd(["git", "add", "-A"], cwd=repo_dir, check=False)
    result = _run_cmd(
        ["git", "commit", "-m", "chore: migrate to Stylus SDK 0.10.0\n\nAutomated migration by ARBuilder fork_and_migrate.py"],
        cwd=repo_dir,
        check=False,
    )
    if result.returncode != 0:
        if "nothing to commit" in (result.stdout or "") + (result.stderr or ""):
            console.print("  [yellow]No changes to commit[/yellow]")
            return True
        console.print(f"  [red]Commit failed: {result.stderr.strip()}[/red]")
        return False

    push_result = _run_cmd(["git", "push"], cwd=repo_dir, check=False)
    if push_result.returncode != 0:
        console.print(f"  [red]Push failed: {push_result.stderr.strip()}[/red]")
        return False
    return True


def process_repo(
    repo_info: dict,
    dry_run: bool = False,
    skip_verify: bool = False,
    verify_only: bool = False,
) -> dict:
    """Process a single repo: fork, migrate, verify.

    Returns report dict.
    """
    owner_repo = repo_info["owner_repo"]
    original_sdk = repo_info.get("sdk_version", "unknown")
    repo_name = owner_repo.split("/")[-1]

    report = {
        "repo": owner_repo,
        "original_sdk": original_sdk,
        "target_sdk": TARGET_VERSION,
        "status": "pending",
        "files_changed": [],
        "files_added": [],
        "compile_result": None,
        "test_result": None,
        "error": None,
    }

    console.print(f"\n[bold]Processing {owner_repo}[/bold] (SDK {original_sdk})")

    # If verify-only, just re-verify existing fork
    if verify_only:
        clone_dir = FORKS_DIR / repo_name
        if not clone_dir.exists():
            report["status"] = "skipped"
            report["error"] = "Fork clone not found"
            console.print(f"  [yellow]Skipped: clone not found at {clone_dir}[/yellow]")
            return report

        console.print("  [blue]Verifying...[/blue]")
        verify_results = verify_repo(clone_dir)
        report["compile_result"] = verify_results.get("compile_check")
        report["test_result"] = verify_results.get("test_check")
        report["status"] = "verified" if verify_results.get("compile_check", {}).get("passed") else "verify_failed"
        return report

    # Step 1: Check if fork exists
    if not dry_run:
        if fork_exists(owner_repo):
            console.print(f"  [yellow]Fork already exists: {FORK_ORG}/{repo_name}[/yellow]")
        else:
            # Step 2: Fork
            console.print("  [blue]Forking...[/blue]")
            if not create_fork(owner_repo):
                report["status"] = "fork_failed"
                report["error"] = "Fork creation failed"
                return report

        # Step 3: Clone
        console.print("  [blue]Cloning...[/blue]")
        clone_dir = clone_fork(owner_repo)
        if not clone_dir:
            report["status"] = "clone_failed"
            report["error"] = "Clone failed"
            return report
    else:
        # Dry run: use existing clone or original repo
        clone_dir = FORKS_DIR / repo_name
        if not clone_dir.exists():
            # Try the original scraper repos dir
            clone_dir = PROJECT_ROOT / "data" / "raw" / "repos" / repo_name
            if not clone_dir.exists():
                # Try with owner prefix
                for d in (PROJECT_ROOT / "data" / "raw" / "repos").iterdir():
                    if d.name.endswith(repo_name) or d.name == f"{owner_repo.replace('/', '_')}":
                        clone_dir = d
                        break
        if not clone_dir.exists():
            report["status"] = "dry_run_no_source"
            report["error"] = f"No local clone found for dry run. Clone to {FORKS_DIR / repo_name} first."
            console.print(f"  [yellow]Dry run: no local clone found[/yellow]")
            return report

    # Step 4: Migrate .rs files
    from_version = original_sdk if original_sdk and original_sdk != "unknown" else "0.9.0"
    console.print(f"  [blue]Migrating .rs files ({from_version} → {TARGET_VERSION})...[/blue]")
    rs_changed = migrate_rust_files(clone_dir, from_version, dry_run=dry_run)
    report["files_changed"] = rs_changed

    # Step 5: Update Cargo.toml
    console.print("  [blue]Updating Cargo.toml...[/blue]")
    cargo_changed = update_cargo_toml(clone_dir, dry_run=dry_run)
    report["files_changed"].extend(cargo_changed)

    # Step 6: Add required files
    console.print("  [blue]Adding required files...[/blue]")
    added = add_required_files(clone_dir, dry_run=dry_run)
    report["files_added"] = added

    # Step 7: Apply fix_code patterns
    if not dry_run:
        fix_count = apply_fix_code_patterns(clone_dir)
        if fix_count > 0:
            console.print(f"  [blue]Applied fix patterns to {fix_count} files[/blue]")

    if dry_run:
        console.print(f"  [cyan]DRY RUN — would change {len(rs_changed)} .rs files, "
                       f"{len(cargo_changed)} Cargo.toml, add {len(added)} files[/cyan]")
        report["status"] = "dry_run"
        return report

    # Step 8: Verify (unless skip_verify)
    if not skip_verify:
        console.print("  [blue]Verifying...[/blue]")
        verify_results = verify_repo(clone_dir)
        report["compile_result"] = verify_results.get("compile_check")
        report["test_result"] = verify_results.get("test_check")

        compile_passed = verify_results.get("compile_check", {}).get("passed", False)

        # Step 9: Auto-fix on failure (up to 2 attempts)
        if not compile_passed:
            for attempt in range(2):
                console.print(f"  [yellow]Compile failed, fix attempt {attempt + 1}...[/yellow]")
                apply_fix_code_patterns(clone_dir)
                verify_results = verify_repo(clone_dir)
                report["compile_result"] = verify_results.get("compile_check")
                compile_passed = verify_results.get("compile_check", {}).get("passed", False)
                if compile_passed:
                    break

        if not compile_passed:
            console.print("  [red]Compile check FAILED after fix attempts[/red]")
            report["status"] = "compile_failed"
        else:
            console.print("  [green]Compile check PASSED[/green]")
            report["status"] = "success"
    else:
        report["status"] = "migrated_unverified"

    # Step 10: Commit + Push
    console.print("  [blue]Committing and pushing...[/blue]")
    if commit_and_push(clone_dir):
        console.print("  [green]Pushed to fork[/green]")
    else:
        console.print("  [yellow]Push failed (may need manual intervention)[/yellow]")
        if report["status"] == "success":
            report["status"] = "migrated_push_failed"

    return report


def print_summary(reports: list[dict]):
    """Print a summary table of all repo results."""
    table = Table(title="Fork & Migration Report")
    table.add_column("Repo", style="cyan", no_wrap=True)
    table.add_column("Original SDK", style="dim")
    table.add_column("Status", style="bold")
    table.add_column("Files Changed")
    table.add_column("Compile")
    table.add_column("Tests")

    for r in reports:
        status_style = {
            "success": "green",
            "dry_run": "cyan",
            "compile_failed": "red",
            "fork_failed": "red",
            "clone_failed": "red",
            "verified": "green",
            "verify_failed": "red",
            "migrated_unverified": "yellow",
            "migrated_push_failed": "yellow",
        }.get(r["status"], "dim")

        compile_str = ""
        if r.get("compile_result"):
            compile_str = "[green]PASS[/green]" if r["compile_result"].get("passed") else "[red]FAIL[/red]"

        test_str = ""
        if r.get("test_result"):
            test_str = "[green]PASS[/green]" if r["test_result"].get("passed") else "[yellow]FAIL[/yellow]"

        table.add_row(
            r["repo"],
            r.get("original_sdk", ""),
            f"[{status_style}]{r['status']}[/{status_style}]",
            str(len(r.get("files_changed", []))),
            compile_str,
            test_str,
        )

    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="Fork & Migrate Stylus repos to SDK 0.10.0")
    parser.add_argument("--all", action="store_true", help="Process all target repos")
    parser.add_argument("--repo", type=str, help="Process specific repo (owner/name)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without modifying")
    parser.add_argument("--skip-verify", action="store_true", help="Skip compile verification")
    parser.add_argument("--verify-only", action="store_true", help="Only re-verify existing forks")
    parser.add_argument("--output", type=str, help="Output JSON report path")
    args = parser.parse_args()

    if not args.all and not args.repo:
        parser.error("Must specify --all or --repo")

    # Select repos to process
    if args.repo:
        # Find matching repo in targets
        matching = [r for r in TARGET_REPOS if r["owner_repo"] == args.repo]
        if not matching:
            # Allow arbitrary repo
            matching = [{
                "owner_repo": args.repo,
                "url": f"https://github.com/{args.repo}",
                "sdk_version": "0.9.0",
                "category": "custom",
            }]
        repos_to_process = matching
    else:
        repos_to_process = TARGET_REPOS

    console.print(f"\n[bold]Fork & Migrate to SDK {TARGET_VERSION}[/bold]")
    console.print(f"  Target org: {FORK_ORG}")
    console.print(f"  Repos: {len(repos_to_process)}")
    console.print(f"  Mode: {'DRY RUN' if args.dry_run else 'VERIFY ONLY' if args.verify_only else 'FULL MIGRATION'}")

    reports = []
    for repo_info in repos_to_process:
        report = process_repo(
            repo_info,
            dry_run=args.dry_run,
            skip_verify=args.skip_verify,
            verify_only=args.verify_only,
        )
        reports.append(report)

    # Print summary
    print_summary(reports)

    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output or f"reports/fork_migration_{timestamp}.json"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2)
    console.print(f"\n[green]Report saved to {output_path}[/green]")

    # Summary stats
    success = sum(1 for r in reports if r["status"] in ("success", "verified", "dry_run"))
    failed = sum(1 for r in reports if "fail" in r["status"])
    console.print(f"\n  Success: {success}/{len(reports)}, Failed: {failed}/{len(reports)}")


if __name__ == "__main__":
    main()

"""
GitHub Repository Scraper for ARBuilder.
Clones repositories and extracts Rust/code files for the RAG pipeline.
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import (
    PROJECT_EXAMPLES,
    get_all_config_repo_urls,
    get_config_repo_info,
)

load_dotenv()

console = Console()
logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 5  # seconds

RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
REPOS_DIR = RAW_DATA_DIR / "repos"

# File extensions to extract for code context
CODE_EXTENSIONS = {
    ".rs",      # Rust (Stylus contracts)
    ".toml",    # Cargo.toml
    ".md",      # Documentation
    ".json",    # Config files
    ".ts",      # TypeScript (SDK)
    ".js",      # JavaScript
    ".sol",     # Solidity (for reference)
}

# Directories to skip
SKIP_DIRS = {
    "node_modules",
    "target",
    ".git",
    "dist",
    "build",
    "__pycache__",
    ".cargo",
    "vendor",
    "third_party",
    "artifacts",
    ".next",
    "coverage",
}

# Lock files and generated files to skip entirely
SKIP_FILE_NAMES = {"package-lock.json", "yarn.lock", "Cargo.lock", "pnpm-lock.yaml"}

# Files with these substrings in their relative path are auto-generated
SKIP_FILE_SUBSTRINGS = ["__factory.ts", "__factory.js"]

# Skip .ts/.js files inside these directory names (keep .rs, .json, etc.)
SKIP_TS_JS_IN_DIRS = {"abi"}

# Skip ALL files in directories whose name starts with these prefixes
SKIP_DIR_PREFIXES = ["abi-"]


def clone_repo(repo_url: str, target_dir: Path, retries: int = MAX_RETRIES, force_reclone: bool = False) -> bool:
    """
    Clone a GitHub repository with retry logic.

    Args:
        repo_url: URL of the GitHub repository.
        target_dir: Target directory for the clone.
        retries: Number of retry attempts.
        force_reclone: If True, delete existing dir and re-clone.

    Returns:
        True if successful, False otherwise.
    """
    if target_dir.exists():
        if force_reclone:
            console.print(f"[yellow]Force re-cloning: {target_dir}[/yellow]")
            shutil.rmtree(target_dir, ignore_errors=True)
        else:
            console.print(f"[yellow]Repository already exists: {target_dir}[/yellow]")
            return True

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    last_error = None

    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(target_dir)],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                console.print(f"[green]Cloned: {repo_url}[/green]")
                return True
            else:
                last_error = result.stderr.strip()

                # Check for retryable errors
                retryable_errors = [
                    "connection",
                    "timeout",
                    "could not resolve",
                    "unable to access",
                    "SSL",
                    "rate limit",
                    "temporary failure",
                ]

                is_retryable = any(err.lower() in last_error.lower() for err in retryable_errors)

                if is_retryable and attempt < retries - 1:
                    delay = RETRY_DELAY_BASE * (2 ** attempt)
                    logger.warning(
                        f"Retryable error cloning {repo_url} (attempt {attempt + 1}/{retries}): {last_error}. "
                        f"Retrying in {delay}s..."
                    )
                    console.print(
                        f"[yellow]Retry {attempt + 1}/{retries} for {repo_url} in {delay}s...[/yellow]"
                    )
                    # Clean up partial clone if exists
                    if target_dir.exists():
                        shutil.rmtree(target_dir, ignore_errors=True)
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Failed to clone {repo_url}: {last_error}")
                    console.print(f"[red]Failed to clone {repo_url}: {last_error}[/red]")
                    return False

        except subprocess.TimeoutExpired:
            last_error = "Operation timed out"
            if attempt < retries - 1:
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(f"Timeout cloning {repo_url} (attempt {attempt + 1}/{retries}). Retrying in {delay}s...")
                console.print(f"[yellow]Timeout, retrying {repo_url} in {delay}s...[/yellow]")
                # Clean up partial clone if exists
                if target_dir.exists():
                    shutil.rmtree(target_dir, ignore_errors=True)
                time.sleep(delay)
                continue
            else:
                logger.error(f"Timeout cloning {repo_url} after {retries} attempts")
                console.print(f"[red]Timeout cloning {repo_url} after {retries} attempts[/red]")
                return False

        except Exception as e:
            last_error = str(e)
            error_type = type(e).__name__

            if attempt < retries - 1:
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(
                    f"Error cloning {repo_url} (attempt {attempt + 1}/{retries}): {error_type}: {e}. "
                    f"Retrying in {delay}s..."
                )
                console.print(f"[yellow]Error, retrying {repo_url} in {delay}s...[/yellow]")
                # Clean up partial clone if exists
                if target_dir.exists():
                    shutil.rmtree(target_dir, ignore_errors=True)
                time.sleep(delay)
                continue
            else:
                logger.error(f"Error cloning {repo_url}: {error_type}: {e}")
                console.print(f"[red]Error cloning {repo_url}: {error_type}: {e}[/red]")
                return False

    logger.error(f"Failed to clone {repo_url} after {retries} attempts. Last error: {last_error}")
    return False


def extract_code_files(repo_dir: Path) -> list[dict]:
    """
    Extract relevant code files from a cloned repository.

    Args:
        repo_dir: Path to the cloned repository.

    Returns:
        List of dictionaries containing file information.
    """
    files = []
    skipped_count = 0
    error_count = 0

    try:
        all_files = list(repo_dir.rglob("*"))
    except Exception as e:
        logger.error(f"Error listing files in {repo_dir}: {e}")
        console.print(f"[red]Error listing files in {repo_dir}: {e}[/red]")
        return files

    for path in all_files:
        try:
            if not path.is_file():
                continue

            # Skip unwanted directories
            if any(skip in path.parts for skip in SKIP_DIRS):
                skipped_count += 1
                continue

            # Only include relevant extensions
            if path.suffix not in CODE_EXTENSIONS:
                continue

            # Skip lock files and known generated files
            if path.name in SKIP_FILE_NAMES:
                skipped_count += 1
                continue

            rel_path = str(path.relative_to(repo_dir))

            # Skip __factory.ts / __factory.js generated files
            if any(sub in rel_path for sub in SKIP_FILE_SUBSTRINGS):
                skipped_count += 1
                continue

            # For .ts/.js files: skip if inside abi/ dirs or abi-* dirs
            if path.suffix in {".ts", ".js"}:
                parts = path.relative_to(repo_dir).parts
                if any(part in SKIP_TS_JS_IN_DIRS for part in parts):
                    skipped_count += 1
                    continue
                if any(
                    part.startswith(prefix)
                    for part in parts
                    for prefix in SKIP_DIR_PREFIXES
                ):
                    skipped_count += 1
                    continue

            try:
                content = path.read_text(encoding="utf-8", errors="ignore")

                # Skip very large files (>100KB)
                if len(content) > 100_000:
                    logger.debug(f"Skipping large file: {path} ({len(content)} bytes)")
                    skipped_count += 1
                    continue

                # Skip empty files
                if not content.strip():
                    logger.debug(f"Skipping empty file: {path}")
                    skipped_count += 1
                    continue

                files.append({
                    "path": str(path.relative_to(repo_dir)),
                    "extension": path.suffix,
                    "content": content,
                    "lines": len(content.splitlines()),
                })
            except UnicodeDecodeError as e:
                logger.debug(f"Unicode error reading {path}: {e}")
                skipped_count += 1
            except PermissionError as e:
                logger.warning(f"Permission denied reading {path}: {e}")
                error_count += 1
            except Exception as e:
                logger.warning(f"Could not read {path}: {type(e).__name__}: {e}")
                error_count += 1

        except Exception as e:
            logger.warning(f"Error processing path {path}: {type(e).__name__}: {e}")
            error_count += 1

    if error_count > 0:
        console.print(f"[yellow]Encountered {error_count} errors while extracting files from {repo_dir}[/yellow]")

    logger.info(f"Extracted {len(files)} files from {repo_dir} (skipped: {skipped_count}, errors: {error_count})")
    return files


def get_repo_name(url: str) -> str:
    """Extract repository name from GitHub URL."""
    # https://github.com/owner/repo -> owner_repo
    parts = url.rstrip("/").split("/")
    if len(parts) >= 2:
        return f"{parts[-2]}_{parts[-1]}"
    return parts[-1]


def audit_repos() -> dict:
    """
    Compare repos on disk vs config. Reports orphans and missing repos.

    Returns:
        Dict with 'orphans' (on disk but not in config) and 'missing' (in config but not on disk).
    """
    config_urls = get_all_config_repo_urls()
    config_repo_names = {get_repo_name(url) for url in config_urls}

    # Repos on disk
    on_disk = set()
    if REPOS_DIR.exists():
        on_disk = {d.name for d in REPOS_DIR.iterdir() if d.is_dir()}

    orphans = on_disk - config_repo_names
    missing = config_repo_names - on_disk

    console.print(f"\n[bold]Audit Report[/bold]")
    console.print(f"  Config repos: {len(config_repo_names)}")
    console.print(f"  On disk: {len(on_disk)}")

    if orphans:
        console.print(f"\n[yellow]Orphan repos (on disk but NOT in config): {len(orphans)}[/yellow]")
        for name in sorted(orphans):
            console.print(f"  - {name}")
    else:
        console.print(f"\n[green]No orphan repos[/green]")

    if missing:
        console.print(f"\n[red]Missing repos (in config but NOT on disk): {len(missing)}[/red]")
        for name in sorted(missing):
            console.print(f"  - {name}")
    else:
        console.print(f"\n[green]All configured repos are on disk[/green]")

    return {"orphans": sorted(orphans), "missing": sorted(missing)}


def prune_orphan_repos(dry_run: bool = True) -> list[str]:
    """
    Delete orphan repo directories not in config.

    Args:
        dry_run: If True, only report what would be deleted.

    Returns:
        List of deleted (or would-be-deleted) directory names.
    """
    audit = audit_repos()
    orphans = audit["orphans"]

    if not orphans:
        console.print("[green]Nothing to prune.[/green]")
        return []

    pruned = []
    for name in orphans:
        repo_path = REPOS_DIR / name
        if dry_run:
            console.print(f"  [yellow]Would delete: {repo_path}[/yellow]")
        else:
            console.print(f"  [red]Deleting: {repo_path}[/red]")
            shutil.rmtree(repo_path, ignore_errors=True)
        pruned.append(name)

    if dry_run:
        console.print(f"\n[yellow]Dry run: {len(pruned)} repos would be deleted. Use --prune (without --dry-run) to delete.[/yellow]")
    else:
        console.print(f"\n[red]Pruned {len(pruned)} orphan repos.[/red]")

    return pruned


async def scrape_all_repos(
    categories: Optional[list[str]] = None,
    force_reclone: bool = False,
) -> None:
    """
    Clone and extract code from all configured GitHub repositories.
    Reads from PROJECT_EXAMPLES config and embeds sdk_version into output.

    Args:
        categories: List of categories to process (stylus, arbitrum_sdk, orbit_sdk).
                   If None, process all.
        force_reclone: If True, re-clone repos even if they exist.
    """
    REPOS_DIR.mkdir(parents=True, exist_ok=True)

    # Collect all GitHub repo entries from PROJECT_EXAMPLES
    all_repos = []
    repo_info_map = get_config_repo_info()

    for category, subcategories in PROJECT_EXAMPLES.items():
        if categories and category not in categories:
            continue

        for subcategory, entries in subcategories.items():
            for entry in entries:
                url = entry["url"]
                if "github.com" in url:
                    all_repos.append({
                        "url": url,
                        "category": category,
                        "subcategory": subcategory,
                        "sdk_version": entry.get("sdk_version", ""),
                        "verified": entry.get("verified", ""),
                    })

    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing repositories...", total=len(all_repos))

        for repo_info in all_repos:
            url = repo_info["url"]
            repo_name = get_repo_name(url)
            target_dir = REPOS_DIR / repo_name

            progress.update(task, description=f"Processing {repo_name}...")

            # Clone repository
            if clone_repo(url, target_dir, force_reclone=force_reclone):
                # Extract code files
                files = extract_code_files(target_dir)

                results.append({
                    "repo_url": url,
                    "repo_name": repo_name,
                    "category": repo_info["category"],
                    "subcategory": repo_info["subcategory"],
                    "sdk_version": repo_info["sdk_version"],
                    "verified": repo_info["verified"],
                    "files": files,
                    "file_count": len(files),
                    "scraped_at": datetime.utcnow().isoformat(),
                })

                console.print(f"[green]Extracted {len(files)} files from {repo_name}[/green]")

            progress.advance(task)

    # Save results
    output_file = RAW_DATA_DIR / f"github_repos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    total_files = sum(r["file_count"] for r in results)
    console.print(f"\n[green]Processed {len(results)} repositories with {total_files} total files[/green]")
    console.print(f"[green]Saved to {output_file}[/green]")


def main():
    """Entry point for GitHub scraper."""
    import argparse

    parser = argparse.ArgumentParser(description="ARBuilder GitHub Repository Scraper")
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=["stylus", "arbitrum_sdk", "orbit_sdk"],
        help="Categories to scrape (default: all)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing repos before cloning",
    )
    parser.add_argument(
        "--force-reclone",
        action="store_true",
        help="Force re-clone repos even if they exist on disk",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Compare repos on disk vs config, report orphans and missing",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Delete orphan repo directories not in config",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --prune: only report what would be deleted",
    )

    args = parser.parse_args()

    if args.audit:
        audit_repos()
        return

    if args.prune:
        prune_orphan_repos(dry_run=args.dry_run)
        return

    if args.clean and REPOS_DIR.exists():
        console.print(f"[yellow]Removing existing repos directory: {REPOS_DIR}[/yellow]")
        shutil.rmtree(REPOS_DIR)

    asyncio.run(scrape_all_repos(categories=args.categories, force_reclone=args.force_reclone))


if __name__ == "__main__":
    main()

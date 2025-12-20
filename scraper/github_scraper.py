"""
GitHub Repository Scraper for ARBuilder.
Clones repositories and extracts Rust/code files for the RAG pipeline.
"""

import asyncio
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import STYLUS_SOURCES, ARBITRUM_SDK_SOURCES, ORBIT_SDK_SOURCES

load_dotenv()

console = Console()

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
}


def clone_repo(repo_url: str, target_dir: Path) -> bool:
    """Clone a GitHub repository."""
    try:
        if target_dir.exists():
            console.print(f"[yellow]Repository already exists: {target_dir}[/yellow]")
            return True

        target_dir.parent.mkdir(parents=True, exist_ok=True)

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
            console.print(f"[red]Failed to clone {repo_url}: {result.stderr}[/red]")
            return False

    except subprocess.TimeoutExpired:
        console.print(f"[red]Timeout cloning {repo_url}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Error cloning {repo_url}: {e}[/red]")
        return False


def extract_code_files(repo_dir: Path) -> list[dict]:
    """Extract relevant code files from a cloned repository."""
    files = []

    for path in repo_dir.rglob("*"):
        if path.is_file():
            # Skip unwanted directories
            if any(skip in path.parts for skip in SKIP_DIRS):
                continue

            # Only include relevant extensions
            if path.suffix not in CODE_EXTENSIONS:
                continue

            try:
                content = path.read_text(encoding="utf-8", errors="ignore")

                # Skip very large files (>100KB)
                if len(content) > 100_000:
                    continue

                files.append({
                    "path": str(path.relative_to(repo_dir)),
                    "extension": path.suffix,
                    "content": content,
                    "lines": len(content.splitlines()),
                })
            except Exception as e:
                console.print(f"[yellow]Could not read {path}: {e}[/yellow]")

    return files


def get_repo_name(url: str) -> str:
    """Extract repository name from GitHub URL."""
    # https://github.com/owner/repo -> owner_repo
    parts = url.rstrip("/").split("/")
    if len(parts) >= 2:
        return f"{parts[-2]}_{parts[-1]}"
    return parts[-1]


async def scrape_all_repos(
    categories: Optional[list[str]] = None,
) -> None:
    """
    Clone and extract code from all configured GitHub repositories.

    Args:
        categories: List of categories to process (stylus, arbitrum_sdk, orbit_sdk).
                   If None, process all.
    """
    REPOS_DIR.mkdir(parents=True, exist_ok=True)

    # Collect all GitHub URLs
    all_repos = []

    sources = {
        "stylus": STYLUS_SOURCES,
        "arbitrum_sdk": ARBITRUM_SDK_SOURCES,
        "orbit_sdk": ORBIT_SDK_SOURCES,
    }

    for category, source_dict in sources.items():
        if categories and category not in categories:
            continue

        for subcategory, urls in source_dict.items():
            for url in urls:
                if "github.com" in url:
                    all_repos.append({
                        "url": url,
                        "category": category,
                        "subcategory": subcategory,
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
            if clone_repo(url, target_dir):
                # Extract code files
                files = extract_code_files(target_dir)

                results.append({
                    "repo_url": url,
                    "repo_name": repo_name,
                    "category": repo_info["category"],
                    "subcategory": repo_info["subcategory"],
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

    args = parser.parse_args()

    if args.clean and REPOS_DIR.exists():
        console.print(f"[yellow]Removing existing repos directory: {REPOS_DIR}[/yellow]")
        shutil.rmtree(REPOS_DIR)

    asyncio.run(scrape_all_repos(categories=args.categories))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Data audit script for ARBuilder.
Compares repos on disk vs config, reports orphans, missing repos,
SDK version coverage, and category distribution.

Usage:
    python scripts/audit_data.py           # Full audit report
    python scripts/audit_data.py --prune   # Delete orphan repos (dry-run)
    python scripts/audit_data.py --prune --confirm  # Actually delete orphans
    python scripts/audit_data.py --chromadb # Include ChromaDB stats
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

from scraper.config import (
    PROJECT_EXAMPLES,
    DOCS,
    get_all_config_repo_urls,
    get_config_repo_info,
)
from scraper.github_scraper import get_repo_name, REPOS_DIR, RAW_DATA_DIR

console = Console()


def audit_config():
    """Report on what's configured."""
    console.print("\n[bold]== Config Summary ==[/bold]")

    # Docs
    doc_count = sum(
        len(urls) for subcats in DOCS.values() for urls in subcats.values()
    )
    console.print(f"  Documentation URLs: {doc_count}")
    for category, subcats in DOCS.items():
        total = sum(len(urls) for urls in subcats.values())
        console.print(f"    {category}: {total} URLs")

    # Projects
    repo_count = sum(
        len(entries)
        for subcats in PROJECT_EXAMPLES.values()
        for entries in subcats.values()
    )
    console.print(f"  Project repos: {repo_count}")
    for category, subcats in PROJECT_EXAMPLES.items():
        total = sum(len(entries) for entries in subcats.values())
        console.print(f"    {category}: {total} repos")
        for subcat, entries in subcats.items():
            console.print(f"      {subcat}: {len(entries)}")


def audit_disk_vs_config():
    """Compare repos on disk vs config."""
    console.print("\n[bold]== Disk vs Config ==[/bold]")

    config_urls = get_all_config_repo_urls()
    config_repo_names = {get_repo_name(url) for url in config_urls}

    on_disk = set()
    if REPOS_DIR.exists():
        on_disk = {d.name for d in REPOS_DIR.iterdir() if d.is_dir()}

    orphans = on_disk - config_repo_names
    missing = config_repo_names - on_disk
    matched = on_disk & config_repo_names

    console.print(f"  Config repos: {len(config_repo_names)}")
    console.print(f"  On disk: {len(on_disk)}")
    console.print(f"  Matched: {len(matched)}")

    if orphans:
        console.print(f"\n  [yellow]Orphans (on disk, NOT in config): {len(orphans)}[/yellow]")
        for name in sorted(orphans):
            console.print(f"    - {name}")

    if missing:
        console.print(f"\n  [red]Missing (in config, NOT on disk): {len(missing)}[/red]")
        for name in sorted(missing):
            console.print(f"    - {name}")

    if not orphans and not missing:
        console.print(f"\n  [green]Perfect match — no orphans or missing repos[/green]")

    return orphans, missing


def audit_sdk_versions():
    """Report SDK version coverage from config."""
    console.print("\n[bold]== SDK Version Coverage (Config) ==[/bold]")

    version_counts: dict[str, int] = {}
    no_version = 0

    for category, subcats in PROJECT_EXAMPLES.items():
        for subcat, entries in subcats.items():
            for entry in entries:
                v = entry.get("sdk_version", "")
                if v:
                    version_counts[v] = version_counts.get(v, 0) + 1
                else:
                    no_version += 1

    table = Table(title="SDK Versions in Config")
    table.add_column("Version", style="cyan")
    table.add_column("Count", justify="right")

    for version in sorted(version_counts.keys(), reverse=True):
        table.add_row(version, str(version_counts[version]))

    if no_version:
        table.add_row("[dim]unspecified[/dim]", str(no_version))

    console.print(table)


def audit_processed_files():
    """Report on processed data files."""
    console.print("\n[bold]== Processed Data Files ==[/bold]")

    processed_dir = Path("data/processed")
    if not processed_dir.exists():
        console.print("  [red]No processed directory[/red]")
        return

    chunk_files = sorted(processed_dir.glob("processed_chunks_*.json"))
    stat_files = sorted(processed_dir.glob("processing_stats_*.json"))

    console.print(f"  Chunk files: {len(chunk_files)}")
    for f in chunk_files:
        size_mb = f.stat().st_size / (1024 * 1024)
        console.print(f"    {f.name} ({size_mb:.1f} MB)")

    console.print(f"  Stats files: {len(stat_files)}")
    for f in stat_files:
        console.print(f"    {f.name}")

    # Show latest stats if available
    if stat_files:
        latest_stats = stat_files[-1]
        with open(latest_stats) as fh:
            stats = json.load(fh)
        console.print(f"\n  [bold]Latest stats ({latest_stats.name}):[/bold]")
        console.print(f"    Total chunks: {stats.get('total_chunks', '?')}")
        console.print(f"    By source: {stats.get('by_source', {})}")
        console.print(f"    By category: {stats.get('by_category', {})}")
        if stats.get("by_sdk_version"):
            console.print(f"    By SDK version: {stats['by_sdk_version']}")


def audit_chromadb():
    """Report on ChromaDB contents."""
    console.print("\n[bold]== ChromaDB ==[/bold]")
    try:
        import chromadb

        db_path = Path("data/chroma_db")
        if not db_path.exists():
            console.print("  [red]No ChromaDB directory[/red]")
            return

        client = chromadb.PersistentClient(path=str(db_path))
        collections = client.list_collections()

        for col in collections:
            count = col.count()
            console.print(f"  Collection '{col.name}': {count:,} embeddings")

            # Sample metadata to check for orphan repos
            if count > 0:
                sample = col.peek(limit=10)
                repo_names = set()
                if sample.get("metadatas"):
                    for meta in sample["metadatas"]:
                        if meta.get("repo_name"):
                            repo_names.add(meta["repo_name"])
                if repo_names:
                    console.print(f"    Sample repos: {', '.join(sorted(repo_names))}")

    except ImportError:
        console.print("  [yellow]chromadb not installed, skipping[/yellow]")
    except Exception as e:
        console.print(f"  [red]Error reading ChromaDB: {e}[/red]")


def prune_orphans(confirm: bool = False):
    """Delete orphan repo directories."""
    orphans, _ = audit_disk_vs_config()

    if not orphans:
        console.print("\n[green]Nothing to prune.[/green]")
        return

    import shutil

    for name in sorted(orphans):
        repo_path = REPOS_DIR / name
        if confirm:
            console.print(f"  [red]Deleting: {repo_path}[/red]")
            shutil.rmtree(repo_path, ignore_errors=True)
        else:
            console.print(f"  [yellow]Would delete: {repo_path}[/yellow]")

    if not confirm:
        console.print(f"\n[yellow]Dry run. Use --confirm to actually delete {len(orphans)} repos.[/yellow]")
    else:
        console.print(f"\n[red]Pruned {len(orphans)} orphan repos.[/red]")


def main():
    parser = argparse.ArgumentParser(description="ARBuilder Data Audit")
    parser.add_argument("--prune", action="store_true", help="Delete orphan repos (dry-run by default)")
    parser.add_argument("--confirm", action="store_true", help="With --prune: actually delete")
    parser.add_argument("--chromadb", action="store_true", help="Include ChromaDB stats")

    args = parser.parse_args()

    if args.prune:
        prune_orphans(confirm=args.confirm)
        return

    audit_config()
    audit_disk_vs_config()
    audit_sdk_versions()
    audit_processed_files()

    if args.chromadb:
        audit_chromadb()

    console.print("\n[bold green]Audit complete.[/bold green]")


if __name__ == "__main__":
    main()

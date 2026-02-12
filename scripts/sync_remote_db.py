#!/usr/bin/env python3
"""
Sync remote Cloudflare database with local cleaned config.

This script:
1. Fetches current remote sources from /api/public/sources
2. Compares with local config (DOCS + PROJECT_EXAMPLES)
3. Deletes stale sources from remote (KV registry + Vectorize vectors)
4. Re-ingests clean sources via batch ingestion

Usage:
    # Dry run — show what would change
    python scripts/sync_remote_db.py --dry-run

    # Step 1: Delete stale sources from remote
    python scripts/sync_remote_db.py --delete-stale

    # Step 2: Clear all vectors and re-ingest from clean config
    python scripts/sync_remote_db.py --full-reset

    # Step 3: Trigger batch re-ingestion of all clean sources
    python scripts/sync_remote_db.py --reingest

Environment:
    ARBBUILDER_ADMIN_SECRET — the X-Admin-Secret for admin API
    ARBBUILDER_API_URL — base URL (default: https://arbbuilder.whymelabs.com)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx
from rich.console import Console
from rich.table import Table

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.config import DOCS, PROJECT_EXAMPLES, get_all_config_repo_urls

console = Console()

API_URL = os.environ.get("ARBBUILDER_API_URL", "https://arbbuilder.whymelabs.com")
ADMIN_SECRET = os.environ.get("ARBBUILDER_ADMIN_SECRET", "")


def get_headers():
    if not ADMIN_SECRET:
        console.print("[red]ARBBUILDER_ADMIN_SECRET environment variable not set![/red]")
        sys.exit(1)
    return {
        "X-Admin-Secret": ADMIN_SECRET,
        "Content-Type": "application/json",
    }


def fetch_remote_sources() -> list[dict]:
    """Fetch all sources from the remote API."""
    resp = httpx.get(f"{API_URL}/api/public/sources", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("sources", [])


def get_local_urls() -> set[str]:
    """Get all URLs from local config (docs + projects)."""
    urls = set()

    # Documentation URLs
    for category, subcats in DOCS.items():
        for subcat, url_list in subcats.items():
            for url in url_list:
                urls.add(url)

    # Project repo URLs
    for url in get_all_config_repo_urls():
        urls.add(url)

    return urls


def compare_sources(remote_sources: list[dict], local_urls: set[str]):
    """Compare remote vs local and return stale + missing."""
    remote_urls = {s["url"] for s in remote_sources}
    remote_by_url = {s["url"]: s for s in remote_sources}

    stale = remote_urls - local_urls  # On remote but not local
    missing = local_urls - remote_urls  # On local but not remote

    return stale, missing, remote_by_url


def dry_run():
    """Show what would change without making any modifications."""
    console.print("\n[bold]Fetching remote sources...[/bold]")
    remote_sources = fetch_remote_sources()
    local_urls = get_local_urls()

    stale, missing, remote_by_url = compare_sources(remote_sources, local_urls)

    console.print(f"\nRemote sources: {len(remote_sources)}")
    console.print(f"Local sources: {len(local_urls)}")

    if stale:
        table = Table(title=f"Stale Sources to DELETE ({len(stale)})")
        table.add_column("URL", style="red")
        table.add_column("Category")
        table.add_column("Chunks", justify="right")
        total_stale_chunks = 0
        for url in sorted(stale):
            info = remote_by_url.get(url, {})
            chunks = info.get("chunkCount", 0)
            total_stale_chunks += chunks
            table.add_row(
                url.split("github.com/")[-1] if "github.com" in url else url,
                info.get("category", "?"),
                str(chunks),
            )
        table.add_row("[bold]TOTAL[/bold]", "", f"[bold]{total_stale_chunks}[/bold]")
        console.print(table)
    else:
        console.print("\n[green]No stale sources to remove.[/green]")

    if missing:
        table = Table(title=f"Missing Sources to ADD ({len(missing)})")
        table.add_column("URL", style="green")
        for url in sorted(missing):
            table.add_row(
                url.split("github.com/")[-1] if "github.com" in url else url,
            )
        console.print(table)
    else:
        console.print("\n[green]All local sources are on remote.[/green]")


def delete_stale_sources():
    """Delete stale sources from remote KV registry."""
    console.print("\n[bold]Fetching remote sources...[/bold]")
    remote_sources = fetch_remote_sources()
    local_urls = get_local_urls()
    stale, _, remote_by_url = compare_sources(remote_sources, local_urls)

    if not stale:
        console.print("[green]No stale sources to delete.[/green]")
        return

    console.print(f"\n[yellow]Deleting {len(stale)} stale sources from remote registry...[/yellow]")
    headers = get_headers()

    deleted = 0
    for url in sorted(stale):
        info = remote_by_url.get(url, {})
        console.print(f"  Deleting: {url} ({info.get('chunkCount', '?')} chunks)")
        try:
            resp = httpx.request(
                "DELETE",
                f"{API_URL}/api/admin/sources",
                headers=headers,
                json={"url": url},
                timeout=30,
            )
            if resp.status_code == 200:
                deleted += 1
                console.print(f"    [green]OK[/green]")
            else:
                console.print(f"    [red]Failed: {resp.status_code} {resp.text}[/red]")
        except Exception as e:
            console.print(f"    [red]Error: {e}[/red]")
        time.sleep(0.2)  # Rate limit

    console.print(f"\n[green]Deleted {deleted}/{len(stale)} stale sources from registry.[/green]")
    console.print("[yellow]Note: Vectors still exist in Vectorize. Use --full-reset to clear vectors too.[/yellow]")


def full_reset():
    """Clear all vectors from Vectorize and delete all sources from registry."""
    headers = get_headers()

    console.print("\n[bold red]FULL RESET: Clearing all vectors from Vectorize...[/bold red]")
    try:
        resp = httpx.post(
            f"{API_URL}/api/admin/migrate",
            headers=headers,
            json={"action": "clear"},
            timeout=300,
        )
        data = resp.json()
        console.print(f"  Deleted {data.get('deleted', '?')} vectors in {data.get('iterations', '?')} iterations")
    except Exception as e:
        console.print(f"  [red]Error clearing vectors: {e}[/red]")

    # Now delete all stale sources from registry
    delete_stale_sources()

    console.print("\n[green]Full reset complete. Use --reingest to re-populate.[/green]")


def reingest():
    """Trigger batch re-ingestion of all clean sources."""
    headers = get_headers()
    local_urls = get_local_urls()

    # Build source list for batch ingestion
    sources = []

    # Docs
    for category, subcats in DOCS.items():
        for subcat, url_list in subcats.items():
            for url in url_list:
                sources.append({
                    "url": url,
                    "category": category,
                    "subcategory": subcat,
                })

    # Projects
    for category, subcats in PROJECT_EXAMPLES.items():
        for subcat, entries in subcats.items():
            for entry in entries:
                sources.append({
                    "url": entry["url"],
                    "category": category,
                    "subcategory": subcat,
                })

    console.print(f"\n[bold]Triggering batch re-ingestion of {len(sources)} sources...[/bold]")

    try:
        resp = httpx.post(
            f"{API_URL}/api/admin/ingest/batch",
            headers=headers,
            json={"sources": sources},
            timeout=60,
        )
        data = resp.json()
        console.print(f"  Response: {json.dumps(data, indent=2)}")
    except Exception as e:
        console.print(f"  [red]Error triggering batch ingestion: {e}[/red]")
        return

    console.print("\n[green]Batch ingestion triggered. Monitor progress at the admin dashboard.[/green]")


def main():
    parser = argparse.ArgumentParser(description="Sync remote Cloudflare DB with local config")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Show what would change")
    group.add_argument("--delete-stale", action="store_true", help="Delete stale sources from remote registry")
    group.add_argument("--full-reset", action="store_true", help="Clear all vectors + delete stale sources")
    group.add_argument("--reingest", action="store_true", help="Trigger batch re-ingestion of clean sources")

    args = parser.parse_args()

    if args.dry_run:
        dry_run()
    elif args.delete_stale:
        delete_stale_sources()
    elif args.full_reset:
        full_reset()
    elif args.reingest:
        reingest()


if __name__ == "__main__":
    main()

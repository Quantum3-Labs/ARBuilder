#!/usr/bin/env python3
"""
Sync remote Cloudflare database with local cleaned config.

This script:
1. Fetches current remote sources from /api/public/sources
2. Compares with local config (DOCS + PROJECT_EXAMPLES)
3. Deletes stale sources from remote (KV registry + Vectorize vectors)
4. Pushes local processed chunks directly via /api/admin/migrate

Usage:
    # Dry run — show what would change
    python scripts/sync_remote_db.py --dry-run

    # Step 1: Delete stale sources from remote
    python scripts/sync_remote_db.py --delete-stale

    # Step 2: Clear all vectors and re-ingest from clean config
    python scripts/sync_remote_db.py --full-reset

    # Step 3: Push ALL local chunks to remote (full re-upload)
    python scripts/sync_remote_db.py --reingest

    # Step 3 (alt): Push only chunks for sources missing from remote
    python scripts/sync_remote_db.py --push-missing

Environment:
    ARBBUILDER_ADMIN_SECRET — the X-Admin-Secret for admin API
    ARBBUILDER_API_URL — base URL (default: https://arbuilder.app)
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

from scraper.config import DOCS, get_all_config_repo_urls, get_config_repo_info

console = Console()

API_URL = os.environ.get("ARBBUILDER_API_URL", "https://arbuilder.app")
ADMIN_SECRET = os.environ.get("ARBBUILDER_ADMIN_SECRET", "")

# Remote /api/admin/migrate accepts chunks in batches.
# Keep batches small to avoid Worker timeout (30s) and embedding rate limits.
UPLOAD_BATCH_SIZE = 20


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


def load_local_chunks() -> list[dict]:
    """Load the latest processed chunks from disk."""
    processed_dir = Path("data/processed")
    chunk_files = sorted(processed_dir.glob("processed_chunks_*.json"), reverse=True)

    if not chunk_files:
        console.print("[red]No processed chunk files found in data/processed/[/red]")
        console.print("Run: python -m src.preprocessing.processor")
        sys.exit(1)

    latest = chunk_files[0]
    console.print(f"Loading chunks from: {latest}")

    with open(latest) as f:
        chunks = json.load(f)

    console.print(f"Loaded {len(chunks)} chunks")
    return chunks


def _get_chunk_source_url(chunk: dict) -> str:
    """Extract the source URL from a chunk.

    Chunks have flat structure:
    - Project/GitHub chunks: repo_url = "https://github.com/ARBuilder-Forks/..."
    - Documentation chunks: url = "https://docs.arbitrum.io/..."
    """
    return chunk.get("repo_url", "") or chunk.get("url", "")


def _chunk_to_migrate_format(chunk: dict) -> dict:
    """Convert a local processed chunk to the /api/admin/migrate format."""
    return {
        "id": chunk.get("id", ""),
        "content": chunk.get("content", ""),
        "chunk_index": chunk.get("chunk_index", 0),
        "source": chunk.get("source", ""),
        "url": chunk.get("repo_url", "") or chunk.get("url", ""),
        "title": chunk.get("file_path", "") or chunk.get("title", ""),
        "category": chunk.get("category", ""),
    }


def upload_chunks(chunks: list[dict], label: str = ""):
    """Upload chunks to remote via /api/admin/migrate in batches."""
    headers = get_headers()
    total = len(chunks)
    num_batches = (total + UPLOAD_BATCH_SIZE - 1) // UPLOAD_BATCH_SIZE

    if total == 0:
        print("No chunks to upload.")
        return 0

    succeeded = 0
    failed_batches = 0

    for i in range(0, total, UPLOAD_BATCH_SIZE):
        batch_num = i // UPLOAD_BATCH_SIZE + 1
        batch = chunks[i : i + UPLOAD_BATCH_SIZE]
        migrate_batch = [_chunk_to_migrate_format(c) for c in batch]

        retries = 3
        for attempt in range(retries):
            try:
                resp = httpx.post(
                    f"{API_URL}/api/admin/migrate",
                    headers=headers,
                    json={"chunks": migrate_batch, "action": "upsert"},
                    timeout=300,
                )
                data = resp.json()

                if resp.status_code == 200 and data.get("status") == "ok":
                    batch_ok = data.get("processed", len(batch))
                    succeeded += batch_ok
                    if batch_num % 50 == 0 or batch_num == num_batches:
                        print(
                            f"  [{batch_num}/{num_batches}] {succeeded}/{total} chunks uploaded",
                            flush=True,
                        )
                    break
                else:
                    if attempt < retries - 1:
                        time.sleep(2**attempt)
                        continue
                    print(f"  Batch {batch_num} failed: {data}", flush=True)
                    failed_batches += 1
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(2**attempt)
                    continue
                print(f"  Batch {batch_num} error: {e}", flush=True)
                failed_batches += 1

        # Small delay between batches to avoid rate limiting
        time.sleep(0.3)

    print(f"\nUploaded {succeeded}/{total} chunks ({failed_batches} batches failed)", flush=True)
    return succeeded


def register_sources(urls: set[str]):
    """Register sources in the remote KV registry via POST /api/admin/sources."""
    headers = get_headers()
    config_info = get_config_repo_info()

    registered = 0
    for url in sorted(urls):
        info = config_info.get(url, {})
        payload = {
            "url": url,
            "category": info.get("category", "stylus"),
            "subcategory": info.get("subcategory", ""),
            "sourceType": "github" if "github.com" in url else "documentation",
            "stylusVersion": info.get("sdk_version", ""),
            "status": "active",
        }
        try:
            resp = httpx.post(
                f"{API_URL}/api/admin/sources",
                headers=headers,
                json=payload,
                timeout=30,
            )
            if resp.status_code == 200:
                registered += 1
                short = url.split("github.com/")[-1] if "github.com" in url else url[:60]
                console.print(f"  [green]Registered:[/green] {short}")
            else:
                console.print(f"  [red]Failed ({resp.status_code}):[/red] {url}")
        except Exception as e:
            console.print(f"  [red]Error:[/red] {url} — {e}")
        time.sleep(0.2)

    console.print(f"\n[green]Registered {registered}/{len(urls)} sources[/green]")


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
                console.print("    [green]OK[/green]")
            else:
                console.print(f"    [red]Failed: {resp.status_code} {resp.text}[/red]")
        except Exception as e:
            console.print(f"    [red]Error: {e}[/red]")
        time.sleep(0.2)  # Rate limit

    console.print(f"\n[green]Deleted {deleted}/{len(stale)} stale sources from registry.[/green]")
    console.print(
        "[yellow]Note: Vectors still exist in Vectorize."
        " Use --full-reset to clear vectors"
        " too.[/yellow]"
    )


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
        console.print(
            f"  Deleted {data.get('deleted', '?')} vectors"
            f" in {data.get('iterations', '?')} iterations"
        )
    except Exception as e:
        console.print(f"  [red]Error clearing vectors: {e}[/red]")

    # Now delete all stale sources from registry
    delete_stale_sources()

    console.print("\n[green]Full reset complete. Use --reingest to re-populate.[/green]")


def reingest():
    """Push ALL local processed chunks to remote via /api/admin/migrate."""
    chunks = load_local_chunks()

    # Register all local sources first
    local_urls = get_local_urls()
    console.print(f"\n[bold]Registering {len(local_urls)} sources...[/bold]")
    register_sources(local_urls)

    # Upload all chunks
    console.print(f"\n[bold]Uploading {len(chunks)} chunks to remote...[/bold]")
    upload_chunks(chunks, label="all chunks")


def push_missing():
    """Push only chunks for sources that are missing from remote."""
    console.print("\n[bold]Fetching remote sources...[/bold]")
    remote_sources = fetch_remote_sources()
    local_urls = get_local_urls()
    _, missing, _ = compare_sources(remote_sources, local_urls)

    if not missing:
        console.print("[green]All local sources already exist on remote. Nothing to push.[/green]")
        return

    console.print(f"\n[bold]Found {len(missing)} missing sources to push[/bold]")
    for url in sorted(missing):
        short = url.split("github.com/")[-1] if "github.com" in url else url[:60]
        console.print(f"  {short}")

    # Register missing sources
    console.print(f"\n[bold]Registering {len(missing)} sources...[/bold]")
    register_sources(missing)

    # Load chunks and filter for missing sources
    chunks = load_local_chunks()

    # Filter chunks whose repo_url or url matches a missing source
    filtered = []
    for chunk in chunks:
        chunk_url = _get_chunk_source_url(chunk)
        if chunk_url in missing:
            filtered.append(chunk)

    console.print(
        f"\n[bold]Uploading {len(filtered)} chunks for {len(missing)} missing sources...[/bold]"
    )
    upload_chunks(filtered, label="missing source chunks")


def main():
    parser = argparse.ArgumentParser(description="Sync remote Cloudflare DB with local config")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Show what would change")
    group.add_argument(
        "--delete-stale", action="store_true", help="Delete stale sources from remote registry"
    )
    group.add_argument(
        "--full-reset", action="store_true", help="Clear all vectors + delete stale sources"
    )
    group.add_argument("--reingest", action="store_true", help="Push ALL local chunks to remote")
    group.add_argument(
        "--push-missing", action="store_true", help="Push only chunks for missing sources"
    )

    args = parser.parse_args()

    if args.dry_run:
        dry_run()
    elif args.delete_stale:
        delete_stale_sources()
    elif args.full_reset:
        full_reset()
    elif args.reingest:
        reingest()
    elif args.push_missing:
        push_missing()


if __name__ == "__main__":
    main()

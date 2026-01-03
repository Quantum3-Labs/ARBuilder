"""
RAG CLI - Command-line interface for managing RAG sources.

Usage:
    python -m src.rag.cli add <url> --category <cat>
    python -m src.rag.cli update <url>
    python -m src.rag.cli remove <url>
    python -m src.rag.cli sync
    python -m src.rag.cli list
    python -m src.rag.cli status
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .registry import SourceRegistry, Source, SourceType, SourceStatus

console = Console()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class VectorCleanup:
    """Utilities for cleaning up vectors from ChromaDB."""

    def __init__(self):
        self.chroma_available = False

        # Check ChromaDB availability
        try:
            from src.embeddings.vectordb import VectorDB

            self.VectorDB = VectorDB
            self.chroma_available = True
        except ImportError:
            pass

    def delete_from_chroma(self, chunk_ids: list[str]) -> int:
        """Delete chunks from ChromaDB by IDs."""
        if not self.chroma_available:
            console.print("[yellow]ChromaDB not available[/yellow]")
            return 0

        if not chunk_ids:
            return 0

        try:
            db = self.VectorDB()
            deleted = db.delete_by_ids(chunk_ids)
            console.print(f"[green]Deleted {deleted} chunks from ChromaDB[/green]")
            return deleted
        except Exception as e:
            console.print(f"[red]ChromaDB deletion error: {e}[/red]")
            return 0

    def delete_chunks(self, chunk_ids: list[str]) -> int:
        """Delete chunks from ChromaDB."""
        if not chunk_ids:
            return 0

        console.print(f"\n[bold]Cleaning up {len(chunk_ids)} chunks...[/bold]")
        return self.delete_from_chroma(chunk_ids)


class SourceProcessor:
    """Process individual sources (scrape, chunk, index)."""

    def __init__(self, registry: SourceRegistry):
        self.registry = registry
        self.cleanup = VectorCleanup()

    async def scrape_documentation(self, source: Source) -> tuple[str, dict]:
        """Scrape a documentation URL."""
        try:
            from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

            config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                process_iframes=False,
                remove_overlay_elements=True,
            )

            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=source.url, config=config)

                if not result.success:
                    raise Exception(f"Crawl failed: {result.error_message}")

                return result.markdown, {
                    "title": result.metadata.get("title", ""),
                    "description": result.metadata.get("description", ""),
                }
        except Exception as e:
            raise Exception(f"Scraping error: {e}")

    async def scrape_github(self, source: Source) -> tuple[list[dict], dict]:
        """Scrape a GitHub repository."""
        import tempfile
        import subprocess
        import shutil

        repo_url = source.url
        if not repo_url.endswith(".git"):
            repo_url = f"{repo_url}.git"

        with tempfile.TemporaryDirectory() as tmpdir:
            # Clone repository
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, tmpdir],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise Exception(f"Git clone failed: {result.stderr}")

            # Get commit hash
            commit_result = subprocess.run(
                ["git", "-C", tmpdir, "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
            )
            commit_hash = commit_result.stdout.strip()

            # Extract files
            files = []
            extensions = {".rs", ".toml", ".md", ".json", ".ts", ".js", ".sol"}
            skip_dirs = {"node_modules", "target", ".git", "dist", "build"}

            for root, dirs, filenames in os.walk(tmpdir):
                # Skip directories
                dirs[:] = [d for d in dirs if d not in skip_dirs]

                for filename in filenames:
                    ext = Path(filename).suffix
                    if ext not in extensions:
                        continue

                    filepath = Path(root) / filename
                    rel_path = filepath.relative_to(tmpdir)

                    # Skip large files
                    if filepath.stat().st_size > 100 * 1024:
                        continue

                    try:
                        content = filepath.read_text(encoding="utf-8")
                        if content.strip():
                            files.append(
                                {
                                    "path": str(rel_path),
                                    "extension": ext,
                                    "content": content,
                                    "lines": len(content.splitlines()),
                                }
                            )
                    except Exception:
                        pass

            return files, {"commit_hash": commit_hash}

    def process_and_chunk(
        self, source: Source, content: str | list[dict], metadata: dict
    ) -> list[dict]:
        """Process content and generate chunks."""
        from src.preprocessing.chunker import DocumentChunker, CodeChunker
        import hashlib

        chunks = []

        if source.source_type == SourceType.DOCUMENTATION:
            # Clean and chunk documentation
            from src.preprocessing.cleaner import TextCleaner

            cleaner = TextCleaner()
            cleaned = cleaner.clean(content)

            chunker = DocumentChunker(max_tokens=512, overlap_tokens=50)
            doc_chunks = chunker.chunk(cleaned)

            for i, chunk in enumerate(doc_chunks):
                chunk_dict = chunk.to_dict()
                chunk_dict.update(
                    {
                        "source": "documentation",
                        "url": source.url,
                        "title": metadata.get("title", ""),
                        "category": source.category,
                        "subcategory": source.subcategory,
                    }
                )

                # Generate deterministic ID
                hash_input = f"{source.url}{chunk_dict['content'][:500]}"
                content_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
                chunk_dict["id"] = f"chunk_{content_hash}"

                chunks.append(chunk_dict)

        elif source.source_type == SourceType.GITHUB:
            # Process each file
            repo_name = source.url.rstrip("/").split("/")[-1]

            for file_data in content:
                ext = file_data["extension"]
                file_content = file_data["content"]

                # Choose chunker based on file type
                if ext == ".md":
                    chunker = DocumentChunker(max_tokens=512, overlap_tokens=50)
                else:
                    chunker = CodeChunker(max_tokens=1024, overlap_lines=5)

                file_chunks = chunker.chunk(file_content)

                for chunk in file_chunks:
                    chunk_dict = chunk.to_dict()
                    chunk_dict.update(
                        {
                            "source": "github",
                            "repo_name": repo_name,
                            "repo_url": source.url,
                            "file_path": file_data["path"],
                            "category": source.category,
                            "subcategory": source.subcategory,
                        }
                    )

                    # Generate deterministic ID
                    hash_input = f"{source.url}/{file_data['path']}{chunk_dict['content'][:500]}"
                    content_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
                    chunk_dict["id"] = f"chunk_{content_hash}"

                    chunks.append(chunk_dict)

        return chunks

    async def process_source(self, source: Source) -> list[str]:
        """
        Process a single source: scrape, chunk, and index to ChromaDB.

        Returns list of chunk IDs created.
        """
        console.print(f"\n[bold]Processing: {source.url}[/bold]")

        try:
            # Scrape
            with console.status("Scraping..."):
                if source.source_type == SourceType.GITHUB:
                    content, metadata = await self.scrape_github(source)
                else:
                    content, metadata = await self.scrape_documentation(source)

            console.print(f"  [green]Scraped successfully[/green]")

            # Chunk
            with console.status("Chunking..."):
                chunks = self.process_and_chunk(source, content, metadata)

            console.print(f"  [green]Generated {len(chunks)} chunks[/green]")

            chunk_ids = [c["id"] for c in chunks]

            # Index to ChromaDB
            if chunks:
                with console.status("Indexing to ChromaDB..."):
                    from src.embeddings.vectordb import VectorDB

                    db = VectorDB()
                    db.ingest_chunks(chunks)
                console.print(f"  [green]Indexed to ChromaDB[/green]")

            # Update registry
            self.registry.update_source_state(
                source.url,
                status=SourceStatus.ACTIVE,
                last_scraped=datetime.now().isoformat(),
                last_processed=datetime.now().isoformat(),
                content_hash=metadata.get("commit_hash"),
                commit_hash=metadata.get("commit_hash"),
                chunk_ids=chunk_ids,
            )

            return chunk_ids

        except Exception as e:
            console.print(f"  [red]Error: {e}[/red]")
            self.registry.update_source_state(
                source.url,
                status=SourceStatus.ERROR,
                last_error=str(e),
            )
            return []


# CLI Commands


def cmd_add(args):
    """Add a new source."""
    registry = SourceRegistry()

    # Detect source type
    source_type = None
    if args.type:
        source_type = SourceType(args.type)

    source = registry.add_source(
        url=args.url,
        category=args.category,
        subcategory=args.subcategory or "",
        source_type=source_type,
    )

    console.print(f"[green]Added source: {source.url}[/green]")
    console.print(f"  ID: {source.id}")
    console.print(f"  Type: {source.source_type.value}")
    console.print(f"  Category: {source.category}")
    console.print(f"  Status: {source.status.value}")

    # Optionally process immediately
    if args.process:
        processor = SourceProcessor(registry)
        asyncio.run(processor.process_source(source))


def cmd_update(args):
    """Update (re-process) a source."""
    registry = SourceRegistry()

    source = registry.get_source(args.url)
    if not source:
        console.print(f"[red]Source not found: {args.url}[/red]")
        return

    console.print(f"[bold]Updating: {source.url}[/bold]")

    # Delete old chunks first
    if source.chunk_ids:
        console.print(f"Removing {len(source.chunk_ids)} old chunks...")
        cleanup = VectorCleanup()
        cleanup.delete_chunks(source.chunk_ids)

    # Re-process
    processor = SourceProcessor(registry)
    asyncio.run(processor.process_source(source))


def cmd_remove(args):
    """Remove a source and its chunks."""
    registry = SourceRegistry()

    source = registry.get_source(args.url)
    if not source:
        console.print(f"[red]Source not found: {args.url}[/red]")
        return

    console.print(f"[bold]Removing: {source.url}[/bold]")
    console.print(f"  Chunks to delete: {len(source.chunk_ids)}")

    if not args.yes:
        confirm = input("Are you sure? [y/N] ")
        if confirm.lower() != "y":
            console.print("[yellow]Cancelled[/yellow]")
            return

    # Delete chunks from ChromaDB
    if source.chunk_ids:
        cleanup = VectorCleanup()
        cleanup.delete_chunks(source.chunk_ids)

    # Remove from registry
    registry.remove_source(source.url)
    console.print(f"[green]Removed source: {source.url}[/green]")


def cmd_sync(args):
    """Sync all sources - process pending and check for updates."""
    registry = SourceRegistry()
    processor = SourceProcessor(registry)

    sources = registry.get_sources_needing_update()

    if not sources:
        console.print("[green]All sources up to date![/green]")
        return

    console.print(f"[bold]Found {len(sources)} sources to process[/bold]")

    # Filter by category if specified
    if args.category:
        sources = [s for s in sources if s.category == args.category]
        console.print(f"Filtered to {len(sources)} sources in category '{args.category}'")

    # Process each source
    for source in sources:
        # For updates, delete old chunks first
        if source.status == SourceStatus.ACTIVE and source.chunk_ids:
            cleanup = VectorCleanup()
            cleanup.delete_chunks(source.chunk_ids)

        asyncio.run(processor.process_source(source))

    registry.mark_sync_complete()
    console.print("\n[green]Sync complete![/green]")


def cmd_list(args):
    """List all sources."""
    registry = SourceRegistry()

    sources = registry.list_sources(
        category=args.category,
        source_type=SourceType(args.type) if args.type else None,
        status=SourceStatus(args.status) if args.status else None,
    )

    if not sources:
        console.print("[yellow]No sources found[/yellow]")
        return

    table = Table(title=f"RAG Sources ({len(sources)})")
    table.add_column("ID", style="dim")
    table.add_column("Type")
    table.add_column("Category")
    table.add_column("Status")
    table.add_column("Chunks", justify="right")
    table.add_column("URL", overflow="fold")

    for source in sources:
        status_color = {
            SourceStatus.ACTIVE: "green",
            SourceStatus.PENDING: "yellow",
            SourceStatus.ERROR: "red",
            SourceStatus.REMOVED: "dim",
        }.get(source.status, "white")

        table.add_row(
            source.id[:8],
            source.source_type.value[:4],
            source.category,
            f"[{status_color}]{source.status.value}[/{status_color}]",
            str(source.chunk_count),
            source.url[:60] + ("..." if len(source.url) > 60 else ""),
        )

    console.print(table)


def cmd_status(args):
    """Show registry status."""
    registry = SourceRegistry()
    stats = registry.get_statistics()

    console.print("\n[bold]RAG Registry Status[/bold]")
    console.print(f"  Total sources: {stats['total_sources']}")
    console.print(f"  Total chunks: {stats['total_chunks']}")
    console.print(f"  Last sync: {stats['last_sync'] or 'Never'}")
    console.print(f"  Last rebuild: {stats['last_full_rebuild'] or 'Never'}")

    if stats["by_category"]:
        console.print("\n[bold]By Category:[/bold]")
        for cat, count in sorted(stats["by_category"].items()):
            console.print(f"  {cat}: {count}")

    if stats["by_status"]:
        console.print("\n[bold]By Status:[/bold]")
        for status, count in sorted(stats["by_status"].items()):
            console.print(f"  {status}: {count}")


def cmd_import(args):
    """Import sources from scraper config."""
    registry = SourceRegistry()

    # Import from config.py
    from scraper.config import ALL_SOURCES

    added = registry.import_from_config(ALL_SOURCES)
    console.print(f"[green]Imported {added} new sources from config[/green]")

    # Show stats
    stats = registry.get_statistics()
    console.print(f"Total sources now: {stats['total_sources']}")


def cmd_rebuild(args):
    """Full rebuild - clear all and re-process everything."""
    registry = SourceRegistry()

    if not args.yes:
        confirm = input(
            "This will delete all chunks and re-process everything. Continue? [y/N] "
        )
        if confirm.lower() != "y":
            console.print("[yellow]Cancelled[/yellow]")
            return

    console.print("[bold red]Starting full rebuild...[/bold red]")

    # Get all sources
    sources = registry.list_sources()

    # Collect all chunk IDs
    all_chunk_ids = []
    for source in sources:
        all_chunk_ids.extend(source.chunk_ids)

    # Delete all chunks from ChromaDB
    if all_chunk_ids:
        console.print(f"Deleting {len(all_chunk_ids)} existing chunks...")
        cleanup = VectorCleanup()
        cleanup.delete_chunks(all_chunk_ids)

    # Reset source states
    for source in sources:
        registry.update_source_state(
            source.url,
            status=SourceStatus.PENDING,
            chunk_ids=[],
        )

    # Process all sources
    processor = SourceProcessor(registry)
    for source in sources:
        asyncio.run(processor.process_source(source))

    registry.mark_rebuild_complete()
    console.print("\n[green]Rebuild complete![/green]")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="rag",
        description="RAG Source Management CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new source")
    add_parser.add_argument("url", help="URL to add")
    add_parser.add_argument("--category", "-c", required=True, help="Category")
    add_parser.add_argument("--subcategory", "-s", help="Subcategory")
    add_parser.add_argument(
        "--type", "-t", choices=["documentation", "github"], help="Source type"
    )
    add_parser.add_argument(
        "--process", "-p", action="store_true", help="Process immediately"
    )

    # Update command
    update_parser = subparsers.add_parser("update", help="Update a source")
    update_parser.add_argument("url", help="URL to update")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a source")
    remove_parser.add_argument("url", help="URL to remove")
    remove_parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation"
    )

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync all sources")
    sync_parser.add_argument("--category", "-c", help="Filter by category")

    # List command
    list_parser = subparsers.add_parser("list", help="List sources")
    list_parser.add_argument("--category", "-c", help="Filter by category")
    list_parser.add_argument(
        "--type", "-t", choices=["documentation", "github"], help="Filter by type"
    )
    list_parser.add_argument(
        "--status",
        choices=["active", "pending", "error", "removed"],
        help="Filter by status",
    )

    # Status command
    subparsers.add_parser("status", help="Show registry status")

    # Import command
    subparsers.add_parser("import", help="Import sources from config")

    # Rebuild command
    rebuild_parser = subparsers.add_parser("rebuild", help="Full rebuild")
    rebuild_parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation"
    )

    args = parser.parse_args()

    # Dispatch to command
    commands = {
        "add": cmd_add,
        "update": cmd_update,
        "remove": cmd_remove,
        "sync": cmd_sync,
        "list": cmd_list,
        "status": cmd_status,
        "import": cmd_import,
        "rebuild": cmd_rebuild,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()

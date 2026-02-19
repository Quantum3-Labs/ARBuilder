#!/usr/bin/env python3
"""
Script to ingest Milestone 3 (Full dApp Builder) sources.

This script:
1. Scrapes documentation from M3_SOURCES in scraper/config.py
2. Clones and processes repos from M3_GITHUB_REPOS
3. Processes the raw data into chunks
4. Ingests chunks into the vector database

Usage:
    python scripts/ingest_m3_sources.py              # Full ingestion
    python scripts/ingest_m3_sources.py --scrape     # Only scrape sources
    python scripts/ingest_m3_sources.py --process    # Only process raw data
    python scripts/ingest_m3_sources.py --ingest     # Only ingest to vectordb
    python scripts/ingest_m3_sources.py --category frontend  # Single category
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

console = Console()


def scrape_m3_docs(categories: list[str] | None = None) -> dict:
    """
    Scrape documentation from M3_SOURCES.

    Args:
        categories: Optional list of categories to scrape (e.g., ['frontend', 'backend'])

    Returns:
        Dict with scraping statistics
    """
    from scraper.config import M3_SOURCES
    from scraper.web_scraper import WebScraper

    stats = {"scraped": 0, "failed": 0, "categories": []}

    # Initialize scraper
    scraper = WebScraper()

    console.print("[bold blue]Scraping M3 Documentation Sources[/bold blue]")

    for category, subcategories in M3_SOURCES.items():
        if categories and category not in categories:
            continue

        console.print(f"\n[cyan]Category: {category}[/cyan]")
        stats["categories"].append(category)

        for subcategory, urls in subcategories.items():
            console.print(f"  [dim]Subcategory: {subcategory}[/dim]")

            for url in urls:
                try:
                    console.print(f"    Scraping: {url[:60]}...")
                    result = scraper.scrape_url(url)
                    if result:
                        stats["scraped"] += 1
                    else:
                        stats["failed"] += 1
                except Exception as e:
                    console.print(f"    [red]Error: {e}[/red]")
                    stats["failed"] += 1

    return stats


def clone_m3_repos(categories: list[str] | None = None) -> dict:
    """
    Clone GitHub repositories from M3_GITHUB_REPOS.

    Args:
        categories: Optional list of categories to clone

    Returns:
        Dict with cloning statistics
    """
    from scraper.config import M3_GITHUB_REPOS
    from scraper.github_scraper import GithubScraper

    stats = {"cloned": 0, "failed": 0, "repos": []}

    console.print("\n[bold blue]Cloning M3 GitHub Repositories[/bold blue]")

    scraper = GithubScraper()

    for category, repos in M3_GITHUB_REPOS.items():
        if categories and category not in categories:
            continue

        console.print(f"\n[cyan]Category: {category}[/cyan]")

        for repo_url in repos:
            repo_name = repo_url.split("/")[-1]
            console.print(f"  Cloning: {repo_name}...")

            try:
                result = scraper.clone_repo(repo_url)
                if result:
                    stats["cloned"] += 1
                    stats["repos"].append(repo_name)
                else:
                    stats["failed"] += 1
            except Exception as e:
                console.print(f"    [red]Error: {e}[/red]")
                stats["failed"] += 1

    return stats


def process_m3_data() -> dict:
    """
    Process raw M3 data into chunks.

    Returns:
        Dict with processing statistics
    """
    from src.preprocessing.processor import DataProcessor

    console.print("\n[bold blue]Processing M3 Raw Data[/bold blue]")

    processor = DataProcessor(
        doc_max_tokens=512,
        doc_overlap_tokens=50,
        code_max_tokens=1024,
        code_overlap_lines=5,
    )

    # Process documentation
    stats = {"docs_processed": 0, "code_files_processed": 0, "chunks_created": 0}

    try:
        # Process scraped docs
        console.print("  Processing documentation...")
        doc_result = processor.process_scraped_docs()
        if doc_result:
            stats["docs_processed"] = doc_result.get("documents_processed", 0)
            stats["chunks_created"] += doc_result.get("chunks_created", 0)

        # Process GitHub repos
        console.print("  Processing code repositories...")
        code_result = processor.process_github_repos()
        if code_result:
            stats["code_files_processed"] = code_result.get("files_processed", 0)
            stats["chunks_created"] += code_result.get("chunks_created", 0)

    except Exception as e:
        console.print(f"[red]Processing error: {e}[/red]")

    return stats


def ingest_to_vectordb(collection: str = "arbbuilder_m3") -> dict:
    """
    Ingest processed chunks into vector database.

    Args:
        collection: Name of the ChromaDB collection

    Returns:
        Dict with ingestion statistics
    """
    from src.embeddings.vectordb import VectorDB, PROCESSED_DATA_DIR

    console.print(f"\n[bold blue]Ingesting to Vector Database ({collection})[/bold blue]")

    stats = {"ingested": 0, "skipped": 0, "errors": 0}

    # Find latest processed chunks file
    processed_files = sorted(
        PROCESSED_DATA_DIR.glob("processed_chunks_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not processed_files:
        console.print("[yellow]No processed chunk files found. Run --process first.[/yellow]")
        return stats

    latest_file = processed_files[0]
    console.print(f"  Loading: {latest_file.name}")

    with open(latest_file) as f:
        chunks = json.load(f)

    console.print(f"  Found {len(chunks)} chunks to ingest")

    # Filter for M3-related chunks (optional - include all for now)
    m3_categories = ["frontend", "backend", "indexer", "oracle", "wagmi", "viem",
                     "rainbowkit", "daisyui", "nestjs", "express", "thegraph",
                     "chainlink", "subgraph"]

    # Initialize VectorDB
    db = VectorDB(collection_name=collection)

    # Ingest chunks
    try:
        ingested = db.ingest_chunks(chunks, batch_size=50)
        stats["ingested"] = ingested
    except Exception as e:
        console.print(f"[red]Ingestion error: {e}[/red]")
        stats["errors"] += 1

    return stats


def print_summary(scrape_stats: dict, clone_stats: dict, process_stats: dict, ingest_stats: dict):
    """Print a summary table of all operations."""
    table = Table(title="M3 Ingestion Summary")

    table.add_column("Operation", style="cyan")
    table.add_column("Metric", style="green")
    table.add_column("Value", justify="right")

    # Scraping stats
    if scrape_stats:
        table.add_row("Scraping", "Documents Scraped", str(scrape_stats.get("scraped", 0)))
        table.add_row("", "Failed", str(scrape_stats.get("failed", 0)))
        table.add_row("", "Categories", ", ".join(scrape_stats.get("categories", [])))

    # Cloning stats
    if clone_stats:
        table.add_row("Cloning", "Repos Cloned", str(clone_stats.get("cloned", 0)))
        table.add_row("", "Failed", str(clone_stats.get("failed", 0)))

    # Processing stats
    if process_stats:
        table.add_row("Processing", "Docs Processed", str(process_stats.get("docs_processed", 0)))
        table.add_row("", "Code Files", str(process_stats.get("code_files_processed", 0)))
        table.add_row("", "Chunks Created", str(process_stats.get("chunks_created", 0)))

    # Ingestion stats
    if ingest_stats:
        table.add_row("Ingestion", "Chunks Ingested", str(ingest_stats.get("ingested", 0)))
        table.add_row("", "Errors", str(ingest_stats.get("errors", 0)))

    console.print("\n")
    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Milestone 3 (Full dApp Builder) sources"
    )
    parser.add_argument(
        "--scrape",
        action="store_true",
        help="Only scrape documentation sources"
    )
    parser.add_argument(
        "--clone",
        action="store_true",
        help="Only clone GitHub repositories"
    )
    parser.add_argument(
        "--process",
        action="store_true",
        help="Only process raw data into chunks"
    )
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Only ingest chunks to vector database"
    )
    parser.add_argument(
        "--category",
        type=str,
        nargs="+",
        choices=["frontend", "backend", "indexer", "oracle"],
        help="Filter by category (e.g., --category frontend backend)"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="arbbuilder",
        help="ChromaDB collection name (default: arbbuilder)"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the collection before ingesting"
    )

    args = parser.parse_args()

    # If no specific operation, run all
    run_all = not (args.scrape or args.clone or args.process or args.ingest)

    console.print("[bold]ARBuilder M3 Source Ingestion[/bold]")
    console.print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    scrape_stats = {}
    clone_stats = {}
    process_stats = {}
    ingest_stats = {}

    try:
        # Scrape documentation
        if run_all or args.scrape:
            scrape_stats = scrape_m3_docs(args.category)

        # Clone repos
        if run_all or args.clone:
            clone_stats = clone_m3_repos(args.category)

        # Process data
        if run_all or args.process:
            process_stats = process_m3_data()

        # Ingest to vectordb
        if run_all or args.ingest:
            if args.reset:
                console.print("[yellow]Resetting collection before ingestion...[/yellow]")
                from src.embeddings.vectordb import VectorDB
                db = VectorDB(collection_name=args.collection)
                db.reset_collection()

            ingest_stats = ingest_to_vectordb(args.collection)

        # Print summary
        print_summary(scrape_stats, clone_stats, process_stats, ingest_stats)

        console.print(f"\n[green]Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

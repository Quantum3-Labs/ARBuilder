#!/usr/bin/env python3
"""
Main entry point for ARBuilder data scraping pipeline.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel

console = Console()


async def run_full_pipeline(
    categories: list[str] | None = None,
    skip_web: bool = False,
    skip_github: bool = False,
):
    """Run the complete data scraping pipeline."""
    console.print(Panel.fit(
        "[bold blue]ARBuilder Data Scraping Pipeline[/bold blue]\n"
        "Collecting Arbitrum Stylus documentation and code examples",
        border_style="blue",
    ))

    if not skip_web:
        console.print("\n[bold]Step 1: Scraping documentation websites...[/bold]")
        from scraper.scraper import run_scraper
        await run_scraper(categories=categories)

    if not skip_github:
        console.print("\n[bold]Step 2: Cloning and processing GitHub repositories...[/bold]")
        from scraper.github_scraper import scrape_all_repos
        await scrape_all_repos(categories=categories)

    console.print("\n[bold green]Pipeline completed![/bold green]")


def main():
    parser = argparse.ArgumentParser(
        description="ARBuilder Data Scraping Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline
  python -m scraper.run

  # Scrape only Stylus sources
  python -m scraper.run --categories stylus

  # Skip web scraping, only clone GitHub repos
  python -m scraper.run --skip-web

  # Skip GitHub cloning, only scrape web
  python -m scraper.run --skip-github
        """,
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=["stylus", "arbitrum_sdk", "orbit_sdk", "arbitrum_docs"],
        help="Categories to scrape (default: all)",
    )
    parser.add_argument(
        "--skip-web",
        action="store_true",
        help="Skip web scraping",
    )
    parser.add_argument(
        "--skip-github",
        action="store_true",
        help="Skip GitHub repository cloning",
    )

    args = parser.parse_args()

    asyncio.run(run_full_pipeline(
        categories=args.categories,
        skip_web=args.skip_web,
        skip_github=args.skip_github,
    ))


if __name__ == "__main__":
    main()

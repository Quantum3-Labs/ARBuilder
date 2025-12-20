"""
ARBuilder Documentation Scraper using crawl4ai.
Scrapes Arbitrum Stylus docs, GitHub repos, and related resources.
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import ALL_SOURCES

load_dotenv()

console = Console()

# Output directories
RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
PROCESSED_DATA_DIR = Path(os.getenv("PROCESSED_DATA_DIR", "data/processed"))


def sanitize_filename(url: str) -> str:
    """Convert URL to a safe filename."""
    # Remove protocol
    name = re.sub(r"https?://", "", url)
    # Replace special characters
    name = re.sub(r"[/\\?%*:|\"<>.]", "_", name)
    # Limit length
    return name[:100]


async def scrape_url(
    crawler: AsyncWebCrawler,
    url: str,
    category: str,
    subcategory: str,
) -> Optional[dict]:
    """Scrape a single URL and return structured data."""
    try:
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=10,
            exclude_external_links=True,
            process_iframes=True,
        )

        result = await crawler.arun(url=url, config=config)

        if result.success:
            return {
                "url": url,
                "category": category,
                "subcategory": subcategory,
                "title": result.metadata.get("title", ""),
                "description": result.metadata.get("description", ""),
                "markdown": result.markdown,
                "links": result.links,
                "scraped_at": datetime.utcnow().isoformat(),
            }
        else:
            console.print(f"[red]Failed to scrape {url}: {result.error_message}[/red]")
            return None

    except Exception as e:
        console.print(f"[red]Error scraping {url}: {e}[/red]")
        return None


async def scrape_github_repo(
    crawler: AsyncWebCrawler,
    repo_url: str,
    category: str,
    subcategory: str,
) -> list[dict]:
    """Scrape a GitHub repository including README and key files."""
    results = []

    # Scrape main repo page
    main_result = await scrape_url(crawler, repo_url, category, subcategory)
    if main_result:
        results.append(main_result)

    # Try to scrape README
    readme_urls = [
        f"{repo_url}/blob/main/README.md",
        f"{repo_url}/blob/master/README.md",
        f"{repo_url}#readme",
    ]

    for readme_url in readme_urls:
        readme_result = await scrape_url(crawler, readme_url, category, f"{subcategory}_readme")
        if readme_result and readme_result.get("markdown"):
            results.append(readme_result)
            break

    return results


async def scrape_documentation_site(
    crawler: AsyncWebCrawler,
    base_url: str,
    category: str,
    subcategory: str,
    max_pages: int = 50,
) -> list[dict]:
    """Scrape a documentation site by following internal links."""
    results = []
    visited = set()
    to_visit = [base_url]

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue

        visited.add(url)
        result = await scrape_url(crawler, url, category, subcategory)

        if result:
            results.append(result)

            # Extract internal links to follow
            if result.get("links"):
                internal_links = result["links"].get("internal", [])
                for link in internal_links:
                    link_url = link.get("href", "")
                    # Only follow docs pages
                    if (
                        link_url.startswith(base_url) or
                        link_url.startswith("/")
                    ) and link_url not in visited:
                        if link_url.startswith("/"):
                            # Convert relative to absolute
                            from urllib.parse import urljoin
                            link_url = urljoin(base_url, link_url)
                        to_visit.append(link_url)

    return results


async def run_scraper(
    categories: Optional[list[str]] = None,
    max_concurrent: int = 3,
) -> None:
    """
    Run the full scraping pipeline.

    Args:
        categories: List of categories to scrape (e.g., ['stylus', 'arbitrum_sdk']).
                   If None, scrape all categories.
        max_concurrent: Maximum concurrent requests.
    """
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
    )

    all_results = []

    async with AsyncWebCrawler(config=browser_config) as crawler:
        sources_to_scrape = ALL_SOURCES if categories is None else {
            k: v for k, v in ALL_SOURCES.items() if k in categories
        }

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for category, subcategories in sources_to_scrape.items():
                task = progress.add_task(f"Scraping {category}...", total=None)

                for subcategory, urls in subcategories.items():
                    for url in urls:
                        progress.update(task, description=f"Scraping {category}/{subcategory}: {url[:50]}...")

                        if "github.com" in url:
                            results = await scrape_github_repo(
                                crawler, url, category, subcategory
                            )
                        elif "docs." in url or "/docs/" in url:
                            results = await scrape_documentation_site(
                                crawler, url, category, subcategory, max_pages=30
                            )
                        else:
                            result = await scrape_url(crawler, url, category, subcategory)
                            results = [result] if result else []

                        all_results.extend(results)

                        # Small delay to be respectful
                        await asyncio.sleep(1)

                progress.remove_task(task)

    # Save results
    output_file = RAW_DATA_DIR / f"scraped_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    console.print(f"\n[green]Scraped {len(all_results)} pages. Saved to {output_file}[/green]")

    # Also save individual markdown files for easier processing
    markdown_dir = RAW_DATA_DIR / "markdown"
    markdown_dir.mkdir(exist_ok=True)

    for result in all_results:
        if result and result.get("markdown"):
            filename = sanitize_filename(result["url"]) + ".md"
            filepath = markdown_dir / filename

            # Add metadata header
            content = f"""---
url: {result['url']}
title: {result.get('title', '')}
category: {result['category']}
subcategory: {result['subcategory']}
scraped_at: {result['scraped_at']}
---

{result['markdown']}
"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

    console.print(f"[green]Saved {len(all_results)} markdown files to {markdown_dir}[/green]")


def main():
    """Entry point for the scraper."""
    import argparse

    parser = argparse.ArgumentParser(description="ARBuilder Documentation Scraper")
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=list(ALL_SOURCES.keys()),
        help="Categories to scrape (default: all)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=3,
        help="Maximum concurrent requests (default: 3)",
    )

    args = parser.parse_args()

    asyncio.run(run_scraper(
        categories=args.categories,
        max_concurrent=args.max_concurrent,
    ))


if __name__ == "__main__":
    main()

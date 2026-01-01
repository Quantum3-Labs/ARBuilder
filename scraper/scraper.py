"""
ARBuilder Documentation Scraper using crawl4ai.
Scrapes Arbitrum Stylus docs, GitHub repos, and related resources.
"""

import asyncio
import json
import logging
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
logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # seconds

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
    retries: int = MAX_RETRIES,
) -> Optional[dict]:
    """
    Scrape a single URL and return structured data with retry logic.

    Args:
        crawler: The AsyncWebCrawler instance.
        url: URL to scrape.
        category: Category of the content.
        subcategory: Subcategory of the content.
        retries: Number of retry attempts for transient errors.

    Returns:
        Scraped data dictionary or None if failed.
    """
    last_error = None

    for attempt in range(retries):
        try:
            # Configure crawler with iframe handling disabled to avoid context errors
            config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                word_count_threshold=10,
                exclude_external_links=True,
                process_iframes=False,  # Disabled to avoid "execution context destroyed" errors
            )

            result = await crawler.arun(url=url, config=config)

            if result.success:
                # Validate we got actual content
                markdown_content = result.markdown or ""
                if len(markdown_content.strip()) < 50:
                    logger.warning(f"Scraped content too short for {url} ({len(markdown_content)} chars)")
                    # Still return it, but log the warning

                return {
                    "url": url,
                    "category": category,
                    "subcategory": subcategory,
                    "title": result.metadata.get("title", "") if result.metadata else "",
                    "description": result.metadata.get("description", "") if result.metadata else "",
                    "markdown": markdown_content,
                    "links": result.links if result.links else {},
                    "scraped_at": datetime.utcnow().isoformat(),
                }
            else:
                error_msg = result.error_message if hasattr(result, 'error_message') else "Unknown error"
                last_error = error_msg

                # Check for retryable errors
                retryable_errors = [
                    "timeout",
                    "navigation",
                    "context was destroyed",
                    "connection",
                    "net::",
                    "ERR_",
                ]

                is_retryable = any(err.lower() in str(error_msg).lower() for err in retryable_errors)

                if is_retryable and attempt < retries - 1:
                    delay = RETRY_DELAY_BASE * (2 ** attempt)
                    logger.warning(
                        f"Retryable error scraping {url} (attempt {attempt + 1}/{retries}): {error_msg}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"Failed to scrape {url}: {error_msg}")
                    console.print(f"[red]Failed to scrape {url}: {error_msg}[/red]")
                    return None

        except asyncio.TimeoutError as e:
            last_error = f"Timeout: {e}"
            if attempt < retries - 1:
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(f"Timeout scraping {url} (attempt {attempt + 1}/{retries}). Retrying in {delay}s...")
                await asyncio.sleep(delay)
                continue
            else:
                logger.error(f"Timeout scraping {url} after {retries} attempts")
                console.print(f"[red]Timeout scraping {url}[/red]")
                return None

        except Exception as e:
            last_error = str(e)
            error_type = type(e).__name__

            # Check for retryable exceptions
            retryable_exceptions = ["ConnectionError", "TimeoutError", "BrowserError"]
            is_retryable = any(exc in error_type for exc in retryable_exceptions) or \
                           "context" in str(e).lower() or \
                           "navigation" in str(e).lower()

            if is_retryable and attempt < retries - 1:
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(
                    f"Error scraping {url} (attempt {attempt + 1}/{retries}): {error_type}: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
                continue
            else:
                logger.error(f"Error scraping {url}: {error_type}: {e}")
                console.print(f"[red]Error scraping {url}: {error_type}: {e}[/red]")
                return None

    logger.error(f"Failed to scrape {url} after {retries} attempts. Last error: {last_error}")
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

"""
Main data processor for ARBuilder preprocessing pipeline.
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .cleaner import TextCleaner
from .chunker import DocumentChunker, CodeChunker, Chunk

# Import version extractor - handle import error gracefully
try:
    from scraper.version_extractor import (
        get_latest_sdk_version_sync,
        extract_sdk_version_from_repo,
        detect_deprecated_patterns,
        is_version_current,
    )
    HAS_VERSION_EXTRACTOR = True
except ImportError:
    HAS_VERSION_EXTRACTOR = False

load_dotenv()

console = Console()

RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
PROCESSED_DATA_DIR = Path(os.getenv("PROCESSED_DATA_DIR", "data/processed"))


class DataProcessor:
    """
    Process raw scraped data into chunks ready for embedding.
    """

    def __init__(
        self,
        doc_max_tokens: int = 512,
        doc_overlap_tokens: int = 50,
        code_max_tokens: int = 1024,
        code_overlap_lines: int = 5,
    ):
        """
        Initialize the data processor.

        Args:
            doc_max_tokens: Max tokens per document chunk.
            doc_overlap_tokens: Token overlap for documents.
            code_max_tokens: Max tokens per code chunk.
            code_overlap_lines: Line overlap for code.
        """
        self.text_cleaner = TextCleaner()
        self.doc_chunker = DocumentChunker(
            max_tokens=doc_max_tokens,
            overlap_tokens=doc_overlap_tokens,
        )
        self.code_chunker = CodeChunker(
            max_tokens=code_max_tokens,
            overlap_lines=code_overlap_lines,
        )
        # Cache for latest SDK version
        self._latest_sdk_version: Optional[str] = None
        # Cache for repo SDK versions
        self._repo_sdk_versions: dict[str, Optional[str]] = {}

    def _compute_content_hash(self, content: str) -> str:
        """Compute a short hash of the content for diff detection."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _get_latest_sdk_version(self) -> Optional[str]:
        """Get the latest SDK version, with caching."""
        if self._latest_sdk_version is None and HAS_VERSION_EXTRACTOR:
            console.print("[blue]Fetching latest stylus-sdk version from crates.io...[/blue]")
            self._latest_sdk_version = get_latest_sdk_version_sync()
            if self._latest_sdk_version:
                console.print(f"[green]Latest SDK version: {self._latest_sdk_version}[/green]")
        return self._latest_sdk_version

    def process_scraped_docs(
        self,
        input_file: Optional[Path] = None,
    ) -> list[dict]:
        """
        Process scraped documentation data.

        Args:
            input_file: Path to scraped JSON file. If None, uses latest.

        Returns:
            List of processed chunks as dicts.
        """
        # Find input file
        if input_file is None:
            input_file = self._find_latest_file("scraped_data_*.json")

        if not input_file or not input_file.exists():
            console.print("[red]No scraped data file found![/red]")
            return []

        console.print(f"[blue]Processing: {input_file}[/blue]")

        with open(input_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        all_chunks = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
        ) as progress:
            task = progress.add_task("Processing documents...", total=len(raw_data))

            for item in raw_data:
                if not item or not item.get("markdown"):
                    progress.advance(task)
                    continue

                # Clean the content
                content = self.text_cleaner.remove_frontmatter(item["markdown"])
                content = self.text_cleaner.clean(content)

                if not content.strip():
                    progress.advance(task)
                    continue

                # Compute content hash for diff detection
                content_hash = self._compute_content_hash(content)

                # Extract metadata
                metadata = {
                    "source": "documentation",
                    "url": item.get("url", ""),
                    "title": item.get("title") or self.text_cleaner.extract_title(content) or "",
                    "category": item.get("category", ""),
                    "subcategory": item.get("subcategory", ""),
                    "scraped_at": item.get("scraped_at", "") or datetime.utcnow().isoformat(),
                    "content_hash": content_hash,
                }

                # Chunk the content
                chunks = self.doc_chunker.chunk(content, metadata)

                for chunk in chunks:
                    all_chunks.append(chunk.to_dict())

                progress.advance(task)

        console.print(f"[green]Processed {len(raw_data)} documents into {len(all_chunks)} chunks[/green]")
        return all_chunks

    def process_github_repos(
        self,
        input_file: Optional[Path] = None,
    ) -> list[dict]:
        """
        Process GitHub repository data.

        Args:
            input_file: Path to GitHub repos JSON file. If None, uses latest.

        Returns:
            List of processed chunks as dicts.
        """
        # Find input file
        if input_file is None:
            input_file = self._find_latest_file("github_repos_*.json")

        if not input_file or not input_file.exists():
            console.print("[red]No GitHub repos file found![/red]")
            return []

        console.print(f"[blue]Processing: {input_file}[/blue]")

        with open(input_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        all_chunks = []
        total_files = sum(len(repo.get("files", [])) for repo in raw_data)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
        ) as progress:
            task = progress.add_task("Processing code files...", total=total_files)

            for repo in raw_data:
                repo_name = repo.get("repo_name", "")
                repo_url = repo.get("repo_url", "")
                category = repo.get("category", "")
                subcategory = repo.get("subcategory", "")

                # Try to get SDK version for this repo
                repo_sdk_version = None
                if HAS_VERSION_EXTRACTOR and repo_name:
                    repo_dir = RAW_DATA_DIR / "repos" / repo_name
                    if repo_dir.exists():
                        repo_sdk_version = extract_sdk_version_from_repo(repo_dir)
                        if repo_sdk_version:
                            self._repo_sdk_versions[repo_name] = repo_sdk_version

                for file_info in repo.get("files", []):
                    content = file_info.get("content", "")
                    file_path = file_info.get("path", "")
                    extension = file_info.get("extension", "")

                    if not content.strip():
                        progress.advance(task)
                        continue

                    # Clean the code
                    content = self.text_cleaner.clean_code(content, extension.lstrip("."))

                    if not content.strip():
                        progress.advance(task)
                        continue

                    # Detect deprecated patterns in Rust code
                    deprecated_patterns = []
                    if HAS_VERSION_EXTRACTOR and extension == ".rs":
                        deprecated_patterns = detect_deprecated_patterns(content)

                    # Compute content hash for diff detection
                    content_hash = self._compute_content_hash(content)

                    # Check if repo SDK version is current
                    latest_sdk = self._get_latest_sdk_version()
                    is_current = True
                    if repo_sdk_version and latest_sdk and HAS_VERSION_EXTRACTOR:
                        is_current = is_version_current(repo_sdk_version, latest_sdk)

                    # Metadata for code files
                    metadata = {
                        "source": "github",
                        "repo_name": repo_name,
                        "repo_url": repo_url,
                        "file_path": file_path,
                        "extension": extension,
                        "category": category,
                        "subcategory": subcategory,
                        # New metadata fields
                        "sdk_version": repo_sdk_version or "",
                        "is_current": is_current,
                        "deprecated_patterns": deprecated_patterns,
                        "content_hash": content_hash,
                        "scraped_at": datetime.utcnow().isoformat(),
                    }

                    # Handle markdown files differently
                    if extension in [".md", ".markdown"]:
                        content = self.text_cleaner.remove_frontmatter(content)
                        content = self.text_cleaner.clean(content)
                        chunks = self.doc_chunker.chunk(content, metadata)
                    else:
                        chunks = self.code_chunker.chunk(content, extension, metadata)

                    for chunk in chunks:
                        all_chunks.append(chunk.to_dict())

                    progress.advance(task)

        console.print(f"[green]Processed {total_files} files into {len(all_chunks)} chunks[/green]")
        return all_chunks

    def process_all(self) -> dict:
        """
        Process all raw data and save to processed directory.

        Returns:
            Statistics about the processing.
        """
        PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

        console.print("\n[bold]Step 1: Processing documentation...[/bold]")
        doc_chunks = self.process_scraped_docs()

        console.print("\n[bold]Step 2: Processing code repositories...[/bold]")
        code_chunks = self.process_github_repos()

        # Combine all chunks
        all_chunks = doc_chunks + code_chunks

        # Add deterministic IDs based on content hash
        # This ensures same content always gets same ID (for upsert to work correctly)
        for chunk in all_chunks:
            # Create hash from source URL + content (first 500 chars for stability)
            hash_input = f"{chunk.get('url', '')}{chunk.get('content', '')[:500]}"
            content_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
            chunk["id"] = f"chunk_{content_hash}"

        # Save processed data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = PROCESSED_DATA_DIR / f"processed_chunks_{timestamp}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)

        console.print(f"\n[green]Saved {len(all_chunks)} chunks to {output_file}[/green]")

        # Generate statistics
        stats = self._generate_stats(all_chunks)
        stats_file = PROCESSED_DATA_DIR / f"processing_stats_{timestamp}.json"

        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

        console.print(f"[green]Saved statistics to {stats_file}[/green]")

        # Print summary
        self._print_summary(stats)

        return stats

    def _find_latest_file(self, pattern: str) -> Optional[Path]:
        """Find the latest file matching a pattern."""
        files = list(RAW_DATA_DIR.glob(pattern))
        if not files:
            return None
        return max(files, key=lambda p: p.stat().st_mtime)

    def _generate_stats(self, chunks: list[dict]) -> dict:
        """Generate statistics about processed chunks."""
        total_tokens = sum(c.get("token_count", 0) for c in chunks)

        by_source = {}
        by_category = {}
        by_language = {}
        by_sdk_version = {}
        deprecated_count = 0
        current_count = 0
        outdated_count = 0

        for chunk in chunks:
            # By source
            source = chunk.get("source", "unknown")
            by_source[source] = by_source.get(source, 0) + 1

            # By category
            category = chunk.get("category", "unknown")
            by_category[category] = by_category.get(category, 0) + 1

            # By language (for code)
            if chunk.get("source") == "github":
                lang = chunk.get("language", "unknown")
                by_language[lang] = by_language.get(lang, 0) + 1

                # Track SDK versions
                sdk_version = chunk.get("sdk_version", "")
                if sdk_version:
                    by_sdk_version[sdk_version] = by_sdk_version.get(sdk_version, 0) + 1

                # Track current vs outdated
                if chunk.get("is_current", True):
                    current_count += 1
                else:
                    outdated_count += 1

                # Count chunks with deprecated patterns
                if chunk.get("deprecated_patterns"):
                    deprecated_count += 1

        return {
            "total_chunks": len(chunks),
            "total_tokens": total_tokens,
            "avg_tokens_per_chunk": total_tokens / len(chunks) if chunks else 0,
            "by_source": by_source,
            "by_category": by_category,
            "by_language": by_language,
            "by_sdk_version": by_sdk_version,
            "latest_sdk_version": self._latest_sdk_version,
            "current_chunks": current_count,
            "outdated_chunks": outdated_count,
            "deprecated_pattern_chunks": deprecated_count,
            "processed_at": datetime.utcnow().isoformat(),
        }

    def _print_summary(self, stats: dict):
        """Print processing summary."""
        console.print("\n[bold]Processing Summary:[/bold]")
        console.print(f"  Total chunks: {stats['total_chunks']:,}")
        console.print(f"  Total tokens: {stats['total_tokens']:,}")
        console.print(f"  Avg tokens/chunk: {stats['avg_tokens_per_chunk']:.1f}")

        console.print("\n[bold]By Source:[/bold]")
        for source, count in stats["by_source"].items():
            console.print(f"  {source}: {count:,}")

        console.print("\n[bold]By Category:[/bold]")
        for category, count in sorted(stats["by_category"].items(), key=lambda x: -x[1]):
            console.print(f"  {category}: {count:,}")

        if stats["by_language"]:
            console.print("\n[bold]By Language:[/bold]")
            for lang, count in sorted(stats["by_language"].items(), key=lambda x: -x[1]):
                console.print(f"  {lang}: {count:,}")

        # SDK version info
        if stats.get("latest_sdk_version"):
            console.print(f"\n[bold]SDK Version Info:[/bold]")
            console.print(f"  Latest stylus-sdk: {stats['latest_sdk_version']}")
            console.print(f"  Current chunks: {stats.get('current_chunks', 0):,}")
            console.print(f"  Outdated chunks: {stats.get('outdated_chunks', 0):,}")
            console.print(f"  With deprecated patterns: {stats.get('deprecated_pattern_chunks', 0):,}")

            if stats.get("by_sdk_version"):
                console.print("\n[bold]By SDK Version:[/bold]")
                for version, count in sorted(stats["by_sdk_version"].items(), key=lambda x: -x[1]):
                    console.print(f"  {version}: {count:,}")


def main():
    """Entry point for preprocessing."""
    import argparse

    parser = argparse.ArgumentParser(description="ARBuilder Data Preprocessing")
    parser.add_argument(
        "--doc-max-tokens",
        type=int,
        default=512,
        help="Max tokens per document chunk (default: 512)",
    )
    parser.add_argument(
        "--code-max-tokens",
        type=int,
        default=1024,
        help="Max tokens per code chunk (default: 1024)",
    )

    args = parser.parse_args()

    processor = DataProcessor(
        doc_max_tokens=args.doc_max_tokens,
        code_max_tokens=args.code_max_tokens,
    )

    processor.process_all()


if __name__ == "__main__":
    main()

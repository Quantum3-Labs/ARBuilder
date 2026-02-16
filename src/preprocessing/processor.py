"""
Main data processor for ARBuilder preprocessing pipeline.
"""

import hashlib
import json
import os
import re
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

# Import version manager for deprecation checking
try:
    from src.utils.version_manager import (
        is_version_deprecated as check_version_deprecated,
        get_main_version,
        get_minimum_version,
        apply_version_transforms,
    )
    HAS_VERSION_MANAGER = True
except ImportError:
    HAS_VERSION_MANAGER = False
    apply_version_transforms = None

# Import config for repo filtering
try:
    from scraper.config import get_all_config_repo_urls, get_config_repo_info
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False

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
        # Counter for modernized chunks
        self._modernized_count: int = 0

    def _compute_content_hash(self, content: str) -> str:
        """Compute a short hash of the content for diff detection."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _get_legacy_sdk_versions() -> set[str]:
        """Get SDK versions that need modernization (all supported but not main).

        Derived from version_manager config: any version with status != 'main'
        and status != 'deprecated' (deprecated ones are already excluded at ingest).
        """
        if not HAS_VERSION_MANAGER:
            return set()
        try:
            from src.utils.version_manager import load_version_config
            config = load_version_config()
            main_version = config.get("main_version", "")
            return {
                v for v, info in config.get("versions", {}).items()
                if v != main_version and info.get("status") != "deprecated"
            }
        except Exception:
            return set()

    def _create_modernized_copy(self, chunk: dict) -> Optional[dict]:
        """
        Create a modernized copy of a chunk containing legacy SDK 0.9.x patterns.

        Returns a NEW chunk dict with 0.10.0 patterns, or None if no changes needed.
        The original chunk is NOT modified — both original and modernized versions
        are kept as separate data sources (dual-chunk strategy).

        Uses apply_version_transforms() from version_manager for centralized transforms.

        Args:
            chunk: Chunk dict with 'content' and metadata fields.

        Returns:
            A new modernized chunk dict, or None if no modernization needed.
        """
        extension = chunk.get("extension", "")
        sdk_version = chunk.get("sdk_version", "")

        # Only modernize .rs chunks from legacy SDK versions
        if extension != ".rs" or sdk_version not in self._get_legacy_sdk_versions():
            return None

        content = chunk.get("content", "")
        if not content:
            return None

        # Use centralized version transforms
        target = get_main_version() if HAS_VERSION_MANAGER else "0.10.0"
        if apply_version_transforms is not None:
            modernized_content = apply_version_transforms(content, sdk_version, target)
        else:
            # Fallback: no transforms available
            return None

        # Only create copy if content actually changed
        if modernized_content == content:
            return None

        # Create a copy with modernized content and distinct metadata
        modernized = dict(chunk)
        modernized["content"] = modernized_content
        modernized["modernized"] = True
        modernized["modernized_from"] = sdk_version
        modernized["sdk_version"] = target
        modernized["stylus_version"] = target
        self._modernized_count += 1

        return modernized

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
                    chunk_dict = chunk.to_dict()
                    all_chunks.append(chunk_dict)  # Keep original
                    # Create modernized copy if applicable (dual-chunk)
                    modernized = self._create_modernized_copy(chunk_dict)
                    if modernized:
                        all_chunks.append(modernized)

                progress.advance(task)

        console.print(f"[green]Processed {len(raw_data)} documents into {len(all_chunks)} chunks[/green]")
        return all_chunks

    def process_github_repos(
        self,
        input_file: Optional[Path] = None,
    ) -> list[dict]:
        """
        Process GitHub repository data.
        Uses config-based filtering to skip repos not in the current config.
        Reads sdk_version from input JSON first, falls back to Cargo.toml extraction.

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

        # Build config-based filter: only process repos that are in the config
        config_urls = set()
        config_info = {}
        if HAS_CONFIG:
            config_urls = get_all_config_repo_urls()
            config_info = get_config_repo_info()

        all_chunks = []
        skipped_repos = []
        total_files = 0

        # Pre-filter repos based on config
        filtered_data = []
        for repo in raw_data:
            repo_url = repo.get("repo_url", "")
            if HAS_CONFIG and config_urls and repo_url not in config_urls:
                skipped_repos.append(repo.get("repo_name", repo_url))
                continue
            filtered_data.append(repo)
            total_files += len(repo.get("files", []))

        if skipped_repos:
            console.print(f"[yellow]Skipped {len(skipped_repos)} repos not in config: {', '.join(skipped_repos)}[/yellow]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
        ) as progress:
            task = progress.add_task("Processing code files...", total=total_files)

            for repo in filtered_data:
                repo_name = repo.get("repo_name", "")
                repo_url = repo.get("repo_url", "")
                category = repo.get("category", "")
                subcategory = repo.get("subcategory", "")

                # SDK version resolution:
                # 1. From input JSON (set by scraper from config — source of truth)
                # 2. Fallback to Cargo.toml extraction
                # 3. "N/A" for non-Rust repos (TypeScript SDK, tutorials, etc.)
                repo_sdk_version = repo.get("sdk_version") or None

                # Also check config info as a secondary source
                if not repo_sdk_version and repo_url in config_info:
                    repo_sdk_version = config_info[repo_url].get("sdk_version") or None

                # Fallback: extract from Cargo.toml on disk
                if not repo_sdk_version and HAS_VERSION_EXTRACTOR and repo_name:
                    repo_dir = RAW_DATA_DIR / "repos" / repo_name
                    if repo_dir.exists():
                        repo_sdk_version = extract_sdk_version_from_repo(repo_dir)

                # For non-Rust repos, use "N/A" instead of empty string
                if repo_sdk_version == "N/A":
                    display_sdk_version = "N/A"
                elif repo_sdk_version:
                    display_sdk_version = repo_sdk_version
                else:
                    # Check if this repo has any .rs files — if not, it's non-Rust
                    has_rust = any(
                        f.get("extension") == ".rs" for f in repo.get("files", [])
                    )
                    display_sdk_version = "" if has_rust else "N/A"

                if repo_sdk_version and repo_sdk_version != "N/A":
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
                    effective_version = repo_sdk_version if repo_sdk_version and repo_sdk_version != "N/A" else None
                    if effective_version and latest_sdk and HAS_VERSION_EXTRACTOR:
                        is_current = is_version_current(effective_version, latest_sdk)

                    # Check if version is deprecated (below minimum)
                    version_deprecated = False
                    if effective_version and HAS_VERSION_MANAGER:
                        version_deprecated = check_version_deprecated(effective_version)

                    # Determine source type for cleaner classification
                    source_type = "project" if category in ("stylus",) and subcategory not in ("official", "articles") else "github"

                    # Metadata for code files
                    metadata = {
                        "source": source_type,
                        "repo_name": repo_name,
                        "repo_url": repo_url,
                        "file_path": file_path,
                        "extension": extension,
                        "category": category,
                        "subcategory": subcategory,
                        # SDK version tracking
                        "sdk_version": display_sdk_version,
                        "stylus_version": display_sdk_version,
                        "is_current": is_current,
                        "is_version_deprecated": version_deprecated,
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
                        chunk_dict = chunk.to_dict()
                        all_chunks.append(chunk_dict)  # Keep original
                        # Create modernized copy if applicable (dual-chunk)
                        modernized = self._create_modernized_copy(chunk_dict)
                        if modernized:
                            all_chunks.append(modernized)

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
        # Modernized copies get a _mod suffix for distinct IDs
        for chunk in all_chunks:
            # Create hash from source URL + content (first 500 chars for stability)
            hash_input = f"{chunk.get('url', '')}{chunk.get('content', '')[:500]}"
            content_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
            suffix = "_mod" if chunk.get("modernized") else ""
            chunk["id"] = f"chunk_{content_hash}{suffix}"

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
        deprecated_version_count = 0  # Chunks with deprecated SDK version
        current_count = 0
        outdated_count = 0
        modernized_count = 0
        modernized_from_versions = {}

        for chunk in chunks:
            # By source
            source = chunk.get("source", "unknown")
            by_source[source] = by_source.get(source, 0) + 1

            # By category
            category = chunk.get("category", "unknown")
            by_category[category] = by_category.get(category, 0) + 1

            # By language (for code — includes "project" and "github" sources)
            if chunk.get("source") in ("github", "project"):
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

                # Count chunks with deprecated SDK version (below minimum)
                if chunk.get("is_version_deprecated", False):
                    deprecated_version_count += 1

                # Count modernized chunks
                if chunk.get("modernized", False):
                    modernized_count += 1
                    from_ver = chunk.get("modernized_from", "unknown")
                    modernized_from_versions[from_ver] = modernized_from_versions.get(from_ver, 0) + 1

        # Get version config info
        main_version = None
        minimum_version = None
        if HAS_VERSION_MANAGER:
            try:
                main_version = get_main_version()
                minimum_version = get_minimum_version()
            except Exception:
                pass

        return {
            "total_chunks": len(chunks),
            "total_tokens": total_tokens,
            "avg_tokens_per_chunk": total_tokens / len(chunks) if chunks else 0,
            "by_source": by_source,
            "by_category": by_category,
            "by_language": by_language,
            "by_sdk_version": by_sdk_version,
            "latest_sdk_version": self._latest_sdk_version,
            "main_supported_version": main_version,
            "minimum_supported_version": minimum_version,
            "current_chunks": current_count,
            "outdated_chunks": outdated_count,
            "deprecated_pattern_chunks": deprecated_count,
            "deprecated_version_chunks": deprecated_version_count,
            "modernized_chunks": modernized_count,
            "modernized_from_versions": modernized_from_versions,
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
        if stats.get("latest_sdk_version") or stats.get("main_supported_version"):
            console.print(f"\n[bold]SDK Version Info:[/bold]")
            if stats.get("main_supported_version"):
                console.print(f"  Main supported: {stats['main_supported_version']}")
            if stats.get("minimum_supported_version"):
                console.print(f"  Minimum supported: {stats['minimum_supported_version']}")
            if stats.get("latest_sdk_version"):
                console.print(f"  Latest on crates.io: {stats['latest_sdk_version']}")
            console.print(f"  Current chunks: {stats.get('current_chunks', 0):,}")
            console.print(f"  Outdated chunks: {stats.get('outdated_chunks', 0):,}")
            console.print(f"  Deprecated version chunks: {stats.get('deprecated_version_chunks', 0):,}")
            console.print(f"  With deprecated patterns: {stats.get('deprecated_pattern_chunks', 0):,}")

            if stats.get("modernized_chunks", 0) > 0:
                console.print(f"  Modernized chunks: {stats['modernized_chunks']:,}")
                if stats.get("modernized_from_versions"):
                    for ver, count in sorted(stats["modernized_from_versions"].items()):
                        console.print(f"    from {ver}: {count:,}")

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

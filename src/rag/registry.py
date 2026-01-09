"""
Source Registry for RAG Pipeline.

Tracks all documentation and code sources with their state,
enabling efficient incremental updates.
"""

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum


class SourceType(str, Enum):
    DOCUMENTATION = "documentation"
    GITHUB = "github"


class SourceStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"  # Added but not yet processed
    ERROR = "error"
    REMOVED = "removed"


@dataclass
class Source:
    """Represents a single source (URL or GitHub repo)."""

    url: str
    source_type: SourceType
    category: str
    subcategory: str = ""

    # State tracking
    status: SourceStatus = SourceStatus.PENDING
    last_modified: Optional[str] = None  # From HTTP headers or git commit
    etag: Optional[str] = None  # HTTP ETag for docs
    commit_hash: Optional[str] = None  # Git commit hash for repos
    content_hash: Optional[str] = None  # Hash of scraped content

    # Processing tracking
    last_scraped: Optional[str] = None
    last_processed: Optional[str] = None
    chunk_ids: list[str] = field(default_factory=list)
    chunk_count: int = 0

    # Error tracking
    last_error: Optional[str] = None
    error_count: int = 0

    @property
    def id(self) -> str:
        """Generate deterministic ID from URL."""
        return hashlib.sha256(self.url.encode()).hexdigest()[:16]

    @property
    def is_github(self) -> bool:
        return self.source_type == SourceType.GITHUB or "github.com" in self.url

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["source_type"] = self.source_type.value
        data["status"] = self.status.value
        data["id"] = self.id
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Source":
        """Create Source from dictionary."""
        # Handle enum conversion
        if "source_type" in data:
            data["source_type"] = SourceType(data["source_type"])
        if "status" in data:
            data["status"] = SourceStatus(data["status"])
        # Remove computed fields
        data.pop("id", None)
        return cls(**data)


@dataclass
class RegistryState:
    """Complete registry state."""

    version: str = "1.0"
    last_sync: Optional[str] = None
    sources: dict[str, Source] = field(default_factory=dict)

    # Statistics
    total_chunks: int = 0
    last_full_rebuild: Optional[str] = None


class SourceRegistry:
    """
    Manages the source registry for RAG pipeline.

    Provides operations to add, update, remove, and sync sources
    with efficient incremental updates.
    """

    STATE_DIR = Path(".rag-state")
    REGISTRY_FILE = STATE_DIR / "sources.json"

    def __init__(self, state_dir: Optional[Path] = None):
        if state_dir:
            self.STATE_DIR = state_dir
            self.REGISTRY_FILE = state_dir / "sources.json"

        self._state: Optional[RegistryState] = None

    def _ensure_state_dir(self) -> None:
        """Ensure state directory exists."""
        self.STATE_DIR.mkdir(parents=True, exist_ok=True)

    def load(self) -> RegistryState:
        """Load registry from disk."""
        if self._state is not None:
            return self._state

        if not self.REGISTRY_FILE.exists():
            self._state = RegistryState()
            return self._state

        try:
            with open(self.REGISTRY_FILE, "r") as f:
                data = json.load(f)

            # Convert sources dict
            sources = {}
            for source_id, source_data in data.get("sources", {}).items():
                sources[source_id] = Source.from_dict(source_data)

            self._state = RegistryState(
                version=data.get("version", "1.0"),
                last_sync=data.get("last_sync"),
                sources=sources,
                total_chunks=data.get("total_chunks", 0),
                last_full_rebuild=data.get("last_full_rebuild"),
            )
            return self._state
        except Exception as e:
            print(f"Warning: Could not load registry: {e}")
            self._state = RegistryState()
            return self._state

    def save(self) -> None:
        """Save registry to disk."""
        self._ensure_state_dir()

        state = self.load()

        # Convert to serializable format
        data = {
            "version": state.version,
            "last_sync": state.last_sync,
            "total_chunks": state.total_chunks,
            "last_full_rebuild": state.last_full_rebuild,
            "sources": {
                source_id: source.to_dict()
                for source_id, source in state.sources.items()
            },
        }

        with open(self.REGISTRY_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def add_source(
        self,
        url: str,
        category: str,
        subcategory: str = "",
        source_type: Optional[SourceType] = None,
    ) -> Source:
        """
        Add a new source to the registry.

        Args:
            url: URL of the documentation page or GitHub repo
            category: Category (stylus, arbitrum_sdk, etc.)
            subcategory: Subcategory (official_docs, examples, etc.)
            source_type: Optional type override (auto-detected from URL)

        Returns:
            The created Source object
        """
        # Auto-detect source type
        if source_type is None:
            if "github.com" in url:
                source_type = SourceType.GITHUB
            else:
                source_type = SourceType.DOCUMENTATION

        source = Source(
            url=url,
            source_type=source_type,
            category=category,
            subcategory=subcategory,
            status=SourceStatus.PENDING,
        )

        state = self.load()

        # Check if already exists
        if source.id in state.sources:
            existing = state.sources[source.id]
            print(f"Source already exists: {existing.url}")
            return existing

        state.sources[source.id] = source
        self.save()

        return source

    def get_source(self, url_or_id: str) -> Optional[Source]:
        """Get a source by URL or ID."""
        state = self.load()

        # Try as ID first
        if url_or_id in state.sources:
            return state.sources[url_or_id]

        # Try as URL (compute ID)
        source_id = hashlib.sha256(url_or_id.encode()).hexdigest()[:16]
        return state.sources.get(source_id)

    def remove_source(self, url_or_id: str) -> Optional[Source]:
        """
        Remove a source from the registry.

        Returns the removed source (with chunk_ids for cleanup).
        """
        state = self.load()

        # Find source
        source = self.get_source(url_or_id)
        if not source:
            return None

        # Remove from registry
        del state.sources[source.id]
        state.total_chunks -= source.chunk_count
        self.save()

        return source

    def update_source_state(
        self,
        url_or_id: str,
        *,
        status: Optional[SourceStatus] = None,
        last_modified: Optional[str] = None,
        etag: Optional[str] = None,
        commit_hash: Optional[str] = None,
        content_hash: Optional[str] = None,
        last_scraped: Optional[str] = None,
        last_processed: Optional[str] = None,
        chunk_ids: Optional[list[str]] = None,
        last_error: Optional[str] = None,
    ) -> Optional[Source]:
        """Update source state after scraping/processing."""
        source = self.get_source(url_or_id)
        if not source:
            return None

        state = self.load()

        # Update fields
        if status is not None:
            source.status = status
        if last_modified is not None:
            source.last_modified = last_modified
        if etag is not None:
            source.etag = etag
        if commit_hash is not None:
            source.commit_hash = commit_hash
        if content_hash is not None:
            source.content_hash = content_hash
        if last_scraped is not None:
            source.last_scraped = last_scraped
        if last_processed is not None:
            source.last_processed = last_processed
        if chunk_ids is not None:
            # Update total chunks count
            state.total_chunks -= source.chunk_count
            source.chunk_ids = chunk_ids
            source.chunk_count = len(chunk_ids)
            state.total_chunks += source.chunk_count
        if last_error is not None:
            source.last_error = last_error
            source.error_count += 1

        self.save()
        return source

    def list_sources(
        self,
        category: Optional[str] = None,
        source_type: Optional[SourceType] = None,
        status: Optional[SourceStatus] = None,
    ) -> list[Source]:
        """List sources with optional filtering."""
        state = self.load()

        sources = list(state.sources.values())

        if category:
            sources = [s for s in sources if s.category == category]
        if source_type:
            sources = [s for s in sources if s.source_type == source_type]
        if status:
            sources = [s for s in sources if s.status == status]

        return sources

    def get_pending_sources(self) -> list[Source]:
        """Get sources that need processing."""
        return self.list_sources(status=SourceStatus.PENDING)

    def get_sources_needing_update(self) -> list[Source]:
        """
        Get sources that may need updating.

        This includes pending sources and sources that haven't
        been synced recently.
        """
        state = self.load()

        needs_update = []
        for source in state.sources.values():
            if source.status == SourceStatus.PENDING:
                needs_update.append(source)
            elif source.status == SourceStatus.ACTIVE:
                # Active sources might need checking for updates
                needs_update.append(source)

        return needs_update

    def import_from_config(self, config: dict[str, dict[str, list[str]]]) -> int:
        """
        Import sources from scraper config format.

        Args:
            config: Dict like {"stylus": {"official_docs": ["url1", "url2"], ...}}

        Returns:
            Number of new sources added
        """
        added = 0

        for category, subcategories in config.items():
            for subcategory, urls in subcategories.items():
                for url in urls:
                    source = self.add_source(
                        url=url,
                        category=category,
                        subcategory=subcategory,
                    )
                    if source.status == SourceStatus.PENDING:
                        added += 1

        return added

    def get_statistics(self) -> dict:
        """Get registry statistics."""
        state = self.load()

        by_category = {}
        by_type = {}
        by_status = {}

        for source in state.sources.values():
            # By category
            by_category[source.category] = by_category.get(source.category, 0) + 1
            # By type
            type_key = source.source_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1
            # By status
            status_key = source.status.value
            by_status[status_key] = by_status.get(status_key, 0) + 1

        return {
            "total_sources": len(state.sources),
            "total_chunks": state.total_chunks,
            "last_sync": state.last_sync,
            "last_full_rebuild": state.last_full_rebuild,
            "by_category": by_category,
            "by_type": by_type,
            "by_status": by_status,
        }

    def mark_sync_complete(self) -> None:
        """Mark that a sync operation completed."""
        state = self.load()
        state.last_sync = datetime.now().isoformat()
        self.save()

    def mark_rebuild_complete(self) -> None:
        """Mark that a full rebuild completed."""
        state = self.load()
        state.last_full_rebuild = datetime.now().isoformat()
        state.last_sync = state.last_full_rebuild
        self.save()

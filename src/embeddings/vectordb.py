"""
ChromaDB vector database management for ARBuilder.

Supports true hybrid search with BM25 + vector retrieval and RRF fusion.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Optional

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from .embedder import EmbeddingAPIError, EmbeddingClient

# Import version manager for version-aware boosting
try:
    from src.utils.version_manager import load_version_config as _load_version_config

    _HAS_VERSION_MANAGER = True
except ImportError:
    _HAS_VERSION_MANAGER = False

load_dotenv()

import logging  # noqa: E402

logger = logging.getLogger(__name__)

console = Console()

# Get project root (assuming this file is in src/embeddings/)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
PROCESSED_DATA_DIR = Path(os.getenv("PROCESSED_DATA_DIR", _PROJECT_ROOT / "data" / "processed"))
CHROMA_DB_DIR = _PROJECT_ROOT / "chroma_db"


class VectorDB:
    """
    ChromaDB-based vector database for ARBuilder.
    """

    def __init__(
        self,
        collection_name: str = "arbbuilder",
        persist_directory: Optional[Path] = None,
        embedding_client: Optional[EmbeddingClient] = None,
    ):
        """
        Initialize the vector database.

        Args:
            collection_name: Name of the ChromaDB collection.
            persist_directory: Directory to persist the database.
            embedding_client: Client for generating embeddings.
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory or CHROMA_DB_DIR
        # Ensure absolute path
        if not self.persist_directory.is_absolute():
            self.persist_directory = self.persist_directory.resolve()
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False),
        )

        # Initialize embedding client (gracefully handle missing credentials)
        if embedding_client is not None:
            self.embedding_client = embedding_client
        else:
            try:
                self.embedding_client = EmbeddingClient()
            except (ValueError, Exception) as e:
                logger.warning(f"EmbeddingClient unavailable: {e}")
                self.embedding_client = None

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # BM25 index for hybrid search (lazy-loaded)
        self._bm25_index: Optional[BM25Okapi] = None
        self._bm25_doc_ids: list[str] = []
        self._bm25_documents: list[str] = []
        self._bm25_metadatas: list[dict] = []

    def ingest_chunks(
        self,
        chunks: list[dict],
        batch_size: int = 50,
        max_workers: int | None = None,
    ) -> int:
        """
        Ingest processed chunks into the vector database.

        Args:
            chunks: List of chunk dictionaries with 'id', 'content', and metadata.
            batch_size: Number of chunks to process per batch (default: 50).
            max_workers: Number of parallel workers for embedding/ingest.
                Defaults to 2 when not provided (reduced to avoid rate limits).

        Returns:
            Number of chunks ingested.
        """
        total_ingested = 0
        failed_batches = 0

        # Deduplicate chunks by ID before batching
        # (scaffold/challenge repos share identical template files → same content hash → same ID)
        seen_ids = set()
        deduped_chunks = []
        for chunk in chunks:
            chunk_id = chunk.get("id", "")
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                deduped_chunks.append(chunk)

        if len(deduped_chunks) < len(chunks):
            console.print(
                f"[yellow]Deduplicated {len(chunks) - len(deduped_chunks)} chunks "
                f"with identical IDs ({len(chunks)} → {len(deduped_chunks)})[/yellow]"
            )

        batches = [
            deduped_chunks[i : i + batch_size] for i in range(0, len(deduped_chunks), batch_size)
        ]
        # Reduced default workers from 5 to 2 to avoid rate limiting
        worker_count = max_workers or 2
        collection_lock = Lock()

        logger.info(
            f"Starting ingestion: {len(chunks)} chunks in {len(batches)} batches "
            f"(batch_size={batch_size}, workers={worker_count})"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
        ) as progress:
            task = progress.add_task("Ingesting chunks...", total=len(chunks))

            def process_batch(batch: list[dict], batch_num: int) -> tuple[int, str | None]:
                """
                Process a single batch of chunks.

                Returns:
                    Tuple of (count ingested, error message if any)
                """
                # Extract data
                ids = [chunk["id"] for chunk in batch]
                documents = [chunk["content"] for chunk in batch]

                # Sanitize metadata - ChromaDB only accepts str, int, float, bool (NOT None)
                def sanitize_metadata(chunk: dict) -> dict:
                    result = {}
                    for k, v in chunk.items():
                        if k in ["id", "content"]:
                            continue
                        if v is None:
                            # Skip None values - ChromaDB doesn't accept them
                            continue
                        if isinstance(v, list):
                            # Convert lists to JSON strings
                            result[k] = json.dumps(v) if v else "[]"
                        elif isinstance(v, dict):
                            # Convert dicts to JSON strings
                            result[k] = json.dumps(v)
                        elif isinstance(v, bool):
                            # Keep booleans as-is
                            result[k] = v
                        elif isinstance(v, (int, float)):
                            # Keep numbers as-is
                            result[k] = v
                        elif isinstance(v, str):
                            # Keep strings as-is
                            result[k] = v
                        else:
                            # Convert other types to string
                            result[k] = str(v)
                    return result

                metadatas = [sanitize_metadata(chunk) for chunk in batch]

                # Generate embeddings with detailed error handling
                try:
                    embeddings = self.embedding_client.embed_batch(documents)
                except EmbeddingAPIError as e:
                    error_msg = f"Batch {batch_num}: Embedding API error - {e}"
                    logger.error(error_msg)
                    return 0, error_msg
                except Exception as e:
                    error_msg = (
                        f"Batch {batch_num}: Unexpected embedding error - {type(e).__name__}: {e}"
                    )
                    logger.error(error_msg)
                    return 0, error_msg

                # Validate embeddings count
                if len(embeddings) != len(documents):
                    error_msg = (
                        f"Batch {batch_num}: Embedding count mismatch - "
                        f"expected {len(documents)}, got {len(embeddings)}"
                    )
                    logger.error(error_msg)
                    return 0, error_msg

                # Upsert to collection (guarded for thread safety)
                # Using upsert instead of add to handle any remaining duplicates gracefully
                try:
                    with collection_lock:
                        self.collection.upsert(
                            ids=ids,
                            embeddings=embeddings,
                            documents=documents,
                            metadatas=metadatas,
                        )
                except Exception as e:
                    error_msg = f"Batch {batch_num}: ChromaDB error - {type(e).__name__}: {e}"
                    logger.error(error_msg)
                    return 0, error_msg

                logger.debug(f"Batch {batch_num} completed: {len(batch)} chunks ingested")
                return len(batch), None

            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                # Submit batches with their index for better error reporting
                futures = {
                    executor.submit(process_batch, batch, i + 1): i + 1
                    for i, batch in enumerate(batches)
                }

                for future in as_completed(futures):
                    batch_num = futures[future]
                    try:
                        ingested, error = future.result()
                        if error:
                            console.print(f"[red]{error}[/red]")
                            failed_batches += 1
                        total_ingested += ingested
                        progress.advance(task, ingested if ingested > 0 else batch_size)
                    except Exception as e:
                        error_msg = (
                            f"Batch {batch_num}: Future execution error - {type(e).__name__}: {e}"
                        )
                        logger.error(error_msg)
                        console.print(f"[red]{error_msg}[/red]")
                        failed_batches += 1
                        progress.advance(task, batch_size)

        # Summary logging
        if failed_batches > 0:
            console.print(
                f"[yellow]Warning: {failed_batches}/{len(batches)} batches failed. "
                f"Check logs for details.[/yellow]"
            )
            logger.warning(
                f"Ingestion completed with errors: {total_ingested}/{len(chunks)} chunks ingested, "
                f"{failed_batches} batches failed"
            )
        else:
            logger.info(f"Ingestion completed successfully: {total_ingested} chunks ingested")

        return total_ingested

    def query(
        self,
        query_text: str,
        n_results: int = 10,
        where: Optional[dict] = None,
        where_document: Optional[dict] = None,
    ) -> dict:
        """
        Query the vector database.

        Args:
            query_text: Query text.
            n_results: Number of results to return.
            where: Metadata filter.
            where_document: Document content filter.

        Returns:
            Query results with ids, documents, metadatas, and distances.
        """
        # Generate query embedding
        if self.embedding_client is None:
            raise RuntimeError("EmbeddingClient not available. Set OPENROUTER_API_KEY in .env.")
        query_embedding = self.embedding_client.embed(query_text)

        # Query collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=["documents", "metadatas", "distances"],
        )

        return results

    def hybrid_search(
        self,
        query_text: str,
        n_results: int = 10,
        where: Optional[dict] = None,
        alpha: float = 0.5,
        category_boosts: Optional[dict[str, float]] = None,
        use_bm25: bool = True,
        target_version: Optional[str] = None,
    ) -> dict:
        """
        Perform hybrid search using vector similarity + BM25 + metadata boosting.

        Args:
            query_text: Query text.
            n_results: Number of results to return.
            where: Metadata filter.
            alpha: Weight between BM25 (1.0) and vector (0.0). Default 0.5 for balanced.
            category_boosts: Dict mapping category names to boost
                multipliers (e.g., {"stylus": 1.3}).
            use_bm25: Whether to use BM25 scoring (if False, falls back to simple keyword matching).
            target_version: Target stylus-sdk version for version-aware scoring.
                          Matching versions get boosted, deprecated versions get penalized.

        Returns:
            Query results with combined scoring.
        """
        # Get larger candidate set from vector search for reranking
        candidate_multiplier = 3 if use_bm25 else 2
        vector_results = self.query(
            query_text=query_text,
            n_results=n_results * candidate_multiplier,
            where=where,
        )

        # Check if we have any results
        if not vector_results["ids"] or len(vector_results["ids"][0]) == 0:
            return {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
            }

        documents = vector_results["documents"][0]
        metadatas = vector_results["metadatas"][0]
        distances = vector_results["distances"][0]

        # Convert vector distances to similarity scores (0-1, higher is better)
        # Cosine distance: 0 = identical, 2 = opposite
        vector_scores = [max(0.0, 1.0 - (d / 2.0)) for d in distances]

        # Compute BM25 scores if enabled
        if use_bm25:
            try:
                from rank_bm25 import BM25Okapi

                # Tokenize documents
                tokenized_docs = [doc.lower().split() for doc in documents]
                query_tokens = query_text.lower().split()

                # Compute BM25 scores
                bm25 = BM25Okapi(tokenized_docs)
                bm25_scores = bm25.get_scores(query_tokens)

                # Normalize BM25 scores to 0-1 range
                if len(bm25_scores) > 0:
                    max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
                    bm25_normalized = [score / max_bm25 for score in bm25_scores]
                else:
                    bm25_normalized = [0.0] * len(documents)
            except ImportError:
                logger.warning("rank_bm25 not installed. Falling back to simple keyword matching.")
                use_bm25 = False

        # Fallback to simple keyword matching if BM25 unavailable
        if not use_bm25:
            keywords = [w.lower() for w in query_text.split() if len(w) > 3]
            keyword_scores = []
            for doc in documents:
                doc_lower = doc.lower()
                keyword_score = sum(1 for kw in keywords if kw in doc_lower)
                keyword_scores.append(keyword_score)

            # Normalize keyword scores
            max_kw = max(keyword_scores) if max(keyword_scores) > 0 else 1.0
            bm25_normalized = [score / max_kw for score in keyword_scores]

        # Combine vector and BM25 scores with alpha weighting
        combined_scores = [
            alpha * bm25_normalized[i] + (1 - alpha) * vector_scores[i]
            for i in range(len(documents))
        ]

        # Apply metadata boosting (category + version)
        if category_boosts or target_version:
            boosted_scores = []
            for i, score in enumerate(combined_scores):
                boost = self._calculate_metadata_boost(
                    metadatas[i],
                    query_text,
                    category_boosts or {},
                    target_version=target_version,
                )
                boosted_scores.append(score * boost)
            combined_scores = boosted_scores

        # Create scored results
        scored_results = [
            {
                "id": vector_results["ids"][0][i],
                "document": documents[i],
                "metadata": metadatas[i],
                "distance": distances[i],
                "vector_score": vector_scores[i],
                "bm25_score": bm25_normalized[i],
                "combined_score": combined_scores[i],
            }
            for i in range(len(documents))
        ]

        # Sort by combined score (descending - higher is better)
        scored_results.sort(key=lambda x: x["combined_score"], reverse=True)
        top_results = scored_results[:n_results]

        # Format as ChromaDB-style results
        return {
            "ids": [[r["id"] for r in top_results]],
            "documents": [[r["document"] for r in top_results]],
            "metadatas": [[r["metadata"] for r in top_results]],
            "distances": [[r["distance"] for r in top_results]],
            "scores": [[r["combined_score"] for r in top_results]],  # Include combined scores
        }

    @staticmethod
    def _get_deprecated_sdk_versions() -> set[str]:
        """Get deprecated SDK versions from version_manager config."""
        if not _HAS_VERSION_MANAGER:
            return set()
        try:
            config = _load_version_config()
            return {
                v
                for v, info in config.get("versions", {}).items()
                if info.get("status") == "deprecated"
            }
        except Exception:
            return set()

    def _calculate_metadata_boost(
        self,
        metadata: dict,
        query: str,
        category_boosts: dict[str, float],
        target_version: Optional[str] = None,
    ) -> float:
        """
        Calculate boost factor based on metadata.

        Args:
            metadata: Chunk metadata.
            query: Search query.
            category_boosts: Dict mapping category names to boost multipliers.
            target_version: Target SDK version for version-aware scoring.

        Returns:
            Boost multiplier (1.0 = no boost, >1.0 = boost, <1.0 = penalty).
        """
        boost = 1.0
        query_lower = query.lower()

        # Category boost - primary factor
        category = metadata.get("category", "")
        if category and category in category_boosts:
            boost *= category_boosts[category]
            logger.debug(f"Applied category boost for '{category}': {category_boosts[category]}")

        # Source type boost - prefer documentation for conceptual queries
        if any(kw in query_lower for kw in ["what", "how", "why", "explain", "understand"]):
            source = metadata.get("source", "")
            if source == "documentation":
                boost *= 1.15
                logger.debug("Applied documentation boost for conceptual query")

        # Code-specific boosts
        if any(kw in query_lower for kw in ["function", "impl", "example", "code", "fn", "method"]):
            source = metadata.get("source", "")
            language = metadata.get("language", "")
            if source == "github" or language in ["rs", "sol", "ts", "js"]:
                boost *= 1.15
                logger.debug("Applied code source boost")

        # Version-aware scoring (mirrors TS applyVersionScoring)
        if target_version:
            chunk_version = metadata.get("sdk_version", "")
            if chunk_version and chunk_version not in ("", "N/A"):
                # Parse major.minor for comparison
                target_mm = self._parse_major_minor(target_version)
                chunk_mm = self._parse_major_minor(chunk_version)

                if target_mm and chunk_mm:
                    if chunk_mm == target_mm:
                        # Exact major.minor match → 1.2x boost
                        boost *= 1.2
                        logger.debug(f"Version match boost for {chunk_version}")
                    elif chunk_version in self._get_deprecated_sdk_versions():
                        # Deprecated version → 0.8x penalty
                        boost *= 0.8
                        logger.debug(f"Deprecated version penalty for {chunk_version}")

                # Dual-chunk awareness: modernized chunks are copies of
                # 0.9.x originals upgraded to 0.10.0 via regex transforms.
                # When target is 0.9.x, prefer the real 0.9.x original.
                # When target is 0.10.x, boost the modernized copy.
                if metadata.get("modernized"):
                    if chunk_mm == target_mm:
                        # Modernized chunk matches target → boost it
                        boost *= 1.1
                        logger.debug("Modernized chunk boost applied (matches target)")
                    else:
                        # Modernized chunk doesn't match target (e.g., target=0.9,
                        # chunk was upgraded to 0.10) → skip the version-match
                        # boost that was already applied above
                        pass

        return boost

    @staticmethod
    def _parse_major_minor(version: str) -> Optional[tuple[int, int]]:
        """Parse a version string into (major, minor) tuple."""
        try:
            parts = version.lstrip("^~>=<").split(".")
            return (int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return None

    def get_stats(self) -> dict:
        """Get collection statistics."""
        return {
            "collection_name": self.collection_name,
            "count": self.collection.count(),
            "persist_directory": str(self.persist_directory),
        }

    def delete_by_ids(self, ids: list[str]) -> int:
        """
        Delete chunks by their IDs.

        Args:
            ids: List of chunk IDs to delete.

        Returns:
            Number of chunks deleted.
        """
        if not ids:
            return 0

        try:
            self.collection.delete(ids=ids)
            return len(ids)
        except Exception as e:
            console.print(f"[red]Delete error: {e}[/red]")
            return 0

    def delete_by_source(self, source_url: str) -> int:
        """
        Delete all chunks from a specific source URL.

        Args:
            source_url: The source URL to delete chunks for.

        Returns:
            Number of chunks deleted.
        """
        # Query for all chunks with this source URL
        results = self.collection.get(
            where={"$or": [{"url": source_url}, {"repo_url": source_url}]},
            include=[],  # Only need IDs
        )

        if not results["ids"]:
            return 0

        return self.delete_by_ids(results["ids"])

    def delete_collection(self):
        """Delete the collection."""
        self.client.delete_collection(self.collection_name)
        console.print(f"[yellow]Deleted collection: {self.collection_name}[/yellow]")


def ingest_from_file(
    input_file: Optional[Path] = None,
    collection_name: str = "arbbuilder",
    batch_size: int = 50,
) -> dict:
    """
    Ingest processed chunks from a JSON file.

    Args:
        input_file: Path to processed chunks JSON. If None, uses latest.
        collection_name: ChromaDB collection name.
        batch_size: Batch size for ingestion.

    Returns:
        Ingestion statistics.
    """
    # Find input file
    if input_file is None:
        files = list(PROCESSED_DATA_DIR.glob("processed_chunks_*.json"))
        if not files:
            console.print("[red]No processed chunks file found![/red]")
            return {}
        input_file = max(files, key=lambda p: p.stat().st_mtime)

    console.print(f"[blue]Loading chunks from: {input_file}[/blue]")

    with open(input_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    console.print(f"[blue]Loaded {len(chunks)} chunks[/blue]")

    # Initialize database and ingest
    db = VectorDB(collection_name=collection_name)

    console.print(f"\n[bold]Ingesting into ChromaDB collection: {collection_name}[/bold]")
    ingested = db.ingest_chunks(chunks, batch_size=batch_size)

    stats = db.get_stats()
    stats["ingested"] = ingested

    console.print(f"\n[green]Ingested {ingested} chunks[/green]")
    console.print(f"[green]Total in collection: {stats['count']}[/green]")

    return stats


def main():
    """Entry point for ingestion."""
    import argparse

    parser = argparse.ArgumentParser(description="ARBuilder Vector Database Ingestion")
    parser.add_argument(
        "--collection",
        type=str,
        default="arbbuilder",
        help="ChromaDB collection name (default: arbbuilder)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for ingestion (default: 50)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing collection before ingesting",
    )

    args = parser.parse_args()

    if args.reset:
        db = VectorDB(collection_name=args.collection)
        db.delete_collection()

    ingest_from_file(
        collection_name=args.collection,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()

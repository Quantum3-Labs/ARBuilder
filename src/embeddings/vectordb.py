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
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .embedder import EmbeddingClient, EmbeddingAPIError

load_dotenv()

import logging

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

        # Initialize embedding client
        self.embedding_client = embedding_client or EmbeddingClient()

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
        batches = [
            chunks[i:i + batch_size] for i in range(0, len(chunks), batch_size)
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
                    error_msg = f"Batch {batch_num}: Unexpected embedding error - {type(e).__name__}: {e}"
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

                # Add to collection (guarded for thread safety)
                try:
                    with collection_lock:
                        self.collection.add(
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
                        error_msg = f"Batch {batch_num}: Future execution error - {type(e).__name__}: {e}"
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
    ) -> dict:
        """
        Perform hybrid search (vector + keyword).

        ChromaDB supports basic keyword filtering via where_document.
        For more advanced hybrid search, we combine vector results
        with keyword matching.

        Args:
            query_text: Query text.
            n_results: Number of results to return.
            where: Metadata filter.

        Returns:
            Query results.
        """
        # Get more results from vector search
        vector_results = self.query(
            query_text=query_text,
            n_results=n_results * 2,
            where=where,
        )

        # Extract keywords from query (simple approach)
        keywords = [w.lower() for w in query_text.split() if len(w) > 3]

        # Score results based on keyword presence
        scored_results = []
        for i in range(len(vector_results["ids"][0])):
            doc = vector_results["documents"][0][i].lower()
            distance = vector_results["distances"][0][i]

            # Count keyword matches
            keyword_score = sum(1 for kw in keywords if kw in doc)

            # Combined score (lower distance is better, higher keyword score is better)
            combined_score = distance - (keyword_score * 0.1)

            scored_results.append({
                "id": vector_results["ids"][0][i],
                "document": vector_results["documents"][0][i],
                "metadata": vector_results["metadatas"][0][i],
                "distance": distance,
                "keyword_score": keyword_score,
                "combined_score": combined_score,
            })

        # Sort by combined score and take top n
        scored_results.sort(key=lambda x: x["combined_score"])
        top_results = scored_results[:n_results]

        # Format as ChromaDB-style results
        return {
            "ids": [[r["id"] for r in top_results]],
            "documents": [[r["document"] for r in top_results]],
            "metadatas": [[r["metadata"] for r in top_results]],
            "distances": [[r["distance"] for r in top_results]],
        }

    def _build_bm25_index(self, force_rebuild: bool = False) -> None:
        """
        Build or rebuild the BM25 index from all documents in the collection.

        Args:
            force_rebuild: Force rebuild even if index exists.
        """
        if self._bm25_index is not None and not force_rebuild:
            return

        logger.info("Building BM25 index for hybrid search...")

        # Fetch all documents from collection
        all_docs = self.collection.get(include=["documents", "metadatas"])

        if not all_docs["ids"]:
            logger.warning("No documents in collection for BM25 index")
            self._bm25_index = None
            return

        self._bm25_doc_ids = all_docs["ids"]
        self._bm25_documents = all_docs["documents"]
        self._bm25_metadatas = all_docs["metadatas"]

        # Tokenize documents for BM25
        tokenized_docs = [
            self._tokenize(doc) for doc in self._bm25_documents
        ]

        self._bm25_index = BM25Okapi(tokenized_docs)
        logger.info(f"BM25 index built with {len(self._bm25_doc_ids)} documents")

    def _tokenize(self, text: str) -> list[str]:
        """
        Tokenize text for BM25 indexing.

        Args:
            text: Text to tokenize.

        Returns:
            List of tokens.
        """
        import re

        # Lowercase and split on non-alphanumeric
        tokens = re.findall(r'\b[a-z0-9_]+\b', text.lower())
        # Filter short tokens
        return [t for t in tokens if len(t) > 2]

    def _bm25_search(
        self,
        query_text: str,
        n_results: int = 20,
    ) -> list[dict]:
        """
        Search using BM25 index.

        Args:
            query_text: Query text.
            n_results: Number of results.

        Returns:
            List of results with id, document, metadata, bm25_score.
        """
        self._build_bm25_index()

        if self._bm25_index is None:
            return []

        query_tokens = self._tokenize(query_text)

        if not query_tokens:
            return []

        # Get BM25 scores for all documents
        scores = self._bm25_index.get_scores(query_tokens)

        # Create scored results
        results = []
        for i, score in enumerate(scores):
            if score > 0:  # Only include documents with positive scores
                results.append({
                    "id": self._bm25_doc_ids[i],
                    "document": self._bm25_documents[i],
                    "metadata": self._bm25_metadatas[i],
                    "bm25_score": float(score),
                })

        # Sort by score descending
        results.sort(key=lambda x: x["bm25_score"], reverse=True)

        return results[:n_results]

    def _rrf_fusion(
        self,
        bm25_results: list[dict],
        vector_results: dict,
        k: int = 60,
    ) -> list[dict]:
        """
        Reciprocal Rank Fusion to combine BM25 and vector results.

        RRF score = sum(1 / (k + rank)) for each ranking.

        Args:
            bm25_results: Results from BM25 search.
            vector_results: Results from vector search (ChromaDB format).
            k: RRF constant (default 60).

        Returns:
            Fused results sorted by RRF score.
        """
        rrf_scores: dict[str, float] = {}
        doc_data: dict[str, dict] = {}

        # Process BM25 results
        for rank, result in enumerate(bm25_results, start=1):
            doc_id = result["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank)
            doc_data[doc_id] = {
                "document": result["document"],
                "metadata": result["metadata"],
                "bm25_rank": rank,
                "bm25_score": result["bm25_score"],
            }

        # Process vector results
        if vector_results["ids"] and vector_results["ids"][0]:
            for rank, (doc_id, doc, meta, dist) in enumerate(
                zip(
                    vector_results["ids"][0],
                    vector_results["documents"][0],
                    vector_results["metadatas"][0],
                    vector_results["distances"][0],
                ),
                start=1,
            ):
                rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank)
                if doc_id not in doc_data:
                    doc_data[doc_id] = {
                        "document": doc,
                        "metadata": meta,
                    }
                doc_data[doc_id]["vector_rank"] = rank
                doc_data[doc_id]["vector_distance"] = dist

        # Create fused results
        fused_results = []
        for doc_id, rrf_score in rrf_scores.items():
            data = doc_data[doc_id]
            fused_results.append({
                "id": doc_id,
                "document": data["document"],
                "metadata": data["metadata"],
                "rrf_score": rrf_score,
                "bm25_rank": data.get("bm25_rank"),
                "bm25_score": data.get("bm25_score"),
                "vector_rank": data.get("vector_rank"),
                "vector_distance": data.get("vector_distance"),
            })

        # Sort by RRF score descending
        fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)

        return fused_results

    def hybrid_search_v2(
        self,
        query_text: str,
        n_results: int = 10,
        alpha: float = 0.5,
        where: Optional[dict] = None,
    ) -> dict:
        """
        True hybrid search: BM25 retrieval + vector retrieval + RRF fusion.

        This is the improved hybrid search that uses BM25 for actual retrieval
        (not just reranking) and combines results using Reciprocal Rank Fusion.

        Args:
            query_text: Query text.
            n_results: Number of results to return.
            alpha: Weight for vector vs BM25 (0.5 = equal, >0.5 = more vector).
            where: Metadata filter for vector search.

        Returns:
            Query results in ChromaDB format with additional ranking metadata.
        """
        # 1. BM25 retrieval (get more than needed for fusion)
        bm25_results = self._bm25_search(query_text, n_results * 2)

        # 2. Vector retrieval (get more than needed for fusion)
        vector_results = self.query(
            query_text=query_text,
            n_results=n_results * 2,
            where=where,
        )

        # 3. RRF fusion
        fused = self._rrf_fusion(bm25_results, vector_results, k=60)

        # Take top n_results
        top_results = fused[:n_results]

        # Format as ChromaDB-style results with extra metadata
        return {
            "ids": [[r["id"] for r in top_results]],
            "documents": [[r["document"] for r in top_results]],
            "metadatas": [[r["metadata"] for r in top_results]],
            "distances": [[r.get("vector_distance", 0.5) for r in top_results]],
            "rrf_scores": [[r["rrf_score"] for r in top_results]],
            "bm25_ranks": [[r.get("bm25_rank") for r in top_results]],
            "vector_ranks": [[r.get("vector_rank") for r in top_results]],
        }

    def rebuild_bm25_index(self) -> None:
        """Force rebuild the BM25 index."""
        self._build_bm25_index(force_rebuild=True)

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

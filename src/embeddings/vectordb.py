"""
ChromaDB vector database management for ARBuilder.
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
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .embedder import EmbeddingClient

load_dotenv()

console = Console()

PROCESSED_DATA_DIR = Path(os.getenv("PROCESSED_DATA_DIR", "data/processed"))
CHROMA_DB_DIR = Path("chroma_db")


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

    def ingest_chunks(
        self,
        chunks: list[dict],
        batch_size: int = 100,
        max_workers: int | None = None,
    ) -> int:
        """
        Ingest processed chunks into the vector database.

        Args:
            chunks: List of chunk dictionaries with 'id', 'content', and metadata.
            batch_size: Number of chunks to process per batch.
            max_workers: Number of parallel workers for embedding/ingest.
                Defaults to 5 when not provided.

        Returns:
            Number of chunks ingested.
        """
        total_ingested = 0
        batches = [
            chunks[i:i + batch_size] for i in range(0, len(chunks), batch_size)
        ]
        worker_count = max_workers or 5
        collection_lock = Lock()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
        ) as progress:
            task = progress.add_task("Ingesting chunks...", total=len(chunks))

            def process_batch(batch: list[dict]) -> int:
                # Extract data
                ids = [chunk["id"] for chunk in batch]
                documents = [chunk["content"] for chunk in batch]
                metadatas = [
                    {k: v for k, v in chunk.items() if k not in ["id", "content"]}
                    for chunk in batch
                ]

                # Generate embeddings
                try:
                    embeddings = self.embedding_client.embed_batch(documents)
                except Exception as e:
                    console.print(f"[red]Error generating embeddings: {e}[/red]")
                    return 0

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
                    console.print(f"[red]Error adding to collection: {e}[/red]")
                    return 0

                return len(batch)

            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = [executor.submit(process_batch, batch) for batch in batches]

                for future in as_completed(futures):
                    ingested = future.result()
                    total_ingested += ingested
                    progress.advance(task, ingested)

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

    def get_stats(self) -> dict:
        """Get collection statistics."""
        return {
            "collection_name": self.collection_name,
            "count": self.collection.count(),
            "persist_directory": str(self.persist_directory),
        }

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

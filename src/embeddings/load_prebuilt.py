"""
Load pre-built embeddings into ChromaDB.

This script loads embeddings from the portable NPZ format
into a local ChromaDB instance, skipping the embedding generation step.

Usage:
    python -m src.embeddings.load_prebuilt

    # Or specify a specific file:
    python -m src.embeddings.load_prebuilt --input data/embeddings/embeddings_v1.0.0.npz
"""

import json
from pathlib import Path
from typing import Optional

import chromadb
import numpy as np
from chromadb.config import Settings
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
EMBEDDINGS_DIR = PROJECT_ROOT / "data" / "embeddings"
CHROMA_DB_DIR = PROJECT_ROOT / "chroma_db"


def find_latest_embeddings_file() -> Path:
    """Find the most recent embeddings file."""
    files = list(EMBEDDINGS_DIR.glob("embeddings_*.npz"))
    if not files:
        raise FileNotFoundError(
            "No embeddings file found. Download one first:\n"
            "  npx tsx scripts/download-chunks.ts --embeddings"
        )
    return max(files, key=lambda p: p.stat().st_mtime)


def load_prebuilt(
    input_file: Optional[Path] = None,
    collection_name: str = "arbbuilder",
    reset: bool = False,
    batch_size: int = 500,
) -> dict:
    """
    Load pre-built embeddings into ChromaDB.

    Args:
        input_file: Path to embeddings NPZ file. If None, uses latest.
        collection_name: ChromaDB collection name.
        reset: If True, delete existing collection first.
        batch_size: Number of items to add per batch.

    Returns:
        Statistics about the import.
    """
    # Find input file
    if input_file is None:
        input_file = find_latest_embeddings_file()

    console.print(f"[blue]Loading embeddings from: {input_file}[/blue]")

    # Load NPZ file
    data = np.load(input_file, allow_pickle=True)

    ids = data["ids"]
    embeddings = data["embeddings"]
    documents = data["documents"]
    metadatas_json = data["metadatas"][0]
    model = data["model"][0]
    dimensions = int(data["dimensions"][0])
    chunk_count = int(data["chunk_count"][0])
    created_at = data["created_at"][0]

    # Parse metadatas
    metadatas = json.loads(metadatas_json)

    console.print(f"[blue]Loaded {chunk_count} embeddings[/blue]")
    console.print(f"[blue]Model: {model}[/blue]")
    console.print(f"[blue]Dimensions: {dimensions}[/blue]")
    console.print(f"[blue]Created: {created_at}[/blue]")

    # Initialize ChromaDB
    CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(CHROMA_DB_DIR),
        settings=Settings(anonymized_telemetry=False),
    )

    # Handle existing collection
    if reset:
        try:
            client.delete_collection(collection_name)
            console.print(f"[yellow]Deleted existing collection: {collection_name}[/yellow]")
        except Exception:
            pass

    # Get or create collection
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    existing_count = collection.count()
    if existing_count > 0:
        console.print(f"[yellow]Collection has {existing_count} existing items[/yellow]")

    # Sanitize metadata for ChromaDB
    def sanitize_metadata(meta: dict) -> dict:
        result = {}
        for k, v in meta.items():
            if k == "id":  # Skip id, it's stored separately
                continue
            if isinstance(v, list):
                result[k] = json.dumps(v) if v else ""
            elif isinstance(v, dict):
                result[k] = json.dumps(v)
            elif v is None or isinstance(v, (str, int, float, bool)):
                result[k] = v
            else:
                result[k] = str(v)
        return result

    # Add to collection in batches
    console.print(f"\n[bold]Adding {chunk_count} items to ChromaDB...[/bold]")

    added = 0
    skipped = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading...", total=chunk_count)

        for i in range(0, chunk_count, batch_size):
            batch_end = min(i + batch_size, chunk_count)

            batch_ids = [str(id_) for id_ in ids[i:batch_end]]
            batch_embeddings = embeddings[i:batch_end].tolist()
            batch_documents = [str(doc) for doc in documents[i:batch_end]]
            batch_metadatas = [sanitize_metadata(m) for m in metadatas[i:batch_end]]

            try:
                # Use upsert to handle duplicates
                collection.upsert(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_documents,
                    metadatas=batch_metadatas,
                )
                added += len(batch_ids)
            except Exception as e:
                console.print(f"\n[red]Batch {i // batch_size} failed: {e}[/red]")
                skipped += len(batch_ids)

            progress.advance(task, batch_end - i)

    # Final stats
    final_count = collection.count()

    stats = {
        "input_file": str(input_file),
        "collection": collection_name,
        "model": model,
        "dimensions": dimensions,
        "total_chunks": chunk_count,
        "added": added,
        "skipped": skipped,
        "final_count": final_count,
    }

    console.print(f"\n[green]Import complete![/green]")
    console.print(f"  Collection: {collection_name}")
    console.print(f"  Total in collection: {final_count}")
    console.print(f"  Added: {added}")
    if skipped:
        console.print(f"  [yellow]Skipped: {skipped}[/yellow]")

    return stats


def main():
    """Entry point for loading pre-built embeddings."""
    import argparse

    parser = argparse.ArgumentParser(description="Load pre-built embeddings into ChromaDB")
    parser.add_argument(
        "--input",
        type=str,
        help="Path to embeddings NPZ file (default: latest)",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="arbbuilder",
        help="ChromaDB collection name (default: arbbuilder)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing collection before loading",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Batch size for ChromaDB inserts (default: 500)",
    )

    args = parser.parse_args()

    input_file = Path(args.input) if args.input else None

    load_prebuilt(
        input_file=input_file,
        collection_name=args.collection,
        reset=args.reset,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()

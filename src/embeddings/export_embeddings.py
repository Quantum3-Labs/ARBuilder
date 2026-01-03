"""
Export embeddings in a portable format for distribution.

Generates embeddings for all chunks and saves them in a format
that can be loaded into any ChromaDB version or other vector DBs.

Usage:
    OPENROUTER_API_KEY=xxx python -m src.embeddings.export_embeddings

Output:
    data/embeddings/embeddings_<timestamp>.npz
"""

import json
import os
from datetime import datetime
from pathlib import Path

import numpy as np
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .embedder import EmbeddingClient

console = Console()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EMBEDDINGS_DIR = PROJECT_ROOT / "data" / "embeddings"


def find_latest_chunks_file() -> Path:
    """Find the most recent processed chunks file."""
    files = list(PROCESSED_DIR.glob("processed_chunks_*.json"))
    if not files:
        raise FileNotFoundError("No processed chunks file found")
    return max(files, key=lambda p: p.stat().st_mtime)


def export_embeddings(
    input_file: Path | None = None,
    output_file: Path | None = None,
    batch_size: int = 50,
    max_workers: int = 2,
    dry_run: bool = False,
    limit: int | None = None,
) -> Path:
    """
    Generate embeddings and export to portable format.

    Args:
        input_file: Path to processed chunks JSON. If None, uses latest.
        output_file: Path for output NPZ file. If None, auto-generated.
        batch_size: Batch size for embedding API calls.
        max_workers: Number of parallel workers.
        dry_run: If True, use fake embeddings (no API calls).
        limit: Limit number of chunks to process (for testing).

    Returns:
        Path to the generated embeddings file.
    """
    # Find input file
    if input_file is None:
        input_file = find_latest_chunks_file()

    console.print(f"[blue]Loading chunks from: {input_file}[/blue]")

    with open(input_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    # Apply limit if specified
    if limit:
        chunks = chunks[:limit]
        console.print(f"[yellow]Limited to {limit} chunks (dry run/test mode)[/yellow]")

    console.print(f"[blue]Loaded {len(chunks)} chunks[/blue]")

    if dry_run:
        console.print(f"[yellow]DRY RUN MODE - using random embeddings[/yellow]")
        dimensions = 768  # Standard embedding dimension
        model_name = "dry-run/fake-embeddings"
    else:
        # Initialize embedding client
        client = EmbeddingClient()
        console.print(f"[blue]Using model: {client.model}[/blue]")

        # Get embedding dimension
        console.print("[dim]Testing embedding dimension...[/dim]")
        test_embedding = client.embed("test")
        dimensions = len(test_embedding)
        model_name = client.model

    console.print(f"[blue]Embedding dimensions: {dimensions}[/blue]")

    # Prepare data
    ids = []
    documents = []
    metadatas = []

    for chunk in chunks:
        ids.append(chunk["id"])
        documents.append(chunk["content"])
        # Store all metadata except content
        metadata = {k: v for k, v in chunk.items() if k not in ["content"]}
        metadatas.append(metadata)

    # Generate embeddings with progress
    console.print(f"\n[bold]Generating embeddings for {len(chunks)} chunks...[/bold]")

    all_embeddings = []
    failed_indices = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating embeddings...", total=len(documents))

        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            batch_indices = list(range(i, min(i + batch_size, len(documents))))

            try:
                if dry_run:
                    # Generate random embeddings for testing
                    import random
                    embeddings = [[random.uniform(-1, 1) for _ in range(dimensions)] for _ in batch]
                else:
                    embeddings = client.embed_batch(batch, batch_size=batch_size)
                all_embeddings.extend(embeddings)
                progress.advance(task, len(batch))
            except Exception as e:
                console.print(f"\n[red]Batch {i // batch_size} failed: {e}[/red]")
                # Add zero embeddings for failed items
                for _ in batch:
                    all_embeddings.append([0.0] * dimensions)
                    failed_indices.append(len(all_embeddings) - 1)
                progress.advance(task, len(batch))

    if not dry_run:
        client.close()

    # Convert to numpy arrays
    embeddings_array = np.array(all_embeddings, dtype=np.float32)
    ids_array = np.array(ids, dtype=object)
    documents_array = np.array(documents, dtype=object)

    # Prepare output
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = EMBEDDINGS_DIR / f"embeddings_{timestamp}.npz"

    # Save metadata as JSON string (numpy can't store dicts directly)
    metadatas_json = json.dumps(metadatas)

    # Save to compressed numpy format
    np.savez_compressed(
        output_file,
        ids=ids_array,
        embeddings=embeddings_array,
        documents=documents_array,
        metadatas=np.array([metadatas_json], dtype=object),
        model=np.array([model_name], dtype=object),
        dimensions=np.array([dimensions], dtype=np.int32),
        created_at=np.array([datetime.now().isoformat()], dtype=object),
        chunk_count=np.array([len(chunks)], dtype=np.int32),
        failed_count=np.array([len(failed_indices)], dtype=np.int32),
    )

    # Get file size
    file_size_mb = output_file.stat().st_size / (1024 * 1024)

    console.print(f"\n[green]Embeddings exported successfully![/green]")
    console.print(f"  File: {output_file}")
    console.print(f"  Size: {file_size_mb:.1f} MB")
    console.print(f"  Chunks: {len(chunks)}")
    console.print(f"  Dimensions: {dimensions}")
    console.print(f"  Model: {model_name}")
    if failed_indices:
        console.print(f"  [yellow]Failed: {len(failed_indices)} chunks[/yellow]")

    return output_file


def main():
    """Entry point for embedding export."""
    import argparse

    parser = argparse.ArgumentParser(description="Export embeddings to portable format")
    parser.add_argument(
        "--input",
        type=str,
        help="Path to processed chunks JSON (default: latest)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path for output NPZ file (default: auto-generated)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for embedding API (default: 50)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use fake embeddings (no API calls, for testing)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of chunks to process (for testing)",
    )

    args = parser.parse_args()

    input_file = Path(args.input) if args.input else None
    output_file = Path(args.output) if args.output else None

    export_embeddings(
        input_file=input_file,
        output_file=output_file,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()

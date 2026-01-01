#!/usr/bin/env python3
"""
Ingest M3 processed chunks into ChromaDB.
Supports resume functionality to continue from where it left off.

Usage:
    python scripts/ingest_m3.py          # Fresh start (deletes existing collection)
    python scripts/ingest_m3.py --resume # Resume from current collection count
"""

import argparse
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from functools import partial

# Enable unbuffered output
print = partial(print, flush=True)

import chromadb
from chromadb.config import Settings
import httpx
from dotenv import load_dotenv

load_dotenv()

# Configuration
PROCESSED_DATA_DIR = Path("data/processed")
CHROMA_DB_DIR = Path("chroma_db")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
EMBEDDING_MODEL = os.getenv("DEFAULT_EMBEDDING", "google/gemini-embedding-001")


def get_embeddings_with_retry(texts: list[str], max_retries: int = 3) -> list[list[float]]:
    """Generate embeddings with retry logic for resilience."""
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is required")

    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=180.0) as client:
                response = client.post(
                    "https://openrouter.ai/api/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": EMBEDDING_MODEL,
                        "input": texts,
                    },
                )

                if response.status_code != 200:
                    if response.status_code == 429:  # Rate limited
                        import time
                        wait = 2 ** attempt
                        print(f"Rate limited, waiting {wait}s...")
                        time.sleep(wait)
                        continue
                    print(f"Error: {response.status_code} - {response.text}")
                    raise Exception(f"Embedding API error: {response.status_code}")

                data = response.json()
                return [item["embedding"] for item in data["data"]]

        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                import time
                wait = 2 ** attempt
                print(f"Timeout, retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise

    raise Exception("Max retries exceeded")


def get_embeddings(texts: list[str], batch_size: int = 50) -> list[list[float]]:
    """Generate embeddings using OpenRouter API with batching."""
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embeddings = get_embeddings_with_retry(batch)
        all_embeddings.extend(embeddings)

    return all_embeddings


def main():
    parser = argparse.ArgumentParser(description="Ingest M3 data into ChromaDB")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from current collection count instead of starting fresh",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=None,
        help="Start from specific index (overrides --resume)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for embedding generation (default: 50)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("ARBuilder M3 Data Ingestion")
    print("=" * 60)

    # Find latest processed file
    files = list(PROCESSED_DATA_DIR.glob("processed_chunks_*.json"))
    if not files:
        print("ERROR: No processed chunks found in data/processed/")
        sys.exit(1)

    latest_file = max(files, key=lambda p: p.stat().st_mtime)
    print(f"\nLoading: {latest_file}")

    with open(latest_file, "r") as f:
        chunks = json.load(f)

    print(f"Loaded {len(chunks):,} chunks")

    # Initialize ChromaDB
    CHROMA_DB_DIR.mkdir(exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(CHROMA_DB_DIR),
        settings=Settings(anonymized_telemetry=False),
    )

    # Determine start index
    if args.start_index is not None:
        start_index = args.start_index
        collection = client.get_or_create_collection(
            name="arbbuilder",
            metadata={"hnsw:space": "cosine"},
        )
    elif args.resume:
        collection = client.get_or_create_collection(
            name="arbbuilder",
            metadata={"hnsw:space": "cosine"},
        )
        start_index = collection.count()
        print(f"Resuming from index: {start_index:,}")
    else:
        # Fresh start - delete and recreate collection
        try:
            client.delete_collection("arbbuilder")
            print("Deleted existing collection")
        except Exception:
            pass
        collection = client.get_or_create_collection(
            name="arbbuilder",
            metadata={"hnsw:space": "cosine"},
        )
        start_index = 0

    print(f"Collection ready: {collection.name}")
    print(f"Current count: {collection.count():,}")

    # Check if already complete
    if start_index >= len(chunks):
        print(f"\nAll {len(chunks):,} chunks already ingested!")
        return

    remaining_chunks = chunks[start_index:]
    print(f"Remaining to ingest: {len(remaining_chunks):,}")

    # Ingest in batches
    batch_size = args.batch_size
    total_ingested = 0
    errors = 0

    print(f"\nStarting ingestion (batch size {batch_size})...")
    print("-" * 60)

    start_time = datetime.now()

    for i in range(0, len(remaining_chunks), batch_size):
        batch = remaining_chunks[i:i + batch_size]

        ids = [c["id"] for c in batch]
        documents = [c["content"] for c in batch]
        metadatas = []
        for c in batch:
            meta = {k: v for k, v in c.items() if k not in ["id", "content"]}
            # Convert non-string values
            for key, value in meta.items():
                if isinstance(value, (list, dict)):
                    meta[key] = json.dumps(value)
                elif value is None:
                    meta[key] = ""
            metadatas.append(meta)

        try:
            # Generate embeddings
            embeddings = get_embeddings(documents, batch_size=batch_size)

            # Add to collection
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

            total_ingested += len(batch)

            # Progress update every 500 chunks
            if total_ingested % 500 == 0 or total_ingested == len(remaining_chunks):
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = total_ingested / elapsed if elapsed > 0 else 0
                eta = (len(remaining_chunks) - total_ingested) / rate if rate > 0 else 0
                current = start_index + total_ingested
                print(f"Progress: {current:,}/{len(chunks):,} ({rate:.1f}/s, ETA: {eta:.0f}s)")

        except Exception as e:
            print(f"Error at index {start_index + i}: {e}")
            errors += 1
            if errors > 10:
                print("\nToo many errors, stopping.")
                print(f"\nTo resume, run: python scripts/ingest_m3.py --resume")
                break

    elapsed = (datetime.now() - start_time).total_seconds()

    print("-" * 60)
    print(f"\nIngestion {'complete' if errors <= 10 else 'stopped'}!")
    print(f"  Ingested this run: {total_ingested:,}")
    print(f"  Collection count: {collection.count():,}")
    print(f"  Errors: {errors}")
    if elapsed > 0:
        print(f"  Time: {elapsed:.1f}s ({total_ingested/elapsed:.1f} chunks/s)")

    if collection.count() < len(chunks):
        print(f"\nTo resume: python scripts/ingest_m3.py --resume")

    print("=" * 60)


if __name__ == "__main__":
    main()

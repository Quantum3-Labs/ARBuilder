#!/usr/bin/env python3
"""Upload chunks for a single source to the remote Cloudflare API."""

import json
import os
import sys
import time
from pathlib import Path

import httpx

API_URL = os.environ.get("ARBBUILDER_API_URL", "https://arbuilder.app")
ADMIN_SECRET = os.environ.get("ARBBUILDER_ADMIN_SECRET", "")
BATCH_SIZE = 5


def main():
    if not ADMIN_SECRET:
        print("ERROR: ARBBUILDER_ADMIN_SECRET not set")
        sys.exit(1)

    source_filter = sys.argv[1] if len(sys.argv) > 1 else "rust-contracts-stylus"
    print(f"Filter: {source_filter}", flush=True)

    headers = {
        "X-Admin-Secret": ADMIN_SECRET,
        "Content-Type": "application/json",
    }

    # Load chunks
    processed_dir = Path("data/processed")
    chunk_files = sorted(processed_dir.glob("processed_chunks_*.json"), reverse=True)
    with open(chunk_files[0]) as f:
        chunks = json.load(f)

    filtered = [c for c in chunks if source_filter in c.get("repo_url", "")]
    total = len(filtered)
    num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Found {total} chunks, {num_batches} batches", flush=True)

    succeeded = 0
    failed_batches = 0

    for i in range(0, total, BATCH_SIZE):
        batch_num = i // BATCH_SIZE + 1
        batch = filtered[i : i + BATCH_SIZE]
        migrate_batch = [
            {
                "id": c.get("id", ""),
                "content": c.get("content", ""),
                "chunk_index": c.get("chunk_index", 0),
                "source": c.get("source", ""),
                "url": c.get("repo_url", "") or c.get("url", ""),
                "title": c.get("file_path", "") or c.get("title", ""),
                "category": c.get("category", ""),
            }
            for c in batch
        ]

        ok = False
        for attempt in range(3):
            try:
                resp = httpx.post(
                    f"{API_URL}/api/admin/migrate",
                    headers=headers,
                    json={"chunks": migrate_batch, "action": "upsert"},
                    timeout=300,
                )
                data = resp.json()
                if resp.status_code == 200 and data.get("status") == "ok":
                    batch_ok = data.get("processed", len(batch))
                    succeeded += batch_ok
                    print(
                        f"  [{batch_num}/{num_batches}] +{batch_ok} = {succeeded}/{total}",
                        flush=True,
                    )
                    ok = True
                    break
                else:
                    print(
                        f"  [{batch_num}] attempt {attempt + 1} bad response: {resp.status_code}",
                        flush=True,
                    )
                    if attempt < 2:
                        time.sleep(2**attempt)
            except Exception as e:
                print(f"  [{batch_num}] attempt {attempt + 1} error: {e}", flush=True)
                if attempt < 2:
                    time.sleep(2**attempt)

        if not ok:
            failed_batches += 1
            print(f"  [{batch_num}] FAILED after 3 attempts", flush=True)

        time.sleep(0.5)

    print(f"\nDone: {succeeded}/{total} chunks ({failed_batches} failed batches)", flush=True)


if __name__ == "__main__":
    main()

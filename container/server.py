"""
HTTP server for Cloudflare Container - handles source re-ingestion.

Endpoints:
- POST /ingest - Scrape, chunk, and upload a source to Vectorize
- GET /health - Health check
"""

import asyncio
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
import httpx

app = Flask(__name__)

# Environment variables (passed from Worker)
MIGRATE_URL = os.environ.get("MIGRATE_URL", "https://arbuilder.app")
AUTH_SECRET = os.environ.get("AUTH_SECRET", "")

# Minimum supported stylus-sdk version
MINIMUM_SDK_VERSION = "0.8.0"


def extract_stylus_version(cargo_content: str) -> str | None:
    """Extract stylus-sdk version from Cargo.toml content."""
    if not cargo_content:
        return None

    # Pattern 1: Simple format - stylus-sdk = "0.9.0"
    match = re.search(r'stylus-sdk\s*=\s*"([^"]+)"', cargo_content)
    if match:
        return match.group(1)

    # Pattern 2: Complex format - stylus-sdk = { version = "0.9.0", ... }
    match = re.search(r'stylus-sdk\s*=\s*\{[^}]*version\s*=\s*"([^"]+)"', cargo_content, re.DOTALL)
    if match:
        return match.group(1)

    return None


def compare_versions(v1: str, v2: str) -> int:
    """Compare two semantic versions. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2."""
    def parse(v: str) -> list[int]:
        cleaned = re.sub(r'^[\^~>=<]+', '', v)
        parts = cleaned.split(".")
        return [int(x) for x in parts[:3] if x.isdigit()]

    p1, p2 = parse(v1), parse(v2)
    while len(p1) < 3:
        p1.append(0)
    while len(p2) < 3:
        p2.append(0)

    if p1 < p2:
        return -1
    elif p1 > p2:
        return 1
    return 0


def is_version_deprecated(version: str) -> bool:
    """Check if version is below minimum supported."""
    return compare_versions(version, MINIMUM_SDK_VERSION) < 0


class SourceProcessor:
    """Process sources: scrape, chunk, upload to Vectorize."""

    def __init__(self, migrate_url: str, auth_secret: str):
        self.migrate_url = migrate_url
        self.auth_secret = auth_secret

    async def scrape_documentation(self, url: str) -> tuple[str, dict]:
        """Scrape a documentation URL."""
        try:
            from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

            config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                process_iframes=False,
                remove_overlay_elements=True,
            )

            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url, config=config)

                if not result.success:
                    raise Exception(f"Crawl failed: {result.error_message}")

                return result.markdown, {
                    "title": result.metadata.get("title", ""),
                    "description": result.metadata.get("description", ""),
                }
        except Exception as e:
            raise Exception(f"Scraping error: {e}")

    def scrape_github(self, url: str) -> tuple[list[dict], dict]:
        """Scrape a GitHub repository."""
        repo_url = url
        if not repo_url.endswith(".git"):
            repo_url = f"{repo_url}.git"

        with tempfile.TemporaryDirectory() as tmpdir:
            # Clone repository
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, tmpdir],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                raise Exception(f"Git clone failed: {result.stderr}")

            # Get commit hash
            commit_result = subprocess.run(
                ["git", "-C", tmpdir, "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
            )
            commit_hash = commit_result.stdout.strip()

            # Extract stylus version from Cargo.toml files
            stylus_version = None
            cargo_files = list(Path(tmpdir).rglob("Cargo.toml"))
            for cargo_file in cargo_files:
                try:
                    content = cargo_file.read_text(encoding="utf-8")
                    version = extract_stylus_version(content)
                    if version:
                        stylus_version = version
                        break  # Use first found version
                except Exception:
                    pass

            # Extract files
            files = []
            extensions = {".rs", ".toml", ".md", ".json", ".ts", ".js", ".sol"}
            skip_dirs = {"node_modules", "target", ".git", "dist", "build"}

            for root, dirs, filenames in os.walk(tmpdir):
                # Skip directories
                dirs[:] = [d for d in dirs if d not in skip_dirs]

                for filename in filenames:
                    ext = Path(filename).suffix
                    if ext not in extensions:
                        continue

                    filepath = Path(root) / filename
                    rel_path = filepath.relative_to(tmpdir)

                    # Skip large files (100KB)
                    if filepath.stat().st_size > 100 * 1024:
                        continue

                    try:
                        content = filepath.read_text(encoding="utf-8")
                        if content.strip():
                            files.append({
                                "path": str(rel_path),
                                "extension": ext,
                                "content": content,
                                "lines": len(content.splitlines()),
                            })
                    except Exception:
                        pass

            metadata = {"commit_hash": commit_hash}
            if stylus_version:
                metadata["stylus_version"] = stylus_version
                metadata["is_version_deprecated"] = is_version_deprecated(stylus_version)

            return files, metadata

    def chunk_content(
        self, url: str, content: str | list[dict], source_type: str,
        category: str, subcategory: str, metadata: dict
    ) -> list[dict]:
        """Chunk content for indexing."""
        from src.preprocessing.chunker import DocumentChunker, CodeChunker

        chunks = []

        if source_type == "documentation":
            from src.preprocessing.cleaner import TextCleaner

            cleaner = TextCleaner()
            cleaned = cleaner.clean(content)

            chunker = DocumentChunker(max_tokens=512, overlap_tokens=50)
            doc_chunks = chunker.chunk(cleaned)

            for chunk in doc_chunks:
                chunk_dict = chunk.to_dict()
                chunk_dict.update({
                    "source": "documentation",
                    "url": url,
                    "title": metadata.get("title", ""),
                    "category": category,
                    "subcategory": subcategory,
                })

                # Generate deterministic ID
                hash_input = f"{url}{chunk_dict['content'][:500]}"
                content_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
                chunk_dict["id"] = f"chunk_{content_hash}"

                chunks.append(chunk_dict)

        else:  # GitHub
            repo_name = url.rstrip("/").split("/")[-1]

            for file_data in content:
                ext = file_data["extension"]
                file_content = file_data["content"]

                if ext == ".md":
                    chunker = DocumentChunker(max_tokens=512, overlap_tokens=50)
                    file_chunks = chunker.chunk(file_content)
                else:
                    chunker = CodeChunker(max_tokens=1024, overlap_lines=5)
                    file_chunks = chunker.chunk(file_content, ext)

                for chunk in file_chunks:
                    chunk_dict = chunk.to_dict()
                    chunk_dict.update({
                        "source": "github",
                        "repo_name": repo_name,
                        "repo_url": url,
                        "url": url,
                        "file_path": file_data["path"],
                        "category": category,
                        "subcategory": subcategory,
                    })

                    hash_input = f"{url}/{file_data['path']}{chunk_dict['content'][:500]}"
                    content_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
                    chunk_dict["id"] = f"chunk_{content_hash}"

                    chunks.append(chunk_dict)

        return chunks

    async def upload_to_vectorize(self, chunks: list[dict]) -> dict:
        """Upload chunks to Cloudflare Vectorize via the migrate API."""
        results = {"success": 0, "failed": 0, "errors": []}

        # Process in batches of 20
        batch_size = 20

        async with httpx.AsyncClient(timeout=60.0) as client:
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]

                try:
                    response = await client.post(
                        f"{self.migrate_url}/api/admin/migrate",
                        headers={
                            "Content-Type": "application/json",
                            "X-Admin-Secret": self.auth_secret,
                        },
                        json={
                            "action": "upsert",
                            "chunks": [{
                                "id": c["id"],
                                "content": c["content"],
                                "chunk_index": c.get("chunk_index", 0),
                                "source": c.get("source", ""),
                                "url": c.get("url", ""),
                                "title": c.get("title", ""),
                                "category": c.get("category", ""),
                            } for c in batch],
                        },
                    )

                    if response.status_code == 200:
                        data = response.json()
                        results["success"] += data.get("results", {}).get("success", len(batch))
                        results["failed"] += data.get("results", {}).get("failed", 0)
                    else:
                        results["failed"] += len(batch)
                        results["errors"].append(f"Batch {i}: HTTP {response.status_code}")

                except Exception as e:
                    results["failed"] += len(batch)
                    results["errors"].append(f"Batch {i}: {str(e)}")

        return results

    async def update_source_metadata(
        self, url: str, category: str, subcategory: str, chunk_count: int,
        stylus_version: str | None = None, is_version_deprecated: bool = False
    ) -> bool:
        """Update source metadata in KV."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                payload = {
                    "url": url,
                    "category": category,
                    "subcategory": subcategory,
                    "status": "active",
                    "chunkCount": chunk_count,
                }
                if stylus_version:
                    payload["stylusVersion"] = stylus_version
                    payload["isVersionDeprecated"] = is_version_deprecated

                response = await client.post(
                    f"{self.migrate_url}/api/admin/sources",
                    headers={
                        "Content-Type": "application/json",
                        "X-Admin-Secret": self.auth_secret,
                    },
                    json=payload,
                )
                return response.status_code == 200
            except Exception:
                return False

    async def process_source(
        self, url: str, category: str, subcategory: str
    ) -> dict:
        """Full pipeline: scrape, chunk, upload, update metadata."""
        result = {
            "url": url,
            "status": "error",
            "chunks": 0,
            "uploaded": 0,
            "errors": [],
            "stylusVersion": None,
            "isVersionDeprecated": False,
        }

        try:
            # Detect source type
            is_github = "github.com" in url

            # Scrape
            if is_github:
                content, metadata = self.scrape_github(url)
                source_type = "github"
                # Extract version info from metadata
                result["stylusVersion"] = metadata.get("stylus_version")
                result["isVersionDeprecated"] = metadata.get("is_version_deprecated", False)
            else:
                content, metadata = await self.scrape_documentation(url)
                source_type = "documentation"

            # Chunk
            chunks = self.chunk_content(
                url, content, source_type, category, subcategory, metadata
            )
            result["chunks"] = len(chunks)

            if not chunks:
                result["errors"].append("No chunks generated")
                return result

            # Upload to Vectorize
            upload_result = await self.upload_to_vectorize(chunks)
            result["uploaded"] = upload_result["success"]
            result["errors"].extend(upload_result["errors"])

            # Update KV metadata with version info
            await self.update_source_metadata(
                url, category, subcategory, len(chunks),
                stylus_version=result["stylusVersion"],
                is_version_deprecated=result["isVersionDeprecated"]
            )

            result["status"] = "success" if upload_result["failed"] == 0 else "partial"

        except Exception as e:
            result["errors"].append(str(e))

        return result


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


@app.route("/ingest", methods=["POST"])
def ingest():
    """
    Ingest a source: scrape, chunk, upload to Vectorize.

    Request body:
    {
        "url": "https://github.com/...",
        "category": "stylus",
        "subcategory": "community_projects",
        "auth_secret": "..." (optional, overrides env var)
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON body"}), 400

    url = data.get("url")
    category = data.get("category", "stylus")
    subcategory = data.get("subcategory", "")
    # Accept auth_secret from request body (preferred) or fall back to env var
    auth_secret = data.get("auth_secret") or AUTH_SECRET

    if not url:
        return jsonify({"error": "url is required"}), 400

    # Check auth
    if not auth_secret:
        return jsonify({"error": "AUTH_SECRET not configured (pass auth_secret in request or set AUTH_SECRET env var)"}), 500

    # Process the source
    processor = SourceProcessor(MIGRATE_URL, auth_secret)
    result = asyncio.run(processor.process_source(url, category, subcategory))

    status_code = 200 if result["status"] == "success" else 500
    return jsonify(result), status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)

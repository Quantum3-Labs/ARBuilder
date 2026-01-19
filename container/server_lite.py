"""
HTTP server for Cloudflare Container - handles source re-ingestion.
Uses simple HTTP requests (no Playwright) to stay under 2GB disk limit.

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
MIGRATE_URL = os.environ.get("MIGRATE_URL", "https://arbbuilder.whymelabs.com")
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


def extract_stylus_version_from_docs(content: str) -> str | None:
    """Extract stylus-sdk version from documentation content (code examples, etc.)."""
    if not content:
        return None

    # Look for SDK version patterns in docs
    patterns = [
        # Cargo.toml code blocks: stylus-sdk = "0.9.0"
        r'stylus-sdk\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"',
        # Version mentions: stylus-sdk version 0.9.0
        r'stylus-sdk\s+version\s+([0-9]+\.[0-9]+\.[0-9]+)',
        # SDK v0.9.0 mentions
        r'stylus[\s-]*sdk\s+v?([0-9]+\.[0-9]+\.[0-9]+)',
        # alloy-primitives often paired with SDK: alloy-primitives = "0.8.14" (indicates SDK ~0.8.x)
        r'alloy-primitives\s*=\s*"([0-9]+\.[0-9]+)\.[0-9]+"',
    ]

    found_versions = []
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            # Normalize version (handle alloy-primitives correlation)
            if 'alloy' in pattern:
                # alloy-primitives 0.8.x -> SDK 0.8.x, 0.9.x -> SDK 0.9.x
                found_versions.append(match + ".0")
            else:
                found_versions.append(match)

    if not found_versions:
        return None

    # Return the most recent/highest version found (docs usually show latest)
    try:
        sorted_versions = sorted(found_versions, key=lambda v: [int(x) for x in v.split(".")[:3]], reverse=True)
        return sorted_versions[0]
    except (ValueError, IndexError):
        return found_versions[0] if found_versions else None


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
        """Scrape a documentation URL using simple HTTP (no browser needed)."""
        try:
            from bs4 import BeautifulSoup
            from markdownify import markdownify as md

            # Use simple HTTP request - works for most static docs
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ArbBuilder/1.0; +https://arbbuilder.whymelabs.com)"
                })
                response.raise_for_status()
                html = response.text

            # Parse HTML
            soup = BeautifulSoup(html, "html.parser")

            # Extract title
            title = ""
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)

            # Extract description
            description = ""
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                description = meta_desc.get("content", "")

            # Remove script, style, nav, footer, header elements
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
                tag.decompose()

            # Find main content area (common patterns)
            main_content = (
                soup.find("main") or
                soup.find("article") or
                soup.find(class_=lambda x: x and any(c in str(x).lower() for c in ["content", "docs", "markdown"])) or
                soup.find("div", class_="prose") or
                soup.body
            )

            if main_content:
                # Convert to markdown
                markdown = md(str(main_content), heading_style="ATX", strip=["a"])
            else:
                markdown = md(str(soup.body), heading_style="ATX", strip=["a"]) if soup.body else ""

            # Clean up excessive whitespace
            markdown = re.sub(r'\n{3,}', '\n\n', markdown)
            markdown = markdown.strip()

            if not markdown:
                raise Exception("No content extracted from page")

            # Extract Stylus SDK version from doc content (code examples, etc.)
            stylus_version = extract_stylus_version_from_docs(markdown)
            is_deprecated = is_version_deprecated(stylus_version) if stylus_version else False

            return markdown, {
                "title": title,
                "description": description,
                "stylus_version": stylus_version,
                "is_version_deprecated": is_deprecated,
            }
        except httpx.HTTPError as e:
            raise Exception(f"HTTP error scraping {url}: {e}")
        except Exception as e:
            raise Exception(f"Scraping error: {e}")

    def scrape_github(self, url: str) -> tuple[list[dict], dict]:
        """Scrape a GitHub repository using tarball download (faster than git clone)."""
        import tarfile

        # Parse repo owner and name
        parts = url.rstrip("/").replace("https://github.com/", "").split("/")
        if len(parts) < 2:
            raise Exception(f"Invalid GitHub URL: {url}")
        owner, repo = parts[0], parts[1]

        # Try tarball download first (much faster than git clone)
        tarball_url = f"https://api.github.com/repos/{owner}/{repo}/tarball"

        with tempfile.TemporaryDirectory() as tmpdir:
            tarball_path = os.path.join(tmpdir, "repo.tar.gz")
            extract_dir = tmpdir

            try:
                # Stream tarball to disk (memory-efficient for large repos)
                print(f"Downloading tarball from {tarball_url}")
                with httpx.stream(
                    "GET",
                    tarball_url,
                    follow_redirects=True,
                    timeout=180.0,  # 3 minute timeout for download
                    headers={"User-Agent": "ArbBuilder/1.0"}
                ) as response:
                    response.raise_for_status()
                    with open(tarball_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)

                # Extract tarball from disk
                print(f"Extracting tarball...")
                with tarfile.open(tarball_path, mode="r:gz") as tar:
                    tar.extractall(extract_dir)

                # Find the extracted directory (GitHub adds a prefix)
                extracted_dirs = [d for d in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, d))]
                if not extracted_dirs:
                    raise Exception("No directory found in tarball")
                extract_dir = os.path.join(extract_dir, extracted_dirs[0])

            except Exception as e:
                # Fallback to git clone if tarball fails
                print(f"Tarball download failed ({e}), falling back to git clone")
                repo_url = url if not url.endswith(".git") else url
                repo_url = f"{repo_url}.git" if not repo_url.endswith(".git") else repo_url

                result = subprocess.run(
                    ["git", "clone", "--depth", "1", repo_url, extract_dir],
                    capture_output=True,
                    text=True,
                    timeout=240,  # 4 minutes for git clone fallback
                )

                if result.returncode != 0:
                    raise Exception(f"Git clone failed: {result.stderr}")

            tmpdir = extract_dir

            # Get commit hash (only works with git clone, not tarball)
            commit_hash = ""
            if os.path.exists(os.path.join(tmpdir, ".git")):
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

            # Extract files with limits to prevent timeout on huge repos
            files = []
            extensions = {".rs", ".toml", ".md", ".json", ".ts", ".js", ".sol"}
            skip_dirs = {"node_modules", "target", ".git", "dist", "build", "vendor", "third_party"}
            max_files = 500  # Limit to prevent timeout on huge repos
            max_total_size = 5 * 1024 * 1024  # 5MB total content limit
            total_size = 0

            for root, dirs, filenames in os.walk(tmpdir):
                # Skip directories
                dirs[:] = [d for d in dirs if d not in skip_dirs]

                for filename in filenames:
                    # Stop if we hit file limit
                    if len(files) >= max_files:
                        break

                    ext = Path(filename).suffix
                    if ext not in extensions:
                        continue

                    filepath = Path(root) / filename
                    rel_path = filepath.relative_to(tmpdir)

                    # Skip large files (100KB)
                    file_size = filepath.stat().st_size
                    if file_size > 100 * 1024:
                        continue

                    # Skip if total size limit exceeded
                    if total_size + file_size > max_total_size:
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
                            total_size += file_size
                    except Exception:
                        pass

                # Stop outer loop if file limit reached
                if len(files) >= max_files:
                    break

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

    async def upload_batch(self, client: httpx.AsyncClient, batch: list[dict]) -> dict:
        """Upload a single batch to Vectorize."""
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
                return {
                    "success": data.get("results", {}).get("success", len(batch)),
                    "failed": data.get("results", {}).get("failed", 0),
                }
            else:
                return {"success": 0, "failed": len(batch), "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": 0, "failed": len(batch), "error": str(e)}

    async def upload_to_vectorize(self, chunks: list[dict]) -> dict:
        """Upload chunks to Cloudflare Vectorize via the migrate API."""
        results = {"success": 0, "failed": 0, "errors": []}

        # Process in batches of 20, with up to 3 concurrent uploads
        batch_size = 20
        max_concurrent = 3

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Create batches
            batches = [chunks[i:i + batch_size] for i in range(0, len(chunks), batch_size)]

            # Process batches with concurrency limit
            for i in range(0, len(batches), max_concurrent):
                concurrent_batches = batches[i:i + max_concurrent]
                tasks = [self.upload_batch(client, batch) for batch in concurrent_batches]
                batch_results = await asyncio.gather(*tasks)

                for result in batch_results:
                    results["success"] += result.get("success", 0)
                    results["failed"] += result.get("failed", 0)
                    if "error" in result:
                        results["errors"].append(result["error"])

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

    async def process_github_streaming(
        self, url: str, category: str, subcategory: str, metadata: dict
    ) -> dict:
        """Process GitHub repo with streaming: chunk and upload in pipeline."""
        from src.preprocessing.chunker import DocumentChunker, CodeChunker

        results = {"success": 0, "failed": 0, "errors": [], "chunks": 0}
        repo_name = url.rstrip("/").split("/")[-1]
        batch_size = 20
        max_concurrent = 3
        pending_chunks = []

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Process files from metadata (already extracted)
            files = metadata.get("files", [])

            for file_data in files:
                ext = file_data["extension"]
                file_content = file_data["content"]

                # Chunk the file
                if ext == ".md":
                    chunker = DocumentChunker(max_tokens=512, overlap_tokens=50)
                    file_chunks = chunker.chunk(file_content)
                else:
                    chunker = CodeChunker(max_tokens=1024, overlap_lines=5)
                    file_chunks = chunker.chunk(file_content, ext)

                # Convert to dict and add metadata
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

                    pending_chunks.append(chunk_dict)
                    results["chunks"] += 1

                    # Upload when we have enough chunks (pipeline!)
                    if len(pending_chunks) >= batch_size * max_concurrent:
                        batches = [pending_chunks[i:i + batch_size] for i in range(0, len(pending_chunks), batch_size)]
                        tasks = [self.upload_batch(client, batch) for batch in batches[:max_concurrent]]
                        batch_results = await asyncio.gather(*tasks)

                        for br in batch_results:
                            results["success"] += br.get("success", 0)
                            results["failed"] += br.get("failed", 0)
                            if "error" in br:
                                results["errors"].append(br["error"])

                        # Keep remaining chunks
                        pending_chunks = pending_chunks[batch_size * max_concurrent:]

            # Upload remaining chunks
            if pending_chunks:
                batches = [pending_chunks[i:i + batch_size] for i in range(0, len(pending_chunks), batch_size)]
                for i in range(0, len(batches), max_concurrent):
                    concurrent_batches = batches[i:i + max_concurrent]
                    tasks = [self.upload_batch(client, batch) for batch in concurrent_batches]
                    batch_results = await asyncio.gather(*tasks)

                    for br in batch_results:
                        results["success"] += br.get("success", 0)
                        results["failed"] += br.get("failed", 0)
                        if "error" in br:
                            results["errors"].append(br["error"])

        return results

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
                files, metadata = self.scrape_github(url)
                # Extract version info from metadata
                result["stylusVersion"] = metadata.get("stylus_version")
                result["isVersionDeprecated"] = metadata.get("is_version_deprecated", False)

                # Store files in metadata for streaming processing
                metadata["files"] = files

                # Use streaming pipeline for GitHub repos
                stream_result = await self.process_github_streaming(
                    url, category, subcategory, metadata
                )
                result["chunks"] = stream_result["chunks"]
                result["uploaded"] = stream_result["success"]
                result["errors"].extend(stream_result["errors"])

                if result["chunks"] == 0:
                    result["errors"].append("No chunks generated")
                    return result

            else:
                content, metadata = await self.scrape_documentation(url)
                # Extract version info from docs metadata
                result["stylusVersion"] = metadata.get("stylus_version")
                result["isVersionDeprecated"] = metadata.get("is_version_deprecated", False)

                # For docs, use the original chunking (usually small)
                chunks = self.chunk_content(
                    url, content, "documentation", category, subcategory, metadata
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
                url, category, subcategory, result["chunks"],
                stylus_version=result["stylusVersion"],
                is_version_deprecated=result["isVersionDeprecated"]
            )

            result["status"] = "success" if result["uploaded"] == result["chunks"] else "partial"

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

    status_code = 200 if result["status"] in ("success", "partial") else 500
    return jsonify(result), status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)

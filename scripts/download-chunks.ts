/**
 * Download pre-built processed chunks and embeddings from GitHub releases.
 *
 * This allows users to skip the scraping/processing/embedding steps and directly
 * load into their local ChromaDB.
 *
 * Usage:
 *   npx tsx scripts/download-chunks.ts
 *   npx tsx scripts/download-chunks.ts --version v1.0.0
 *   npx tsx scripts/download-chunks.ts --embeddings  # Also download embeddings
 */

import { writeFileSync, mkdirSync, existsSync } from "fs";
import { join } from "path";

const REPO = "Quantum3-Labs/ARBuilder";
const PROCESSED_DIR = "./data/processed";
const EMBEDDINGS_DIR = "./data/embeddings";

interface Release {
  tag_name: string;
  assets: Array<{
    name: string;
    browser_download_url: string;
    size: number;
  }>;
}

async function getLatestRelease(): Promise<Release | null> {
  const response = await fetch(
    `https://api.github.com/repos/${REPO}/releases/latest`
  );

  if (!response.ok) {
    if (response.status === 404) {
      console.log("No releases found. You may need to run the scraper manually.");
      return null;
    }
    throw new Error(`Failed to fetch releases: ${response.status}`);
  }

  return response.json();
}

async function getReleaseByTag(tag: string): Promise<Release | null> {
  const response = await fetch(
    `https://api.github.com/repos/${REPO}/releases/tags/${tag}`
  );

  if (!response.ok) {
    if (response.status === 404) {
      console.log(`Release ${tag} not found.`);
      return null;
    }
    throw new Error(`Failed to fetch release: ${response.status}`);
  }

  return response.json();
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

async function downloadFile(url: string, outputPath: string): Promise<void> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Download failed: ${response.status}`);
  }

  const buffer = await response.arrayBuffer();
  writeFileSync(outputPath, Buffer.from(buffer));
}

async function downloadChunks(
  version?: string,
  includeEmbeddings: boolean = false
): Promise<void> {
  console.log("=".repeat(60));
  console.log("Download Pre-built RAG Data");
  console.log("=".repeat(60));

  // Get release
  const release = version
    ? await getReleaseByTag(version)
    : await getLatestRelease();

  if (!release) {
    console.log("\nNo release available. Run the scraper manually:");
    console.log("  python -m scraper.run");
    console.log("  python -m src.preprocessing.processor");
    return;
  }

  console.log(`\nRelease: ${release.tag_name}`);
  console.log(`Assets: ${release.assets.length}`);

  // Find chunks asset
  const chunksAsset = release.assets.find(
    (a) => a.name.startsWith("processed_chunks_") && a.name.endsWith(".json")
  );

  if (!chunksAsset) {
    console.log("\nNo processed chunks found in this release.");
    console.log("Run the scraper manually:");
    console.log("  python -m scraper.run");
    console.log("  python -m src.preprocessing.processor");
    return;
  }

  // Ensure directories exist
  if (!existsSync(PROCESSED_DIR)) {
    mkdirSync(PROCESSED_DIR, { recursive: true });
  }

  // Download chunks
  console.log(`\nDownloading chunks: ${chunksAsset.name} (${formatBytes(chunksAsset.size)})`);
  const chunksPath = join(PROCESSED_DIR, chunksAsset.name);

  const chunksResponse = await fetch(chunksAsset.browser_download_url);
  if (!chunksResponse.ok) {
    throw new Error(`Chunks download failed: ${chunksResponse.status}`);
  }
  const chunksContent = await chunksResponse.text();
  writeFileSync(chunksPath, chunksContent);

  // Parse to get stats
  const chunks = JSON.parse(chunksContent);
  console.log(`  Saved ${chunks.length} chunks to ${chunksPath}`);

  // Show category breakdown
  const categories: Record<string, number> = {};
  for (const chunk of chunks) {
    const cat = chunk.category || "unknown";
    categories[cat] = (categories[cat] || 0) + 1;
  }

  console.log("\n  Category breakdown:");
  for (const [cat, count] of Object.entries(categories).sort((a, b) => b[1] - a[1])) {
    console.log(`    ${cat}: ${count}`);
  }

  // Download embeddings if requested
  if (includeEmbeddings) {
    const embeddingsAsset = release.assets.find(
      (a) => a.name.startsWith("embeddings_") && a.name.endsWith(".npz")
    );

    if (embeddingsAsset) {
      if (!existsSync(EMBEDDINGS_DIR)) {
        mkdirSync(EMBEDDINGS_DIR, { recursive: true });
      }

      console.log(`\nDownloading embeddings: ${embeddingsAsset.name} (${formatBytes(embeddingsAsset.size)})`);
      const embeddingsPath = join(EMBEDDINGS_DIR, embeddingsAsset.name);
      await downloadFile(embeddingsAsset.browser_download_url, embeddingsPath);
      console.log(`  Saved to ${embeddingsPath}`);
    } else {
      console.log("\n[Warning] No embeddings file found in this release.");
      console.log("  You'll need to generate embeddings locally:");
      console.log("  python -m src.embeddings.vectordb");
    }
  }

  // Next steps
  console.log("\n" + "=".repeat(60));
  console.log("Next steps:");
  console.log("=".repeat(60));

  if (includeEmbeddings) {
    console.log("\nLoad pre-built embeddings into ChromaDB:");
    console.log("  python -m src.embeddings.load_prebuilt --reset");
  } else {
    console.log("\nOption 1: Download embeddings too (no API costs):");
    console.log(`  npx tsx scripts/download-chunks.ts --version=${release.tag_name} --embeddings`);
    console.log("  python -m src.embeddings.load_prebuilt --reset");
    console.log("\nOption 2: Generate embeddings locally (requires OPENROUTER_API_KEY):");
    console.log("  python -m src.embeddings.vectordb");
  }

  console.log("\nFor Cloudflare Vectorize (internal use):");
  console.log("  AUTH_SECRET=xxx npx tsx scripts/diff-migrate.ts --full");
}

// Parse arguments
const args = process.argv.slice(2);
const versionArg = args.find((a) => a.startsWith("--version="));
const version = versionArg?.split("=")[1];
const includeEmbeddings = args.includes("--embeddings") || args.includes("-e");

downloadChunks(version, includeEmbeddings).catch((err) => {
  console.error("Download failed:", err);
  process.exit(1);
});

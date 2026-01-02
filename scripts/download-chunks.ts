/**
 * Download pre-built processed chunks from GitHub releases.
 *
 * This allows users to skip the scraping/processing step and directly
 * ingest into their local ChromaDB or Cloudflare Vectorize.
 *
 * Usage:
 *   npx tsx scripts/download-chunks.ts
 *   npx tsx scripts/download-chunks.ts --version v1.0.0
 */

import { writeFileSync, mkdirSync, existsSync } from "fs";
import { join } from "path";

const REPO = "Quantum3-Labs/ARBuilder";
const PROCESSED_DIR = "./data/processed";

interface Release {
  tag_name: string;
  assets: Array<{
    name: string;
    browser_download_url: string;
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

async function downloadChunks(version?: string): Promise<void> {
  console.log("=".repeat(60));
  console.log("Download Pre-built Chunks");
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

  console.log(`Downloading: ${chunksAsset.name}`);

  // Download
  const response = await fetch(chunksAsset.browser_download_url);
  if (!response.ok) {
    throw new Error(`Download failed: ${response.status}`);
  }

  const content = await response.text();

  // Ensure directory exists
  if (!existsSync(PROCESSED_DIR)) {
    mkdirSync(PROCESSED_DIR, { recursive: true });
  }

  // Save file
  const outputPath = join(PROCESSED_DIR, chunksAsset.name);
  writeFileSync(outputPath, content);

  // Parse to get stats
  const chunks = JSON.parse(content);
  console.log(`\nSaved ${chunks.length} chunks to ${outputPath}`);

  // Show category breakdown
  const categories: Record<string, number> = {};
  for (const chunk of chunks) {
    const cat = chunk.category || "unknown";
    categories[cat] = (categories[cat] || 0) + 1;
  }

  console.log("\nCategory breakdown:");
  for (const [cat, count] of Object.entries(categories).sort((a, b) => b[1] - a[1])) {
    console.log(`  ${cat}: ${count}`);
  }

  console.log("\nNext steps:");
  console.log("  - For local ChromaDB: python -m src.embeddings.vectordb");
  console.log("  - For Cloudflare: npx tsx scripts/diff-migrate.ts --full");
}

// Parse arguments
const args = process.argv.slice(2);
const versionArg = args.find((a) => a.startsWith("--version="));
const version = versionArg?.split("=")[1];

downloadChunks(version).catch((err) => {
  console.error("Download failed:", err);
  process.exit(1);
});

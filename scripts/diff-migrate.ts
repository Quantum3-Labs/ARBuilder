/**
 * Diff-based migration script for cost-efficient updates to Vectorize.
 *
 * Only uploads chunks that have changed since the last migration,
 * saving ~80% on embedding costs.
 *
 * Usage:
 * AUTH_SECRET=xxx npx tsx scripts/diff-migrate.ts
 *
 * For full refresh (ignore diff):
 * AUTH_SECRET=xxx npx tsx scripts/diff-migrate.ts --full
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";
import { readdirSync } from "fs";
import { join, dirname } from "path";

// Configuration
const PROCESSED_DIR = "./data/processed";
const STATE_DIR = "./.rag-state";
const STATE_FILE = join(STATE_DIR, "chunk-hashes.json");
const LAST_REFRESH_FILE = join(STATE_DIR, "last-refresh.json");
const BATCH_SIZE = 20;
const AUTH_SECRET = process.env.AUTH_SECRET!;
const MIGRATE_URL =
  process.env.MIGRATE_URL || "https://arbbuilder.whymelabs.com";

// Chunk structure with new metadata fields
interface ProcessedChunk {
  id: string;
  content: string;
  chunk_index: number;
  total_chunks: number;
  token_count: number;
  source: string;
  url: string;
  title: string;
  category: string;
  subcategory: string;
  scraped_at: string;
  // New fields
  content_hash?: string;
  sdk_version?: string;
  is_current?: boolean;
  deprecated_patterns?: string[];
}

// State tracking for each chunk
interface ChunkState {
  id: string;
  contentHash: string;
  sdkVersion: string;
  migratedAt: string;
}

interface LastRefresh {
  timestamp: string;
  totalChunks: number;
  uploadedChunks: number;
  skippedChunks: number;
  sdkVersion: string | null;
  success: number;
  failed: number;
}

// Ensure state directory exists
function ensureStateDir(): void {
  if (!existsSync(STATE_DIR)) {
    mkdirSync(STATE_DIR, { recursive: true });
    console.log(`Created state directory: ${STATE_DIR}`);
  }
}

// Load previous migration state
function loadState(): Map<string, ChunkState> {
  if (existsSync(STATE_FILE)) {
    try {
      const data = JSON.parse(readFileSync(STATE_FILE, "utf-8"));
      console.log(`Loaded state for ${Object.keys(data).length} chunks`);
      return new Map(Object.entries(data));
    } catch (err) {
      console.log(`Could not load state: ${err}`);
    }
  }
  console.log("No previous state found - will upload all chunks");
  return new Map();
}

// Save current migration state
function saveState(state: Map<string, ChunkState>): void {
  ensureStateDir();
  const data = Object.fromEntries(state);
  writeFileSync(STATE_FILE, JSON.stringify(data, null, 2));
  console.log(`Saved state for ${state.size} chunks`);
}

// Save last refresh info
function saveLastRefresh(info: LastRefresh): void {
  ensureStateDir();
  writeFileSync(LAST_REFRESH_FILE, JSON.stringify(info, null, 2));
}

// Compute content hash if not present
function computeHash(content: string): string {
  // Use Node's crypto for hashing
  const crypto = require("crypto");
  return crypto.createHash("sha256").update(content).digest("hex").slice(0, 16);
}

// Load chunks from the latest processed file
async function loadChunks(): Promise<ProcessedChunk[]> {
  const files = readdirSync(PROCESSED_DIR).filter((f) =>
    f.startsWith("processed_chunks_")
  );
  if (files.length === 0) {
    throw new Error("No processed chunks file found");
  }

  const latestFile = files.sort().reverse()[0];
  console.log(`Loading chunks from: ${latestFile}`);

  const filePath = join(PROCESSED_DIR, latestFile);
  const content = readFileSync(filePath, "utf-8");
  return JSON.parse(content) as ProcessedChunk[];
}

// Check Vectorize status
async function checkStatus(): Promise<{ vectorCount: number }> {
  const response = await fetch(`${MIGRATE_URL}/api/admin/migrate`, {
    method: "GET",
    headers: {
      "X-Admin-Secret": AUTH_SECRET,
    },
  });

  if (!response.ok) {
    throw new Error(`Status check failed: ${response.status}`);
  }

  return response.json();
}

// Upload a batch of chunks
async function uploadBatch(
  chunks: ProcessedChunk[]
): Promise<{ success: number; failed: number; errors: string[] }> {
  const response = await fetch(`${MIGRATE_URL}/api/admin/migrate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Secret": AUTH_SECRET,
    },
    body: JSON.stringify({
      action: "upsert",
      chunks: chunks.map((c) => ({
        id: c.id,
        content: c.content,
        chunk_index: c.chunk_index,
        source: c.source,
        url: c.url,
        title: c.title,
        category: c.category,
      })),
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Upload failed: ${response.status} - ${error}`);
  }

  const result = (await response.json()) as {
    results: { success: number; failed: number; errors: string[] };
  };
  return result.results;
}

async function diffMigrate(forceFullRefresh: boolean): Promise<void> {
  console.log("=".repeat(60));
  console.log("Diff-Based Migration to Cloudflare Vectorize");
  console.log("=".repeat(60));
  console.log(`Target: ${MIGRATE_URL}/api/admin/migrate`);
  console.log(`Mode: ${forceFullRefresh ? "FULL REFRESH" : "DIFF-BASED"}\n`);

  // Validate environment
  if (!AUTH_SECRET) {
    throw new Error("Missing AUTH_SECRET environment variable");
  }

  // Check current status
  console.log("Checking current Vectorize status...");
  try {
    const status = await checkStatus();
    console.log(`Current vector count: ${status.vectorCount}\n`);
  } catch (err) {
    console.log(`Could not get status: ${err}\n`);
  }

  // Load previous state
  const state = forceFullRefresh ? new Map() : loadState();

  // Load chunks
  const chunks = await loadChunks();
  console.log(`Total chunks in file: ${chunks.length}\n`);

  // Determine which chunks need uploading
  const toUpload: ProcessedChunk[] = [];
  const skipped: string[] = [];

  for (const chunk of chunks) {
    // Get or compute content hash
    const contentHash = chunk.content_hash || computeHash(chunk.content);

    // Check if this chunk has changed
    const existingState = state.get(chunk.id);

    if (existingState && existingState.contentHash === contentHash) {
      skipped.push(chunk.id);
    } else {
      toUpload.push(chunk);
    }
  }

  console.log(`Chunks to upload: ${toUpload.length}`);
  console.log(`Chunks skipped (unchanged): ${skipped.length}`);

  if (toUpload.length === 0) {
    console.log("\nNo changes detected - nothing to upload!");
    saveLastRefresh({
      timestamp: new Date().toISOString(),
      totalChunks: chunks.length,
      uploadedChunks: 0,
      skippedChunks: skipped.length,
      sdkVersion: null,
      success: 0,
      failed: 0,
    });
    return;
  }

  // Calculate cost savings
  const savings = Math.round((skipped.length / chunks.length) * 100);
  console.log(`Cost savings: ${savings}%\n`);

  // Process in batches
  let totalSuccess = 0;
  let totalFailed = 0;
  const newState = new Map(state);

  for (let i = 0; i < toUpload.length; i += BATCH_SIZE) {
    const batch = toUpload.slice(i, i + BATCH_SIZE);
    const progress = Math.round(((i + batch.length) / toUpload.length) * 100);
    process.stdout.write(
      `\rUploading: ${progress}% (${i + batch.length}/${toUpload.length}) | Success: ${totalSuccess} | Failed: ${totalFailed}`
    );

    try {
      const result = await uploadBatch(batch);
      totalSuccess += result.success;
      totalFailed += result.failed;

      // Update state for successfully uploaded chunks
      for (const chunk of batch) {
        const contentHash = chunk.content_hash || computeHash(chunk.content);
        newState.set(chunk.id, {
          id: chunk.id,
          contentHash,
          sdkVersion: chunk.sdk_version || "",
          migratedAt: new Date().toISOString(),
        });
      }

      if (result.errors.length > 0) {
        console.log(`\nBatch errors: ${result.errors.slice(0, 3).join(", ")}`);
      }

      // Rate limit delay
      await new Promise((resolve) => setTimeout(resolve, 500));
    } catch (err) {
      console.error(`\nError processing batch at ${i}:`, err);
      totalFailed += batch.length;
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
  }

  // Save updated state
  saveState(newState);

  // Save refresh info
  saveLastRefresh({
    timestamp: new Date().toISOString(),
    totalChunks: chunks.length,
    uploadedChunks: toUpload.length,
    skippedChunks: skipped.length,
    sdkVersion: chunks.find((c) => c.sdk_version)?.sdk_version || null,
    success: totalSuccess,
    failed: totalFailed,
  });

  console.log(`\n\n${"=".repeat(60)}`);
  console.log("Migration Complete!");
  console.log(`${"=".repeat(60)}`);
  console.log(`Total chunks: ${chunks.length}`);
  console.log(`Uploaded: ${toUpload.length} (${100 - savings}%)`);
  console.log(`Skipped: ${skipped.length} (${savings}%)`);
  console.log(`Success: ${totalSuccess}`);
  console.log(`Failed: ${totalFailed}`);

  // Final status check
  try {
    const status = await checkStatus();
    console.log(`\nFinal vector count: ${status.vectorCount}`);
  } catch {
    // Ignore
  }
}

// Parse arguments
const args = process.argv.slice(2);
const forceFullRefresh = args.includes("--full") || args.includes("-f");
const clearFirst = args.includes("--clear") || args.includes("-c");

// Clear existing vectors using IDs from state file
async function clearExistingVectors(): Promise<void> {
  console.log("=".repeat(60));
  console.log("Clearing Existing Vectors");
  console.log("=".repeat(60));

  const state = loadState();
  if (state.size === 0) {
    console.log("No state file found - nothing to clear\n");
    return;
  }

  const ids = Array.from(state.keys());
  console.log(`Found ${ids.length} vectors to clear\n`);

  // Delete in batches
  const batchSize = 100;
  for (let i = 0; i < ids.length; i += batchSize) {
    const batch = ids.slice(i, i + batchSize);
    const progress = Math.round(((i + batch.length) / ids.length) * 100);
    process.stdout.write(`\rClearing: ${progress}% (${i + batch.length}/${ids.length})`);

    try {
      await fetch(`${MIGRATE_URL}/api/admin/migrate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Secret": AUTH_SECRET,
        },
        body: JSON.stringify({
          action: "clear",
          chunks: batch.map((id) => ({ id })),
        }),
      });
    } catch (err) {
      console.error(`\nError clearing batch: ${err}`);
    }

    await new Promise((resolve) => setTimeout(resolve, 200));
  }

  // Clear the state file
  ensureStateDir();
  writeFileSync(STATE_FILE, JSON.stringify({}, null, 2));
  console.log("\n\nCleared state file\n");
}

// Run migration
async function main(): Promise<void> {
  if (clearFirst) {
    await clearExistingVectors();
  }
  await diffMigrate(forceFullRefresh);
}

main().catch((err) => {
  console.error("Migration failed:", err);
  process.exit(1);
});

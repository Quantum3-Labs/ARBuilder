/**
 * Migration script to upload processed chunks to Cloudflare Vectorize.
 *
 * Uses the Worker's /api/admin/migrate endpoint instead of direct API calls.
 * This approach uses the Worker's AI binding directly.
 *
 * Prerequisites:
 * 1. Deploy the Worker first
 * 2. Create metadata index: npx wrangler vectorize create-metadata-index arbbuilder --property-name=source --type=string
 *
 * Usage:
 * AUTH_SECRET=xxx npx tsx scripts/migrate-to-vectorize.ts
 *
 * Or for production:
 * AUTH_SECRET=xxx MIGRATE_URL=https://arbbuilder.whymelabs.com npx tsx scripts/migrate-to-vectorize.ts
 */

import { readFileSync, readdirSync } from "fs";
import { join } from "path";

// Configuration
const PROCESSED_DIR = "./data/processed";
const BATCH_SIZE = 20; // Smaller batches since embedding happens server-side
const AUTH_SECRET = process.env.AUTH_SECRET!;
const MIGRATE_URL = process.env.MIGRATE_URL || "http://localhost:3000";

// Processed chunk structure from data/processed/processed_chunks_*.json
interface ProcessedChunk {
  id: string;
  content: string;
  chunk_index: number;
  total_chunks: number;
  token_count: number;
  source: string; // "documentation" or "github"
  url: string;
  title: string;
  category: string; // "stylus", "arbitrum_docs", etc.
  subcategory: string;
  scraped_at: string;
}

async function checkStatus(): Promise<{ vectorCount: number }> {
  const response = await fetch(`${MIGRATE_URL}/api/admin/migrate`, {
    method: "GET",
    headers: {
      "X-Admin-Secret": AUTH_SECRET,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Status check failed: ${response.status} - ${error}`);
  }

  return response.json();
}

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

  const result = await response.json();
  return result.results;
}

async function loadChunks(): Promise<ProcessedChunk[]> {
  // Find the most recent processed chunks file
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

async function migrate(): Promise<void> {
  console.log("Starting migration to Cloudflare Vectorize...\n");
  console.log(`Target: ${MIGRATE_URL}/api/admin/migrate`);
  console.log("Using BGE-M3 model (1024 dimensions)\n");

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

  // Load chunks
  const chunks = await loadChunks();
  console.log(`Loaded ${chunks.length} chunks\n`);

  // Show data distribution
  const docCount = chunks.filter((c) => c.source === "documentation").length;
  const codeCount = chunks.filter((c) => c.source === "github").length;
  console.log(
    `Distribution: ${docCount} documentation, ${codeCount} github (code)\n`
  );

  // Process in batches
  let totalSuccess = 0;
  let totalFailed = 0;

  for (let i = 0; i < chunks.length; i += BATCH_SIZE) {
    const batch = chunks.slice(i, i + BATCH_SIZE);
    const progress = Math.round(((i + batch.length) / chunks.length) * 100);
    process.stdout.write(
      `\rProcessing: ${progress}% (${i + batch.length}/${chunks.length}) | Success: ${totalSuccess} | Failed: ${totalFailed}`
    );

    try {
      const result = await uploadBatch(batch);
      totalSuccess += result.success;
      totalFailed += result.failed;

      if (result.errors.length > 0) {
        console.log(`\nBatch errors: ${result.errors.slice(0, 3).join(", ")}`);
      }

      // Rate limit delay (be nice to the API)
      await new Promise((resolve) => setTimeout(resolve, 500));
    } catch (err) {
      console.error(`\nError processing batch at ${i}:`, err);
      totalFailed += batch.length;

      // Longer delay on error
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
  }

  console.log(`\n\nMigration complete!`);
  console.log(`Successfully inserted: ${totalSuccess} vectors`);
  console.log(`Failed: ${totalFailed}`);

  // Final status check
  try {
    const status = await checkStatus();
    console.log(`\nFinal vector count: ${status.vectorCount}`);
  } catch {
    // Ignore
  }

  console.log(`\nRemember to create metadata index if not done:`);
  console.log(
    `  npx wrangler vectorize create-metadata-index arbbuilder --property-name=source --type=string`
  );
}

// Run migration
migrate().catch(console.error);

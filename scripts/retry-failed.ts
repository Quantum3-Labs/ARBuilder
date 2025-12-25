/**
 * Retry script for failed chunks during migration.
 */

import { readFileSync, readdirSync } from "fs";
import { join } from "path";

const PROCESSED_DIR = "./data/processed";
const AUTH_SECRET = process.env.AUTH_SECRET;
const MIGRATE_URL = process.env.MIGRATE_URL || "https://arbbuilder.swmengappdev.workers.dev";

// Failed chunk IDs from the migration
const FAILED_IDS = [
  "chunk_002438", "chunk_002439",
  "chunk_004060", "chunk_004061",
  "chunk_004320",
  "chunk_005074", "chunk_005075",
  "chunk_005119", "chunk_005120", "chunk_005121", "chunk_005122",
  "chunk_007489", "chunk_007490", "chunk_007492",
  "chunk_007783", "chunk_007784"
];

interface ProcessedChunk {
  id: string;
  content: string;
  chunk_index: number;
  source: string;
  url: string;
  title: string;
  category: string;
}

async function retryFailed() {
  console.log("Retrying failed chunks...\n");

  if (!AUTH_SECRET) {
    throw new Error("Missing AUTH_SECRET");
  }

  // Load chunks
  const files = readdirSync(PROCESSED_DIR).filter(f => f.startsWith("processed_chunks_"));
  const latestFile = files.sort().reverse()[0];
  const filePath = join(PROCESSED_DIR, latestFile);
  const allChunks = JSON.parse(readFileSync(filePath, "utf-8")) as ProcessedChunk[];

  // Filter to just failed ones
  const failedChunks = allChunks.filter(c => FAILED_IDS.includes(c.id));
  console.log(`Found ${failedChunks.length} chunks to retry\n`);

  // Retry one at a time for better success rate
  let success = 0;
  let failed = 0;

  for (const chunk of failedChunks) {
    console.log(`Retrying ${chunk.id}...`);

    try {
      const response = await fetch(`${MIGRATE_URL}/api/admin/migrate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Secret": AUTH_SECRET,
        },
        body: JSON.stringify({
          action: "upsert",
          chunks: [{
            id: chunk.id,
            content: chunk.content,
            chunk_index: chunk.chunk_index,
            source: chunk.source,
            url: chunk.url,
            title: chunk.title,
            category: chunk.category,
          }],
        }),
      });

      const result = await response.json() as { results?: { success?: number; failed?: number; errors?: string[] } };

      if (result.results?.success && result.results.success > 0) {
        console.log(`  ✓ Success`);
        success++;
      } else if (result.results?.errors?.length) {
        console.log(`  ✗ Failed: ${result.results.errors[0]}`);
        failed++;
      } else {
        console.log(`  ? Unknown result`);
        failed++;
      }

      // Wait between requests
      await new Promise(r => setTimeout(r, 1000));
    } catch (err) {
      console.log(`  ✗ Error: ${err}`);
      failed++;
    }
  }

  console.log(`\nRetry complete! Success: ${success}, Failed: ${failed}`);
}

retryFailed();

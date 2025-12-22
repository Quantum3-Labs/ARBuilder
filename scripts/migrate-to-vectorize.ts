/**
 * Migration script to upload processed chunks to Cloudflare Vectorize.
 *
 * Prerequisites:
 * 1. Create Vectorize index: wrangler vectorize create arbbuilder --dimensions=768 --metric=cosine
 * 2. Deploy the Workers with AI binding
 *
 * Usage:
 * npx tsx scripts/migrate-to-vectorize.ts
 */

import { readFileSync, readdirSync } from "fs";
import { join } from "path";

// Configuration
const PROCESSED_DIR = "./data/processed";
const BATCH_SIZE = 100;
const CLOUDFLARE_ACCOUNT_ID = process.env.CLOUDFLARE_ACCOUNT_ID!;
const CLOUDFLARE_API_TOKEN = process.env.CLOUDFLARE_API_TOKEN!;
const VECTORIZE_INDEX_NAME = "arbbuilder";

interface Chunk {
  id: string;
  content: string;
  source: string;
  content_type: string;
  chunk_index: number;
  metadata?: Record<string, unknown>;
}

interface VectorizeVector {
  id: string;
  values: number[];
  metadata: {
    content: string;
    source: string;
    content_type: string;
    chunk_index: number;
  };
}

async function generateEmbedding(text: string): Promise<number[]> {
  // Use Cloudflare AI API to generate embeddings
  const response = await fetch(
    `https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/baai/bge-base-en-v1.5`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${CLOUDFLARE_API_TOKEN}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: [text],
      }),
    }
  );

  if (!response.ok) {
    throw new Error(`Embedding API error: ${response.status}`);
  }

  const data = (await response.json()) as { result: { data: number[][] } };
  return data.result.data[0];
}

async function insertVectors(vectors: VectorizeVector[]): Promise<void> {
  const response = await fetch(
    `https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/vectorize/v2/indexes/${VECTORIZE_INDEX_NAME}/upsert`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${CLOUDFLARE_API_TOKEN}`,
        "Content-Type": "application/x-ndjson",
      },
      body: vectors.map((v) => JSON.stringify(v)).join("\n"),
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Vectorize upsert error: ${response.status} - ${error}`);
  }
}

async function loadChunks(): Promise<Chunk[]> {
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
  return JSON.parse(content) as Chunk[];
}

async function migrate(): Promise<void> {
  console.log("Starting migration to Cloudflare Vectorize...\n");

  // Validate environment
  if (!CLOUDFLARE_ACCOUNT_ID || !CLOUDFLARE_API_TOKEN) {
    throw new Error(
      "Missing CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN environment variables"
    );
  }

  // Load chunks
  const chunks = await loadChunks();
  console.log(`Loaded ${chunks.length} chunks\n`);

  // Process in batches
  let successCount = 0;
  let errorCount = 0;

  for (let i = 0; i < chunks.length; i += BATCH_SIZE) {
    const batch = chunks.slice(i, i + BATCH_SIZE);
    const progress = Math.round(((i + batch.length) / chunks.length) * 100);
    process.stdout.write(`\rProcessing: ${progress}% (${i + batch.length}/${chunks.length})`);

    try {
      // Generate embeddings for batch
      const vectors: VectorizeVector[] = [];
      for (const chunk of batch) {
        try {
          const embedding = await generateEmbedding(chunk.content);
          vectors.push({
            id: chunk.id,
            values: embedding,
            metadata: {
              content: chunk.content.slice(0, 1000), // Truncate for metadata limits
              source: chunk.source,
              content_type: chunk.content_type,
              chunk_index: chunk.chunk_index,
            },
          });
        } catch (err) {
          console.error(`\nError embedding chunk ${chunk.id}:`, err);
          errorCount++;
        }
      }

      // Insert vectors
      if (vectors.length > 0) {
        await insertVectors(vectors);
        successCount += vectors.length;
      }

      // Rate limit delay
      await new Promise((resolve) => setTimeout(resolve, 100));
    } catch (err) {
      console.error(`\nError processing batch at ${i}:`, err);
      errorCount += batch.length;
    }
  }

  console.log(`\n\nMigration complete!`);
  console.log(`Successfully inserted: ${successCount} vectors`);
  console.log(`Errors: ${errorCount}`);
}

// Run migration
migrate().catch(console.error);

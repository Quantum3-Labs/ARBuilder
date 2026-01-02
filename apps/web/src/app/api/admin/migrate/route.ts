/**
 * Migration endpoint for uploading embeddings to Vectorize.
 * Protected by admin secret - only accessible internally.
 *
 * Usage:
 * POST /api/admin/migrate
 * Headers: X-Admin-Secret: <AUTH_SECRET>
 * Body: { chunks: [...] }
 */

import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";

interface ProcessedChunk {
  id: string;
  content: string;
  chunk_index: number;
  source: string;
  url: string;
  title: string;
  category: string;
}

interface MigrateRequest {
  chunks: ProcessedChunk[];
  action?: "upsert" | "status" | "clear";
}

/**
 * Retry a function with exponential backoff.
 * Handles transient errors like AiError: 3043 (inference error).
 */
async function withRetry<T>(
  fn: () => Promise<T>,
  options: {
    maxRetries?: number;
    baseDelayMs?: number;
    maxDelayMs?: number;
  } = {}
): Promise<T> {
  const { maxRetries = 3, baseDelayMs = 500, maxDelayMs = 5000 } = options;

  let lastError: Error | unknown;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      // Don't retry on the last attempt
      if (attempt === maxRetries) {
        break;
      }

      // Calculate delay with exponential backoff + jitter
      const delay = Math.min(
        baseDelayMs * Math.pow(2, attempt) + Math.random() * 100,
        maxDelayMs
      );

      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}

export async function POST(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();

    // Verify admin secret
    const adminSecret = request.headers.get("X-Admin-Secret");
    if (!adminSecret || adminSecret !== env.AUTH_SECRET) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = (await request.json()) as MigrateRequest;
    const action = body.action || "upsert";

    // Handle status check
    if (action === "status") {
      const info = await env.VECTORIZE.describe();
      return NextResponse.json({
        status: "ok",
        vectorCount: info.vectorsCount,
      });
    }

    // Handle clear - delete vectors by IDs
    if (action === "clear") {
      const ids = body.chunks?.map((c) => c.id) || [];
      if (ids.length === 0) {
        return NextResponse.json({
          status: "ok",
          message: "No IDs provided to clear",
          deleted: 0,
        });
      }

      try {
        // Delete in batches of 100
        let totalDeleted = 0;
        for (let i = 0; i < ids.length; i += 100) {
          const batch = ids.slice(i, i + 100);
          await env.VECTORIZE.deleteByIds(batch);
          totalDeleted += batch.length;
        }

        return NextResponse.json({
          status: "ok",
          deleted: totalDeleted,
        });
      } catch (err) {
        return NextResponse.json(
          { error: `Clear failed: ${err}` },
          { status: 500 }
        );
      }
    }

    // Handle upsert
    if (action === "upsert") {
      if (!body.chunks || !Array.isArray(body.chunks) || body.chunks.length === 0) {
        return NextResponse.json(
          { error: "No chunks provided" },
          { status: 400 }
        );
      }

      const results = {
        success: 0,
        failed: 0,
        errors: [] as string[],
      };

      // Process chunks and generate embeddings
      const vectors: Array<{
        id: string;
        values: number[];
        metadata: Record<string, string | number>;
      }> = [];

      for (const chunk of body.chunks) {
        try {
          // Generate embedding using BGE-M3 with retry logic
          const embeddingResponse = await withRetry(
            async () => {
              return await env.AI.run("@cf/baai/bge-m3", {
                text: [chunk.content],
              });
            },
            { maxRetries: 3, baseDelayMs: 500, maxDelayMs: 5000 }
          );

          let embedding: number[] = [];
          if ("data" in embeddingResponse && Array.isArray(embeddingResponse.data)) {
            embedding = embeddingResponse.data[0];
          }

          if (embedding.length === 0) {
            results.failed++;
            results.errors.push(`Empty embedding for ${chunk.id}`);
            continue;
          }

          vectors.push({
            id: chunk.id,
            values: embedding,
            metadata: {
              content: chunk.content.slice(0, 2000),
              source: chunk.source,
              category: chunk.category || "",
              title: (chunk.title || "").slice(0, 200),
              url: (chunk.url || "").slice(0, 500),
              chunk_index: chunk.chunk_index,
            },
          });
          results.success++;
        } catch (err) {
          results.failed++;
          results.errors.push(`Error processing ${chunk.id}: ${err}`);
        }
      }

      // Upsert to Vectorize with retry
      if (vectors.length > 0) {
        try {
          await withRetry(
            async () => {
              await env.VECTORIZE.upsert(vectors);
            },
            { maxRetries: 3, baseDelayMs: 1000, maxDelayMs: 10000 }
          );
        } catch (err) {
          return NextResponse.json(
            {
              error: `Vectorize upsert failed after retries: ${err}`,
              results,
            },
            { status: 500 }
          );
        }
      }

      return NextResponse.json({
        status: "ok",
        processed: body.chunks.length,
        results,
      });
    }

    return NextResponse.json({ error: "Unknown action" }, { status: 400 });
  } catch (error) {
    console.error("Migration error:", error);
    return NextResponse.json(
      { error: `Migration failed: ${error}` },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();

    // Verify admin secret
    const adminSecret = request.headers.get("X-Admin-Secret");
    if (!adminSecret || adminSecret !== env.AUTH_SECRET) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Return Vectorize status
    const info = await env.VECTORIZE.describe();
    return NextResponse.json({
      status: "ok",
      vectorCount: info.vectorsCount,
    });
  } catch (error) {
    return NextResponse.json(
      { error: `Status check failed: ${error}` },
      { status: 500 }
    );
  }
}

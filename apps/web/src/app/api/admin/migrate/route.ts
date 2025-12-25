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
          // Generate embedding using BGE-M3
          const embeddingResponse = await env.AI.run("@cf/baai/bge-m3", {
            text: [chunk.content],
          });

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

      // Upsert to Vectorize
      if (vectors.length > 0) {
        try {
          await env.VECTORIZE.upsert(vectors);
        } catch (err) {
          return NextResponse.json(
            {
              error: `Vectorize upsert failed: ${err}`,
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

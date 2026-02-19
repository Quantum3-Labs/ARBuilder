/**
 * Admin API for source ingestion.
 * Protected by admin secret - only accessible internally.
 *
 * POST /api/admin/ingest - Ingest a specific source, process next, or handle queue messages
 * GET /api/admin/ingest - Return ingestion status and active progress
 *
 * Headers: X-Admin-Secret: <AUTH_SECRET>
 */

import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import {
  ingestSource,
  selectNextSource,
  getActiveProgress,
  handleEmbedMessage,
  handleContinueMessage,
  handleFinalizeMessage,
  type IngestOptions,
  type QueueMessage,
} from "../../../../lib/ingestPipeline";

function verifyAuth(request: NextRequest, authSecret: string): boolean {
  const adminSecret = request.headers.get("X-Admin-Secret");
  return adminSecret === authSecret;
}

/**
 * POST /api/admin/ingest
 * Ingest a specific source, process the next pending source, or handle a queue message.
 *
 * Body options:
 * - { url, category, subcategory? } — ingest a specific source
 * - { action: "process_next" } — pick and process the next pending source (cron-like)
 * - { queueMessage: QueueMessage } — handle a queue message (from worker.ts queue handler)
 */
export async function POST(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();

    if (!verifyAuth(request, env.AUTH_SECRET)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = (await request.json()) as {
      url?: string;
      category?: string;
      subcategory?: string;
      action?: "process_next";
      queueMessage?: QueueMessage;
    };

    const options: IngestOptions = {
      githubToken: env.GITHUB_TOKEN,
    };

    // Handle queue messages (from worker.ts queue consumer)
    if (body.queueMessage) {
      const msg = body.queueMessage;
      switch (msg.type) {
        case "embed":
          await handleEmbedMessage(msg, env);
          return NextResponse.json({ status: "ok", type: "embed", sourceId: msg.sourceId });
        case "continue":
          await handleContinueMessage(msg, env);
          return NextResponse.json({ status: "ok", type: "continue", sourceId: msg.sourceId });
        case "finalize":
          await handleFinalizeMessage(msg, env);
          return NextResponse.json({ status: "ok", type: "finalize", sourceId: msg.sourceId });
        default:
          return NextResponse.json({ error: "Unknown queue message type" }, { status: 400 });
      }
    }

    // Handle "process_next" — pick next source from registry
    if (body.action === "process_next") {
      const source = await selectNextSource(env);
      if (!source) {
        return NextResponse.json({
          status: "ok",
          message: "No sources to process",
        });
      }

      const result = await ingestSource(
        {
          url: source.url,
          category: source.category,
          subcategory: source.subcategory,
          sourceType: source.sourceType,
        },
        env,
        options
      );

      return NextResponse.json(result);
    }

    // Handle specific source ingestion
    if (!body.url) {
      return NextResponse.json(
        { error: "url is required (or use action: 'process_next')" },
        { status: 400 }
      );
    }

    const result = await ingestSource(
      {
        url: body.url,
        category: body.category || "stylus",
        subcategory: body.subcategory,
      },
      env,
      options
    );

    return NextResponse.json(result);
  } catch (error) {
    console.error("Ingest error:", error);
    return NextResponse.json(
      { error: `Ingestion failed: ${error}` },
      { status: 500 }
    );
  }
}

/**
 * GET /api/admin/ingest
 * Returns ingestion status and active progress entries.
 */
export async function GET(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();

    if (!verifyAuth(request, env.AUTH_SECRET)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const progress = await getActiveProgress(env);

    return NextResponse.json({
      status: "ok",
      activeJobs: progress,
    });
  } catch (error) {
    return NextResponse.json(
      { error: `Status check failed: ${error}` },
      { status: 500 }
    );
  }
}

/**
 * Admin API for triggering source re-ingestion via Cloudflare Container.
 * Protected by admin secret - only accessible internally.
 *
 * POST /api/admin/ingest - Trigger re-ingestion for a source
 * GET /api/admin/ingest - Check container health status
 *
 * Headers: X-Admin-Secret: <AUTH_SECRET>
 * Body: { url, category, subcategory }
 *
 * The container runs a Python Flask server that:
 * - Scrapes documentation or GitHub repos
 * - Chunks content for RAG
 * - Uploads to Cloudflare Vectorize via /api/admin/migrate
 */

import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";

// Verify admin auth
function verifyAuth(request: NextRequest, authSecret: string): boolean {
  const adminSecret = request.headers.get("X-Admin-Secret");
  return adminSecret === authSecret;
}

/**
 * POST /api/admin/ingest
 * Trigger re-ingestion for a source using the Python scraper container
 */
export async function POST(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();

    if (!verifyAuth(request, env.AUTH_SECRET)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json() as {
      url: string;
      category: string;
      subcategory?: string;
    };

    if (!body.url) {
      return NextResponse.json(
        { error: "url is required" },
        { status: 400 }
      );
    }

    // Check if container binding exists
    if (!env.SCRAPER_CONTAINER) {
      // Fallback to CLI command if container not available
      const cliCommand = `AUTH_SECRET=$AUTH_SECRET npx tsx scripts/diff-migrate.ts --source "${body.url}"`;
      return NextResponse.json({
        status: "fallback",
        message: "Container binding not available. Use CLI command.",
        cliCommand,
        url: body.url,
      });
    }

    // Get container instance using source URL hash as the Durable Object ID
    // This ensures each source gets its own container instance
    const containerId = env.SCRAPER_CONTAINER.idFromName(body.url);
    const container = env.SCRAPER_CONTAINER.get(containerId);

    // Send ingest request to the container
    const containerResponse = await container.fetch(
      new Request("http://container/ingest", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: body.url,
          category: body.category || "stylus",
          subcategory: body.subcategory || "",
        }),
      })
    );

    if (!containerResponse.ok) {
      const errorText = await containerResponse.text();
      return NextResponse.json(
        {
          status: "error",
          error: "Container ingest failed",
          details: errorText,
          httpStatus: containerResponse.status,
        },
        { status: 500 }
      );
    }

    const result = await containerResponse.json() as {
      url: string;
      status: string;
      chunks: number;
      uploaded: number;
      errors: string[];
    };

    return NextResponse.json({
      status: "ok",
      message: "Ingest completed successfully",
      result,
    });
  } catch (error) {
    console.error("Ingest trigger error:", error);

    // Check if it's a container startup error
    const errorMessage = String(error);
    if (errorMessage.includes("container") || errorMessage.includes("Container")) {
      return NextResponse.json({
        status: "starting",
        message: "Container is starting up. Please try again in a moment.",
        error: errorMessage,
      });
    }

    return NextResponse.json(
      { status: "error", error: `Failed to trigger ingest: ${error}` },
      { status: 500 }
    );
  }
}

/**
 * GET /api/admin/ingest
 * Check container health status
 */
export async function GET(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();

    if (!verifyAuth(request, env.AUTH_SECRET)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Check if container binding exists
    if (!env.SCRAPER_CONTAINER) {
      return NextResponse.json({
        status: "unavailable",
        message: "Container binding not configured",
        cliAvailable: true,
        cliCommand: "AUTH_SECRET=$AUTH_SECRET npx tsx scripts/diff-migrate.ts --source <URL>",
      });
    }

    // Get a container instance for health check
    const containerId = env.SCRAPER_CONTAINER.idFromName("health-check");
    const container = env.SCRAPER_CONTAINER.get(containerId);

    try {
      const healthResponse = await container.fetch(
        new Request("http://container/health", {
          method: "GET",
        })
      );

      if (healthResponse.ok) {
        const healthData = await healthResponse.json() as { status: string; timestamp: string };
        return NextResponse.json({
          status: "healthy",
          container: healthData,
        });
      }

      return NextResponse.json({
        status: "unhealthy",
        message: `Container returned ${healthResponse.status}`,
      });
    } catch (healthError) {
      return NextResponse.json({
        status: "starting",
        message: "Container may be starting up or sleeping",
        error: String(healthError),
      });
    }
  } catch (error) {
    console.error("Health check error:", error);
    return NextResponse.json(
      { status: "error", error: `Health check failed: ${error}` },
      { status: 500 }
    );
  }
}

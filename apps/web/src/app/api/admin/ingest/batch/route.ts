/**
 * Batch Ingestion API with background processing.
 *
 * POST /api/admin/ingest/batch - Start a batch ingestion job
 * GET /api/admin/ingest/batch?jobId=xxx - Get job status
 *
 * Jobs are stored in KV and processed in background using waitUntil().
 * This allows the browser to close without stopping the ingestion.
 */

import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";

// KV key prefix for batch jobs
const BATCH_JOB_PREFIX = "batch:job:";

interface BatchJob {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  sources: Array<{
    url: string;
    category: string;
    subcategory: string;
  }>;
  progress: {
    current: number;
    total: number;
    succeeded: number;
    failed: number;
  };
  results: Array<{
    url: string;
    status: "success" | "error" | "pending";
    message?: string;
    stylusVersion?: string;
  }>;
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
}

// Generate job ID
function generateJobId(): string {
  return `job_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

// Verify admin auth
function verifyAuth(request: NextRequest, authSecret: string): boolean {
  const adminSecret = request.headers.get("X-Admin-Secret");
  return adminSecret === authSecret;
}

/**
 * GET /api/admin/ingest/batch?jobId=xxx
 * Get job status
 */
export async function GET(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();

    if (!verifyAuth(request, env.AUTH_SECRET)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const jobId = searchParams.get("jobId");

    if (!jobId) {
      // List recent jobs
      const jobs: BatchJob[] = [];
      const list = await env.KV.list({ prefix: BATCH_JOB_PREFIX, limit: 10 });

      for (const key of list.keys) {
        const job = await env.KV.get(key.name, "json") as BatchJob | null;
        if (job) jobs.push(job);
      }

      // Sort by createdAt descending
      jobs.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

      return NextResponse.json({ status: "ok", jobs });
    }

    // Get specific job
    const job = await env.KV.get(`${BATCH_JOB_PREFIX}${jobId}`, "json") as BatchJob | null;

    if (!job) {
      return NextResponse.json({ error: "Job not found" }, { status: 404 });
    }

    return NextResponse.json({ status: "ok", job });
  } catch (error) {
    console.error("Batch job status error:", error);
    return NextResponse.json(
      { error: `Failed to get job status: ${error}` },
      { status: 500 }
    );
  }
}

/**
 * POST /api/admin/ingest/batch
 * Start a batch ingestion job
 * Body: { sources: [{ url, category, subcategory }] }
 */
export async function POST(request: NextRequest) {
  try {
    const { env, ctx } = getCloudflareContext();

    if (!verifyAuth(request, env.AUTH_SECRET)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json() as {
      sources: Array<{
        url: string;
        category: string;
        subcategory?: string;
      }>;
    };

    if (!body.sources || body.sources.length === 0) {
      return NextResponse.json(
        { error: "sources array is required" },
        { status: 400 }
      );
    }

    // Create job
    const jobId = generateJobId();
    const now = new Date().toISOString();

    const job: BatchJob = {
      id: jobId,
      status: "pending",
      sources: body.sources.map((s) => ({
        url: s.url,
        category: s.category,
        subcategory: s.subcategory || "",
      })),
      progress: {
        current: 0,
        total: body.sources.length,
        succeeded: 0,
        failed: 0,
      },
      results: body.sources.map((s) => ({
        url: s.url,
        status: "pending" as const,
      })),
      createdAt: now,
      updatedAt: now,
    };

    // Save job to KV
    await env.KV.put(`${BATCH_JOB_PREFIX}${jobId}`, JSON.stringify(job), {
      expirationTtl: 86400 * 7, // 7 days
    });

    // Process in background using waitUntil
    ctx.waitUntil(processJobInBackground(env, jobId));

    return NextResponse.json({
      status: "ok",
      jobId,
      message: `Started batch ingestion of ${body.sources.length} sources`,
    });
  } catch (error) {
    console.error("Batch job start error:", error);
    return NextResponse.json(
      { error: `Failed to start batch job: ${error}` },
      { status: 500 }
    );
  }
}

/**
 * Process job in background
 */
async function processJobInBackground(env: CloudflareEnv, jobId: string): Promise<void> {
  const jobKey = `${BATCH_JOB_PREFIX}${jobId}`;

  try {
    // Load job
    const job = await env.KV.get(jobKey, "json") as BatchJob | null;
    if (!job) return;

    // Update status to running
    job.status = "running";
    job.updatedAt = new Date().toISOString();
    await env.KV.put(jobKey, JSON.stringify(job));

    // Check if container is available
    const hasContainer = !!env.SCRAPER_CONTAINER;

    // Process each source
    for (let i = 0; i < job.sources.length; i++) {
      const source = job.sources[i];

      try {
        let result: {
          status?: string;
          chunks?: number;
          uploaded?: number;
          stylusVersion?: string;
          error?: string;
          message?: string;
        };

        if (hasContainer) {
          // Use container
          const containerId = env.SCRAPER_CONTAINER.idFromName(source.url);
          const container = env.SCRAPER_CONTAINER.get(containerId);

          const response = await container.fetch(
            new Request("http://container/ingest", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                url: source.url,
                category: source.category,
                subcategory: source.subcategory,
              }),
            })
          );

          result = await response.json() as typeof result;
        } else {
          // No container - mark source as pending for CLI processing
          // Update the source status in KV via internal fetch
          try {
            await fetch("https://arbbuilder.swmengappdev.workers.dev/api/admin/sources", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-Admin-Secret": env.AUTH_SECRET,
              },
              body: JSON.stringify({
                url: source.url,
                category: source.category,
                subcategory: source.subcategory,
                status: "pending",
              }),
            });
          } catch {
            // Ignore fetch errors
          }

          result = {
            status: "queued",
            message: "Marked as pending - run CLI to process",
          };
        }

        // Update result
        job.results[i] = {
          url: source.url,
          status: result.status === "success" || result.status === "partial" || result.status === "queued" ? "success" : "error",
          message: result.status === "success"
            ? `${result.chunks} chunks, ${result.uploaded} uploaded`
            : result.error || result.message || "Unknown error",
          stylusVersion: result.stylusVersion,
        };

        if (result.status === "success" || result.status === "partial" || result.status === "queued") {
          job.progress.succeeded++;
        } else {
          job.progress.failed++;
        }
      } catch (err) {
        job.results[i] = {
          url: source.url,
          status: "error",
          message: `Error: ${err}`,
        };
        job.progress.failed++;
      }

      // Update progress
      job.progress.current = i + 1;
      job.updatedAt = new Date().toISOString();
      await env.KV.put(jobKey, JSON.stringify(job));

      // Small delay between sources to avoid overwhelming
      if (i < job.sources.length - 1) {
        await new Promise((r) => setTimeout(r, 1000));
      }
    }

    // Mark as completed
    job.status = "completed";
    job.completedAt = new Date().toISOString();
    job.updatedAt = job.completedAt;
    await env.KV.put(jobKey, JSON.stringify(job));

  } catch (error) {
    console.error("Background job error:", error);

    // Mark as failed
    try {
      const job = await env.KV.get(jobKey, "json") as BatchJob | null;
      if (job) {
        job.status = "failed";
        job.updatedAt = new Date().toISOString();
        await env.KV.put(jobKey, JSON.stringify(job));
      }
    } catch {
      // Ignore errors when updating failed status
    }
  }
}

/**
 * DELETE /api/admin/ingest/batch?jobId=xxx
 * Delete a job
 */
export async function DELETE(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();

    if (!verifyAuth(request, env.AUTH_SECRET)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const jobId = searchParams.get("jobId");

    if (!jobId) {
      return NextResponse.json({ error: "jobId is required" }, { status: 400 });
    }

    await env.KV.delete(`${BATCH_JOB_PREFIX}${jobId}`);

    return NextResponse.json({ status: "ok", message: "Job deleted" });
  } catch (error) {
    console.error("Delete job error:", error);
    return NextResponse.json(
      { error: `Failed to delete job: ${error}` },
      { status: 500 }
    );
  }
}

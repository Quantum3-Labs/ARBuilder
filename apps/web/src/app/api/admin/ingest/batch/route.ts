/**
 * Batch Ingestion API with Durable Object-based processing.
 *
 * POST /api/admin/ingest/batch - Start a batch ingestion job
 * GET /api/admin/ingest/batch - List all jobs or get specific job
 * DELETE /api/admin/ingest/batch?jobId=xxx - Delete a job
 * PUT /api/admin/ingest/batch?jobId=xxx&action=pause|resume - Pause/resume a job
 *
 * Uses BatchJobDO Durable Object with alarms for reliable long-running processing.
 * Each source is processed in a separate alarm invocation, avoiding timeout issues.
 */

import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";

// KV key prefix for batch jobs (for listing)
const BATCH_JOB_PREFIX = "batch:job:";

interface BatchSource {
  url: string;
  category: string;
  subcategory: string;
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
 * Get job status or list all jobs
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
      // List recent jobs from KV
      const jobs: unknown[] = [];
      const list = await env.KV.list({ prefix: BATCH_JOB_PREFIX, limit: 20 });

      for (const key of list.keys) {
        const job = await env.KV.get(key.name, "json");
        if (job) jobs.push(job);
      }

      // Sort by createdAt descending
      jobs.sort((a, b) => {
        const aJob = a as { createdAt?: string };
        const bJob = b as { createdAt?: string };
        return new Date(bJob.createdAt || 0).getTime() - new Date(aJob.createdAt || 0).getTime();
      });

      return NextResponse.json({ status: "ok", jobs });
    }

    // Get specific job from DO
    if (!env.BATCH_JOB) {
      // Fallback to KV if DO not available
      const job = await env.KV.get(`${BATCH_JOB_PREFIX}${jobId}`, "json");
      if (!job) {
        return NextResponse.json({ error: "Job not found" }, { status: 404 });
      }
      return NextResponse.json({ status: "ok", job });
    }

    const doId = env.BATCH_JOB.idFromName(jobId);
    const stub = env.BATCH_JOB.get(doId);

    const response = await stub.fetch(
      new Request("http://do/status", { method: "GET" })
    );

    if (!response.ok) {
      // Try KV as fallback
      const job = await env.KV.get(`${BATCH_JOB_PREFIX}${jobId}`, "json");
      if (job) {
        return NextResponse.json({ status: "ok", job });
      }
      return NextResponse.json({ error: "Job not found" }, { status: 404 });
    }

    const data = await response.json() as { status: string; job?: unknown };
    return NextResponse.json(data);
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
    const { env } = getCloudflareContext();

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

    // Check if BATCH_JOB DO is available
    if (!env.BATCH_JOB) {
      return NextResponse.json(
        { error: "Batch processing not available (BATCH_JOB binding missing)" },
        { status: 503 }
      );
    }

    // Generate job ID
    const jobId = generateJobId();

    // Normalize sources
    const sources: BatchSource[] = body.sources.map((s) => ({
      url: s.url,
      category: s.category,
      subcategory: s.subcategory || "",
    }));

    // Create DO instance for this job
    const doId = env.BATCH_JOB.idFromName(jobId);
    const stub = env.BATCH_JOB.get(doId);

    // Start the job
    const response = await stub.fetch(
      new Request("http://do/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jobId, sources }),
      })
    );

    if (!response.ok) {
      const error = await response.text();
      return NextResponse.json(
        { error: `Failed to start job: ${error}` },
        { status: 500 }
      );
    }

    const result = await response.json() as { status: string; jobId: string; message: string };

    return NextResponse.json({
      status: "ok",
      jobId: result.jobId,
      message: result.message,
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
 * PUT /api/admin/ingest/batch?jobId=xxx&action=pause|resume
 * Pause or resume a job
 */
export async function PUT(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();

    if (!verifyAuth(request, env.AUTH_SECRET)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const jobId = searchParams.get("jobId");
    const action = searchParams.get("action");

    if (!jobId) {
      return NextResponse.json({ error: "jobId is required" }, { status: 400 });
    }

    if (!action || !["pause", "resume"].includes(action)) {
      return NextResponse.json(
        { error: "action must be 'pause' or 'resume'" },
        { status: 400 }
      );
    }

    if (!env.BATCH_JOB) {
      return NextResponse.json(
        { error: "Batch processing not available" },
        { status: 503 }
      );
    }

    const doId = env.BATCH_JOB.idFromName(jobId);
    const stub = env.BATCH_JOB.get(doId);

    const response = await stub.fetch(
      new Request(`http://do/${action}`, { method: "POST" })
    );

    if (!response.ok) {
      const error = await response.text();
      return NextResponse.json(
        { error: `Failed to ${action} job: ${error}` },
        { status: 500 }
      );
    }

    const result = await response.json() as { status: string; message: string };
    return NextResponse.json(result);
  } catch (error) {
    console.error("Batch job update error:", error);
    return NextResponse.json(
      { error: `Failed to update job: ${error}` },
      { status: 500 }
    );
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

    // Delete from KV
    await env.KV.delete(`${BATCH_JOB_PREFIX}${jobId}`);

    // Delete from DO if available
    if (env.BATCH_JOB) {
      try {
        const doId = env.BATCH_JOB.idFromName(jobId);
        const stub = env.BATCH_JOB.get(doId);

        await stub.fetch(
          new Request("http://do/delete", { method: "DELETE" })
        );
      } catch (e) {
        // Ignore DO deletion errors (may not exist)
        console.log("DO delete error (may be expected):", e);
      }
    }

    return NextResponse.json({ status: "ok", message: "Job deleted" });
  } catch (error) {
    console.error("Delete job error:", error);
    return NextResponse.json(
      { error: `Failed to delete job: ${error}` },
      { status: 500 }
    );
  }
}

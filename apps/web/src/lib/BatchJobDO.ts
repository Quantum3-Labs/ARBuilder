/**
 * BatchJobDO - Durable Object for reliable batch source ingestion.
 *
 * Uses DO alarms for long-running processing without timeout issues.
 * Each source is processed in a separate alarm invocation.
 *
 * Flow:
 * 1. POST /batch creates job, stores in DO, schedules first alarm
 * 2. Alarm processes one source, updates state, schedules next alarm
 * 3. GET /batch returns current job state from DO
 * 4. Job completes when all sources are processed
 */

import { DurableObject } from "cloudflare:workers";

export interface BatchSource {
  url: string;
  category: string;
  subcategory: string;
}

export interface BatchResult {
  url: string;
  status: "success" | "error" | "pending" | "processing";
  message?: string;
  stylusVersion?: string | null;
  isVersionDeprecated?: boolean;
}

export interface BatchJob {
  id: string;
  status: "pending" | "running" | "completed" | "failed" | "paused";
  sources: BatchSource[];
  progress: {
    current: number;
    total: number;
    succeeded: number;
    failed: number;
  };
  results: BatchResult[];
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
  error?: string;
}

interface Env {
  SCRAPER_CONTAINER: DurableObjectNamespace;
  AUTH_SECRET: string;
  KV: KVNamespace;
}

export class BatchJobDO extends DurableObject<Env> {
  private job: BatchJob | null = null;

  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
  }

  /**
   * Initialize job state from storage
   */
  private async loadJob(): Promise<BatchJob | null> {
    if (this.job) return this.job;
    const storedJob = await this.ctx.storage.get<BatchJob>("job");
    this.job = storedJob ?? null;
    return this.job;
  }

  /**
   * Save job state to storage
   */
  private async saveJob(): Promise<void> {
    if (this.job) {
      this.job.updatedAt = new Date().toISOString();
      await this.ctx.storage.put("job", this.job);
      // Also sync to KV for listing
      await this.syncToKV();
    }
  }

  /**
   * Sync job state to KV for listing/querying
   */
  private async syncToKV(): Promise<void> {
    if (this.job) {
      try {
        await this.env.KV.put(
          `batch:job:${this.job.id}`,
          JSON.stringify(this.job),
          { expirationTtl: 86400 * 7 } // 7 days
        );
      } catch (e) {
        console.error("Failed to sync to KV:", e);
      }
    }
  }

  /**
   * Handle HTTP requests to this DO
   */
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    try {
      if (request.method === "POST" && path === "/start") {
        return await this.handleStart(request);
      }

      if (request.method === "GET" && path === "/status") {
        return await this.handleStatus();
      }

      if (request.method === "POST" && path === "/pause") {
        return await this.handlePause();
      }

      if (request.method === "POST" && path === "/resume") {
        return await this.handleResume();
      }

      if (request.method === "DELETE" && path === "/delete") {
        return await this.handleDelete();
      }

      return new Response(JSON.stringify({ error: "Not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      console.error("BatchJobDO error:", error);
      return new Response(
        JSON.stringify({ error: String(error) }),
        { status: 500, headers: { "Content-Type": "application/json" } }
      );
    }
  }

  /**
   * Start a new batch job
   */
  private async handleStart(request: Request): Promise<Response> {
    const body = await request.json() as {
      jobId: string;
      sources: BatchSource[];
    };

    // Check if job already exists
    const existingJob = await this.loadJob();
    if (existingJob && existingJob.status === "running") {
      return new Response(
        JSON.stringify({
          error: "Job already running",
          jobId: existingJob.id,
        }),
        { status: 409, headers: { "Content-Type": "application/json" } }
      );
    }

    // Create new job
    const now = new Date().toISOString();
    this.job = {
      id: body.jobId,
      status: "running",
      sources: body.sources,
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

    await this.saveJob();

    // Schedule first alarm immediately
    await this.ctx.storage.setAlarm(Date.now() + 100);

    return new Response(
      JSON.stringify({
        status: "ok",
        jobId: this.job.id,
        message: `Started batch job with ${body.sources.length} sources`,
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  }

  /**
   * Get job status
   */
  private async handleStatus(): Promise<Response> {
    const job = await this.loadJob();

    if (!job) {
      return new Response(
        JSON.stringify({ error: "No job found" }),
        { status: 404, headers: { "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ status: "ok", job }),
      { headers: { "Content-Type": "application/json" } }
    );
  }

  /**
   * Pause the job
   */
  private async handlePause(): Promise<Response> {
    const job = await this.loadJob();

    if (!job) {
      return new Response(
        JSON.stringify({ error: "No job found" }),
        { status: 404, headers: { "Content-Type": "application/json" } }
      );
    }

    if (job.status !== "running") {
      return new Response(
        JSON.stringify({ error: "Job is not running" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    job.status = "paused";
    await this.saveJob();

    // Cancel any pending alarm
    await this.ctx.storage.deleteAlarm();

    return new Response(
      JSON.stringify({ status: "ok", message: "Job paused" }),
      { headers: { "Content-Type": "application/json" } }
    );
  }

  /**
   * Resume a paused job
   */
  private async handleResume(): Promise<Response> {
    const job = await this.loadJob();

    if (!job) {
      return new Response(
        JSON.stringify({ error: "No job found" }),
        { status: 404, headers: { "Content-Type": "application/json" } }
      );
    }

    if (job.status !== "paused") {
      return new Response(
        JSON.stringify({ error: "Job is not paused" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    job.status = "running";
    await this.saveJob();

    // Schedule next alarm
    await this.ctx.storage.setAlarm(Date.now() + 100);

    return new Response(
      JSON.stringify({ status: "ok", message: "Job resumed" }),
      { headers: { "Content-Type": "application/json" } }
    );
  }

  /**
   * Delete the job
   */
  private async handleDelete(): Promise<Response> {
    const job = await this.loadJob();

    if (job) {
      // Delete from KV
      try {
        await this.env.KV.delete(`batch:job:${job.id}`);
      } catch (e) {
        console.error("Failed to delete from KV:", e);
      }
    }

    // Clear storage
    await this.ctx.storage.deleteAll();
    this.job = null;

    return new Response(
      JSON.stringify({ status: "ok", message: "Job deleted" }),
      { headers: { "Content-Type": "application/json" } }
    );
  }

  /**
   * Alarm handler - processes one source at a time
   */
  async alarm(): Promise<void> {
    const job = await this.loadJob();

    if (!job) {
      console.log("No job found in alarm");
      return;
    }

    // Check if job should continue
    if (job.status !== "running") {
      console.log(`Job status is ${job.status}, not processing`);
      return;
    }

    // Check if all sources are processed
    if (job.progress.current >= job.sources.length) {
      job.status = "completed";
      job.completedAt = new Date().toISOString();
      await this.saveJob();
      console.log(`Job ${job.id} completed`);
      return;
    }

    // Get next source to process
    const sourceIndex = job.progress.current;
    const source = job.sources[sourceIndex];

    console.log(`Processing source ${sourceIndex + 1}/${job.sources.length}: ${source.url}`);

    // Mark as processing
    job.results[sourceIndex].status = "processing";
    await this.saveJob();

    try {
      // Process the source using the container
      const result = await this.processSource(source);

      // Update result
      job.results[sourceIndex] = {
        url: source.url,
        status: result.success ? "success" : "error",
        message: result.message,
        stylusVersion: result.stylusVersion,
        isVersionDeprecated: result.isVersionDeprecated,
      };

      if (result.success) {
        job.progress.succeeded++;
      } else {
        job.progress.failed++;
      }
    } catch (error) {
      console.error(`Error processing ${source.url}:`, error);
      job.results[sourceIndex] = {
        url: source.url,
        status: "error",
        message: `Processing error: ${error}`,
      };
      job.progress.failed++;
    }

    // Increment progress
    job.progress.current++;
    await this.saveJob();

    // Schedule next alarm if more sources remain
    if (job.progress.current < job.sources.length && job.status === "running") {
      // Small delay between sources (1 second)
      await this.ctx.storage.setAlarm(Date.now() + 1000);
    } else if (job.progress.current >= job.sources.length) {
      // All done
      job.status = "completed";
      job.completedAt = new Date().toISOString();
      await this.saveJob();
      console.log(`Job ${job.id} completed: ${job.progress.succeeded} succeeded, ${job.progress.failed} failed`);
    }
  }

  /**
   * Process a single source using the scraper container
   */
  private async processSource(source: BatchSource): Promise<{
    success: boolean;
    message: string;
    stylusVersion?: string | null;
    isVersionDeprecated?: boolean;
  }> {
    // Check if container is available
    if (!this.env.SCRAPER_CONTAINER) {
      return {
        success: false,
        message: "Container binding not available",
      };
    }

    try {
      // Get shared container instance
      const containerId = this.env.SCRAPER_CONTAINER.idFromName("shared-scraper-v6");
      const container = this.env.SCRAPER_CONTAINER.get(containerId);

      // Send ingest request
      const response = await container.fetch(
        new Request("http://container/ingest", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: source.url,
            category: source.category,
            subcategory: source.subcategory,
            auth_secret: this.env.AUTH_SECRET,
          }),
        })
      );

      if (!response.ok) {
        const errorText = await response.text();
        return {
          success: false,
          message: `Container HTTP ${response.status}: ${errorText.slice(0, 200)}`,
        };
      }

      const result = await response.json() as {
        status: string;
        chunks?: number;
        uploaded?: number;
        stylusVersion?: string | null;
        isVersionDeprecated?: boolean;
        errors?: string[];
      };

      const success = result.status === "success" || result.status === "partial";

      return {
        success,
        message: success
          ? `${result.chunks} chunks, ${result.uploaded} uploaded`
          : result.errors?.join("; ") || "Unknown error",
        stylusVersion: result.stylusVersion,
        isVersionDeprecated: result.isVersionDeprecated,
      };
    } catch (error) {
      // Check if container is starting up
      const errorStr = String(error);
      if (errorStr.includes("not running") || errorStr.includes("start()")) {
        // Retry by re-scheduling the alarm
        console.log("Container not ready, will retry...");
        throw new Error("Container starting up, retrying...");
      }
      throw error;
    }
  }
}

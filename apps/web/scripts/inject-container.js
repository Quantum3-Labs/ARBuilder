/**
 * Post-build script to inject Durable Object classes into the generated worker.
 *
 * This is needed because OpenNext generates its own worker.js, and we need to
 * add our Cloudflare Container and BatchJob classes for Durable Objects support.
 */

const fs = require('fs');
const path = require('path');

const workerPath = path.join(__dirname, '../.open-next/worker.js');

// Read the generated worker
let workerCode = fs.readFileSync(workerPath, 'utf-8');

// Check if already injected
if (workerCode.includes('ScraperContainer') && workerCode.includes('BatchJobDO')) {
  console.log('Durable Objects already injected, skipping...');
  process.exit(0);
}

// Classes to inject - external modules resolved by wrangler
const containerCode = `
// ===== Injected Durable Objects for Cloudflare =====
//@ts-expect-error: Will be resolved by wrangler
import { Container } from "@cloudflare/containers";
//@ts-expect-error: Will be resolved by wrangler
import { DurableObject } from "cloudflare:workers";

/**
 * ScraperContainer - Durable Object-backed container for Python scraper.
 * Runs the Python Flask server that handles source re-ingestion.
 */
export class ScraperContainer extends Container {
  defaultPort = 8080;
  sleepAfter = "5m";
}

/**
 * BatchJobDO - Durable Object for reliable batch source ingestion.
 * Uses alarms for long-running processing without timeout issues.
 */
export class BatchJobDO extends DurableObject {
  job = null;

  async loadJob() {
    if (this.job) return this.job;
    const storedJob = await this.ctx.storage.get("job");
    this.job = storedJob ?? null;
    return this.job;
  }

  async saveJob() {
    if (this.job) {
      this.job.updatedAt = new Date().toISOString();
      await this.ctx.storage.put("job", this.job);
      await this.syncToKV();
    }
  }

  async syncToKV() {
    if (this.job) {
      try {
        await this.env.KV.put(
          \`batch:job:\${this.job.id}\`,
          JSON.stringify(this.job),
          { expirationTtl: 86400 * 7 }
        );
      } catch (e) {
        console.error("Failed to sync to KV:", e);
      }
    }
  }

  async fetch(request) {
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

  async handleStart(request) {
    const body = await request.json();
    const existingJob = await this.loadJob();
    if (existingJob && existingJob.status === "running") {
      return new Response(
        JSON.stringify({ error: "Job already running", jobId: existingJob.id }),
        { status: 409, headers: { "Content-Type": "application/json" } }
      );
    }

    const now = new Date().toISOString();
    this.job = {
      id: body.jobId,
      status: "running",
      sources: body.sources,
      progress: { current: 0, total: body.sources.length, succeeded: 0, failed: 0 },
      results: body.sources.map((s) => ({ url: s.url, status: "pending" })),
      createdAt: now,
      updatedAt: now,
    };

    await this.saveJob();
    await this.ctx.storage.setAlarm(Date.now() + 100);

    return new Response(
      JSON.stringify({ status: "ok", jobId: this.job.id, message: \`Started batch job with \${body.sources.length} sources\` }),
      { headers: { "Content-Type": "application/json" } }
    );
  }

  async handleStatus() {
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

  async handlePause() {
    const job = await this.loadJob();
    if (!job) {
      return new Response(JSON.stringify({ error: "No job found" }), { status: 404, headers: { "Content-Type": "application/json" } });
    }
    if (job.status !== "running") {
      return new Response(JSON.stringify({ error: "Job is not running" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }
    job.status = "paused";
    await this.saveJob();
    await this.ctx.storage.deleteAlarm();
    return new Response(JSON.stringify({ status: "ok", message: "Job paused" }), { headers: { "Content-Type": "application/json" } });
  }

  async handleResume() {
    const job = await this.loadJob();
    if (!job) {
      return new Response(JSON.stringify({ error: "No job found" }), { status: 404, headers: { "Content-Type": "application/json" } });
    }
    if (job.status !== "paused") {
      return new Response(JSON.stringify({ error: "Job is not paused" }), { status: 400, headers: { "Content-Type": "application/json" } });
    }
    job.status = "running";
    await this.saveJob();
    await this.ctx.storage.setAlarm(Date.now() + 100);
    return new Response(JSON.stringify({ status: "ok", message: "Job resumed" }), { headers: { "Content-Type": "application/json" } });
  }

  async handleDelete() {
    const job = await this.loadJob();
    if (job) {
      try {
        await this.env.KV.delete(\`batch:job:\${job.id}\`);
      } catch (e) {
        console.error("Failed to delete from KV:", e);
      }
    }
    await this.ctx.storage.deleteAll();
    this.job = null;
    return new Response(JSON.stringify({ status: "ok", message: "Job deleted" }), { headers: { "Content-Type": "application/json" } });
  }

  async alarm() {
    const job = await this.loadJob();
    if (!job || job.status !== "running") {
      return;
    }

    if (job.progress.current >= job.sources.length) {
      job.status = "completed";
      job.completedAt = new Date().toISOString();
      await this.saveJob();
      return;
    }

    const sourceIndex = job.progress.current;
    const source = job.sources[sourceIndex];
    const retryCount = job.results[sourceIndex].retryCount || 0;
    console.log(\`Processing source \${sourceIndex + 1}/\${job.sources.length}: \${source.url} (retry: \${retryCount})\`);

    job.results[sourceIndex].status = "processing";
    await this.saveJob();

    try {
      const result = await this.processSource(source);
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
      job.progress.current++;
    } catch (error) {
      const errorStr = String(error);
      console.error(\`Error processing \${source.url}:\`, errorStr);

      // Retry if container is starting up (max 3 retries)
      if ((errorStr.includes("not running") || errorStr.includes("start()") || errorStr.includes("retrying")) && retryCount < 3) {
        console.log(\`Container starting, will retry in 5 seconds (retry \${retryCount + 1}/3)\`);
        job.results[sourceIndex] = { url: source.url, status: "pending", retryCount: retryCount + 1 };
        await this.saveJob();
        await this.ctx.storage.setAlarm(Date.now() + 5000);
        return;
      }

      job.results[sourceIndex] = { url: source.url, status: "error", message: \`Processing error: \${errorStr.slice(0, 200)}\` };
      job.progress.failed++;
      job.progress.current++;
    }

    await this.saveJob();

    if (job.progress.current < job.sources.length && job.status === "running") {
      await this.ctx.storage.setAlarm(Date.now() + 1000);
    } else if (job.progress.current >= job.sources.length) {
      job.status = "completed";
      job.completedAt = new Date().toISOString();
      await this.saveJob();
    }
  }

  async processSource(source) {
    if (!this.env.SCRAPER_CONTAINER) {
      return { success: false, message: "Container binding not available" };
    }

    try {
      const containerId = this.env.SCRAPER_CONTAINER.idFromName("shared-scraper-v11");
      const container = this.env.SCRAPER_CONTAINER.get(containerId);

      // Create AbortController with 7 minute timeout (5min processing + 2min cold start buffer)
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 420000); // 7 min timeout

      try {
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
            signal: controller.signal,
          })
        );
        clearTimeout(timeoutId);

        if (!response.ok) {
          const errorText = await response.text();
          return { success: false, message: \`Container HTTP \${response.status}: \${errorText.slice(0, 200)}\` };
        }

        const result = await response.json();
        const success = result.status === "success" || result.status === "partial";

        return {
          success,
          message: success
            ? \`\${result.chunks} chunks, \${result.uploaded} uploaded\`
            : result.errors?.join("; ") || "Unknown error",
          stylusVersion: result.stylusVersion,
          isVersionDeprecated: result.isVersionDeprecated,
        };
      } catch (fetchError) {
        clearTimeout(timeoutId);
        if (fetchError.name === "AbortError") {
          return { success: false, message: "Container request timed out after 7 minutes" };
        }
        throw fetchError;
      }
    } catch (error) {
      const errorStr = String(error);
      if (errorStr.includes("not running") || errorStr.includes("start()")) {
        throw new Error("Container starting up, retrying...");
      }
      throw error;
    }
  }
}
// ===== End Durable Objects injection =====

`;

// Inject at the beginning of the file, after any initial comments
const injectionPoint = workerCode.indexOf('import');
if (injectionPoint === -1) {
  // No imports found, inject at the beginning
  workerCode = containerCode + workerCode;
} else {
  // Inject before the first import
  workerCode = workerCode.slice(0, injectionPoint) + containerCode + workerCode.slice(injectionPoint);
}

// Write back
fs.writeFileSync(workerPath, workerCode);

console.log('✅ ScraperContainer and BatchJobDO injected into worker.js');

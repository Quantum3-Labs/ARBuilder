/**
 * Custom Worker for OpenNext.js.
 *
 * Wraps the generated OpenNext handler.
 * Includes:
 * - scheduled handler for periodic source ingestion via cron
 * - queue handler for async ingestion of large repos
 *
 * Queue handler calls pipeline functions DIRECTLY (no HTTP roundtrip)
 * to avoid the 30s wall clock limit on self-reference fetches.
 * Cron handler still uses self-reference since it triggers a full
 * ingest cycle that benefits from the Next.js route handler context.
 */

// @ts-ignore - Generated at build time
import { default as handler } from "./.open-next/worker.js";

// Re-export OpenNext DO handlers if using caching
// @ts-ignore - Generated at build time
export { DOQueueHandler, DOShardedTagCache } from "./.open-next/worker.js";

// Direct imports for queue handler (avoids self-reference HTTP roundtrip)
import {
  handleEmbedMessage,
  handleContinueMessage,
  handleFinalizeMessage,
} from "./src/lib/ingestPipeline";

/**
 * Main worker handler
 */
export default {
  fetch: handler.fetch,

  /**
   * Cron-triggered ingestion handler.
   * Picks the next pending/stale source and ingests it.
   * Configured in wrangler.jsonc: triggers.crons
   */
  async scheduled(
    _controller: ScheduledController,
    env: CloudflareEnv,
    ctx: ExecutionContext
  ) {
    ctx.waitUntil(handleCronIngestion(env));
  },

  /**
   * Queue consumer for async ingestion.
   * Calls pipeline functions DIRECTLY — no HTTP roundtrip via self-reference.
   * max_batch_size=1 in wrangler config ensures one message per invocation.
   */
  async queue(
    batch: MessageBatch,
    env: CloudflareEnv
  ) {
    for (const msg of batch.messages) {
      try {
        await handleQueueMessage(msg.body as QueueMessage, env);
        msg.ack();
      } catch (err) {
        console.error("Queue message failed:", err);
        msg.retry();
      }
    }
  },
} satisfies ExportedHandler<CloudflareEnv>;

// --- Queue message types (must match ingestPipeline.ts) ---

type QueueMessage =
  | { type: "embed"; sourceId: string; url: string; batchIndex: number }
  | { type: "continue"; sourceId: string; url: string; category: string; subcategory?: string; fileOffset: number; totalFiles: number; sdkVersion?: string; token?: string }
  | { type: "finalize"; sourceId: string; url: string; sdkVersion?: string };

/**
 * Dispatch queue messages directly to pipeline handlers.
 * No HTTP roundtrip — avoids 30s wall clock timeout on self-reference fetches.
 */
async function handleQueueMessage(msg: QueueMessage, env: CloudflareEnv) {
  switch (msg.type) {
    case "embed":
      await handleEmbedMessage(msg, env);
      break;
    case "continue":
      await handleContinueMessage(msg, env);
      break;
    case "finalize":
      await handleFinalizeMessage(msg, env);
      break;
    default:
      console.error("Unknown queue message type:", msg);
  }
  console.log(`Queue ${msg.type}: done for ${msg.sourceId}`);
}

/**
 * Handle cron-triggered ingestion.
 * Uses self-reference to call the ingest API endpoint.
 */
async function handleCronIngestion(env: CloudflareEnv) {
  try {
    if (!env.WORKER_SELF_REFERENCE) {
      console.error("Cron: WORKER_SELF_REFERENCE binding not available");
      return;
    }

    const response = await env.WORKER_SELF_REFERENCE.fetch(
      "https://internal/api/admin/ingest",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Secret": env.AUTH_SECRET,
        },
        body: JSON.stringify({ action: "process_next" }),
      }
    );

    if (!response.ok) {
      console.error(
        `Cron ingestion failed: HTTP ${response.status}`,
        await response.text()
      );
    } else {
      const result = await response.json();
      console.log("Cron ingestion result:", JSON.stringify(result));
    }
  } catch (err) {
    console.error("Cron ingestion error:", err);
  }
}

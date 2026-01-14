/**
 * Custom Worker for OpenNext.js with Cloudflare Containers support.
 *
 * This worker wraps the generated OpenNext handler and adds:
 * - ScraperContainer: Durable Object-backed container for Python scraper
 * - BatchJobDO: Durable Object for reliable batch processing with alarms
 *
 * The container runs the Python scraper for re-ingesting documentation
 * and GitHub repos into Cloudflare Vectorize.
 */

// @ts-ignore - Generated at build time
import { default as handler } from "./.open-next/worker.js";

// Import Container utilities from Cloudflare
import { Container, getContainer } from "@cloudflare/containers";

// Import BatchJobDO for batch processing
export { BatchJobDO } from "./src/lib/BatchJobDO";

/**
 * ScraperContainer - Durable Object-backed container for Python scraper.
 *
 * Runs the Python Flask server that handles:
 * - POST /ingest - Scrape, chunk, and upload a source to Vectorize
 * - GET /health - Health check
 */
export class ScraperContainer extends Container {
  // Port the Flask server listens on
  defaultPort = 8080;

  // Sleep after 5 minutes of inactivity to save resources
  sleepAfter = "5m";

  // Maximum memory for the container
  // memory = "256Mi";
}

// Re-export OpenNext DO handlers if using caching
// @ts-ignore - Generated at build time
export { DOQueueHandler, DOShardedTagCache } from "./.open-next/worker.js";

/**
 * Main worker handler
 */
export default {
  fetch: handler.fetch,
} satisfies ExportedHandler<CloudflareEnv>;

/**
 * Helper to get a scraper container instance.
 * Used by API routes to trigger re-ingestion.
 */
export function getScraperContainer(
  binding: DurableObjectNamespace<ScraperContainer>,
  sourceUrl: string
): DurableObjectStub<ScraperContainer> {
  // Use source URL hash as the container instance ID
  // This ensures the same source always goes to the same container
  return getContainer(binding, sourceUrl);
}

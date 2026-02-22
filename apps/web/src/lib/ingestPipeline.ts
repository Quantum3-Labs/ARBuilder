/**
 * Ingestion pipeline orchestrator for Worker-native ingestion.
 *
 * Two paths:
 * - **Sync** (small sources ≤30 files or doc pages): scrape → chunk → embed → upsert in one invocation.
 * - **Async** (large repos >30 files): scrape → chunk → enqueue batches to INGEST_QUEUE → consumer embeds/upserts.
 *
 * Uses direct env.AI and env.VECTORIZE bindings (no HTTP roundtrip).
 */

import { scrapeDocumentation } from "./scraper";
import { scrapeGithubRepo, type ScrapedRepo } from "./github";
import { chunkDocument, chunkCode, type ProcessedChunk } from "./chunker";

// KV key for the source registry (matches sources/route.ts)
const SOURCES_KEY = "rag:sources:registry";
const PROGRESS_PREFIX = "ingest:progress:";
const CHUNKS_PREFIX = "ingest:chunks:"; // Chunk batches stored here for queue consumer

// Subrequest-safe limits
const SYNC_FILE_LIMIT = 30; // Max files for sync path (30 fetches + embedding + upsert ≈ 40 subrequests)
const QUEUE_CHUNK_BATCH = 10; // Chunks per queue message (2 embed + 1 upsert = 3 subrequests)
const CONTINUE_FILE_BATCH = 30; // Files per "continue" batch

export interface IngestResult {
  sourceId: string;
  url: string;
  status: "success" | "partial" | "error" | "queued";
  chunks: number;
  embedded: number;
  failed: number;
  errors: string[];
  sdkVersion?: string;
  durationMs: number;
}

export interface IngestOptions {
  githubToken?: string;
  maxFilesPerBatch?: number;
  embeddingBatchSize?: number;
  vectorizeBatchSize?: number;
}

interface Source {
  id: string;
  url: string;
  sourceType: "documentation" | "github";
  category: string;
  subcategory: string;
  stylusVersion?: string;
  isVersionDeprecated?: boolean;
  branch?: string;
  status: "active" | "pending" | "error" | "removed" | "processing";
  lastScraped?: string;
  lastProcessed?: string;
  chunkCount: number;
  lastError?: string;
  errorCount: number;
  createdAt: string;
  updatedAt: string;
}

interface SourcesRegistry {
  version: string;
  lastSync?: string;
  totalChunks: number;
  sources: Record<string, Source>;
}

interface IngestProgress {
  sourceId: string;
  url: string;
  phase: "scraping" | "embedding" | "complete";
  totalChunks: number;
  embeddedChunks: number;
  failedChunks: number;
  pendingMessages: number;
  errors: string[];
  sdkVersion?: string;
  startedAt: string;
  updatedAt: string;
}

// Env type for the pipeline (includes optional Queue)
interface PipelineEnv {
  AI: Ai;
  VECTORIZE: VectorizeIndex;
  KV: KVNamespace;
  INGEST_QUEUE?: Queue;
}

// --- Queue message types ---

export type QueueMessage =
  | EmbedMessage
  | ContinueMessage
  | FinalizeMessage;

interface EmbedMessage {
  type: "embed";
  sourceId: string;
  url: string;
  batchIndex: number; // Chunks stored in KV at ingest:chunks:{sourceId}:{batchIndex}
}

interface ContinueMessage {
  type: "continue";
  sourceId: string;
  url: string;
  category: string;
  subcategory?: string;
  fileOffset: number;
  totalFiles: number;
  sdkVersion?: string;
  branch?: string;
  token?: string;
}

interface FinalizeMessage {
  type: "finalize";
  sourceId: string;
  url: string;
  sdkVersion?: string;
}

/**
 * Main entry point: ingest a single source.
 * Uses sync path for small sources, async queue path for large repos.
 */
export async function ingestSource(
  source: { url: string; category: string; subcategory?: string; sourceType?: string; branch?: string },
  env: PipelineEnv,
  options: IngestOptions = {}
): Promise<IngestResult> {
  const startTime = Date.now();
  const idKey = source.branch ? `${source.url}#${source.branch}` : source.url;
  const sourceId = generateSourceId(idKey);
  const {
    githubToken,
    embeddingBatchSize = 5,
    vectorizeBatchSize = 20,
  } = options;

  const result: IngestResult = {
    sourceId,
    url: source.url,
    status: "error",
    chunks: 0,
    embedded: 0,
    failed: 0,
    errors: [],
    durationMs: 0,
  };

  try {
    const isGithub =
      source.sourceType === "github" || source.url.includes("github.com");

    if (isGithub) {
      // Scrape first batch of files
      const repo: ScrapedRepo = await scrapeGithubRepo(
        source.url,
        githubToken,
        SYNC_FILE_LIMIT,
        undefined, // fileOffset
        source.branch
      );

      result.sdkVersion = repo.sdkVersion;
      const chunks = await chunkRepoFiles(repo, source);
      result.chunks = chunks.length;

      const isLargeRepo = repo.totalFiles > SYNC_FILE_LIMIT;
      const queue = env.INGEST_QUEUE;

      if (isLargeRepo && queue) {
        // --- ASYNC PATH: enqueue chunks for background processing ---
        const progress: IngestProgress = {
          sourceId,
          url: source.url,
          phase: "embedding",
          totalChunks: chunks.length, // Will grow as "continue" messages add more
          embeddedChunks: 0,
          failedChunks: 0,
          pendingMessages: 0,
          errors: [],
          sdkVersion: repo.sdkVersion,
          startedAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };

        // Save chunk batches to KV, enqueue lightweight references
        let messageCount = 0;
        let batchIndex = 0;
        for (let i = 0; i < chunks.length; i += QUEUE_CHUNK_BATCH) {
          const batch = chunks.slice(i, i + QUEUE_CHUNK_BATCH);
          await env.KV.put(
            `${CHUNKS_PREFIX}${sourceId}:${batchIndex}`,
            JSON.stringify(batch),
            { expirationTtl: 86400 }
          );
          await queue.send({
            type: "embed",
            sourceId,
            url: source.url,
            batchIndex,
          } satisfies EmbedMessage);
          messageCount++;
          batchIndex++;
        }

        // Enqueue "continue" for remaining files
        if (repo.totalFiles > SYNC_FILE_LIMIT) {
          await queue.send({
            type: "continue",
            sourceId,
            url: source.url,
            category: source.category,
            subcategory: source.subcategory,
            fileOffset: SYNC_FILE_LIMIT,
            totalFiles: repo.totalFiles,
            sdkVersion: repo.sdkVersion,
            branch: source.branch,
            token: githubToken,
          } satisfies ContinueMessage);
          messageCount++;
        }

        // No finalize message — last embed/continue handler auto-finalizes when pendingMessages hits 0

        progress.pendingMessages = messageCount;
        await env.KV.put(
          PROGRESS_PREFIX + sourceId,
          JSON.stringify(progress),
          { expirationTtl: 86400 } // 24h TTL
        );

        // Mark source as processing
        await updateSourceProcessing(env, source.url, sourceId);

        result.status = "queued";
        result.chunks = chunks.length;
        result.durationMs = Date.now() - startTime;
        return result;
      }

      // --- SYNC PATH: small repo, embed in-place ---
      if (chunks.length === 0) {
        result.errors.push("No chunks generated");
        result.durationMs = Date.now() - startTime;
        await updateSourceStatus(env, source.url, result);
        return result;
      }

      const embedResult = await embedAndUpsert(chunks, env, embeddingBatchSize, vectorizeBatchSize);
      result.embedded = embedResult.embedded;
      result.failed = embedResult.failed;
      result.errors.push(...embedResult.errors);
      result.status = result.failed === 0 ? "success" : result.embedded > 0 ? "partial" : "error";
    } else {
      // --- DOC PAGE: always sync ---
      const doc = await scrapeDocumentation(source.url);
      result.sdkVersion = doc.stylusVersion;

      const chunks = await chunkDocument(doc.content, {
        url: source.url,
        title: doc.title,
        category: source.category,
        source: "documentation",
      });

      result.chunks = chunks.length;

      if (chunks.length === 0) {
        result.errors.push("No chunks generated");
        result.durationMs = Date.now() - startTime;
        await updateSourceStatus(env, source.url, result);
        return result;
      }

      const embedResult = await embedAndUpsert(chunks, env, embeddingBatchSize, vectorizeBatchSize);
      result.embedded = embedResult.embedded;
      result.failed = embedResult.failed;
      result.errors.push(...embedResult.errors);
      result.status = result.failed === 0 ? "success" : result.embedded > 0 ? "partial" : "error";
    }
  } catch (err) {
    result.errors.push(String(err));
  }

  result.durationMs = Date.now() - startTime;

  try {
    await updateSourceStatus(env, source.url, result);
  } catch (err) {
    result.errors.push(`Failed to update source status: ${err}`);
  }

  return result;
}

// --- Queue message handlers (called from worker.ts) ---

/**
 * Handle "embed" queue message: load chunks from KV, embed, and upsert to Vectorize.
 */
export async function handleEmbedMessage(
  msg: EmbedMessage,
  env: PipelineEnv
): Promise<void> {
  const { sourceId, batchIndex } = msg;
  const progressKey = PROGRESS_PREFIX + sourceId;
  const chunksKey = `${CHUNKS_PREFIX}${sourceId}:${batchIndex}`;

  let embedResult = { embedded: 0, failed: 0, errors: [] as string[] };

  try {
    // Load chunks from KV
    const chunks = (await env.KV.get(chunksKey, "json")) as ProcessedChunk[] | null;
    if (!chunks || chunks.length === 0) {
      console.error(`No chunks found at ${chunksKey}`);
      return; // Still decrements pendingMessages in finally
    }

    // Truncate oversized chunks to stay under BGE-M3's 60K token limit (~4 chars/token)
    // 20K chars ≈ 5K tokens per chunk × 5 per batch = 25K tokens (well within 60K)
    const MAX_CHARS = 20_000;
    const safeChunks = chunks.map((c) =>
      c.content.length > MAX_CHARS
        ? { ...c, content: c.content.slice(0, MAX_CHARS) }
        : c
    );

    embedResult = await embedAndUpsert(safeChunks, env, 5, 20);

    // Clean up chunk data from KV
    await env.KV.delete(chunksKey);
  } catch (err) {
    embedResult.errors.push(`Embed handler error for batch ${batchIndex}: ${err}`);
    console.error(`Embed handler error for ${sourceId}:${batchIndex}:`, err);
  } finally {
    // ALWAYS decrement pendingMessages, even on error/early-return
    const progress = (await env.KV.get(progressKey, "json")) as IngestProgress | null;
    if (progress) {
      progress.embeddedChunks += embedResult.embedded;
      progress.failedChunks += embedResult.failed;
      progress.pendingMessages = Math.max(0, progress.pendingMessages - 1);
      progress.errors.push(...embedResult.errors);
      progress.updatedAt = new Date().toISOString();
      await env.KV.put(progressKey, JSON.stringify(progress), { expirationTtl: 86400 });

      // Auto-finalize if this was the last message
      if (progress.pendingMessages === 0) {
        await finalizeIngestion(sourceId, msg.url, progress, env);
      }
    }
  }
}

/**
 * Handle "continue" queue message: fetch next batch of files, chunk, and enqueue more embed messages.
 */
export async function handleContinueMessage(
  msg: ContinueMessage,
  env: PipelineEnv
): Promise<void> {
  const { sourceId, url, category, subcategory, fileOffset, sdkVersion, branch, token } = msg;
  const progressKey = PROGRESS_PREFIX + sourceId;

  let newChunks = 0;
  let newMessages = 0;

  try {
    const repo = await scrapeGithubRepo(url, token, CONTINUE_FILE_BATCH, fileOffset, branch);
    const chunks = await chunkRepoFiles(repo, { url, category, subcategory });
    newChunks = chunks.length;

    // Save chunks to KV, enqueue lightweight references
    const continueQueue = env.INGEST_QUEUE;
    if (continueQueue) {
      // Determine next batch index from progress
      const existingProgress = (await env.KV.get(progressKey, "json")) as IngestProgress | null;
      let batchIndex = existingProgress ? Math.ceil(existingProgress.totalChunks / QUEUE_CHUNK_BATCH) : 0;

      for (let i = 0; i < chunks.length; i += QUEUE_CHUNK_BATCH) {
        const batch = chunks.slice(i, i + QUEUE_CHUNK_BATCH);
        await env.KV.put(
          `${CHUNKS_PREFIX}${sourceId}:${batchIndex}`,
          JSON.stringify(batch),
          { expirationTtl: 86400 }
        );
        await continueQueue.send({
          type: "embed",
          sourceId,
          url,
          batchIndex,
        } satisfies EmbedMessage);
        newMessages++;
        batchIndex++;
      }

      // If there are still more files, enqueue another continue
      const nextOffset = fileOffset + CONTINUE_FILE_BATCH;
      if (nextOffset < msg.totalFiles) {
        await continueQueue.send({
          type: "continue",
          sourceId,
          url,
          category,
          subcategory,
          fileOffset: nextOffset,
          totalFiles: msg.totalFiles,
          sdkVersion,
          branch,
          token,
        } satisfies ContinueMessage);
        newMessages++;
      }
    }
  } catch (err) {
    console.error(`Continue handler error for ${sourceId} at offset ${fileOffset}:`, err);
  } finally {
    // ALWAYS decrement pendingMessages, even on error
    const progress = (await env.KV.get(progressKey, "json")) as IngestProgress | null;
    if (progress) {
      progress.totalChunks += newChunks;
      progress.pendingMessages = Math.max(0, progress.pendingMessages - 1) + newMessages;
      progress.updatedAt = new Date().toISOString();
      await env.KV.put(progressKey, JSON.stringify(progress), { expirationTtl: 86400 });

      // Auto-finalize if this was the last message
      if (progress.pendingMessages === 0) {
        await finalizeIngestion(sourceId, url, progress, env);
      }
    }
  }
}

/**
 * Handle "finalize" queue message (legacy — kept for backward compat with in-flight messages).
 * New flow: embed/continue handlers auto-finalize when pendingMessages hits 0.
 */
export async function handleFinalizeMessage(
  msg: FinalizeMessage,
  env: PipelineEnv
): Promise<void> {
  const { sourceId, url, sdkVersion } = msg;
  const progressKey = PROGRESS_PREFIX + sourceId;
  const progress = (await env.KV.get(progressKey, "json")) as IngestProgress | null;

  // If no progress or already finalized (key cleaned up), nothing to do
  if (!progress) return;

  // If still pending, throw to retry — but with new flow this path is rarely hit
  if (progress.pendingMessages > 0) {
    throw new Error(
      `Finalize waiting: ${progress.pendingMessages} messages pending for ${sourceId} (${progress.embeddedChunks}/${progress.totalChunks} embedded)`
    );
  }

  await finalizeIngestion(sourceId, url, progress, env, sdkVersion);
}

// --- Shared helpers ---

/**
 * Finalize an ingestion job: update source status and clean up progress.
 * Called automatically by the last embed/continue handler when pendingMessages reaches 0.
 */
async function finalizeIngestion(
  sourceId: string,
  url: string,
  progress: IngestProgress,
  env: PipelineEnv,
  sdkVersion?: string
): Promise<void> {
  const effectiveSdkVersion = sdkVersion || progress.sdkVersion;
  const result: IngestResult = {
    sourceId,
    url,
    status: progress.failedChunks === 0 ? "success" : progress.embeddedChunks > 0 ? "partial" : "error",
    chunks: progress.totalChunks,
    embedded: progress.embeddedChunks,
    failed: progress.failedChunks,
    errors: progress.errors.slice(0, 10),
    sdkVersion: effectiveSdkVersion,
    durationMs: Date.now() - new Date(progress.startedAt).getTime(),
  };

  await updateSourceStatus(env, url, result);

  // Clean up progress key
  await env.KV.delete(PROGRESS_PREFIX + sourceId);

  console.log(
    `Finalized ${url}: ${result.embedded} embedded, ${result.failed} failed, ${result.durationMs}ms`
  );
}

/**
 * Chunk repo files into ProcessedChunks (code + markdown).
 */
async function chunkRepoFiles(
  repo: ScrapedRepo,
  source: { url: string; category: string; subcategory?: string }
): Promise<ProcessedChunk[]> {
  const mdFiles = repo.files.filter((f) => f.extension === ".md");
  const codeFiles = repo.files.filter((f) => f.extension !== ".md");

  const codeChunks = await chunkCode(codeFiles, {
    url: source.url,
    category: source.category,
    source: "github",
  });

  const docChunks =
    mdFiles.length > 0
      ? await chunkDocument(
          mdFiles.map((f) => `# ${f.path}\n\n${f.content}`).join("\n\n---\n\n"),
          {
            url: source.url,
            title: source.url.split("/").pop() || "",
            category: source.category,
            source: "github",
          }
        )
      : [];

  return [...codeChunks, ...docChunks];
}

/**
 * Select the next source to process from the registry.
 * Priority: pending > error with retries left > stale active (>7 days).
 */
export async function selectNextSource(
  env: PipelineEnv
): Promise<Source | null> {
  const registry = await loadRegistry(env.KV);
  const sources = Object.values(registry.sources);
  const now = Date.now();
  const sevenDays = 7 * 24 * 60 * 60 * 1000;
  const processingTimeout = 10 * 60 * 1000; // 10 minutes

  // 0. Force-finalize sources stuck in "processing" beyond timeout (dead-lettered queue messages)
  const stuckProcessing = sources.filter((s) => {
    if (s.status !== "processing") return false;
    const updated = s.updatedAt ? new Date(s.updatedAt).getTime() : 0;
    return now - updated > processingTimeout;
  });
  for (const stuck of stuckProcessing) {
    const progressKey = PROGRESS_PREFIX + stuck.id;
    const progress = (await env.KV.get(progressKey, "json")) as IngestProgress | null;
    if (progress) {
      console.log(`Force-finalizing stuck source ${stuck.id} (${stuck.url}): ${progress.embeddedChunks}/${progress.totalChunks} embedded`);
      await finalizeIngestion(stuck.id, stuck.url, progress, env, progress.sdkVersion);
    } else {
      // No progress key — just reset to error status
      stuck.status = "error";
      stuck.errorCount = (stuck.errorCount || 0) + 1;
      stuck.updatedAt = new Date().toISOString();
      await saveRegistry(env.KV, registry);
    }
  }

  // 1. Pending sources (never processed), oldest first
  const pending = sources
    .filter((s) => s.status === "pending")
    .sort(
      (a, b) =>
        new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
    );
  if (pending.length > 0) return pending[0];

  // 2. Error sources with retries left (errorCount < 3), oldest first
  const errored = sources
    .filter((s) => s.status === "error" && s.errorCount < 3)
    .sort(
      (a, b) =>
        new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime()
    );
  if (errored.length > 0) return errored[0];

  // 3. Active sources not processed in 7 days
  const stale = sources
    .filter((s) => {
      if (s.status !== "active") return false;
      const lastProcessed = s.lastProcessed
        ? new Date(s.lastProcessed).getTime()
        : 0;
      return now - lastProcessed > sevenDays;
    })
    .sort((a, b) => {
      const aTime = a.lastProcessed
        ? new Date(a.lastProcessed).getTime()
        : 0;
      const bTime = b.lastProcessed
        ? new Date(b.lastProcessed).getTime()
        : 0;
      return aTime - bTime;
    });
  if (stale.length > 0) return stale[0];

  return null;
}

/**
 * Embed chunks via Workers AI and upsert to Vectorize.
 * Uses direct bindings - no HTTP roundtrip.
 */
async function embedAndUpsert(
  chunks: ProcessedChunk[],
  env: PipelineEnv,
  embeddingBatchSize: number,
  vectorizeBatchSize: number
): Promise<{ embedded: number; failed: number; errors: string[] }> {
  const result = { embedded: 0, failed: 0, errors: [] as string[] };
  const vectors: Array<{
    id: string;
    values: number[];
    metadata: Record<string, string | number>;
  }> = [];

  // Generate embeddings in batches
  for (let i = 0; i < chunks.length; i += embeddingBatchSize) {
    const batch = chunks.slice(i, i + embeddingBatchSize);
    const texts = batch.map((c) => c.content);

    try {
      const embeddingResponse = await withRetry(
        async () => env.AI.run("@cf/baai/bge-m3", { text: texts }),
        { maxRetries: 3, baseDelayMs: 500, maxDelayMs: 5000 }
      );

      if ("data" in embeddingResponse && Array.isArray(embeddingResponse.data)) {
        for (let j = 0; j < batch.length; j++) {
          const embedding = embeddingResponse.data[j];
          if (!embedding || embedding.length === 0) {
            result.failed++;
            result.errors.push(`Empty embedding for ${batch[j].id}`);
            continue;
          }

          vectors.push({
            id: batch[j].id,
            values: embedding,
            metadata: {
              content: batch[j].content.slice(0, 2000),
              source: batch[j].source,
              category: batch[j].category,
              title: (batch[j].title || "").slice(0, 200),
              url: (batch[j].url || "").slice(0, 500),
              chunk_index: batch[j].chunk_index,
            },
          });
          result.embedded++;
        }
      } else {
        result.failed += batch.length;
        result.errors.push(`Unexpected embedding response format at batch ${i}`);
      }
    } catch (err) {
      result.failed += batch.length;
      result.errors.push(`Embedding batch ${i} failed: ${err}`);
    }
  }

  // Upsert vectors to Vectorize in batches
  for (let i = 0; i < vectors.length; i += vectorizeBatchSize) {
    const batch = vectors.slice(i, i + vectorizeBatchSize);
    try {
      await withRetry(
        async () => env.VECTORIZE.upsert(batch),
        { maxRetries: 3, baseDelayMs: 1000, maxDelayMs: 10000 }
      );
    } catch (err) {
      result.failed += batch.length;
      result.embedded -= batch.length;
      result.errors.push(`Vectorize upsert batch ${i} failed: ${err}`);
    }
  }

  return result;
}

/**
 * Mark source as "processing" in the registry (for async queue path).
 */
async function updateSourceProcessing(
  env: PipelineEnv,
  url: string,
  sourceId: string
): Promise<void> {
  const registry = await loadRegistry(env.KV);
  const existing = registry.sources[sourceId];
  if (!existing) return;

  existing.status = "processing" as Source["status"];
  existing.updatedAt = new Date().toISOString();
  await saveRegistry(env.KV, registry);
}

/**
 * Update source status in the KV registry after ingestion.
 */
async function updateSourceStatus(
  env: PipelineEnv,
  _url: string,
  result: IngestResult
): Promise<void> {
  const registry = await loadRegistry(env.KV);
  const sourceId = result.sourceId;
  const now = new Date().toISOString();

  const existing = registry.sources[sourceId];
  if (!existing) return;

  existing.status = result.status === "error" ? "error" : "active";
  existing.chunkCount = result.embedded;
  existing.lastScraped = now;
  existing.lastProcessed = now;
  existing.updatedAt = now;

  if (result.sdkVersion) {
    existing.stylusVersion = result.sdkVersion;
    existing.isVersionDeprecated =
      result.sdkVersion < "0.8.0";
  }

  if (result.status === "error") {
    existing.lastError = result.errors.join("; ").slice(0, 500);
    existing.errorCount = (existing.errorCount || 0) + 1;
  } else {
    existing.lastError = undefined;
  }

  registry.totalChunks = Object.values(registry.sources).reduce(
    (sum, s) => sum + (s.chunkCount || 0),
    0
  );

  await saveRegistry(env.KV, registry);
}

/**
 * Clean up stale progress entries (abandoned > 24 hours).
 */
export async function cleanupStaleProgress(
  env: PipelineEnv
): Promise<number> {
  const list = await env.KV.list({ prefix: PROGRESS_PREFIX });
  const now = Date.now();
  const maxAge = 24 * 60 * 60 * 1000;
  let cleaned = 0;

  for (const key of list.keys) {
    try {
      const progress = (await env.KV.get(key.name, "json")) as IngestProgress | null;
      if (progress) {
        const age = now - new Date(progress.updatedAt).getTime();
        if (age > maxAge) {
          await env.KV.delete(key.name);
          cleaned++;
        }
      }
    } catch {
      await env.KV.delete(key.name);
      cleaned++;
    }
  }

  return cleaned;
}

/**
 * Get active ingestion progress entries.
 */
export async function getActiveProgress(
  env: PipelineEnv
): Promise<IngestProgress[]> {
  const list = await env.KV.list({ prefix: PROGRESS_PREFIX });
  const entries: IngestProgress[] = [];

  for (const key of list.keys) {
    try {
      const progress = (await env.KV.get(key.name, "json")) as IngestProgress | null;
      if (progress) entries.push(progress);
    } catch {
      // Skip unreadable entries
    }
  }

  return entries;
}

// --- Helpers ---

function generateSourceId(url: string): string {
  let hash = 0;
  for (let i = 0; i < url.length; i++) {
    const char = url.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash;
  }
  return Math.abs(hash).toString(16).padStart(8, "0").slice(0, 16);
}

async function loadRegistry(kv: KVNamespace): Promise<SourcesRegistry> {
  const data = (await kv.get(SOURCES_KEY, "json")) as SourcesRegistry | null;
  if (data) return data;
  return { version: "1.0", totalChunks: 0, sources: {} };
}

async function saveRegistry(
  kv: KVNamespace,
  registry: SourcesRegistry
): Promise<void> {
  await kv.put(SOURCES_KEY, JSON.stringify(registry));
}

async function withRetry<T>(
  fn: () => Promise<T>,
  options: { maxRetries?: number; baseDelayMs?: number; maxDelayMs?: number } = {}
): Promise<T> {
  const { maxRetries = 3, baseDelayMs = 500, maxDelayMs = 5000 } = options;
  let lastError: unknown;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      if (attempt === maxRetries) break;
      const delay = Math.min(
        baseDelayMs * Math.pow(2, attempt) + Math.random() * 100,
        maxDelayMs
      );
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}

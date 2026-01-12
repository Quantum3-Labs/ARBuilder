/**
 * Admin API for managing RAG sources.
 * Protected by admin secret - only accessible internally.
 *
 * Stores source registry in Cloudflare KV.
 *
 * Usage:
 * GET /api/admin/sources - List all sources
 * POST /api/admin/sources - Add/update a source
 * DELETE /api/admin/sources - Remove a source
 *
 * Headers: X-Admin-Secret: <AUTH_SECRET>
 */

import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";

// KV key for storing sources registry
const SOURCES_KEY = "rag:sources:registry";

// Source types matching Python implementation
type SourceType = "documentation" | "github";
type SourceStatus = "active" | "pending" | "error" | "removed";

interface Source {
  id: string;
  url: string;
  sourceType: SourceType;
  category: string;
  subcategory: string;
  // Version tracking
  stylusVersion?: string;
  isVersionDeprecated?: boolean;
  // State tracking
  status: SourceStatus;
  lastModified?: string;
  contentHash?: string;
  // Processing tracking
  lastScraped?: string;
  lastProcessed?: string;
  chunkCount: number;
  // Error tracking
  lastError?: string;
  errorCount: number;
  // Timestamps
  createdAt: string;
  updatedAt: string;
}

interface SourcesRegistry {
  version: string;
  lastSync?: string;
  totalChunks: number;
  sources: Record<string, Source>;
}

// Generate deterministic ID from URL
function generateSourceId(url: string): string {
  // Simple hash function for browser/edge compatibility
  let hash = 0;
  for (let i = 0; i < url.length; i++) {
    const char = url.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash).toString(16).padStart(8, "0").slice(0, 16);
}

// Detect source type from URL
function detectSourceType(url: string): SourceType {
  return url.includes("github.com") ? "github" : "documentation";
}

// Load registry from KV
async function loadRegistry(kv: KVNamespace): Promise<SourcesRegistry> {
  const data = await kv.get(SOURCES_KEY, "json") as SourcesRegistry | null;
  if (data) {
    return data;
  }
  return {
    version: "1.0",
    totalChunks: 0,
    sources: {},
  };
}

// Save registry to KV
async function saveRegistry(kv: KVNamespace, registry: SourcesRegistry): Promise<void> {
  await kv.put(SOURCES_KEY, JSON.stringify(registry));
}

// Verify admin auth
function verifyAuth(request: NextRequest, authSecret: string): boolean {
  const adminSecret = request.headers.get("X-Admin-Secret");
  return adminSecret === authSecret;
}

/**
 * GET /api/admin/sources
 * List all sources with optional filtering
 */
export async function GET(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();

    if (!verifyAuth(request, env.AUTH_SECRET)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const registry = await loadRegistry(env.KV);

    // Parse query params for filtering
    const { searchParams } = new URL(request.url);
    const category = searchParams.get("category");
    const status = searchParams.get("status") as SourceStatus | null;
    const sourceType = searchParams.get("type") as SourceType | null;
    const stylusVersion = searchParams.get("version");

    // Filter sources
    let sources = Object.values(registry.sources);

    if (category) {
      sources = sources.filter((s) => s.category === category);
    }
    if (status) {
      sources = sources.filter((s) => s.status === status);
    }
    if (sourceType) {
      sources = sources.filter((s) => s.sourceType === sourceType);
    }
    if (stylusVersion) {
      sources = sources.filter((s) => s.stylusVersion === stylusVersion);
    }

    // Sort by category, then by URL
    sources.sort((a, b) => {
      if (a.category !== b.category) {
        return a.category.localeCompare(b.category);
      }
      return a.url.localeCompare(b.url);
    });

    // Generate statistics
    const stats = {
      totalSources: Object.keys(registry.sources).length,
      totalChunks: registry.totalChunks,
      lastSync: registry.lastSync,
      byCategory: {} as Record<string, number>,
      byStatus: {} as Record<string, number>,
      byType: {} as Record<string, number>,
      byStylusVersion: {} as Record<string, number>,
      deprecatedCount: 0,
    };

    for (const source of Object.values(registry.sources)) {
      stats.byCategory[source.category] = (stats.byCategory[source.category] || 0) + 1;
      stats.byStatus[source.status] = (stats.byStatus[source.status] || 0) + 1;
      stats.byType[source.sourceType] = (stats.byType[source.sourceType] || 0) + 1;
      if (source.stylusVersion) {
        stats.byStylusVersion[source.stylusVersion] = (stats.byStylusVersion[source.stylusVersion] || 0) + 1;
      }
      if (source.isVersionDeprecated) {
        stats.deprecatedCount++;
      }
    }

    return NextResponse.json({
      status: "ok",
      sources,
      stats,
    });
  } catch (error) {
    console.error("Sources list error:", error);
    return NextResponse.json(
      { error: `Failed to list sources: ${error}` },
      { status: 500 }
    );
  }
}

/**
 * POST /api/admin/sources
 * Add or update a source
 * Body: { url, category, subcategory?, sourceType?, stylusVersion? }
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
      sourceType?: SourceType;
      stylusVersion?: string;
      isVersionDeprecated?: boolean;
      status?: SourceStatus;
      chunkCount?: number;
      lastError?: string;
    };

    if (!body.url || !body.category) {
      return NextResponse.json(
        { error: "url and category are required" },
        { status: 400 }
      );
    }

    const registry = await loadRegistry(env.KV);
    const sourceId = generateSourceId(body.url);
    const now = new Date().toISOString();

    // Check if source exists
    const existing = registry.sources[sourceId];

    if (existing) {
      // Update existing source
      const updated: Source = {
        ...existing,
        category: body.category,
        subcategory: body.subcategory || existing.subcategory,
        stylusVersion: body.stylusVersion ?? existing.stylusVersion,
        isVersionDeprecated: body.isVersionDeprecated ?? existing.isVersionDeprecated,
        status: body.status ?? existing.status,
        chunkCount: body.chunkCount ?? existing.chunkCount,
        lastError: body.lastError,
        errorCount: body.lastError ? existing.errorCount + 1 : existing.errorCount,
        updatedAt: now,
      };
      registry.sources[sourceId] = updated;
      await saveRegistry(env.KV, registry);

      return NextResponse.json({
        status: "ok",
        action: "updated",
        source: updated,
      });
    }

    // Create new source
    const newSource: Source = {
      id: sourceId,
      url: body.url,
      sourceType: body.sourceType || detectSourceType(body.url),
      category: body.category,
      subcategory: body.subcategory || "",
      stylusVersion: body.stylusVersion,
      isVersionDeprecated: body.isVersionDeprecated ?? false,
      status: body.status || "pending",
      chunkCount: body.chunkCount || 0,
      errorCount: 0,
      createdAt: now,
      updatedAt: now,
    };

    registry.sources[sourceId] = newSource;
    await saveRegistry(env.KV, registry);

    return NextResponse.json({
      status: "ok",
      action: "created",
      source: newSource,
    });
  } catch (error) {
    console.error("Source add error:", error);
    return NextResponse.json(
      { error: `Failed to add source: ${error}` },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/admin/sources
 * Remove a source
 * Body: { url } or { id }
 */
export async function DELETE(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();

    if (!verifyAuth(request, env.AUTH_SECRET)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json() as { url?: string; id?: string };

    if (!body.url && !body.id) {
      return NextResponse.json(
        { error: "url or id is required" },
        { status: 400 }
      );
    }

    const registry = await loadRegistry(env.KV);
    const sourceId = body.id || generateSourceId(body.url!);

    const source = registry.sources[sourceId];
    if (!source) {
      return NextResponse.json(
        { error: "Source not found" },
        { status: 404 }
      );
    }

    // Remove from registry
    registry.totalChunks -= source.chunkCount;
    delete registry.sources[sourceId];
    await saveRegistry(env.KV, registry);

    return NextResponse.json({
      status: "ok",
      action: "deleted",
      source,
    });
  } catch (error) {
    console.error("Source delete error:", error);
    return NextResponse.json(
      { error: `Failed to delete source: ${error}` },
      { status: 500 }
    );
  }
}

/**
 * PATCH /api/admin/sources
 * Bulk import sources from config
 * Body: { sources: [{ url, category, subcategory? }] }
 */
export async function PATCH(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();

    if (!verifyAuth(request, env.AUTH_SECRET)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json() as {
      action: "import" | "sync_complete";
      sources?: Array<{ url: string; category: string; subcategory?: string }>;
    };

    const registry = await loadRegistry(env.KV);
    const now = new Date().toISOString();

    if (body.action === "sync_complete") {
      registry.lastSync = now;
      await saveRegistry(env.KV, registry);
      return NextResponse.json({
        status: "ok",
        action: "sync_complete",
        lastSync: now,
      });
    }

    if (body.action === "import" && body.sources) {
      let added = 0;
      let skipped = 0;

      for (const src of body.sources) {
        const sourceId = generateSourceId(src.url);

        if (registry.sources[sourceId]) {
          skipped++;
          continue;
        }

        registry.sources[sourceId] = {
          id: sourceId,
          url: src.url,
          sourceType: detectSourceType(src.url),
          category: src.category,
          subcategory: src.subcategory || "",
          status: "pending",
          chunkCount: 0,
          errorCount: 0,
          createdAt: now,
          updatedAt: now,
        };
        added++;
      }

      await saveRegistry(env.KV, registry);

      return NextResponse.json({
        status: "ok",
        action: "import",
        added,
        skipped,
        total: Object.keys(registry.sources).length,
      });
    }

    return NextResponse.json({ error: "Invalid action" }, { status: 400 });
  } catch (error) {
    console.error("Source patch error:", error);
    return NextResponse.json(
      { error: `Failed to patch sources: ${error}` },
      { status: 500 }
    );
  }
}

/**
 * Public API for viewing ingested RAG sources.
 * Read-only, no authentication required.
 * Provides transparency into what data powers the knowledge base.
 *
 * Usage:
 * GET /api/public/sources - List all active sources (read-only)
 */

import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";

// KV key for storing sources registry
const SOURCES_KEY = "rag:sources:registry";

// Source types
type SourceType = "documentation" | "github";
type SourceStatus = "active" | "pending" | "error" | "removed";

interface Source {
  id: string;
  url: string;
  sourceType: SourceType;
  category: string;
  subcategory: string;
  stylusVersion?: string;
  isVersionDeprecated?: boolean;
  status: SourceStatus;
  chunkCount: number;
  lastScraped?: string;
  createdAt: string;
  updatedAt: string;
}

interface SourcesRegistry {
  version: string;
  lastSync?: string;
  totalChunks: number;
  sources: Record<string, Source>;
}

// Public source view (excludes internal fields like errors)
interface PublicSource {
  id: string;
  url: string;
  sourceType: SourceType;
  category: string;
  subcategory: string;
  stylusVersion?: string;
  chunkCount: number;
  lastUpdated: string;
}

interface PublicStats {
  totalSources: number;
  totalChunks: number;
  lastSync?: string;
  byCategory: Record<string, number>;
  byType: Record<string, number>;
  byStylusVersion: Record<string, number>;
}

/**
 * GET /api/public/sources
 * List all active sources with public information only
 */
export async function GET(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();

    const data = await env.KV.get(SOURCES_KEY, "json") as SourcesRegistry | null;

    if (!data) {
      return NextResponse.json({
        status: "ok",
        sources: [],
        stats: {
          totalSources: 0,
          totalChunks: 0,
          byCategory: {},
          byType: {},
          byStylusVersion: {},
        },
      });
    }

    // Parse query params for filtering
    const { searchParams } = new URL(request.url);
    const category = searchParams.get("category");
    const sourceType = searchParams.get("type") as SourceType | null;

    // Filter to only active sources and map to public view
    let sources = Object.values(data.sources)
      .filter((s) => s.status === "active")
      .map((s): PublicSource => ({
        id: s.id,
        url: s.url,
        sourceType: s.sourceType,
        category: s.category,
        subcategory: s.subcategory,
        stylusVersion: s.stylusVersion,
        chunkCount: s.chunkCount,
        lastUpdated: s.updatedAt,
      }));

    // Apply filters
    if (category) {
      sources = sources.filter((s) => s.category === category);
    }
    if (sourceType) {
      sources = sources.filter((s) => s.sourceType === sourceType);
    }

    // Sort by category, then by URL
    sources.sort((a, b) => {
      if (a.category !== b.category) {
        return a.category.localeCompare(b.category);
      }
      return a.url.localeCompare(b.url);
    });

    // Generate public statistics (only from active sources)
    const activeSources = Object.values(data.sources).filter((s) => s.status === "active");
    const stats: PublicStats = {
      totalSources: activeSources.length,
      totalChunks: activeSources.reduce((sum, s) => sum + (s.chunkCount || 0), 0),
      lastSync: data.lastSync,
      byCategory: {},
      byType: {},
      byStylusVersion: {},
    };

    for (const source of activeSources) {
      stats.byCategory[source.category] = (stats.byCategory[source.category] || 0) + 1;
      stats.byType[source.sourceType] = (stats.byType[source.sourceType] || 0) + 1;
      if (source.stylusVersion) {
        stats.byStylusVersion[source.stylusVersion] = (stats.byStylusVersion[source.stylusVersion] || 0) + 1;
      }
    }

    return NextResponse.json({
      status: "ok",
      sources,
      stats,
    });
  } catch (error) {
    console.error("Public sources error:", error);
    return NextResponse.json(
      { error: "Failed to fetch sources" },
      { status: 500 }
    );
  }
}

/**
 * Sync sources.json to Cloudflare KV registry.
 *
 * Reads the canonical sources.json file and pushes all sources to the
 * CF Worker's admin API. For versioned repos (multiple branches),
 * each version is registered as a separate ingestion entry.
 *
 * Usage:
 *   ARBBUILDER_ADMIN_SECRET=xxx npx tsx scripts/sync_sources.ts
 *   ARBBUILDER_ADMIN_SECRET=xxx npx tsx scripts/sync_sources.ts --dry-run
 *   ARBBUILDER_ADMIN_SECRET=xxx npx tsx scripts/sync_sources.ts --remove-stale
 */

import { readFileSync } from "fs";
import { resolve } from "path";

const API_URL = process.env.ARBBUILDER_API_URL || "https://arbuilder.app";
const ADMIN_SECRET = process.env.ARBBUILDER_ADMIN_SECRET;

if (!ADMIN_SECRET) {
  console.error("ARBBUILDER_ADMIN_SECRET is required");
  process.exit(1);
}

// --- Types ---

interface SourceVersion {
  sdkVersion: string;
  branch: string;
}

interface SourceEntry {
  url: string;
  type: "documentation" | "github";
  milestone: string;
  category: string;
  subcategory: string;
  sdkVersion?: string;
  versions?: SourceVersion[];
  forkedFrom?: string;
  verified?: string;
  note?: string;
}

interface SourcesFile {
  version: number;
  sources: SourceEntry[];
}

interface KVSource {
  id: string;
  url: string;
  sourceType: string;
  category: string;
  subcategory: string;
  stylusVersion?: string;
  branch?: string;
  status: string;
}

// --- Helpers ---

async function apiCall(
  method: string,
  path: string,
  body?: unknown
): Promise<{ ok: boolean; status: number; data: unknown }> {
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Secret": ADMIN_SECRET!,
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });

  const data = await res.json().catch(() => null);
  return { ok: res.ok, status: res.status, data };
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

function truncateUrl(url: string): string {
  try {
    const parsed = new URL(url);
    const path =
      parsed.pathname.length > 40
        ? parsed.pathname.slice(0, 40) + "..."
        : parsed.pathname;
    return parsed.host + path;
  } catch {
    return url.slice(0, 60);
  }
}

/**
 * Expand sources.json entries into flat registration entries.
 * Versioned repos become one entry per version+branch.
 */
function expandSources(
  sources: SourceEntry[]
): Array<{
  url: string;
  category: string;
  subcategory: string;
  sourceType: string;
  stylusVersion?: string;
  branch?: string;
}> {
  const entries: Array<{
    url: string;
    category: string;
    subcategory: string;
    sourceType: string;
    stylusVersion?: string;
    branch?: string;
  }> = [];

  for (const source of sources) {
    if (source.versions && source.versions.length > 0) {
      // Versioned repo: one entry per version+branch
      for (const version of source.versions) {
        entries.push({
          url: source.url,
          category: source.category,
          subcategory: source.subcategory,
          sourceType: source.type,
          stylusVersion: version.sdkVersion,
          branch: version.branch,
        });
      }
    } else {
      // Non-versioned source: single entry
      entries.push({
        url: source.url,
        category: source.category,
        subcategory: source.subcategory,
        sourceType: source.type,
        stylusVersion: source.sdkVersion,
      });
    }
  }

  return entries;
}

// --- Main ---

async function main() {
  const args = process.argv.slice(2);
  const dryRun = args.includes("--dry-run");
  const removeStale = args.includes("--remove-stale");

  // Load sources.json
  const sourcesPath = resolve(__dirname, "..", "sources.json");
  const sourcesFile: SourcesFile = JSON.parse(
    readFileSync(sourcesPath, "utf-8")
  );

  console.log(`Source Sync — ${API_URL}`);
  console.log(`Sources file: ${sourcesFile.sources.length} entries`);

  // Expand versioned repos into flat entries
  const expanded = expandSources(sourcesFile.sources);
  console.log(`Expanded to ${expanded.length} registration entries`);

  if (dryRun) {
    console.log("\n--- Dry run: would register ---");
    for (const entry of expanded) {
      const branch = entry.branch ? ` [${entry.branch}]` : "";
      const version = entry.stylusVersion ? ` (${entry.stylusVersion})` : "";
      console.log(
        `  ${entry.category}/${entry.subcategory}: ${truncateUrl(entry.url)}${branch}${version}`
      );
    }
    console.log(`\nTotal: ${expanded.length} entries`);
    return;
  }

  // Get current KV registry for comparison
  const { ok: listOk, data: listData } = await apiCall(
    "GET",
    "/api/admin/sources"
  );
  const existingSources: KVSource[] = listOk
    ? ((listData as { sources?: KVSource[] })?.sources ?? [])
    : [];
  const existingUrls = new Set(existingSources.map((s) => s.url));

  console.log(`\nExisting KV sources: ${existingSources.length}`);

  // Register sources
  let added = 0;
  let updated = 0;
  let skipped = 0;
  let failed = 0;

  for (const entry of expanded) {
    const branch = entry.branch ? ` [${entry.branch}]` : "";
    const label = `${entry.subcategory}${branch}`;

    const { ok, data } = await apiCall("POST", "/api/admin/sources", {
      url: entry.url,
      category: entry.category,
      subcategory: entry.subcategory,
      sourceType: entry.sourceType,
      stylusVersion: entry.stylusVersion,
      branch: entry.branch,
    });

    if (ok) {
      const d = data as { action?: string; source?: { status?: string } };
      if (d?.action === "updated") {
        console.log(`  UPDATE: ${label} — ${truncateUrl(entry.url)}`);
        updated++;
      } else if (d?.source?.status === "active") {
        skipped++;
      } else {
        console.log(`  ADD: ${label} — ${truncateUrl(entry.url)}`);
        added++;
      }
    } else {
      console.error(
        `  FAIL [${(data as { error?: string })?.error}]: ${entry.url}`
      );
      failed++;
    }

    await sleep(100);
  }

  console.log(
    `\nSync complete: ${added} added, ${updated} updated, ${skipped} unchanged, ${failed} failed`
  );

  // Remove stale sources (in KV but not in sources.json)
  if (removeStale) {
    const jsonUrls = new Set(sourcesFile.sources.map((s) => s.url));
    const stale = existingSources.filter((s) => !jsonUrls.has(s.url));

    if (stale.length === 0) {
      console.log("\nNo stale sources to remove.");
    } else {
      console.log(`\nRemoving ${stale.length} stale sources...`);
      for (const source of stale) {
        const { ok } = await apiCall("DELETE", "/api/admin/sources", {
          url: source.url,
        });
        if (ok) {
          console.log(`  REMOVED: ${truncateUrl(source.url)}`);
        } else {
          console.error(`  FAIL to remove: ${truncateUrl(source.url)}`);
        }
        await sleep(100);
      }
    }
  }

  // Mark sync complete
  await apiCall("PATCH", "/api/admin/sources", { action: "sync_complete" });

  // Final stats
  const { ok: statsOk, data: statsData } = await apiCall(
    "GET",
    "/api/admin/sources"
  );
  if (statsOk) {
    const d = statsData as {
      stats: {
        totalSources: number;
        totalChunks: number;
        byCategory: Record<string, number>;
      };
    };
    console.log(`\n--- Final Status ---`);
    console.log(`Total sources: ${d.stats.totalSources}`);
    console.log(`Total chunks: ${d.stats.totalChunks}`);
    console.log("By category:", d.stats.byCategory);
  }
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});

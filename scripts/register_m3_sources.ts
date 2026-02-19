/**
 * Register and ingest M3 (dApp Builder) sources into the Worker KV registry.
 *
 * Mirrors M3_SOURCES and M3_GITHUB_REPOS from scraper/config.py.
 *
 * Usage:
 *   ARBBUILDER_ADMIN_SECRET=xxx npx tsx scripts/register_m3_sources.ts
 *   ARBBUILDER_ADMIN_SECRET=xxx npx tsx scripts/register_m3_sources.ts --register-only
 *   ARBBUILDER_ADMIN_SECRET=xxx npx tsx scripts/register_m3_sources.ts --ingest-only
 */

const API_URL = process.env.ARBBUILDER_API_URL || "https://arbuilder.app";
const ADMIN_SECRET = process.env.ARBBUILDER_ADMIN_SECRET;

if (!ADMIN_SECRET) {
  console.error("ARBBUILDER_ADMIN_SECRET is required");
  process.exit(1);
}

// --- M3 Documentation Sources (mirrors scraper/config.py M3_SOURCES) ---

interface SourceEntry {
  url: string;
  category: string;
  subcategory: string;
}

const M3_DOCS: SourceEntry[] = [
  // Backend: NestJS
  { url: "https://docs.nestjs.com/first-steps", category: "m3_backend", subcategory: "nestjs" },
  { url: "https://docs.nestjs.com/modules", category: "m3_backend", subcategory: "nestjs" },
  { url: "https://docs.nestjs.com/providers", category: "m3_backend", subcategory: "nestjs" },
  { url: "https://docs.nestjs.com/controllers", category: "m3_backend", subcategory: "nestjs" },
  { url: "https://docs.nestjs.com/techniques/configuration", category: "m3_backend", subcategory: "nestjs" },

  // Backend: Express
  { url: "https://expressjs.com/en/starter/basic-routing.html", category: "m3_backend", subcategory: "express" },
  { url: "https://expressjs.com/en/guide/routing.html", category: "m3_backend", subcategory: "express" },
  { url: "https://expressjs.com/en/guide/error-handling.html", category: "m3_backend", subcategory: "express" },

  // Frontend: wagmi
  { url: "https://wagmi.sh/react/getting-started", category: "m3_frontend", subcategory: "wagmi" },
  { url: "https://wagmi.sh/react/guides/connect-wallet", category: "m3_frontend", subcategory: "wagmi" },
  { url: "https://wagmi.sh/react/guides/read-from-contract", category: "m3_frontend", subcategory: "wagmi" },
  { url: "https://wagmi.sh/react/guides/write-to-contract", category: "m3_frontend", subcategory: "wagmi" },
  { url: "https://wagmi.sh/react/guides/send-transaction", category: "m3_frontend", subcategory: "wagmi" },

  // Frontend: viem
  { url: "https://viem.sh/docs/getting-started", category: "m3_frontend", subcategory: "viem" },
  { url: "https://viem.sh/docs/contract/readContract", category: "m3_frontend", subcategory: "viem" },
  { url: "https://viem.sh/docs/contract/writeContract", category: "m3_frontend", subcategory: "viem" },
  { url: "https://viem.sh/docs/actions/public/waitForTransactionReceipt", category: "m3_frontend", subcategory: "viem" },

  // Frontend: RainbowKit
  { url: "https://www.rainbowkit.com/docs/introduction", category: "m3_frontend", subcategory: "rainbowkit" },
  { url: "https://www.rainbowkit.com/docs/installation", category: "m3_frontend", subcategory: "rainbowkit" },
  { url: "https://www.rainbowkit.com/docs/connect-button", category: "m3_frontend", subcategory: "rainbowkit" },
  { url: "https://www.rainbowkit.com/docs/custom-chains", category: "m3_frontend", subcategory: "rainbowkit" },

  // Frontend: DaisyUI
  { url: "https://daisyui.com/docs/install/", category: "m3_frontend", subcategory: "daisyui" },
  { url: "https://daisyui.com/components/button/", category: "m3_frontend", subcategory: "daisyui" },
  { url: "https://daisyui.com/components/card/", category: "m3_frontend", subcategory: "daisyui" },
  { url: "https://daisyui.com/components/modal/", category: "m3_frontend", subcategory: "daisyui" },
  { url: "https://daisyui.com/components/input/", category: "m3_frontend", subcategory: "daisyui" },

  // Indexer: The Graph
  { url: "https://thegraph.com/docs/en/developing/creating-a-subgraph/", category: "m3_indexer", subcategory: "the_graph" },
  { url: "https://thegraph.com/docs/en/developing/assemblyscript-api/", category: "m3_indexer", subcategory: "the_graph" },
  { url: "https://thegraph.com/docs/en/developing/graph-ts/api/", category: "m3_indexer", subcategory: "the_graph" },
  { url: "https://thegraph.com/docs/en/cookbook/arweave/", category: "m3_indexer", subcategory: "the_graph" },
  { url: "https://thegraph.com/docs/en/developing/unit-testing-framework/", category: "m3_indexer", subcategory: "the_graph" },

  // Oracle: Chainlink
  { url: "https://docs.chain.link/data-feeds/price-feeds", category: "m3_oracle", subcategory: "chainlink" },
  { url: "https://docs.chain.link/vrf/v2-5/subscription/get-a-random-number", category: "m3_oracle", subcategory: "chainlink" },
  { url: "https://docs.chain.link/chainlink-automation/overview/getting-started", category: "m3_oracle", subcategory: "chainlink" },
  { url: "https://docs.chain.link/chainlink-functions/getting-started", category: "m3_oracle", subcategory: "chainlink" },
  { url: "https://docs.chain.link/data-feeds/using-data-feeds", category: "m3_oracle", subcategory: "chainlink" },
];

// --- M3 GitHub Repos (mirrors scraper/config.py M3_GITHUB_REPOS) ---

const M3_REPOS: SourceEntry[] = [
  // Frontend
  { url: "https://github.com/wevm/wagmi", category: "m3_frontend", subcategory: "wagmi" },
  { url: "https://github.com/wevm/viem", category: "m3_frontend", subcategory: "viem" },
  { url: "https://github.com/rainbow-me/rainbowkit", category: "m3_frontend", subcategory: "rainbowkit" },
  { url: "https://github.com/saadeghi/daisyui", category: "m3_frontend", subcategory: "daisyui" },
  { url: "https://github.com/scaffold-eth/scaffold-eth-2", category: "m3_frontend", subcategory: "scaffold_eth" },

  // Indexer
  { url: "https://github.com/graphprotocol/graph-tooling", category: "m3_indexer", subcategory: "graph_tooling" },
  { url: "https://github.com/messari/subgraphs", category: "m3_indexer", subcategory: "subgraphs" },

  // Oracle
  { url: "https://github.com/smartcontractkit/smart-contract-examples", category: "m3_oracle", subcategory: "chainlink_examples" },
  { url: "https://github.com/smartcontractkit/chainlink", category: "m3_oracle", subcategory: "chainlink" },

  // Backend
  { url: "https://github.com/nestjs/nest", category: "m3_backend", subcategory: "nestjs" },
  { url: "https://github.com/OffchainLabs/arbitrum-token-bridge", category: "m3_backend", subcategory: "arbitrum_bridge_ui" },
];

const ALL_SOURCES = [...M3_DOCS, ...M3_REPOS];

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

// --- Main ---

async function registerSources(sources: SourceEntry[]) {
  console.log(`\nRegistering ${sources.length} sources...\n`);

  let added = 0;
  let skipped = 0;
  let failed = 0;

  for (const source of sources) {
    const { ok, status, data } = await apiCall("POST", "/api/admin/sources", {
      url: source.url,
      category: source.category,
      subcategory: source.subcategory,
    });

    if (ok) {
      const d = data as { source?: { status?: string } };
      if (d?.source?.status === "active") {
        console.log(`  SKIP (exists): ${source.subcategory} — ${source.url}`);
        skipped++;
      } else {
        console.log(`  ADD: ${source.subcategory} — ${source.url}`);
        added++;
      }
    } else {
      console.error(`  FAIL [${status}]: ${source.url}`, data);
      failed++;
    }

    // Small delay to avoid rate limiting
    await sleep(100);
  }

  console.log(`\nRegistration complete: ${added} added, ${skipped} skipped, ${failed} failed`);
  return { added, skipped, failed };
}

async function ingestSources(sources: SourceEntry[]) {
  console.log(`\nIngesting ${sources.length} sources...\n`);

  let success = 0;
  let queued = 0;
  let failed = 0;

  for (const source of sources) {
    process.stdout.write(`  ${source.subcategory} — ${truncateUrl(source.url)} ... `);

    const { ok, data } = await apiCall("POST", "/api/admin/ingest", {
      url: source.url,
      category: source.category,
      subcategory: source.subcategory,
    });

    if (!ok) {
      console.log(`FAIL`);
      console.error(`    Error:`, data);
      failed++;
    } else {
      const result = data as { status: string; chunks?: number; embedded?: number; durationMs?: number };
      if (result.status === "queued") {
        console.log(`QUEUED (${result.chunks} chunks)`);
        queued++;
      } else if (result.status === "success" || result.status === "partial") {
        const duration = ((result.durationMs || 0) / 1000).toFixed(1);
        console.log(`OK (${result.embedded}/${result.chunks} chunks, ${duration}s)`);
        success++;
      } else {
        console.log(`${result.status}`);
        failed++;
      }
    }

    // Wait between ingestions to let the queue breathe
    // Docs are fast (sync), repos may be queued
    const isRepo = source.url.includes("github.com");
    await sleep(isRepo ? 3000 : 1000);
  }

  console.log(`\nIngestion complete: ${success} success, ${queued} queued, ${failed} failed`);
  return { success, queued, failed };
}

function truncateUrl(url: string): string {
  try {
    const parsed = new URL(url);
    const path = parsed.pathname.length > 40 ? parsed.pathname.slice(0, 40) + "..." : parsed.pathname;
    return parsed.host + path;
  } catch {
    return url.slice(0, 60);
  }
}

async function main() {
  const args = process.argv.slice(2);
  const registerOnly = args.includes("--register-only");
  const ingestOnly = args.includes("--ingest-only");

  console.log(`M3 Source Registration — ${API_URL}`);
  console.log(`Total: ${M3_DOCS.length} docs + ${M3_REPOS.length} repos = ${ALL_SOURCES.length} sources\n`);

  // Step 1: Register sources
  if (!ingestOnly) {
    await registerSources(ALL_SOURCES);
  }

  // Step 2: Ingest (docs first, then repos)
  if (!registerOnly) {
    console.log("\n--- Ingesting documentation sources ---");
    await ingestSources(M3_DOCS);

    console.log("\n--- Ingesting GitHub repos ---");
    await ingestSources(M3_REPOS);
  }

  // Step 3: Summary
  console.log("\n--- Final Status ---");
  const { ok, data } = await apiCall("GET", "/api/admin/sources");
  if (ok) {
    const d = data as { stats: { totalSources: number; totalChunks: number; byCategory: Record<string, number> } };
    console.log(`Total sources: ${d.stats.totalSources}`);
    console.log(`Total chunks: ${d.stats.totalChunks}`);
    console.log("By category:", d.stats.byCategory);
  }
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});

# Design: Single Source of Truth for Data Sources

**Date:** 2026-02-22
**Status:** Approved
**Branch:** TBD (off feat/data-curation or main)

## Problem

Data sources are defined in two independent registries that can drift apart:

| | `scraper/config.py` | CF KV Registry |
|---|---|---|
| Used by | Local pipeline (scraper, processor, ChromaDB) | Hosted pipeline (cron, queue, Vectorize) |
| Managed via | Git commits | Admin UI / API / `register_m3_sources.ts` |
| Fields | url, category, sdk_version, forked_from, verified | url, category, status, chunkCount, timestamps |
| Count | 84 sources | ~90 sources |

`register_m3_sources.ts` is a one-shot bridge that hardcodes a copy of M3 sources only. Any config.py edit requires manual re-registration. No automation keeps them in sync.

## Solution

Introduce `sources.json` as the single source of truth. Both Python and TypeScript consumers read from it. A sync script pushes to CF KV (manually or via GitHub Actions).

## Schema

```json
{
  "version": 1,
  "sources": [
    {
      "url": "https://docs.arbitrum.io/stylus/reference/rust-sdk-guide",
      "type": "documentation",
      "milestone": "m1",
      "category": "stylus",
      "subcategory": "official",
      "sdkVersion": "0.10.0"
    },
    {
      "url": "https://github.com/ARBuilder-Forks/stylus-hello-world",
      "type": "github",
      "milestone": "m1",
      "category": "stylus",
      "subcategory": "official_examples",
      "versions": [
        { "sdkVersion": "0.10.0", "branch": "main" },
        { "sdkVersion": "0.9.0", "branch": "v0.9.0" }
      ],
      "forkedFrom": "OffchainLabs/stylus-hello-world",
      "verified": "2026-02-16"
    },
    {
      "url": "https://github.com/wevm/wagmi",
      "type": "github",
      "milestone": "m3",
      "category": "frontend",
      "subcategory": "wagmi"
    }
  ]
}
```

### Field Rules

| Field | Required | Notes |
|-------|----------|-------|
| `url` | Yes | Top-level URL (or base repo URL for versioned repos) |
| `type` | Yes | `"documentation"` or `"github"` |
| `milestone` | Yes | `"m1"`, `"m2"`, `"m3"`, `"m4"` |
| `category` | Yes | e.g., `"stylus"`, `"frontend"`, `"oracle"` |
| `subcategory` | Yes | e.g., `"official"`, `"wagmi"`, `"chainlink"` |
| `sdkVersion` | No | For docs: metadata tag (what version the page covers) |
| `versions` | No | For GitHub repos with multi-version branches |
| `versions[].sdkVersion` | Yes (if versions) | SDK version for this branch |
| `versions[].branch` | Yes (if versions) | Git branch name |
| `forkedFrom` | No | Original repo (for ARBuilder-Forks repos) |
| `verified` | No | Date of last verification |
| `note` | No | Free-text notes |

### Versioning Model

- **GitHub repos with branches**: `versions` array, each entry = `{ sdkVersion, branch }`. Scraper clones each branch separately, chunks tagged with version.
- **Documentation**: Optional `sdkVersion` string. Arbitrum docs are single-version (no versioned URLs), so this is just a metadata tag for filtering.
- **Non-versioned sources** (M3 libs, general docs): Omit `sdkVersion` and `versions`.
- **KV-only fields** (status, chunkCount, timestamps): Never in `sources.json` — ephemeral runtime state managed by the ingestion pipeline.

## Consumer Changes

### 1. `scraper/config.py` — Thin Wrapper

Loads `sources.json` and exposes backward-compatible helpers:

```python
import json
from pathlib import Path

_SOURCES_PATH = Path(__file__).parent.parent / "sources.json"
SOURCES = json.loads(_SOURCES_PATH.read_text())["sources"]

def get_all_config_repo_urls() -> set[str]:
    return {s["url"] for s in SOURCES if s["type"] == "github"}

def get_sources_by_milestone(milestone: str) -> list[dict]:
    return [s for s in SOURCES if s["milestone"] == milestone]

# Backward-compat flat dicts auto-generated from SOURCES
```

Existing consumers (`scraper.py`, `github_scraper.py`, `processor.py`) keep working via the same helpers.

### 2. `scripts/sync_sources.ts` — Replaces `register_m3_sources.ts`

Reads `sources.json`, pushes ALL sources to CF KV via admin API:

- Compares against existing KV registry to detect additions/removals
- For versioned repos, registers each version+branch as a separate ingestion entry
- Run manually: `npx tsx scripts/sync_sources.ts`
- Or via GitHub Actions on push to main

### 3. GitHub Actions — Auto-Sync

```yaml
sync-sources:
  if: contains(github.event.commits.*.modified, 'sources.json')
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: npx tsx scripts/sync_sources.ts
      env:
        ARBBUILDER_ADMIN_SECRET: ${{ secrets.ARBBUILDER_ADMIN_SECRET }}
        ARBBUILDER_API_URL: ${{ secrets.ARBBUILDER_API_URL }}
```

### 4. CF Worker — Branch-Aware Scraping

`github.ts` already supports branch params via Trees API. KV entries from sync include the branch:

```
KV entry: { url, branch: "v0.9.0", sdkVersion: "0.9.0" }
  -> github.ts fetches tree for that branch
  -> chunks tagged with sdkVersion metadata
  -> Vectorize upsert with version in metadata
```

### 5. Admin API — Accept Version Fields

`/api/admin/sources` route accepts `branch` and `sdkVersion` fields in POST/PATCH.

## Files Changed

| Action | File | Description |
|--------|------|-------------|
| NEW | `sources.json` | Single source of truth (all 84 sources) |
| NEW | `scripts/sync_sources.ts` | Push sources.json to CF KV |
| MODIFY | `scraper/config.py` | Thin wrapper loading sources.json |
| MODIFY | `apps/web/src/lib/github.ts` | Pass branch from KV entry to Trees API |
| MODIFY | `apps/web/src/app/api/admin/sources/route.ts` | Accept branch/sdkVersion fields |
| MODIFY | `.github/workflows/maintenance.yml` | Add sync-sources job |
| MODIFY | `src/preprocessing/processor.py` | Remove dual-chunk transform logic |
| MODIFY | `README.md` | Document single source of truth |
| DELETE | `scripts/register_m3_sources.ts` | Replaced by sync_sources.ts |

## Pre-Requisites

- Create `v0.9.0` branches on ARBuilder-Forks repos that have been migrated to 0.10.0 (preserve original code)
- Repos that were reverted already have original code on `main` — these get `v0.10.0` branch (if migration is re-attempted later)

## What Gets Deleted

- `DOCS`, `PROJECT_EXAMPLES`, `M3_SOURCES`, `M3_GITHUB_REPOS` dicts from `config.py`
- `register_m3_sources.ts`
- Dual-chunk transform logic in `processor.py`

## What Stays

- `config.py` — thin wrapper, backward-compat helpers
- `version_manager.py` — still needed for `_fix_code()` transforms in code generation
- Admin UI — viewing status, triggering refresh (source registration flows from `sources.json`)

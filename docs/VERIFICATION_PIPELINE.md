# Source Verification Pipeline

## Overview

ARBuilder uses automated verification to ensure only working, SDK-compatible code enters the knowledge base. Two scripts handle this:

- **`scripts/verify_source.py`** — 6-step verification for individual repos (compile, test, health)
- **`scripts/maintain_sources.py`** — Ongoing maintenance (SDK monitoring, discovery, health checks)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      SOURCE REGISTRY                         │
│  scraper/config.py (PROJECT_EXAMPLES dict)                   │
│  19 verified repos across 3 SDK categories                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┼──────────────┐
         ▼             ▼              ▼
┌─────────────┐ ┌────────────┐ ┌──────────────┐
│ verify_     │ │ maintain_  │ │ audit_       │
│ source.py   │ │ sources.py │ │ data.py      │
│             │ │            │ │              │
│ • SDK ver   │ │ • monitor  │ │ • orphan     │
│ • compile   │ │ • discover │ │   detection  │
│ • deploy    │ │ • health   │ │ • config     │
│ • tests     │ │            │ │   drift      │
│ • AI review │ │            │ │              │
│ • fork      │ │            │ │              │
└─────────────┘ └────────────┘ └──────────────┘
```

## Verification Steps (verify_source.py)

| Step | Name | Method | Pass Criteria |
|------|------|--------|---------------|
| 1 | SDK Version | Parse Cargo.toml / package.json | stylus-sdk >= 0.8.0 or @arbitrum/sdk >= 4.0.0 |
| 2 | Compile | `cargo build --release` / `npm run build` | Exit code 0 |
| 3 | Deploy | Deploy to Arbitrum Sepolia | Successful deployment (optional) |
| 4 | Tests, Health & Audit | `cargo test` + GitHub API + dependency audit | Tests pass, not archived, no critical vulns |
| 5 | AI Review | LLM code review | Security, quality, teaching value (optional) |
| 6 | Fork | Fork to our org | Preservation copy (optional) |

### Dependency Audit (integrated into Step 4)

Step 4 now includes dependency vulnerability scanning:

- **Rust repos**: `cargo audit --json` — checks for known CVEs in Cargo.lock dependencies
- **TypeScript repos**: `npm audit --json` — checks for known vulnerabilities in package-lock.json

Results are stored in the step details under the `dependency_audit` key:
```json
{
  "dependency_audit": {
    "audit_run": true,
    "tool": "cargo audit",
    "has_vulnerabilities": false,
    "count": 0
  }
}
```

Prerequisites: `cargo install cargo-audit` for Rust repos, `npm` for TypeScript repos.

### Usage

```bash
# Verify a single repo (steps 1, 2, 4)
python scripts/verify_source.py https://github.com/org/repo --steps 1,2,4

# Verify all repos in config
python scripts/verify_source.py --all --steps 1,2,4

# Full verification with deployment
python scripts/verify_source.py --all --deploy

# Save JSON report
python scripts/verify_source.py --all --steps 1,2,4 --output reports/verification.json
```

## Maintenance Operations (maintain_sources.py)

### A. SDK Version Monitor

Checks crates.io and npm for new SDK releases, flags all configured repos that are behind.

```bash
python scripts/maintain_sources.py monitor
```

### B. Repo Discovery

Searches GitHub for new community repos using stylus-sdk or @arbitrum/sdk. Returns candidates sorted by stars, filtered against already-known repos.

```bash
python scripts/maintain_sources.py discover --min-stars 3
```

### C. Health Check

Checks all configured repos via GitHub API (archived? deleted? stale?).

```bash
python scripts/maintain_sources.py health
```

### Run All

```bash
python scripts/maintain_sources.py all --output reports/maintenance.json
```

## Handling Scenarios

### New SDK Release

```bash
# 1. Monitor detects new version
python scripts/maintain_sources.py monitor

# 2. Re-verify all repos
python scripts/verify_source.py --all --steps 1,2,4

# 3. Update config for repos that pass, remove those that fail
# 4. Re-run pipeline
```

### Repo Archived or Deleted

```bash
# 1. Health check detects issue
python scripts/maintain_sources.py health

# 2. Remove from config, add to "Removed Sources" in DATA_CURATION_POLICY.md
# 3. Prune orphan data
python scripts/audit_data.py --prune --confirm
```

### New Community Project Found

```bash
# 1. Discovery finds candidate
python scripts/maintain_sources.py discover

# 2. Verify it
python scripts/verify_source.py https://github.com/org/repo --steps 1,2,4

# 3. If passes, add to scraper/config.py
# 4. Run pipeline to ingest
```

## Last Verification Results (2026-02-10)

- **Tool**: `scripts/verify_source.py --all --steps 1,2,4`
- **Before**: 34 repos
- **After cleanup**: 16 repos (removed 10 challenge dupes, 5 broken scaffolds, 2 broken community, 1 broken production)
- **After M2 additions**: 19 repos (added 3 community @arbitrum/sdk repos)
- **Report**: `reports/verification_2026-02-10.json`

## Key Files

| File | Purpose |
|------|---------|
| `scraper/config.py` | Source of truth for all data sources (19 repos) |
| `scraper/version_extractor.py` | SDK version parsing from Cargo.toml/package.json |
| `scripts/verify_source.py` | 6-step repo verification pipeline |
| `scripts/maintain_sources.py` | SDK monitoring, repo discovery, health checks |
| `scripts/audit_data.py` | Detect orphans and config drift |
| `docs/DATA_CURATION_POLICY.md` | Curation rules and verified source registry |

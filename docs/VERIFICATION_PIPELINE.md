# Source Verification Pipeline

## Overview

ARBuilder uses automated verification to ensure only working, SDK-compatible code enters the knowledge base. Two scripts handle this:

- **`scripts/verify_source.py`** — 6-step verification for individual repos (compile, lint, test, health)
- **`scripts/maintain_sources.py`** — Ongoing maintenance (SDK monitoring, discovery, health checks, auto-remediation)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      SOURCE REGISTRY                       │
│  sources.json — single source of truth                     │
│  84 sources: docs (53) + GitHub repos (31)                 │
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
│ • lint      │ │ • health   │ │ • config     │
│ • deploy    │ │ • remediate│ │   drift      │
│ • tests     │ │            │ │              │
│ • AI review │ │            │ │              │
│ • fork      │ │            │ │              │
└─────────────┘ └────────────┘ └──────────────┘
```

## Verification Steps (verify_source.py)

| Step | Name | Method | Pass Criteria |
|------|------|--------|---------------|
| 1 | SDK Version | Parse Cargo.toml / package.json | stylus-sdk >= 0.8.0 or @arbitrum/sdk >= 4.0.0 |
| 2 | Compile + Lint | `cargo check --target wasm32-unknown-unknown` / `npm run build` + clippy/npm lint | Exit code 0 (lint is informational) |
| 3 | Deploy | Deploy to Arbitrum Sepolia | Successful deployment (optional, requires --deploy) |
| 4 | Tests, Health & Audit | `cargo test` + GitHub API + dependency audit | Tests pass, not archived, no critical vulns |
| 5 | AI Review | LLM code review | Security, quality, teaching value (optional) |
| 6 | Fork | Fork to our org | Preservation copy (optional) |

### Step 2: Compile + Lint Details

**Rust (Stylus) repos:**
- Compile: `cargo check --target wasm32-unknown-unknown --lib` (WASM target, no codegen)
- Lint: `cargo clippy --target wasm32-unknown-unknown --lib` (informational, doesn't affect pass/fail)
- Cleanup: `target/` deleted after each repo to save disk space

**TypeScript repos:**
- Package manager auto-detected: pnpm > yarn > npm (based on lockfile presence)
- Install: `{pkg_manager} install`
- Build: `{pkg_manager} run build`
- Lint: `{pkg_manager} run lint` if lint script exists (informational)
- Cleanup: `node_modules/` deleted after each repo

### Step 4: Tests, Health & Dependency Audit

**Tests:**
- Rust: `cargo test` — Stylus host function crashes detected and marked as "expected" (not failures)
- TypeScript: `npm test --passWithNoTests`

**Health (GitHub API):**
- Active: last push < 90 days
- Stale: 90-180 days
- Abandoned: > 180 days
- Archived/Deleted: Critical (fails verification)

**Dependency Audit:**
- Rust: `cargo audit --json` (requires `cargo install cargo-audit`)
- TypeScript: `npm audit --json`

Results stored under `dependency_audit` key in report:
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

### Source Coverage

The `--all` flag verifies all GitHub repos from `sources.json`:
- **M1 Stylus** (13 repos) + **M2 SDK** (5 repos) + **Orbit** (1 repo)
- **M3 dApp Builder** (12 repos: wagmi, viem, nestjs, chainlink, etc.)

### Usage

```bash
# Verify a single repo (steps 1, 2, 4)
python scripts/verify_source.py https://github.com/org/repo --steps 1,2,4

# Verify all repos in config (M1 + M2 + M3)
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

### D. Auto-Remediation

Removes **critical** (archived/deleted) repos from `sources.json` automatically. Flags **abandoned** (>365 days stale) repos for manual review but does not auto-remove them.

```bash
python scripts/maintain_sources.py remediate
```

### Run All

```bash
python scripts/maintain_sources.py all --output reports/maintenance.json
```

## GitHub Actions Automation

**Workflow: `.github/workflows/maintenance.yml`**

| Job | Trigger | What It Does |
|-----|---------|-------------|
| `sdk-monitor` | Weekly (Mon 6 AM UTC) | Checks for new SDK versions |
| `health-check` | Weekly (Mon 6 AM UTC) | Checks all repos for archived/deleted |
| `discover` | Manual only | Searches GitHub for new community repos |
| `reverify` | On SDK update OR manual | Runs `verify_source.py --all` to re-check all repos |
| `remediate` | Manual only | Runs `maintain_sources.py remediate` to auto-remove critical repos |
| `sync-sources` | Weekly + manual | Syncs `sources.json` to CF KV registry |
| `create-issue` | When problems found | Creates GitHub issue with maintenance label |

## Handling Scenarios

### New SDK Release

1. Weekly cron detects new version via `sdk-monitor` job
2. `reverify` job automatically triggers, re-verifying all repos
3. If repos fail, GitHub issue created for manual review
4. Run `remediate` manually if repos need removal

### Repo Archived or Deleted

```bash
# Option A: Auto-remediate (removes from config)
python scripts/maintain_sources.py remediate

# Option B: Manual
python scripts/maintain_sources.py health
# Review results, manually edit sources.json
python scripts/audit_data.py --prune --confirm
```

### New Community Project Found

```bash
# 1. Discovery finds candidate
python scripts/maintain_sources.py discover

# 2. Verify it
python scripts/verify_source.py https://github.com/org/repo --steps 1,2,4

# 3. If passes, add to sources.json
# 4. Run pipeline to ingest
```

## Last Verification Results (2026-02-21)

### Compile + Lint + Tests + Health (Steps 1, 2, 4)

- **Tool**: `scripts/verify_source.py --all --steps 1,2,4`
- **Total**: 31 repos — 15 pass, 16 fail
- **M1 Stylus**: 13 repos — 10 pass, 3 fail (test-helpers: native-only lib; stylusport: upstream SPL bug; cross-protocol: compile timeout)
- **M2 SDK**: 5 repos — 2 pass, 3 fail (tutorials: yarn workspace issue; api: build timeout; orbit-sdk: yarn install fail)
- **Orbit**: 1 repo — 0 pass (token-bridge: build timeout)
- **M3 dApp Builder**: 12 repos — 3 pass, 9 fail

**M3 failure analysis**: Most M3 failures are expected — large monorepos (wagmi, rainbowkit, chainlink, nestjs, daisyui) require project-specific build tooling (turbo, nx, workspace scripts) that a generic `npm/pnpm install && build` can't satisfy. All are actively maintained (health: active) and included for RAG teaching value, not as direct build targets. viem, graph-tooling, and subgraphs build successfully.

- **Report**: `reports/verification_full.json`

### AI Security + Code Quality Review (Step 5)

- **Tool**: `scripts/verify_source.py --all --steps 5`
- **Total**: 31 repos — 30 reviewed, 1 parse error (clink-bridging)
- **Security scores**: 75–100 (mean ~86/100)
- **Recommendations**: 6 "include", 24 "include_with_caveats", 1 skipped
- **Teaching value**: 2 "high" (rust-contracts-stylus, stylusport), 28 "medium"
- **Top security** (95–100): daisyui, stylusport, rust-contracts-stylus, wagmi, rainbowkit, graph-tooling, nestjs, arbitrum-token-bridge, arbitrum-subgraphs, arbitrum-tutorials

**Common issues flagged**: hardcoded private keys in examples (expected for tutorials), missing input validation on contract setters, use of deprecated Solidity versions in older SDK repos, `unwrap()`/`panic!()` usage in Rust code.

All repos scored ≥75 security and received "include" or "include_with_caveats" recommendation — none excluded.

- **Report**: `reports/verification_ai_review.json`

## Key Files

| File | Purpose |
|------|---------|
| `sources.json` | Single source of truth for all data sources (84 entries) |
| `scraper/config.py` | Thin wrapper — backward-compat helpers for Python consumers |
| `scripts/sync_sources.ts` | Sync sources.json to CF KV registry |
| `scraper/version_extractor.py` | SDK version parsing from Cargo.toml/package.json |
| `scripts/verify_source.py` | 6-step repo verification pipeline |
| `scripts/maintain_sources.py` | SDK monitoring, discovery, health checks, auto-remediation |
| `scripts/audit_data.py` | Detect orphans and config drift |
| `.github/workflows/maintenance.yml` | Weekly automation + manual triggers |
| `docs/DATA_CURATION_POLICY.md` | Curation rules and verified source registry |

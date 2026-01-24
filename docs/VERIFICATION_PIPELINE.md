# Source Verification Pipeline

## Overview

Instead of forking repos, we maintain a **source registry** with automated verification. Only verified sources get ingested into the knowledge base.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SOURCE REGISTRY                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │ Candidate   │  │ Verified    │  │ Excluded    │                  │
│  │ Sources     │  │ Sources     │  │ Sources     │                  │
│  └──────┬──────┘  └──────▲──────┘  └──────▲──────┘                  │
│         │                │                │                          │
│         ▼                │                │                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  VERIFICATION WORKER                          │   │
│  │  1. Clone repo                                                │   │
│  │  2. Check Cargo.toml for SDK version                         │   │
│  │  3. Run `cargo stylus check` (optional)                      │   │
│  │  4. Check GitHub API (archived? last commit?)                │   │
│  │  5. Update registry with result                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         TRIGGERS                                     │
│  • Cron (daily/weekly)                                              │
│  • SDK release detected (monitor crates.io)                         │
│  • Manual trigger (new candidate added)                             │
│  • Webhook (repo updated)                                           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         ACTIONS                                      │
│  • Pass → Add to verified, ingest                                   │
│  • Fail → Move to excluded, log reason                              │
│  • Degraded → Alert team, keep previous version                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Source Registry Schema

```json
{
  "sources": [
    {
      "url": "https://github.com/OpenZeppelin/rust-contracts-stylus",
      "type": "stylus",
      "category": "production",
      "status": "verified",
      "last_verified": "2025-01-24T00:00:00Z",
      "sdk_version": "0.9.0",
      "last_commit": "2025-01-20T00:00:00Z",
      "archived": false,
      "verification_result": {
        "cargo_check": "pass",
        "stylus_check": "pass",
        "notes": ""
      }
    }
  ]
}
```

## Verification Checks

### For Stylus Repos

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| SDK Version | Parse Cargo.toml | stylus-sdk >= 0.9.0 |
| Repo Active | GitHub API | Last commit < 6 months |
| Not Archived | GitHub API | archived = false |
| Compiles | `cargo stylus check` | Exit code 0 |

### For SDK/TypeScript Repos

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| SDK Version | Parse package.json | @arbitrum/sdk >= 4.0.0 |
| Repo Active | GitHub API | Last commit < 6 months |
| Not Archived | GitHub API | archived = false |
| Tests Pass | `npm test` (optional) | Exit code 0 |

## Handling Scenarios

### 1. New SDK Release (e.g., 0.10.0)

```
1. SDK release monitor detects new version on crates.io
2. Trigger re-verification of all verified sources
3. For each source:
   - Clone latest
   - Update Cargo.toml to new SDK version
   - Run verification
   - If pass: update registry
   - If fail: alert team, keep ingesting old version temporarily
4. Generate report: "X of Y sources compatible with 0.10.0"
```

### 2. Author Stops Updating

```
1. Daily check detects last_commit > 6 months
2. Mark source as "stale"
3. Still ingest if verification passes
4. If verification fails, move to excluded
5. No action needed from us - natural lifecycle
```

### 3. Repo Archived

```
1. GitHub API check detects archived = true
2. Move source to excluded
3. Remove from next ingestion cycle
4. Log reason: "Repository archived by owner"
```

### 4. Owner Updates Repo

```
1. Webhook or daily check detects new commits
2. Trigger re-verification
3. If passes: re-ingest with fresh content
4. If fails: alert team, keep previous version
```

### 5. Code Not Working

```
1. Verification fails (cargo stylus check fails)
2. Move to excluded
3. Log failure reason
4. Alert team if previously verified source fails
```

## Implementation Phases

### Phase 1: Manual Registry (Current)
- JSON file with source list
- Manual verification before adding
- Documented in DATA_CURATION_POLICY.md

### Phase 2: Automated Checks
- Script to verify sources
- Run before each scrape
- GitHub API integration

### Phase 3: Full Automation
- Cron job for periodic verification
- SDK release monitoring
- Slack/Discord alerts
- Dashboard for status

## Candidate Sources to Verify

### Stylus (need to check SDK version)

| Repo | Category | Notes |
|------|----------|-------|
| cygaar/inkmate | Library | Gas-efficient primitives |
| code-423n4/2024-10-superposition | Audited | Oct 2024 audit |
| malik672/open-stylus | Library | OZ alternatives |
| gvladika/stylus-erc721 | Example | ERC-721 impl |

### SDK (already verified)

| Repo | Category | Notes |
|------|----------|-------|
| OffchainLabs/arbitrum-tutorials | Examples | Official, comprehensive |
| OffchainLabs/arbitrum-sdk | SDK | Official SDK source |

## Our Own Examples (Optional Future)

If we decide to create our own reference implementations:

```
ARBuilder/
└── examples/
    ├── stylus/
    │   ├── erc20-basic/        # Minimal ERC20
    │   ├── erc721-basic/       # Minimal ERC721
    │   └── counter/            # Hello world
    └── sdk/
        ├── eth-bridge/         # ETH deposit/withdraw
        ├── erc20-bridge/       # Token bridging
        └── messaging/          # Retryable tickets
```

Benefits:
- Full control over versions
- Guaranteed to work
- Tailored for code generation

Costs:
- Maintenance burden
- Duplicates official examples

**Recommendation:** Only create our own examples if official ones become unreliable.

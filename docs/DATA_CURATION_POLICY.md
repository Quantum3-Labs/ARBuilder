# Data Curation Policy

## Overview

ARBuilder's knowledge base must only contain **verified, working code** that compiles with the current SDK version. This document outlines our curation policy and the rationale behind source selection.

## Curation Rules

### 1. Official Documentation
- **Always include** - maintained by Arbitrum team
- Source: `docs.arbitrum.io`
- No verification needed - docs are always current

### 2. Code Repositories

**Inclusion criteria:**
- Must compile with `stylus-sdk >= 0.8.0` (minimum supported version)
- Prefer `stylus-sdk >= 0.10.0` (main version)
- Must be actively maintained (commits within 6 months)
- Must be deployable and functional
- Verified with `scripts/verify_source.py --steps 1,2,4`

**Exclusion criteria:**
- Meta-lists (e.g., awesome-stylus) - contain mixed quality/versions
- Unverified community submissions
- Deprecated SDK versions (< 0.8.0)
- Non-Arbitrum code (e.g., general Rust libs, UI frameworks)
- Challenge submissions with identical template code (zero unique value)
- Scaffold forks that don't compile

### 3. Version Requirements

| Component | Main Version | Minimum Version |
|-----------|--------------|-----------------|
| stylus-sdk | 0.10.0 | 0.8.0 |
| @arbitrum/sdk | 4.0.4 | 4.0.0 |
| alloy-primitives | 1.0.1 | 0.8.0 |
| alloy-sol-types | 1.0.1 | 0.8.0 |
| Rust | 1.88.0 | 1.81 |

**Note:** Anything below stylus-sdk 0.8.0 is deprecated (uses `#[external]` instead of `#[public]`).

## Current Verified Sources (19 repos, verified 2026-02-10)

### M1: Stylus Development

**Official Examples:**
| Source | SDK Version | Status | Notes |
|--------|-------------|--------|-------|
| OffchainLabs/stylus-hello-world | 0.9.0 | Verified | Official example |
| OffchainLabs/stylus-quickstart-vending-machine | 0.8.4 | Verified | Official example |
| ArbitrumFoundation/stylus-workshop-gol | 0.9.0 | Verified | Tests fail (needs devnode) |

**Production Libraries:**
| Source | SDK Version | Status | Notes |
|--------|-------------|--------|-------|
| OpenZeppelin/rust-contracts-stylus | 0.9.0 | Verified | Production library (146 stars) |
| OpenZeppelin/stylus-test-helpers | 0.9.0 | Verified | Motsu testing framework (47 tests) |
| oak-security/stylusport | 0.9.0 | Verified | Linker error on arm64, compiles to wasm32 |
| gnosisguild/stylus-provider | 0.8.4 | Verified | Tests fail, production library |

**Community Projects:**
| Source | SDK Version | Status | Notes |
|--------|-------------|--------|-------|
| philogicae/ethbuc2025-gyges | 0.8.4 | Verified | Hackathon project |
| Oluwatobilobaoke/erc6909-with-arbitrum-stylus | 0.9.0 | Verified | ERC6909 implementation |
| hummusonrails/fortune-generator | 0.8.0 | Verified | Randomness example |

**Scaffold-Stylus Projects:**
| Source | SDK Version | Status | Notes |
|--------|-------------|--------|-------|
| Arb-Stylus/scaffold-stylus | 0.9.0 | Verified | Canonical scaffold template |
| iyansr/cross-protocol-defi-tracker | 0.9.0 | Verified | DeFi tracker dApp |
| Einarmig/WalletNaming-scaffold-stylus | 0.9.0 | Verified | Wallet naming dApp |

### M2: Arbitrum SDK

**Official Repos:**
| Source | SDK Version | Status | Notes |
|--------|-------------|--------|-------|
| OffchainLabs/arbitrum-sdk | N/A | Verified | Official SDK library |
| OffchainLabs/arbitrum-tutorials | 4.0.1 | Verified | Working bridging/messaging examples |

**Community Examples:**
| Source | SDK Version | Status | Notes |
|--------|-------------|--------|-------|
| kevinb1003/arbitrum-api | 4.0.4 | Verified | REST API wrapping EthBridger/Erc20Bridger (32 stars) |
| gelatodigital/how-tos-18-arbitrum-orbit-bridging | 4.0.2 | Verified | Orbit chain bridging scripts |
| gelatodigital/clink-bridging-cross-messaging | 4.0.2 | Verified | Cross-chain messaging (abandoned but unique) |

### Orbit SDK

| Source | SDK Version | Status | Notes |
|--------|-------------|--------|-------|
| OffchainLabs/arbitrum-orbit-sdk | 4.0.4 | Verified | Official Orbit SDK |

## Removed Sources (2026-02-10 Cleanup)

### Challenge Submissions (10 repos removed)
All 98% identical template code with zero unique value. Added 4700+ duplicate chunks that polluted retrieval results.
- Huygon764, Fnz11, ndrewlex, athallarizky, dimasd-angga, ammar-rasyidi, rizkianakbar, math-marcellino, lucky-ivanius (x2), dante4rt (404)

### Broken Scaffold Forks (5 repos removed)
All fail to compile due to OZ 0.3.0 incompatibility or linker errors:
- mavix21/poap-scaffold-stylus (openzeppelin-stylus 0.3.0 incompatible)
- dchagast/scaffold-stylus-staking (linker errors on arm64)
- cidkagenow/EmersonApp-scaffold-stylus (non-exhaustive patterns)
- autodidacttrade/DeFi-Project-ERC20 (linker errors)
- ByteToHex/VRF-scaffold-stylus (linker errors)

### Broken Community Projects (2 repos removed)
- IndexMaker/vaultworks (archived, no stylus-sdk detected)
- Inteli-Club5/EdCation (compile fails, StorageAddress::new wrong args)

### Broken Production Repos (1 repo removed)
- stylus-developers-guild/reentrancy-transient-storage (compile fails, trait bound error)

### Deprecated SDK Versions (< 0.8.0)
- OffchainLabs/stylus-chess (v0.4.2), OffchainLabs/stylus-by-example (v0.6.0)
- fluidity-money/9lives.so (v0.7.0), fluidity-money/long.so (v0.7.0)
- hammertoe/ArbitrumOnchainAgent (v0.7.0), cygaar/inkmate (v0.4.3)
- malik672/open-stylus (v0.4.2), code-423n4/2024-10-superposition (v0.6.0)

### Irrelevant Code
- nestjs/nest, saadeghi/daisyui, rainbow-me/rainbowkit
- smartcontractkit/chainlink, messari/subgraphs

## Maintenance Runbook

### Automated Tools

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/verify_source.py` | Verify repos compile and pass tests | `python scripts/verify_source.py --all --steps 1,2,4` |
| `scripts/maintain_sources.py monitor` | Check crates.io/npm for new SDK releases | Flags all outdated repos |
| `scripts/maintain_sources.py discover` | Search GitHub for new community repos | Returns candidates to verify |
| `scripts/maintain_sources.py health` | Check GitHub health of all config repos | Finds archived/deleted repos |
| `scripts/audit_data.py` | Detect orphans and config drift | Compare disk vs config |

### Scenario 1: Adding New Sources

```bash
# 1. Verify the repo
python scripts/verify_source.py https://github.com/org/repo --steps 1,2,4

# 2. Add to scraper/config.py under the right section
#    Each repo entry needs: url, sdk_version, verified (date)

# 3. Run the pipeline
python -m scraper.run --skip-web
python -m src.preprocessing.processor
python -m src.embeddings.vectordb --reset

# 4. Sync remote (production)
python scripts/sync_remote_db.py --dry-run
python scripts/sync_remote_db.py --reingest
```

### Scenario 2: Removing Unmaintained Sources

```bash
# 1. Run health check to identify issues
python scripts/maintain_sources.py health

# 2. Remove from scraper/config.py
# 3. Prune orphan repos from disk
python scripts/audit_data.py --prune --confirm

# 4. Re-run pipeline and sync remote
python -m src.preprocessing.processor
python -m src.embeddings.vectordb --reset
python scripts/sync_remote_db.py --delete-stale
python scripts/sync_remote_db.py --reingest
```

### Scenario 3: New SDK Version Released

```bash
# 1. Check what's outdated
python scripts/maintain_sources.py monitor

# 2. Update scraper/config.py version constants
# 3. Re-verify all repos with new SDK
python scripts/verify_source.py --all --steps 1,2,4

# 4. Update config, re-run pipeline, sync remote
```

### Quick Reference: Key Files

| File | Purpose |
|------|---------|
| `scraper/config.py` | Source of truth for all data sources |
| `shared/stylus-versions.json` | SDK version metadata and compatibility |
| `scripts/verify_source.py` | 6-step repo verification pipeline |
| `scripts/maintain_sources.py` | SDK monitoring, repo discovery, health checks |
| `scripts/audit_data.py` | Detect orphans and config drift |
| `scripts/sync_remote_db.py` | Sync remote Cloudflare DB with local config |

### Quick Reference: Environment Variables

| Variable | Purpose |
|----------|---------|
| `GITHUB_TOKEN` | GitHub API auth (for discovery + health checks) |
| `ARBBUILDER_ADMIN_SECRET` | Admin API auth for remote sync |
| `ARBBUILDER_API_URL` | Remote API URL (default: https://arbbuilder.whymelabs.com) |

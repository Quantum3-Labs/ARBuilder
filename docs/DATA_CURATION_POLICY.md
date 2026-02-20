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
- Verified with `scripts/verify_source.py --steps 1,2,4,5`

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

## Verification Coverage

The verification pipeline (`scripts/verify_source.py --all`) covers all source registries:

- **PROJECT_EXAMPLES** (19 repos): M1 Stylus (13) + M2 SDK (5) + Orbit (1)
- **M3_GITHUB_REPOS** (12 repos): wagmi, viem, nestjs, chainlink, etc.

**Verification includes:**
- SDK version check (stylus-sdk >= 0.8.0 or @arbitrum/sdk >= 4.0.0)
- Compile check + linting (cargo clippy for Rust, npm lint for TypeScript — informational)
- Tests, GitHub health, and dependency audit
- Package manager auto-detection (pnpm/yarn/npm from lockfile)

**Continuous verification:** The `maintenance.yml` workflow automatically re-verifies all repos when a new SDK version is detected, and creates a GitHub issue if any repos fail.

### AI Security + Code Quality Review

Step 5 of the verification pipeline runs an LLM-based code review (via OpenRouter) on each repo's source files:

- **Security score** (0–100): Checks for key management issues, input validation, access control, overflow risks
- **Quality score** (0–100): Code structure, error handling, documentation
- **Teaching value** (high/medium/low): Whether the code demonstrates clean patterns worth teaching the AI
- **Recommendation**: "include", "include_with_caveats", or "exclude"

**Last review (2026-02-21):** 30/31 repos reviewed. Mean security score: 86/100. All repos scored ≥75 and received "include" or "include_with_caveats". 2 repos rated "high" teaching value (rust-contracts-stylus, stylusport). Common flagged issues: hardcoded example keys, missing input validation, use of `unwrap()`/`panic!()` — typical for tutorial code and non-blocking.

## Current Verified Sources (19 repos, verified 2026-02-16)

> **Fork Strategy:** All 13 Stylus repos are sourced from the [ARBuilder-Forks](https://github.com/ARBuilder-Forks) GitHub org. This ensures resilience against upstream deletions. Each entry's `forked_from` field tracks the original repo.

### M1: Stylus Development

**Official Examples:**
| Source (ARBuilder-Forks) | Forked From | SDK Version | Notes |
|--------------------------|-------------|-------------|-------|
| ARBuilder-Forks/stylus-hello-world | OffchainLabs/stylus-hello-world | 0.10.0 | Migrated to SDK 0.10.0 |
| ARBuilder-Forks/stylus-quickstart-vending-machine | OffchainLabs/stylus-quickstart-vending-machine | 0.10.0 | Migrated to SDK 0.10.0 |
| ARBuilder-Forks/stylus-workshop-gol | ArbitrumFoundation/stylus-workshop-gol | 0.9.0 | Reverted — OZ alloy conflict |

**Production Libraries:**
| Source (ARBuilder-Forks) | Forked From | SDK Version | Notes |
|--------------------------|-------------|-------------|-------|
| ARBuilder-Forks/rust-contracts-stylus | OpenZeppelin/rust-contracts-stylus | 0.9.0 | Reverted — c-kzg + alloy conflict |
| ARBuilder-Forks/stylus-test-helpers | OpenZeppelin/stylus-test-helpers | 0.9.0 | Reverted — c-kzg native lib conflict |
| ARBuilder-Forks/stylusport | oak-security/stylusport | 0.9.0 | Reverted — c-kzg native lib conflict |
| ARBuilder-Forks/stylus-provider | gnosisguild/stylus-provider | 0.8.4 | Reverted — c-kzg native lib conflict |

**Community Projects:**
| Source (ARBuilder-Forks) | Forked From | SDK Version | Notes |
|--------------------------|-------------|-------------|-------|
| ARBuilder-Forks/ethbuc2025-gyges | philogicae/ethbuc2025-gyges | 0.10.0 | Migrated to SDK 0.10.0 |
| ARBuilder-Forks/erc6909-with-arbitrum-stylus | Oluwatobilobaoke/erc6909-with-arbitrum-stylus | 0.10.0 | Migrated to SDK 0.10.0 |
| ARBuilder-Forks/fortune-generator | hummusonrails/fortune-generator | 0.10.0 | Migrated to SDK 0.10.0 |

**Scaffold-Stylus Projects:**
| Source (ARBuilder-Forks) | Forked From | SDK Version | Notes |
|--------------------------|-------------|-------------|-------|
| ARBuilder-Forks/scaffold-stylus | Arb-Stylus/scaffold-stylus | 0.9.0 | Reverted — OZ v0.3.0 incompatible |
| ARBuilder-Forks/cross-protocol-defi-tracker | iyansr/cross-protocol-defi-tracker | 0.9.0 | Reverted — OZ alloy conflict |
| ARBuilder-Forks/WalletNaming-scaffold-stylus | Einarmig/WalletNaming-scaffold-stylus | 0.10.0 | Migrated to SDK 0.10.0 |

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

### Previously Excluded (Now M3 Sources)
The following repos were originally excluded as "irrelevant" but are now included as M3 dApp Builder sources:
- nestjs/nest, saadeghi/daisyui, rainbow-me/rainbowkit
- smartcontractkit/chainlink, messari/subgraphs
- wevm/wagmi, wevm/viem, scaffold-eth/scaffold-eth-2
- graphprotocol/graph-tooling, smartcontractkit/smart-contract-examples
- OffchainLabs/arbitrum-token-bridge

### M3: Full dApp Builder

**Documentation Sources (36 URLs):**
| Category | Subcategory | Count | Source |
|----------|-------------|-------|--------|
| m3_backend | nestjs | 5 | docs.nestjs.com |
| m3_backend | express | 3 | expressjs.com |
| m3_frontend | wagmi | 5 | wagmi.sh |
| m3_frontend | viem | 4 | viem.sh |
| m3_frontend | rainbowkit | 4 | rainbowkit.com |
| m3_frontend | daisyui | 5 | daisyui.com |
| m3_indexer | the_graph | 5 | thegraph.com |
| m3_oracle | chainlink | 5 | docs.chain.link |

**GitHub Repos (12 repos):**
| Source | Category | Notes |
|--------|----------|-------|
| wevm/wagmi | m3_frontend | React hooks for Ethereum |
| wevm/viem | m3_frontend | TypeScript Interface for Ethereum |
| rainbow-me/rainbowkit | m3_frontend | Wallet connection UI |
| saadeghi/daisyui | m3_frontend | Tailwind CSS component library |
| scaffold-eth/scaffold-eth-2 | m3_frontend | Full-stack Ethereum starter |
| graphprotocol/graph-tooling | m3_indexer | The Graph CLI and codegen |
| messari/subgraphs | m3_indexer | Production subgraph examples |
| smartcontractkit/smart-contract-examples | m3_oracle | Chainlink integration examples |
| smartcontractkit/chainlink | m3_oracle | Chainlink oracle framework |
| nestjs/nest | m3_backend | NestJS framework |
| OffchainLabs/arbitrum-token-bridge | m3_backend | Bridge UI patterns |

**M3 Inclusion Criteria:**
- Framework library repos are assessed for **teaching value**, not SDK version compliance
- Documentation must be from stable/current versions
- Large repos (wagmi, nestjs, chainlink) are ingested via CF Queue async pipeline
- Content is filtered through the standard 3-layer system (SKIP_DIRS, hex filter, dedup)

## Data Quality Filters (3-Layer System)

The preprocessing pipeline applies a 3-layer filtering system to remove junk data before it reaches the vector database. Without these filters, ~62% of chunks would be low-quality vendored code, auto-generated files, or bytecode.

### Layer 1: Scraper (`scraper/github_scraper.py`)

Skips junk files at clone time, before reading content from disk.

| Filter | What it catches | Example |
|--------|----------------|---------|
| `SKIP_DIRS` | Vendored crates, build artifacts | `vendor/`, `third_party/`, `artifacts/` |
| `SKIP_FILE_NAMES` | Lock files | `package-lock.json`, `Cargo.lock` |
| `SKIP_FILE_SUBSTRINGS` | TypeChain factories | `*__factory.ts`, `*__factory.js` |
| `SKIP_TS_JS_IN_DIRS` | TS/JS in ABI dirs | `abi/*.ts` (keeps `.rs`, `.json`) |
| `SKIP_DIR_PREFIXES` | ABI variant dirs | `abi-bold/`, `abi-nitro/` |

### Layer 2: Processor (`src/preprocessing/processor.py`)

Defense-in-depth for files already in `github_repos_*.json`, plus content-based filters.

| Filter | What it catches |
|--------|----------------|
| `_should_skip_file()` | Same patterns as Layer 1 (catches pre-existing raw data) |
| `_is_hex_heavy()` | Bytecode mocks, ABI hex dumps (>40% hex chars) |
| `_cross_repo_dedup()` | Exact-content duplicates across different repos (keeps highest-priority source) |

**Cross-repo dedup priority** (lower number = kept):
1. `official_examples` / `official_repos`
2. `verified_production` / `forked_0_10_0`
3. `community_projects` / `community_examples`
4. `scaffold_projects`

### Layer 3: Stats & Reporting

Filter results are tracked in `processing_stats_*.json` under `filter_stats` and printed to console after processing.

## Embedding Model

Both the local Python pipeline and Cloudflare hosted service use **BGE-M3** (1024 dimensions) for embedding consistency:

| Environment | Model ID | Provider |
|-------------|----------|----------|
| Local (Python) | `baai/bge-m3` | OpenRouter |
| CF Workers (hosted) | `@cf/baai/bge-m3` | Cloudflare Workers AI |

BGE-M3 supports multi-lingual text and dense/sparse/multi-vector retrieval. Using the same model ensures compatible embeddings — corpus vectors from Python work with query vectors from the CF worker. Pre-built embeddings are published via GitHub Releases for zero-setup local dev.

## Multi-Version Data Strategy

### Overview

The pipeline supports both SDK 0.9.x and 0.10.0 code through two complementary approaches:

1. **Dual-chunk ingestion**: Original 0.9.x code is preserved alongside a modernized 0.10.0 copy
2. **Forked repos**: Community repos are forked and fully migrated to SDK 0.10.0

### Fork Strategy

All 13 Stylus repos in the config are sourced from the [ARBuilder-Forks](https://github.com/ARBuilder-Forks) GitHub org. This ensures resilience against upstream deletions. 6 forks are fully migrated to SDK 0.10.0; 7 retain original code (blocked by upstream dependency conflicts) and rely on the dual-chunk strategy for 0.10.0 coverage.

```bash
# Fork and migrate all repos
python scripts/fork_and_migrate.py --all

# Dry run first to review changes
python scripts/fork_and_migrate.py --all --dry-run
```

The script:
1. Forks the repo to `ARBuilder-Forks/{repo-name}` via `gh`
2. Applies `apply_version_transforms()` to all `.rs` files
3. Updates Cargo.toml with 0.10.0 dependencies
4. Adds required files (Stylus.toml, rust-toolchain.toml, src/main.rs)
5. Runs compilation verification (`cargo check`)
6. Auto-fixes failures using `_fix_code()` patterns (up to 2 attempts)
7. Commits and pushes

**Results (2026-02-16):** 6 of 13 repos compile with SDK 0.10.0:

| Fork | Original | Status |
|------|----------|--------|
| ARBuilder-Forks/stylus-hello-world | OffchainLabs/stylus-hello-world | Compiling |
| ARBuilder-Forks/stylus-quickstart-vending-machine | OffchainLabs/stylus-quickstart-vending-machine | Compiling |
| ARBuilder-Forks/erc6909-with-arbitrum-stylus | Oluwatobilobaoke/erc6909-with-arbitrum-stylus | Compiling |
| ARBuilder-Forks/fortune-generator | hummusonrails/fortune-generator | Compiling |
| ARBuilder-Forks/ethbuc2025-gyges | philogicae/ethbuc2025-gyges | Compiling |
| ARBuilder-Forks/WalletNaming-scaffold-stylus | Einarmig/WalletNaming-scaffold-stylus | Compiling |
| ARBuilder-Forks/rust-contracts-stylus | OpenZeppelin/rust-contracts-stylus | Blocked: c-kzg + alloy version conflict |
| ARBuilder-Forks/stylus-test-helpers | OpenZeppelin/stylus-test-helpers | Blocked: c-kzg native library conflict |
| ARBuilder-Forks/stylusport | oak-security/stylusport | Blocked: c-kzg native library conflict |
| ARBuilder-Forks/stylus-provider | gnosisguild/stylus-provider | Blocked: c-kzg native library conflict |
| ARBuilder-Forks/stylus-workshop-gol | ArbitrumFoundation/stylus-workshop-gol | Blocked: OZ alloy-primitives mismatch |
| ARBuilder-Forks/cross-protocol-defi-tracker | iyansr/cross-protocol-defi-tracker | Blocked: OZ alloy-primitives mismatch |
| ARBuilder-Forks/scaffold-stylus | Arb-Stylus/scaffold-stylus | Blocked: OZ v0.3.0 incompatible with SDK 0.10.0 |

The 7 blocked repos all depend on OpenZeppelin's rust-contracts-stylus or its test helpers (motsu), which pin `alloy-primitives = "=0.8.20"` — incompatible with stylus-sdk 0.10.0's requirement for alloy-primitives 1.0.1. These will unblock when OZ releases a compatible version.

All Stylus repos in `scraper/config.py` now point to ARBuilder-Forks URLs. Each entry includes a `forked_from` field tracking the original repo:
```python
{"url": "https://github.com/ARBuilder-Forks/stylus-hello-world",
 "sdk_version": "0.10.0", "verified": "2026-02-16",
 "forked_from": "OffchainLabs/stylus-hello-world"},
```

Repos that couldn't be migrated to 0.10.0 retain their original `sdk_version` and use the dual-chunk strategy for 0.10.0 coverage.

### Dual-Chunk Ingestion

During preprocessing, legacy 0.9.x `.rs` chunks get both their original form and a modernized copy:

```
Original chunk (sdk_version: "0.9.0")  → kept as-is
  └── Modernized copy (sdk_version: "0.10.0", modernized: true)  → new chunk with _mod ID suffix
```

The modernized copy uses `apply_version_transforms()` from `version_manager.py` (centralized transform rules).

### Transform Rules (0.9.x → 0.10.0)

| Old Pattern (0.9.x) | New Pattern (0.10.0) |
|---------------------|---------------------|
| `msg::sender()` | `self.vm().msg_sender()` |
| `msg::value()` | `self.vm().msg_value()` |
| `evm::log(...)` | `self.vm().log(...)` |
| `use stylus_sdk::evm` | (removed) |
| `use stylus_sdk::msg` | (removed) |
| `.getter(...)` | `.get(...)` |
| `sol! { interface ... }` | `sol_interface! { interface ... }` |
| `StorageMap<K, V>` | `mapping(k => v)` |
| `StorageVec<X>` | `x[]` |
| `StorageAddress` | `address` |
| `StorageU256` | `uint256` |
| `print_abi()` | `print_from_args()` |

These transforms are defined centrally in `VERSION_TRANSFORMS` in `src/utils/version_manager.py` and consumed by:
- `src/preprocessing/processor.py` (dual-chunk creation)
- `src/templates/stylus_templates.py` (template adaptation)
- `src/mcp/tools/generate_stylus_code.py` (`_fix_code()`)
- `src/mcp/tools/ask_stylus.py` (`_fix_code_in_response()`)
- `scripts/fork_and_migrate.py` (repo migration)

### Version-Aware Generation

All code generation tools accept `target_version`:
- `generate_stylus_code(target_version="0.9.0")` → produces 0.9.x code with msg::sender(), .getter(), etc.
- `ask_stylus(target_version="0.9.0")` → fixes code blocks in responses to use 0.9.x patterns
- Templates are adapted via `adapt_template()` to strip 0.10-only files and reverse transforms

### Version-Aware Retrieval

The RAG pipeline applies version-aware scoring during retrieval:

- Chunks matching `target_version` major.minor get a **1.2x boost**
- Chunks from deprecated SDK versions (< 0.8.0) get a **0.8x penalty**
- Modernized chunks matching target get **1.1x boost**; non-matching modernized chunks don't get version boost (lets real 0.9.x chunks win when targeting 0.9.x)
- `target_version` flows from MCP schema → `generate_stylus_code` → `get_stylus_context` → `vectordb.hybrid_search`

## Maintenance Runbook

### Automated Tools

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/verify_source.py` | Verify repos compile, lint, and pass tests | `python scripts/verify_source.py --all --steps 1,2,4` |
| `scripts/maintain_sources.py monitor` | Check crates.io/npm for new SDK releases | Flags all outdated repos |
| `scripts/maintain_sources.py discover` | Search GitHub for new community repos | Returns candidates to verify |
| `scripts/maintain_sources.py health` | Check GitHub health of all config repos | Finds archived/deleted repos |
| `scripts/maintain_sources.py remediate` | Auto-remove critical repos from config | Removes archived/deleted, flags abandoned |
| `scripts/audit_data.py` | Detect orphans and config drift | Compare disk vs config |

### Auto-Remediation Policy

The `remediate` command performs automatic cleanup of the source registry:

- **Critical (archived/deleted/404)**: Automatically removed from `scraper/config.py`
- **Abandoned (>365 days without update)**: Flagged for manual review but NOT auto-removed
- **Stale (90-365 days)**: Informational only, no action taken

In CI (`maintenance.yml`), remediation is **manual trigger only** — config changes always need human review. When triggered, it auto-commits the cleaned config.

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
# Option A: Auto-remediate (removes archived/deleted from config)
python scripts/maintain_sources.py remediate

# Option B: Manual
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
| `shared/stylus-versions.json` | SDK version metadata, patterns, and compatibility |
| `src/utils/version_manager.py` | Version transforms, cargo deps, pattern lookup |
| `scripts/verify_source.py` | 6-step repo verification pipeline |
| `scripts/fork_and_migrate.py` | Fork repos to ARBuilder-Forks + migrate to SDK 0.10.0 |
| `scripts/maintain_sources.py` | SDK monitoring, repo discovery, health checks |
| `scripts/audit_data.py` | Detect orphans and config drift |
| `scripts/sync_remote_db.py` | Sync remote Cloudflare DB with local config |

### Quick Reference: Environment Variables

| Variable | Purpose |
|----------|---------|
| `GITHUB_TOKEN` | GitHub API auth (for discovery + health checks) |
| `ARBBUILDER_ADMIN_SECRET` | Admin API auth for remote sync |
| `ARBBUILDER_API_URL` | Remote API URL (default: https://arbuilder.app) |

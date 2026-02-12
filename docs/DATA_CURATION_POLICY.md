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
- Prefer `stylus-sdk >= 0.9.0` (main version)
- Must be actively maintained (commits within 6 months)
- Must be deployable and functional

**Exclusion criteria:**
- Meta-lists (e.g., awesome-stylus) - contain mixed quality/versions
- Unverified community submissions
- Deprecated SDK versions
- Non-Arbitrum code (e.g., general Rust libs, UI frameworks)

### 3. Version Requirements

| Component | Main Version | Minimum Version |
|-----------|--------------|-----------------|
| stylus-sdk | 0.9.2 | 0.8.0 |
| alloy-primitives | =0.8.20 | 0.8.0 |
| alloy-sol-types | =0.8.20 | 0.8.0 |
| Rust | 1.81 | 1.81 |

**Note:** Anything below stylus-sdk 0.8.0 is deprecated (uses `#[external]` instead of `#[public]`).

## Current Verified Sources

### M1: Stylus Development

**Official Sources:**
| Source | Type | SDK Version | Status | Notes |
|--------|------|-------------|--------|-------|
| docs.arbitrum.io/stylus/* | Docs | N/A | Verified | Official docs |
| OffchainLabs/stylus-hello-world | Code | 0.9.0 | Verified | Official example |
| OffchainLabs/stylus-quickstart-vending-machine | Code | 0.8.4 | Verified | Official example |
| ArbitrumFoundation/stylus-workshop-gol | Code | 0.9.0 | Verified | Workshop material |

**Production Libraries:**
| Source | Type | SDK Version | Status | Notes |
|--------|------|-------------|--------|-------|
| OpenZeppelin/rust-contracts-stylus | Code | 0.9.0 | Verified | Production library |
| OpenZeppelin/stylus-test-helpers | Code | 0.9.0 | Verified | Motsu testing framework |
| stylus-developers-guild/reentrancy-transient-storage | Code | 0.9.0 | Verified | Security patterns |
| oak-security/stylusport | Code | 0.9.0 | Verified | Solana-to-Stylus porting |
| gnosisguild/stylus-provider | Code | 0.8.4 | Verified | Infrastructure tooling |

**Community Projects (Verified 2025-01-25):**
| Source | Type | SDK Version | Status | Notes |
|--------|------|-------------|--------|-------|
| philogicae/ethbuc2025-gyges | Code | 0.8.4 | Verified | Hackathon project |
| Oluwatobilobaoke/erc6909-with-arbitrum-stylus | Code | 0.9.0 | Verified | ERC6909 implementation |
| hummusonrails/fortune-generator | Code | 0.8.0 | Verified | Randomness example |
| IndexMaker/vaultworks | Code | 0.9.0 | Verified | DeFi vault contracts |
| Inteli-Club5/EdCation | Code | 0.8.0 | Verified | Education platform |

**Scaffold-Stylus Projects (All SDK 0.9.0):**
- Arb-Stylus/scaffold-stylus (main template)
- iyansr/cross-protocol-defi-tracker
- Einarmig/WalletNaming-scaffold-stylus
- mavix21/poap-scaffold-stylus
- dchagast/scaffold-stylus-staking
- cidkagenow/EmersonApp-scaffold-stylus
- autodidacttrade/DeFi-Project-ERC20-scaffold-stylus
- ByteToHex/VRF-scaffold-stylus

**Challenge Submissions (All SDK 0.9.0):**
- Huygon764/challenge-001, Fnz11/challenge-001
- ndrewlex/challenge-001, athallarizky/challenge-001, dimasd-angga/challenge-001
- ammar-rasyidi/challenge-001, rizkianakbar/challenge-001
- math-marcellino/challenge-002, lucky-ivanius/challenge-001, lucky-ivanius/challenge-002

### M2: Arbitrum SDK

| Source | Type | Status | Notes |
|--------|------|--------|-------|
| docs.arbitrum.io/sdk | Docs | Verified | Official docs |
| docs.arbitrum.io/build-decentralized-apps/* | Docs | Verified | Bridging/messaging docs |
| OffchainLabs/arbitrum-sdk | Code | Verified | Official SDK |
| OffchainLabs/arbitrum-tutorials | Code | Verified | Working examples |

## Removed Sources (and why)

### Deprecated SDK Versions (< 0.8.0)
- `OffchainLabs/stylus-chess` - SDK v0.4.2 (deprecated)
- `OffchainLabs/stylus-by-example` - SDK v0.6.0 (deprecated)
- `fluidity-money/9lives.so` - SDK v0.7.0 (deprecated)
- `fluidity-money/long.so` - SDK v0.7.0 (deprecated)
- `hammertoe/ArbitrumOnchainAgent` - SDK v0.7.0 (deprecated)
- `cygaar/inkmate` - SDK v0.4.3 (deprecated)
- `malik672/open-stylus` - SDK v0.4.2 (deprecated)
- `code-423n4/2024-10-superposition` - SDK v0.6.0 (deprecated)

### Deleted Repos
- `dante4rt/challenge-001` - Repository deleted by owner (404)

### Meta-lists
- `OffchainLabs/awesome-stylus` - Contains mixed versions, outdated projects

### Previously Unverified (Now Verified and Included)
- Challenge submissions - VERIFIED 2025-01-25 (all SDK 0.9.0, now included)
- Scaffold-stylus forks - VERIFIED 2025-01-25 (all SDK 0.9.0, now included)

### Still Excluded (Failed Verification)
- yahgwai/rkfall-nft - SDK v0.4.1 (deprecated)
- gvladika/stylus-erc721 - SDK v0.4.1 (deprecated)
- scarfish-dapps/integrum-swap - SDK v0.5.2 (deprecated)
- OffchainLabs/stylus-tutorials - SDK v0.5.0 (deprecated)
- LimeChain/stylus-toolkit - SDK v0.5.0 (deprecated)

### Irrelevant Code
- `nestjs/nest` - Node.js framework, not Arbitrum
- `saadeghi/daisyui` - CSS framework
- `rainbow-me/rainbowkit` - Wallet UI kit
- `smartcontractkit/chainlink` - Chainlink, not Arbitrum-specific
- `messari/subgraphs` - Analytics, not SDK examples

## Maintenance Runbook

### Scenario 1: Adding New Sources

When you find a new repo or doc page to add:

**For a code repository:**

```bash
# 1. Verify the repo first
git clone <repo-url> /tmp/verify-repo
cd /tmp/verify-repo
cat Cargo.toml | grep stylus-sdk   # Must be >= 0.8.0
cargo stylus check                  # Optional: verify it compiles

# 2. Add to scraper/config.py under the right section
#    - DOCS dict → for documentation pages
#    - PROJECT_EXAMPLES dict → for code repos
#    Each repo entry needs: url, sdk_version, verified (date)
```

Example entry in `PROJECT_EXAMPLES`:
```python
{"url": "https://github.com/org/repo", "sdk_version": "0.9.0", "verified": "2026-02-09"},
```

**For a documentation page:**

Add the URL to the appropriate category in the `DOCS` dict in `scraper/config.py`.

**Then run the pipeline:**

```bash
# Local pipeline
python -m scraper.run --skip-web         # Clone new repos (add --force-reclone if updating)
python -m src.preprocessing.processor    # Re-process all chunks
python -m src.embeddings.vectordb --reset  # Reset local ChromaDB and re-ingest

# Remote (production Cloudflare)
python scripts/sync_remote_db.py --dry-run    # Preview changes
python scripts/sync_remote_db.py --reingest   # Trigger batch re-ingestion of all sources
```

**Finally:** Update the source tables in this doc and commit.

---

### Scenario 2: Removing Unmaintained Sources

When a repo is archived, deleted, or no longer compiles:

```bash
# 1. Run audit to see current state
python scripts/audit_data.py

# 2. Remove the entry from scraper/config.py
#    - Delete from DOCS or PROJECT_EXAMPLES

# 3. Prune orphan repo directories from disk
python scripts/audit_data.py --prune --confirm

# 4. Re-run the local pipeline
python -m src.preprocessing.processor
python -m src.embeddings.vectordb --reset

# 5. Sync remote — removes stale sources from production
python scripts/sync_remote_db.py --dry-run       # Preview: shows stale sources to delete
python scripts/sync_remote_db.py --delete-stale   # Delete stale from KV registry
python scripts/sync_remote_db.py --reingest       # Re-ingest clean sources
```

If there are many stale vectors in Vectorize that won't clear (CPU timeout), recreate the index:

```bash
cd apps/web
npx wrangler vectorize delete arbbuilder
npx wrangler vectorize create arbbuilder --dimensions 1024 --metric cosine
cd ../..
python scripts/sync_remote_db.py --reingest   # Re-populate fresh index
```

**Finally:** Move the removed source to the "Removed Sources" section in this doc with the reason.

---

### Scenario 3: New Stylus SDK Version Released (e.g., 0.10.0)

When a new `stylus-sdk` version is published on crates.io:

```bash
# 1. Update shared/stylus-versions.json
#    - Add the new version entry with breaking changes, migration notes
#    - Update main_version if this is the new recommended version
#    - Update deprecated_below if older versions are no longer supported

# 2. Update scraper/config.py version constants
#    - MAIN_STYLUS_SDK_VERSION = "0.10.0"  (if it's the new recommended)
#    - MIN_STYLUS_SDK_VERSION = "0.9.0"    (if raising the minimum)

# 3. Verify existing repos compile with the new SDK
#    For each repo in PROJECT_EXAMPLES:
git clone <repo-url> /tmp/verify
cd /tmp/verify
# Update Cargo.toml to new SDK version
cargo stylus check

# 4. Update sdk_version in config entries for repos that upgraded
#    Remove repos that no longer compile and won't be updated

# 5. Re-run the full pipeline
python -m scraper.run                        # Re-scrape all (repos + web)
python -m src.preprocessing.processor        # Re-process with new version metadata
python -m src.embeddings.vectordb --reset    # Reset and re-ingest locally

# 6. Sync remote
python scripts/sync_remote_db.py --dry-run
python scripts/sync_remote_db.py --reingest
```

**Also update:**
- Version table in this doc (section 3)
- `CLAUDE.md` Stylus dependencies section
- Any MCP tool prompts that reference specific SDK versions

---

### Quick Reference: Key Files

| File | Purpose |
|------|---------|
| `scraper/config.py` | Source of truth for all data sources |
| `shared/stylus-versions.json` | SDK version metadata and compatibility |
| `scripts/audit_data.py` | Detect orphans and config drift |
| `scripts/sync_remote_db.py` | Sync remote Cloudflare DB with local config |
| `docs/DATA_CURATION_POLICY.md` | This doc — curation rules and source registry |

### Quick Reference: Environment Variables

| Variable | Purpose |
|----------|---------|
| `ARBBUILDER_ADMIN_SECRET` | Admin API auth for remote sync |
| `ARBBUILDER_API_URL` | Remote API URL (default: https://arbbuilder.whymelabs.com) |

---

## TODO

- [ ] Create SDK bridging examples (none exist as standalone projects)
- [ ] Set up CI to verify sources on SDK releases
- [ ] Re-evaluate removed community projects after manual verification
- [ ] Automate SDK release monitoring (crates.io watch)

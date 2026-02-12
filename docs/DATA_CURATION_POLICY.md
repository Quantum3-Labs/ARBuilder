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

**Exclusion criteria:**
- Meta-lists (e.g., awesome-stylus) - contain mixed quality/versions
- Unverified community submissions
- Deprecated SDK versions
- Non-Arbitrum code (e.g., general Rust libs, UI frameworks)

### 3. Version Requirements

| Component | Main Version | Minimum Version |
|-----------|--------------|-----------------|
| stylus-sdk | 0.10.0 | 0.8.0 |
| alloy-primitives | 1.0.1 | 0.8.0 |
| alloy-sol-types | 1.0.1 | 0.8.0 |
| Rust | 1.88.0 | 1.81 |

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
- dante4rt/challenge-001, Huygon764/challenge-001, Fnz11/challenge-001
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

## Maintenance Process

### When SDK Updates (e.g., 0.10.0 release)

1. **Verify official examples** still compile
2. **Check OpenZeppelin** for updates
3. **Update version requirements** in this doc
4. **Re-scrape** verified sources only
5. **Update system prompts** with new version info

### Adding New Sources

1. Clone the repository
2. Check `Cargo.toml` for SDK version
3. Run `cargo stylus check` to verify compilation
4. If passes, add to `scraper/config.py` under appropriate section
5. Document in this file

## TODO

- [ ] Fork and maintain our own reference implementations
- [ ] Create SDK bridging examples (none exist as standalone projects)
- [ ] Set up CI to verify sources on SDK releases
- [ ] Re-evaluate removed community projects after manual verification

# ARBuilder

AI-powered development assistant for the Arbitrum ecosystem. ARBuilder transforms natural language prompts into:

- **Stylus smart contracts** (Rust)
- **Cross-chain SDK implementations** (asset bridging and messaging)
- **Full-stack dApps** (contracts + backend + indexer + oracle + frontend + wallet integration)
- **Orbit chain deployment assistance**

## Architecture

ARBuilder uses a **Retrieval-Augmented Generation (RAG)** pipeline with hybrid search (vector + BM25 + cross-encoder reranking) to provide context-aware code generation. Available as a hosted service at [arbuilder.app](https://arbuilder.app) or self-hosted via MCP server.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            ARBuilder                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  DATA PIPELINE                                                          │
│  ┌──────────┐    ┌──────────┐    ┌───────────┐    ┌──────────────────┐ │
│  │ Scraper  │───▶│Processor │───▶│ Embedder  │───▶│    ChromaDB      │ │
│  │ crawl4ai │    │ 3-layer  │    │ BGE-M3    │    │ (local vectors)  │ │
│  │ + GitHub │    │ filters  │    │ 1024-dim  │    │                  │ │
│  └──────────┘    └──────────┘    └───────────┘    └────────┬─────────┘ │
│                                                             │           │
│  RETRIEVAL                                                  │           │
│  ┌──────────────────────────────────────────────────────────▼─────────┐ │
│  │                    Hybrid Search Engine                             │ │
│  │  ┌──────────┐    ┌──────────┐    ┌───────────┐                    │ │
│  │  │  Vector  │    │   BM25   │    │CrossEncoder│   RRF Fusion      │ │
│  │  │  Search  │───▶│ Keywords │───▶│ Reranker  │──▶ + MMR           │ │
│  │  └──────────┘    └──────────┘    └───────────┘                    │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                         │                               │
│  GENERATION                             ▼                               │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      MCP Server (19 tools)                        │  │
│  │                                                                   │  │
│  │  M1: Stylus        M2: SDK           M3: dApp Builder            │  │
│  │  ┌─────────────┐   ┌─────────────┐   ┌──────────────────────┐   │  │
│  │  │ generate_    │   │ generate_   │   │ generate_backend     │   │  │
│  │  │ stylus_code  │   │ bridge_code │   │ generate_frontend    │   │  │
│  │  │ ask_stylus   │   │ generate_   │   │ generate_indexer     │   │  │
│  │  │ get_context  │   │ messaging   │   │ generate_oracle      │   │  │
│  │  │ gen_tests    │   │ ask_bridging│   │ orchestrate_dapp     │   │  │
│  │  │ get_workflow │   │             │   │                      │   │  │
│  │  │ validate_code│   │             │   │                      │   │  │
│  │  └─────────────┘   └─────────────┘   └──────────────────────┘   │  │
│  │                                                                   │  │
│  │  M4: Orbit Chain                                                  │  │
│  │  ┌──────────────────────┐                                        │  │
│  │  │ generate_orbit_config│                                        │  │
│  │  │ generate_orbit_deploy│                                        │  │
│  │  │ gen_validator_setup  │                                        │  │
│  │  │ ask_orbit            │                                        │  │
│  │  │ orchestrate_orbit    │                                        │  │
│  │  └──────────────────────┘                                        │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                           │                                             │
│  IDE INTEGRATION          ▼                                             │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Cursor / VS Code / Claude Desktop / Any MCP Client              │  │
│  │  <- via local stdio or remote mcp-remote proxy ->                │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  HOSTED SERVICE (Cloudflare Workers)                                    │
│  ┌──────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Workers AI  │  │ Vectorize│  │    D1    │  │      KV         │  │
│  │  BGE-M3 +    │  │ 1024-dim │  │  Users   │  │   Source registry│  │
│  │  Reranker    │  │  index   │  │  API keys│  │   + Ingest state │  │
│  └──────────────┘  └──────────┘  └──────────┘  └──────────────────┘  │
│                                                                       │
│  INGESTION PIPELINE (Worker-native, cron every 6h)                    │
│  ┌──────────┐    ┌──────────┐    ┌───────────┐    ┌──────────────┐  │
│  │ scraper  │───▶│ chunker  │───▶│ Workers AI│───▶│  Vectorize   │  │
│  │ HTML/    │    │ doc+code │    │  BGE-M3   │    │   upsert     │  │
│  │ GitHub   │    │ splitter │    │ embedding │    │              │  │
│  └──────────┘    └──────────┘    └───────────┘    └──────────────┘  │
│                       │                ▲                             │
│                       │ >30 files      │ embed messages              │
│                       ▼                │                             │
│              ┌─────────────────────────┴──┐                         │
│              │    CF Queue (async path)    │                         │
│              │  embed │ continue │finalize │                         │
│              └────────────────────────────┘                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## TL;DR - Quick Start

**Option 1: Hosted Service (Easiest)**
```bash
# No local setup needed - just configure your IDE
# Add to ~/.cursor/mcp.json:
{
  "mcpServers": {
    "arbbuilder": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://arbuilder.app/mcp",
               "--header", "Authorization: Bearer YOUR_API_KEY"]
    }
  }
}
```
Get your API key at [arbuilder.app](https://arbuilder.app)

**Option 2: Self-Hosted**
```bash
# 1. Clone and setup
git clone https://github.com/Quantum3-Labs/ARBuilder.git
cd ARBuilder
conda env create -f environment.yml
conda activate arbbuilder

# 2. Configure API key
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY and NVIDIA_API_KEY

# 3. Generate vector database (required)
python -m src.embeddings.vectordb

# 4. Test MCP server
python -m src.mcp.server
# Should show: "Capabilities: 19 tools, 11 resources, 5 prompts"

# 5. Configure Cursor IDE (~/.cursor/mcp.json) - see Setup section below
```

## Tutorial Video

Watch the tutorial to see ARBuilder in action:

[Tutorial Video](https://drive.google.com/file/d/1gLfXvwNyYeVfLY2g6WQySDyOcNDxmOP2/view?usp=share_link)

## Project Structure

```
ArbBuilder/
├── sources.json          # Single source of truth for all data sources
├── scraper/              # Data collection module
│   ├── config.py         # Thin wrapper around sources.json (backward-compat helpers)
│   ├── scraper.py        # Web scraping with crawl4ai
│   ├── github_scraper.py # GitHub repository cloning
│   └── run.py            # Pipeline entry point
├── src/
│   ├── preprocessing/    # Text cleaning and chunking
│   │   ├── cleaner.py    # Text normalization
│   │   ├── chunker.py    # Document chunking with token limits
│   │   └── processor.py  # Main preprocessing pipeline
│   ├── embeddings/       # Embedding and vector storage
│   │   ├── embedder.py   # OpenRouter embedding client
│   │   ├── vectordb.py   # ChromaDB wrapper with hybrid search (BM25 + vector)
│   │   └── reranker.py   # CrossEncoder, MMR, LLM reranking
│   ├── templates/        # Code generation templates
│   │   ├── stylus_templates.py   # M1: Stylus contract templates
│   │   ├── backend_templates.py  # M3: NestJS/Express templates
│   │   ├── frontend_templates.py # M3: Next.js + wagmi templates
│   │   ├── indexer_templates.py  # M3: Subgraph templates
│   │   ├── oracle_templates.py   # M3: Chainlink templates
│   │   └── orbit_templates.py    # M4: Orbit chain deployment templates
│   ├── utils/            # Shared utilities
│   │   ├── version_manager.py   # SDK version management
│   │   ├── env_config.py        # Centralized env var configuration
│   │   ├── abi_extractor.py     # Stylus ABI extraction from Rust code
│   │   └── compiler_verifier.py # Docker-based cargo check verification
│   ├── mcp/              # MCP server for IDE integration
│   │   ├── server.py     # MCP server (tools, resources, prompts)
│   │   ├── tools/        # MCP tool implementations (19 tools)
│   │   │   ├── get_stylus_context.py       # M1
│   │   │   ├── generate_stylus_code.py     # M1
│   │   │   ├── ask_stylus.py               # M1
│   │   │   ├── generate_tests.py           # M1
│   │   │   ├── get_workflow.py             # M1
│   │   │   ├── validate_stylus_code.py     # M1
│   │   │   ├── generate_bridge_code.py     # M2
│   │   │   ├── generate_messaging_code.py  # M2
│   │   │   ├── ask_bridging.py             # M2
│   │   │   ├── generate_backend.py         # M3
│   │   │   ├── generate_frontend.py        # M3
│   │   │   ├── generate_indexer.py         # M3
│   │   │   ├── generate_oracle.py          # M3
│   │   │   ├── orchestrate_dapp.py         # M3
│   │   │   ├── generate_orbit_config.py    # M4
│   │   │   ├── generate_orbit_deployment.py # M4
│   │   │   ├── generate_validator_setup.py # M4
│   │   │   ├── ask_orbit.py                # M4
│   │   │   └── orchestrate_orbit.py        # M4
│   │   ├── resources/    # Static knowledge (11 resources)
│   │   │   ├── stylus_cli.py      # M1
│   │   │   ├── workflows.py       # M1
│   │   │   ├── networks.py        # M1
│   │   │   ├── coding_rules.py    # M1
│   │   │   ├── sdk_rules.py       # M2
│   │   │   ├── backend_rules.py   # M3
│   │   │   ├── frontend_rules.py  # M3
│   │   │   ├── indexer_rules.py   # M3
│   │   │   └── oracle_rules.py    # M3
│   │   └── prompts/      # Workflow templates
│   └── rag/              # RAG pipeline (TBD)
├── tests/
│   ├── mcp_tools/        # MCP tool test cases and benchmarks
│   │   ├── test_get_stylus_context.py
│   │   ├── test_generate_stylus_code.py
│   │   ├── test_ask_stylus.py
│   │   ├── test_generate_tests.py
│   │   ├── test_m2_e2e.py    # M2 end-to-end tests
│   │   ├── test_m3_tools.py  # M3 full dApp tests
│   │   └── benchmark.py      # Evaluation framework
│   └── test_retrieval.py # Retrieval quality tests
├── docs/
│   └── mcp_tools_spec.md # MCP tools specification
├── apps/web/               # Hosted service (Cloudflare Workers + Next.js)
│   ├── src/lib/
│   │   ├── scraper.ts      # Web doc scraping (HTMLRewriter)
│   │   ├── github.ts       # GitHub repo scraping (Trees/Contents API)
│   │   ├── chunker.ts      # Document + code chunking
│   │   ├── ingestPipeline.ts # Ingestion orchestrator (sync + async queue paths)
│   │   └── vectorize.ts    # Search + embedding utilities
│   ├── src/app/api/admin/  # Admin APIs (sources, ingest, migrate)
│   ├── worker.ts           # Worker entry + cron + queue consumer handler
│   └── wrangler.prod.jsonc # Production config (D1, KV, Vectorize, Queue)
├── scripts/
│   ├── run_benchmarks.py     # Benchmark runner
│   ├── diff-migrate.ts       # Push chunks to CF Vectorize
│   ├── sync_sources.ts       # Sync sources.json to CF KV registry
│   └── ingest_m3_sources.py  # M3 source ingestion
├── data/
│   ├── raw/              # Raw scraped data (docs + curated repos)
│   ├── processed/        # Pre-processed chunks
│   └── chroma_db/        # ChromaDB vector store (generated locally, not in repo)
├── environment.yml       # Conda environment specification
├── pyproject.toml        # Project metadata and dependencies
└── .env                  # Environment variables (not committed)
```

## Setup

### 1. Create Conda Environment

```bash
# Create and activate the environment
conda env create -f environment.yml
conda activate arbbuilder
```

> **Note:** If you plan to refresh the knowledge base by scraping (optional), also install playwright:
> ```bash
> playwright install chromium
> ```

### 2. Configure Environment Variables

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
OPENROUTER_API_KEY=your-api-key
NVIDIA_API_KEY=your-nvidia-api-key
DEFAULT_MODEL=deepseek/deepseek-v3.2
DEFAULT_EMBEDDING=baai/bge-m3
DEFAULT_CROSS_ENCODER=nvidia/llama-3.2-nv-rerankqa-1b-v2
```

### 3. Setup Data

The repository includes all data needed:
- **Raw data** (`data/raw/`): Documentation pages + curated GitHub repos
- **Processed chunks** (`data/processed/`): Chunks ready for embedding

**Important:** The ChromaDB vector database must be generated locally (it's not included in the repo due to binary compatibility issues across systems).

```bash
# Generate the vector database (required before using MCP tools)
python -m src.embeddings.vectordb
```

### 4. Verify MCP Server

Test that the MCP server starts correctly:

```bash
# Run the MCP server directly (press Ctrl+C to exit)
python -m src.mcp.server
```

You should see:
```
ARBuilder MCP Server started
Capabilities: 19 tools, 11 resources, 5 prompts
```

#### Optional: Refresh Data

If you want to re-scrape the latest documentation and code:

```bash
# Run full pipeline (web scraping + GitHub cloning)
python -m scraper.run

# Then preprocess the raw data
python -m src.preprocessing.processor

# And re-ingest into ChromaDB
python -m src.embeddings.vectordb --reset
```

**Data Quality Filters:** The pipeline applies a 3-layer filtering system to remove junk data (vendored crates, auto-generated TypeChain files, hex bytecode, lock files, and cross-repo duplicates). See [docs/DATA_CURATION_POLICY.md](docs/DATA_CURATION_POLICY.md) for details.

#### Data Maintenance

Audit and clean up data sources:

```bash
# Audit: compare repos on disk vs config
python scripts/audit_data.py

# Show what orphan repos would be deleted
python scripts/audit_data.py --prune

# Actually delete orphan repos
python scripts/audit_data.py --prune --confirm

# Include ChromaDB stats in audit
python scripts/audit_data.py --chromadb

# GitHub scraper also supports audit/prune
python -m scraper.github_scraper --audit
python -m scraper.github_scraper --prune --dry-run
```

#### Fork & Migrate (SDK 0.10.0)

Fork community Stylus repos and migrate them to SDK 0.10.0:

```bash
# Dry run: show what would change without modifying anything
python scripts/fork_and_migrate.py --all --dry-run

# Migrate all 13 Stylus repos
python scripts/fork_and_migrate.py --all

# Migrate a specific repo
python scripts/fork_and_migrate.py --repo OffchainLabs/stylus-hello-world

# Re-verify already-forked repos after manual fixes
python scripts/fork_and_migrate.py --all --verify-only
```

Reports are saved to `reports/fork_migration_*.json`.

## Quick Start (IDE Integration)

### Option A: Self-Hosted (Full Control)

Run ARBuilder locally with your own API keys. No rate limits.

**Step 1: Configure your IDE**

Add the following to your MCP configuration file:

**Cursor** (`~/.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "arbbuilder": {
      "command": "/path/to/miniconda3/envs/arbbuilder/bin/python3",
      "args": ["-m", "src.mcp.server"],
      "env": {
        "OPENROUTER_API_KEY": "your-api-key",
        "PYTHONPATH":"/path/to/ArbBuilder"
      }
    }
  }
}
```

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):
```json
{
  "mcpServers": {
    "arbbuilder": {
      "command": "python",
      "args": ["-m", "src.mcp.server"],
      "cwd": "/path/to/ArbBuilder",
      "env": {
        "OPENROUTER_API_KEY": "your-api-key"
      }
    }
  }
}
```

**Step 2: Restart your IDE**

After saving the configuration, restart Cursor or Claude Desktop. The ARBuilder tools will be available to the AI assistant.

**Step 3: Start building!**

Ask your AI assistant:
- "Generate an ERC20 token contract in Stylus"
- "How do I deploy a contract to Arbitrum Sepolia?"
- "Write tests for my counter contract"

### Option B: Hosted Service (Zero Setup)

Use our hosted API - no local setup required. Available at [arbuilder.app](https://arbuilder.app).

1. Sign up at https://arbuilder.app and get your API key
2. Add to your MCP configuration:

```json
{
  "mcpServers": {
    "arbbuilder": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://arbuilder.app/mcp",
               "--header", "Authorization: Bearer YOUR_API_KEY"]
    }
  }
}
```

The hosted service includes:
- 100 API calls/day (free tier)
- No local setup or Python environment required
- Always up-to-date with latest Stylus SDK patterns

## Usage

### Data Ingestion

**Hosted (Worker-native)**: The hosted service at [arbuilder.app](https://arbuilder.app) has a built-in ingestion pipeline that runs automatically via cron (every 6 hours). Sources can also be manually ingested via the admin UI at `/admin`.

The pipeline uses two paths based on source size:
- **Sync path** (docs and repos ≤30 files): scrape → chunk → embed → upsert in a single Worker invocation (~40 subrequests)
- **Async path** (repos >30 files): scrape → chunk → save to KV → enqueue to CF Queue. The queue consumer processes embed/upsert in batches of 10 chunks (~4 subrequests each), with `continue` messages for additional file batches and a `finalize` message to update source status. This stays within the 50 subrequest/invocation limit on the Free plan.

**Local (Python pipeline)**: For self-hosted setups, run the full data collection pipeline:

```bash
conda activate arbbuilder

# Run full pipeline (web scraping + GitHub cloning)
python -m scraper.run

# Preprocess and push to CF Vectorize
python -m src.preprocessing.processor
AUTH_SECRET=xxx npx tsx scripts/diff-migrate.ts --full
```

### Data Sources

All data sources are defined in `sources.json` — the single source of truth for both the local Python pipeline and the hosted CF Worker ingestion. The file contains 84 curated sources (53 documentation pages + 31 GitHub repos) across 4 milestones.

Versioned repos (with multiple SDK branches) use a `versions` array:
```json
{
  "url": "https://github.com/ARBuilder-Forks/stylus-hello-world",
  "versions": [
    { "sdkVersion": "0.10.0", "branch": "main" },
    { "sdkVersion": "0.9.0", "branch": "v0.9.0" }
  ]
}
```

**Sync to hosted service:**
```bash
ARBBUILDER_ADMIN_SECRET=xxx npx tsx scripts/sync_sources.ts
ARBBUILDER_ADMIN_SECRET=xxx npx tsx scripts/sync_sources.ts --dry-run
ARBBUILDER_ADMIN_SECRET=xxx npx tsx scripts/sync_sources.ts --remove-stale
```

**Stylus (M1)** — 17 docs + 19 repos
- Official documentation: [docs.arbitrum.io](https://docs.arbitrum.io/stylus/stylus-overview) (7 pages + gas-metering)
- **All Stylus repos sourced from [ARBuilder-Forks](https://github.com/ARBuilder-Forks)** for resilience against upstream deletions
- 6 forks with SDK 0.10.0 branches: hello-world, vending-machine, erc6909, fortune-generator, ethbuc2025-gyges, WalletNaming
- 7 forks at original SDK version (0.8.4–0.9.0) with separate branch per version
- Production codebases: OpenZeppelin rust-contracts-stylus, stylus-test-helpers, stylusport, stylus-provider

**Curation Policy:**
- No meta-lists (awesome-stylus) — causes outdated code ingestion
- No unverified community submissions
- All code repos must compile with stylus-sdk >= 0.8.0
- SDK version tracked per-repo in `sources.json`
- All Stylus repos forked to ARBuilder-Forks org with `forkedFrom` provenance tracking

**Stylus SDK Version Support:**

| Version | Status | Notes |
|---------|--------|-------|
| 0.10.0 | **Main** (default) | Latest stable, recommended for new projects |
| 0.9.x | Supported | Separate branches in forked repos |
| 0.8.x | Supported | Minimum supported version |
| < 0.8.0 | Deprecated | Excluded from knowledge base |

**Multi-Version Strategy:**
- **Branch-per-version**: Forked repos maintain separate Git branches per SDK version (e.g., `main` for 0.10.0, `v0.9.0` for original)
- **Branch-aware scraping**: CF Worker ingests each branch as a separate source entry
- **Version-aware generation**: `generate_stylus_code` and `ask_stylus` accept `target_version` to produce code for any supported SDK version
- **Version-aware retrieval**: Vector search boosts chunks matching the requested SDK version

**Arbitrum SDK (M2)** — 6 docs + 5 repos
- [arbitrum-sdk](https://github.com/OffchainLabs/arbitrum-sdk), [arbitrum-tutorials](https://github.com/OffchainLabs/arbitrum-tutorials)
- 3 community repos: arbitrum-api, orbit-bridging, cross-messaging
- Official bridging and messaging documentation (6 pages)

**Full dApp Builder (M3)** — 30 docs + 11 repos
- Backend: NestJS (5 docs), Express (3 docs), nestjs/nest, arbitrum-token-bridge
- Frontend: wagmi (5 docs), viem (4 docs), RainbowKit (4 docs), DaisyUI (5 docs) + 5 repos
- Indexer: The Graph (5 docs), graph-tooling, messari/subgraphs
- Oracle: Chainlink (4 docs), smart-contract-examples, chainlink

**Orbit SDK (M4)** — 5 Python MCP tools + 9 TypeScript templates
- Tools: `generate_orbit_config`, `generate_orbit_deployment`, `generate_validator_setup`, `ask_orbit`, `orchestrate_orbit`
- Templates: Chain Config, Deploy Rollup, Deploy Token Bridge, Custom Gas Token, Validator Management, Governance, Node Config, AnyTrust Config, Orchestration
- Uses `@arbitrum/chain-sdk` ^0.25.0 + `viem` ^1.20.0 for `prepareChainConfig()`, `createRollup()`, `createTokenBridge()`, `prepareNodeConfig()`
- Deployment output persisted to `deployment.json` — downstream scripts (token bridge, node config) chain automatically
- Crash-proof deployment: saves `deployment.json` BEFORE receipt fetch, with try/catch for block number
- Custom gas tokens: generates `approve-token.ts` with correct RollupCreator addresses, ERC-20 deploy guidance
- Docker: `offchainlabs/nitro-node:v3.9.4-7f582c3`, bind mounts (`./data/arbitrum`), no `user: root`
- Node config post-processing: restores masked private keys, disables staker for single-key setups, fixes DAS URL double-port
- Wasm root check: `--validation.wasm.allowed-wasm-module-roots` prevents crash-loops on startup
- AnyTrust: BLS keygen via `datool keygen` from nitro-node image
- Supports: Rollup and AnyTrust chains, custom gas tokens, validator/batch poster management, full project scaffolding

## API Access

### Public MCP Endpoint (Free)

The MCP endpoint at `/mcp` is free to use and designed for IDE integration:

```
https://arbuilder.app/mcp
```

- Requires `arb_` API key from dashboard
- Usage tracked per API key
- Rate limited per free tier (100 calls/day)

### Transparency Page

View all ingested sources and code templates at [arbuilder.app/transparency](https://arbuilder.app/transparency).

This public page provides:
- **Ingested Sources**: All documentation and GitHub repos in the knowledge base
- **Code Templates**: Verified Stylus templates with full source code
- **Statistics**: Chunk counts, SDK versions, and category breakdowns

Public API endpoints (no authentication required):
- `GET /api/public/sources` - List all active sources
- `GET /api/public/templates` - List all code templates
- `GET /api/public/templates?code=true` - Templates with full source code

### Internal Direct API (Testing Only)

Direct API routes at `/api/v1/tools/*` are for **internal testing only**:

- Requires `AUTH_SECRET` in Authorization header
- Not for public use
- Used by CI/CD and internal validation scripts

## MCP Capabilities

ARBuilder exposes a full MCP server with **19 tools**, **11 resources**, and **5 prompts** for Cursor/VS Code integration.

### Tools

**M1: Stylus Development (6 tools)**

| Tool | Description |
|------|-------------|
| `get_stylus_context` | RAG retrieval for docs and code examples |
| `generate_stylus_code` | Generate Stylus contracts from prompts |
| `ask_stylus` | Q&A, debugging, concept explanations |
| `generate_tests` | Generate unit/integration/fuzz tests |
| `get_workflow` | Build/deploy/test workflow guidance |
| `validate_stylus_code` | Compile-check code via Docker cargo check with Stylus-specific fix guidance |

**M2: Arbitrum SDK - Bridging & Messaging (3 tools)**

| Tool | Description |
|------|-------------|
| `generate_bridge_code` | Generate ETH/ERC20 bridging code (L1<->L2, L1->L3, L3->L2) |
| `generate_messaging_code` | Generate cross-chain messaging code (L1<->L2, L2<->L3) |
| `ask_bridging` | Q&A about bridging patterns and SDK usage |

**M3: Full dApp Builder (5 tools)**

| Tool | Description |
|------|-------------|
| `generate_backend` | Generate NestJS/Express backends with Web3 integration |
| `generate_frontend` | Generate Next.js + wagmi + RainbowKit frontends |
| `generate_indexer` | Generate The Graph subgraphs for indexing |
| `generate_oracle` | Generate Chainlink oracle integrations |
| `orchestrate_dapp` | Scaffold complete dApps with multiple components |

**M4: Orbit Chain Integration (5 tools)**

| Tool | Description |
|------|-------------|
| `generate_orbit_config` | Generate Orbit chain configuration (prepareChainConfig, AnyTrust, custom gas tokens) |
| `generate_orbit_deployment` | Generate rollup and token bridge deployment scripts (createRollup, createTokenBridge) |
| `generate_validator_setup` | Manage validators, batch posters, and AnyTrust DAC keysets |
| `ask_orbit` | Q&A about Orbit chain deployment, configuration, and operations |
| `orchestrate_orbit` | Scaffold complete Orbit chain deployment projects with all scripts |

#### Example: Get Build/Deploy Workflow

```json
{
  "workflow_type": "deploy",
  "network": "arbitrum_sepolia",
  "include_troubleshooting": true
}
```

Returns step-by-step commands:
```bash
# Check balance
cast balance YOUR_ADDRESS --rpc-url https://sepolia-rollup.arbitrum.io/rpc

# Deploy contract
cargo stylus deploy --private-key-path=./key.txt --endpoint=https://sepolia-rollup.arbitrum.io/rpc
```

### Resources (Knowledge Injection)

MCP Resources provide static knowledge that AI IDEs can load automatically:

**M1: Stylus Resources**

| Resource URI | Description |
|--------------|-------------|
| `stylus://cli/commands` | Complete cargo-stylus CLI reference |
| `stylus://workflows/build` | Step-by-step build workflow |
| `stylus://workflows/deploy` | Deployment workflow with network configs |
| `stylus://workflows/test` | Testing workflow (unit, integration, fuzz) |
| `stylus://config/networks` | Arbitrum network configurations |
| `stylus://rules/coding` | Stylus coding guidelines and patterns |

**M2: Arbitrum SDK Resources**

| Resource URI | Description |
|--------------|-------------|
| `arbitrum://rules/sdk` | Arbitrum SDK bridging and messaging guidelines |

**M3: Full dApp Builder Resources**

| Resource URI | Description |
|--------------|-------------|
| `dapp://rules/backend` | NestJS/Express Web3 backend patterns |
| `dapp://rules/frontend` | Next.js + wagmi + RainbowKit patterns |
| `dapp://rules/indexer` | The Graph subgraph development patterns |
| `dapp://rules/oracle` | Chainlink oracle integration patterns |

### Prompts (Workflow Templates)

MCP Prompts provide reusable templates for common workflows:

| Prompt | Description | Arguments |
|--------|-------------|-----------|
| `build-contract` | Build workflow guidance | `project_path`, `release_mode` |
| `deploy-contract` | Deploy workflow guidance | `network`, `key_method` |
| `debug-error` | Error diagnosis workflow | `error_message`, `context` |
| `optimize-gas` | Gas optimization workflow | `contract_code`, `focus` |
| `generate-contract` | Contract generation workflow | `description`, `contract_type` |

### How It Works

```
User: "Deploy my contract to Arbitrum Sepolia"
    ↓
AI IDE calls get_workflow(workflow_type="deploy", network="arbitrum_sepolia")
    ↓
Returns structured commands + troubleshooting
    ↓
AI IDE presents commands to user (user executes locally)
```

The MCP server provides **knowledge about commands**, not command execution. This ensures:
- User controls what runs on their machine
- No security risks from remote execution
- AI IDE knows exact commands without hardcoding

See [docs/mcp_tools_spec.md](docs/mcp_tools_spec.md) for full specification.

## User Guide

### Generating Stylus Contracts

ARBuilder uses **template-based code generation** to ensure generated code compiles correctly. Instead of generating from scratch, it customizes verified working templates from official Stylus examples.

**Available Templates:**

| Template | Type | Description |
|----------|------|-------------|
| Counter | utility | Simple storage with getter/setter operations |
| VendingMachine | defi | Mappings with time-based rate limiting |
| SimpleERC20 | token | Basic ERC20 with transfer, approve, transferFrom |
| AccessControl | utility | Owner-only functions with ownership transfer |
| DeFiVault | defi | Cross-contract calls (sol_interface!), transfer_eth, Call::new_in(self) |
| NftRegistry | nft | Dynamic arrays (push), sol! events with camelCase, mint/transfer |

**Stylus SDK Version Support:**

| Version | Status | Notes |
|---------|--------|-------|
| 0.10.0 | **Main** (default) | Recommended for new projects |
| 0.9.x | Supported | Use `target_version: "0.9.0"` for 0.9.x output. Separate branches in forks |
| 0.8.x | Supported | Minimum supported version |
| < 0.8.0 | Deprecated | Warning shown, may not compile |

Pass `target_version` to tools for version-specific output:
```
User: "Generate a counter contract for SDK 0.9.0"
AI uses: generate_stylus_code(prompt="...", target_version="0.9.0")
Returns: Code using msg::sender(), .getter(), print_abi() patterns
```

Ask your AI assistant to generate contracts:

```
User: "Create an ERC20 token called MyToken with 1 million supply"

AI uses: generate_stylus_code tool
Returns: Complete Rust contract based on SimpleERC20 template with proper imports, storage, and methods
```

### Getting Context and Examples

Search the knowledge base for documentation and code examples:

```
User: "Show me how to implement a mapping in Stylus"

AI uses: get_stylus_context tool
Returns: Relevant documentation and code snippets from official examples
```

### Q&A and Debugging

Ask questions about Stylus development:

```
User: "Why am I getting 'storage not initialized' error?"

AI uses: ask_stylus tool
Returns: Explanation with solution based on documentation context
```

### Generating Tests

Create test suites for your contracts:

```
User: "Write unit tests for this counter contract: [paste code]"

AI uses: generate_tests tool
Returns: Comprehensive test module with edge cases
```

### Build/Deploy Workflows

Get step-by-step deployment guidance:

```
User: "How do I deploy to Arbitrum Sepolia?"

AI uses: get_workflow tool
Returns: Commands for checking balance, deploying, and verifying
```

## Milestones

| Milestone | Description | Status |
|-----------|-------------|--------|
| M1 | Stylus Smart Contract Builder | ✅ Complete |
| M2 | Arbitrum SDK Integration (Bridging & Messaging) | ✅ Complete |
| M3 | Full dApp Builder (Backend + Frontend + Indexer + Oracle + Orchestration) | ✅ Complete |
| M4 | Orbit Chain Integration (Config, Deployment, Validators, Q&A, Orchestration) | In Progress |
| M5 | Unified AI Assistant | Planned |

### M2: Arbitrum SDK Integration

Cross-chain bridging and messaging support:

- **ETH Bridging**: L1 <-> L2 deposits and withdrawals
- **ERC20 Bridging**: Token bridging with gateway approvals
- **L1 -> L3 Bridging**: Direct L1 to Orbit chain bridging via double retryables
- **Cross-chain Messaging**: L1 -> L2 retryable tickets, L2 -> L1 messages via ArbSys
- **Status Tracking**: Message status monitoring and withdrawal claiming

```bash
# Example: Generate ETH deposit code
echo '{"method": "tools/call", "id": 1, "params": {"name": "generate_bridge_code", "arguments": {"bridge_type": "eth_deposit", "amount": "0.5"}}}' | python -m src.mcp.server
```

### M3: Full dApp Builder

Complete dApp scaffolding with all components:

- **Backend Generation**: NestJS or Express with viem/wagmi integration
- **Frontend Generation**: Next.js 14 + wagmi v2 + RainbowKit v2 + DaisyUI
- **Indexer Generation**: The Graph subgraphs (ERC20, ERC721, DeFi, custom events)
- **Oracle Integration**: Chainlink Price Feeds, VRF, Automation, Functions
- **Full Orchestration**: Scaffold complete dApps with monorepo structure
- **ABI Auto-Extraction**: Contract ABI is parsed from Stylus Rust code and injected into backend/frontend
- **ABI-Aware Generation**: Indexer schema/mappings, frontend hooks, and backend routes are generated from contract ABI
- **Compiler Verification**: Docker-based `cargo check` loop catches and auto-fixes compilation errors
- **Executable Scripts**: Generated `setup.sh`, `deploy.sh`, and `start.sh` for one-command workflows
- **CLI Scaffolding**: `setup.sh` uses a scaffold-first, backfill pattern with official CLI tools (`cargo stylus new`, `create-next-app`, `@nestjs/cli`) to fill in config files our templates don't generate, with graceful fallback if tools aren't installed
- **Env Standardization**: Centralized env var config (PORT 3001, CORS, BACKEND_URL) across all components

**Backend Templates:**
- NestJS + Stylus contract integration
- Express + Stylus (lightweight)
- NestJS + GraphQL (for subgraph querying)
- API Gateway (cross-chain proxy)

**Frontend Templates:**
- Next.js + wagmi + RainbowKit base
- DaisyUI component library
- Contract Dashboard (admin panel)
- Token Interface (ERC20/721 UI)

**Indexer Templates:**
- ERC20 Subgraph (transfers, balances)
- ERC721 Subgraph (ownership, metadata)
- DeFi Subgraph (swaps, liquidity)
- Custom Events Subgraph

**Oracle Templates:**
- Chainlink Price Feed
- Chainlink VRF (randomness)
- Chainlink Automation (keepers)
- Chainlink Functions

```bash
# Example: Generate full dApp scaffold
echo '{"method": "tools/call", "params": {"name": "orchestrate_dapp", "arguments": {"prompt": "Create a token staking dApp", "components": ["contract", "backend", "frontend", "indexer"]}}}' | python -m src.mcp.server

# Example: Generate backend only
echo '{"method": "tools/call", "params": {"name": "generate_backend", "arguments": {"prompt": "Create a staking API", "framework": "nestjs"}}}' | python -m src.mcp.server

# Example: Generate frontend with contract ABI
echo '{"method": "tools/call", "params": {"name": "generate_frontend", "arguments": {"prompt": "Create token dashboard", "contract_abi": "[...]"}}}' | python -m src.mcp.server
```

### M4: Orbit Chain Integration

Orbit chain deployment and management support:

- **Chain Configuration**: Generate `prepareChainConfig()` scripts for Rollup or AnyTrust chains
- **Rollup Deployment**: Generate `createRollup()` scripts with crash-proof `deployment.json` output (saves before receipt fetch)
- **Token Bridge**: Generate `createTokenBridge()` scripts with automatic ERC-20 approval for custom gas token chains
- **Custom Gas Tokens**: Full approval flow — RollupCreator + TokenBridgeCreator + Inbox approvals
- **AnyTrust DAC**: Full keyset lifecycle — BLS key generation (`generate-das-keys.sh`), keyset encoding, UpgradeExecutor-routed `setValidKeyset()`, hash verification
- **Validator Management**: Add/remove validators and batch posters
- **Node Configuration**: Generate Nitro node config via `prepareNodeConfig()` with post-processing — private key restoration, staker disable for single-key setups, `deployed-at` injection, DAS URL fix
- **Docker Compose**: Battle-tested templates with explicit HTTP/WS/metrics CLI flags, WASM cache cleanup entrypoint, DAS server with all required flags
- **Governance Management**: UpgradeExecutor role checking, granting, and revocation (`manage-governance.ts`)
- **Chain Verification**: Health check script tests RPC connectivity, balances, transfers, and contract deployment (`test-chain.ts`)
- **Full Orchestration**: Scaffold complete deployment projects with all scripts, configs, and documentation

```bash
# Example: Scaffold a complete Orbit chain deployment project
echo '{"method": "tools/call", "params": {"name": "orchestrate_orbit", "arguments": {"prompt": "Deploy an AnyTrust chain on Arbitrum Sepolia", "chain_name": "my-orbit-chain", "chain_id": 412346, "is_anytrust": true, "parent_chain": "arbitrum-sepolia"}}}' | python -m src.mcp.server

# Example: Generate chain configuration
echo '{"method": "tools/call", "params": {"name": "generate_orbit_config", "arguments": {"prompt": "Configure a custom gas token chain", "native_token": "0x...", "parent_chain": "arbitrum-sepolia"}}}' | python -m src.mcp.server

# Example: Ask about Orbit deployment
echo '{"method": "tools/call", "params": {"name": "ask_orbit", "arguments": {"question": "How do I deploy an Orbit chain with a custom gas token?"}}}' | python -m src.mcp.server
```

## Development

### Running Tests

```bash
# Run all unit tests
pytest tests/ -m "not integration"

# Run retrieval quality tests
pytest tests/test_retrieval.py -v

# Run MCP tool tests (requires tool implementations)
pytest tests/mcp_tools/ -v

# Run template selection and validation tests
pytest tests/test_templates.py -v -m "not integration"

# Run template compilation tests (requires Rust toolchain + cargo-stylus)
pytest tests/test_templates.py -v -m integration
```

**Template compilation tests require:**
- Rust toolchain 1.87.0: `rustup install 1.87.0`
- WASM target: `rustup target add wasm32-unknown-unknown --toolchain 1.87.0`
- cargo-stylus: `cargo install --locked cargo-stylus`

### Running Benchmarks

```bash
# Run all benchmarks
python scripts/run_benchmarks.py

# Run only P0 (critical) tests
python scripts/run_benchmarks.py --priority P0

# Run benchmarks for a specific tool
python scripts/run_benchmarks.py --tool get_stylus_context
```

Benchmark reports are saved to `benchmark_results/`.

### Code Formatting

```bash
black .
ruff check .
```

## Troubleshooting

### Embedding Generation Errors

If you encounter errors like `Error generating embeddings: RetryError` or `KeyError` during vector database ingestion:

**1. Check OpenRouter API Key**
```bash
# Verify your .env file has a valid API key
cat .env | grep OPENROUTER_API_KEY
```

Ensure:
- The API key is correctly set (no extra spaces or quotes)
- Your OpenRouter account has credits
- The embedding model `baai/bge-m3` is available on OpenRouter

**2. Rate Limiting Issues**

If you see `HTTPStatusError` with status 429, you're being rate limited. Solutions:

```bash
# Run with smaller batch size
python -m src.embeddings.vectordb --batch-size 25

# Or modify max_workers in vectordb.py to 1 for sequential processing
```

**3. Enable Debug Logging**

Add this to your script or at the start of your session to see detailed logs:

```python
import logging
logging.basicConfig(level=logging.INFO)
# For more verbose output:
# logging.basicConfig(level=logging.DEBUG)
```

### Scraper Errors

**"Execution context was destroyed" errors**

This is a browser navigation issue during scraping. The scraper will automatically retry. If it persists:
- The page may have heavy JavaScript that interferes with scraping
- These pages are skipped after retries; the scraper continues with other URLs

**Git clone failures**

If repository cloning fails:
```bash
# Check your network connection
ping github.com

# Try cloning manually to diagnose
git clone --depth 1 https://github.com/OffchainLabs/stylus-hello-world

# If behind a proxy, configure git
git config --global http.proxy http://proxy:port
```

**Timeout errors**

For slow connections, increase timeouts in the scraper config or reduce concurrent requests:
```bash
python -m scraper.run --max-concurrent 1
```

### ChromaDB Issues

**"Collection is empty" error**

If you see `collection is empty` when using `get_stylus_context` tool:
```bash
# The vector database must be generated locally (it's not included in the repo)
# Run this command to populate the database:
python -m src.embeddings.vectordb

# If that doesn't work, try resetting first:
python -m src.embeddings.vectordb --reset
```

**Import errors with opentelemetry**

If you see `TypeError: 'NoneType' object is not subscriptable` when importing chromadb:
```bash
# This is usually a conda environment issue
# Make sure you're in the correct environment
conda activate arbbuilder

# Or reinstall chromadb
pip uninstall chromadb
pip install chromadb
```

**Database corruption**

If the vector database seems corrupted:
```bash
# Reset and re-ingest
python -m src.embeddings.vectordb --reset
```

## CI/CD Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `qa.yml` | PRs to main, push to main | TypeScript type check, Python lint, Python tests |
| `maintenance.yml` | Weekly (Mon 6AM UTC) + manual | SDK monitoring, health checks, discovery, re-verification, auto-remediation |
| `refresh-rag.yml` | Manual | Full RAG refresh: scrape, process, migrate to Vectorize |
| `deploy-staging.yml` | Manual | Deploy to staging environment |
| `release-chunks.yml` | GitHub release | Build and publish pre-processed chunks + embeddings |

### maintenance.yml Jobs

| Job | Trigger | What It Does |
|-----|---------|-------------|
| `sdk-monitor` | Weekly + manual | Checks crates.io/npm for new SDK versions |
| `health-check` | Weekly + manual | Checks all repos for archived/deleted status |
| `discover` | Manual only | Searches GitHub for new community repos |
| `reverify` | On SDK update or manual | Re-verifies all repos with `verify_source.py --all` |
| `remediate` | Manual only | Auto-removes archived/deleted repos from `sources.json` |
| `sync-sources` | Weekly + manual | Syncs `sources.json` to CF KV registry |
| `create-issue` | When problems found | Creates GitHub issue with maintenance label |

## License

MIT License - see [LICENSE](LICENSE) for details.

## References

- [Arbitrum Documentation](https://docs.arbitrum.io)
- [Stylus Documentation](https://docs.arbitrum.io/stylus/stylus-overview)
- [ICP Coder](https://github.com/Quantum3-Labs/icp-coder) - Reference implementation
- [Stacks Builder](https://github.com/Quantum3-Labs/stacks-builder) - Reference implementation

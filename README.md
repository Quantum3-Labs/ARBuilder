# ARBuilder

AI-powered development assistant for the Arbitrum ecosystem. ARBuilder transforms natural language prompts into:

- **Stylus smart contracts** (Rust)
- **Cross-chain SDK implementations** (asset bridging and messaging)
- **Full-stack dApps** (contracts + backend + indexer + oracle + frontend + wallet integration)
- **Orbit chain deployment assistance**

## Architecture

ARBuilder uses a **Retrieval-Augmented Generation (RAG)** pipeline to provide context-aware code generation and assistance. It integrates with Cursor/VS Code via an MCP server.

```
┌─────────────────────────────────────────────────────────────┐
│                      ARBuilder                               │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │   Scraper   │───▶│  Embeddings │───▶│  Vector DB      │  │
│  │  (crawl4ai) │    │  (Gemini)   │    │  (ChromaDB)     │  │
│  └─────────────┘    └─────────────┘    └────────┬────────┘  │
│                                                  │           │
│  ┌─────────────┐    ┌─────────────┐    ┌────────▼────────┐  │
│  │  MCP Server │◀───│  RAG Engine │◀───│    Retrieval    │  │
│  │ (Cursor/VS) │    │ (DeepSeek)  │    │                 │  │
│  └─────────────┘    └─────────────┘    └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
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
      "args": ["-y", "mcp-remote", "https://arbbuilder.whymelabs.com/mcp",
               "--header", "Authorization: Bearer YOUR_API_KEY"]
    }
  }
}
```
Get your API key at [arbbuilder.whymelabs.com](https://arbbuilder.whymelabs.com)

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
# Should show: "Capabilities: 13 tools, 11 resources, 5 prompts"

# 5. Configure Cursor IDE (~/.cursor/mcp.json) - see Setup section below
```

## Tutorial Video

Watch the tutorial to see ARBuilder in action:

[Tutorial Video](https://drive.google.com/file/d/1gLfXvwNyYeVfLY2g6WQySDyOcNDxmOP2/view?usp=share_link)

## Project Structure

```
ArbBuilder/
├── scraper/              # Data collection module
│   ├── config.py         # URLs and source configuration (M1-M3 sources)
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
│   │   └── oracle_templates.py   # M3: Chainlink templates
│   ├── utils/            # Shared utilities
│   │   ├── version_manager.py   # SDK version management
│   │   ├── env_config.py        # Centralized env var configuration
│   │   ├── abi_extractor.py     # Stylus ABI extraction from Rust code
│   │   └── compiler_verifier.py # Docker-based cargo check verification
│   ├── mcp/              # MCP server for IDE integration
│   │   ├── server.py     # MCP server (tools, resources, prompts)
│   │   ├── tools/        # MCP tool implementations (13 tools)
│   │   │   ├── get_stylus_context.py   # M1
│   │   │   ├── generate_stylus_code.py # M1
│   │   │   ├── ask_stylus.py           # M1
│   │   │   ├── generate_tests.py       # M1
│   │   │   ├── get_workflow.py         # M1
│   │   │   ├── generate_bridge_code.py # M2
│   │   │   ├── generate_messaging_code.py # M2
│   │   │   ├── ask_bridging.py         # M2
│   │   │   ├── generate_backend.py     # M3
│   │   │   ├── generate_frontend.py    # M3
│   │   │   ├── generate_indexer.py     # M3
│   │   │   ├── generate_oracle.py      # M3
│   │   │   └── orchestrate_dapp.py     # M3
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
├── scripts/
│   ├── run_benchmarks.py     # Benchmark runner
│   └── ingest_m3_sources.py  # M3 source ingestion
├── data/
│   ├── raw/              # Raw scraped data (73 pages + 17 repos)
│   ├── processed/        # Pre-processed chunks (8,692 chunks)
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
DEFAULT_EMBEDDING=google/gemini-embedding-001
DEFAULT_CROSS_ENCODER=nvidia/llama-3.2-nv-rerankqa-1b-v2
```

### 3. Setup Data

The repository includes all data needed:
- **Raw data** (`data/raw/`): 73 markdown pages + 17 GitHub repos
- **Processed chunks** (`data/processed/`): 8,692 chunks ready for embedding

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
Capabilities: 13 tools, 11 resources, 5 prompts
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

Use our hosted API - no local setup required. Available at [arbbuilder.whymelabs.com](https://arbbuilder.whymelabs.com).

1. Sign up at https://arbbuilder.whymelabs.com and get your API key
2. Add to your MCP configuration:

```json
{
  "mcpServers": {
    "arbbuilder": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://arbbuilder.whymelabs.com/mcp",
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

### Data Scraping (Optional)

Run the full data collection pipeline to refresh raw data:

```bash
# Activate environment
conda activate arbbuilder

# Run full pipeline (web scraping + GitHub cloning)
python -m scraper.run

# Scrape only Stylus sources
python -m scraper.run --categories stylus

# Skip web scraping, only clone GitHub repos
python -m scraper.run --skip-web

# Skip GitHub cloning, only scrape web
python -m scraper.run --skip-github
```

### Data Sources

The scraper collects data from 50+ sources with automatic Stylus SDK version detection:

**Stylus (M1)**
- Official documentation: [docs.arbitrum.io](https://docs.arbitrum.io/stylus/stylus-overview) (8 pages including gas-metering)
- Curated resources: [awesome-stylus](https://github.com/OffchainLabs/awesome-stylus)
- Official examples: stylus-hello-world (v0.9.0), stylus-quickstart-vending-machine (v0.8.4)
- Production codebases: OpenZeppelin rust-contracts-stylus (v0.9.0), renegade-contracts
- Community projects and challenges (19 challenge submissions, all v0.9.0)
- Blog articles

**Stylus SDK Version Support:**

| Version | Status | Notes |
|---------|--------|-------|
| 0.9.0 | **Main** (default) | Recommended for new projects |
| 0.8.x | Supported | Minimum supported version |
| < 0.8.0 | Deprecated | Warning shown, excluded from knowledge base |

**Version Filtering:**
- Only sources using Stylus SDK >= 0.8.0 are included
- Each GitHub repo's SDK version is auto-detected from Cargo.toml
- Deprecated versions (< 0.8.0) are excluded from the knowledge base
- Code generation targets the main version (0.9.0) by default

**Arbitrum SDK (M2)**
- [arbitrum-sdk](https://github.com/OffchainLabs/arbitrum-sdk)
- [arbitrum-tutorials](https://github.com/OffchainLabs/arbitrum-tutorials)
- Official bridging and messaging documentation (7 pages)

**Orbit SDK (M4)**
- [arbitrum-orbit-sdk](https://github.com/OffchainLabs/arbitrum-orbit-sdk)

## API Access

### Public MCP Endpoint (Free)

The MCP endpoint at `/mcp` is free to use and designed for IDE integration:

```
https://arbbuilder.whymelabs.com/mcp
```

- Requires `arb_` API key from dashboard
- Usage tracked per API key
- Rate limited per free tier (100 calls/day)

### Transparency Page

View all ingested sources and code templates at [arbbuilder.whymelabs.com/transparency](https://arbbuilder.whymelabs.com/transparency).

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

ARBuilder exposes a full MCP server with **13 tools**, **11 resources**, and **5 prompts** for Cursor/VS Code integration.

### Tools

**M1: Stylus Development (5 tools)**

| Tool | Description |
|------|-------------|
| `get_stylus_context` | RAG retrieval for docs and code examples |
| `generate_stylus_code` | Generate Stylus contracts from prompts |
| `ask_stylus` | Q&A, debugging, concept explanations |
| `generate_tests` | Generate unit/integration/fuzz tests |
| `get_workflow` | Build/deploy/test workflow guidance |

**M2: Arbitrum SDK - Bridging & Messaging (3 tools)**

| Tool | Description |
|------|-------------|
| `generate_bridge_code` | Generate ETH/ERC20 bridging code (L1<->L2, L1->L3) |
| `generate_messaging_code` | Generate cross-chain messaging code |
| `ask_bridging` | Q&A about bridging patterns and SDK usage |

**M3: Full dApp Builder (5 tools)**

| Tool | Description |
|------|-------------|
| `generate_backend` | Generate NestJS/Express backends with Web3 integration |
| `generate_frontend` | Generate Next.js + wagmi + RainbowKit frontends |
| `generate_indexer` | Generate The Graph subgraphs for indexing |
| `generate_oracle` | Generate Chainlink oracle integrations |
| `orchestrate_dapp` | Scaffold complete dApps with multiple components |

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

**Stylus SDK Version Support:**

| Version | Status | Notes |
|---------|--------|-------|
| 0.9.0 | **Main** (default) | Recommended for new projects |
| 0.8.x | Supported | Minimum supported version |
| < 0.8.0 | Deprecated | Warning shown, may not compile |

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
| M3 | Full dApp Builder | ✅ Complete |
| M4 | Orbit Chain Integration | Planned |
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
- The embedding model `google/gemini-embedding-001` is available

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

## License

MIT License - see [LICENSE](LICENSE) for details.

## References

- [Arbitrum Documentation](https://docs.arbitrum.io)
- [Stylus Documentation](https://docs.arbitrum.io/stylus/stylus-overview)
- [ICP Coder](https://github.com/Quantum3-Labs/icp-coder) - Reference implementation
- [Stacks Builder](https://github.com/Quantum3-Labs/stacks-builder) - Reference implementation

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

## Project Structure

```
ArbBuilder/
├── scraper/              # Data collection module
│   ├── config.py         # URLs and source configuration
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
│   │   ├── vectordb.py   # ChromaDB wrapper with hybrid search
│   │   └── reranker.py   # BM25, LLM, and hybrid reranking
│   ├── mcp/              # MCP server for IDE integration
│   │   ├── server.py     # MCP server (tools, resources, prompts)
│   │   ├── tools/        # MCP tool implementations (5 tools)
│   │   ├── resources/    # Static knowledge (CLI, workflows, networks)
│   │   └── prompts/      # Workflow templates
│   └── rag/              # RAG pipeline (TBD)
├── tests/
│   ├── mcp_tools/        # MCP tool test cases and benchmarks
│   │   ├── test_get_stylus_context.py
│   │   ├── test_generate_stylus_code.py
│   │   ├── test_ask_stylus.py
│   │   ├── test_generate_tests.py
│   │   └── benchmark.py  # Evaluation framework
│   └── test_retrieval.py # Retrieval quality tests
├── docs/
│   └── mcp_tools_spec.md # MCP tools specification
├── scripts/
│   └── run_benchmarks.py # Benchmark runner
├── data/
│   ├── raw/              # Raw scraped data (73 pages + 17 repos)
│   ├── processed/        # Pre-processed chunks (8,692 chunks)
│   └── chroma_db/        # ChromaDB vector store (generated locally)
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

# Install playwright browsers for web scraping
playwright install chromium
```

### 2. Configure Environment Variables

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
OPENROUTER_API_KEY=your-api-key
DEFAULT_MODEL=deepseek/deepseek-v3.2
DEFAULT_EMBEDDING=google/gemini-embedding-001
```

### 3. Setup Data

The repository includes all data needed:
- **Raw data** (`data/raw/`): 73 markdown pages + 17 GitHub repos
- **Processed chunks** (`data/processed/`): 8,692 chunks ready for embedding

To generate the vector database:

```bash
# Ingest processed chunks into ChromaDB
python -m src.embeddings.vectordb
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

The scraper collects data from:

**Stylus (M1)**
- Official documentation: [docs.arbitrum.io](https://docs.arbitrum.io/stylus/stylus-overview)
- Curated resources: [awesome-stylus](https://github.com/OffchainLabs/awesome-stylus)
- Official examples: stylus-by-example, stylus-hello-world, etc.
- Production codebases: OpenZeppelin rust-contracts-stylus, renegade-contracts, etc.
- Community projects and blog articles

**Arbitrum SDK (M2)**
- [arbitrum-sdk](https://github.com/OffchainLabs/arbitrum-sdk)

**Orbit SDK (M4)**
- [arbitrum-orbit-sdk](https://github.com/OffchainLabs/arbitrum-orbit-sdk)

## MCP Capabilities

ARBuilder exposes a full MCP server with **5 tools**, **5 resources**, and **5 prompts** for Cursor/VS Code integration.

### Tools

| Tool | Description |
|------|-------------|
| `get_stylus_context` | RAG retrieval for docs and code examples |
| `generate_stylus_code` | Generate Stylus contracts from prompts |
| `ask_stylus` | Q&A, debugging, concept explanations |
| `generate_tests` | Generate unit/integration/fuzz tests |
| `get_workflow` | Build/deploy/test workflow guidance |

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

| Resource URI | Description |
|--------------|-------------|
| `stylus://cli/commands` | Complete cargo-stylus CLI reference |
| `stylus://workflows/build` | Step-by-step build workflow |
| `stylus://workflows/deploy` | Deployment workflow with network configs |
| `stylus://workflows/test` | Testing workflow (unit, integration, fuzz) |
| `stylus://config/networks` | Arbitrum network configurations |

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

Ask your AI assistant to generate contracts:

```
User: "Create an ERC20 token called MyToken with 1 million supply"

AI uses: generate_stylus_code tool
Returns: Complete Rust contract with proper imports, storage, and methods
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
| M2 | Arbitrum SDK Integration | Planned |
| M3 | Full dApp Builder | Planned |
| M4 | Orbit Chain Integration | Planned |
| M5 | Unified AI Assistant | Planned |

## Development

### Running Tests

```bash
# Run all tests
pytest tests/

# Run retrieval quality tests
pytest tests/test_retrieval.py -v

# Run MCP tool tests (requires tool implementations)
pytest tests/mcp_tools/ -v
```

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

## License

MIT License - see [LICENSE](LICENSE) for details.

## References

- [Arbitrum Documentation](https://docs.arbitrum.io)
- [Stylus Documentation](https://docs.arbitrum.io/stylus/stylus-overview)
- [ICP Coder](https://github.com/Quantum3-Labs/icp-coder) - Reference implementation
- [Stacks Builder](https://github.com/Quantum3-Labs/stacks-builder) - Reference implementation

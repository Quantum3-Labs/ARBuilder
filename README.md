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
│   │   └── tools/        # MCP tool implementations
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

## MCP Tools

ARBuilder provides 4 MCP tools for Cursor/VS Code integration:

### 1. `get_stylus_context`
Retrieves relevant documentation and code examples from the RAG database.

```json
{
  "query": "How to create an ERC20 token",
  "n_results": 5,
  "content_type": "all"
}
```

### 2. `generate_stylus_code`
Generates Stylus/Rust smart contract code based on requirements.

```json
{
  "prompt": "Create a counter contract with increment and get functions",
  "contract_type": "custom",
  "include_tests": false
}
```

### 3. `ask_stylus`
Answers questions, explains concepts, and helps debug Stylus code.

```json
{
  "question": "What is the sol_storage! macro?",
  "question_type": "concept"
}
```

### 4. `generate_tests`
Generates test cases for Stylus smart contracts.

```json
{
  "contract_code": "...",
  "test_framework": "rust_native",
  "test_types": ["unit"]
}
```

See [docs/mcp_tools_spec.md](docs/mcp_tools_spec.md) for full specification.

## Milestones

| Milestone | Description | Status |
|-----------|-------------|--------|
| M1 | Stylus Smart Contract Builder | In Progress |
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

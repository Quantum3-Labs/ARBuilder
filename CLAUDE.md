# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ARBuilder is an AI-powered development assistant for the Arbitrum ecosystem. It uses RAG (Retrieval-Augmented Generation) to provide context-aware code generation for:

- **Stylus smart contracts** (Rust/WASM)
- **Arbitrum SDK bridging** (TypeScript)
- **Cross-chain messaging** (L1 ↔ L2 ↔ L3)
- **Full-stack dApps** (contracts + backend + frontend + indexer)

## Repository Structure

```
ArbBuilder/
├── src/
│   ├── mcp/                  # MCP server for IDE integration
│   │   ├── server.py         # Main MCP server
│   │   ├── tools/            # 13 MCP tools (M1: 5, M2: 3, M3: 5)
│   │   ├── resources/        # Static knowledge (11 resources)
│   │   └── prompts/          # Workflow templates
│   ├── embeddings/           # Vector DB and retrieval
│   │   ├── vectordb.py       # ChromaDB wrapper with hybrid BM25+vector search
│   │   └── reranker.py       # BM25 + LLM reranking
│   ├── templates/            # Code generation templates
│   │   ├── stylus_templates.py   # M1: Stylus contracts
│   │   ├── backend_templates.py  # M3: NestJS/Express
│   │   ├── frontend_templates.py # M3: Next.js + wagmi
│   │   ├── indexer_templates.py  # M3: The Graph subgraphs
│   │   └── oracle_templates.py   # M3: Chainlink integrations
│   └── preprocessing/        # Text chunking and cleaning
├── scraper/                  # Data collection (web + GitHub)
├── data/
│   ├── raw/                  # Scraped docs and repos
│   ├── processed/            # Pre-processed chunks
│   └── chroma_db/            # Vector database (local)
├── tests/                    # Test suites
├── docs/                     # Documentation
└── scripts/                  # Utility scripts
```

## Development Commands

### Environment Setup
```bash
conda env create -f environment.yml
conda activate arbbuilder
playwright install chromium  # For web scraping
```

### Running the MCP Server
```bash
# Direct execution
python -m src.mcp.server

# Test with JSON-RPC
echo '{"method": "tools/list"}' | python -m src.mcp.server
```

### Data Pipeline
```bash
# Scrape documentation and repos
python -m scraper.run

# Preprocess raw data
python -m src.preprocessing.processor

# Generate vector database
python -m src.embeddings.vectordb

# Reset and regenerate
python -m src.embeddings.vectordb --reset
```

### Testing
```bash
# Run all tests
pytest tests/

# Run MCP tool tests
pytest tests/mcp_tools/ -v

# Run benchmarks
python scripts/run_benchmarks.py
```

### Code Quality
```bash
black .
ruff check .
```

## MCP Tools Reference

### M1: Stylus Development (5 tools)
| Tool | Purpose |
|------|---------|
| `get_stylus_context` | RAG retrieval for docs/code examples |
| `generate_stylus_code` | Generate Stylus contracts from prompts |
| `ask_stylus` | Q&A, debugging, concept explanations |
| `generate_tests` | Generate unit/integration/fuzz tests |
| `get_workflow` | Build/deploy/test workflow guidance |

### M2: Arbitrum SDK (3 tools)
| Tool | Purpose |
|------|---------|
| `generate_bridge_code` | ETH/ERC20 bridging (L1↔L2, L1→L3) |
| `generate_messaging_code` | Cross-chain messaging via retryables |
| `ask_bridging` | Bridging Q&A and patterns |

### M3: Full dApp Builder (5 tools)
| Tool | Purpose |
|------|---------|
| `generate_backend` | NestJS/Express backend with viem integration |
| `generate_frontend` | Next.js + wagmi + RainbowKit frontend |
| `generate_indexer` | The Graph subgraph generation |
| `generate_oracle` | Chainlink oracle integrations |
| `orchestrate_dapp` | Full dApp scaffolding coordinator |

## Architecture Notes

### RAG Pipeline
1. **Query** → BM25 + Vector search (hybrid)
2. **Retrieve** → Top-k chunks from ChromaDB
3. **Rerank** → LLM-based relevance scoring
4. **Generate** → Context-augmented response via DeepSeek/OpenRouter

### Embedding Model
- Provider: OpenRouter
- Model: `google/gemini-embedding-001`
- Dimensions: 768

### LLM Models
- Code generation: `deepseek/deepseek-v3.2`
- Q&A: `google/gemini-2.0-flash-001`

## Stylus Development Guidelines

When generating or reviewing Stylus code:

### Required Attributes
```rust
#![cfg_attr(not(any(feature = "export-abi", test)), no_std)]
#![cfg_attr(not(test), no_main)]
extern crate alloc;
```

### Storage Pattern
```rust
sol_storage! {
    #[entrypoint]
    pub struct MyContract {
        uint256 value;
        mapping(address => uint256) balances;
    }
}
```

### Public Interface
```rust
#[public]
impl MyContract {
    pub fn get_value(&self) -> U256 {
        self.value.get()
    }
}
```

### Dependencies (Cargo.toml)
```toml
[dependencies]
stylus-sdk = "0.9.2"
alloy-primitives = "=0.8.20"
alloy-sol-types = "=0.8.20"

[lib]
crate-type = ["cdylib"]

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"
```

### Key Constraints
- **24KB size limit** (Brotli-compressed WASM)
- **Rust 1.81** (1.82+ may have issues)
- **No floating point** operations
- **Yearly reactivation** required

## Network Endpoints

| Network | RPC URL | Chain ID |
|---------|---------|----------|
| Arbitrum Sepolia | `https://sepolia-rollup.arbitrum.io/rpc` | 421614 |
| Arbitrum One | `https://arb1.arbitrum.io/rpc` | 42161 |
| Arbitrum Nova | `https://nova.arbitrum.io/rpc` | 42170 |

## Common Tasks

### Adding a New MCP Tool
1. Create tool class in `src/mcp/tools/`
2. Inherit from `BaseTool`
3. Define `name`, `description`, `input_schema`
4. Implement `execute()` method
5. Register in `src/mcp/tools/__init__.py`
6. Add tests in `tests/mcp_tools/`

### Updating Knowledge Base
1. Add URLs to `scraper/config.py`
2. Run `python -m scraper.run`
3. Run `python -m src.preprocessing.processor`
4. Run `python -m src.embeddings.vectordb --reset`

### Testing MCP Tools Locally
```bash
# Test specific tool
echo '{"method": "tools/call", "params": {"name": "ask_stylus", "arguments": {"question": "How do I use mappings?"}}}' | python -m src.mcp.server
```

## Environment Variables

Required in `.env`:
```env
OPENROUTER_API_KEY=your-api-key
DEFAULT_MODEL=deepseek/deepseek-v3.2
DEFAULT_EMBEDDING=google/gemini-embedding-001
```

## Commit Guidelines

- Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
- Include `Co-Authored-By: Claude` for AI-assisted commits
- Update README.md for architectural changes

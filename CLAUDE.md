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
│   │   ├── backend_templates.py  # M3: NestJS/Express (ABI placeholder support)
│   │   ├── frontend_templates.py # M3: Next.js + wagmi (ABI placeholder support)
│   │   ├── indexer_templates.py  # M3: The Graph subgraphs
│   │   └── oracle_templates.py   # M3: Chainlink integrations
│   ├── utils/                # Shared utilities
│   │   ├── version_manager.py    # SDK version management
│   │   ├── env_config.py         # Centralized env var configuration
│   │   ├── abi_extractor.py      # Stylus ABI extraction from Rust code
│   │   └── compiler_verifier.py  # Docker-based cargo check verification
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

### Data Pipeline (Local)
```bash
# Scrape documentation and repos
python -m scraper.run

# Preprocess raw data
python -m src.preprocessing.processor

# Generate vector database
python -m src.embeddings.vectordb

# Push to CF Vectorize
AUTH_SECRET=xxx npx tsx scripts/diff-migrate.ts --full
```

### Data Pipeline (Hosted - Worker-Native)
The hosted service has a Worker-native ingestion pipeline that runs automatically:
- **Cron**: Every 6 hours, processes next pending/stale source
- **Admin UI**: `/admin` page with per-source Refresh and "Process Next" buttons
- **API**: `POST /api/admin/ingest` with `{ url, category }` or `{ action: "process_next" }`
- **Pipeline**: `scraper.ts` → `chunker.ts` → `ingestPipeline.ts` → Workers AI embedding → Vectorize upsert

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

### M3 dApp Generation Pipeline
1. **Template Selection** → Based on contract_type and prompt keywords
2. **ABI Extraction** → `abi_extractor.py` parses #[public] impl blocks from lib.rs
3. **Compiler Verification** → `compiler_verifier.py` runs `cargo check` via Docker (up to 2 fix attempts)
4. **ABI Injection** → Backend/frontend templates have `__ABI_PLACEHOLDER__` markers replaced with actual ABI
5. **Env Config** → `env_config.py` generates standardized `.env.example` (PORT=3001, CORS, BACKEND_URL)
6. **Script Generation** → `setup.sh`, `deploy.sh`, `start.sh` for one-command workflows
7. **CLI Scaffolding** → `setup.sh` uses a **scaffold-first, backfill** pattern: official CLI tools scaffold into a temp dir, then only config files missing from the project are copied over (our generated `src/` always takes precedence). Supported CLI tools:
   - **Contract**: `cargo stylus new` → `.cargo/config.toml`, latest `rust-toolchain.toml`
   - **Frontend**: `npx create-next-app@latest` → `postcss.config.mjs`, `tailwind.config.ts`, `public/` icons
   - **Backend (NestJS only)**: `npx @nestjs/cli@latest new` → `nest-cli.json`, `.prettierrc`, test scaffold
   - Falls back gracefully if CLI tools are not installed

### Utility Modules (`src/utils/`)
- **env_config.py**: Single source of truth for env var names (PORT=3001, FRONTEND_URL, NEXT_PUBLIC_BACKEND_URL)
- **abi_extractor.py**: Regex-based ABI extraction from Stylus Rust code (no Docker needed)
- **compiler_verifier.py**: Docker-based `cargo check` with structured error parsing and LLM fix loop

### Worker-Native Ingestion Pipeline (`apps/web/src/lib/`)
- **scraper.ts**: Web documentation scraping via HTMLRewriter + regex HTML-to-markdown
- **github.ts**: GitHub repo scraping via Trees API + Contents API (no tarball)
- **chunker.ts**: DocumentChunker (512 tokens) + CodeChunker (1024 tokens), character-based token estimation
- **ingestPipeline.ts**: Orchestrator — scrape → chunk → embed (BGE-M3) → upsert (Vectorize)
- **Cron**: `worker.ts` scheduled handler calls ingest API via `WORKER_SELF_REFERENCE`
- **Admin API**: `/api/admin/ingest` (POST for ingestion, GET for progress)

### Embedding Model
- Model: `@cf/baai/bge-m3` (CF Workers AI)
- Dimensions: 1024

### LLM Models
- Code generation: `openai/gpt-oss-120b`
- Q&A: `openai/gpt-oss-120b`

## Stylus Development Guidelines

When generating or reviewing Stylus code:

### Required Attributes
```rust
#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]
#[macro_use]
extern crate alloc;

use alloc::{vec, vec::Vec};
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

    pub fn get_caller(&self) -> Address {
        self.vm().msg_sender()
    }
}
```

### Dependencies (Cargo.toml)
```toml
[package]
name = "my_contract"  # MUST use underscores, not hyphens

[dependencies]
stylus-sdk = "0.10.0"
alloy-primitives = "1.0.1"
alloy-sol-types = "1.0.1"

[lib]
crate-type = ["lib", "cdylib"]  # "lib" needed for bin target linking

[[bin]]
name = "my_contract"
path = "src/main.rs"

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"
```

### Required Project Files (SDK 0.10.0+)

**Stylus.toml** (required):
```toml
[workspace]

[workspace.networks]

[contract]
```

**rust-toolchain.toml** (required):
```toml
[toolchain]
channel = "1.91.0"
targets = ["wasm32-unknown-unknown"]
```

**src/main.rs** (required for cargo stylus deploy):
```rust
#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]

#[cfg(not(any(test, feature = "export-abi")))]
#[unsafe(no_mangle)]
pub extern "C" fn main() {}

#[cfg(feature = "export-abi")]
fn main() {
    my_contract::print_from_args();  // NOT print_abi()
}
```

### SDK 0.10.0 API Changes
```rust
// Old (0.9.x) → New (0.10.0)
// msg::sender()  → self.vm().msg_sender()
// msg::value()   → self.vm().msg_value()
// evm::log(...)  → self.vm().log(...)
```

### Cross-Contract Calls (sol_interface!)
```rust
// Call is available from prelude::* — no separate import needed
// Or explicitly: use stylus_sdk::call::Call;

sol_interface! {
    interface IPriceFeed {
        function latestPrice() external view returns (uint256);
    }
    interface IToken {
        function transfer(address to, uint256 amount) external returns (bool);
        function balanceOf(address account) external view returns (uint256);
    }
}

// VIEW call — Call::new() is fine (read-only, no state changes)
let balance = token.balance_of(self.vm(), Call::new(), account)?;
let price = feed.latest_price(self.vm(), Call::new())?;

// STATE-MODIFYING call — extract Call first to avoid borrow conflict
let call = Call::new_mutating(self);
let success = token.transfer(self.vm(), call, recipient, amount)?;
```

### Events and Errors (sol! macro)
```rust
// sol! is NOT in prelude — MUST import explicitly
use alloy_sol_types::{sol, SolError};

sol! {
    event Transfer(address indexed from, address indexed to, uint256 tokenId);
    error InsufficientBalance(uint256 available, uint256 required);
}

// Use camelCase in sol! field names (Solidity convention)
// tokenId NOT token_id, fromAddress NOT from_address

// Emit event:
self.vm().log(Transfer { from, to, tokenId: token_id });

// Return error:
return Err(InsufficientBalance { available: bal, required: amount }.abi_encode());
```

### Dynamic Arrays (StorageVec)
```rust
sol_storage! {
    #[entrypoint]
    pub struct MyContract {
        uint256[] items;         // Dynamic array
        // mapping(uint256 => MyStruct) structs;
    }
}

// Append to dynamic array:
self.items.push(value);          // For primitive types (uint256, address, bool)
// self.structs.grow();          // For struct types — grow() adds empty slot

// Read length and elements:
let len = self.items.len();
let val = self.items.get(index).unwrap();
```

### Key Constraints
- **24KB size limit** (Brotli-compressed WASM)
- **Rust 1.91.0** (via rust-toolchain.toml)
- **No floating point** operations
- **Yearly reactivation** required
- **Stylus.toml required** since SDK 0.10.0
- **rust-toolchain.toml required** since SDK 0.10.0
- **src/main.rs required** — cargo stylus deploy uses `cargo run` to check constructors
- **Package name must use underscores** — hyphens prevent cargo-stylus WASM lookup
- **crate-type = ["lib", "cdylib"]** — "lib" needed for bin target linking
- **use alloc::{vec, vec::Vec}** — sol_storage! macro needs vec module in scope
- **print_from_args()** is the 0.10.0 ABI export function (NOT print_abi())
- **uint8 in sol_storage!** maps to Uint<8,1>, not u8 — prefer uint256
- **RawCall::new_with_value(self.vm(), amount)** — needs self.vm() as first arg + unsafe block
- **transfer_eth** — `use stylus_sdk::call::transfer::transfer_eth;` then `transfer_eth(self.vm(), to, amount)?` (needs `self.vm()` not `self`)
- **sol_interface! for interfaces** — use `sol_interface!` (NOT `sol!`) to define external contract interfaces for cross-contract calls
- **Call contexts** — `Call::new()` for VIEW calls, `Call::new_mutating(self)` for STATE-MODIFYING calls. Extract Call to local var to avoid borrow conflict: `let call = Call::new_mutating(self);`
- **sol! needs explicit import** — `use alloy_sol_types::{sol, SolError};` — sol! is NOT in prelude
- **sol! uses camelCase fields** — `tokenId` not `token_id`, `fromAddress` not `from_address` (Solidity convention)
- **Dynamic arrays** — `uint256[] items;` in sol_storage!, append with `.push(val)` for primitives, `.grow()` for structs. Never `.setter(len).unwrap()`
- **Borrow checker** — extract `.get()` values to local vars before combining with `.set()`. Never `self.field.setter(self.vm().something())`
- **B256 conversion** — `B256::from_uint()` does NOT exist. Use `B256::from(value.to_be_bytes::<32>())` to convert U256 to B256
- **ABI uses camelCase** — Stylus exports snake_case Rust fns as camelCase (`create_market` → `createMarket`). Frontend must use camelCase in `functionName`
- **View functions can't call external contracts** — `&self` view fns revert on cross-contract calls (unlike Solidity). Use `&mut self` or read from frontend
- **Arbitrum L2 gas** — MetaMask may underestimate `maxFeePerGas` on Arbitrum Sepolia. Add explicit gas overrides if "max fee per gas less than block base fee"

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

**Via Admin UI (hosted)**:
1. Go to `/admin`, authenticate
2. Click "Add Source" with URL and category
3. Click "Refresh" on the source to trigger ingestion

**Via Local Pipeline**:
1. Add sources to `sources.json`
2. Run `python -m scraper.run`
3. Run `python -m src.preprocessing.processor`
4. Run `AUTH_SECRET=xxx npx tsx scripts/diff-migrate.ts --full`

### Syncing Sources to CF KV
```bash
ARBBUILDER_ADMIN_SECRET=xxx npx tsx scripts/sync_sources.ts
ARBBUILDER_ADMIN_SECRET=xxx npx tsx scripts/sync_sources.ts --dry-run
ARBBUILDER_ADMIN_SECRET=xxx npx tsx scripts/sync_sources.ts --remove-stale
```

### Running QA Checks Locally
```bash
# TypeScript
cd apps/web && npx tsc --noEmit

# Python
ruff check .
pytest tests/ -x --timeout=120
```

### Source Verification & Maintenance
```bash
# Verify all repos — M1 Stylus + M2 SDK + M3 dApp Builder (compile, lint, tests, health, audit, AI review)
python scripts/verify_source.py --all --steps 1,2,4,5 --output reports/verification.json

# SDK monitoring + health check + community discovery
python scripts/maintain_sources.py all --output reports/maintenance.json

# Auto-remove archived/deleted repos from config
python scripts/maintain_sources.py remediate
```

### Testing MCP Tools Locally
```bash
# Test specific tool
echo '{"method": "tools/call", "params": {"name": "ask_stylus", "arguments": {"question": "How do I use mappings?"}}}' | python -m src.mcp.server
```

## Environment Variables

Required in `.env`:
```env
OPENROUTER_API_KEY=your-api-key
DEFAULT_MODEL=openai/gpt-oss-120b
DEFAULT_EMBEDDING=baai/bge-m3
```

## Commit Guidelines

- Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
- Include `Co-Authored-By: Claude` for AI-assisted commits
- Update README.md for architectural changes

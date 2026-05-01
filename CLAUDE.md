# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ARBuilder is an AI-powered development assistant for the Arbitrum ecosystem. It uses RAG (Retrieval-Augmented Generation) to provide context-aware code generation for:

- **Stylus smart contracts** (Rust/WASM)
- **Arbitrum SDK bridging** (TypeScript)
- **Cross-chain messaging** (L1 ↔ L2 ↔ L3)
- **Full-stack dApps** (contracts + backend + frontend + indexer)
- **Orbit chain deployment** (@arbitrum/orbit-sdk)

## Repository Structure

```
ArbBuilder/
├── src/
│   ├── mcp/                  # MCP server for IDE integration
│   │   ├── server.py         # Main MCP server
│   │   ├── tools/            # 19 MCP tools (M1: 6, M2: 3, M3: 5, M4: 5)
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
│   │   ├── oracle_templates.py   # M3: Chainlink integrations
│   │   └── orbit_templates.py    # M4: Orbit chain deployment (@arbitrum/orbit-sdk)
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

### M1: Stylus Development (6 tools)
| Tool | Purpose |
|------|---------|
| `get_stylus_context` | RAG retrieval for docs/code examples |
| `generate_stylus_code` | Generate Stylus contracts from prompts |
| `ask_stylus` | Q&A, debugging, concept explanations |
| `generate_tests` | Generate unit/integration/fuzz tests |
| `get_workflow` | Build/deploy/test workflow guidance |
| `validate_stylus_code` | Compile-check code via Docker cargo check with fix guidance |

### M2: Arbitrum SDK (3 tools)
| Tool | Purpose |
|------|---------|
| `generate_bridge_code` | ETH/ERC20 bridging (L1↔L2, L1→L3, L3→L2) |
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

### M4: Orbit Chain Integration (5 tools)
| Tool | Purpose |
|------|---------|
| `generate_orbit_config` | Orbit chain configuration (prepareChainConfig, AnyTrust, custom gas tokens) |
| `generate_orbit_deployment` | Rollup/token bridge deployment (createRollup, createTokenBridge) |
| `generate_validator_setup` | Validator/batch poster management, AnyTrust DAC keysets |
| `ask_orbit` | Orbit chain Q&A (deployment, configuration, operations) |
| `orchestrate_orbit` | Full Orbit chain project scaffolding |

## Architecture Notes

### RAG Pipeline
1. **Query** → BM25 + Vector search (hybrid)
2. **Retrieve** → Top-k chunks from ChromaDB
3. **Rerank** → LLM-based relevance scoring
4. **Generate** → Context-augmented response via DeepSeek/OpenRouter

### M3 dApp Generation Pipeline
1. **Template Selection** → Based on contract_type and prompt keywords
2. **ABI Extraction** → `abi_extractor.py` parses #[public] impl blocks from lib.rs
3. **Compiler Verification** → `compiler_verifier.py` runs `cargo check` via Docker (up to 3 fix attempts with Stylus-specific error guidance)
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

### Rate Limits (`apps/web/src/lib/rateLimit.ts`)
- Per-day, per-key (or per-user for session auth) quotas backed by KV counters at `rl:{subject}:{category}:{YYYY-MM-DD}` with 48h TTL.
- Tiers (code-defined; only the name lives in `api_keys.rate_limit_tier`):
  - `free` (default): 30 chat / 100 tool per day
  - `pro`: 300 chat / 1000 tool per day
  - `unlimited`: 10K / 10K (effectively uncapped)
- Enforcement points: `/api/v1/chat/completions`, every `/api/v1/tools/*` route, and `tools/call` on `/mcp`. Admin requests (`AUTH_SECRET` Bearer) bypass.
- Headers on every response: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `X-RateLimit-Tier`. 429 also carries `Retry-After`.
- Tier management: `GET/PATCH /api/admin/rate-limits` (admin secret), surfaced in `/dashboard/admin` under the "Rate Limits" tab.

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
- **sol_interface! host argument** — `self.vm()` MUST be the FIRST argument when calling sol_interface! methods: `token.transfer(self.vm(), call, to, amount)?;` NOT `token.transfer(call, to, amount)?;`
- **sol! needs explicit import** — `use alloy_sol_types::{sol, SolError};` — sol! is NOT in prelude
- **sol! uses camelCase fields** — `tokenId` not `token_id`, `fromAddress` not `from_address` (Solidity convention)
- **Dynamic arrays** — `uint256[] items;` in sol_storage!, append with `.push(val)` for primitives, `.grow()` for structs. Never `.setter(len).unwrap()`
- **Borrow checker** — extract `.get()` values to local vars before combining with `.set()`. Never `self.field.setter(self.vm().something())`
- **B256 is FixedBytes, not Uint** — `B256::from_uint()` and `B256::from_limbs()` do NOT exist. B256 is `FixedBytes<32>`, not `Uint<256>`. Use `B256::from(value.to_be_bytes::<32>())` for U256→B256, `B256::from(U256::from_limbs([N, 0, 0, 0]).to_be_bytes::<32>())` for limbs, `B256::ZERO` for zero, `B256::with_last_byte(n)` for small values
- **Const U256** — `U256::from()` is NOT const-compatible. Use `U256::from_limbs([N, 0, 0, 0])` for const declarations. `U256::ZERO` is fine.
- **String mapping reads** — `mapping(uint256 => string)` — `.get(key)` returns `StorageGuard<StorageString>`, NOT `String`. Use `.getter(key).get_string()` to read. For writes: `.setter(key).set_str("value")`
- **abi_encode() on errors** — `.abi_encode()` is on the inner `sol!` error struct (SolError trait), NOT on the `#[derive(SolidityError)]` enum wrapper. WRONG: `MyErrors::NotOwner(NotOwner{...}).abi_encode()`. CORRECT: `NotOwner{caller, owner}.abi_encode()`
- **StorageString view functions** — When returning a `string` field from sol_storage! in a view function, ALWAYS call `.get_string()`: `pub fn name(&self) -> String { self.name.get_string() }`. NEVER return `self.name` directly — it is `StorageString`, not `String`. Do NOT use `.push_str()` on StorageString — extract first: `let s = self.name.get_string(); format!("{}{}", s, other)`
- **String imports in no_std** — `String` needs `use alloc::string::String;`. `.to_string()` also needs `use alloc::string::ToString;`. These are NOT in prelude in no_std.
- **No const in #[public] impl** — `pub const` inside `#[public] impl` is unsupported by the proc macro. Move constants to module level before the impl block.
- **sol! error/event type matching** — Solidity field types in sol! MUST match the Rust values passed. `address` → Address, `uint256` → U256. For comparison errors (InsufficientBalance, InsufficientStake), ALL value fields (have/want, available/required) should be `uint256`, NOT `address`.
- **ABI uses camelCase** — Stylus exports snake_case Rust fns as camelCase (`create_market` → `createMarket`). Frontend must use camelCase in `functionName`
- **View functions can't call external contracts** — `&self` view fns revert on cross-contract calls (unlike Solidity). Use `&mut self` or read from frontend
- **Arbitrum L2 gas** — MetaMask may underestimate `maxFeePerGas` on Arbitrum Sepolia. Add explicit gas overrides if "max fee per gas less than block base fee"
- **No Debug with SolidityError** — sol! generated types do NOT implement Debug. `#[derive(SolidityError, Debug)]` fails. Use `#[derive(SolidityError)]` only.
- **No underscore fns in #[public] impl** — `#[public]` macro strips leading underscores for ABI selectors, so `fn _grant_role` and `fn grant_role` produce the same selector ("unreachable pattern"). Put internal helpers in a separate `impl MyContract { ... }` block without `#[public]`.
- **address[] deref** — `*self.list.get(idx).unwrap()` on `address[]` returns `FixedBytes<20>`, not `Address`. Use `Address::from(*self.list.get(idx).unwrap())`.
- **String mapping writes** — For `mapping(... => string)`, `.setter(key)` returns `StorageGuardMut<StorageString>` — call `.set_str(val)` directly. WRONG: `.setter(key).setter().set_str(val)`. CORRECT: `.setter(key).set_str(val)`.
- **Nested struct writes** — For `mapping(uint256 => MyStruct)`, `.get(key)` returns immutable `StorageGuard<MyStruct>` — CANNOT call `.setter()` on its fields. Use `.setter(key)` for writes. WRONG: `self.roles.get(role).members.setter(account).set(true)`. CORRECT: `self.roles.setter(role).members.setter(account).set(true)`.
- **No function overloading** — Rust does not support function overloading. Two `fn` with the same name in the same impl block is a compile error (E0428). If you need variants, use different names (e.g. `check_role`, `check_role_with_admin`). Never define a function twice.

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

## Chat Endpoint (OpenAI-compatible)

`POST /api/v1/chat/completions` exposes a ReAct agent over 14 of the MCP tools as an OpenAI-compatible endpoint. Backed by `openai/gpt-oss-120b` via OpenRouter, supports streaming + non-streaming, native function calling, chain-of-thought passthrough via `reasoning_content`, and length-continuation across `finish_reason: "length"`. See `docs/api/chat-completions.md`. Playground UI at `/playground/chat`.

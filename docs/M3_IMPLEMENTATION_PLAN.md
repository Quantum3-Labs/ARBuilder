# M3: Full dApp Builder - Implementation Plan

## Overview

Transform ARBuilder from a Stylus contract generator into a **full-stack dApp builder** that generates production-ready applications from natural language prompts.

**Target**: Reduce dApp scaffolding time from 1-2 weeks → 2-4 hours

---

## Tech Stack (Per Proposal Requirements)

| Layer | Technology | Notes |
|-------|------------|-------|
| Smart Contracts | Stylus (Rust) | ✅ Already implemented in M1 |
| Backend | NestJS / Express | API routes, DB schemas, business logic |
| Frontend | Next.js / React | Components, state management, routing |
| Wallet | wagmi / viem / RainbowKit | Web3 connectivity |
| UI Styling | DaisyUI | Tailwind-based component library |
| Indexer | The Graph (Subgraphs) | Event tracking, GraphQL APIs |
| Oracle | Chainlink | Price feeds, data feeds, VRF |

---

## Data Sources to Scrape

### Phase 1: Backend & API Patterns

```python
DAPP_BACKEND_SOURCES = {
    "arbitrum_tutorials": [
        "https://github.com/OffchainLabs/arbitrum-tutorials",
    ],
    "web3_backend_patterns": [
        "https://github.com/thirdweb-dev/engine",  # Production Web3 backend
        "https://github.com/scaffold-eth/scaffold-eth-2",  # Full-stack reference
    ],
    "nestjs_web3": [
        "https://github.com/nickytonline/nest-js-web3-example",
        "https://github.com/AgoraDigital/backend-nest-dapp",
    ],
}
```

### Phase 2: Frontend & Wallet Integration

```python
DAPP_FRONTEND_SOURCES = {
    "wallet_libraries": [
        "https://github.com/wevm/wagmi",
        "https://github.com/wevm/viem",
        "https://github.com/rainbow-me/rainbowkit",
    ],
    "arbitrum_frontends": [
        "https://github.com/OffchainLabs/arbitrum-token-bridge",
        "https://github.com/ArbitrumFoundation/docs",
    ],
    "production_dapps": [
        "https://github.com/gmx-io/gmx-interface",  # Arbitrum-native DEX
        "https://github.com/camelotlabs/interface",  # Arbitrum DEX
    ],
    "ui_components": [
        "https://github.com/saadeghi/daisyui",
    ],
}
```

### Phase 3: Indexer & Subgraphs

```python
DAPP_INDEXER_SOURCES = {
    "the_graph": [
        "https://github.com/graphprotocol/graph-tooling",
        "https://github.com/graphprotocol/graph-node",
    ],
    "arbitrum_subgraphs": [
        "https://github.com/OffchainLabs/arbitrum-subgraphs",
        "https://github.com/messari/subgraphs",  # Production examples
    ],
}
```

### Phase 4: Oracle Integration

```python
DAPP_ORACLE_SOURCES = {
    "chainlink": [
        "https://github.com/smartcontractkit/chainlink",
        "https://github.com/smartcontractkit/hardhat-chainlink",
    ],
    "chainlink_examples": [
        "https://github.com/smartcontractkit/smart-contract-examples",
    ],
}
```

---

## New MCP Tools

### Tool 1: `generate_backend`

**Purpose**: Generate NestJS/Express backend with Web3 integration

**Input Schema**:
```json
{
  "prompt": "string - Description of the backend to generate",
  "framework": "nestjs | express (default: nestjs)",
  "features": ["auth", "database", "web3", "api"],
  "contract_abi": "string - Optional ABI to generate contract interactions",
  "database": "postgresql | mongodb | none (default: postgresql)"
}
```

**Output**:
- Project structure (src/, config/, etc.)
- API route handlers
- Database models/schemas
- Web3 service for contract interactions
- Environment configuration
- package.json with dependencies

### Tool 2: `generate_frontend`

**Purpose**: Generate Next.js frontend with wallet integration

**Input Schema**:
```json
{
  "prompt": "string - Description of the frontend to generate",
  "wallet_kit": "rainbowkit | connectkit | web3modal (default: rainbowkit)",
  "ui_library": "daisyui | shadcn | none (default: daisyui)",
  "features": ["wallet", "contract-read", "contract-write", "tx-history"],
  "contract_abi": "string - Optional ABI for typed hooks",
  "networks": ["arbitrum_one", "arbitrum_sepolia"]
}
```

**Output**:
- Next.js app structure
- Wallet provider setup
- Contract interaction hooks (wagmi)
- UI components (DaisyUI)
- Network configuration
- TypeScript types

### Tool 3: `generate_indexer`

**Purpose**: Generate subgraph for event indexing

**Input Schema**:
```json
{
  "prompt": "string - Description of what to index",
  "contract_address": "string - Deployed contract address",
  "contract_abi": "string - Contract ABI with events",
  "network": "arbitrum-one | arbitrum-sepolia",
  "entities": ["string - Entity names to track"]
}
```

**Output**:
- subgraph.yaml (manifest)
- schema.graphql (entities)
- src/mapping.ts (event handlers)
- package.json
- Deployment instructions

### Tool 4: `generate_dapp`

**Purpose**: Orchestrate full-stack dApp generation

**Input Schema**:
```json
{
  "prompt": "string - Full dApp description",
  "name": "string - Project name",
  "include": {
    "contract": true,
    "backend": true,
    "frontend": true,
    "indexer": false,
    "oracle": false
  },
  "contract_type": "erc20 | erc721 | erc1155 | custom"
}
```

**Output**:
- Complete monorepo structure
- All generated components
- Integration instructions
- Deployment guide

---

## MCP Resources to Add

### Resource 1: `dapp://workflows/fullstack`
Full-stack development workflow with integration steps

### Resource 2: `dapp://config/wagmi`
wagmi configuration templates for Arbitrum networks

### Resource 3: `dapp://config/subgraph`
Subgraph configuration for Arbitrum deployment

### Resource 4: `dapp://patterns/backend`
Common backend patterns for Web3 applications

### Resource 5: `dapp://patterns/frontend`
Common frontend patterns for dApps

---

## Implementation Phases

### Phase 1: Data Collection (3-4 days)
1. Update `scraper/config.py` with all M3 sources
2. Run scrapers for each category
3. Process and chunk new data
4. Generate embeddings and update ChromaDB

### Phase 2: Backend Tool (3-4 days)
1. Create `generate_backend.py` tool
2. Build NestJS generation templates
3. Build Express generation templates
4. Add Web3 service patterns
5. Test with sample prompts

### Phase 3: Frontend Tool (3-4 days)
1. Create `generate_frontend.py` tool
2. Build Next.js generation templates
3. Add wagmi/RainbowKit integration
4. Add DaisyUI component patterns
5. Test with sample prompts

### Phase 4: Indexer Tool (2-3 days)
1. Create `generate_indexer.py` tool
2. Build subgraph manifest templates
3. Build mapping file templates
4. Test with sample contracts

### Phase 5: Orchestration (2-3 days)
1. Create `generate_dapp.py` orchestration tool
2. Build integration logic
3. Add project structure generation
4. Test end-to-end generation

### Phase 6: Testing & Benchmarks (2-3 days)
1. Create 50+ benchmark prompts
2. Run accuracy tests
3. Measure response times
4. Document results

---

## Success Metrics (from Proposal)

| Metric | Target |
|--------|--------|
| Code generation accuracy | 85%+ |
| Contract generation time | <5 seconds |
| Full dApp generation time | <15 seconds |
| Benchmark tests | 50+ completed |

---

## File Structure

```
src/mcp/tools/
├── generate_stylus_code.py  # ✅ M1
├── generate_tests.py        # ✅ M1
├── get_stylus_context.py    # ✅ M1
├── ask_stylus.py            # ✅ M1
├── get_workflow.py          # ✅ M1
├── generate_backend.py      # 🆕 M3
├── generate_frontend.py     # 🆕 M3
├── generate_indexer.py      # 🆕 M3
└── generate_dapp.py         # 🆕 M3

src/mcp/resources/
├── stylus_resources.py      # ✅ M1
└── dapp_resources.py        # 🆕 M3

scraper/
├── config.py                # Update with M3 sources
└── ...
```

---

## Implementation Progress

### Phase 1: Data Collection ✅
- [x] Update `scraper/config.py` with M3 data sources
- [x] Run scrapers for each category (14 repos, 25,085 files)
- [x] Process and chunk new data (91,571 chunks)
- [ ] Generate embeddings and update ChromaDB (in progress)

### Phase 2: Backend Tool ✅
- [x] Create `generate_backend.py` tool
- [x] Build NestJS generation templates
- [x] Build Express generation templates
- [x] Add Web3 service patterns (viem integration)
- [x] Register in MCP server

### Phase 3: Frontend Tool ✅
- [x] Create `generate_frontend.py` tool
- [x] Build Next.js App Router templates
- [x] Add wagmi/RainbowKit integration
- [x] Add DaisyUI component patterns
- [x] Register in MCP server

### Phase 4: Indexer Tool ✅
- [x] Create `generate_indexer.py` tool
- [x] Build subgraph manifest templates
- [x] Build mapping file templates
- [x] Register in MCP server

### Phase 5: Orchestration ✅
- [x] Create `generate_dapp.py` orchestration tool
- [x] Build integration logic
- [x] Add project structure generation
- [x] Register in MCP server

### Phase 6: Testing & Benchmarks
- [ ] Create 50+ benchmark prompts
- [ ] Run accuracy tests
- [ ] Measure response times
- [ ] Document results

---

## Files Created

### New MCP Tools
- `src/mcp/tools/generate_backend.py` - NestJS/Express generation
- `src/mcp/tools/generate_frontend.py` - Next.js with wallet integration
- `src/mcp/tools/generate_indexer.py` - The Graph subgraph generation
- `src/mcp/tools/generate_dapp.py` - Full-stack orchestration

### Enhanced RAG Pipeline
- `src/preprocessing/semantic_chunker.py` - SOTA semantic chunking
- `src/embeddings/query_rewriter.py` - HyDE, multi-query, step-back
- `src/embeddings/advanced_retrieval.py` - Configurable retrieval modes

### Data Processing
- `scripts/ingest_m3.py` - Ingestion with resume support

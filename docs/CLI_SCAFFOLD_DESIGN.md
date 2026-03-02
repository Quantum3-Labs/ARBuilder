# CLI Scaffold Design

## Philosophy

ARBuilder's CLI follows a two-layer architecture:

```
CLI (deterministic, fast, no LLM)    MCP Server (AI-powered, contextual)
├── Scaffolds projects               ├── Implements custom features
├── Generates boilerplate            ├── RAG-powered code generation
├── Manages versions                 ├── Debugging and Q&A
└── Validates configuration          └── Test generation
```

**The CLI is `create-react-app`, not Copilot.** It generates working boilerplate from templates — no API calls, no AI, no network dependency. The MCP server handles everything that needs intelligence.

Inspired by `npm create cloudflare`, `cargo-generate`, and `forge init`.

## Installation & Usage

```bash
# Install globally
npm install -g arbbuilder

# Or use npx (no install)
npx arbbuilder init my-project

# Or use the shorter alias
npx arb init my-project
```

## Commands

### `arbbuilder init [name] [--template <template>]`

Scaffold a new project from a template.

```bash
# Interactive mode (prompts for template)
arbbuilder init my-project

# Direct template selection
arbbuilder init my-token --template stylus-erc20
arbbuilder init my-bridge --template sdk-bridge
arbbuilder init my-dapp --template full-dapp
arbbuilder init my-chain --template orbit-chain
```

**Interactive flow:**
```
$ arbbuilder init my-project
? What are you building?
  > Stylus Smart Contract (Rust/WASM)
    Arbitrum SDK Integration (TypeScript)
    Full-Stack dApp (Contract + Backend + Frontend)
    Orbit Chain Configuration

? Which contract template?
  > ERC20 Token
    ERC721 NFT
    Counter (minimal)
    Access Control (ownable)
    Blank (empty contract)

? SDK version?
  > 0.9.2 (recommended)
    0.9.0
    0.8.4

✓ Created my-project/
  ├── Cargo.toml (stylus-sdk 0.9.2)
  ├── src/lib.rs (ERC20 contract)
  ├── src/main.rs (ABI export)
  ├── rust-toolchain.toml (1.81)
  └── .arbbuilder.json (project config)

Next steps:
  cd my-project
  cargo build --release
  cargo test
```

### `arbbuilder add-contract [type]`

Add a Stylus contract to an existing project.

```bash
# Inside an existing project
arbbuilder add-contract erc20
arbbuilder add-contract erc721
arbbuilder add-contract staking
arbbuilder add-contract governance
```

**What it does:**
- Creates `contracts/<name>/` directory with `Cargo.toml` + `src/lib.rs`
- Adds to workspace `Cargo.toml` if it exists
- Pins SDK version to match the project's existing version
- Generates matching `src/main.rs` for ABI export

### `arbbuilder add-bridge [direction]`

Add bridging integration to an existing project.

```bash
arbbuilder add-bridge l1-to-l2        # ETH/ERC20 deposit
arbbuilder add-bridge l2-to-l1        # ETH/ERC20 withdrawal
arbbuilder add-bridge l1-to-l3        # L3 deposit via L2
arbbuilder add-bridge bidirectional   # Both directions
```

**What it does:**
- Creates `bridge/` directory with TypeScript scripts
- Adds `@arbitrum/sdk` dependency (version-pinned)
- Generates deposit/withdrawal scripts with env var setup
- Creates `.env.example` with required RPC URLs and keys

### `arbbuilder add-indexer [events]`

Add an event indexer/subgraph for Stylus contract events.

```bash
arbbuilder add-indexer Transfer,Approval     # Index specific events
arbbuilder add-indexer --from-abi            # Auto-detect events from ABI
```

**What it does:**
- Creates `indexer/` directory with subgraph manifest
- Generates `schema.graphql` from contract events
- Creates event handler TypeScript stubs
- Adds `package.json` with `@graphprotocol/graph-ts`

### `arbbuilder check`

Validate project configuration and dependencies.

```bash
$ arbbuilder check
✓ stylus-sdk 0.9.2 (up to date)
✓ alloy-primitives =0.8.20 (compatible)
✓ alloy-sol-types =0.8.20 (compatible)
✓ Rust 1.81 (compatible)
⚠ @arbitrum/sdk 4.0.1 → 4.0.4 available (minor update)
✓ Project compiles successfully
```

### `arbbuilder migrate [target-version]`

Migrate a project to a newer SDK version.

```bash
$ arbbuilder migrate 0.10.0
Migrating from stylus-sdk 0.9.2 → 0.10.0...

Changes required:
  1. Update Cargo.toml: stylus-sdk = "0.9.2" → "0.10.0"
  2. Update alloy-primitives pinning (if changed)
  3. Replace deprecated patterns (if any)

Apply changes? [y/N]
```

## Templates

### Category 1: Stylus Smart Contracts (`stylus-*`)

| Template ID | Description | Files | Based On |
|------------|-------------|-------|----------|
| `stylus-counter` | Minimal counter with storage | `Cargo.toml`, `src/lib.rs`, `src/main.rs` | stylus-hello-world |
| `stylus-erc20` | ERC20 token (no OZ dependency) | Same + events/errors | Internal template |
| `stylus-erc721` | ERC721 NFT (no OZ dependency) | Same + metadata | Internal template |
| `stylus-ownable` | Access control pattern | Same + ownership | Internal template |
| `stylus-blank` | Empty contract skeleton | Same (minimal) | — |

**All Stylus templates include:**
```
my-contract/
├── Cargo.toml              # Pinned dependencies
├── rust-toolchain.toml     # Rust 1.81
├── src/
│   ├── lib.rs              # Contract code with tests
│   └── main.rs             # ABI export binary
└── .arbbuilder.json        # Project metadata
```

### Category 2: Arbitrum SDK (`sdk-*`)

| Template ID | Description | Files |
|------------|-------------|-------|
| `sdk-bridge` | ETH/ERC20 bridging scripts | TypeScript + env setup |
| `sdk-messaging` | Cross-chain messaging | Retryable ticket scripts |
| `sdk-orbit-bridge` | Orbit chain bridging | L1→L2→L3 deposit/withdraw |

**SDK template structure:**
```
my-bridge/
├── package.json            # @arbitrum/sdk pinned
├── tsconfig.json
├── .env.example            # Required RPC URLs, keys
├── src/
│   ├── deposit.ts          # L1 → L2 deposit
│   ├── withdraw.ts         # L2 → L1 withdrawal
│   └── utils.ts            # Shared setup (providers, wallet)
└── .arbbuilder.json
```

### Category 3: Full-Stack dApp (`dapp-*`)

| Template ID | Description | Components |
|------------|-------------|------------|
| `dapp-token-launchpad` | Token launch platform | ERC20 + mint page + deploy |
| `dapp-nft-minting` | NFT minting site | ERC721 + mint UI + metadata |
| `dapp-defi-vault` | DeFi vault | Vault contract + deposit/withdraw UI |
| `dapp-dao-voting` | DAO governance | Governance contract + proposal UI |

**Full dApp template structure:**
```
my-dapp/
├── contracts/              # Stylus contracts (Rust workspace)
│   ├── Cargo.toml          # Workspace root
│   └── token/
│       ├── Cargo.toml
│       └── src/lib.rs
├── backend/                # Optional: API server
│   ├── package.json
│   └── src/index.ts
├── frontend/               # Next.js frontend
│   ├── package.json
│   ├── next.config.js
│   └── src/
│       ├── app/page.tsx
│       └── hooks/useContract.ts
├── scripts/
│   ├── deploy.ts           # Deploy contract to Arbitrum
│   └── bridge.ts           # Optional: bridging setup
├── .env.example
└── .arbbuilder.json
```

### Category 4: Orbit Chain (`orbit-*`)

| Template ID | Description | Components |
|------------|-------------|------------|
| `orbit-chain` | Orbit L3 chain config | SDK setup + gas token + bridge |

**Orbit template structure:**
```
my-chain/
├── package.json            # @arbitrum/orbit-sdk pinned
├── tsconfig.json
├── config/
│   └── chain-config.json   # Chain parameters
├── src/
│   ├── create-chain.ts     # Deploy Orbit chain
│   ├── configure-gas.ts    # Custom gas token setup
│   └── setup-bridge.ts     # Bridge configuration
├── .env.example
└── .arbbuilder.json
```

## Project Config (`.arbbuilder.json`)

Every scaffolded project gets a `.arbbuilder.json` at the root:

```json
{
  "version": "1.0.0",
  "template": "stylus-erc20",
  "created": "2026-02-10",
  "sdk": {
    "stylus-sdk": "0.9.2",
    "alloy-primitives": "=0.8.20",
    "alloy-sol-types": "=0.8.20"
  },
  "features": ["erc20", "events", "tests"],
  "contracts": ["token"],
  "network": {
    "default": "arbitrum-sepolia",
    "chainId": 421614,
    "rpc": "https://sepolia-rollup.arbitrum.io/rpc"
  }
}
```

This file is read by:
- `arbbuilder check` — to validate versions
- `arbbuilder migrate` — to know what to update
- `arbbuilder add-*` — to maintain version consistency
- MCP server — to understand project context when providing AI assistance

## Version-Aware Routing

The CLI detects the user's SDK version from their project and serves matching content:

```
User runs: arbbuilder add-contract erc20
  1. Read .arbbuilder.json → sdk.stylus-sdk = "0.9.2"
  2. Select template for 0.9.x
  3. Generate code with correct patterns (#[public] vs #[external])
  4. Pin matching dependency versions
```

**Fallback detection** (no `.arbbuilder.json`):
1. Check `Cargo.toml` for `stylus-sdk` version
2. Check `package.json` for `@arbitrum/sdk` version
3. Default to latest version

**Version compatibility matrix** is loaded from `shared/stylus-versions.json`:
- Maps SDK version → dependency pins, code patterns, breaking changes
- Used by both CLI (template selection) and MCP server (code generation)

## Template Versioning Strategy

Templates are **embedded in the CLI package**, not fetched remotely:

```
cli/
├── package.json
├── src/
│   ├── index.ts            # CLI entry point
│   ├── commands/
│   │   ├── init.ts
│   │   ├── add-contract.ts
│   │   ├── add-bridge.ts
│   │   ├── add-indexer.ts
│   │   ├── check.ts
│   │   └── migrate.ts
│   └── templates/
│       ├── stylus/         # Stylus templates (Handlebars/EJS)
│       ├── sdk/            # SDK templates
│       ├── dapp/           # Full dApp templates
│       └── orbit/          # Orbit templates
└── shared/
    └── stylus-versions.json  # Symlink to repo root
```

**Why embedded, not remote:**
- Works offline
- No API dependency for scaffolding
- Deterministic output (same CLI version = same scaffold)
- Version-locked templates (CLI v1.2.0 always generates the same code)

**Template update flow:**
1. SDK releases new version
2. We update templates + `stylus-versions.json`
3. Publish new CLI version
4. Users run `npm update -g arbbuilder`

## Migration Workflow

When a new SDK version is released (e.g., 0.10.0):

```bash
# 1. Monitor detects new version
python scripts/maintain_sources.py monitor

# 2. Update shared/stylus-versions.json with new version entry
# 3. Update CLI templates for new version
# 4. Test: scaffold → compile → test → deploy

# 5. Publish CLI update
cd cli && npm version minor && npm publish

# 6. Users migrate existing projects
arbbuilder migrate 0.10.0
```

The `migrate` command uses `shared/stylus-versions.json` to:
- Know what dependency pins changed between versions
- Detect deprecated patterns to replace
- Warn about breaking changes

## MCP Server Integration

The MCP server can invoke CLI commands for scaffolding, then layer on AI:

```
User (in IDE): "Create a token launchpad dApp"

MCP orchestrate_dapp tool:
  1. Call CLI: arbbuilder init my-launchpad --template dapp-token-launchpad
  2. RAG: Retrieve relevant Stylus ERC20 patterns
  3. AI: Customize the contract (add custom mint logic, vesting, etc.)
  4. AI: Generate frontend components for mint page
  5. AI: Generate deployment scripts
```

The split is intentional:
- **CLI** handles what can be deterministic (file structure, dependencies, boilerplate)
- **MCP** handles what needs intelligence (custom logic, debugging, explanations)

## Implementation Plan

### Phase 1: Core Scaffold (MVP)
- [ ] `init` command with 5 Stylus templates
- [ ] `.arbbuilder.json` project config
- [ ] `check` command
- [ ] Version detection from `Cargo.toml`

### Phase 2: SDK + Full dApp
- [ ] `init` with SDK templates (bridge, messaging)
- [ ] `init` with dApp templates (token launchpad, NFT mint)
- [ ] `add-contract` command
- [ ] `add-bridge` command

### Phase 3: Advanced
- [ ] `add-indexer` command
- [ ] `migrate` command
- [ ] Orbit templates
- [ ] MCP server integration (call CLI from tools)

### Phase 4: Polish
- [ ] Interactive prompts (inquirer.js)
- [ ] `--dry-run` flag for all commands
- [ ] Colorized output
- [ ] `arbbuilder doctor` (environment check: Rust, cargo-stylus, node)

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | TypeScript (Node.js) | npm ecosystem, matches SDK tooling |
| Template engine | Handlebars | Simple, logic-less, well-known |
| CLI framework | Commander.js | Lightweight, standard |
| Prompts | Inquirer.js | Rich interactive prompts |
| Package name | `arbbuilder` | Matches project name |
| Templates | Embedded | Offline-first, deterministic |
| Config format | JSON | Universal, easy to parse |

## File Ownership

Per the branching strategy, CLI development happens on `feat/cli-scaffold`:

| File | Owner |
|------|-------|
| `cli/` (new directory) | Track 3: CLI |
| `src/templates/` updates | Track 3: CLI |
| `shared/stylus-versions.json` | Shared (merge-safe, additive) |

No overlap with Track 1 (M3 + RAG quality) or Track 2 (data curation).

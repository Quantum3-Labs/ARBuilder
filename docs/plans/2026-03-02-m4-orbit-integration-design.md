# M4 Design: Orbit Chain Integration

**Date:** 2026-03-02
**Status:** Approved
**Budget:** 32,000 MYR (SOW Deliverable #4)
**Deadline:** 02/06/2026

## Context

M1-M3 delivered Stylus contract generation, Arbitrum SDK bridging/messaging, and full dApp scaffolding. M4 extends ARBuilder to support Orbit chain deployment — configuring, deploying, and managing custom L3 chains on Arbitrum.

### What Already Exists
- Orbit SDK repo (`OffchainLabs_arbitrum-orbit-sdk` v4.0.4) fully ingested in RAG
- L1-L3 bridging templates in M2 tools (EthL1L3Bridger, Erc20L1L3Bridger)
- L2-L3 messaging templates in M2 tools (retryable tickets, ArbSys)
- `ask_bridging` handles basic Orbit/L3 Q&A
- CLI scaffold pattern proven in M3 (setup.sh scaffold-first, backfill)

### What's Missing
- No dedicated MCP tools for Orbit chain deployment
- No templates for createRollup, createTokenBridge, validator management
- No Orbit-specific MCP resources/rules
- No chain configuration or node config generation
- No orchestrator for full Orbit chain scaffold

## Approach: Template-First with LLM Customization

Same proven pattern as M2/M3:
1. **Curated templates** for each Orbit SDK operation (createRollup, createTokenBridge, validators)
2. **CLI scaffold** where available; `npm init` + template injection otherwise
3. **LLM layer** for Q&A (`ask_orbit`) and customizing templates based on user prompts
4. **RAG** for Orbit SDK context retrieval

## New MCP Tools (5 tools)

### 1. `generate_orbit_config`
Generate chain configuration for Orbit L3 deployment.

**Input:**
- `prompt` (string, required) — Description of chain requirements
- `chain_id` (number) — L3 chain ID
- `owner` (string) — Initial chain owner address
- `is_anytrust` (boolean, default false) — AnyTrust vs Rollup mode
- `native_token` (string) — Custom gas token address (0x0 for ETH)
- `parent_chain` (enum: arbitrum-one, arbitrum-sepolia, ethereum-mainnet, ethereum-sepolia)

**Output:**
- `config/chain-config.json` — ChainConfig from `prepareChainConfig()`
- `scripts/prepare-config.ts` — TypeScript script that calls `prepareChainConfig()` + `createRollupPrepareDeploymentParamsConfig()`
- `config/deployment-params.json` — Default deployment parameters
- `.env.example` — Required environment variables

**Templates:** CHAIN_CONFIG_TEMPLATE, ANYTRUST_CONFIG_TEMPLATE, CUSTOM_GAS_TOKEN_CONFIG_TEMPLATE

### 2. `generate_orbit_deployment`
Generate deployment scripts for creating the Orbit chain and token bridge.

**Input:**
- `prompt` (string, required) — Description of deployment requirements
- `deployment_type` (enum: rollup, token_bridge, full) — What to deploy
- `chain_config` (string) — JSON chain config (or use defaults)
- `validators` (array of strings) — Initial validator addresses
- `batch_posters` (array of strings) — Batch poster addresses
- `native_token` (string) — Custom gas token address
- `parent_chain` (enum)
- `rollup_version` (enum: v2.1, v3.1, default v3.1)

**Output:**
- `scripts/deploy-rollup.ts` — `createRollup()` script
- `scripts/deploy-token-bridge.ts` — `createTokenBridge()` script
- `scripts/check-deployment.ts` — Verify deployment + extract CoreContracts
- `.env.example` — DEPLOYER_PRIVATE_KEY, PARENT_RPC_URL, etc.

**Templates:** DEPLOY_ROLLUP_V31_TEMPLATE, DEPLOY_ROLLUP_V21_TEMPLATE, DEPLOY_TOKEN_BRIDGE_TEMPLATE, DEPLOY_FULL_TEMPLATE

### 3. `generate_validator_setup`
Generate validator and batch poster management scripts.

**Input:**
- `prompt` (string, required)
- `action` (enum: list, add, remove) — Management action
- `target` (enum: validator, batch_poster, keyset) — What to manage
- `addresses` (array of strings) — Addresses to add/remove
- `rollup_address` (string) — Rollup contract address
- `sequencer_inbox` (string) — SequencerInbox address

**Output:**
- `scripts/manage-validators.ts` — getValidators/setValidator scripts
- `scripts/manage-batch-posters.ts` — getBatchPosters/setIsBatchPoster scripts
- `scripts/manage-keysets.ts` — getKeysets/setValidKeyset scripts (AnyTrust)

**Templates:** LIST_VALIDATORS_TEMPLATE, ADD_VALIDATOR_TEMPLATE, REMOVE_VALIDATOR_TEMPLATE, LIST_BATCH_POSTERS_TEMPLATE, MANAGE_KEYSET_TEMPLATE

### 4. `ask_orbit`
Q&A tool for Orbit chain questions, powered by RAG + LLM.

**Input:**
- `question` (string, required)

**Output:**
- Answer with code examples, referencing Orbit SDK docs
- Knowledge base covers: chain config, deployment, validators, gas tokens, AnyTrust, migration, monitoring

**Implementation:** Same pattern as `ask_stylus` / `ask_bridging`:
- Built-in knowledge base for common Orbit patterns
- RAG context from ingested Orbit SDK docs/examples
- LLM generates answer with code snippets
- Post-processing validates code references

### 5. `orchestrate_orbit`
Full Orbit chain project scaffold (analogous to M3's `orchestrate_dapp`).

**Input:**
- `prompt` (string, required) — Description of the chain
- `chain_name` (string) — Chain name (used for project directory)
- `chain_id` (number)
- `is_anytrust` (boolean, default false)
- `native_token` (string) — Custom gas token or "eth"
- `parent_chain` (enum)
- `validators` (array of strings)
- `batch_posters` (array of strings)

**Output:** Complete project scaffold:
```
{chain_name}/
├── package.json                    # @arbitrum/orbit-sdk, viem
├── tsconfig.json
├── .env.example                    # All required env vars
├── config/
│   ├── chain-config.json           # ChainConfig
│   └── node-config.json            # NodeConfig for Nitro
├── scripts/
│   ├── 1-prepare-config.ts         # prepareChainConfig()
│   ├── 2-deploy-rollup.ts          # createRollup()
│   ├── 3-deploy-token-bridge.ts    # createTokenBridge()
│   ├── 4-setup-validators.ts       # Validator management
│   ├── 5-configure-node.ts         # prepareNodeConfig()
│   └── 6-verify-deployment.ts      # Health check script
├── setup.sh                        # npm install + env validation
├── deploy.sh                       # Run scripts 1-4 in order
└── README.md                       # Usage instructions
```

## Templates

New file: `src/templates/orbit_templates.py`

### Template Categories

1. **Chain Configuration** — `prepareChainConfig()` with Rollup and AnyTrust variants
2. **Rollup Deployment** — `createRollup()` for v2.1 and v3.1
3. **Token Bridge** — `createTokenBridge()` with WETH gateway
4. **Custom Gas Token** — ERC20 approval + fee token setup
5. **Validator Management** — get/set validators, batch posters
6. **Governance** — UpgradeExecutor operations
7. **Keyset Management** — AnyTrust DAC keyset operations
8. **Node Configuration** — Nitro node config JSON generation
9. **Orchestration** — Full project package.json, setup.sh, deploy.sh

### Template Structure
Each template is a parameterized TypeScript string with placeholders:
- `{chain_id}`, `{owner}`, `{parent_chain_rpc}`, `{native_token}`
- `{validators_array}`, `{batch_posters_array}`
- `{rollup_address}`, `{sequencer_inbox}`
- `{is_anytrust}`, `{arbos_version}`

## Knowledge Base

### New MCP Resource: `orbit_rules`
Key constraints and patterns for Orbit chain development:

- Parent chain must be Ethereum or Arbitrum (L2 or L3)
- `InitialChainOwner` is required and should be a multisig in production
- AnyTrust mode requires DAC committee + keyset configuration
- Custom gas tokens must be ERC20 on parent chain; approve RollupCreator before createRollup
- v3.1 supports multiple batch posters; v2.1 only supports one
- Token bridge deployment requires both parent and orbit chain RPC
- Validators need ETH on parent chain for staking
- Node config is separate from chain config (Nitro node vs on-chain state)

### RAG Sources (add to sources.json)
```json
[
  { "url": "https://docs.arbitrum.io/launch-orbit-chain/orbit-gentle-introduction", "milestone": "m4", "category": "orbit" },
  { "url": "https://docs.arbitrum.io/launch-orbit-chain/orbit-quickstart", "milestone": "m4", "category": "orbit" },
  { "url": "https://docs.arbitrum.io/launch-orbit-chain/how-tos/orbit-sdk-deploying-rollup-chain", "milestone": "m4", "category": "orbit" },
  { "url": "https://docs.arbitrum.io/launch-orbit-chain/how-tos/orbit-sdk-deploying-anytrust-chain", "milestone": "m4", "category": "orbit" },
  { "url": "https://docs.arbitrum.io/launch-orbit-chain/how-tos/orbit-sdk-deploying-custom-gas-token-chain", "milestone": "m4", "category": "orbit" },
  { "url": "https://docs.arbitrum.io/launch-orbit-chain/how-tos/orbit-sdk-configuring-chain-parameters", "milestone": "m4", "category": "orbit" }
]
```

## API Routes (CF Worker)

New files in `apps/web/src/app/api/v1/tools/`:
- `orbit-config/route.ts` — Chain config generation
- `orbit-deploy/route.ts` — Deployment script generation
- `orbit-validator/route.ts` — Validator management
- `ask-orbit/route.ts` — Orbit Q&A
- `orchestrate-orbit/route.ts` — Full scaffold

Each route follows the existing pattern: validate input → call tool function → return JSON response.

## Files Summary

### New Files (Python MCP)
| File | Purpose |
|------|---------|
| `src/mcp/tools/generate_orbit_config.py` | Chain configuration tool |
| `src/mcp/tools/generate_orbit_deployment.py` | Deployment script tool |
| `src/mcp/tools/generate_validator_setup.py` | Validator management tool |
| `src/mcp/tools/ask_orbit.py` | Orbit Q&A tool |
| `src/mcp/tools/orchestrate_orbit.py` | Full scaffold orchestrator |
| `src/templates/orbit_templates.py` | All Orbit templates |
| `src/mcp/resources/orbit_rules.py` | Orbit knowledge resource |

### New Files (TS CF Worker)
| File | Purpose |
|------|---------|
| `apps/web/src/lib/tools/generateOrbitConfig.ts` | TS chain config tool |
| `apps/web/src/lib/tools/generateOrbitDeployment.ts` | TS deployment tool |
| `apps/web/src/lib/tools/generateValidatorSetup.ts` | TS validator tool |
| `apps/web/src/lib/tools/askOrbit.ts` | TS Orbit Q&A tool |
| `apps/web/src/lib/tools/orchestrateOrbit.ts` | TS orchestrator |
| `apps/web/src/app/api/v1/tools/orbit-config/route.ts` | API route |
| `apps/web/src/app/api/v1/tools/orbit-deploy/route.ts` | API route |
| `apps/web/src/app/api/v1/tools/orbit-validator/route.ts` | API route |
| `apps/web/src/app/api/v1/tools/ask-orbit/route.ts` | API route |
| `apps/web/src/app/api/v1/tools/orchestrate-orbit/route.ts` | API route |

### Modified Files
| File | Changes |
|------|---------|
| `src/mcp/tools/__init__.py` | Register 5 new tools |
| `src/mcp/server.py` | Register 5 new tools |
| `sources.json` | Add M4 Orbit documentation sources |
| `CLAUDE.md` | Add M4 tools reference table |
| `README.md` | Update with M4 documentation |
| `apps/web/src/app/playground/page.tsx` | Add Orbit tools to playground UI |

## Testing

10+ test scenarios across categories:
1. **Chain config** — Rollup mode, AnyTrust mode, custom gas token
2. **Deployment** — v2.1 rollup, v3.1 rollup, token bridge, full deployment
3. **Validators** — List, add, remove validators and batch posters
4. **Q&A** — Orbit concepts, deployment guidance, troubleshooting
5. **Orchestration** — Full project scaffold with various configurations

Success criteria: Same benchmarking framework as M1-M3 (pass/fail per test).

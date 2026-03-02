# M4 Orbit Chain Integration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add 5 new MCP tools for Orbit chain deployment — config generation, chain deployment, validator management, Q&A, and full orchestration — following the proven M2/M3 template-based pattern.

**Architecture:** Template-first approach with LLM customization. Each tool has curated TypeScript templates for Orbit SDK operations (createRollup, createTokenBridge, etc.), parameterized with user input. Python MCP tools + TS CF Worker equivalents. RAG provides Orbit SDK context for the Q&A tool.

**Tech Stack:** `@arbitrum/orbit-sdk` v4.0.4, `viem`, Python MCP server, CF Workers (Next.js), OpenRouter LLM

---

## Phase 1: Templates Foundation

### Task 1: Create Orbit template data structures

**Files:**
- Create: `src/templates/orbit_templates.py`

**Step 1: Create orbit_templates.py with OrbitTemplate dataclass and 9 templates**

The file follows the same pattern as `oracle_templates.py` (line 17 `OracleTemplate` dataclass).

```python
"""
Orbit chain templates for L3 deployment.

Templates:
- Chain Config: prepareChainConfig() for Rollup and AnyTrust modes
- Rollup Deployment: createRollup() v3.1 and v2.1
- Token Bridge: createTokenBridge() deployment
- Custom Gas Token: ERC20 fee token setup
- Validator Management: get/set validators and batch posters
- Governance: UpgradeExecutor operations
- Node Config: Nitro node configuration
- AnyTrust Config: DAC committee + keyset
- Orchestration: Full project scaffold (package.json, setup.sh, deploy.sh)
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OrbitTemplate:
    """A curated Orbit chain template."""

    name: str
    description: str
    template_type: str  # chain_config | deployment | token_bridge | validator | governance | node_config | anytrust | orchestration
    files: dict[str, str]  # filename -> content
    dependencies: dict[str, str] = field(default_factory=dict)
    env_vars: list[str] = field(default_factory=list)
```

Then add 9 template constants:
1. `CHAIN_CONFIG_TEMPLATE` — TypeScript calling `prepareChainConfig()` with `{chain_id}`, `{owner}`, `{is_anytrust}` placeholders
2. `DEPLOY_ROLLUP_TEMPLATE` — TypeScript calling `createRollup()` with validators, batch posters, native token
3. `DEPLOY_TOKEN_BRIDGE_TEMPLATE` — TypeScript calling `createTokenBridge()`
4. `CUSTOM_GAS_TOKEN_TEMPLATE` — Token approval + rollup creation with custom fee token
5. `VALIDATOR_MANAGEMENT_TEMPLATE` — getValidators, getBatchPosters, setValidator
6. `GOVERNANCE_TEMPLATE` — UpgradeExecutor operations
7. `NODE_CONFIG_TEMPLATE` — prepareNodeConfig() + JSON output
8. `ANYTRUST_CONFIG_TEMPLATE` — DAC keyset management
9. `ORCHESTRATION_TEMPLATE` — package.json, tsconfig.json, setup.sh, deploy.sh, .env.example

Each template's `files` dict maps filename to parameterized TypeScript code using `@arbitrum/orbit-sdk` APIs from the SDK (see design doc for API signatures).

Key dependencies for all templates:
```python
dependencies = {
    "@arbitrum/orbit-sdk": "^0.27.0",
    "viem": "^2.23.0",
    "dotenv": "^16.4.0",
}
```

Key env vars:
```python
env_vars = [
    "DEPLOYER_PRIVATE_KEY",
    "PARENT_CHAIN_RPC",
    "ORBIT_CHAIN_RPC",
]
```

Template helper functions:
```python
def get_orbit_template(name: str) -> Optional[OrbitTemplate]:
    """Get template by name."""

def select_orbit_template(prompt: str) -> OrbitTemplate:
    """Select best template from prompt keywords."""

ORBIT_TEMPLATES: dict[str, OrbitTemplate] = { ... }
```

**Step 2: Verify import works**

Run: `python -c "from src.templates.orbit_templates import ORBIT_TEMPLATES; print(len(ORBIT_TEMPLATES))"`
Expected: `9`

**Step 3: Commit**

```bash
git add src/templates/orbit_templates.py
git commit -m "feat(m4): add Orbit chain templates for chain config, deployment, validators"
```

---

## Phase 2: Python MCP Tools (5 tools)

### Task 2: Create generate_orbit_config tool (Python)

**Files:**
- Create: `src/mcp/tools/generate_orbit_config.py`

**Step 1: Create the tool**

Follow `generate_indexer.py` pattern (inherits `BaseTool`, has `name`, `description`, `input_schema`, `execute()`).

```python
"""
Generate Orbit chain configuration.

Generates chain configuration using prepareChainConfig() from the Orbit SDK.
Supports Rollup and AnyTrust modes, custom gas tokens, and configurable parameters.
"""

from typing import Any, Optional

from ...templates.orbit_templates import (
    OrbitTemplate,
    get_orbit_template,
    select_orbit_template,
)
from .base import BaseTool


class GenerateOrbitConfigTool(BaseTool):
    """Generate Orbit chain configuration."""

    name = "generate_orbit_config"
    description = """Generate chain configuration for deploying an Orbit L3 chain.

Supports:
- Rollup mode (fraud proofs)
- AnyTrust mode (data availability committee)
- Custom gas tokens (ERC20 fee tokens)
- Configurable chain parameters (chainId, owner, validators)

Output includes TypeScript scripts using @arbitrum/orbit-sdk."""

    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Description of chain requirements"},
            "chain_id": {"type": "integer", "description": "L3 chain ID"},
            "owner": {"type": "string", "description": "Initial chain owner address"},
            "is_anytrust": {"type": "boolean", "description": "Use AnyTrust mode", "default": False},
            "native_token": {"type": "string", "description": "Custom gas token address (0x0 for ETH)"},
            "parent_chain": {
                "type": "string",
                "enum": ["arbitrum-one", "arbitrum-sepolia", "ethereum-mainnet", "ethereum-sepolia"],
                "description": "Parent chain",
                "default": "arbitrum-sepolia",
            },
        },
        "required": ["prompt"],
    }

    def execute(self, **kwargs) -> dict[str, Any]:
        prompt = kwargs.get("prompt", "")
        chain_id = kwargs.get("chain_id", 412346)
        owner = kwargs.get("owner", "0x0000000000000000000000000000000000000000")
        is_anytrust = kwargs.get("is_anytrust", False)
        native_token = kwargs.get("native_token", "0x0000000000000000000000000000000000000000")
        parent_chain = kwargs.get("parent_chain", "arbitrum-sepolia")

        if not prompt:
            return {"error": "prompt is required"}

        # Select template
        template_name = "anytrust_config" if is_anytrust else "chain_config"
        if native_token and native_token != "0x0000000000000000000000000000000000000000":
            template_name = "custom_gas_token"

        template = get_orbit_template(template_name)
        if not template:
            template = select_orbit_template(prompt)

        # Customize template
        files = self._customize_template(template, chain_id, owner, is_anytrust, native_token, parent_chain)

        return {
            "template_used": template.name,
            "files": files,
            "dependencies": template.dependencies,
            "env_vars": template.env_vars,
            "setup_instructions": [
                "1. npm install",
                "2. Copy .env.example to .env and fill in values",
                "3. Run: npx tsx scripts/prepare-config.ts",
            ],
        }

    def _customize_template(self, template, chain_id, owner, is_anytrust, native_token, parent_chain):
        files = dict(template.files)
        for filename, content in files.items():
            content = content.replace("{chain_id}", str(chain_id))
            content = content.replace("{owner}", owner)
            content = content.replace("{is_anytrust}", str(is_anytrust).lower())
            content = content.replace("{native_token}", native_token)
            content = content.replace("{parent_chain_rpc}", self._get_rpc_url(parent_chain))
            files[filename] = content
        return files

    def _get_rpc_url(self, parent_chain):
        rpc_map = {
            "arbitrum-one": "https://arb1.arbitrum.io/rpc",
            "arbitrum-sepolia": "https://sepolia-rollup.arbitrum.io/rpc",
            "ethereum-mainnet": "https://eth.llamarpc.com",
            "ethereum-sepolia": "https://rpc.sepolia.org",
        }
        return rpc_map.get(parent_chain, "https://sepolia-rollup.arbitrum.io/rpc")
```

**Step 2: Verify import**

Run: `python -c "from src.mcp.tools.generate_orbit_config import GenerateOrbitConfigTool; print('OK')"`

**Step 3: Commit**

```bash
git add src/mcp/tools/generate_orbit_config.py
git commit -m "feat(m4): add generate_orbit_config MCP tool"
```

### Task 3: Create generate_orbit_deployment tool (Python)

**Files:**
- Create: `src/mcp/tools/generate_orbit_deployment.py`

Same pattern as Task 2. Tool generates `createRollup()` and `createTokenBridge()` scripts.

Key input params: `prompt`, `deployment_type` (rollup|token_bridge|full), `validators[]`, `batch_posters[]`, `native_token`, `parent_chain`, `rollup_version` (v2.1|v3.1).

`execute()` selects DEPLOY_ROLLUP_TEMPLATE or DEPLOY_TOKEN_BRIDGE_TEMPLATE or both, customizes with user params (validators array, batch posters, native token address), returns files dict.

**Commit message:** `feat(m4): add generate_orbit_deployment MCP tool`

### Task 4: Create generate_validator_setup tool (Python)

**Files:**
- Create: `src/mcp/tools/generate_validator_setup.py`

Key input params: `prompt`, `action` (list|add|remove), `target` (validator|batch_poster|keyset), `addresses[]`, `rollup_address`, `sequencer_inbox`.

`execute()` selects appropriate template section from VALIDATOR_MANAGEMENT_TEMPLATE, substitutes addresses and contract addresses.

**Commit message:** `feat(m4): add generate_validator_setup MCP tool`

### Task 5: Create ask_orbit tool (Python)

**Files:**
- Create: `src/mcp/tools/ask_orbit.py`

Follow `ask_bridging.py` pattern exactly:
1. Define `ORBIT_KNOWLEDGE` dict with common Q&A topics (chain_config, deployment, validators, gas_tokens, anytrust, node_setup, governance, migration)
2. `execute()`: detect topic from question keywords → build context from knowledge base → call `_call_llm()` with system prompt + context → return answer

System prompt includes Orbit SDK rules from design doc (parent chain requirements, AnyTrust DAC, custom gas token approval, v2.1 vs v3.1 differences).

**Commit message:** `feat(m4): add ask_orbit Q&A MCP tool`

### Task 6: Create orchestrate_orbit tool (Python)

**Files:**
- Create: `src/mcp/tools/orchestrate_orbit.py`

Follow `orchestrate_dapp.py` pattern. Coordinates all other orbit tools:
1. Call `generate_orbit_config` → chain config files
2. Call `generate_orbit_deployment` → deployment scripts
3. Call `generate_validator_setup` → validator management scripts
4. Generate orchestration files: package.json, tsconfig.json, .env.example, setup.sh, deploy.sh, README.md
5. Merge all files into single project scaffold

Key input: `prompt`, `chain_name`, `chain_id`, `is_anytrust`, `native_token`, `parent_chain`, `validators[]`, `batch_posters[]`.

**Commit message:** `feat(m4): add orchestrate_orbit full scaffold MCP tool`

### Task 7: Register all 5 tools in MCP server

**Files:**
- Modify: `src/mcp/tools/__init__.py`
- Modify: `src/mcp/server.py`

**Step 1: Update `__init__.py`**

Add imports and `__all__` entries for:
- `GenerateOrbitConfigTool`
- `GenerateOrbitDeploymentTool`
- `GenerateValidatorSetupTool`
- `AskOrbitTool`
- `OrchestrateOrbitTool`

Add M4 comment block.

**Step 2: Update `server.py`**

Add 5 new TOOL_DEFINITIONS entries with inputSchema for each tool.
Add tool instances to the handler dispatch.

**Step 3: Verify**

Run: `python -c "from src.mcp.tools import AskOrbitTool, GenerateOrbitConfigTool, GenerateOrbitDeploymentTool, GenerateValidatorSetupTool, OrchestrateOrbitTool; print('All 5 M4 tools OK')"`

**Step 4: Commit**

```bash
git add src/mcp/tools/__init__.py src/mcp/server.py
git commit -m "feat(m4): register 5 Orbit tools in MCP server"
```

---

## Phase 3: Orbit Knowledge Resource

### Task 8: Create orbit_rules MCP resource

**Files:**
- Create: `src/mcp/resources/orbit_rules.py`
- Modify: `src/mcp/resources/__init__.py` (if barrel exists)

Follow existing resources pattern. Define key Orbit chain rules:

1. Parent chain constraints (must be Ethereum or Arbitrum)
2. AnyTrust vs Rollup mode differences
3. Custom gas token requirements (ERC20 approval before createRollup)
4. Validator staking requirements
5. v2.1 vs v3.1 RollupCreator differences
6. Token bridge deployment order (after rollup, before node start)
7. Node config vs chain config distinction
8. Common deployment errors and solutions

**Commit message:** `feat(m4): add orbit_rules MCP resource`

---

## Phase 4: TypeScript CF Worker Tools (5 tools)

### Task 9: Create TS generateOrbitConfig tool

**Files:**
- Create: `apps/web/src/lib/tools/generateOrbitConfig.ts`

Follow `generateBridgeCode.ts` pattern:
- Define input/output interfaces
- Define template constants (same templates as Python, ported to TS)
- Export `generateOrbitConfig()` function
- Template selection logic + parameter substitution

**Commit message:** `feat(m4): add TS generateOrbitConfig tool`

### Task 10: Create TS generateOrbitDeployment tool

**Files:**
- Create: `apps/web/src/lib/tools/generateOrbitDeployment.ts`

Same pattern. Templates for createRollup() and createTokenBridge().

**Commit message:** `feat(m4): add TS generateOrbitDeployment tool`

### Task 11: Create TS generateValidatorSetup tool

**Files:**
- Create: `apps/web/src/lib/tools/generateValidatorSetup.ts`

Same pattern. Templates for validator/batch poster management.

**Commit message:** `feat(m4): add TS generateValidatorSetup tool`

### Task 12: Create TS askOrbit tool

**Files:**
- Create: `apps/web/src/lib/tools/askOrbit.ts`

Follow `askBridging.ts` pattern:
- `ORBIT_KNOWLEDGE` dict
- `askOrbit()` function: detect topic → build context → call `answerOrbitQuestion()` from openrouter → return answer
- Add `answerOrbitQuestion()` to `apps/web/src/lib/openrouter.ts`

**Commit message:** `feat(m4): add TS askOrbit Q&A tool`

### Task 13: Create TS orchestrateOrbit tool

**Files:**
- Create: `apps/web/src/lib/tools/orchestrateOrbit.ts`

Coordinates all TS orbit tools into a full project scaffold.

**Commit message:** `feat(m4): add TS orchestrateOrbit scaffold tool`

---

## Phase 5: API Routes

### Task 14: Create 5 API routes for Orbit tools

**Files:**
- Create: `apps/web/src/app/api/v1/tools/orbit-config/route.ts`
- Create: `apps/web/src/app/api/v1/tools/orbit-deploy/route.ts`
- Create: `apps/web/src/app/api/v1/tools/orbit-validator/route.ts`
- Create: `apps/web/src/app/api/v1/tools/ask-orbit/route.ts`
- Create: `apps/web/src/app/api/v1/tools/orchestrate-orbit/route.ts`

Each follows `bridge/route.ts` pattern:
```typescript
import { NextRequest, NextResponse } from "next/server";
import { generateOrbitConfig } from "@/lib/tools/generateOrbitConfig";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateRequest } from "@/lib/auth/validateRequest";

export async function POST(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();
    const auth = await validateRequest(request, env.DB, env.AUTH_SECRET);
    if (!auth.success) return auth.response;

    const body = await request.json();
    // validate required fields...
    const result = generateOrbitConfig(body);
    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return NextResponse.json({ error: `Tool error: ${message}` }, { status: 500 });
  }
}
```

**Commit message:** `feat(m4): add 5 API routes for Orbit tools`

---

## Phase 6: RAG Sources + Documentation

### Task 15: Add Orbit documentation sources

**Files:**
- Modify: `sources.json`

Add M4 Orbit documentation URLs (see design doc for list).

**Commit message:** `feat(m4): add Orbit documentation sources to RAG`

### Task 16: Update CLAUDE.md and README.md

**Files:**
- Modify: `CLAUDE.md` — Add M4 tools reference table
- Modify: `README.md` — Add M4 Orbit section

Add to CLAUDE.md under `## MCP Tools Reference`:

```markdown
### M4: Orbit Chain Integration (5 tools)
| Tool | Purpose |
|------|---------|
| `generate_orbit_config` | Chain config (prepareChainConfig, deployment params) |
| `generate_orbit_deployment` | Deployment scripts (createRollup, createTokenBridge) |
| `generate_validator_setup` | Validator/batch poster management |
| `ask_orbit` | Orbit Q&A (chain config, deployment, troubleshooting) |
| `orchestrate_orbit` | Full Orbit chain project scaffold |
```

**Commit message:** `docs: update CLAUDE.md and README.md with M4 Orbit tools`

---

## Phase 7: QA + Playground

### Task 17: Add Orbit tools to playground

**Files:**
- Modify: `apps/web/src/app/playground/page.tsx`

Add Orbit tool options to the playground UI dropdown/tabs.

**Commit message:** `feat(m4): add Orbit tools to playground UI`

### Task 18: TypeScript type check

Run: `cd apps/web && npx tsc --noEmit`
Expected: Clean compilation (0 errors)

Fix any type errors.

### Task 19: Python lint check

Run: `ruff check src/mcp/tools/generate_orbit_config.py src/mcp/tools/generate_orbit_deployment.py src/mcp/tools/generate_validator_setup.py src/mcp/tools/ask_orbit.py src/mcp/tools/orchestrate_orbit.py src/templates/orbit_templates.py`
Expected: Clean (0 errors)

Fix any lint errors.

### Task 20: Deploy to staging

Run: `cd apps/web && npm run deploy`
Expected: Successful deployment

### Task 21: Final commit + push

```bash
git push origin feat/m4-orbit-integration
```

Create PR to main with M4 changes.

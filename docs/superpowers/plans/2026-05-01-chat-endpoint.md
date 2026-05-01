# Chat Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an OpenAI-compatible `/v1/chat/completions` endpoint that runs a ReAct agent loop over 14 of the existing MCP tools, plus a `/playground/chat` UI and full API documentation.

**Architecture:** New endpoint at `apps/web/src/app/api/v1/chat/completions/route.ts` calls a ReAct agent in `lib/chat/agent.ts` that loops up to 6 iterations × 3 length-continuations against OpenRouter (`openai/gpt-oss-120b`) with native function-calling. SSE streams strict-OpenAI-format chunks (with additive `delta.reasoning_content` for chain-of-thought). Auth reuses the existing `validateRequest` helper. Tool dispatch is extracted from `app/mcp/route.ts` into a shared `lib/tools/dispatch.ts` so MCP and chat share one source of truth.

**Tech Stack:** Next.js 15 App Router (Edge runtime via OpenNext + Cloudflare Workers), TypeScript, OpenRouter (`openai/gpt-oss-120b`), D1 (SQLite), Vitest for unit tests.

**Spec:** `docs/superpowers/specs/2026-05-01-chat-endpoint-design.md`

---

### Task 1: Branch setup, dependencies, and migration

**Files:**
- Modify: `apps/web/package.json` (add `vitest`)
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/migrations/0004_chat_tool_calls.sql`

- [ ] **Step 1: Create new branch from main**

```bash
cd /home/soh/ARBuilder
git checkout -b feat/chat-endpoint
```

Expected: `Switched to a new branch 'feat/chat-endpoint'`

- [ ] **Step 2: Install vitest**

```bash
cd /home/soh/ARBuilder/apps/web
npm install --save-dev vitest@^2 @vitest/ui@^2
```

Expected: `added N packages` with no errors. Verify `package.json` now lists `vitest` under `devDependencies`.

- [ ] **Step 3: Add test script to package.json**

In `apps/web/package.json` `"scripts"` block, add:

```json
"test": "vitest run",
"test:watch": "vitest"
```

(Keep all existing scripts unchanged.)

- [ ] **Step 4: Create vitest config**

Create `apps/web/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
    globals: false,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

- [ ] **Step 5: Run vitest with no tests to confirm it works**

```bash
cd /home/soh/ARBuilder/apps/web
npm test
```

Expected: `No test files found` exit code 0 (or similar). Vitest is wired up.

- [ ] **Step 6: Create migration `0004_chat_tool_calls.sql`**

Create `apps/web/migrations/0004_chat_tool_calls.sql`:

```sql
-- Add tool_calls column to usage_logs to track which MCP tools a chat turn invoked.
-- NULL for non-chat tool invocations (existing rows and direct /api/v1/tools/* calls).
-- Stored as JSON array, e.g. '["get_stylus_context","generate_stylus_code"]'.
ALTER TABLE usage_logs ADD COLUMN tool_calls TEXT;
```

- [ ] **Step 7: Commit setup**

```bash
cd /home/soh/ARBuilder
git add apps/web/package.json apps/web/package-lock.json apps/web/vitest.config.ts apps/web/migrations/0004_chat_tool_calls.sql
git commit -m "chore: add vitest and migration for chat endpoint"
```

---

### Task 2: OpenAI-shape TypeScript types

**Files:**
- Create: `apps/web/src/lib/chat/types.ts`

- [ ] **Step 1: Create types file**

Create `apps/web/src/lib/chat/types.ts`:

```ts
/**
 * OpenAI-compatible Chat Completions types for the /v1/chat/completions endpoint.
 * Matches https://platform.openai.com/docs/api-reference/chat with one additive field
 * (`reasoning_content` on messages and deltas) for chain-of-thought passthrough.
 */

export type ChatRole = "system" | "user" | "assistant" | "tool";

export interface ToolCall {
  id: string;
  type: "function";
  function: {
    name: string;
    arguments: string; // JSON string
  };
}

export interface ChatMessage {
  role: ChatRole;
  content: string | null;
  name?: string;
  tool_call_id?: string;
  tool_calls?: ToolCall[];
  reasoning_content?: string;
}

export interface ChatCompletionRequest {
  model: string;
  messages: ChatMessage[];
  stream?: boolean;
  temperature?: number;
  max_tokens?: number;
  stop?: string | string[];
  // Ignored fields (server controls): tools, tool_choice
}

export interface OpenAIToolDef {
  type: "function";
  function: {
    name: string;
    description: string;
    parameters: {
      type: "object";
      properties: Record<string, unknown>;
      required?: string[];
    };
  };
}

export interface ChatUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface ChatCompletionResponse {
  id: string;
  object: "chat.completion";
  created: number;
  model: string;
  choices: Array<{
    index: number;
    message: ChatMessage;
    finish_reason: "stop" | "length" | "tool_calls" | "content_filter";
  }>;
  usage: ChatUsage;
}

export interface ChatCompletionChunkDelta {
  role?: ChatRole;
  content?: string;
  reasoning_content?: string;
  tool_calls?: Array<{
    index: number;
    id?: string;
    type?: "function";
    function?: { name?: string; arguments?: string };
  }>;
}

export interface ChatCompletionChunk {
  id: string;
  object: "chat.completion.chunk";
  created: number;
  model: string;
  choices: Array<{
    index: number;
    delta: ChatCompletionChunkDelta;
    finish_reason: null | "stop" | "length" | "tool_calls" | "content_filter";
  }>;
  usage?: ChatUsage; // emitted in the final chunk before [DONE]
}

export interface OpenAIErrorBody {
  error: {
    message: string;
    type: string;
    code?: string | null;
  };
}
```

- [ ] **Step 2: Commit**

```bash
cd /home/soh/ARBuilder
git add apps/web/src/lib/chat/types.ts
git commit -m "feat(chat): add OpenAI-compatible TypeScript types"
```

---

### Task 3: System prompt

**Files:**
- Create: `apps/web/src/lib/chat/systemPrompt.ts`

- [ ] **Step 1: Create system prompt module**

Create `apps/web/src/lib/chat/systemPrompt.ts`:

```ts
/**
 * System prompt for the ARBuilder chat agent.
 * Prepended to every chat turn before any client-supplied system message.
 */
export const ARBBUILDER_SYSTEM_PROMPT = `You are ARBuilder, an AI assistant for Arbitrum and Stylus development.

You have 14 tools covering:
- Stylus smart contracts (Rust/WASM): get_stylus_context, generate_stylus_code, ask_stylus, generate_tests, get_workflow
- Arbitrum SDK bridging and messaging: generate_bridge_code, generate_messaging_code, ask_bridging
- Orbit chain deployment: generate_orbit_config, generate_orbit_deployment, generate_validator_setup, ask_orbit
- Indexers and oracles: generate_indexer, generate_oracle

Rules:
1. ALWAYS call get_stylus_context or the matching ask_* tool BEFORE generating code on topics you're unsure about. Stylus SDK 0.10.0+ has subtle API changes you must verify.
2. Prefer ask_* tools for conceptual questions, generate_* for code production, get_workflow for build/deploy steps.
3. Never invent network params, contract addresses, or SDK versions — retrieve them with a tool.
4. If a user request is outside Arbitrum/Stylus/Orbit, say so plainly. Do not attempt other domains.
5. You may call multiple tools in parallel when they're independent.
6. After tool results arrive, synthesize a single coherent answer for the user. Reference the tool outputs naturally; do not paste raw JSON.

Network endpoints (do not call a tool just to look these up):
- Arbitrum Sepolia: https://sepolia-rollup.arbitrum.io/rpc (chainId 421614)
- Arbitrum One: https://arb1.arbitrum.io/rpc (chainId 42161)
- Arbitrum Nova: https://nova.arbitrum.io/rpc (chainId 42170)`;
```

- [ ] **Step 2: Commit**

```bash
cd /home/soh/ARBuilder
git add apps/web/src/lib/chat/systemPrompt.ts
git commit -m "feat(chat): add ARBuilder system prompt"
```

---

### Task 4: Shared tool dispatch

**Files:**
- Create: `apps/web/src/lib/tools/dispatch.ts`
- Test: `apps/web/src/lib/tools/dispatch.test.ts`

This extracts the `handleToolCall` switch from `app/mcp/route.ts` into a shared module so both MCP and chat use one dispatch table.

- [ ] **Step 1: Write the failing test**

Create `apps/web/src/lib/tools/dispatch.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { ALL_TOOL_NAMES, CHAT_TOOL_NAMES } from "./dispatch";

describe("dispatch tool registry", () => {
  it("exposes all 18 tools", () => {
    expect(ALL_TOOL_NAMES).toHaveLength(18);
  });

  it("chat tools exclude the 4 big scaffolders", () => {
    const excluded = ["generate_backend", "generate_frontend", "orchestrate_dapp", "orchestrate_orbit"];
    expect(CHAT_TOOL_NAMES).toHaveLength(14);
    for (const name of excluded) {
      expect(CHAT_TOOL_NAMES).not.toContain(name);
      expect(ALL_TOOL_NAMES).toContain(name);
    }
  });

  it("chat tools is a strict subset of all tools", () => {
    for (const name of CHAT_TOOL_NAMES) {
      expect(ALL_TOOL_NAMES).toContain(name);
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/soh/ARBuilder/apps/web && npm test -- dispatch
```

Expected: FAIL with "Cannot find module './dispatch'"

- [ ] **Step 3: Create the dispatch module**

Create `apps/web/src/lib/tools/dispatch.ts`:

```ts
/**
 * Shared tool dispatch — single source of truth for invoking an MCP tool by name.
 * Used by:
 *   - apps/web/src/app/mcp/route.ts (JSON-RPC MCP endpoint)
 *   - apps/web/src/lib/chat/toolDefs.ts (chat ReAct agent)
 */

// M1: Stylus
import { getStylusContext } from "./getStylusContext";
import { askStylus } from "./askStylus";
import { generateStylusCode } from "./generateStylusCode";
import { generateTests } from "./generateTests";
import { getWorkflow } from "./getWorkflow";
// M2: SDK
import { generateBridgeCode } from "./generateBridgeCode";
import { generateMessagingCode } from "./generateMessagingCode";
import { askBridging } from "./askBridging";
// M3: dApp
import { generateBackend } from "./generateBackend";
import { generateFrontend } from "./generateFrontend";
import { generateIndexer } from "./generateIndexer";
import { generateOracle } from "./generateOracle";
import { orchestrateDapp } from "./orchestrateDapp";
// M4: Orbit
import { generateOrbitConfig } from "./generateOrbitConfig";
import { generateOrbitDeployment } from "./generateOrbitDeployment";
import { generateValidatorSetup } from "./generateValidatorSetup";
import { askOrbit } from "./askOrbit";
import { orchestrateOrbit } from "./orchestrateOrbit";

export interface ToolEnv {
  VECTORIZE: VectorizeIndex;
  AI: Ai;
  DB: D1Database;
  OPENROUTER_API_KEY?: string;
}

export interface ToolResult {
  data: unknown;
  tokensUsed?: number;
}

/**
 * The 4 large scaffolders that produce 50–200KB of files.
 * Excluded from the chat agent surface but exposed to /mcp and /api/v1/tools/*.
 */
export const CHAT_EXCLUDED_TOOLS = [
  "generate_backend",
  "generate_frontend",
  "orchestrate_dapp",
  "orchestrate_orbit",
] as const;

export const ALL_TOOL_NAMES = [
  // M1
  "get_stylus_context",
  "generate_stylus_code",
  "ask_stylus",
  "generate_tests",
  "get_workflow",
  // M2
  "generate_bridge_code",
  "generate_messaging_code",
  "ask_bridging",
  // M3
  "generate_backend",
  "generate_frontend",
  "generate_indexer",
  "generate_oracle",
  "orchestrate_dapp",
  // M4
  "generate_orbit_config",
  "generate_orbit_deployment",
  "generate_validator_setup",
  "ask_orbit",
  "orchestrate_orbit",
] as const;

export const CHAT_TOOL_NAMES = ALL_TOOL_NAMES.filter(
  (n) => !CHAT_EXCLUDED_TOOLS.includes(n as (typeof CHAT_EXCLUDED_TOOLS)[number]),
);

export type ToolName = (typeof ALL_TOOL_NAMES)[number];

export async function runTool(
  toolName: string,
  args: Record<string, unknown>,
  env: ToolEnv,
): Promise<ToolResult> {
  const { VECTORIZE, AI, OPENROUTER_API_KEY } = env;
  const requireOpenRouter = () => {
    if (!OPENROUTER_API_KEY) throw new Error("OpenRouter API key not configured");
    return OPENROUTER_API_KEY;
  };

  switch (toolName) {
    case "get_stylus_context": {
      const r = await getStylusContext(VECTORIZE, AI, {
        query: args.query as string,
        nResults: (args.nResults as number) ?? 5,
        contentType: (args.contentType as "code" | "documentation" | "all") ?? "all",
        rerank: (args.rerank as boolean) ?? true,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_stylus_code": {
      const r = await generateStylusCode(VECTORIZE, AI, requireOpenRouter(), {
        prompt: args.prompt as string,
        contractType:
          (args.contractType as "token" | "nft" | "defi" | "utility" | "custom") ?? "utility",
        includeTests: (args.includeTests as boolean) ?? false,
      });
      return { data: r, tokensUsed: r.tokensUsed || 0 };
    }
    case "ask_stylus": {
      const r = await askStylus(VECTORIZE, AI, requireOpenRouter(), {
        question: args.question as string,
        codeContext: args.codeContext as string | undefined,
        questionType:
          (args.questionType as "general" | "debugging" | "optimization" | "security") ??
          "general",
      });
      return { data: r, tokensUsed: r.tokensUsed || 0 };
    }
    case "generate_tests": {
      const r = await generateTests(requireOpenRouter(), {
        contractCode: args.contractCode as string,
        testFramework: (args.testFramework as "rust_native" | "foundry") ?? "rust_native",
      });
      return { data: r, tokensUsed: r.tokensUsed || 0 };
    }
    case "get_workflow": {
      const r = getWorkflow({
        workflowType: args.workflowType as "build" | "deploy" | "test",
        network:
          (args.network as "arbitrum_sepolia" | "arbitrum_one" | "arbitrum_nova") ??
          "arbitrum_sepolia",
        includeTroubleshooting: (args.includeTroubleshooting as boolean) ?? true,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_bridge_code": {
      const r = generateBridgeCode({
        bridgeType: args.bridgeType as
          | "eth_deposit" | "eth_deposit_to" | "eth_withdraw"
          | "erc20_deposit" | "erc20_withdraw" | "eth_l1_l3" | "erc20_l1_l3",
        amount: args.amount as string | undefined,
        tokenAddress: args.tokenAddress as string | undefined,
        destinationAddress: args.destinationAddress as string | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_messaging_code": {
      const r = generateMessagingCode({
        messageType: args.messageType as "l1_to_l2" | "l2_to_l1" | "l2_to_l1_claim" | "check_status",
        includeExample: (args.includeExample as boolean) ?? true,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "ask_bridging": {
      const r = await askBridging(VECTORIZE, AI, requireOpenRouter(), {
        question: args.question as string,
        questionType: (args.questionType as "general" | "bridging" | "messaging" | "l3") ?? "general",
      });
      return { data: r, tokensUsed: r.tokensUsed || 0 };
    }
    case "generate_backend": {
      const r = generateBackend({
        prompt: args.prompt as string,
        framework: (args.framework as "nestjs" | "express") ?? "nestjs",
        contractAbi: args.contractAbi as string | undefined,
        features: args.features as string[] | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_frontend": {
      const r = generateFrontend({
        prompt: args.prompt as string,
        contractAbi: args.contractAbi as string | undefined,
        uiFramework: (args.uiFramework as "daisyui" | "shadcn" | "none") ?? "daisyui",
        template: (args.template as "base" | "dashboard" | "token") ?? "base",
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_indexer": {
      const r = generateIndexer({
        contractAddress: args.contractAddress as string,
        subgraphType: (args.subgraphType as "erc20" | "erc721" | "defi" | "custom") ?? "erc20",
        abi: args.abi as string | undefined,
        events: args.events as string[] | undefined,
        network: args.network as string | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_oracle": {
      const r = generateOracle({
        oracleType: args.oracleType as "price_feed" | "vrf" | "automation" | "functions",
        network: (args.network as "arbitrum-one" | "arbitrum-sepolia") ?? "arbitrum-sepolia",
        feeds: args.feeds as string[] | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "orchestrate_dapp": {
      const r = orchestrateDapp({
        prompt: args.prompt as string,
        components: args.components as ("contract" | "backend" | "frontend" | "indexer" | "oracle")[] | undefined,
        network: (args.network as "arbitrum-sepolia" | "arbitrum-one") ?? "arbitrum-sepolia",
        contractAddress: args.contractAddress as string | undefined,
        contractAbi: args.contractAbi as string | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_orbit_config": {
      const r = generateOrbitConfig({
        prompt: args.prompt as string,
        chainId: args.chainId as number | undefined,
        owner: args.owner as string | undefined,
        isAnyTrust: args.isAnyTrust as boolean | undefined,
        nativeToken: args.nativeToken as string | undefined,
        parentChain: args.parentChain as
          | "arbitrum-one" | "arbitrum-sepolia" | "ethereum-mainnet" | "ethereum-sepolia" | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_orbit_deployment": {
      const r = generateOrbitDeployment({
        prompt: args.prompt as string,
        deploymentType: (args.deploymentType as "rollup" | "token_bridge" | "full") ?? "rollup",
        validators: args.validators as string[] | undefined,
        batchPosters: args.batchPosters as string[] | undefined,
        nativeToken: args.nativeToken as string | undefined,
        parentChain: args.parentChain as
          | "arbitrum-one" | "arbitrum-sepolia" | "ethereum-mainnet" | "ethereum-sepolia" | undefined,
        rollupVersion: (args.rollupVersion as "v2.1" | "v3.1") ?? "v3.1",
        chainId: args.chainId as number | undefined,
        isAnyTrust: args.isAnyTrust as boolean | undefined,
        rollupAddress: args.rollupAddress as string | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_validator_setup": {
      const r = generateValidatorSetup({
        prompt: args.prompt as string,
        action: (args.action as "list" | "add" | "remove") ?? "list",
        target: (args.target as "validator" | "batch_poster" | "keyset") ?? "validator",
        addresses: args.addresses as string[] | undefined,
        rollupAddress: args.rollupAddress as string | undefined,
        sequencerInbox: args.sequencerInbox as string | undefined,
        parentChain: args.parentChain as
          | "arbitrum-one" | "arbitrum-sepolia" | "ethereum-mainnet" | "ethereum-sepolia" | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "ask_orbit": {
      const r = await askOrbit(VECTORIZE, AI, requireOpenRouter(), {
        question: args.question as string,
        questionType:
          (args.questionType as "general" | "deployment" | "config" | "validator" | "troubleshooting") ??
          "general",
      });
      return { data: r, tokensUsed: r.tokensUsed || 0 };
    }
    case "orchestrate_orbit": {
      const r = orchestrateOrbit({
        prompt: args.prompt as string,
        chainName: args.chainName as string | undefined,
        chainId: args.chainId as number | undefined,
        isAnyTrust: args.isAnyTrust as boolean | undefined,
        nativeToken: args.nativeToken as string | undefined,
        parentChain: args.parentChain as
          | "arbitrum-one" | "arbitrum-sepolia" | "ethereum-mainnet" | "ethereum-sepolia" | undefined,
        validators: args.validators as string[] | undefined,
        batchPosters: args.batchPosters as string[] | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    default:
      throw new Error(`Unknown tool: ${toolName}`);
  }
}
```

- [ ] **Step 4: Run tests**

```bash
cd /home/soh/ARBuilder/apps/web && npm test -- dispatch
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
cd /home/soh/ARBuilder
git add apps/web/src/lib/tools/dispatch.ts apps/web/src/lib/tools/dispatch.test.ts
git commit -m "feat(tools): add shared dispatch module"
```

---

### Task 5: Refactor `/mcp` to use shared dispatch

**Files:**
- Modify: `apps/web/src/app/mcp/route.ts` — replace inline `handleToolCall` switch with `runTool` import.

- [ ] **Step 1: Replace handleToolCall implementation**

In `apps/web/src/app/mcp/route.ts`:

1. Remove the 18 individual `import { ... } from "@/lib/tools/..."` lines at the top (lines ~10-31).
2. Add: `import { runTool, type ToolEnv } from "@/lib/tools/dispatch";`
3. Remove the entire `interface ToolResult { ... }` block (lines ~728-731) and replace with `import { type ToolResult } from "@/lib/tools/dispatch";` (combine with the runTool import line).
4. Replace the entire `async function handleToolCall(...)` body (the giant switch from ~733 to ~978) with:

```ts
async function handleToolCall(
  toolName: string,
  args: Record<string, unknown>,
  env: ToolEnv,
): Promise<ToolResult> {
  return runTool(toolName, args, env);
}
```

5. Wherever `handleToolCall` is called (search for `handleToolCall(`), confirm signature still matches.

- [ ] **Step 2: Run typecheck**

```bash
cd /home/soh/ARBuilder/apps/web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Run lint**

```bash
cd /home/soh/ARBuilder/apps/web && npm run lint
```

Expected: no new errors in `app/mcp/route.ts`.

- [ ] **Step 4: Smoke-test MCP endpoint locally**

```bash
cd /home/soh/ARBuilder/apps/web && npm run dev &
sleep 6
# In a new terminal:
curl -s -X POST http://localhost:3000/mcp \
  -H "Authorization: Bearer arb_REPLACE_WITH_REAL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Expected: JSON response with `result.tools` array of 18 entries. Kill dev server with `kill %1`.

If you don't have a working API key locally, skip this step; the tsc + lint checks confirm the refactor is sound.

- [ ] **Step 5: Commit**

```bash
cd /home/soh/ARBuilder
git add apps/web/src/app/mcp/route.ts
git commit -m "refactor(mcp): use shared runTool dispatch"
```

---

### Task 6: OpenRouter streaming + reasoning passthrough

**Files:**
- Modify: `apps/web/src/lib/openrouter.ts`
- Test: `apps/web/src/lib/openrouter.test.ts`

- [ ] **Step 1: Write failing test for `getMaxTokens`**

Create `apps/web/src/lib/openrouter.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { getMaxTokens, MODEL_MAX_OUTPUT_TOKENS } from "./openrouter";

describe("getMaxTokens", () => {
  it("returns model max when no requested value", () => {
    expect(getMaxTokens("openai/gpt-oss-120b")).toBe(32768);
  });

  it("honors smaller requested value", () => {
    expect(getMaxTokens("openai/gpt-oss-120b", 1000)).toBe(1000);
  });

  it("caps requested value at model max", () => {
    expect(getMaxTokens("openai/gpt-oss-120b", 100000)).toBe(32768);
  });

  it("falls back to 4096 for unknown models", () => {
    expect(getMaxTokens("unknown/model")).toBe(4096);
  });

  it("MODEL_MAX_OUTPUT_TOKENS includes gpt-oss-120b", () => {
    expect(MODEL_MAX_OUTPUT_TOKENS["openai/gpt-oss-120b"]).toBe(32768);
  });
});
```

- [ ] **Step 2: Run test, verify failure**

```bash
cd /home/soh/ARBuilder/apps/web && npm test -- openrouter
```

Expected: FAIL with "MODEL_MAX_OUTPUT_TOKENS is not defined".

- [ ] **Step 3: Add `MODEL_MAX_OUTPUT_TOKENS` and `getMaxTokens`**

In `apps/web/src/lib/openrouter.ts`, after the existing `MODELS` const declaration (around line 45), add:

```ts
/**
 * Per-model maximum output token caps (upstream provider ceilings).
 * Used by the chat endpoint to honor the model's true max while letting
 * client requests cap below it.
 */
export const MODEL_MAX_OUTPUT_TOKENS: Record<string, number> = {
  "openai/gpt-oss-120b": 32768,
};

export function getMaxTokens(model: string, requested?: number): number {
  const cap = MODEL_MAX_OUTPUT_TOKENS[model] ?? 4096;
  return requested && requested > 0 ? Math.min(requested, cap) : cap;
}
```

- [ ] **Step 4: Run test, verify passes**

```bash
cd /home/soh/ARBuilder/apps/web && npm test -- openrouter
```

Expected: PASS (5 tests).

- [ ] **Step 5: Add streaming chat completion function**

Still in `apps/web/src/lib/openrouter.ts`, append at the end of the file:

```ts
/**
 * Streaming chat completion with native tool calling and reasoning passthrough.
 *
 * Yields raw OpenRouter SSE chunk strings (each is a JSON object — already
 * decoded from `data: ...`). The agent layer handles re-encoding into our
 * /v1/chat/completions stream.
 *
 * Errors are thrown synchronously before yielding any chunk if the upstream
 * returns a non-2xx status. Mid-stream errors yield an `{ error: {...} }`
 * chunk and end the iterator.
 */
export interface StreamingCallParams {
  apiKey: string;
  model: string;
  messages: Array<{ role: string; content: string | null; name?: string; tool_call_id?: string; tool_calls?: unknown }>;
  tools?: unknown[]; // OpenAI-shape tool defs
  tool_choice?: unknown;
  temperature?: number;
  max_tokens: number;
  stop?: string | string[];
  signal?: AbortSignal;
}

export async function* streamChatCompletion(
  params: StreamingCallParams,
): AsyncGenerator<Record<string, unknown>, void, void> {
  const body: Record<string, unknown> = {
    model: params.model,
    messages: params.messages,
    stream: true,
    temperature: params.temperature ?? 0.3,
    max_tokens: params.max_tokens,
    // Ask OpenRouter to surface chain-of-thought (gpt-oss-120b honors this).
    reasoning: { effort: "medium" },
  };
  if (params.tools && params.tools.length > 0) body.tools = params.tools;
  if (params.tool_choice) body.tool_choice = params.tool_choice;
  if (params.stop) body.stop = params.stop;

  const response = await fetch(OPENROUTER_API_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${params.apiKey}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://arbuilder.app",
      "X-Title": "ARBuilder",
    },
    body: JSON.stringify(body),
    signal: params.signal,
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`OpenRouter HTTP ${response.status}: ${errText.slice(0, 500)}`);
  }
  if (!response.body) {
    throw new Error("OpenRouter returned no response body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by \n\n; each frame may contain multiple
      // "data: ..." lines and possibly comments (": ...").
      let frameEnd: number;
      while ((frameEnd = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, frameEnd);
        buffer = buffer.slice(frameEnd + 2);

        for (const rawLine of frame.split("\n")) {
          const line = rawLine.trim();
          if (!line || line.startsWith(":")) continue;
          if (!line.startsWith("data:")) continue;
          const data = line.slice(5).trim();
          if (data === "[DONE]") return;
          try {
            yield JSON.parse(data) as Record<string, unknown>;
          } catch {
            // skip malformed chunk
          }
        }
      }
    }
  } finally {
    try { reader.releaseLock(); } catch { /* ignore */ }
  }
}
```

- [ ] **Step 6: Run typecheck and tests**

```bash
cd /home/soh/ARBuilder/apps/web && npx tsc --noEmit && npm test
```

Expected: tsc clean, all tests pass.

- [ ] **Step 7: Commit**

```bash
cd /home/soh/ARBuilder
git add apps/web/src/lib/openrouter.ts apps/web/src/lib/openrouter.test.ts
git commit -m "feat(openrouter): add streaming + max-tokens helpers for chat"
```

---

### Task 7: Tool definitions for chat agent

**Files:**
- Create: `apps/web/src/lib/chat/toolDefs.ts`
- Test: `apps/web/src/lib/chat/toolDefs.test.ts`

- [ ] **Step 1: Write failing test**

Create `apps/web/src/lib/chat/toolDefs.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { ARBBUILDER_TOOL_DEFS } from "./toolDefs";
import { CHAT_TOOL_NAMES } from "@/lib/tools/dispatch";

describe("ARBBUILDER_TOOL_DEFS", () => {
  it("contains exactly the 14 chat-friendly tools", () => {
    expect(ARBBUILDER_TOOL_DEFS).toHaveLength(14);
    const names = ARBBUILDER_TOOL_DEFS.map((t) => t.function.name);
    expect(new Set(names)).toEqual(new Set(CHAT_TOOL_NAMES));
  });

  it("every def has type=function and a non-empty description", () => {
    for (const t of ARBBUILDER_TOOL_DEFS) {
      expect(t.type).toBe("function");
      expect(t.function.description.length).toBeGreaterThan(0);
      expect(t.function.parameters.type).toBe("object");
    }
  });

  it("every def with required params lists them", () => {
    const expectsRequired = [
      "get_stylus_context", "generate_stylus_code", "ask_stylus", "generate_tests",
      "get_workflow", "generate_bridge_code", "generate_messaging_code", "ask_bridging",
      "generate_indexer", "generate_oracle", "generate_orbit_config",
      "generate_orbit_deployment", "generate_validator_setup", "ask_orbit",
    ];
    for (const name of expectsRequired) {
      const def = ARBBUILDER_TOOL_DEFS.find((t) => t.function.name === name)!;
      expect(def.function.parameters.required, `${name}.required`).toBeDefined();
      expect(def.function.parameters.required!.length).toBeGreaterThan(0);
    }
  });
});
```

- [ ] **Step 2: Run test, verify failure**

```bash
cd /home/soh/ARBuilder/apps/web && npm test -- toolDefs
```

Expected: FAIL with "Cannot find module './toolDefs'".

- [ ] **Step 3: Create the toolDefs module**

Create `apps/web/src/lib/chat/toolDefs.ts`:

```ts
import type { OpenAIToolDef } from "./types";
import { CHAT_TOOL_NAMES, runTool, type ToolEnv } from "@/lib/tools/dispatch";

/**
 * 14 OpenAI-format tool definitions exposed to the chat agent.
 * The 4 large scaffolders (generate_backend, generate_frontend,
 * orchestrate_dapp, orchestrate_orbit) are intentionally excluded —
 * their multi-file outputs blow context budgets in a ReAct loop.
 *
 * Schemas are lifted from apps/web/src/app/mcp/route.ts TOOLS array,
 * filtered to chat-friendly names and reformatted per OpenAI's
 * `{type:"function", function:{...}}` envelope.
 */
export const ARBBUILDER_TOOL_DEFS: OpenAIToolDef[] = [
  {
    type: "function",
    function: {
      name: "get_stylus_context",
      description:
        "Search for relevant Stylus documentation, code examples, and patterns. Use this to find information about Stylus SDK, Rust smart contract development, and Arbitrum.",
      parameters: {
        type: "object",
        properties: {
          query: { type: "string", description: "The search query to find relevant context" },
          nResults: { type: "number", description: "Number of results to return (default: 5)" },
          contentType: {
            type: "string",
            enum: ["code", "documentation", "all"],
            description: "Type of content to search for",
          },
          rerank: { type: "boolean", description: "Whether to rerank results for better relevance" },
        },
        required: ["query"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_stylus_code",
      description:
        "Generate Stylus (Rust) smart contract code based on a description. Produces production-ready code using stylus-sdk.",
      parameters: {
        type: "object",
        properties: {
          prompt: { type: "string", description: "Description of the contract or code to generate" },
          contractType: {
            type: "string",
            enum: ["token", "nft", "defi", "utility", "custom"],
            description: "Type of contract",
          },
          includeTests: { type: "boolean", description: "Whether to include test code" },
        },
        required: ["prompt"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "ask_stylus",
      description:
        "Ask questions about Stylus development, debugging, optimization, or security. Gets context-aware answers with code examples.",
      parameters: {
        type: "object",
        properties: {
          question: { type: "string", description: "The question to ask about Stylus development" },
          codeContext: { type: "string", description: "Optional code context for more specific answers" },
          questionType: {
            type: "string",
            enum: ["general", "debugging", "optimization", "security"],
            description: "Type of question",
          },
        },
        required: ["question"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_tests",
      description:
        "Generate comprehensive tests for Stylus contract code. Supports Rust native tests and Foundry Solidity tests.",
      parameters: {
        type: "object",
        properties: {
          contractCode: { type: "string", description: "The Stylus contract code to generate tests for" },
          testFramework: {
            type: "string",
            enum: ["rust_native", "foundry"],
            description: "Test framework",
          },
        },
        required: ["contractCode"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "get_workflow",
      description:
        "Get step-by-step workflow instructions for building, deploying, or testing Stylus contracts.",
      parameters: {
        type: "object",
        properties: {
          workflowType: { type: "string", enum: ["build", "deploy", "test"] },
          network: {
            type: "string",
            enum: ["arbitrum_sepolia", "arbitrum_one", "arbitrum_nova"],
            description: "Target network",
          },
          includeTroubleshooting: { type: "boolean" },
        },
        required: ["workflowType"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_bridge_code",
      description:
        "Generate TypeScript code for bridging ETH or ERC20 tokens between L1, L2, and L3 (Orbit chains). Supports deposits, withdrawals, and L1->L3 bridging.",
      parameters: {
        type: "object",
        properties: {
          bridgeType: {
            type: "string",
            enum: [
              "eth_deposit", "eth_deposit_to", "eth_withdraw",
              "erc20_deposit", "erc20_withdraw", "eth_l1_l3", "erc20_l1_l3",
            ],
          },
          amount: { type: "string", description: "Amount to bridge (e.g., '0.1' for ETH)" },
          tokenAddress: { type: "string", description: "ERC20 token address" },
          destinationAddress: { type: "string", description: "Destination address (for depositTo)" },
        },
        required: ["bridgeType"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_messaging_code",
      description:
        "Generate TypeScript code for Arbitrum cross-chain messaging. Supports L1->L2 messaging via retryable tickets, L2->L1 messaging via ArbSys, and message status checking.",
      parameters: {
        type: "object",
        properties: {
          messageType: {
            type: "string",
            enum: ["l1_to_l2", "l2_to_l1", "l2_to_l1_claim", "check_status"],
          },
          includeExample: { type: "boolean" },
        },
        required: ["messageType"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "ask_bridging",
      description:
        "Answer questions about Arbitrum bridging and cross-chain messaging using RAG. Topics: ETH/ERC20 bridging, L1->L3 bridging, retryable tickets, challenge periods, gas estimation.",
      parameters: {
        type: "object",
        properties: {
          question: { type: "string", description: "Question about Arbitrum bridging or messaging" },
          questionType: {
            type: "string",
            enum: ["general", "bridging", "messaging", "l3"],
          },
        },
        required: ["question"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_indexer",
      description:
        "Generate a The Graph subgraph for indexing Arbitrum smart contract events. Supports ERC20, ERC721, DeFi, and custom event patterns.",
      parameters: {
        type: "object",
        properties: {
          contractAddress: { type: "string", description: "Contract address to index" },
          subgraphType: {
            type: "string",
            enum: ["erc20", "erc721", "defi", "custom"],
          },
          abi: { type: "string", description: "Contract ABI JSON for custom event handling" },
          events: { type: "array", items: { type: "string" }, description: "Event signatures to index" },
          network: { type: "string", description: "Target network" },
        },
        required: ["contractAddress"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_oracle",
      description:
        "Generate Chainlink oracle integration code for Arbitrum. Supports Price Feeds, VRF (randomness), Automation (keepers), and Functions.",
      parameters: {
        type: "object",
        properties: {
          oracleType: {
            type: "string",
            enum: ["price_feed", "vrf", "automation", "functions"],
          },
          network: { type: "string", enum: ["arbitrum-one", "arbitrum-sepolia"] },
          feeds: { type: "array", items: { type: "string" }, description: "Price feed pairs" },
        },
        required: ["oracleType"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_orbit_config",
      description:
        "Generate configuration code for Orbit chain deployment. Supports chain config, AnyTrust DAC setup, and custom gas token configuration using @arbitrum/orbit-sdk.",
      parameters: {
        type: "object",
        properties: {
          prompt: { type: "string", description: "Description of the configuration needed" },
          chainId: { type: "number", description: "Chain ID for the new Orbit chain" },
          owner: { type: "string", description: "Initial chain owner address" },
          isAnyTrust: { type: "boolean", description: "AnyTrust (vs Rollup)" },
          nativeToken: { type: "string", description: "Custom gas token address (ERC20)" },
          parentChain: {
            type: "string",
            enum: ["arbitrum-one", "arbitrum-sepolia", "ethereum-mainnet", "ethereum-sepolia"],
          },
        },
        required: ["prompt"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_orbit_deployment",
      description:
        "Generate deployment code for Orbit chains. Supports rollup deployment (createRollup), token bridge deployment (createTokenBridge), or full deployment with both.",
      parameters: {
        type: "object",
        properties: {
          prompt: { type: "string", description: "Description of the deployment needed" },
          deploymentType: { type: "string", enum: ["rollup", "token_bridge", "full"] },
          validators: { type: "array", items: { type: "string" } },
          batchPosters: { type: "array", items: { type: "string" } },
          nativeToken: { type: "string" },
          parentChain: {
            type: "string",
            enum: ["arbitrum-one", "arbitrum-sepolia", "ethereum-mainnet", "ethereum-sepolia"],
          },
          rollupVersion: { type: "string", enum: ["v2.1", "v3.1"] },
          chainId: { type: "number" },
          isAnyTrust: { type: "boolean" },
          rollupAddress: { type: "string", description: "Existing rollup contract address" },
        },
        required: ["prompt"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_validator_setup",
      description:
        "Generate code for managing Orbit chain validators, batch posters, and AnyTrust DAC keysets. Supports listing, adding, and removing validators.",
      parameters: {
        type: "object",
        properties: {
          prompt: { type: "string", description: "Description of the validator management needed" },
          action: { type: "string", enum: ["list", "add", "remove"] },
          target: { type: "string", enum: ["validator", "batch_poster", "keyset"] },
          addresses: { type: "array", items: { type: "string" } },
          rollupAddress: { type: "string" },
          sequencerInbox: { type: "string" },
          parentChain: {
            type: "string",
            enum: ["arbitrum-one", "arbitrum-sepolia", "ethereum-mainnet", "ethereum-sepolia"],
          },
        },
        required: ["prompt"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "ask_orbit",
      description:
        "Answer questions about Arbitrum Orbit chain deployment, configuration, and management. Covers chain config, deployment, validators, gas tokens, AnyTrust, node setup, governance, and token bridges.",
      parameters: {
        type: "object",
        properties: {
          question: { type: "string", description: "Question about Orbit chain deployment or management" },
          questionType: {
            type: "string",
            enum: ["general", "deployment", "config", "validator", "troubleshooting"],
          },
        },
        required: ["question"],
      },
    },
  },
];

/**
 * Tool result serialization for the role:tool message fed back to the model.
 * Soft-cap at 32_000 chars (~8000 tokens). Past the cap, return a structured
 * truncation marker so the model can still reason about the call's outcome.
 */
const TOOL_RESULT_MAX_CHARS = 32_000;

function serializeToolResult(data: unknown): string {
  const json = typeof data === "string" ? data : JSON.stringify(data, null, 2);
  if (json.length <= TOOL_RESULT_MAX_CHARS) return json;
  return JSON.stringify({
    truncated: true,
    note: `Result was ${json.length} chars; truncated to first ${TOOL_RESULT_MAX_CHARS} for context budget.`,
    preview: json.slice(0, TOOL_RESULT_MAX_CHARS),
  });
}

/**
 * Execute a single OpenAI-format tool_call, returning the tool message
 * to append to the conversation. Errors during tool execution are returned
 * as a structured error so the model can react rather than crashing the loop.
 */
export async function executeToolCall(
  toolCall: { id: string; function: { name: string; arguments: string } },
  env: ToolEnv,
): Promise<{ tool_call_id: string; content: string; toolName: string; success: boolean }> {
  const { name, arguments: argsJson } = toolCall.function;

  // Reject tools that aren't in the chat surface.
  if (!CHAT_TOOL_NAMES.includes(name as (typeof CHAT_TOOL_NAMES)[number])) {
    return {
      tool_call_id: toolCall.id,
      toolName: name,
      success: false,
      content: JSON.stringify({ error: `Tool '${name}' is not available in chat surface.` }),
    };
  }

  let args: Record<string, unknown>;
  try {
    args = JSON.parse(argsJson || "{}");
  } catch (e) {
    return {
      tool_call_id: toolCall.id,
      toolName: name,
      success: false,
      content: JSON.stringify({ error: `Invalid JSON in tool arguments: ${(e as Error).message}` }),
    };
  }

  try {
    const result = await runTool(name, args, env);
    return {
      tool_call_id: toolCall.id,
      toolName: name,
      success: true,
      content: serializeToolResult(result.data),
    };
  } catch (e) {
    return {
      tool_call_id: toolCall.id,
      toolName: name,
      success: false,
      content: JSON.stringify({ error: (e as Error).message || String(e) }),
    };
  }
}
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd /home/soh/ARBuilder/apps/web && npm test -- toolDefs
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
cd /home/soh/ARBuilder
git add apps/web/src/lib/chat/toolDefs.ts apps/web/src/lib/chat/toolDefs.test.ts
git commit -m "feat(chat): add 14 OpenAI-format tool defs and executeToolCall"
```

---

### Task 8: SSE streaming helpers

**Files:**
- Create: `apps/web/src/lib/chat/streaming.ts`
- Test: `apps/web/src/lib/chat/streaming.test.ts`

- [ ] **Step 1: Write failing test**

Create `apps/web/src/lib/chat/streaming.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { encodeSSEChunk, mergeToolCallDeltas, accumulateChunk } from "./streaming";
import type { ChatCompletionChunk } from "./types";

describe("encodeSSEChunk", () => {
  it("encodes an OpenAI chunk as a data: line", () => {
    const chunk: ChatCompletionChunk = {
      id: "x", object: "chat.completion.chunk", created: 0, model: "m",
      choices: [{ index: 0, delta: { content: "hi" }, finish_reason: null }],
    };
    const out = encodeSSEChunk(chunk);
    expect(out).toMatch(/^data: /);
    expect(out.endsWith("\n\n")).toBe(true);
    expect(JSON.parse(out.slice(6).trim())).toEqual(chunk);
  });
});

describe("mergeToolCallDeltas", () => {
  it("accumulates argument fragments by index", () => {
    const acc: Array<{ id?: string; type?: string; function: { name?: string; arguments: string } }> = [];
    mergeToolCallDeltas(acc, [{ index: 0, id: "c1", type: "function", function: { name: "foo", arguments: '{"q":' } }]);
    mergeToolCallDeltas(acc, [{ index: 0, function: { arguments: '"hi"}' } }]);
    expect(acc[0].id).toBe("c1");
    expect(acc[0].function.name).toBe("foo");
    expect(acc[0].function.arguments).toBe('{"q":"hi"}');
  });

  it("handles multiple parallel tool calls", () => {
    const acc: Array<{ id?: string; type?: string; function: { name?: string; arguments: string } }> = [];
    mergeToolCallDeltas(acc, [
      { index: 0, id: "a", function: { name: "x", arguments: "{}" } },
      { index: 1, id: "b", function: { name: "y", arguments: '{"k":1}' } },
    ]);
    expect(acc).toHaveLength(2);
    expect(acc[0].function.name).toBe("x");
    expect(acc[1].function.name).toBe("y");
  });
});

describe("accumulateChunk", () => {
  it("accumulates content, reasoning, and tool_calls across chunks", () => {
    const acc = { content: "", reasoning_content: "", tool_calls: [] as Array<{ id?: string; type?: string; function: { name?: string; arguments: string } }>, finish_reason: null as null | string, usage: undefined as undefined | { prompt_tokens: number; completion_tokens: number; total_tokens: number } };
    accumulateChunk(acc, { choices: [{ delta: { content: "ab" }, finish_reason: null }] } as Partial<ChatCompletionChunk>);
    accumulateChunk(acc, { choices: [{ delta: { reasoning_content: "thinking..." }, finish_reason: null }] } as Partial<ChatCompletionChunk>);
    accumulateChunk(acc, { choices: [{ delta: { content: "cd" }, finish_reason: "stop" }] } as Partial<ChatCompletionChunk>);
    expect(acc.content).toBe("abcd");
    expect(acc.reasoning_content).toBe("thinking...");
    expect(acc.finish_reason).toBe("stop");
  });
});
```

- [ ] **Step 2: Run test, verify failure**

```bash
cd /home/soh/ARBuilder/apps/web && npm test -- streaming
```

Expected: FAIL with "Cannot find module './streaming'".

- [ ] **Step 3: Create streaming module**

Create `apps/web/src/lib/chat/streaming.ts`:

```ts
import type { ChatCompletionChunk, ChatUsage } from "./types";

/**
 * Encode an OpenAI chat.completion.chunk as a single SSE frame.
 */
export function encodeSSEChunk(chunk: ChatCompletionChunk): string {
  return `data: ${JSON.stringify(chunk)}\n\n`;
}

/**
 * Encode the terminal [DONE] frame.
 */
export function encodeSSEDone(): string {
  return "data: [DONE]\n\n";
}

/**
 * Encode a mid-stream error frame in OpenAI shape (no HTTP status — already 200).
 */
export function encodeSSEError(message: string, type: string, code?: string): string {
  return `data: ${JSON.stringify({ error: { message, type, code: code ?? null } })}\n\n`;
}

export interface ToolCallAccumulator {
  id?: string;
  type?: string;
  function: { name?: string; arguments: string };
}

/**
 * Apply incoming tool_calls delta to an accumulator array, in-place.
 * Each delta entry has an index — we extend the array as needed and string-concat
 * function.arguments at that index. id, type, function.name latch on first sight.
 */
export function mergeToolCallDeltas(
  acc: ToolCallAccumulator[],
  deltas: Array<{
    index: number;
    id?: string;
    type?: "function";
    function?: { name?: string; arguments?: string };
  }>,
): void {
  for (const d of deltas) {
    while (acc.length <= d.index) {
      acc.push({ function: { arguments: "" } });
    }
    const slot = acc[d.index];
    if (d.id && !slot.id) slot.id = d.id;
    if (d.type && !slot.type) slot.type = d.type;
    if (d.function?.name && !slot.function.name) slot.function.name = d.function.name;
    if (d.function?.arguments) slot.function.arguments += d.function.arguments;
  }
}

export interface IterationAccumulator {
  content: string;
  reasoning_content: string;
  tool_calls: ToolCallAccumulator[];
  finish_reason: null | string;
  usage?: ChatUsage;
}

/**
 * Apply a streaming chunk's first-choice delta into the accumulator.
 * Tolerant of partial chunks (missing choices, missing delta).
 */
export function accumulateChunk(
  acc: IterationAccumulator,
  chunk: Partial<ChatCompletionChunk> & {
    choices?: Array<{ delta?: { content?: string; reasoning_content?: string; reasoning?: string; tool_calls?: Array<{ index: number; id?: string; type?: "function"; function?: { name?: string; arguments?: string } }> }; finish_reason?: null | string }>;
    usage?: ChatUsage;
  },
): void {
  const choice = chunk.choices?.[0];
  if (choice?.delta) {
    const d = choice.delta;
    if (d.content) acc.content += d.content;
    // Accept either `reasoning_content` (DeepSeek convention) or `reasoning`
    // (OpenRouter native field name on gpt-oss).
    if (d.reasoning_content) acc.reasoning_content += d.reasoning_content;
    if (d.reasoning) acc.reasoning_content += d.reasoning;
    if (d.tool_calls && d.tool_calls.length > 0) mergeToolCallDeltas(acc.tool_calls, d.tool_calls);
  }
  if (choice?.finish_reason) acc.finish_reason = choice.finish_reason;
  if (chunk.usage) acc.usage = chunk.usage;
}

export function newIterationAccumulator(): IterationAccumulator {
  return { content: "", reasoning_content: "", tool_calls: [], finish_reason: null };
}
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd /home/soh/ARBuilder/apps/web && npm test -- streaming
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
cd /home/soh/ARBuilder
git add apps/web/src/lib/chat/streaming.ts apps/web/src/lib/chat/streaming.test.ts
git commit -m "feat(chat): add SSE encoding and stream accumulation helpers"
```

---

### Task 9: ReAct agent loop

**Files:**
- Create: `apps/web/src/lib/chat/agent.ts`
- Test: `apps/web/src/lib/chat/agent.test.ts`

The agent runs the ReAct loop with continuation. It exposes one entrypoint, `runAgent`, that returns either a non-streaming response or yields SSE frames.

- [ ] **Step 1: Write failing tests**

Create `apps/web/src/lib/chat/agent.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { runAgentNonStreaming } from "./agent";
import type { ChatMessage } from "./types";
import type { ToolEnv } from "@/lib/tools/dispatch";

// Mock the openrouter streaming generator so we can script LLM responses.
vi.mock("@/lib/openrouter", async () => {
  const actual = await vi.importActual<typeof import("@/lib/openrouter")>("@/lib/openrouter");
  return {
    ...actual,
    streamChatCompletion: vi.fn(),
  };
});

// Mock the runTool dispatch so we can return synthetic tool results.
vi.mock("@/lib/tools/dispatch", async () => {
  const actual = await vi.importActual<typeof import("@/lib/tools/dispatch")>("@/lib/tools/dispatch");
  return {
    ...actual,
    runTool: vi.fn(async (name: string) => ({ data: { ok: true, tool: name }, tokensUsed: 10 })),
  };
});

import { streamChatCompletion } from "@/lib/openrouter";

const fakeEnv: ToolEnv = {
  VECTORIZE: {} as VectorizeIndex,
  AI: {} as Ai,
  DB: {} as D1Database,
  OPENROUTER_API_KEY: "test-key",
};

function makeStream(chunks: unknown[]) {
  // eslint-disable-next-line require-yield
  return async function* () {
    for (const c of chunks) yield c as Record<string, unknown>;
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("runAgentNonStreaming", () => {
  it("returns final answer when model emits no tool_calls", async () => {
    (streamChatCompletion as unknown as ReturnType<typeof vi.fn>).mockImplementation(
      makeStream([
        { choices: [{ delta: { content: "hello" } }] },
        { choices: [{ delta: { content: " world" }, finish_reason: "stop" }], usage: { prompt_tokens: 5, completion_tokens: 2, total_tokens: 7 } },
      ]),
    );
    const messages: ChatMessage[] = [{ role: "user", content: "say hi" }];
    const out = await runAgentNonStreaming(messages, fakeEnv, { temperature: 0.3, max_tokens: 100 });
    expect(out.content).toBe("hello world");
    expect(out.finish_reason).toBe("stop");
    expect(out.usage.total_tokens).toBe(7);
    expect(out.toolCallNames).toEqual([]);
  });

  it("executes a tool and loops once", async () => {
    const callA = makeStream([
      {
        choices: [{
          delta: {
            tool_calls: [{ index: 0, id: "call_1", type: "function", function: { name: "ask_stylus", arguments: '{"question":"q"}' } }],
          },
          finish_reason: "tool_calls",
        }],
        usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
      },
    ]);
    const callB = makeStream([
      { choices: [{ delta: { content: "answer" }, finish_reason: "stop" }], usage: { prompt_tokens: 20, completion_tokens: 3, total_tokens: 23 } },
    ]);
    const mock = streamChatCompletion as unknown as ReturnType<typeof vi.fn>;
    mock.mockImplementationOnce(callA).mockImplementationOnce(callB);

    const messages: ChatMessage[] = [{ role: "user", content: "explain mappings" }];
    const out = await runAgentNonStreaming(messages, fakeEnv, { temperature: 0.3, max_tokens: 100 });
    expect(out.content).toBe("answer");
    expect(out.toolCallNames).toEqual(["ask_stylus"]);
    expect(out.usage.total_tokens).toBe(15 + 23);
  });

  it("continues across finish_reason='length'", async () => {
    const part1 = makeStream([
      { choices: [{ delta: { content: "first " }, finish_reason: "length" }], usage: { prompt_tokens: 5, completion_tokens: 2, total_tokens: 7 } },
    ]);
    const part2 = makeStream([
      { choices: [{ delta: { content: "second" }, finish_reason: "stop" }], usage: { prompt_tokens: 5, completion_tokens: 2, total_tokens: 7 } },
    ]);
    const mock = streamChatCompletion as unknown as ReturnType<typeof vi.fn>;
    mock.mockImplementationOnce(part1).mockImplementationOnce(part2);

    const out = await runAgentNonStreaming(
      [{ role: "user", content: "long" }],
      fakeEnv,
      { temperature: 0.3, max_tokens: 100 },
    );
    expect(out.content).toBe("first second");
    expect(out.finish_reason).toBe("stop");
  });
});
```

- [ ] **Step 2: Run test, verify failure**

```bash
cd /home/soh/ARBuilder/apps/web && npm test -- agent
```

Expected: FAIL with "Cannot find module './agent'".

- [ ] **Step 3: Create agent module**

Create `apps/web/src/lib/chat/agent.ts`:

```ts
import { streamChatCompletion, getMaxTokens } from "@/lib/openrouter";
import { ARBBUILDER_TOOL_DEFS, executeToolCall } from "./toolDefs";
import { ARBBUILDER_SYSTEM_PROMPT } from "./systemPrompt";
import {
  accumulateChunk,
  encodeSSEChunk,
  encodeSSEDone,
  encodeSSEError,
  newIterationAccumulator,
  type IterationAccumulator,
  type ToolCallAccumulator,
} from "./streaming";
import type {
  ChatCompletionChunk,
  ChatMessage,
  ChatUsage,
  ToolCall,
} from "./types";
import type { ToolEnv } from "@/lib/tools/dispatch";

const UPSTREAM_MODEL = "openai/gpt-oss-120b";
const MAX_REACT_ITERATIONS = 6;
const MAX_LENGTH_CONTINUATIONS = 3;
const TOTAL_TURN_BUDGET_TOKENS = 200_000;

export interface AgentOptions {
  temperature: number;
  max_tokens: number;
  stop?: string | string[];
  signal?: AbortSignal;
}

export interface AgentNonStreamResult {
  content: string;
  reasoning_content: string;
  finish_reason: "stop" | "length" | "tool_calls" | "content_filter";
  usage: ChatUsage;
  toolCallNames: string[]; // for usage logging
}

/**
 * Build the message array sent to the model: prepend our system prompt,
 * then any user-supplied system message, then conversation history.
 */
function withSystemPrompt(messages: ChatMessage[]): ChatMessage[] {
  const userSystem = messages.find((m) => m.role === "system");
  const rest = messages.filter((m) => m.role !== "system");
  const sys: ChatMessage = {
    role: "system",
    content: userSystem
      ? `${ARBBUILDER_SYSTEM_PROMPT}\n\n---\n\n${userSystem.content ?? ""}`
      : ARBBUILDER_SYSTEM_PROMPT,
  };
  return [sys, ...rest];
}

function sumUsage(a: ChatUsage, b?: ChatUsage): ChatUsage {
  if (!b) return a;
  return {
    prompt_tokens: a.prompt_tokens + (b.prompt_tokens ?? 0),
    completion_tokens: a.completion_tokens + (b.completion_tokens ?? 0),
    total_tokens: a.total_tokens + (b.total_tokens ?? 0),
  };
}

/**
 * Convert the internal tool_calls accumulator (with id?: string)
 * into the canonical ToolCall[] form (id: string required) for the message log.
 * Tool calls with no id (rare; usually a streaming glitch) get a synthesized id.
 */
function finalizeToolCalls(acc: ToolCallAccumulator[]): ToolCall[] {
  return acc.map((tc, i) => ({
    id: tc.id ?? `call_${Date.now()}_${i}`,
    type: "function" as const,
    function: { name: tc.function.name ?? "", arguments: tc.function.arguments },
  }));
}

/**
 * Run a single LLM call with auto-continuation on finish_reason="length".
 * Returns an accumulator with the full iteration's content/tool_calls/usage.
 *
 * If `onSseChunk` is provided, each upstream chunk is forwarded as an SSE
 * frame (after rewriting `reasoning` → `reasoning_content`). The caller
 * controls when [DONE] is emitted.
 */
async function callIterationWithContinuation(
  apiKey: string,
  messages: ChatMessage[],
  opts: AgentOptions,
  onSseChunk?: (chunk: ChatCompletionChunk) => void,
  streamId?: string,
  createdAt?: number,
): Promise<IterationAccumulator> {
  const acc = newIterationAccumulator();
  let working = messages;

  for (let cont = 0; cont < MAX_LENGTH_CONTINUATIONS; cont++) {
    const usagePerCall = await runOneCall(apiKey, working, opts, acc, onSseChunk, streamId, createdAt);
    if (usagePerCall) acc.usage = sumUsage(acc.usage ?? { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 }, usagePerCall);

    if (acc.finish_reason !== "length") return acc;

    // Continuation: append partial assistant turn so model knows where to resume.
    working = [
      ...messages,
      {
        role: "assistant",
        content: acc.content,
        tool_calls: acc.tool_calls.length > 0 ? finalizeToolCalls(acc.tool_calls) : undefined,
      },
    ];
    // Reset finish_reason for the next pass.
    acc.finish_reason = null;
  }

  // Three continuations not enough — return what we have, finish_reason still null
  // (caller treats null as "length" effectively).
  if (!acc.finish_reason) acc.finish_reason = "length";
  return acc;
}

/**
 * Run one underlying OpenRouter call and accumulate into `acc`.
 * Returns the usage reported on the final chunk (or undefined).
 */
async function runOneCall(
  apiKey: string,
  messages: ChatMessage[],
  opts: AgentOptions,
  acc: IterationAccumulator,
  onSseChunk?: (chunk: ChatCompletionChunk) => void,
  streamId?: string,
  createdAt?: number,
): Promise<ChatUsage | undefined> {
  const stream = streamChatCompletion({
    apiKey,
    model: UPSTREAM_MODEL,
    messages: messages.map((m) => ({
      role: m.role,
      content: m.content,
      name: m.name,
      tool_call_id: m.tool_call_id,
      tool_calls: m.tool_calls,
    })),
    tools: ARBBUILDER_TOOL_DEFS,
    temperature: opts.temperature,
    max_tokens: opts.max_tokens,
    stop: opts.stop,
    signal: opts.signal,
  });

  let usage: ChatUsage | undefined;
  for await (const rawChunk of stream) {
    // Re-emit as SSE if streaming. Rewrite `reasoning` → `reasoning_content`
    // so downstream clients see the DeepSeek-convention field.
    if (onSseChunk && streamId && createdAt) {
      const rewritten = rewriteChunkForOutput(rawChunk, streamId, createdAt);
      if (rewritten) onSseChunk(rewritten);
    }
    accumulateChunk(acc, rawChunk as Parameters<typeof accumulateChunk>[1]);
    if ((rawChunk as { usage?: ChatUsage }).usage) usage = (rawChunk as { usage?: ChatUsage }).usage;
  }
  return usage;
}

/**
 * Translate an upstream OpenRouter chunk into our outbound stream shape.
 * Strips internal fields, normalizes reasoning field name, preserves choices.
 */
function rewriteChunkForOutput(
  raw: Record<string, unknown>,
  streamId: string,
  createdAt: number,
): ChatCompletionChunk | null {
  const choices = raw.choices as Array<{
    index?: number;
    delta?: { content?: string; reasoning?: string; reasoning_content?: string; role?: string; tool_calls?: unknown };
    finish_reason?: null | string;
  }> | undefined;
  if (!choices || choices.length === 0) {
    if (raw.usage) {
      return {
        id: streamId,
        object: "chat.completion.chunk",
        created: createdAt,
        model: "arbbuilder-chat",
        choices: [],
        usage: raw.usage as ChatUsage,
      };
    }
    return null;
  }
  const c = choices[0];
  const outDelta: ChatCompletionChunk["choices"][0]["delta"] = {};
  if (c.delta?.role) outDelta.role = c.delta.role as ChatCompletionChunk["choices"][0]["delta"]["role"];
  if (c.delta?.content) outDelta.content = c.delta.content;
  // Normalize reasoning field name.
  const reasoning = c.delta?.reasoning_content ?? c.delta?.reasoning;
  if (reasoning) outDelta.reasoning_content = reasoning;
  if (c.delta?.tool_calls) outDelta.tool_calls = c.delta.tool_calls as ChatCompletionChunk["choices"][0]["delta"]["tool_calls"];

  return {
    id: streamId,
    object: "chat.completion.chunk",
    created: createdAt,
    model: "arbbuilder-chat",
    choices: [{
      index: c.index ?? 0,
      delta: outDelta,
      finish_reason: (c.finish_reason ?? null) as ChatCompletionChunk["choices"][0]["finish_reason"],
    }],
    usage: raw.usage as ChatUsage | undefined,
  };
}

/**
 * Run the ReAct loop end-to-end and return a fully assembled non-streaming result.
 */
export async function runAgentNonStreaming(
  initialMessages: ChatMessage[],
  env: ToolEnv,
  opts: AgentOptions,
): Promise<AgentNonStreamResult> {
  if (!env.OPENROUTER_API_KEY) throw new Error("OpenRouter API key not configured");

  let messages = withSystemPrompt(initialMessages);
  let totalUsage: ChatUsage = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };
  const reasoningParts: string[] = [];
  const toolCallNames: string[] = [];
  let finalContent = "";
  let lastFinishReason: AgentNonStreamResult["finish_reason"] = "stop";
  const cappedMax = getMaxTokens(UPSTREAM_MODEL, opts.max_tokens);

  for (let iter = 0; iter < MAX_REACT_ITERATIONS; iter++) {
    if (totalUsage.total_tokens > TOTAL_TURN_BUDGET_TOKENS) {
      finalContent = (finalContent + "\n\n[Note: response truncated due to per-turn token budget.]").trim();
      lastFinishReason = "length";
      break;
    }

    const acc = await callIterationWithContinuation(env.OPENROUTER_API_KEY, messages, {
      ...opts,
      max_tokens: cappedMax,
    });

    totalUsage = sumUsage(totalUsage, acc.usage);
    if (acc.reasoning_content) reasoningParts.push(`[Step ${iter + 1}] ${acc.reasoning_content}`);

    if (acc.tool_calls.length === 0) {
      finalContent = acc.content;
      lastFinishReason = (acc.finish_reason as AgentNonStreamResult["finish_reason"]) ?? "stop";
      break;
    }

    // Execute tool calls, append messages, loop.
    const toolCallList = finalizeToolCalls(acc.tool_calls);
    messages = [
      ...messages,
      { role: "assistant", content: acc.content || null, tool_calls: toolCallList },
    ];
    const results = await Promise.all(toolCallList.map((tc) => executeToolCall(tc, env)));
    for (const r of results) {
      toolCallNames.push(r.toolName);
      messages.push({ role: "tool", tool_call_id: r.tool_call_id, content: r.content });
    }

    if (iter === MAX_REACT_ITERATIONS - 1) {
      // Hit cap — do one final wrap-up call without tools.
      const finalAcc = await callIterationWithContinuation(
        env.OPENROUTER_API_KEY,
        [
          ...messages,
          { role: "user", content: "Wrap up your reasoning into a final answer for the user. Do not call any more tools." },
        ],
        { ...opts, max_tokens: cappedMax },
      );
      totalUsage = sumUsage(totalUsage, finalAcc.usage);
      if (finalAcc.reasoning_content) reasoningParts.push(`[Wrap-up] ${finalAcc.reasoning_content}`);
      finalContent = finalAcc.content || "I needed more steps than allowed; please ask a more specific question.";
      lastFinishReason = "length";
    }
  }

  return {
    content: finalContent,
    reasoning_content: reasoningParts.join("\n"),
    finish_reason: lastFinishReason,
    usage: totalUsage,
    toolCallNames,
  };
}

/**
 * Run the ReAct loop and stream OpenAI-format SSE frames as they're produced.
 * The caller is expected to pipe `chunks` into a Response body.
 *
 * Yields:
 *   - chat.completion.chunk frames (encoded as `data: {...}\n\n`)
 *   - exactly one final usage chunk before [DONE]
 *   - terminal `data: [DONE]\n\n`
 *
 * Tool execution happens inline between iterations and is invisible on the wire.
 */
export async function* runAgentStreaming(
  initialMessages: ChatMessage[],
  env: ToolEnv,
  opts: AgentOptions,
  streamId: string,
  createdAt: number,
): AsyncGenerator<string, { toolCallNames: string[]; usage: ChatUsage }, void> {
  if (!env.OPENROUTER_API_KEY) {
    yield encodeSSEError("OpenRouter API key not configured", "internal_error");
    yield encodeSSEDone();
    return { toolCallNames: [], usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 } };
  }

  let messages = withSystemPrompt(initialMessages);
  let totalUsage: ChatUsage = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };
  const toolCallNames: string[] = [];
  const cappedMax = getMaxTokens(UPSTREAM_MODEL, opts.max_tokens);

  // Buffer for ordered SSE emission across iterations.
  const queue: string[] = [];
  const onChunk = (chunk: ChatCompletionChunk) => {
    // Suppress per-chunk usage from upstream; we emit a final consolidated usage chunk ourselves.
    const safe = { ...chunk, usage: undefined };
    queue.push(encodeSSEChunk(safe));
  };

  try {
    for (let iter = 0; iter < MAX_REACT_ITERATIONS; iter++) {
      if (totalUsage.total_tokens > TOTAL_TURN_BUDGET_TOKENS) {
        const cutoff: ChatCompletionChunk = {
          id: streamId, object: "chat.completion.chunk", created: createdAt, model: "arbbuilder-chat",
          choices: [{ index: 0, delta: { content: "\n\n[Response truncated: turn token budget exceeded.]" }, finish_reason: "length" }],
        };
        yield encodeSSEChunk(cutoff);
        break;
      }

      const acc = await callIterationWithContinuation(
        env.OPENROUTER_API_KEY,
        messages,
        { ...opts, max_tokens: cappedMax },
        onChunk,
        streamId,
        createdAt,
      );

      // Flush any buffered chunks for this iteration.
      while (queue.length > 0) yield queue.shift()!;

      totalUsage = sumUsage(totalUsage, acc.usage);

      if (acc.tool_calls.length === 0) {
        // Final answer — close the choice with finish_reason if not already done.
        if (acc.finish_reason && acc.finish_reason !== "stop") {
          // already conveyed in stream
        }
        break;
      }

      // Append assistant tool-calls to messages and execute tools.
      const toolCallList = finalizeToolCalls(acc.tool_calls);
      messages = [
        ...messages,
        { role: "assistant", content: acc.content || null, tool_calls: toolCallList },
      ];
      const results = await Promise.all(toolCallList.map((tc) => executeToolCall(tc, env)));
      for (const r of results) {
        toolCallNames.push(r.toolName);
        messages.push({ role: "tool", tool_call_id: r.tool_call_id, content: r.content });
      }

      if (iter === MAX_REACT_ITERATIONS - 1) {
        const finalAcc = await callIterationWithContinuation(
          env.OPENROUTER_API_KEY,
          [
            ...messages,
            { role: "user", content: "Wrap up your reasoning into a final answer for the user. Do not call any more tools." },
          ],
          { ...opts, max_tokens: cappedMax },
          onChunk,
          streamId,
          createdAt,
        );
        while (queue.length > 0) yield queue.shift()!;
        totalUsage = sumUsage(totalUsage, finalAcc.usage);
      }
    }

    // Emit final usage chunk before [DONE].
    const usageChunk: ChatCompletionChunk = {
      id: streamId, object: "chat.completion.chunk", created: createdAt, model: "arbbuilder-chat",
      choices: [{ index: 0, delta: {}, finish_reason: "stop" }],
      usage: totalUsage,
    };
    yield encodeSSEChunk(usageChunk);
    yield encodeSSEDone();
  } catch (e) {
    yield encodeSSEError((e as Error).message || String(e), "internal_error");
    yield encodeSSEDone();
  }

  return { toolCallNames, usage: totalUsage };
}
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd /home/soh/ARBuilder/apps/web && npm test -- agent
```

Expected: PASS (3 tests).

- [ ] **Step 5: Run all tests + tsc**

```bash
cd /home/soh/ARBuilder/apps/web && npm test && npx tsc --noEmit
```

Expected: all tests pass, no tsc errors.

- [ ] **Step 6: Commit**

```bash
cd /home/soh/ARBuilder
git add apps/web/src/lib/chat/agent.ts apps/web/src/lib/chat/agent.test.ts
git commit -m "feat(chat): add ReAct agent loop with continuation"
```

---

### Task 10: `/v1/chat/completions` endpoint

**Files:**
- Create: `apps/web/src/app/api/v1/chat/completions/route.ts`

- [ ] **Step 1: Create the route handler**

Create `apps/web/src/app/api/v1/chat/completions/route.ts`:

```ts
/**
 * POST /api/v1/chat/completions
 *
 * OpenAI-compatible chat completions endpoint backed by a ReAct agent
 * that calls 14 of ARBuilder's MCP tools natively. See:
 *   docs/api/chat-completions.md
 *   docs/superpowers/specs/2026-05-01-chat-endpoint-design.md
 */

import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateRequest } from "@/lib/auth/validateRequest";
import { runAgentNonStreaming, runAgentStreaming } from "@/lib/chat/agent";
import type {
  ChatCompletionRequest,
  ChatCompletionResponse,
  OpenAIErrorBody,
} from "@/lib/chat/types";
import type { ToolEnv } from "@/lib/tools/dispatch";

const MODEL_NAME = "arbbuilder-chat";

function errorResponse(
  message: string,
  type: string,
  status: number,
  code?: string,
): NextResponse {
  const body: OpenAIErrorBody = { error: { message, type, code: code ?? null } };
  return NextResponse.json(body, { status });
}

async function logChatUsage(
  db: D1Database,
  apiKeyId: string,
  toolCallNames: string[],
  totalTokens: number,
  latencyMs: number,
  success: boolean,
  errorMessage?: string,
): Promise<void> {
  try {
    await db
      .prepare(
        `INSERT INTO usage_logs (id, api_key_id, tool, tokens_used, latency_ms, success, error_message, tool_calls, created_at)
         VALUES (?, ?, 'chat', ?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        crypto.randomUUID(),
        apiKeyId,
        totalTokens,
        latencyMs,
        success ? 1 : 0,
        errorMessage ?? null,
        JSON.stringify(toolCallNames),
        new Date().toISOString(),
      )
      .run();
  } catch (e) {
    console.error("Failed to log chat usage:", e);
  }
}

export async function POST(request: NextRequest) {
  const start = Date.now();
  const { env } = getCloudflareContext();

  // Auth — same flow as /api/v1/tools/* and /mcp.
  const auth = await validateRequest(request, env.DB, env.AUTH_SECRET);
  if (!auth.success) {
    return errorResponse(
      "Authentication required. Pass a valid `Authorization: Bearer arb_...` header.",
      "invalid_api_key",
      401,
    );
  }

  // Parse body.
  let body: ChatCompletionRequest;
  try {
    body = (await request.json()) as ChatCompletionRequest;
  } catch {
    return errorResponse("Invalid JSON body.", "invalid_request_error", 400);
  }
  if (!Array.isArray(body.messages) || body.messages.length === 0) {
    return errorResponse(
      "Missing required field 'messages' (must be a non-empty array).",
      "invalid_request_error",
      400,
    );
  }
  if (!env.OPENROUTER_API_KEY) {
    return errorResponse("OpenRouter not configured on this server.", "internal_error", 500);
  }

  const toolEnv: ToolEnv = {
    VECTORIZE: env.VECTORIZE,
    AI: env.AI,
    DB: env.DB,
    OPENROUTER_API_KEY: env.OPENROUTER_API_KEY,
  };

  const opts = {
    temperature: body.temperature ?? 0.3,
    max_tokens: body.max_tokens ?? 32768,
    stop: body.stop,
    signal: request.signal,
  };

  const streamId = `chatcmpl-${crypto.randomUUID()}`;
  const createdAt = Math.floor(Date.now() / 1000);

  // Streaming path.
  if (body.stream === true) {
    const stream = new ReadableStream<Uint8Array>({
      async start(controller) {
        const encoder = new TextEncoder();
        try {
          const gen = runAgentStreaming(body.messages, toolEnv, opts, streamId, createdAt);
          let finalToolCalls: string[] = [];
          let finalUsage = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };
          let next = await gen.next();
          while (!next.done) {
            controller.enqueue(encoder.encode(next.value));
            next = await gen.next();
          }
          if (next.value) {
            finalToolCalls = next.value.toolCallNames;
            finalUsage = next.value.usage;
          }
          if (auth.success && auth.keyId) {
            await logChatUsage(
              env.DB,
              auth.keyId,
              finalToolCalls,
              finalUsage.total_tokens,
              Date.now() - start,
              true,
            );
          }
          controller.close();
        } catch (e) {
          const msg = (e as Error).message || String(e);
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ error: { message: msg, type: "internal_error" } })}\n\n`),
          );
          controller.enqueue(encoder.encode("data: [DONE]\n\n"));
          if (auth.success && auth.keyId) {
            await logChatUsage(env.DB, auth.keyId, [], 0, Date.now() - start, false, msg);
          }
          controller.close();
        }
      },
    });
    return new NextResponse(stream, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      },
    });
  }

  // Non-streaming path.
  try {
    const result = await runAgentNonStreaming(body.messages, toolEnv, opts);
    const response: ChatCompletionResponse = {
      id: streamId,
      object: "chat.completion",
      created: createdAt,
      model: MODEL_NAME,
      choices: [{
        index: 0,
        message: {
          role: "assistant",
          content: result.content,
          reasoning_content: result.reasoning_content || undefined,
        },
        finish_reason: result.finish_reason,
      }],
      usage: result.usage,
    };
    if (auth.keyId) {
      await logChatUsage(
        env.DB, auth.keyId, result.toolCallNames, result.usage.total_tokens, Date.now() - start, true,
      );
    }
    return NextResponse.json(response);
  } catch (e) {
    const msg = (e as Error).message || String(e);
    if (auth.keyId) {
      await logChatUsage(env.DB, auth.keyId, [], 0, Date.now() - start, false, msg);
    }
    return errorResponse(msg, "internal_error", 500);
  }
}

// CORS preflight.
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    },
  });
}
```

- [ ] **Step 2: Run typecheck**

```bash
cd /home/soh/ARBuilder/apps/web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Apply migration to local D1**

```bash
cd /home/soh/ARBuilder/apps/web && npx wrangler d1 execute arbbuilder --local --file=./migrations/0004_chat_tool_calls.sql
```

(If the local DB binding name differs, look at `wrangler.jsonc` for the actual `database_name` and substitute. Skip this step if you don't run the local DB yet — the production migration runs on deploy.)

- [ ] **Step 4: Manual smoke test (non-streaming)**

```bash
cd /home/soh/ARBuilder/apps/web && npm run dev &
sleep 6
curl -s -X POST http://localhost:3000/api/v1/chat/completions \
  -H "Authorization: Bearer arb_REPLACE_WITH_REAL_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "arbbuilder-chat",
    "messages": [{"role":"user","content":"Explain Stylus storage mappings briefly."}],
    "stream": false
  }' | jq .
kill %1
```

Expected: JSON body with `choices[0].message.content` non-empty and at least one tool call name in the D1 `usage_logs.tool_calls`. (Skip if no key available; tsc + tests already validate shape.)

- [ ] **Step 5: Manual smoke test (streaming)**

```bash
cd /home/soh/ARBuilder/apps/web && npm run dev &
sleep 6
curl -N -X POST http://localhost:3000/api/v1/chat/completions \
  -H "Authorization: Bearer arb_REPLACE_WITH_REAL_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "arbbuilder-chat",
    "messages": [{"role":"user","content":"Generate a tiny ERC20 in Stylus."}],
    "stream": true
  }'
kill %1
```

Expected: stream of `data: {...}` chunks ending with `data: [DONE]`. Reasoning chunks (`reasoning_content` deltas) and tool-call deltas should both appear.

- [ ] **Step 6: Commit**

```bash
cd /home/soh/ARBuilder
git add apps/web/src/app/api/v1/chat/completions/route.ts
git commit -m "feat(chat): add /v1/chat/completions endpoint"
```

---

### Task 11: API documentation

**Files:**
- Create: `docs/api/chat-completions.md`

- [ ] **Step 1: Write documentation**

Create `docs/api/chat-completions.md`:

````markdown
# Chat Completions API

OpenAI-compatible chat completions endpoint backed by a ReAct agent over ARBuilder's MCP tools. Use any standard OpenAI SDK pointed at this endpoint to chat about Arbitrum, Stylus, and Orbit chain development.

## Endpoint

```
POST https://<your-arbbuilder-host>/api/v1/chat/completions
```

## Authentication

Pass an ARBuilder API key as a Bearer token. Get one from `/dashboard/keys`.

```
Authorization: Bearer arb_<your-key>
```

## Models

Only one model name is accepted (other values are silently aliased to it):

| Model | Backing | Max output tokens |
|---|---|---|
| `arbbuilder-chat` | `openai/gpt-oss-120b` via OpenRouter | 32 768 |

## Request body

| Field | Type | Default | Notes |
|---|---|---|---|
| `model` | string | required | `"arbbuilder-chat"` |
| `messages` | array | required | OpenAI message array. `role`: `system` / `user` / `assistant` / `tool`. |
| `stream` | boolean | `false` | If true, returns SSE. |
| `temperature` | number | `0.3` | 0–2. |
| `max_tokens` | number | model max | Per-call cap; auto-capped at upstream max. |
| `stop` | string \| string[] | none | Forwarded unchanged. |
| `tools` / `tool_choice` | — | ignored | Server controls the tool set. |

`messages` follows OpenAI conventions:

```json
[
  { "role": "system", "content": "Optional extra system context" },
  { "role": "user", "content": "Generate an ERC20 in Stylus" },
  { "role": "assistant", "content": "...", "tool_calls": [...] },
  { "role": "tool", "tool_call_id": "call_abc", "content": "..." }
]
```

The endpoint is **stateless** — the client must send the full conversation history each turn. There is no server-side conversation persistence.

## Tool surface

The agent has access to **14 tools** covering:

- Stylus contracts: `get_stylus_context`, `generate_stylus_code`, `ask_stylus`, `generate_tests`, `get_workflow`
- Arbitrum SDK bridging/messaging: `generate_bridge_code`, `generate_messaging_code`, `ask_bridging`
- Orbit chain deployment: `generate_orbit_config`, `generate_orbit_deployment`, `generate_validator_setup`, `ask_orbit`
- Indexers and oracles: `generate_indexer`, `generate_oracle`

The agent decides when to call which tool based on the user's request. Tool definitions match the schemas exposed at `POST /mcp` (`tools/list` method).

The 4 large project scaffolders (`generate_backend`, `generate_frontend`, `orchestrate_dapp`, `orchestrate_orbit`) are **not** exposed in chat — call them directly via `POST /api/v1/tools/<name>` or via MCP.

## Non-streaming response

```json
{
  "id": "chatcmpl-<uuid>",
  "object": "chat.completion",
  "created": 1730000000,
  "model": "arbbuilder-chat",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Here's the contract you asked for...",
      "reasoning_content": "[Step 1] I should check the storage docs first..."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 1234,
    "completion_tokens": 567,
    "total_tokens": 1801
  }
}
```

`reasoning_content` is the chain-of-thought emitted by the model across all ReAct iterations, sectioned by `[Step N]`. Strict OpenAI clients ignore this field.

## Streaming response (`stream: true`)

`Content-Type: text/event-stream`. Standard OpenAI `chat.completion.chunk` deltas:

```
data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant"}}]}

data: {"id":"...","choices":[{"index":0,"delta":{"reasoning_content":"I should check the docs..."}}]}

data: {"id":"...","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"call_abc","type":"function","function":{"name":"get_stylus_context","arguments":"{\"que"}}]}}]}

data: {"id":"...","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"ry\":\"mappings\"}"}}]}}]}

data: {"id":"...","choices":[{"index":0,"delta":{"reasoning_content":"Now I have the docs..."}}]}

data: {"id":"...","choices":[{"index":0,"delta":{"content":"Here's the contract..."}}]}

data: {"id":"...","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":1234,"completion_tokens":567,"total_tokens":1801}}

data: [DONE]
```

Notes:
- Tool **calls** are visible in deltas as standard `delta.tool_calls`. Tool **results** are not emitted on the wire — they stay server-internal and the model references them naturally in its next-iteration text.
- Length-continuations (when the upstream returns `finish_reason: "length"` and the agent auto-continues) are invisible to the client. The stream looks seamless.
- The final non-`[DONE]` chunk includes `usage` totals across all internal LLM calls during the turn.
- A mid-stream error is emitted as `data: {"error": {...}}` followed by `data: [DONE]`. HTTP status remains 200 because headers were already sent.

## Errors

OpenAI shape:

```json
{ "error": { "message": "...", "type": "...", "code": null } }
```

| Status | `type` | When |
|---|---|---|
| 400 | `invalid_request_error` | Body missing `messages` or invalid JSON. |
| 401 | `invalid_api_key` | Missing or invalid `Authorization` header. |
| 429 | `rate_limit_exceeded` | OpenRouter upstream rate limit. |
| 500 | `internal_error` | Server misconfiguration (missing OpenRouter key) or pre-stream failure. |
| 502 | `upstream_error` | OpenRouter returned a non-retryable 4xx/5xx. |

Mid-stream errors are surfaced as a `data:` frame, not an HTTP status change.

## Limits

| Limit | Value |
|---|---|
| Max ReAct iterations per turn | 6 |
| Max length-continuations per iteration | 3 |
| Total turn output budget | 200 000 tokens |
| Max single tool result fed back to model | 32 000 chars (~8K tokens, then truncated) |
| Max parallel tool calls per iteration | unbounded (model's choice) |

If a turn hits the iteration cap, the agent runs one final no-tools wrap-up call and returns its answer with `finish_reason: "length"`. If the total token budget is exceeded mid-turn, the stream is closed cleanly with a truncation note.

## Examples

### Curl, non-streaming

```bash
curl -X POST https://api.arbuilder.app/api/v1/chat/completions \
  -H "Authorization: Bearer arb_xxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "arbbuilder-chat",
    "messages": [
      { "role": "user", "content": "Generate a simple ERC20 in Stylus" }
    ]
  }'
```

### Curl, streaming

```bash
curl -N -X POST https://api.arbuilder.app/api/v1/chat/completions \
  -H "Authorization: Bearer arb_xxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "arbbuilder-chat",
    "messages": [{ "role": "user", "content": "How do I bridge ETH from L1 to L2?" }],
    "stream": true
  }'
```

### Python (openai SDK)

```python
from openai import OpenAI

client = OpenAI(
    api_key="arb_xxxxx",
    base_url="https://api.arbuilder.app/api/v1",
)

resp = client.chat.completions.create(
    model="arbbuilder-chat",
    messages=[{"role": "user", "content": "What is AnyTrust on Orbit chains?"}],
)
print(resp.choices[0].message.content)
```

### Python streaming

```python
stream = client.chat.completions.create(
    model="arbbuilder-chat",
    messages=[{"role": "user", "content": "Generate an ERC721 in Stylus"}],
    stream=True,
)
for chunk in stream:
    delta = chunk.choices[0].delta
    if getattr(delta, "reasoning_content", None):
        print(f"[thinking] {delta.reasoning_content}", end="")
    if delta.content:
        print(delta.content, end="", flush=True)
    if delta.tool_calls:
        for tc in delta.tool_calls:
            if tc.function and tc.function.name:
                print(f"\n[tool] {tc.function.name}", end="")
```

### TypeScript (openai SDK)

```ts
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: "arb_xxxxx",
  baseURL: "https://api.arbuilder.app/api/v1",
});

const stream = await client.chat.completions.create({
  model: "arbbuilder-chat",
  messages: [{ role: "user", content: "Show me how to deploy an Orbit rollup" }],
  stream: true,
});

for await (const chunk of stream) {
  const delta = chunk.choices[0]?.delta;
  if ((delta as { reasoning_content?: string }).reasoning_content) {
    process.stdout.write((delta as { reasoning_content?: string }).reasoning_content!);
  }
  if (delta?.content) process.stdout.write(delta.content);
}
```

## Comparison with `/api/v1/tools/*` and `/mcp`

| Surface | Use when |
|---|---|
| `POST /api/v1/chat/completions` | You want conversational, multi-tool, intent-routed answers. Compatible with any OpenAI SDK. |
| `POST /api/v1/tools/<name>` | You know exactly which tool to call and want a deterministic single-call response. |
| `POST /mcp` (JSON-RPC) | You're an MCP client (Cursor, Claude Desktop, etc.) and want to expose individual tools to your own LLM. |

All three share the same authentication and the same underlying tool implementations.
````

- [ ] **Step 2: Commit**

```bash
cd /home/soh/ARBuilder
git add docs/api/chat-completions.md
git commit -m "docs(api): document /v1/chat/completions endpoint"
```

---

### Task 12: Playground chat UI

**Files:**
- Create: `apps/web/src/app/playground/chat/page.tsx`
- Modify: `apps/web/src/app/playground/page.tsx` (add link to chat)

- [ ] **Step 1: Add link from /playground to /playground/chat**

In `apps/web/src/app/playground/page.tsx`, find the header section (around line 776–807, look for the `<header>` block) and replace the inner content of the `flex justify-between items-center` div with:

Locate this block (around line 786):

```tsx
            <span className="text-gray-300 hidden sm:block">/</span>
            <span className="text-gray-600 font-medium">Playground</span>
          </div>
```

Replace with:

```tsx
            <span className="text-gray-300 hidden sm:block">/</span>
            <span className="text-gray-600 font-medium">Playground · Tools</span>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/playground/chat"
              className="px-3 py-1.5 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            >
              Switch to Chat →
            </Link>
          </div>
```

Note: there's already a `<div>` for the user info on the right side. The new link should be added BEFORE that div, not replacing it. After this change, the header will have: logo / "Playground · Tools" on the left, [Switch to Chat] + user info on the right.

Look at the existing structure carefully — the existing right-side div with `sessionUser` should remain as the third flex child. If there's only one wrapping flex container, wrap the existing right-side div and the new chat link in a single flex group.

- [ ] **Step 2: Create the chat page**

Create `apps/web/src/app/playground/chat/page.tsx`:

```tsx
"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";

interface SessionUser {
  id: string;
  email: string;
  name?: string | null;
}

interface ApiKey {
  id: string;
  keyPrefix: string;
  name: string | null;
  createdAt: string;
  lastUsedAt: string | null;
}

type AuthMode = "session" | "apikey";

interface ToolCallView {
  id: string;
  name: string;
  arguments: string;
}

interface ChatMessageView {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning?: string;
  reasoningOpen?: boolean;
  toolCalls: ToolCallView[];
  streaming?: boolean;
}

export default function ChatPlaygroundPage() {
  const [messages, setMessages] = useState<ChatMessageView[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auth state (mirrors /playground/page.tsx for consistency)
  const [sessionUser, setSessionUser] = useState<SessionUser | null>(null);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [userKeys, setUserKeys] = useState<ApiKey[]>([]);
  const [authMode, setAuthMode] = useState<AuthMode>("session");
  const [apiKey, setApiKey] = useState("");

  useEffect(() => {
    async function init() {
      try {
        const res = await fetch("/api/auth/session");
        const data = (await res.json()) as { user: SessionUser | null };
        if (data.user) {
          setSessionUser(data.user);
          setAuthMode("session");
          const keysRes = await fetch("/api/keys");
          if (keysRes.ok) {
            const keysData = (await keysRes.json()) as { keys: ApiKey[] };
            setUserKeys(keysData.keys || []);
          }
        } else {
          setAuthMode("apikey");
        }
      } catch {
        setAuthMode("apikey");
      } finally {
        setSessionLoading(false);
      }
    }
    init();
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = useCallback(async () => {
    if (!input.trim() || streaming) return;
    setError(null);

    const userMsg: ChatMessageView = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
      toolCalls: [],
    };
    const assistantMsg: ChatMessageView = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      reasoning: "",
      toolCalls: [],
      streaming: true,
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (authMode === "apikey" && apiKey) {
      headers["Authorization"] = `Bearer ${apiKey}`;
    }

    // Build OpenAI-shape messages from history (drop view-only fields).
    const wireMessages = [...messages, userMsg].map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const res = await fetch("/api/v1/chat/completions", {
        method: "POST",
        headers,
        credentials: "include",
        signal: controller.signal,
        body: JSON.stringify({
          model: "arbbuilder-chat",
          messages: wireMessages,
          stream: true,
        }),
      });

      if (!res.ok || !res.body) {
        const errBody = await res.json().catch(() => ({ error: { message: `HTTP ${res.status}` } }));
        throw new Error(errBody.error?.message || `HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      // Track tool_calls being assembled across deltas.
      const toolCallAcc: Map<number, ToolCallView> = new Map();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let frameEnd: number;
        while ((frameEnd = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, frameEnd);
          buffer = buffer.slice(frameEnd + 2);
          for (const line of frame.split("\n")) {
            const trimmed = line.trim();
            if (!trimmed.startsWith("data:")) continue;
            const data = trimmed.slice(5).trim();
            if (data === "[DONE]") continue;
            let chunk: { error?: { message: string }; choices?: Array<{ delta?: { content?: string; reasoning_content?: string; tool_calls?: Array<{ index: number; id?: string; function?: { name?: string; arguments?: string } }> } }> };
            try { chunk = JSON.parse(data); } catch { continue; }

            if (chunk.error) {
              throw new Error(chunk.error.message);
            }

            const delta = chunk.choices?.[0]?.delta;
            if (!delta) continue;

            if (delta.reasoning_content) {
              setMessages((prev) => {
                const copy = [...prev];
                const last = copy[copy.length - 1];
                copy[copy.length - 1] = { ...last, reasoning: (last.reasoning ?? "") + delta.reasoning_content };
                return copy;
              });
            }
            if (delta.content) {
              setMessages((prev) => {
                const copy = [...prev];
                const last = copy[copy.length - 1];
                copy[copy.length - 1] = { ...last, content: last.content + delta.content };
                return copy;
              });
            }
            if (delta.tool_calls) {
              for (const tc of delta.tool_calls) {
                const existing = toolCallAcc.get(tc.index) ?? {
                  id: tc.id ?? `call_${tc.index}`,
                  name: "",
                  arguments: "",
                };
                if (tc.function?.name) existing.name = tc.function.name;
                if (tc.function?.arguments) existing.arguments += tc.function.arguments;
                if (tc.id) existing.id = tc.id;
                toolCallAcc.set(tc.index, existing);
              }
              const calls = Array.from(toolCallAcc.values());
              setMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = { ...copy[copy.length - 1], toolCalls: calls };
                return copy;
              });
            }
          }
        }
      }
    } catch (e) {
      if ((e as Error).name === "AbortError") {
        // user cancelled — keep partial state
      } else {
        setError((e as Error).message);
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
      setMessages((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        if (last && last.role === "assistant") {
          copy[copy.length - 1] = { ...last, streaming: false };
        }
        return copy;
      });
    }
  }, [input, streaming, messages, authMode, apiKey]);

  function stop() {
    abortRef.current?.abort();
  }

  function clearConversation() {
    if (streaming) return;
    setMessages([]);
    setError(null);
  }

  function toggleReasoning(id: string) {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, reasoningOpen: !m.reasoningOpen } : m)),
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">AR</span>
              </div>
              <span className="text-xl font-bold text-gray-900 hidden sm:block">ARBuilder</span>
            </Link>
            <span className="text-gray-300 hidden sm:block">/</span>
            <span className="text-gray-600 font-medium">Playground · Chat</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/playground" className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg">
              Tools view
            </Link>
            {sessionLoading ? null : sessionUser ? (
              <span className="text-sm text-gray-500 hidden sm:block">{sessionUser.email}</span>
            ) : (
              <Link href="/login" className="text-blue-600 hover:text-blue-700 font-medium">Sign In</Link>
            )}
          </div>
        </div>
      </header>

      {/* Auth strip when no session and using API key */}
      {!sessionLoading && !sessionUser && (
        <div className="bg-amber-50 border-b border-amber-100 px-4 py-2 text-center">
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Paste arb_... API key to continue"
            className="text-sm border border-amber-200 rounded-lg px-3 py-1 w-80 max-w-full"
          />
        </div>
      )}
      {!sessionLoading && sessionUser && userKeys.length > 0 && (
        <div className="bg-white border-b border-gray-100 px-4 py-2 flex items-center gap-2 justify-end max-w-5xl mx-auto w-full">
          <span className="text-xs text-gray-500">Auth:</span>
          <button
            onClick={() => setAuthMode("session")}
            className={`text-xs px-2 py-1 rounded ${authMode === "session" ? "bg-blue-100 text-blue-700" : "text-gray-500 hover:bg-gray-100"}`}
          >Session</button>
          <button
            onClick={() => setAuthMode("apikey")}
            className={`text-xs px-2 py-1 rounded ${authMode === "apikey" ? "bg-blue-100 text-blue-700" : "text-gray-500 hover:bg-gray-100"}`}
          >API Key</button>
          {authMode === "apikey" && (
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="arb_..."
              className="text-xs border border-gray-200 rounded px-2 py-1 w-48"
            />
          )}
        </div>
      )}

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-6 flex flex-col gap-4">
        <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-4 pr-2" style={{ minHeight: "60vh" }}>
          {messages.length === 0 && (
            <div className="text-center text-gray-400 py-20">
              <p className="text-lg">Ask anything about Stylus, Arbitrum SDK, or Orbit chains.</p>
              <p className="text-sm mt-2">The assistant has 14 tools at its disposal and will call them automatically.</p>
            </div>
          )}
          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-3xl rounded-2xl px-4 py-3 ${m.role === "user" ? "bg-blue-600 text-white" : "bg-white border border-gray-100 shadow-sm"}`}>
                {m.role === "assistant" && m.reasoning && (
                  <button
                    onClick={() => toggleReasoning(m.id)}
                    className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1 mb-2"
                  >
                    <span>{m.reasoningOpen ? "▾" : "▸"}</span>
                    Thinking ({m.reasoning.length} chars)
                  </button>
                )}
                {m.role === "assistant" && m.reasoningOpen && m.reasoning && (
                  <pre className="text-xs text-gray-500 whitespace-pre-wrap mb-3 bg-gray-50 rounded-lg p-2 border border-gray-100">
                    {m.reasoning}
                  </pre>
                )}
                {m.toolCalls.length > 0 && (
                  <div className="space-y-1 mb-2">
                    {m.toolCalls.map((tc) => (
                      <div key={tc.id} className="text-xs font-mono bg-gray-50 border border-gray-200 rounded px-2 py-1">
                        🔧 <span className="text-blue-700">{tc.name}</span>
                        <span className="text-gray-500"> ({tc.arguments.length > 80 ? tc.arguments.slice(0, 80) + "…" : tc.arguments})</span>
                      </div>
                    ))}
                  </div>
                )}
                <div className="whitespace-pre-wrap text-sm">{m.content || (m.streaming ? "…" : "")}</div>
              </div>
            </div>
          ))}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-100 text-red-700 px-4 py-2 rounded-xl text-sm">
            {error}
          </div>
        )}

        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-3 flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            disabled={streaming}
            placeholder="Ask about Stylus, bridging, or Orbit chains..."
            rows={2}
            className="flex-1 resize-none border-0 focus:ring-0 outline-none text-sm py-2 px-3"
          />
          <div className="flex flex-col gap-2">
            <button
              onClick={clearConversation}
              disabled={streaming || messages.length === 0}
              className="px-3 py-2 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Clear
            </button>
            {streaming ? (
              <button
                onClick={stop}
                className="px-4 py-2 bg-red-500 text-white rounded-lg text-sm font-medium hover:bg-red-600"
              >
                Stop
              </button>
            ) : (
              <button
                onClick={send}
                disabled={!input.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                Send
              </button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Run typecheck**

```bash
cd /home/soh/ARBuilder/apps/web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Manual test**

```bash
cd /home/soh/ARBuilder/apps/web && npm run dev
```

Open http://localhost:3000/playground/chat in a browser. Sign in, then send messages:
- "Explain Stylus mappings briefly" → expect `ask_stylus` tool-call card, then a streamed answer.
- "Generate a tiny ERC20 in Stylus" → expect `get_stylus_context` then `generate_stylus_code` cards, then a code block in the answer.
- "What's the weather?" → expect a polite refusal, no tool calls.

Verify the "Thinking" panel renders reasoning for each assistant turn, expandable.

- [ ] **Step 5: Commit**

```bash
cd /home/soh/ARBuilder
git add apps/web/src/app/playground/chat/page.tsx apps/web/src/app/playground/page.tsx
git commit -m "feat(playground): add chat UI at /playground/chat"
```

---

### Task 13: Final verification and PR prep

- [ ] **Step 1: Full test suite**

```bash
cd /home/soh/ARBuilder/apps/web && npm test && npx tsc --noEmit && npm run lint
```

Expected: all tests pass, no tsc errors, no new lint errors.

- [ ] **Step 2: Update README index**

Edit `apps/web/README.md` (if it has an "API Endpoints" or similar section) to add a row for the new endpoint pointing at `docs/api/chat-completions.md`. If the README has no such section, skip — the docs file is discoverable directly.

Also append to `/home/soh/ARBuilder/CLAUDE.md` under "MCP Tools Reference" (or in a new section near the bottom):

```md
## Chat Endpoint (OpenAI-compatible)

`POST /api/v1/chat/completions` exposes a ReAct agent over 14 of the MCP tools as an OpenAI-compatible endpoint. See `docs/api/chat-completions.md`. Playground UI at `/playground/chat`.
```

- [ ] **Step 3: Commit doc updates**

```bash
cd /home/soh/ARBuilder
git add CLAUDE.md apps/web/README.md
git commit -m "docs: link chat endpoint from README and CLAUDE.md"
```

(Skip the README edit if the file has no sensible section for it.)

- [ ] **Step 4: Push branch and open PR**

```bash
cd /home/soh/ARBuilder
git push -u origin feat/chat-endpoint
```

Then via `gh`:

```bash
gh pr create --title "feat: OpenAI-compatible chat endpoint with ReAct agent" --body "$(cat <<'EOF'
## Summary

- New `POST /api/v1/chat/completions` endpoint, OpenAI-compatible (works with the official `openai` SDK).
- ReAct agent loop over 14 of ARBuilder's MCP tools (lightweight ones; the 4 big scaffolders stay form-only).
- Strict OpenAI streaming format with one additive field (`delta.reasoning_content`) for chain-of-thought.
- Auto-continuation across `finish_reason: "length"` so long answers stream seamlessly.
- New `/playground/chat` UI consuming the endpoint.
- API documentation at `docs/api/chat-completions.md`.

## Test plan

- [ ] `npm test` passes (unit tests for agent loop, tool dispatch, streaming, max-tokens helper)
- [ ] `npx tsc --noEmit` clean
- [ ] Manual: non-streaming curl returns valid OpenAI-shape JSON
- [ ] Manual: streaming curl emits valid SSE chunks ending in `[DONE]`
- [ ] Manual: `/playground/chat` renders reasoning, tool-call cards, and streamed answers
- [ ] Manual: `/mcp` JSON-RPC endpoint still works after dispatch refactor (smoke test `tools/list`)
- [ ] Migration `0004_chat_tool_calls.sql` applies cleanly

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: PR URL printed.

---

## Self-Review Checklist (run after writing the plan)

- [x] Spec coverage: every section of the spec has a corresponding task (architecture → tasks 4/5/6/9/10; types → 2; system prompt → 3; tool defs → 7; streaming helpers → 8; agent → 9; endpoint → 10; docs → 11; UI → 12; migration → 1)
- [x] No placeholders: searched for TBD/TODO/FIXME — none in the plan
- [x] Type consistency: `ToolEnv`, `ChatMessage`, `IterationAccumulator`, `ToolCallAccumulator`, `runTool`, `executeToolCall`, `runAgentNonStreaming`, `runAgentStreaming` referenced in later tasks all defined in earlier ones
- [x] Bite-sized: each task averages 4–6 steps, each step is one focused action
- [x] Frequent commits: every task ends with a commit

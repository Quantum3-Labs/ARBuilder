# Chat Endpoint — OpenAI-Compatible ReAct Agent

**Date:** 2026-05-01
**Status:** Design approved, pending implementation plan

## Goal

Add a chat endpoint to ARBuilder that:
1. Accepts free-form user messages and routes intent to MCP tools automatically.
2. Exposes an OpenAI-compatible `/v1/chat/completions` HTTP API so any standard OpenAI SDK can call it.
3. Powers a new `/playground/chat` UI that complements the existing form-based tool picker at `/playground`.

The endpoint runs a **ReAct agent loop** with **native LLM tool calling** over a curated subset of 14 lightweight MCP tools. It supports both streaming (SSE) and non-streaming responses, streams reasoning content per the de-facto OpenAI-ecosystem convention, and continues automatically past `finish_reason: "length"` to deliver seamlessly long answers.

## Non-Goals

- Server-side conversation persistence. The API is stateless — clients send the full message history each turn.
- Multi-tenant rate limiting beyond what existing API key infrastructure provides.
- Replacing the existing tool picker at `/playground`. The chat UI is a sibling page.
- Exposing the 4 large-scaffolding tools (`generate_backend`, `generate_frontend`, `orchestrate_dapp`, `orchestrate_orbit`) through chat. Their output sizes (50–200KB JSON) make them unsuitable for ReAct context budgets. They remain form-only.
- Native MCP protocol exposure of the chat capability. MCP clients (Cursor, Claude Desktop) already do their own tool selection — adding a chat tool there would be redundant.

## Architecture

```
Client ──► POST /api/v1/chat/completions  (OpenAI-shape body, Bearer arb_...)
            │
            ▼
       authenticate (lib/apiKeys.ts) ──► D1.api_keys
            │
            ▼
       ReAct loop  (max 6 iterations)
       ┌──────────────────────────────────────┐
       │  callWithContinuation(messages, tools)│
       │     ├─ openrouter call                │
       │     ├─ if finish_reason="length"      │
       │     │     append partial assistant    │
       │     │     loop up to 3 continuations  │
       │     └─ return accumulated turn        │
       │                                       │
       │  if no tool_calls in result:          │
       │      → emit final, return             │
       │  else:                                │
       │      execute tool_calls in parallel   │
       │      append role:tool messages        │
       │      iterate                          │
       └──────────────────────────────────────┘
            │
            ▼
       SSE chunks (stream:true) or JSON (stream:false)
            │
            ▼
       log usage to D1.usage_logs (one row per turn)
```

## Endpoint

**`POST /api/v1/chat/completions`**

Request body (OpenAI standard, fields not listed are ignored):

| Field | Type | Default | Notes |
|---|---|---|---|
| `model` | string | required | Accepts `"arbbuilder-chat"` as canonical; other values silently aliased. |
| `messages` | array | required | Standard OpenAI message array (`role`: `system`/`user`/`assistant`/`tool`). |
| `stream` | boolean | `false` | When `true`, returns SSE stream. |
| `temperature` | number | `0.3` | Honored (forwarded to OpenRouter). |
| `max_tokens` | number | model max (32768 for gpt-oss-120b) | Per-call cap. Honored if smaller; ignored if larger. |
| `stop` | string \| string[] | none | Forwarded unchanged on every continuation pass. |
| `tools` | array | ignored | Server controls the tool set. |
| `tool_choice` | string \| object | ignored | Server controls. |

Auth: `Authorization: Bearer arb_...` — same flow as `/api/v1/tools/*` and `/mcp`. Validated via `lib/apiKeys.ts`. `last_used_at` updated on success.

### Non-streaming response (`stream: false`)

Standard OpenAI shape:

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
      "content": "<final answer>",
      "reasoning_content": "[Step 1] <reasoning>\n[Step 2] <reasoning>"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": <sum across all internal LLM calls>,
    "completion_tokens": <sum>,
    "total_tokens": <sum>
  }
}
```

`reasoning_content` (additive, non-OpenAI-spec) is the concatenation of per-iteration reasoning emitted by `gpt-oss-120b`. Sectioned with `[Step N]` headers. Strict OpenAI clients ignore it; ecosystem clients (DeepSeek SDK, OpenRouter SDK, our playground) render it.

### Streaming response (`stream: true`)

`Content-Type: text/event-stream`. Standard OpenAI `chat.completion.chunk` deltas:

```
data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant"}}]}

data: {"id":"...","choices":[{"index":0,"delta":{"reasoning_content":"I should check the docs first..."}}]}

data: {"id":"...","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"call_abc","type":"function","function":{"name":"get_stylus_context","arguments":"{\"que"}}]}}]}

data: {"id":"...","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"ry\":\"mappings\"}"}}]}}]}

(server executes tool, appends role:tool message, calls model again — no client-visible event)

data: {"id":"...","choices":[{"index":0,"delta":{"reasoning_content":"Now I have the docs. I'll generate..."}}]}

data: {"id":"...","choices":[{"index":0,"delta":{"content":"Here's the contract:"}}]}

data: {"id":"...","choices":[{"index":0,"delta":{"content":" ```rust\n..."}}]}

data: {"id":"...","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{...}}

data: [DONE]
```

Notes:
- Tool *calls* are visible to the client as standard `delta.tool_calls` (the model announces them). Tool *results* are not emitted on the wire — they stay server-internal and are referenced indirectly through the model's next-iteration text.
- `usage` is emitted in the final non-`[DONE]` chunk (matches OpenRouter convention).
- Continuations across `finish_reason: "length"` are invisible — the client sees one continuous stream.

### Errors

OpenAI shape: `{ "error": { "message", "type", "code" } }`.

| Condition | HTTP | `type` |
|---|---|---|
| Missing/invalid Bearer key | 401 | `invalid_api_key` |
| Malformed body (no `messages`) | 400 | `invalid_request_error` |
| OpenRouter upstream 4xx (not 401/429) | 502 | `upstream_error` |
| OpenRouter rate limit | 429 | `rate_limit_exceeded` |
| Tool execution throws | n/a — injected as `role:tool` content `{"error": "..."}` so model can react |
| Pre-stream internal error | 500 | `internal_error` |
| Mid-stream internal error | 200 | SSE event `data: {"error": {...}}` then `data: [DONE]` |
| Total turn budget exceeded mid-stream | 200 | final assistant chunk with `finish_reason: "length"`, then `[DONE]` |

## ReAct Loop (`lib/chat/agent.ts`)

```ts
const MAX_ITER = 6;
const MAX_CONT = 3;
const TOTAL_TURN_BUDGET_TOKENS = 200_000;

async function* runAgent(initialMessages, env, opts):
    let messages = [SYSTEM_PROMPT, ...initialMessages];
    let totalUsage = zero;
    let allReasoning: string[] = [];

    for (let iter = 0; iter < MAX_ITER; iter++) {
        const turn = await callWithContinuation(messages, ARBBUILDER_TOOL_DEFS, {
            stream: opts.stream,
            temperature: opts.temperature,
            max_tokens: opts.max_tokens,
            onChunk: opts.stream ? (chunk) => yield translateChunk(chunk) : undefined,
        });

        totalUsage = sumUsage(totalUsage, turn.usage);
        if (turn.reasoning) allReasoning.push(`[Step ${iter+1}] ${turn.reasoning}`);

        if (totalUsage.total_tokens > TOTAL_TURN_BUDGET_TOKENS) {
            yield emitGracefulCutoff();
            return;
        }

        if (turn.tool_calls.length === 0) {
            // model emitted final answer
            return { content: turn.content, reasoning: allReasoning.join("\n"), usage: totalUsage, finish_reason: "stop" };
        }

        // execute tools in parallel
        messages.push({ role: "assistant", content: turn.content, tool_calls: turn.tool_calls });
        const results = await Promise.all(turn.tool_calls.map(tc => executeToolCall(tc, env)));
        for (const r of results) {
            messages.push({ role: "tool", tool_call_id: r.tool_call_id, content: r.content });
        }
    }

    // hit MAX_ITER — wrap up
    return await forceFinalAnswer(messages, totalUsage, allReasoning);
```

### `callWithContinuation`

Wraps a single OpenRouter call with auto-continuation on `finish_reason: "length"`. Up to 3 continuation passes per iteration. Continuation message construction:

```ts
msgs = [...originalMessages, {
    role: "assistant",
    content: accumulated.content,
    tool_calls: accumulated.tool_calls,  // partial tool args okay; model continues string-concat by index
}];
```

Tool-call argument accumulation: each streaming chunk's `tool_calls[i].function.arguments` (a string) is appended to the accumulator at index `i`. Tool calls execute only after the iteration's `finish_reason` is non-`length` and `JSON.parse(arguments)` succeeds. If after 3 continuations a tool call's arguments still don't parse, drop the tool call and inject a `role:tool` message: `{"error": "Tool arguments truncated and could not be recovered"}`.

### Cap exhaustion at MAX_ITER

After 6 iterations without a final answer, do one more LLM call with no tools and a synthetic user message: `"Wrap up your reasoning into a final answer for the user. Do not call any more tools."` Return that as the final.

### Per-tool max output / model max

In `lib/openrouter.ts`:

```ts
export const MODEL_MAX_OUTPUT_TOKENS: Record<string, number> = {
  "openai/gpt-oss-120b": 32768,
};

export function getMaxTokens(model: string, requested?: number): number {
  const cap = MODEL_MAX_OUTPUT_TOKENS[model] ?? 4096;
  return requested ? Math.min(requested, cap) : cap;
}
```

OpenRouter call body includes `{ "reasoning": { "effort": "medium" } }` for gpt-oss-120b to emit chain-of-thought.

## Tool Surface

The chat agent exposes **14 of the 18 MCP tools** — the 4 big scaffolders (`generate_backend`, `generate_frontend`, `orchestrate_dapp`, `orchestrate_orbit`) are excluded.

**Included (14):**

| Tool | Module | Notes |
|---|---|---|
| `get_stylus_context` | M1 Stylus | RAG retrieval |
| `generate_stylus_code` | M1 Stylus | Single-file contract |
| `ask_stylus` | M1 Stylus | Q&A |
| `generate_tests` | M1 Stylus | Test generation |
| `get_workflow` | M1 Stylus | Build/deploy steps |
| `generate_bridge_code` | M2 SDK | Bridge snippets |
| `generate_messaging_code` | M2 SDK | Cross-chain message snippets |
| `ask_bridging` | M2 SDK | Q&A |
| `generate_indexer` | M3 dApp | Subgraph |
| `generate_oracle` | M3 dApp | Chainlink integrations |
| `generate_orbit_config` | M4 Orbit | Chain config |
| `generate_orbit_deployment` | M4 Orbit | Rollup/bridge deploy code |
| `generate_validator_setup` | M4 Orbit | Validator/keyset management |
| `ask_orbit` | M4 Orbit | Q&A |

**Excluded (4):** `generate_backend`, `generate_frontend`, `orchestrate_dapp`, `orchestrate_orbit`. Available via existing form picker only.

### Tool definitions and dispatch

`lib/chat/toolDefs.ts` exports:

```ts
export const ARBBUILDER_TOOL_DEFS: OpenAITool[] = [
  { type: "function", function: { name: "get_stylus_context", description: "...", parameters: { ... } } },
  // ... 13 more
];

export async function executeToolCall(
  tc: ToolCall,
  env: Env,
): Promise<{ tool_call_id: string; content: string }> {
  const args = JSON.parse(tc.function.arguments);
  const result = await runTool(tc.function.name, args, env);
  return {
    tool_call_id: tc.id,
    content: serializeToolResult(result),
  };
}
```

### Shared `runTool` dispatch

`lib/tools/dispatch.ts` (new) extracts the `handleToolCall` switch statement currently inside `app/mcp/route.ts` so the same dispatch table powers `/mcp`, `/api/v1/tools/*` (each route can use it instead of inlining), and the new chat endpoint. Reduces duplication and prevents drift between MCP tool args and chat tool args.

### Tool result serialization

`serializeToolResult`:
1. `JSON.stringify(result, null, 2)`
2. If `> 32_000` chars (~8000 tokens), replace with `{"truncated": true, "summary": "<schema-aware summary>", "original_size_chars": N}`. Schema-aware: for the 14 chat tools we know the result shapes — pick relevant fields. For unknown shapes, take first 16K chars verbatim and append `"... [truncated]"`.

## System Prompt (`lib/chat/systemPrompt.ts`)

```
You are ARBuilder, an AI assistant for Arbitrum and Stylus development.

You have 14 tools covering:
- Stylus smart contracts (Rust/WASM): get_stylus_context, generate_stylus_code, ask_stylus, generate_tests, get_workflow
- Arbitrum SDK bridging and messaging: generate_bridge_code, generate_messaging_code, ask_bridging
- Orbit chain deployment: generate_orbit_config, generate_orbit_deployment, generate_validator_setup, ask_orbit
- Indexers and oracles: generate_indexer, generate_oracle

Rules:
1. ALWAYS call get_stylus_context or the matching ask_* tool BEFORE generating code on topics you're unsure about. Stylus SDK 0.10.0+ has subtle API changes that you must verify.
2. Prefer ask_* tools for conceptual questions, generate_* for code production, get_workflow for build/deploy steps.
3. Never invent network params, contract addresses, or SDK versions — retrieve them with a tool.
4. If a user request is outside Arbitrum/Stylus/Orbit, say so plainly. Do not attempt other domains.
5. You may call multiple tools in parallel when they're independent.
6. After tool results arrive, synthesize a single coherent answer for the user. Reference the tool outputs naturally; do not paste raw JSON.

Network endpoints (do not call a tool just to look these up):
- Arbitrum Sepolia: https://sepolia-rollup.arbitrum.io/rpc (chainId 421614)
- Arbitrum One: https://arb1.arbitrum.io/rpc (chainId 42161)
- Arbitrum Nova: https://nova.arbitrum.io/rpc (chainId 42170)
```

If the client passes their own `system` message, it is appended after this prompt.

## Database Changes

Migration `0004_chat_tool_calls.sql`:

```sql
ALTER TABLE usage_logs ADD COLUMN tool_calls TEXT;
```

`tool_calls` is a JSON array of tool names invoked during the chat turn (e.g. `["get_stylus_context", "generate_stylus_code"]`). NULL for non-chat tool invocations.

Usage row written per chat turn:

```ts
{
  id: <uuid>,
  api_key_id,
  tool: "chat",
  tokens_used: totalUsage.total_tokens,
  latency_ms: <wall clock>,
  success: 1 | 0,
  error_message: <if failed>,
  tool_calls: JSON.stringify(["get_stylus_context", ...]),
  created_at: <now>,
}
```

## Playground UI (`app/playground/chat/page.tsx`)

New page, separate from `/playground`. Shares the auth panel layout (session or API key, identical UX to existing playground page).

Layout:
- Top: header bar (matching existing playground), with link back to `/playground` ("Tools" view)
- Main: full-height conversation pane, message bubbles
- Tool-call cards rendered inline: `🔧 get_stylus_context({"query": "..."})` — collapsed by default, expandable
- `reasoning_content` rendered as a collapsed gray "Thinking…" panel above each assistant message, expandable
- Bottom: text area + send button + stop button

Streaming consumption: plain `fetch` POST + `ReadableStream` reader over the SSE body (browser EventSource cannot POST or set custom headers). Each SSE chunk parsed and merged into the active assistant message state.

State:
- `messages: ChatMessage[]` — in-memory React state
- `streaming: boolean` — disables input while streaming
- `abortController: AbortController` — for stop button (aborts fetch; server detects via `request.signal` and cancels upstream OpenRouter call)

No persistence in v1. "Clear" button resets state.

## Testing

Unit tests in `apps/web/src/lib/chat/__tests__/` using vitest:

1. **`agent.test.ts`** — mock `chatCompletionStream` and verify:
   - ReAct terminates on no-tool-call response
   - Parallel tool execution (single iteration with 2+ tool calls)
   - Continuation: model returns `finish_reason: "length"` twice, then `"stop"` — content is concatenated correctly
   - Iteration cap: model keeps calling tools, hits `MAX_ITER`, `forceFinalAnswer` runs
   - Tool argument truncation: tool args never close after 3 continuations → injected error message
   - Total turn budget exceeded → graceful cutoff with `finish_reason: "length"`

2. **`toolDefs.test.ts`** — every chat-tool name routes to the right `lib/tools/*` function with arg shape validated. Excluded tools (`generate_backend`, etc.) are not present in `ARBBUILDER_TOOL_DEFS`.

3. **`streaming.test.ts`** — SSE encode/decode round-trip; partial chunk reassembly across network boundary.

4. **Integration smoke** (`integration.test.ts`, gated on `OPENROUTER_API_KEY` env var) — hit `/api/v1/chat/completions` non-streaming with a single user message, assert response shape and that at least one tool was invoked.

Manual playground test plan (in spec, executed during implementation):
- "Explain Stylus mappings" → expect `ask_stylus` tool call, no code generation
- "Generate a simple ERC20 in Stylus" → expect `get_stylus_context` then `generate_stylus_code`
- "How do I bridge ETH from L1 to L2?" → expect `ask_bridging` or `generate_bridge_code`
- "Deploy an Orbit chain" → expect `ask_orbit` or `generate_orbit_deployment`
- "What's the weather?" → expect plain refusal, no tool call

## File Layout

```
apps/web/src/
├── app/
│   ├── api/v1/chat/completions/route.ts      # NEW — endpoint handler, auth, SSE assembly
│   └── playground/chat/page.tsx              # NEW — chat UI
├── lib/
│   ├── chat/                                 # NEW
│   │   ├── agent.ts                          # ReAct loop, callWithContinuation, forceFinalAnswer
│   │   ├── toolDefs.ts                       # 14 OpenAI-format tool defs + executeToolCall
│   │   ├── systemPrompt.ts                   # ARBuilder system prompt constant
│   │   ├── streaming.ts                      # SSE encode/decode helpers
│   │   ├── types.ts                          # OpenAI-shape TS types
│   │   └── __tests__/
│   │       ├── agent.test.ts
│   │       ├── toolDefs.test.ts
│   │       ├── streaming.test.ts
│   │       └── integration.test.ts
│   ├── tools/dispatch.ts                     # NEW — shared runTool() used by /mcp + chat
│   └── openrouter.ts                         # MODIFIED — add chatCompletionStream + MODEL_MAX_OUTPUT_TOKENS + reasoning passthrough
├── migrations/
│   └── 0004_chat_tool_calls.sql              # NEW — adds tool_calls column to usage_logs
```

Refactor: `app/mcp/route.ts` `handleToolCall` switch statement is replaced by a call to the new shared `runTool` dispatch.

## Open Questions

None. All design decisions are committed:

| Decision | Outcome |
|---|---|
| Routing approach | LLM tool calling with ReAct loop |
| Tool surface | 14 lightweight tools; 4 big scaffolders excluded |
| Streaming | Strict OpenAI standard, both `stream:true` and `stream:false` supported |
| Reasoning | `delta.reasoning_content` (DeepSeek/ecosystem convention) |
| Statefulness | Stateless — client sends full history |
| `max_tokens` | Per-call cap = upstream model max (32768 for gpt-oss-120b); auto-continuation on `length` |
| Auth | Existing `Bearer arb_...` API keys via `lib/apiKeys.ts` |
| UI placement | Separate route `/playground/chat` |
| Iteration cap | 6 ReAct iterations × 3 continuations × 200K total turn budget |
| Model name | `arbbuilder-chat` canonical; aliased silently |

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

- **Stylus contracts**: `get_stylus_context`, `generate_stylus_code`, `ask_stylus`, `generate_tests`, `get_workflow`
- **Arbitrum SDK bridging/messaging**: `generate_bridge_code`, `generate_messaging_code`, `ask_bridging`
- **Orbit chain deployment**: `generate_orbit_config`, `generate_orbit_deployment`, `generate_validator_setup`, `ask_orbit`
- **Indexers and oracles**: `generate_indexer`, `generate_oracle`

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
      "reasoning_content": "I should check the storage docs first..."
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

`reasoning_content` is the chain-of-thought emitted by the model across all ReAct iterations. Strict OpenAI clients ignore this field; ecosystem clients (DeepSeek SDK, OpenRouter SDK, our playground) render it.

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
| 429 | `rate_limit_exceeded` | Daily quota for the key's tier exhausted. Response carries `Retry-After` and `X-RateLimit-*` headers. |
| 500 | `internal_error` | Server misconfiguration (missing OpenRouter key) or pre-stream failure. |
| 502 | `upstream_error` | OpenRouter returned a non-retryable 4xx/5xx. |

Mid-stream errors are surfaced as a `data:` frame, not an HTTP status change.

## Rate limits

Two windows, both enforced per key per category (chat and tool counters are independent). The minute window catches abuse bursts; the day window caps total cost. Whichever window is exhausted first triggers a 429 — clients should respect `Retry-After`.

| Tier | Per-minute (each category) | Per-day (each category) |
|---|---|---|
| `free` (default) | 100 | 1000 |
| `pro` | 500 | 10 000 |
| `unlimited` | 10 000 | 1 000 000 |

Headers on every response:

- `X-RateLimit-Limit` / `-Remaining` / `-Reset` — bottleneck window (whichever has fewer calls left)
- `X-RateLimit-Limit-Minute` / `-Remaining-Minute` / `-Reset-Minute`
- `X-RateLimit-Limit-Day` / `-Remaining-Day` / `-Reset-Day`
- `X-RateLimit-Tier` — your tier (`free`, `pro`, `unlimited`)

A 429 additionally carries `Retry-After: <seconds>` for the window that denied the request.

To request a higher tier, ping the admin — tier is bumped per key from the admin dashboard. Session-auth requests (playground) always count under `free` per user.

### Checking usage without burning a slot

```
GET /api/v1/usage
Authorization: Bearer arb_xxxxx
```

Returns the current rate-limit state for the calling key. This endpoint does **not** increment counters, so polling it is free.

```json
{
  "tier": "free",
  "admin": false,
  "chat": {
    "minute": { "limit": 100, "remaining": 99, "used": 1, "resetSeconds": 12 },
    "day":    { "limit": 1000, "remaining": 999, "used": 1, "resetSeconds": 74012 }
  },
  "tool": {
    "minute": { "limit": 100, "remaining": 100, "used": 0, "resetSeconds": 12 },
    "day":    { "limit": 1000, "remaining": 1000, "used": 0, "resetSeconds": 74012 }
  },
  "recent": {
    "calls24h": 17,
    "lastCallAt": "2026-05-02T10:23:45.000Z",
    "successRate": 1.0
  }
}
```

`recent` is sourced from `usage_logs` over the last 24h and is only populated for API-key auth (session-auth requests don't have a `keyId` to filter on, so `recent` is `null`).

## Per-turn caps

| Cap | Value |
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

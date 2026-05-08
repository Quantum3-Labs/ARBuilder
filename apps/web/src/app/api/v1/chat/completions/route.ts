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
import { encodeSSEChunk, encodeSSEDone, encodeSSEError } from "@/lib/chat/streaming";
import { enforceRateLimit, rateLimitHeaders, subjectFor } from "@/lib/rateLimit";
import { evaluateCors, preflightResponse } from "@/lib/cors";
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
  extraHeaders?: Record<string, string>,
): NextResponse {
  const body: OpenAIErrorBody = { error: { message, type, code: code ?? null } };
  return NextResponse.json(body, { status, headers: extraHeaders });
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

  // Permissive CORS for pre-auth errors — we don't know the key yet, so we
  // reflect Origin to keep the browser happy while still returning the real
  // status code and body.
  const reqOrigin = request.headers.get("Origin");
  const preAuthCors: Record<string, string> = reqOrigin
    ? { "Access-Control-Allow-Origin": reqOrigin, "Access-Control-Allow-Credentials": "true", Vary: "Origin" }
    : { Vary: "Origin" };

  // Auth — same flow as /api/v1/tools/* and /mcp.
  const auth = await validateRequest(request, env.DB, env.AUTH_SECRET);
  if (!auth.success) {
    return errorResponse(
      "Authentication required. Pass a valid `Authorization: Bearer arb_...` header.",
      "invalid_api_key",
      401,
      undefined,
      preAuthCors,
    );
  }

  // CORS allowlist enforcement (browser-only).
  const cors = evaluateCors(request, auth.allowedOrigins);
  if (!cors.ok) return cors.response;

  // Rate limit — per-key for arb_ keys, per-user for session auth, bypass for admin.
  const subj = subjectFor(auth);
  let rlHeaders: Record<string, string> = {};
  if (subj) {
    const decision = await enforceRateLimit(env.KV, subj.subject, "chat", subj.tier);
    rlHeaders = rateLimitHeaders(decision);
    if (!decision.allowed) {
      const denyWindow = decision.exceededWindow === "minute" ? decision.minute : decision.day;
      const label = decision.exceededWindow === "minute" ? "per-minute" : "per-day";
      return errorResponse(
        `Chat rate limit exceeded (${label}: ${denyWindow.limit} on tier '${decision.tier}'). Try again in ${denyWindow.resetSeconds}s.`,
        "rate_limit_exceeded",
        429,
        undefined,
        { ...rlHeaders, ...cors.headers },
      );
    }
  }
  // Merge CORS headers into the rate-limit header bag for the success path.
  rlHeaders = { ...rlHeaders, ...cors.headers };

  // Parse body.
  let body: ChatCompletionRequest;
  try {
    body = (await request.json()) as ChatCompletionRequest;
  } catch {
    return errorResponse("Invalid JSON body.", "invalid_request_error", 400, undefined, rlHeaders);
  }
  if (!Array.isArray(body.messages) || body.messages.length === 0) {
    return errorResponse(
      "Missing required field 'messages' (must be a non-empty array).",
      "invalid_request_error",
      400,
      undefined,
      rlHeaders,
    );
  }
  if (!env.OPENROUTER_API_KEY) {
    return errorResponse("OpenRouter not configured on this server.", "internal_error", 500, undefined, rlHeaders);
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
  const apiKeyId = auth.keyId;

  // Streaming path.
  if (body.stream === true) {
    const stream = new ReadableStream<Uint8Array>({
      async start(controller) {
        const encoder = new TextEncoder();
        let finalToolCalls: string[] = [];
        let finalUsage = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };
        try {
          const gen = runAgentStreaming(body.messages, toolEnv, opts, streamId, createdAt);
          let next = await gen.next();
          while (!next.done) {
            controller.enqueue(encoder.encode(encodeSSEChunk(next.value)));
            next = await gen.next();
          }
          if (next.value) {
            finalToolCalls = next.value.toolCallNames;
            finalUsage = next.value.usage;
          }
          controller.enqueue(encoder.encode(encodeSSEDone()));
          if (apiKeyId) {
            await logChatUsage(
              env.DB,
              apiKeyId,
              finalToolCalls,
              finalUsage.total_tokens,
              Date.now() - start,
              true,
            );
          }
          controller.close();
        } catch (e) {
          const msg = (e as Error).message || String(e);
          controller.enqueue(encoder.encode(encodeSSEError(msg, "internal_error")));
          controller.enqueue(encoder.encode(encodeSSEDone()));
          if (apiKeyId) {
            await logChatUsage(env.DB, apiKeyId, [], 0, Date.now() - start, false, msg);
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
        ...rlHeaders,
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
    if (apiKeyId) {
      await logChatUsage(
        env.DB, apiKeyId, result.toolCallNames, result.usage.total_tokens, Date.now() - start, true,
      );
    }
    return NextResponse.json(response, { headers: rlHeaders });
  } catch (e) {
    const msg = (e as Error).message || String(e);
    if (apiKeyId) {
      await logChatUsage(env.DB, apiKeyId, [], 0, Date.now() - start, false, msg);
    }
    return errorResponse(msg, "internal_error", 500, undefined, rlHeaders);
  }
}

export async function OPTIONS(request: NextRequest) {
  return preflightResponse(request, "POST, OPTIONS");
}

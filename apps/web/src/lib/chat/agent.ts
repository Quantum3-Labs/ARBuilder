import { streamChatCompletion, getMaxTokens } from "@/lib/openrouter";
import { ARBBUILDER_TOOL_DEFS, executeToolCall } from "./toolDefs";
import { ARBBUILDER_SYSTEM_PROMPT } from "./systemPrompt";
import {
  accumulateChunk,
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
const OUTPUT_MODEL_NAME = "arbbuilder-chat";
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
 * into the canonical ToolCall[] form (id: string required).
 */
function finalizeToolCalls(acc: ToolCallAccumulator[]): ToolCall[] {
  return acc.map((tc, i) => ({
    id: tc.id ?? `call_${Date.now()}_${i}`,
    type: "function" as const,
    function: { name: tc.function.name ?? "", arguments: tc.function.arguments },
  }));
}

/**
 * Translate an upstream OpenRouter chunk into our outbound stream shape.
 * Strips internal fields, normalizes reasoning field name (`reasoning` → `reasoning_content`),
 * preserves choices.
 */
function rewriteChunkForOutput(
  raw: Record<string, unknown>,
  streamId: string,
  createdAt: number,
): ChatCompletionChunk | null {
  const choices = raw.choices as Array<{
    index?: number;
    delta?: {
      content?: string;
      reasoning?: string;
      reasoning_content?: string;
      role?: string;
      tool_calls?: unknown;
    };
    finish_reason?: null | string;
  }> | undefined;

  // Suppress per-call usage chunks from upstream — the agent emits a single
  // consolidated usage chunk at the very end. Forwarding upstream usage would
  // make clients see partial usage values mid-stream.
  if (!choices || choices.length === 0) return null;

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
    model: OUTPUT_MODEL_NAME,
    choices: [{
      index: c.index ?? 0,
      delta: outDelta,
      finish_reason: (c.finish_reason ?? null) as ChatCompletionChunk["choices"][0]["finish_reason"],
    }],
  };
}

interface IterationOptions extends AgentOptions {
  /** Set true on the wrap-up call so the model can't request more tools. */
  excludeTools?: boolean;
}

/**
 * Run a single ReAct iteration with auto-continuation across `finish_reason: "length"`.
 *
 * Async generator: yields each rewritten outbound `ChatCompletionChunk` as the
 * upstream stream produces it, then returns the fully-accumulated iteration
 * result. The caller drives the generator and gets real-time chunks.
 */
async function* iterateOnce(
  apiKey: string,
  messages: ChatMessage[],
  opts: IterationOptions,
  streamId: string,
  createdAt: number,
): AsyncGenerator<ChatCompletionChunk, IterationAccumulator, void> {
  const acc = newIterationAccumulator();
  let working = messages;

  for (let cont = 0; cont < MAX_LENGTH_CONTINUATIONS; cont++) {
    const stream = streamChatCompletion({
      apiKey,
      model: UPSTREAM_MODEL,
      messages: working.map((m) => ({
        role: m.role,
        content: m.content,
        name: m.name,
        tool_call_id: m.tool_call_id,
        tool_calls: m.tool_calls,
      })),
      tools: opts.excludeTools ? undefined : ARBBUILDER_TOOL_DEFS,
      temperature: opts.temperature,
      max_tokens: opts.max_tokens,
      stop: opts.stop,
      signal: opts.signal,
    });

    for await (const rawChunk of stream) {
      const rewritten = rewriteChunkForOutput(rawChunk, streamId, createdAt);
      if (rewritten) yield rewritten;
      accumulateChunk(acc, rawChunk as Parameters<typeof accumulateChunk>[1]);
    }

    if (acc.finish_reason !== "length") return acc;

    // Continuation: append partial assistant turn so model resumes from there.
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

  // Three continuations exhausted — return what we have.
  if (!acc.finish_reason) acc.finish_reason = "length";
  return acc;
}

/**
 * Run the full ReAct agent loop and stream outbound chunks as they arrive.
 *
 * Returns (via generator return value) the aggregated tool-call names and
 * total usage, which the route handler logs to D1.
 */
export async function* runAgentStreaming(
  initialMessages: ChatMessage[],
  env: ToolEnv,
  opts: AgentOptions,
  streamId: string,
  createdAt: number,
): AsyncGenerator<ChatCompletionChunk, { toolCallNames: string[]; usage: ChatUsage }, void> {
  if (!env.OPENROUTER_API_KEY) {
    throw new Error("OpenRouter API key not configured");
  }

  let messages = withSystemPrompt(initialMessages);
  let totalUsage: ChatUsage = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };
  const toolCallNames: string[] = [];
  const cappedMax = getMaxTokens(UPSTREAM_MODEL, opts.max_tokens);

  for (let iter = 0; iter < MAX_REACT_ITERATIONS; iter++) {
    if (totalUsage.total_tokens > TOTAL_TURN_BUDGET_TOKENS) {
      const cutoff: ChatCompletionChunk = {
        id: streamId,
        object: "chat.completion.chunk",
        created: createdAt,
        model: OUTPUT_MODEL_NAME,
        choices: [{
          index: 0,
          delta: { content: "\n\n[Response truncated: turn token budget exceeded.]" },
          finish_reason: "length",
        }],
      };
      yield cutoff;
      break;
    }

    // Drive iterateOnce, yielding each chunk as it arrives.
    const subGen = iterateOnce(
      env.OPENROUTER_API_KEY,
      messages,
      { ...opts, max_tokens: cappedMax },
      streamId,
      createdAt,
    );
    let next = await subGen.next();
    while (!next.done) {
      yield next.value;
      next = await subGen.next();
    }
    const acc = next.value;
    totalUsage = sumUsage(totalUsage, acc.usage);

    if (acc.tool_calls.length === 0) {
      // Final answer reached.
      break;
    }

    // Execute tool calls in parallel; append assistant + tool messages.
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
      // Hit cap — final wrap-up call without tools.
      const wrapGen = iterateOnce(
        env.OPENROUTER_API_KEY,
        [
          ...messages,
          {
            role: "user",
            content:
              "Wrap up your reasoning into a final answer for the user. Do not call any more tools.",
          },
        ],
        { ...opts, max_tokens: cappedMax, excludeTools: true },
        streamId,
        createdAt,
      );
      let nx = await wrapGen.next();
      while (!nx.done) {
        yield nx.value;
        nx = await wrapGen.next();
      }
      totalUsage = sumUsage(totalUsage, nx.value.usage);
    }
  }

  // Final consolidated usage chunk before [DONE].
  // OpenAI-canonical pattern: empty choices array + usage. The actual
  // finish_reason was already announced inside the iteration's last chunk
  // (or the budget-cutoff chunk above) — emitting it again here would
  // duplicate the terminal signal.
  const usageChunk: ChatCompletionChunk = {
    id: streamId,
    object: "chat.completion.chunk",
    created: createdAt,
    model: OUTPUT_MODEL_NAME,
    choices: [],
    usage: totalUsage,
  };
  yield usageChunk;

  return { toolCallNames, usage: totalUsage };
}

/**
 * Run the full ReAct agent loop and return a single accumulated response.
 *
 * Implementation note: drives `runAgentStreaming` internally and accumulates
 * content / reasoning / finish_reason from the yielded chunks. Tool execution
 * happens inside `runAgentStreaming` and shows up here only via the aggregated
 * tool-call names returned by the generator.
 */
export async function runAgentNonStreaming(
  initialMessages: ChatMessage[],
  env: ToolEnv,
  opts: AgentOptions,
): Promise<AgentNonStreamResult> {
  const streamId = `chatcmpl-${crypto.randomUUID()}`;
  const createdAt = Math.floor(Date.now() / 1000);

  const gen = runAgentStreaming(initialMessages, env, opts, streamId, createdAt);

  let content = "";
  let reasoningContent = "";
  let lastFinishReason: AgentNonStreamResult["finish_reason"] = "stop";
  // Capture intermediate tool-call announcements only for logging — final
  // synthesized answer text comes from delta.content of the final iteration.
  // We track all content deltas, but tool_call deltas are not part of the
  // final assistant text. The streaming generator yields tool-call deltas
  // during intermediate iterations; we ignore them here.
  let next = await gen.next();
  while (!next.done) {
    const chunk = next.value;
    const choice = chunk.choices?.[0];
    if (choice?.delta?.content) content += choice.delta.content;
    if (choice?.delta?.reasoning_content) reasoningContent += choice.delta.reasoning_content;
    if (choice?.finish_reason) {
      lastFinishReason = choice.finish_reason as AgentNonStreamResult["finish_reason"];
    }
    next = await gen.next();
  }

  return {
    content,
    reasoning_content: reasoningContent,
    finish_reason: lastFinishReason,
    usage: next.value.usage,
    toolCallNames: next.value.toolCallNames,
  };
}

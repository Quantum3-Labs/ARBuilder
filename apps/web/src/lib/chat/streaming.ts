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
    choices?: Array<{
      delta?: {
        content?: string;
        reasoning_content?: string;
        reasoning?: string;
        tool_calls?: Array<{
          index: number;
          id?: string;
          type?: "function";
          function?: { name?: string; arguments?: string };
        }>;
      };
      finish_reason?: null | string;
    }>;
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

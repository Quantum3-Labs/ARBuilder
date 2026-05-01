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

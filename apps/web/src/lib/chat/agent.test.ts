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
        { choices: [{ index: 0, delta: { content: "hello" }, finish_reason: null }] },
        {
          choices: [{ index: 0, delta: { content: " world" }, finish_reason: "stop" }],
          usage: { prompt_tokens: 5, completion_tokens: 2, total_tokens: 7 },
        },
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
          index: 0,
          delta: {
            tool_calls: [{
              index: 0, id: "call_1", type: "function",
              function: { name: "ask_stylus", arguments: '{"question":"q"}' },
            }],
          },
          finish_reason: "tool_calls",
        }],
        usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
      },
    ]);
    const callB = makeStream([
      {
        choices: [{ index: 0, delta: { content: "answer" }, finish_reason: "stop" }],
        usage: { prompt_tokens: 20, completion_tokens: 3, total_tokens: 23 },
      },
    ]);
    const mock = streamChatCompletion as unknown as ReturnType<typeof vi.fn>;
    mock.mockImplementationOnce(callA).mockImplementationOnce(callB);

    const messages: ChatMessage[] = [{ role: "user", content: "explain mappings" }];
    const out = await runAgentNonStreaming(messages, fakeEnv, { temperature: 0.3, max_tokens: 100 });
    expect(out.content).toBe("answer");
    expect(out.toolCallNames).toEqual(["ask_stylus"]);
    expect(out.usage.total_tokens).toBe(15 + 23);
  });

  it("preserves finish_reason='length' when continuation cap is hit", async () => {
    // 3 length-only continuations + a final one still length → finish_reason = length
    const lengthChunk = makeStream([
      {
        choices: [{ index: 0, delta: { content: "x" }, finish_reason: "length" }],
        usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 },
      },
    ]);
    const mock = streamChatCompletion as unknown as ReturnType<typeof vi.fn>;
    // 3 attempts, all hit length, then iterateOnce returns acc with finish_reason="length",
    // tool_calls is empty so loop exits.
    mock.mockImplementation(() => lengthChunk());

    const out = await runAgentNonStreaming(
      [{ role: "user", content: "go" }],
      fakeEnv,
      { temperature: 0.3, max_tokens: 100 },
    );
    expect(out.finish_reason).toBe("length");
    expect(out.content).toBe("xxx"); // 3 continuations of "x"
  });

  it("continues across finish_reason='length'", async () => {
    const part1 = makeStream([
      {
        choices: [{ index: 0, delta: { content: "first " }, finish_reason: "length" }],
        usage: { prompt_tokens: 5, completion_tokens: 2, total_tokens: 7 },
      },
    ]);
    const part2 = makeStream([
      {
        choices: [{ index: 0, delta: { content: "second" }, finish_reason: "stop" }],
        usage: { prompt_tokens: 5, completion_tokens: 2, total_tokens: 7 },
      },
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

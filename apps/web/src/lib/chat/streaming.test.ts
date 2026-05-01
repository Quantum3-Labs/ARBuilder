import { describe, it, expect } from "vitest";
import {
  encodeSSEChunk,
  mergeToolCallDeltas,
  accumulateChunk,
  newIterationAccumulator,
} from "./streaming";
import type { ChatCompletionChunk } from "./types";

describe("encodeSSEChunk", () => {
  it("encodes an OpenAI chunk as a data: line", () => {
    const chunk: ChatCompletionChunk = {
      id: "x",
      object: "chat.completion.chunk",
      created: 0,
      model: "m",
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
    const acc = newIterationAccumulator();
    accumulateChunk(acc, { choices: [{ index: 0, delta: { content: "ab" }, finish_reason: null }] });
    accumulateChunk(acc, { choices: [{ index: 0, delta: { reasoning_content: "thinking..." }, finish_reason: null }] });
    accumulateChunk(acc, { choices: [{ index: 0, delta: { content: "cd" }, finish_reason: "stop" }] });
    expect(acc.content).toBe("abcd");
    expect(acc.reasoning_content).toBe("thinking...");
    expect(acc.finish_reason).toBe("stop");
  });

  it("treats `reasoning` field name (OpenRouter native) as reasoning_content", () => {
    const acc = newIterationAccumulator();
    accumulateChunk(acc, { choices: [{ index: 0, delta: { reasoning: "thought" }, finish_reason: null }] });
    expect(acc.reasoning_content).toBe("thought");
  });
});

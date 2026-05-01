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

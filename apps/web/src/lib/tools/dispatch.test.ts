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

import { describe, it, expect } from "vitest";
import { ARBBUILDER_TOOL_DEFS } from "./toolDefs";
import { CHAT_TOOL_NAMES } from "@/lib/tools/dispatch";

describe("ARBBUILDER_TOOL_DEFS", () => {
  it("contains exactly the 14 chat-friendly tools", () => {
    expect(ARBBUILDER_TOOL_DEFS).toHaveLength(14);
    const names = ARBBUILDER_TOOL_DEFS.map((t) => t.function.name);
    expect(new Set(names)).toEqual(new Set(CHAT_TOOL_NAMES));
  });

  it("every def has type=function and a non-empty description", () => {
    for (const t of ARBBUILDER_TOOL_DEFS) {
      expect(t.type).toBe("function");
      expect(t.function.description.length).toBeGreaterThan(0);
      expect(t.function.parameters.type).toBe("object");
    }
  });

  it("every def with required params lists them", () => {
    const expectsRequired = [
      "get_stylus_context", "generate_stylus_code", "ask_stylus", "generate_tests",
      "get_workflow", "generate_bridge_code", "generate_messaging_code", "ask_bridging",
      "generate_indexer", "generate_oracle", "generate_orbit_config",
      "generate_orbit_deployment", "generate_validator_setup", "ask_orbit",
    ];
    for (const name of expectsRequired) {
      const def = ARBBUILDER_TOOL_DEFS.find((t) => t.function.name === name)!;
      expect(def.function.parameters.required, `${name}.required`).toBeDefined();
      expect(def.function.parameters.required!.length).toBeGreaterThan(0);
    }
  });
});

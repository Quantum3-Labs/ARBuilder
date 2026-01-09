/**
 * Generate Stylus Code Tool
 *
 * Generates Stylus smart contract code based on natural language
 * descriptions, using RAG context for accurate patterns.
 *
 * Supports version-aware code generation for different stylus-sdk versions.
 */

import { generateCode } from "../openrouter";
import { getStylusContext } from "./getStylusContext";
import {
  getMainVersion,
  getAlloyPrimitivesVersion,
  getAlloySolTypesVersion,
  detectVersionFromCargoToml,
  isVersionDeprecated,
  getDeprecationWarning,
} from "../stylusVersions";

export interface GenerateStylusCodeInput {
  prompt: string;
  contextQuery?: string;
  contractType?: "token" | "nft" | "defi" | "utility" | "custom";
  includeTests?: boolean;
  temperature?: number;
  /** Target stylus-sdk version. If not provided, defaults to main version. */
  targetVersion?: string;
  /** Cargo.toml content for automatic version detection. */
  cargoToml?: string;
}

export interface GenerateStylusCodeOutput {
  code: string;
  explanation: string;
  dependencies: string[];
  warnings: string[];
  contextUsed: string[];
  tokensUsed: number;
  /** The stylus-sdk version used for code generation. */
  targetVersion: string;
}

export async function generateStylusCode(
  vectorize: VectorizeIndex,
  ai: Ai,
  openrouterApiKey: string,
  input: GenerateStylusCodeInput
): Promise<GenerateStylusCodeOutput> {
  const {
    prompt,
    contextQuery,
    contractType = "utility",
    includeTests = false,
    cargoToml,
    // temperature reserved for future use with configurable LLM settings
  } = input;

  // Version detection logic
  let targetVersion = input.targetVersion;
  const warnings: string[] = [];

  // Auto-detect version from Cargo.toml if provided
  if (cargoToml && !targetVersion) {
    const detected = detectVersionFromCargoToml(cargoToml);
    if (detected) {
      targetVersion = detected;
    }
  }

  // Default to main version if not specified
  if (!targetVersion) {
    targetVersion = getMainVersion();
  }

  // Check for deprecation warnings
  if (isVersionDeprecated(targetVersion)) {
    const warning = getDeprecationWarning(targetVersion);
    if (warning) {
      warnings.push(warning);
    }
  }

  // Get relevant context from knowledge base with version awareness
  const searchQuery = contextQuery || `${contractType} contract ${prompt}`;
  const contextResult = await getStylusContext(vectorize, ai, {
    query: searchQuery,
    nResults: 5,
    rerank: true,
    targetVersion, // Pass version for boosted search
  });

  // Build context string
  const contextStr = contextResult.contexts
    .map((c, i) => `[${i + 1}] (${c.source})\n${c.content}`)
    .join("\n\n---\n\n");

  // Enhance prompt with test request if needed
  let enhancedPrompt = prompt;
  if (includeTests) {
    enhancedPrompt += "\n\nAlso include a #[cfg(test)] module with comprehensive unit tests.";
  }

  // Generate code using LLM with version-aware prompts
  const response = await generateCode(openrouterApiKey, enhancedPrompt, contextStr, targetVersion);

  // Parse response - extract code blocks and explanation
  const codeMatch = response.content.match(/```rust\n([\s\S]*?)```/);
  const code = codeMatch ? codeMatch[1].trim() : response.content;

  // Extract explanation (text before or after code block)
  const explanation = response.content
    .replace(/```rust\n[\s\S]*?```/g, "")
    .trim()
    .split("\n")
    .filter((line) => line.trim())
    .join("\n");

  // Detect dependencies from code with correct versions for target SDK
  const alloyPrimitivesVer = getAlloyPrimitivesVersion(targetVersion);
  const alloySolTypesVer = getAlloySolTypesVersion(targetVersion);

  const dependencies: string[] = [];
  if (code.includes("stylus_sdk") || code.includes("stylus-sdk"))
    dependencies.push(`stylus-sdk = "${targetVersion}"`);
  if (code.includes("alloy_primitives") || code.includes("U256"))
    dependencies.push(`alloy-primitives = "${alloyPrimitivesVer}"`);
  if (code.includes("alloy_sol_types") || code.includes("sol!"))
    dependencies.push(`alloy-sol-types = "${alloySolTypesVer}"`);

  // Check for potential issues
  if (code.includes("unwrap()"))
    warnings.push("Code contains unwrap() - consider proper error handling");
  if (!code.includes("#![cfg_attr"))
    warnings.push("Missing #![cfg_attr(not(feature = \"export-abi\"), no_main)]");

  return {
    code,
    explanation: explanation || "Contract generated based on your requirements.",
    dependencies,
    warnings,
    contextUsed: contextResult.contexts.map((c) => c.source),
    tokensUsed: response.usage.totalTokens,
    targetVersion,
  };
}

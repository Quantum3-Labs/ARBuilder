/**
 * Generate Stylus Code Tool
 *
 * Generates Stylus smart contract code based on natural language
 * descriptions, using RAG context for accurate patterns.
 */

import { generateCode } from "../openrouter";
import { getStylusContext } from "./getStylusContext";

export interface GenerateStylusCodeInput {
  prompt: string;
  contextQuery?: string;
  contractType?: "token" | "nft" | "defi" | "utility" | "custom";
  includeTests?: boolean;
  temperature?: number;
}

export interface GenerateStylusCodeOutput {
  code: string;
  explanation: string;
  dependencies: string[];
  warnings: string[];
  contextUsed: string[];
  tokensUsed: number;
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
    // temperature reserved for future use with configurable LLM settings
  } = input;

  // Get relevant context from knowledge base
  const searchQuery = contextQuery || `${contractType} contract ${prompt}`;
  const contextResult = await getStylusContext(vectorize, ai, {
    query: searchQuery,
    nResults: 5,
    rerank: true,
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

  // Generate code using LLM
  const response = await generateCode(openrouterApiKey, enhancedPrompt, contextStr);

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

  // Detect dependencies from code
  const dependencies: string[] = [];
  if (code.includes("stylus-sdk")) dependencies.push('stylus-sdk = "0.8.4"');
  if (code.includes("alloy_primitives") || code.includes("U256"))
    dependencies.push('alloy-primitives = "0.8.14"');
  if (code.includes("alloy_sol_types") || code.includes("sol!"))
    dependencies.push('alloy-sol-types = "0.8.14"');

  // Check for potential issues
  const warnings: string[] = [];
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
  };
}

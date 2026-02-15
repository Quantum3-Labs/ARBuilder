/**
 * Ask Stylus Tool
 *
 * Answers questions about Stylus development, debugging,
 * and best practices with context-aware responses.
 */

import { answerQuestion } from "../openrouter";
import { getStylusContext } from "./getStylusContext";

export interface AskStylusInput {
  question: string;
  codeContext?: string;
  questionType?: "general" | "debugging" | "optimization" | "security";
}

export interface AskStylusOutput {
  answer: string;
  codeExamples: Array<{
    title: string;
    code: string;
  }>;
  references: string[];
  followUpQuestions: string[];
  tokensUsed: number;
}

export async function askStylus(
  vectorize: VectorizeIndex,
  ai: Ai,
  openrouterApiKey: string,
  input: AskStylusInput
): Promise<AskStylusOutput> {
  const { question, codeContext, questionType = "general" } = input;

  // Build search query
  let searchQuery = question;
  if (questionType === "debugging") {
    searchQuery = `debugging troubleshooting ${question}`;
  } else if (questionType === "optimization") {
    searchQuery = `optimization performance gas ${question}`;
  } else if (questionType === "security") {
    searchQuery = `security vulnerability audit ${question}`;
  }

  // Get relevant context
  const contextResult = await getStylusContext(vectorize, ai, {
    query: searchQuery,
    nResults: 5,
    rerank: true,
  });

  // Build context string with optional code context
  let contextStr = contextResult.contexts
    .map((c, i) => `[${i + 1}] (${c.source})\n${c.content}`)
    .join("\n\n---\n\n");

  if (codeContext) {
    contextStr = `User's Code:\n\`\`\`rust\n${codeContext}\n\`\`\`\n\n---\n\n${contextStr}`;
  }

  // Get answer from LLM
  const response = await answerQuestion(openrouterApiKey, question, contextStr);

  // Fix wrong patterns in code blocks (RAG context often overrides system prompt)
  const fixedContent = fixCodeInResponse(response.content);

  // Extract code examples from response
  const codeExamples: Array<{ title: string; code: string }> = [];
  const codeBlockRegex = /```rust\n([\s\S]*?)```/g;
  let match;
  let exampleIndex = 1;
  while ((match = codeBlockRegex.exec(fixedContent)) !== null) {
    codeExamples.push({
      title: `Example ${exampleIndex++}`,
      code: match[1].trim(),
    });
  }

  // Generate follow-up questions based on the topic
  const followUpQuestions = generateFollowUpQuestions(question, questionType);

  return {
    answer: fixedContent
      .replace(/```rust\n[\s\S]*?```/g, "[Code example above]")
      .trim(),
    codeExamples,
    references: contextResult.contexts.map((c) => c.source),
    followUpQuestions,
    tokensUsed: response.usage.totalTokens,
  };
}

/**
 * Fix common wrong patterns in code blocks within LLM responses.
 * RAG context often contains outdated SDK 0.9.x patterns that override
 * the system prompt's correct 0.10.0 instructions.
 */
function fixCodeInResponse(content: string): string {
  return content.replace(/```(\w*)\n([\s\S]*?)```/g, (_match, lang: string, code: string) => {
    // Only fix rust/toml code blocks (or unspecified)
    if (lang && lang !== "rust" && lang !== "toml") {
      return _match;
    }

    let fixed = code;

    // Fix sol! { interface → sol_interface! { interface
    fixed = fixed.replace(/sol!\s*\{\s*(interface\b)/g, "sol_interface! { $1");

    // Fix wrong transfer_eth import paths
    fixed = fixed.replace(
      /use stylus_sdk::call::transfer_eth;/g,
      "use stylus_sdk::call::transfer::transfer_eth;"
    );
    fixed = fixed.replace(
      /use stylus_sdk::call::\{([^}]*)\btransfer_eth\b([^}]*)\};/g,
      (_m, before: string, after: string) => {
        const others = (before.replace("transfer_eth", "").trim().replace(/^,|,$/g, "").trim()
          + ", " + after.trim().replace(/^,|,$/g, "").trim()).replace(/^,\s*|,\s*$/g, "").trim();
        const transferLine = "use stylus_sdk::call::transfer::transfer_eth;";
        if (others) {
          return `${transferLine}\nuse stylus_sdk::call::{${others}};`;
        }
        return transferLine;
      }
    );

    // Fix self.transfer_eth(args) → transfer_eth(self.vm(), args)
    fixed = fixed.replace(
      /self\.transfer_eth\(([^)]+)\)/g,
      "transfer_eth(self.vm(), $1)"
    );

    // Fix transfer_eth(self, ...) → transfer_eth(self.vm(), ...)
    fixed = fixed.replace(/transfer_eth\(self,\s*/g, "transfer_eth(self.vm(), ");

    // Fix deprecated msg::sender() → self.vm().msg_sender()
    fixed = fixed.replace(/msg::sender\(\)/g, "self.vm().msg_sender()");
    fixed = fixed.replace(/msg::value\(\)/g, "self.vm().msg_value()");

    // Fix deprecated evm::log( → self.vm().log(
    fixed = fixed.replace(/evm::log\(/g, "self.vm().log(");

    // Remove deprecated imports
    fixed = fixed.replace(/^use stylus_sdk::evm.*;\s*$/gm, "");
    fixed = fixed.replace(/^use stylus_sdk::msg.*;\s*$/gm, "");

    return `\`\`\`${lang}\n${fixed}\`\`\``;
  });
}

function generateFollowUpQuestions(
  question: string,
  questionType: string
): string[] {
  const commonFollowUps: Record<string, string[]> = {
    general: [
      "How can I test this implementation?",
      "What are the gas implications?",
      "How does this compare to Solidity?",
    ],
    debugging: [
      "How can I add logging for debugging?",
      "What tools can I use to trace transactions?",
      "How do I decode error messages?",
    ],
    optimization: [
      "What are the storage costs?",
      "How can I reduce contract size?",
      "What's the most gas-efficient approach?",
    ],
    security: [
      "What are common vulnerabilities to avoid?",
      "How do I handle reentrancy?",
      "Should I add access controls?",
    ],
  };

  return commonFollowUps[questionType] || commonFollowUps.general;
}

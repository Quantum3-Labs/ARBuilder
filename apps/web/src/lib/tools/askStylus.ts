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

    // Fix .getter(key) → .get(key) — .getter() does not exist in SDK 0.10.0
    fixed = fixed.replace(/\.getter\(/g, ".get(");

    // Fix Rust types inside sol_storage! — must use Solidity syntax
    // StorageMap<StorageX, StorageY> → mapping(x => y)
    fixed = fixed.replace(
      /StorageMap<Storage(\w+),\s*Storage(\w+)>/g,
      (_m, k: string, v: string) => `mapping(${k.toLowerCase()} => ${v.toLowerCase()})`
    );
    // StorageVec<StorageX> → x[]
    fixed = fixed.replace(
      /StorageVec<Storage(\w+)>/g,
      (_m, t: string) => `${t.toLowerCase()}[]`
    );
    // StorageString → string, StorageAddress → address, StorageU256 → uint256, etc.
    fixed = fixed.replace(/StorageString/g, "string");
    fixed = fixed.replace(/StorageAddress/g, "address");
    fixed = fixed.replace(/StorageU256/g, "uint256");
    fixed = fixed.replace(/StorageBool/g, "bool");
    fixed = fixed.replace(/StorageU8/g, "uint8");
    fixed = fixed.replace(/StorageU64/g, "uint64");
    fixed = fixed.replace(/StorageU128/g, "uint128");

    // Fix self.vm().address() → self.vm().contract_address()
    fixed = fixed.replace(/self\.vm\(\)\.address\(\)/g, "self.vm().contract_address()");

    // Fix U256::zero() → U256::ZERO
    fixed = fixed.replace(/U256::zero\(\)/g, "U256::ZERO");
    fixed = fixed.replace(/U128::zero\(\)/g, "U128::ZERO");

    // Fix std::time in no_std
    fixed = fixed.replace(/^use std::time.*;\s*$/gm, "");

    // Remove incorrect Call import
    fixed = fixed.replace(/^use stylus_sdk::call::Call;\s*$/gm, "");

    // Fix StorageVec .setter(i).set() missing unwrap
    // Only on dynamic array fields (type[]), not mapping .setter()
    const askArrayFields = new Set<string>();
    const askArrayPattern = /\b\w+\[\]\s+(\w+)\s*;/g;
    let askArrayMatch;
    while ((askArrayMatch = askArrayPattern.exec(fixed)) !== null) {
      askArrayFields.add(askArrayMatch[1]);
    }
    for (const af of askArrayFields) {
      fixed = fixed.replace(
        new RegExp(`\\.${af}\\.setter\\(((?:[^()]*|\\([^()]*\\))*)\\)\\.set\\(`, "g"),
        `.${af}.setter($1).unwrap().set(`
      );
    }

    // Fix 27: .get(k1).setter(k2) → .setter(k1).setter(k2)
    // Nested mapping writes: .get() returns immutable ref, can't
    // call .setter() on it. Must chain .setter() for writes.
    fixed = fixed.replace(
      /\.get\(((?:[^()]*|\([^()]*\))*)\)\.setter\(/g,
      ".setter($1).setter("
    );

    // Fix 23: REMOVED — corrupts sol! event/error declarations.

    // Fix 28: Remove spurious .unwrap_or_default() on mapping reads
    // Balanced parens for nested mapping declarations
    const mappingFlds = new Set<string>();
    const mappingFldPattern = /mapping\(((?:[^()]*|\([^()]*\))*)\)\s+(\w+)\s*;/g;
    let mappingFldMatch;
    while ((mappingFldMatch = mappingFldPattern.exec(fixed)) !== null) {
      mappingFlds.add(mappingFldMatch[2]);
    }
    for (const mf of mappingFlds) {
      fixed = fixed.replace(
        new RegExp(`\\.${mf}\\.get\\(([^)]*)\\)\\.unwrap_or_default\\(\\)`, "g"),
        `.${mf}.get($1)`
      );
      fixed = fixed.replace(
        new RegExp(`\\.${mf}\\.getter\\(([^)]*)\\)\\.get\\(([^)]*)\\)\\.unwrap_or_default\\(\\)`, "g"),
        `.${mf}.getter($1).get($2)`
      );
    }

    // Fix 29: sol_interface! camelCase → snake_case
    const solIfaceRenames: Record<string, string> = {
      transferFrom: "transfer_from",
      balanceOf: "balance_of",
      ownerOf: "owner_of",
      getApproved: "get_approved",
      isApprovedForAll: "is_approved_for_all",
      safeTransferFrom: "safe_transfer_from",
      setApprovalForAll: "set_approval_for_all",
      totalSupply: "total_supply",
      latestAnswer: "latest_answer",
      latestRoundData: "latest_round_data",
      getRoundData: "get_round_data",
    };
    for (const [camel, snake] of Object.entries(solIfaceRenames)) {
      fixed = fixed.replace(
        new RegExp(`\\.${camel}\\(self\\.vm\\(\\)`, "g"),
        `.${snake}(self.vm()`
      );
    }

    // Fix 30: B256::from_uint(&expr) → B256::from(expr.to_be_bytes::<32>())
    fixed = fixed.replace(
      /B256::from_uint\(&(\w+)\)/g,
      "B256::from($1.to_be_bytes::<32>())"
    );

    // Fix 31: U256::from(N) in const context → U256::from_limbs([N, 0, 0, 0])
    fixed = fixed.replace(
      /(const\s+\w+\s*:\s*U256\s*=\s*)U256::from\((\d+)\)/g,
      "$1U256::from_limbs([$2, 0, 0, 0])"
    );

    // Fix 24: .unwrap_or_else(VALUE) → .unwrap_or(VALUE)
    fixed = fixed.replace(
      /\.unwrap_or_else\((\w+::(?:ZERO|MAX|MIN|ONE))\)/g,
      ".unwrap_or($1)"
    );

    // Fix 25: self.vm().log(...)? → self.vm().log(...)
    fixed = fixed.replace(
      /(self\.vm\(\)\.log\([^;]*\))\?/g,
      "$1"
    );

    // Fix 26: .as_usize() → .to::<usize>()
    fixed = fixed.replace(
      /\.as_usize\(\)/g,
      ".to::<usize>()"
    );

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

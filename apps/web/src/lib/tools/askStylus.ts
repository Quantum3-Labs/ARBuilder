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

  // Build context string with optional code context (cap per-item to prevent token overflow)
  const MAX_CONTEXT_CHARS = 2000;
  let contextStr = contextResult.contexts
    .slice(0, 3) // Top 3 most relevant
    .map((c, i) => `[${i + 1}] (${c.source})\n${c.content.slice(0, MAX_CONTEXT_CHARS)}`)
    .join("\n\n---\n\n");

  if (codeContext) {
    contextStr = `User's Code:\n\`\`\`rust\n${codeContext}\n\`\`\`\n\n---\n\n${contextStr}`;
  }

  // Get answer from LLM (chatCompletion retries 3x on empty)
  const response = await answerQuestion(openrouterApiKey, question, contextStr);

  // Fallback: if LLM returned empty after all retries, use RAG context summary
  let responseContent = response.content;
  if (!responseContent || responseContent.trim().length === 0) {
    const ctxSummary = contextResult.contexts
      .slice(0, 3)
      .map((c) => `From ${c.source}:\n${c.content.slice(0, 500)}`)
      .join("\n\n---\n\n");
    responseContent = ctxSummary
      ? `Here are relevant excerpts from the documentation:\n\n${ctxSummary}`
      : `I couldn't generate a detailed answer right now. Please try again or check https://docs.arbitrum.io/stylus`;
  }

  // Fix wrong patterns in code blocks (RAG context often overrides system prompt)
  const fixedContent = fixCodeInResponse(responseContent);

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
      // Allow optional whitespace/newlines between ) and .set( for multiline chains
      fixed = fixed.replace(
        new RegExp(`\\.${af}\\.setter\\(((?:[^()]*|\\([^()]*\\))*)\\)\\s*\\.set\\(`, "g"),
        `.${af}.setter($1).unwrap().set(`
      );
    }

    // Fix 27: .get(k1).setter(k2) → .setter(k1).setter(k2)
    // Nested mapping writes: .get() returns immutable ref, can't
    // call .setter() on it. Must chain .setter() for writes.
    // Allow optional whitespace/newlines between ) and .setter( for multiline chains.
    fixed = fixed.replace(
      /\.get\(((?:[^()]*|\([^()]*\))*)\)\s*\.setter\(/g,
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

    // Fix 32: sol_interface! calls must have self.vm() as first host argument
    fixed = fixed.replace(
      /\b(\w+)\.(\w+)\(Call::new\(\)/g,
      "$1.$2(self.vm(), Call::new()"
    );
    fixed = fixed.replace(
      /\b(\w+)\.(\w+)\(Call::new_mutating\(self\)/g,
      "$1.$2(self.vm(), Call::new_mutating(self)"
    );
    const askCallVarPattern = /let\s+(?:mut\s+)?(\w+)\s*=\s*Call::new/g;
    let askCallVarMatch;
    while ((askCallVarMatch = askCallVarPattern.exec(fixed)) !== null) {
      const cvar = askCallVarMatch[1];
      fixed = fixed.replace(
        new RegExp(`\\b(\\w+)\\.(\\w+)\\(${cvar},\\s*`, "g"),
        `$1.$2(self.vm(), ${cvar}, `
      );
    }

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

    // Fix 33: B256::from_limbs([...]) → B256::from(U256::from_limbs([...]).to_be_bytes::<32>())
    // B256 is FixedBytes<32>, NOT Uint. from_limbs is a Uint method.
    fixed = fixed.replace(
      /B256::from_limbs\((\[[^\]]*\])\)/g,
      "B256::from(U256::from_limbs($1).to_be_bytes::<32>())"
    );

    // Fix 34: mapping(... => string) .get(key) returns StorageGuard<StorageString>.
    // Two-pass approach to avoid doubling .get_string().
    const askStringMapFields = new Set<string>();
    const askStringMapPattern = /mapping\([^=]+=>\s*string\)\s+(\w+)\s*;/g;
    let askStringMapMatch;
    while ((askStringMapMatch = askStringMapPattern.exec(fixed)) !== null) {
      askStringMapFields.add(askStringMapMatch[1]);
    }
    for (const smf of askStringMapFields) {
      // Pass 1: .field.get(k).get_string() → .field.getter(k).get_string()
      fixed = fixed.replace(
        new RegExp(`\\.${smf}\\.get\\(([^)]+)\\)\\.get_string\\(\\)`, "g"),
        `.${smf}.getter($1).get_string()`
      );
      // Pass 2: bare .field.get(k) → .field.getter(k).get_string()
      fixed = fixed.replace(
        new RegExp(`\\.${smf}\\.get\\(([^)]+)\\)`, "g"),
        `.${smf}.getter($1).get_string()`
      );
    }
    // Cleanup: doubled .get_string() chains
    fixed = fixed.replace(
      /\.get_string\(\)(?:\.getter\([^)]*\))?\.get_string\(\)/g,
      ".get_string()"
    );
    // Cleanup: local_var.get_string() is always wrong.
    fixed = fixed.replace(
      /\b([a-z_]\w*)\.get_string\(\)/g,
      (_match: string, varName: string) => varName === "self" ? _match : varName
    );

    // Fix 35: .abi_encode() on SolidityError enum wrapper.
    fixed = fixed.replace(
      /(\w+)::(\w+)\((\2\s*\{[^}]*\})\)\.abi_encode\(\)/g,
      "$3.abi_encode()"
    );

    // Fix 36: StorageString returned directly without .get_string().
    const askStrFields = new Set<string>();
    const askStrFieldPattern = /\bstring\s+(\w+)\s*;/g;
    let askStrFieldMatch;
    while ((askStrFieldMatch = askStrFieldPattern.exec(fixed)) !== null) {
      askStrFields.add(askStrFieldMatch[1]);
    }
    for (const sf of askStrFields) {
      fixed = fixed.replace(
        new RegExp(`self\\.${sf}(?![.\\w])`, "g"),
        `self.${sf}.get_string()`
      );
    }

    // Fix 9d + Fix 37 (N31): Ensure correct alloc::string imports, no duplicates.
    {
      const nsString = fixed.includes("-> String") || fixed.includes(": String") || fixed.includes(".to_string()") || fixed.includes("String::new") || fixed.includes("String::from");
      const nsToString = fixed.includes(".to_string()");
      if (nsString || nsToString) {
        // Remove all existing alloc::string imports to avoid duplicates
        fixed = fixed.replace(/^use alloc::string::\{[^}]*\};\s*\n?/gm, "");
        fixed = fixed.replace(/^use alloc::string::\w+;\s*\n?/gm, "");
        const parts: string[] = [];
        if (nsString) parts.push("String");
        if (nsToString) parts.push("ToString");
        if (parts.length > 0 && fixed.includes("use alloc::{vec, vec::Vec};")) {
          const importLine = parts.length === 1
            ? `use alloc::string::${parts[0]};`
            : `use alloc::string::{${parts.join(", ")}};`;
          fixed = fixed.replace(
            /(use alloc::\{vec, vec::Vec\};)/,
            `$1\n${importLine}`
          );
        }
      }
    }

    // Fix 38 (N32): Move `pub const` out of #[public] impl blocks
    {
      const constInImplPattern = /^([ \t]*)pub const\s+(\w+)\s*:\s*(\w+)\s*=\s*([^;]+);/gm;
      const consts: Array<{ full: string; name: string; ty: string; val: string }> = [];
      let cm;
      while ((cm = constInImplPattern.exec(fixed)) !== null) {
        const before = fixed.slice(0, cm.index);
        const lastPub = before.lastIndexOf("#[public]");
        const lastClose = before.lastIndexOf("\n}\n");
        if (lastPub > -1 && lastPub > lastClose) {
          consts.push({ full: cm[0], name: cm[2], ty: cm[3], val: cm[4].trim() });
        }
      }
      for (const c of consts) {
        fixed = fixed.replace(c.full + "\n", "");
        fixed = fixed.replace(c.full, "");
        fixed = fixed.replace(
          /(\n#\[public\])/,
          `\nconst ${c.name}: ${c.ty} = ${c.val};\n$1`
        );
      }
    }

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

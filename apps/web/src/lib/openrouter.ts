/**
 * OpenRouter API client for LLM calls.
 *
 * Uses DeepSeek for code generation and Gemini for Q&A.
 */

import {
  getMainVersion,
  getVersionPatterns,
  getAlloyPrimitivesVersion,
} from "./stylusVersions";
import type { StylusTemplate } from "./templates/stylusTemplates";

const OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions";

export interface Message {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface ChatCompletionOptions {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  stream?: boolean;
}

export interface ChatCompletionResponse {
  content: string;
  model: string;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

// Default models - using Gemini for all operations
export const MODELS = {
  CODE_GEN: "google/gemini-3-flash-preview",
  QA: "google/gemini-3-flash-preview",
  FAST: "google/gemini-3-flash-preview",
} as const;

/**
 * Call OpenRouter API for chat completions.
 */
export async function chatCompletion(
  apiKey: string,
  messages: Message[],
  options: ChatCompletionOptions = {}
): Promise<ChatCompletionResponse> {
  const {
    model = MODELS.CODE_GEN,
    temperature = 0.2,
    maxTokens = 4096,
    stream = false,
  } = options;

  const response = await fetch(OPENROUTER_API_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://arbbuilder.whymelabs.com",
      "X-Title": "ARBuilder",
    },
    body: JSON.stringify({
      model,
      messages,
      temperature,
      max_tokens: maxTokens,
      stream,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`OpenRouter API error: ${response.status} - ${error}`);
  }

  const data = (await response.json()) as {
    choices: Array<{ message?: { content?: string } }>;
    model: string;
    usage?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
  };

  return {
    content: data.choices[0]?.message?.content ?? "",
    model: data.model,
    usage: {
      promptTokens: data.usage?.prompt_tokens ?? 0,
      completionTokens: data.usage?.completion_tokens ?? 0,
      totalTokens: data.usage?.total_tokens ?? 0,
    },
  };
}

/**
 * Build version-aware system prompt for code generation.
 */
function buildCodeGenSystemPrompt(targetVersion: string): string {
  const patterns = getVersionPatterns(targetVersion);
  const alloyVersion = getAlloyPrimitivesVersion(targetVersion);
  const mainAttr = patterns.attributes[0] || "#[public]";
  const errorHandling = patterns.error_handling;
  const cfgAttr = patterns.cfg_attr;

  return `You are an expert Stylus (Rust) smart contract developer for Arbitrum.
You write clean, secure, and gas-efficient code following best practices.
Use the provided context from the Stylus documentation and examples.

Target SDK Version: stylus-sdk ${targetVersion}

Key patterns for v${targetVersion}:
- Use stylus-sdk ${targetVersion} with alloy-primitives ${alloyVersion}
- Include ${cfgAttr}
- Use sol_storage! macro for storage
- Use ${mainAttr} for external functions
- Handle errors with ${errorHandling}
- Follow Rust naming conventions (snake_case for functions, PascalCase for types)
- For ETH transfers: use transfer_eth(self, to, amount) from stylus_sdk::call::transfer
- For error types: define with sol! { error MyError(...); }, wrap in enum with #[derive(SolidityError)]
- For .abi_encode() on errors: import SolError via use alloy_sol_types::SolError
- Avoid chained .setter() borrows — get value with .get() first, then .setter().set() separately
- Do NOT use stylus_sdk::evm (removed in 0.10.0) or stylus_sdk::msg
- ALWAYS include \`use alloc::{vec, vec::Vec};\` — sol_storage! needs vec module in scope
- RawCall::new_with_value(self.vm(), amount) — requires self.vm() as first arg and unsafe block
- uint8 in sol_storage! maps to Uint<8,1> not native u8 — prefer uint256
- Package name in Cargo.toml MUST use underscores (e.g., "my_contract") — hyphens break cargo-stylus
- src/main.rs is REQUIRED — use print_from_args() (NOT print_abi()) for ABI export
- crate-type in [lib] must be ["lib", "cdylib"]
- For sol_interface! cross-contract calls: methods take (self.vm(), Call::new(), ...args). Call::new_in(self) from 0.9.x is removed.
- Stylus exports snake_case Rust fn names as camelCase in the ABI (create_market → createMarket). Frontend must use camelCase in functionName.
- Stylus &self view functions CANNOT make external contract calls (they revert). Use &mut self or read from frontend.
- On Arbitrum Sepolia, MetaMask may underestimate maxFeePerGas — add explicit gas overrides if "max fee per gas less than block base fee"

Security best practices:
- Check for overflows using checked_add/checked_sub
- Validate all inputs
- Use proper access control`;
}

/**
 * Generate Stylus code using DeepSeek.
 *
 * @param apiKey - OpenRouter API key
 * @param prompt - Code generation prompt
 * @param context - RAG context from documentation
 * @param targetVersion - Target stylus-sdk version (default: main version)
 */
export async function generateCode(
  apiKey: string,
  prompt: string,
  context: string,
  targetVersion?: string
): Promise<ChatCompletionResponse> {
  const version = targetVersion || getMainVersion();
  const systemPrompt = buildCodeGenSystemPrompt(version);

  const messages: Message[] = [
    {
      role: "system",
      content: systemPrompt,
    },
    {
      role: "user",
      content: `Context from documentation:\n${context}\n\n---\n\nTask: ${prompt}`,
    },
  ];

  return chatCompletion(apiKey, messages, {
    model: MODELS.CODE_GEN,
    temperature: 0.2,
  });
}

/**
 * Generate Stylus code from a verified working template.
 *
 * This approach uses a curated template as the foundation, asking the LLM
 * to customize it rather than generate from scratch. This ensures the
 * output maintains the correct structure and compiles successfully.
 *
 * @param apiKey - OpenRouter API key
 * @param prompt - User's customization request
 * @param template - Base template from official examples
 * @param context - Additional RAG context for specific patterns
 * @param targetVersion - Target stylus-sdk version
 */
export async function generateCodeFromTemplate(
  apiKey: string,
  prompt: string,
  template: StylusTemplate,
  context: string,
  targetVersion?: string
): Promise<ChatCompletionResponse> {
  const version = targetVersion || getMainVersion();
  const alloyVersion = getAlloyPrimitivesVersion(version);

  const systemPrompt = `You are an expert Stylus (Rust) smart contract developer for Arbitrum.

CRITICAL: You are customizing a WORKING template. The template below compiles and deploys correctly.
Your job is to MODIFY this template to match the user's requirements while keeping the EXACT structure intact.

Base Template: ${template.name}
Template Description: ${template.description}
Template Features: ${template.features.join(", ")}

Target SDK Version: stylus-sdk ${version}
Alloy Primitives: ${alloyVersion}

ABSOLUTE RULES - NEVER VIOLATE THESE:
1. KEEP the EXACT first 4 lines: #![cfg_attr...], #![cfg_attr...], #[macro_use], extern crate alloc;
2. KEEP all use statements from the template - you may ADD more but NEVER remove
3. There must be EXACTLY ONE sol_storage! block - NEVER create empty sol_storage! blocks
4. KEEP the #[entrypoint] attribute inside sol_storage!
5. KEEP the #[public] attribute on the impl block
6. The sol! macro is available via prelude — do NOT add standalone "use alloy_sol_types::sol;". BUT if using .abi_encode() on errors, MUST import SolError: use alloy_sol_types::SolError;
7. If adding events/errors with sol! macro, they must be BEFORE sol_storage!
8. KEEP the Cargo.toml [profile.release] section exactly as provided

WHAT YOU MAY DO:
- Add/modify storage fields inside sol_storage!
- Add/modify functions inside the #[public] impl block
- Add events using sol! { event EventName(...); } BEFORE sol_storage!
- Add error types using sol! { error ErrorName(...); } BEFORE sol_storage!
- Add internal helper functions (without #[public])

IMPORTS - USE THESE PATTERNS:
- Types from stylus_sdk::alloy_primitives::{Address, U256, U8, ...}
- sol! macro is available from stylus_sdk::prelude::*
- For events: self.vm().log(EventName { field1, field2 }) (NOT evm::log)
- For caller: self.vm().msg_sender() (NOT msg::sender())
- For ETH transfers: transfer_eth(self, to, amount) from stylus_sdk::call::transfer
- For errors: return Err(ErrorName { ... }.abi_encode()) — requires use alloy_sol_types::SolError;
- Do NOT use stylus_sdk::evm (removed in 0.10.0) or stylus_sdk::msg

Output format:
1. Brief explanation of changes (1-2 sentences)
2. Complete lib.rs in a \`\`\`rust code block

IMPORTANT: Do NOT output Cargo.toml - the template's Cargo.toml will be used as-is.`;

  const userPrompt = `BASE TEMPLATE (lib.rs):
\`\`\`rust
${template.libRs}
\`\`\`

BASE TEMPLATE (Cargo.toml):
\`\`\`toml
${template.cargoToml}
\`\`\`

${context ? `ADDITIONAL PATTERNS FROM DOCUMENTATION:\n${context}\n\n` : ""}USER REQUEST:
${prompt}

Please customize the template to implement the user's request. Keep the working structure intact.`;

  const messages: Message[] = [
    { role: "system", content: systemPrompt },
    { role: "user", content: userPrompt },
  ];

  return chatCompletion(apiKey, messages, {
    model: MODELS.CODE_GEN,
    temperature: 0.2,
    maxTokens: 8192, // Allow longer output for complete contracts
  });
}

/**
 * Answer questions about Stylus development.
 */
export async function answerQuestion(
  apiKey: string,
  question: string,
  context: string
): Promise<ChatCompletionResponse> {
  const mainVersion = getMainVersion();
  const alloyVersion = getAlloyPrimitivesVersion(mainVersion);

  const messages: Message[] = [
    {
      role: "system",
      content: `You are a helpful Stylus development assistant.
Answer questions about Stylus smart contract development on Arbitrum.
Use the provided context to give accurate, up-to-date answers.
Include code examples when relevant.
Be concise but thorough.

CRITICAL VERSION INFORMATION (January 2026):
ALWAYS use these versions - ignore any outdated version info in retrieved context:
- stylus-sdk: ${mainVersion} (latest stable, recommended for new projects)
- alloy-primitives: ${alloyVersion}
- alloy-sol-types: ${alloyVersion}
- Rust version: 1.88.0 (via rust-toolchain.toml)

IMPORTANT SDK 0.10.0 changes:
- msg::sender() is replaced by self.vm().msg_sender()
- msg::value() is replaced by self.vm().msg_value()
- evm::log() is replaced by self.vm().log()
- use stylus_sdk::evm is removed entirely — use self.vm() methods
- transfer_eth moved to stylus_sdk::call::transfer, needs self context
- Error types: define with sol! { error MyError(...); }, wrap enum with #[derive(SolidityError)]
- For .abi_encode() on errors: import use alloy_sol_types::SolError;
- Chained .setter() borrows cause compile errors — read with .get() first, then .setter().set() separately
- Projects MUST include Stylus.toml with [workspace], [workspace.networks], and [contract] sections
- Projects MUST include rust-toolchain.toml with channel = "1.88.0"
- Projects MUST include src/main.rs — cargo stylus deploy uses cargo run to check constructors
- ABI export function in 0.10.0 is print_from_args() (NOT print_abi())
- Package name MUST use underscores (e.g., "my_contract") — hyphens break cargo-stylus WASM lookup
- crate-type must be ["lib", "cdylib"] — "lib" needed for bin target linking
- ALWAYS include use alloc::{vec, vec::Vec}; — sol_storage! needs vec module
- RawCall::new_with_value(self.vm(), amount) — needs self.vm() as first arg and unsafe block
- uint8 in sol_storage! maps to Uint<8,1>, not u8 — comparisons with u8 won't compile

When asked about versions, ALWAYS use the version info above, NOT from retrieved context which may be outdated.`,
    },
    {
      role: "user",
      content: `Context from documentation:\n${context}\n\n---\n\nQuestion: ${question}`,
    },
  ];

  return chatCompletion(apiKey, messages, {
    model: MODELS.QA,
    temperature: 0.3,
  });
}

/**
 * Answer questions about Arbitrum bridging and SDK.
 */
export async function answerBridgingQuestion(
  apiKey: string,
  question: string,
  context: string
): Promise<ChatCompletionResponse> {
  const messages: Message[] = [
    {
      role: "system",
      content: `You are an expert on Arbitrum SDK, cross-chain bridging, and messaging.
Answer questions about:
- ETH and ERC20 bridging (L1 <-> L2) using EthBridger and Erc20Bridger
- L1 -> L3 bridging for Orbit chains using EthL1L3Bridger and Erc20L1L3Bridger
- Cross-chain messaging via retryable tickets (L1->L2) and ArbSys (L2->L1)
- Challenge periods, gas estimation, and message status tracking

Use the provided context from the Arbitrum SDK documentation and code examples.
Include TypeScript/JavaScript code examples when relevant.
Be accurate about timings: L1->L2 takes ~10-15 min, L2->L1 takes ~7 days.
Reference the correct SDK v4 classes: ParentTransactionReceipt, ChildTransactionReceipt, etc.`,
    },
    {
      role: "user",
      content: `Context from Arbitrum SDK documentation:\n${context}\n\n---\n\nQuestion: ${question}`,
    },
  ];

  return chatCompletion(apiKey, messages, {
    model: MODELS.QA,
    temperature: 0.3,
  });
}

/**
 * Generate tests for Stylus contract code.
 */
export async function generateTests(
  apiKey: string,
  contractCode: string,
  testFramework: "rust_native" | "foundry" = "rust_native"
): Promise<ChatCompletionResponse> {
  const messages: Message[] = [
    {
      role: "system",
      content: `You are a Stylus testing expert.
Generate comprehensive tests for the provided contract.
Framework: ${testFramework === "rust_native" ? "Rust native #[test] with stylus-test" : "Foundry Solidity tests"}

For Rust native tests:
- Use #[cfg(test)] module
- Import stylus_sdk::testing if needed
- Test all public functions
- Include edge cases and error conditions

For Foundry tests:
- Create Solidity interface matching the contract ABI
- Use forge-std Test contract
- Mock contract deployment`,
    },
    {
      role: "user",
      content: `Generate tests for this contract:\n\n\`\`\`rust\n${contractCode}\n\`\`\``,
    },
  ];

  return chatCompletion(apiKey, messages, {
    model: MODELS.CODE_GEN,
    temperature: 0.2,
  });
}

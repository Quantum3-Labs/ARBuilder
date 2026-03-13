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
  finishReason: string;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

// Default models — FALLBACK used when primary exhausts retries
export const MODELS = {
  CODE_GEN: "openai/gpt-oss-120b",
  QA: "openai/gpt-oss-120b",
  FAST: "openai/gpt-oss-120b",
  FALLBACK: "qwen/qwen3.5-flash-02-23",
} as const;

const EMPTY_RESPONSE: ChatCompletionResponse = {
  content: "",
  model: "unknown",
  finishReason: "error",
  usage: { promptTokens: 0, completionTokens: 0, totalTokens: 0 },
};

/**
 * Make a single OpenRouter API call. Returns parsed response or throws.
 */
async function singleCall(
  apiKey: string,
  model: string,
  messages: Message[],
  temperature: number,
  maxTokens: number,
): Promise<{
  content: string;
  finishReason: string;
  model: string;
  usage: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number };
}> {
  const response = await fetch(OPENROUTER_API_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://arbuilder.app",
      "X-Title": "ARBuilder",
    },
    body: JSON.stringify({
      model,
      messages,
      temperature,
      max_tokens: maxTokens,
      stream: false,
    }),
  });

  // Non-retryable client errors
  if (response.status === 400 || response.status === 401 || response.status === 403) {
    const error = await response.text();
    throw new Error(`NON_RETRYABLE: HTTP ${response.status}: ${error.slice(0, 200)}`);
  }

  // Retryable server errors
  if (response.status === 429 || response.status >= 500) {
    throw new Error(`RETRYABLE: HTTP ${response.status}`);
  }

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`NON_RETRYABLE: HTTP ${response.status}: ${error.slice(0, 200)}`);
  }

  const data = (await response.json()) as {
    choices: Array<{ message?: { content?: string }; finish_reason?: string }>;
    model: string;
    usage?: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number };
  };

  const content = data.choices[0]?.message?.content ?? "";
  const finishReason = data.choices[0]?.finish_reason ?? "unknown";

  return { content, finishReason, model: data.model, usage: data.usage ?? {} };
}

/**
 * Call OpenRouter API for chat completions with production-grade resilience.
 *
 * Strategy:
 * 1. Try primary model up to 3 times with exponential backoff (1s, 2s, 4s)
 * 2. On finish_reason="length" (truncation), increase maxTokens by 1.5x
 * 3. On empty response or transient error, retry with backoff
 * 4. After primary model exhausted, try fallback model up to 2 times
 * 5. Returns empty content only after ALL attempts fail
 *
 * Never throws — callers can use their own fallback logic.
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

  // Phase 1: Primary model — 3 attempts with escalation
  let currentMaxTokens = maxTokens;
  const PRIMARY_ATTEMPTS = 3;

  for (let attempt = 0; attempt < PRIMARY_ATTEMPTS; attempt++) {
    try {
      const result = await singleCall(apiKey, model, messages, temperature, currentMaxTokens);

      // Check for truncation — increase maxTokens and retry
      if (result.finishReason === "length") {
        const oldTokens = currentMaxTokens;
        currentMaxTokens = Math.min(Math.ceil(currentMaxTokens * 1.5), 32000);
        console.warn(
          `[chatCompletion] Truncated (finish_reason=length) on attempt ${attempt + 1}/${PRIMARY_ATTEMPTS}. ` +
          `Model: ${result.model}. Escalating maxTokens: ${oldTokens} → ${currentMaxTokens}`
        );
        // If content is non-empty despite truncation, it may still be usable on last attempt
        if (attempt === PRIMARY_ATTEMPTS - 1 && result.content.trim().length > 0) {
          console.warn(`[chatCompletion] Using truncated response on final primary attempt`);
          return {
            content: result.content,
            model: result.model,
            finishReason: result.finishReason,
            usage: {
              promptTokens: result.usage.prompt_tokens ?? 0,
              completionTokens: result.usage.completion_tokens ?? 0,
              totalTokens: result.usage.total_tokens ?? 0,
            },
          };
        }
        // No backoff on truncation — retry immediately with higher maxTokens
        continue;
      }

      // Check for empty response — retry immediately (no backoff)
      if (!result.content || result.content.trim().length === 0) {
        console.warn(
          `[chatCompletion] Empty response on attempt ${attempt + 1}/${PRIMARY_ATTEMPTS}. ` +
          `Model: ${result.model}, finish_reason: ${result.finishReason}`
        );
        continue;
      }

      // Success
      return {
        content: result.content,
        model: result.model,
        finishReason: result.finishReason,
        usage: {
          promptTokens: result.usage.prompt_tokens ?? 0,
          completionTokens: result.usage.completion_tokens ?? 0,
          totalTokens: result.usage.total_tokens ?? 0,
        },
      };
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : String(e);
      if (errMsg.startsWith("NON_RETRYABLE:")) {
        console.error(`[chatCompletion] Non-retryable error: ${errMsg}`);
        break; // Skip to fallback
      }
      console.warn(
        `[chatCompletion] Error on attempt ${attempt + 1}/${PRIMARY_ATTEMPTS}: ${errMsg}`
      );
      await backoff(attempt);
    }
  }

  // Phase 2: Fallback model — 2 attempts
  const FALLBACK_ATTEMPTS = 2;
  console.warn(
    `[chatCompletion] Primary model ${model} exhausted. Trying fallback: ${MODELS.FALLBACK}`
  );

  for (let attempt = 0; attempt < FALLBACK_ATTEMPTS; attempt++) {
    try {
      const result = await singleCall(
        apiKey, MODELS.FALLBACK, messages, temperature, currentMaxTokens
      );

      if (!result.content || result.content.trim().length === 0) {
        console.warn(
          `[chatCompletion] Fallback empty on attempt ${attempt + 1}/${FALLBACK_ATTEMPTS}. ` +
          `finish_reason: ${result.finishReason}`
        );
        continue;
      }

      console.warn(
        `[chatCompletion] Fallback model succeeded: ${result.model} ` +
        `(${result.usage.total_tokens ?? 0} tokens)`
      );
      return {
        content: result.content,
        model: result.model,
        finishReason: result.finishReason,
        usage: {
          promptTokens: result.usage.prompt_tokens ?? 0,
          completionTokens: result.usage.completion_tokens ?? 0,
          totalTokens: result.usage.total_tokens ?? 0,
        },
      };
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : String(e);
      console.warn(
        `[chatCompletion] Fallback error on attempt ${attempt + 1}/${FALLBACK_ATTEMPTS}: ${errMsg}`
      );
      if (errMsg.startsWith("NON_RETRYABLE:")) break;
      await backoff(attempt);
    }
  }

  console.error(
    `[chatCompletion] All attempts failed. Primary: ${model} (${PRIMARY_ATTEMPTS}x), ` +
    `Fallback: ${MODELS.FALLBACK} (${FALLBACK_ATTEMPTS}x). maxTokens escalated to ${currentMaxTokens}`
  );
  return EMPTY_RESPONSE;
}

/** Exponential backoff: 1s, 2s, 4s */
function backoff(attempt: number): Promise<void> {
  const delay = Math.min(1000 * Math.pow(2, attempt), 4000);
  return new Promise((r) => setTimeout(r, delay));
}

/**
 * Shared Stylus compilation rules — single source of truth.
 * Used by buildCodeGenSystemPrompt(), generateCodeFromTemplate(), and answerQuestion().
 * Deduped from ~70 rules that were previously duplicated across prompts.
 */
const STYLUS_COMPILATION_RULES = `STORAGE ACCESS:
- ALWAYS use .get() to read: \`self.field.get()\` NOT \`self.field\`. Use .set(val) to write: \`self.field.set(val)\`.
- For mappings: read with \`self.map.get(key)\`, write with \`self.map.setter(key).set(val)\`.
- .setter(key) is ONLY for mappings. For simple fields (uint256, address, bool), use \`self.field.set(val)\` directly — NOT \`self.field.setter().set(val)\`.
- StorageMap::get(key) returns value directly (zero-default), NOT Option. Do NOT use .unwrap_or_default().
- NESTED MAPPINGS: read with \`self.map.get(k1).get(k2)\`. Write by chaining .setter(): \`self.map.setter(k1).setter(k2).set(v)\`. Do NOT mix .get() then .setter(). Do NOT use tuple keys.
- StorageString: Use \`.set_str("val")\` and \`.get_string()\`. NOT .set() or .get().
- STRING MAPPING READS: \`mapping(... => string)\` — \`.get(key)\` returns StorageGuard<StorageString>, NOT String. Use \`.getter(key).get_string()\`. Do NOT call .get_string() again on result. Write: \`.setter(key).set_str("val")\`.
- STORAGESTRING VIEW FUNCTIONS: ALWAYS call .get_string(): \`pub fn name(&self) -> String { self.name.get_string() }\`. NEVER return self.name directly. Do NOT use .push_str() on StorageString.
- StorageVec API: len() returns usize. setter(i) returns Option — call .unwrap() before .set(). Convert U256: index.to::<usize>(). Do NOT use .as_usize().
- DYNAMIC ARRAYS: Declare as \`uint256[] items;\`. Append with .push(val) for primitives, .grow() for structs. Do NOT use .setter(len).unwrap().
- BORROW CHECKER: Extract values to local vars before combining storage reads and writes.
- MUTABLE BINDINGS: .setter() result stored in a variable needs \`let mut\`.

IMPORTS AND no_std:
- ALWAYS include \`use alloc::{vec, vec::Vec};\` — sol_storage! needs vec module in scope.
- String: \`use alloc::string::String;\`. .to_string(): ALSO \`use alloc::string::ToString;\`. NOT in prelude.
- Call comes from prelude::*. Do NOT add \`use stylus_sdk::call::Call;\` separately.
- Do NOT use stylus_sdk::evm (removed in 0.10.0) or stylus_sdk::msg.
- Do NOT use std::time, std::collections. For timestamps: self.vm().block_timestamp().

EXTERNAL INTERFACES:
- CRITICAL: sol! is for events and errors ONLY. External contract interfaces MUST use sol_interface!.
- sol_interface! generates Rust methods in snake_case: transferFrom → .transfer_from(), balanceOf → .balance_of(), totalSupply → .total_supply(), latestPrice → .latest_price(). ALWAYS convert ALL camelCase to snake_case — this applies to EVERY method, not just common ones.
- sol_interface! HOST ARG: self.vm() MUST be the FIRST argument, then Call context, then Solidity args.
- VIEW calls: Call::new(). STATE-MODIFYING calls: extract Call first: \`let call = Call::new_mutating(self);\` — avoids borrow conflict.
- External calls require &mut self (NOT &self — view functions revert on external calls).

TYPES:
- B256 is FixedBytes<32>, NOT Uint<256>. B256::from_uint() and B256::from_limbs() do NOT exist. Use B256::from(value.to_be_bytes::<32>()). For limbs: B256::from(U256::from_limbs([...]).to_be_bytes::<32>()). B256::ZERO for zero.
- CONST U256: U256::from() is NOT const-compatible. Use U256::from_limbs([N, 0, 0, 0]).
- I256: implements From<i64> but NOT From<i128>. Use I256::from(1) (bare literal).
- U8: uint8 → U8 (Uint<8,1>), not native u8. Set: U8::from(val). Read: .to::<u8>().
- UINT CONVERSION: .as_usize(), .as_u64(), .as_u32(), .as_u128() do NOT exist on alloy Uint. Use .to::<usize>(), .to::<u64>(), etc.
- ZERO CONSTANTS: U256::ZERO, Address::ZERO (uppercase const). NOT .zero() methods.
- unwrap_or(VALUE) for values, unwrap_or_else(|| VALUE) for closures.

EVENTS AND ERRORS:
- sol! MACRO: MUST \`use alloy_sol_types::{sol, SolError};\` — NOT in prelude.
- sol! fields use camelCase: tokenId NOT token_id.
- sol! STRUCT INIT: ALWAYS use explicit \`field: value\` syntax with camelCase field name on left, snake_case variable on right.
  WRONG: \`Transfer { from, to, tokenId }\` — shorthand fails because \`tokenId\` variable doesn't exist in Rust (it's \`token_id\`).
  WRONG: \`CapExceeded { newCap }\` — no local \`newCap\` exists.
  CORRECT: \`Transfer { from, to, tokenId: token_id }\`.
  CORRECT: \`CapExceeded { newCap: new_cap }\`.
  Rule: if the field name contains an uppercase letter after a lowercase letter (camelCase), you MUST use explicit \`field: value\` syntax. Only pure lowercase fields (from, to, owner) can use shorthand.
- sol! TYPE MATCHING: address → Address, uint256 → U256. Match RUST TYPE, not semantic meaning.
- abi_encode(): on inner sol! error struct, NOT the #[derive(SolidityError)] enum.
- EVENT/ERROR NAMING: Never same name for event and error.
- SolidityError ENUM: Each variant wraps a DISTINCT error type.
- Put all errors in one sol! {} block. Never define same name twice.
- vm().log() returns () — do NOT use ? after it.

SDK API:
- TRANSFER ETH: \`use stylus_sdk::call::transfer::transfer_eth;\` then \`transfer_eth(self.vm(), to, amount)?;\`.
- CONTRACT ADDRESS: self.vm().contract_address() NOT self.vm().address().
- BLOCK TIMESTAMP: self.vm().block_timestamp() returns u64. Wrap with U256::from() for uint256 fields.
- RESULT PROPAGATION: Always use ? to propagate Result from helper methods.
- RawCall::new_with_value(self.vm(), amount) — requires self.vm() and unsafe block.

PROJECT STRUCTURE:
- sol_storage! SYNTAX: type + name + semicolon ONLY. NO default values. Use Solidity types: uint256, address, bool, string, mapping(...), type[]. NOT Rust Storage* types.
- Exactly ONE sol_storage! block with #[entrypoint].
- Package name MUST use underscores. crate-type = ["lib", "cdylib"]. src/main.rs required with print_from_args().

OUTPUT:
- CLEAN OUTPUT: Output ONLY valid Rust code. No commentary inside code blocks.
- NO CONST IN #[public] IMPL: Move constants to module level.
- NO PHANTOM VARIABLES: Functions get data from storage/parameters. Never \`let role = role;\`.
- ABI exports snake_case as camelCase. Frontend must use camelCase.`;

/**
 * Shared reference code examples for Stylus patterns.
 * Used by generateCodeFromTemplate() and answerQuestion().
 */
const STYLUS_REFERENCE_CODE = `ETH transfer:
\`\`\`rust
use stylus_sdk::call::transfer::transfer_eth;

pub fn withdraw(&mut self, to: Address, amount: U256) -> Result<(), Vec<u8>> {
    transfer_eth(self.vm(), to, amount)?;
    Ok(())
}
\`\`\`

Cross-contract VIEW call:
\`\`\`rust
sol_interface! {
    interface IPriceFeed {
        function latestPrice() external view returns (uint256);
    }
}

pub fn get_price(&mut self, feed_addr: Address) -> Result<U256, Vec<u8>> {
    let feed = IPriceFeed::new(feed_addr);
    let price = feed.latest_price(self.vm(), Call::new())?;
    Ok(price)
}
\`\`\`

Cross-contract state-modifying call:
\`\`\`rust
sol_interface! {
    interface IToken {
        function transfer(address to, uint256 amount) external returns (bool);
    }
}

pub fn transfer_tokens(
    &mut self, token: Address, to: Address, amount: U256,
) -> Result<bool, Vec<u8>> {
    let tok = IToken::new(token);
    let call = Call::new_mutating(self);
    let success = tok.transfer(self.vm(), call, to, amount)?;
    Ok(success)
}
\`\`\`

Storage access:
\`\`\`rust
let val = self.my_field.get();
let balance = self.balances.get(user);
self.my_field.set(new_val);
self.balances.setter(user).set(new_balance);
\`\`\`

Nested mapping:
\`\`\`rust
let allowance = self.allowances.get(owner).get(spender);
self.allowances.setter(owner).setter(spender).set(value);
\`\`\`

Dynamic array:
\`\`\`rust
self.items.push(new_val);
// For structs: let mut entry = self.items.grow(); entry.field.set(val);
\`\`\``;

/**
 * Build version-aware system prompt for code generation (uses shared STYLUS_COMPILATION_RULES).
 */
function buildCodeGenSystemPrompt(targetVersion: string): string {
  const alloyVersion = getAlloyPrimitivesVersion(targetVersion);
  const patterns = getVersionPatterns(targetVersion);
  const cfgAttr = patterns.cfg_attr;

  return `You are an expert Stylus (Rust) smart contract developer for Arbitrum.
You write clean, secure, and gas-efficient code following best practices.
Use the provided context from the Stylus documentation and examples.

Target SDK Version: stylus-sdk ${targetVersion}
Alloy Primitives: ${alloyVersion}
Config: ${cfgAttr}

Follow Rust naming conventions (snake_case for functions, PascalCase for types).

${STYLUS_COMPILATION_RULES}

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
    maxTokens: 12000,
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
6. When using sol! for events or errors, you MUST explicitly import it: \`use alloy_sol_types::{sol, SolError};\`
7. If adding events/errors with sol! macro, they must be BEFORE sol_storage!
7b. EVERY event emitted with self.vm().log() MUST be declared in a sol! block
8. KEEP the Cargo.toml [profile.release] section exactly as provided

${STYLUS_COMPILATION_RULES}

WHAT YOU MAY DO:
- Rename the contract struct in sol_storage!
- Add/modify storage fields inside sol_storage!
- Add/modify functions inside the #[public] impl block
- Add events/errors using sol! { } BEFORE sol_storage!
- Add internal helper functions (without #[public])
- Define external contract interfaces with sol_interface!

IMPORTS - USE THESE PATTERNS:
- Types from stylus_sdk::alloy_primitives::{Address, U256, U8, ...}
- sol! macro: \`use alloy_sol_types::sol;\`
- Events: self.vm().log(EventName { field1, field2 })
- Caller: self.vm().msg_sender()
- ETH transfers: \`use stylus_sdk::call::transfer::transfer_eth;\` then \`transfer_eth(self.vm(), to, amount)?;\`
- Errors: return Err(ErrorName { ... }.abi_encode()) — requires use alloy_sol_types::SolError;
- Cross-contract: sol_interface! { interface IFoo { ... } }
- VIEW calls: ifoo.bar(self.vm(), Call::new(), args)?
- STATE calls: let call = Call::new_mutating(self); ifoo.bar(self.vm(), call, args)?

REFERENCE CODE — copy these EXACTLY when needed:
${STYLUS_REFERENCE_CODE}

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
- stylus-sdk: ${mainVersion} (latest stable)
- alloy-primitives: ${alloyVersion}
- alloy-sol-types: ${alloyVersion}
- Rust version: 1.91.0 (via rust-toolchain.toml)

SDK 0.10.0 changes:
- msg::sender() → self.vm().msg_sender()
- msg::value() → self.vm().msg_value()
- evm::log() → self.vm().log()
- stylus_sdk::evm is removed — use self.vm() methods
- transfer_eth: use stylus_sdk::call::transfer::transfer_eth; then transfer_eth(self.vm(), to, amount)?
- Error types: sol! { error MyError(...); } + #[derive(SolidityError)] + use alloy_sol_types::SolError
- Nested mapping writes: chain .setter() calls: self.map.setter(k1).setter(k2).set(v)
- Stylus.toml, rust-toolchain.toml (channel 1.91.0), src/main.rs all required
- print_from_args() for ABI export (NOT print_abi())
- Package name uses underscores, crate-type = ["lib", "cdylib"]
- ALWAYS use alloc::{vec, vec::Vec};
- RawCall::new_with_value(self.vm(), amount) — needs self.vm() + unsafe

When asked about versions, ALWAYS use the version info above, NOT from retrieved context.

REFERENCE CODE — use these EXACT patterns:
${STYLUS_REFERENCE_CODE}`,
    },
    {
      role: "user",
      content: `Context from documentation:\n${context}\n\n---\n\nQuestion: ${question}`,
    },
  ];

  return chatCompletion(apiKey, messages, {
    model: MODELS.QA,
    temperature: 0.3,
    maxTokens: 6000,
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
    maxTokens: 6000,
  });
}

/**
 * Answer questions about Arbitrum Orbit chain deployment and management.
 */
export async function answerOrbitQuestion(
  apiKey: string,
  question: string,
  context: string
): Promise<ChatCompletionResponse> {
  const messages: Message[] = [
    {
      role: "system",
      content: `You are an expert on Arbitrum Orbit chain deployment and management.
Answer questions about:
- Chain configuration using prepareChainConfig() from @arbitrum/orbit-sdk
- Rollup deployment using createRollup() — validators, batch posters, native tokens
- Token bridge deployment using createTokenBridge()
- AnyTrust DAC configuration — keysets, data availability committees
- Custom gas token chains — ERC20 native token setup and approval flow
- Nitro node setup using prepareNodeConfig()
- Governance via UpgradeExecutor — EXECUTOR_ROLE, ADMIN_ROLE, contract upgrades
- Validator and batch poster management

Use the provided context from the Orbit SDK documentation and code examples.
Include TypeScript code examples using viem and @arbitrum/orbit-sdk when relevant.
Be accurate about:
- Deployment order: config → createRollup → start node → createTokenBridge
- AnyTrust vs Rollup trade-offs (cost vs security assumptions)
- Custom gas token requires ERC20 approval before createRollup()
- UpgradeExecutor is the admin proxy for all chain contracts
Reference the correct SDK functions: prepareChainConfig, createRollup, createTokenBridge, prepareNodeConfig.`,
    },
    {
      role: "user",
      content: `Context from Orbit SDK documentation:\n${context}\n\n---\n\nQuestion: ${question}`,
    },
  ];

  return chatCompletion(apiKey, messages, {
    model: MODELS.QA,
    temperature: 0.3,
    maxTokens: 6000,
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
      content: `You are a Stylus testing expert for SDK 0.10.0.
Generate comprehensive tests for the provided contract.
Framework: ${testFramework === "rust_native" ? "Rust native #[test] with stylus-test" : "Foundry Solidity tests"}

For Rust native tests (stylus-sdk 0.10.0):
- Use #[cfg(test)] module with \`use super::*;\` and \`use stylus_sdk::testing::*;\`
- SETUP: \`let vm = TestVM::default(); let mut contract = MyContract::from(&vm);\`
  Do NOT use MyContract::default() — it does not exist in SDK 0.10.0
- Use vm.set_sender(addr) to set msg.sender for tests
- Use vm.set_value(amount) to set msg.value for payable tests
- Use vm.set_block_timestamp(ts) to set block.timestamp
- Test all public functions with happy path, error cases, and edge cases
- Use assert!, assert_eq!, assert_ne! with descriptive messages
- EVENT CHECKING: Use \`vm.get_emitted_logs()\` to check events. Do NOT use \`vm.logs()\` — it does not exist. Return type is \`Vec<(Vec<B256>, Vec<u8>)>\`. Do NOT use a \`Log\` type — it doesn't exist in stylus-test.
- ZERO CONSTANTS: Use \`U256::ZERO\`, \`Address::ZERO\` (uppercase). Do NOT use \`U256::zero()\` or \`Address::zero()\`.
- STORAGE ACCESS: ALWAYS use \`.get()\` to read storage, \`.set()\` to write, \`.setter(key).set(val)\` for mappings
- Cargo.toml needs: [dev-dependencies] stylus-sdk = { version = "0.10.0", features = ["stylus-test"] }
- IMPORTANT: Run tests with \`--target\` flag (tests run on host, not WASM):
  \`cargo test --target=x86_64-unknown-linux-gnu\` (Linux) or \`cargo test --target=aarch64-apple-darwin\` (macOS)
  Do NOT run \`cargo test\` without \`--target\` — it compiles for wasm32-unknown-unknown which cannot run unit tests
- If you get alloy-consensus or alloy-* version conflicts, pin alloy crate versions in workspace Cargo.toml

For Foundry tests:
- Create Solidity interface matching the contract ABI (use camelCase function names)
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
    maxTokens: 8192,
  });
}

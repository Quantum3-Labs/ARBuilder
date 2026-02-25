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

// Default models
export const MODELS = {
  CODE_GEN: "openai/gpt-oss-120b",
  QA: "openai/gpt-oss-120b",
  FAST: "openai/gpt-oss-120b",
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
      "HTTP-Referer": "https://arbuilder.app",
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
- STORAGE ACCESS: ALWAYS use .get() to read: \`self.field.get()\` NOT \`self.field\`. Use .set() to write. For mappings: \`self.map.get(key)\` and \`self.map.setter(key).set(val)\`.
- Handle errors with ${errorHandling}
- Follow Rust naming conventions (snake_case for functions, PascalCase for types)
- TRANSFER ETH: \`use stylus_sdk::call::transfer::transfer_eth;\` then \`transfer_eth(self.vm(), to, amount)?;\` — NOT self.transfer_eth() or call::transfer_eth()
- For error types: define with sol! { error MyError(...); }, wrap in enum with #[derive(SolidityError)]
- For .abi_encode() on errors: import SolError via use alloy_sol_types::SolError
- Nested mapping writes: chain in one expression: self.map.setter(k1).setter(k2).set(v). Do NOT split into separate variables (causes multiple active borrows)
- Do NOT use stylus_sdk::evm (removed in 0.10.0) or stylus_sdk::msg
- ALWAYS include \`use alloc::{vec, vec::Vec};\` — sol_storage! needs vec module in scope
- RawCall::new_with_value(self.vm(), amount) — requires self.vm() as first arg and unsafe block
- uint8 in sol_storage! maps to Uint<8,1> not native u8 — prefer uint256
- Package name in Cargo.toml MUST use underscores (e.g., "my_contract") — hyphens break cargo-stylus
- src/main.rs is REQUIRED — use print_from_args() (NOT print_abi()) for ABI export
- crate-type in [lib] must be ["lib", "cdylib"]
- EXTERNAL INTERFACES: use \`sol_interface!\` (NOT \`sol!\`) for external contract interfaces. VIEW calls: \`ifoo.method(self.vm(), Call::new(), args)?\`. STATE-MODIFYING calls: extract Call first: \`let call = Call::new_mutating(self);\` then \`ifoo.method(self.vm(), call, args)?\` — avoids borrow conflict.
- Stylus exports snake_case Rust fn names as camelCase in the ABI (create_market → createMarket). Frontend must use camelCase in functionName.
- Stylus &self view functions CANNOT make external contract calls (they revert). Use &mut self or read from frontend.
- DYNAMIC ARRAYS: In sol_storage!, declare as \`uint256[] items;\`. Append primitives with \`self.items.push(val)\`. For struct arrays, use \`self.items.grow()\` then set fields. Do NOT use \`.setter(len).unwrap()\`.
- sol! MACRO IMPORT: When using sol! for events/errors, you MUST import it: \`use alloy_sol_types::{sol, SolError};\` — sol! is NOT in prelude.
- BORROW CHECKER: Extract values to local vars before combining storage reads/writes. Never \`self.field.setter(self.vm().something())\`.
- sol! EVENT/ERROR FIELDS: Use camelCase (Solidity convention): \`tokenId\` NOT \`token_id\`.
- On Arbitrum Sepolia, MetaMask may underestimate maxFeePerGas — add explicit gas overrides if "max fee per gas less than block base fee"
- CONTRACT ADDRESS: Use \`self.vm().contract_address()\` — NOT \`self.vm().address()\` which does not exist
- ZERO CONSTANTS: Use \`U256::ZERO\`, \`Address::ZERO\` (uppercase const) — NOT \`U256::zero()\` or \`Address::zero()\` which do not exist
- BLOCK TIMESTAMP: \`self.vm().block_timestamp()\` returns \`u64\`. Wrap with \`U256::from()\` before storing in uint256 fields
- StorageString: Use \`.set_str("value")\` and \`.get_string()\` — NOT \`.set()\` or \`.get()\` on string storage fields
- NO STD: Do NOT use \`std::time\`, \`std::collections\`, or any std library. For timestamps: \`self.vm().block_timestamp()\`
- EVENT/ERROR NAMING: Never give an event and error the same name — they generate conflicting Rust structs. Use distinct names like \`event Paused(address)\` + \`error ContractPaused()\`
- RESULT PROPAGATION: Always use \`?\` when calling helper methods that return Result: \`self.check()?\` not \`self.check()\`
- Call IMPORT: \`Call\` is available from \`prelude::*\` — do NOT add \`use stylus_sdk::call::Call;\` separately
- DUPLICATE DEFINITIONS: Put all errors in one \`sol! {}\` block. Never define the same error/event name twice

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
6. When using sol! for events or errors, you MUST explicitly import it: \`use alloy_sol_types::{sol, SolError};\` — sol! is NOT available from prelude. If only using events (no .abi_encode()), \`use alloy_sol_types::sol;\` is sufficient.
7. If adding events/errors with sol! macro, they must be BEFORE sol_storage!
8. KEEP the Cargo.toml [profile.release] section exactly as provided

COMPILATION-CRITICAL — these mistakes WILL break the build:
- STORAGE ACCESS: ALWAYS use .get() to read storage: \`self.field.get()\` NOT \`self.field\`. ALWAYS use .set(val) to write: \`self.field.set(val)\`. For mappings: read with \`self.map.get(key)\`, write with \`self.map.setter(key).set(val)\`.
- TRANSFER ETH: \`use stylus_sdk::call::transfer::transfer_eth;\` then \`transfer_eth(self.vm(), to, amount)?;\`. Do NOT use \`self.transfer_eth()\`, \`call::transfer_eth()\`, or any other path.
- EXTERNAL INTERFACES: use \`sol_interface!\` macro (NOT \`sol!\`). \`sol!\` is ONLY for events and errors.
- CROSS-CONTRACT CALLS: VIEW calls: \`ifoo.method(self.vm(), Call::new(), args)?\`. STATE-MODIFYING calls: extract Call first: \`let call = Call::new_mutating(self);\` then \`ifoo.method(self.vm(), call, args)?\` — avoids borrow conflict.
- External calls require \`&mut self\` (NOT \`&self\` — view functions revert on external calls)
- DYNAMIC ARRAYS: In sol_storage!, declare as \`uint256[] items;\`. Append with \`self.items.push(val)\` for primitives, \`self.items.grow()\` for structs. Do NOT use \`.setter(len).unwrap()\`.
- BORROW CHECKER: Extract values to local vars before combining storage reads and writes.
- sol! EVENT/ERROR FIELDS: Use camelCase (Solidity convention): \`tokenId\` NOT \`token_id\`.
- CONTRACT ADDRESS: \`self.vm().contract_address()\` NOT \`self.vm().address()\` (does not exist).
- ZERO CONSTANTS: \`U256::ZERO\`, \`Address::ZERO\` (uppercase const). NOT \`U256::zero()\` (does not exist).
- BLOCK TIMESTAMP: \`self.vm().block_timestamp()\` returns \`u64\`. Wrap with \`U256::from()\` before storing in uint256 fields.
- StorageString: \`.set_str("val")\` and \`.get_string()\`. NOT \`.set()\` or \`.get()\`.
- NO STD: Do NOT use \`std::time\`, \`std::collections\`. For timestamps: \`self.vm().block_timestamp()\`.
- EVENT/ERROR NAMING: Never give an event and error the same name — they generate conflicting Rust structs. Use \`event Paused(address)\` and \`error ContractPaused()\`.
- RESULT PROPAGATION: Always use \`?\` to propagate Result from helper methods.
- Call IMPORT: \`Call\` comes from \`prelude::*\`. Do NOT add \`use stylus_sdk::call::Call;\` separately.
- DUPLICATE DEFINITIONS: Put all errors in one \`sol! {}\` block. Never define the same name twice.

WHAT YOU MAY DO:
- Rename the contract struct in sol_storage! to match the user's request (e.g., PredictionMarket, Lottery, etc.)
- Add/modify storage fields inside sol_storage!
- Add/modify functions inside the #[public] impl block
- Add events using sol! { event EventName(...); } BEFORE sol_storage!
- Add error types using sol! { error ErrorName(...); } BEFORE sol_storage!
- Add internal helper functions (without #[public])
- Define external contract interfaces with sol_interface! (NOT sol!) for cross-contract calls

IMPORTS - USE THESE PATTERNS:
- Types from stylus_sdk::alloy_primitives::{Address, U256, U8, ...}
- sol! macro: \`use alloy_sol_types::sol;\` (NOT from prelude)
- For events: self.vm().log(EventName { field1, field2 }) (NOT evm::log)
- For caller: self.vm().msg_sender() (NOT msg::sender())
- For ETH transfers: \`use stylus_sdk::call::transfer::transfer_eth;\` then \`transfer_eth(self.vm(), to, amount)?;\`
- For errors: return Err(ErrorName { ... }.abi_encode()) — requires use alloy_sol_types::SolError;
- For cross-contract calls: define with sol_interface! { interface IFoo { function bar(address) external returns (uint256); } }
- VIEW calls: \`ifoo.bar(self.vm(), Call::new(), addr)?\`
- STATE-MODIFYING calls: \`let call = Call::new_mutating(self); ifoo.bar(self.vm(), call, args)?\`
- External calls require &mut self (NOT &self — view functions revert on external calls)
- Do NOT use stylus_sdk::evm (removed in 0.10.0) or stylus_sdk::msg

REFERENCE CODE — copy these EXACTLY when the user's request needs them:

ETH transfer (withdraw/deposit/send ETH):
\`\`\`rust
use stylus_sdk::call::transfer::transfer_eth;

pub fn withdraw(&mut self, to: Address, amount: U256) -> Result<(), Vec<u8>> {
    transfer_eth(self.vm(), to, amount)?;
    Ok(())
}
\`\`\`

Cross-contract VIEW call (read-only — Call::new() is fine):
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

Cross-contract state-modifying call (extract Call to avoid borrow conflict):
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

Dynamic array (append to sol_storage! array):
\`\`\`rust
// In sol_storage!: uint256[] items;
// Append primitive:
self.items.push(new_val);
// For structs: let mut entry = self.items.grow(); entry.field.set(val);
\`\`\`

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
- Rust version: 1.91.0 (via rust-toolchain.toml)

IMPORTANT SDK 0.10.0 changes:
- msg::sender() is replaced by self.vm().msg_sender()
- msg::value() is replaced by self.vm().msg_value()
- evm::log() is replaced by self.vm().log()
- use stylus_sdk::evm is removed entirely — use self.vm() methods
- transfer_eth: use stylus_sdk::call::transfer::transfer_eth; then call transfer_eth(self.vm(), to, amount)?
- Error types: define with sol! { error MyError(...); }, wrap enum with #[derive(SolidityError)]
- For .abi_encode() on errors: import use alloy_sol_types::SolError;
- Nested mapping writes: chain in one expression: self.map.setter(k1).setter(k2).set(v). Do NOT split into separate variables (causes multiple active borrows)
- Projects MUST include Stylus.toml with [workspace], [workspace.networks], and [contract] sections
- Projects MUST include rust-toolchain.toml with channel = "1.91.0"
- Projects MUST include src/main.rs — cargo stylus deploy uses cargo run to check constructors
- ABI export function in 0.10.0 is print_from_args() (NOT print_abi())
- Package name MUST use underscores (e.g., "my_contract") — hyphens break cargo-stylus WASM lookup
- crate-type must be ["lib", "cdylib"] — "lib" needed for bin target linking
- ALWAYS include use alloc::{vec, vec::Vec}; — sol_storage! needs vec module
- RawCall::new_with_value(self.vm(), amount) — needs self.vm() as first arg and unsafe block
- uint8 in sol_storage! maps to Uint<8,1>, not u8 — comparisons with u8 won't compile

When asked about versions, ALWAYS use the version info above, NOT from retrieved context which may be outdated.

REFERENCE CODE — use these EXACT patterns in your code examples:

ETH transfer (withdraw/deposit/send ETH):
\`\`\`rust
use stylus_sdk::call::transfer::transfer_eth;

pub fn withdraw(&mut self, to: Address, amount: U256) -> Result<(), Vec<u8>> {
    transfer_eth(self.vm(), to, amount)?;
    Ok(())
}
\`\`\`

Cross-contract call (interact with another deployed contract):
\`\`\`rust
sol_interface! {
    interface IToken {
        function balanceOf(address account) external view returns (uint256);
        function transfer(address to, uint256 amount) external returns (bool);
    }
}

// In a #[public] &mut self method:
pub fn get_balance(&mut self, token: Address, account: Address) -> Result<U256, Vec<u8>> {
    let token_contract = IToken::new(token);
    let balance = token_contract.balance_of(self.vm(), Call::new(), account)?;
    Ok(balance)
}
\`\`\`

Storage access:
\`\`\`rust
// Read: ALWAYS use .get()
let val = self.my_field.get();
let balance = self.balances.get(user);

// Write: use .set() or .setter().set()
self.my_field.set(new_val);
self.balances.setter(user).set(new_balance);
\`\`\`

Nested mapping (e.g. mapping(address => mapping(address => uint256))):
\`\`\`rust
// In sol_storage! — use Solidity syntax, NOT Rust types:
//   mapping(address => mapping(address => uint256)) allowances;

// Read nested: chain .get() calls
let allowance = self.allowances.get(owner).get(spender);

// Write nested: chain .setter() calls in ONE expression
self.allowances.setter(owner).setter(spender).set(value);
\`\`\`

Dynamic arrays (sol_storage! uses Solidity syntax: uint256[], address[]):
\`\`\`rust
// In sol_storage! — use Solidity syntax, NOT StorageVec<T>:
//   uint256[] values;

// Read: .get(index), .len() (returns usize)
// Append primitive value — use push():
self.values.push(new_val);

// For struct arrays — use grow() then set fields:
let mut item = self.items.grow();
item.field_a.set(val_a);
\`\`\``,
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
  });
}

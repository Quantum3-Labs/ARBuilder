/**
 * Generate Stylus Code Tool
 *
 * Generates Stylus smart contract code based on natural language
 * descriptions, using verified working templates as the foundation.
 *
 * Key improvement: Uses curated templates from official examples instead
 * of generating from scratch, ensuring the output compiles correctly.
 *
 * Supports version-aware code generation for different stylus-sdk versions.
 */

import { generateCodeFromTemplate } from "../openrouter";
import { getStylusContext } from "./getStylusContext";
import {
  getMainVersion,
  getAlloyPrimitivesVersion,
  getAlloySolTypesVersion,
  detectVersionFromCargoToml,
  isVersionDeprecated,
  getDeprecationWarning,
} from "../stylusVersions";
import { selectTemplate, StylusTemplate } from "../templates/stylusTemplates";

/**
 * Validate and fix common LLM mistakes in generated code.
 * Mirrors the Python _fix_code() safety nets in generate_stylus_code.py.
 */
function validateAndFixCode(code: string, template: StylusTemplate): string {
  let fixed = code;

  // Fix 1: Remove empty sol_storage! blocks
  fixed = fixed.replace(/sol_storage!\s*\{\s*\}/g, "");

  // Fix 2: Ensure proper cfg_attr if missing
  if (!fixed.includes('#![cfg_attr(not(any(test')) {
    const templateStart = template.libRs.split("extern crate alloc")[0];
    if (!fixed.startsWith("#![cfg_attr")) {
      fixed = templateStart + fixed;
    } else {
      // Replace wrong cfg_attr patterns with correct ones
      fixed = fixed.replace(
        /#!\[cfg_attr\(not\(any\(feature\s*=\s*"export-abi",\s*test\)\),\s*no_std\)\]/g,
        '#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]'
      );
      fixed = fixed.replace(
        /#!\[cfg_attr\(not\(test\),\s*no_main\)\]/g,
        '#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]'
      );
    }
  }

  // Fix 3: Ensure extern crate alloc if missing
  if (!fixed.includes("extern crate alloc")) {
    fixed = fixed.replace(
      /^(#!\[cfg_attr.*\n)+/m,
      "$&#[macro_use]\nextern crate alloc;\n\n"
    );
  }

  // Fix 4: REMOVED — sol! is NOT in prelude, the explicit import is correct.
  // Previously this removed `use alloy_sol_types::sol;` which broke sol! events/errors.

  // Fix 5: Handle Vec imports - avoid duplicates
  if (fixed.includes("use alloc::vec::Vec;") && fixed.includes("use alloc::{") && fixed.includes("vec::Vec")) {
    fixed = fixed.replace(/use alloc::vec::Vec;\n?/g, "");
  }
  if (fixed.includes("Vec<u8>") && !fixed.includes("alloc::vec::Vec") && !fixed.includes("alloc::{")) {
    fixed = fixed.replace(
      /(extern crate alloc;)/,
      "$1\n\nuse alloc::vec::Vec;"
    );
  }

  // Fix 6: Ensure use alloc::vec; is present (sol_storage! needs vec module)
  if (!fixed.includes("use alloc::vec;") && !fixed.includes("use alloc::{")) {
    fixed = fixed.replace(
      /(extern crate alloc;\s*\n)/,
      "$1\nuse alloc::{vec, vec::Vec};\n"
    );
  } else if (fixed.includes("use alloc::vec::Vec;") && !fixed.includes("use alloc::vec;") && !fixed.includes("alloc::{")) {
    // Has Vec but not vec module — replace with combined import
    fixed = fixed.replace(
      "use alloc::vec::Vec;",
      "use alloc::{vec, vec::Vec};"
    );
  }

  // Fix 7: Ensure there's exactly one sol_storage! block with #[entrypoint]
  const solStorageCount = (fixed.match(/sol_storage!\s*\{/g) || []).length;
  if (solStorageCount === 0) {
    return template.libRs;
  }

  // Fix 8: Ensure #[entrypoint] is inside sol_storage! if missing
  if (!fixed.includes("#[entrypoint]")) {
    fixed = fixed.replace(
      /sol_storage!\s*\{\s*(\n?\s*pub struct)/,
      "sol_storage! {\n    #[entrypoint]$1"
    );
  }

  // Fix 9: Convert sol! { interface ... } to sol_interface! { interface ... }
  // LLMs often use sol! for interfaces, but Stylus requires sol_interface!
  fixed = fixed.replace(
    /sol!\s*\{\s*(interface\b)/g,
    "sol_interface! { $1"
  );

  // Fix 9b: Convert Rust Storage* types to Solidity types in sol_storage!
  // LLMs sometimes use Rust types instead of Solidity types
  fixed = fixed.replace(/StorageString/g, "string");
  fixed = fixed.replace(/StorageAddress/g, "address");
  fixed = fixed.replace(/StorageU256/g, "uint256");
  fixed = fixed.replace(/StorageU128/g, "uint128");
  fixed = fixed.replace(/StorageU64/g, "uint64");
  fixed = fixed.replace(/StorageU8/g, "uint8");
  fixed = fixed.replace(/StorageBool/g, "bool");
  fixed = fixed.replace(
    /StorageMap<Storage(\w+),\s*Storage(\w+)>/g,
    (_m, k: string, v: string) => `mapping(${k.toLowerCase()} => ${v.toLowerCase()})`
  );
  fixed = fixed.replace(
    /StorageVec<Storage(\w+)>/g,
    (_m, t: string) => `${t.toLowerCase()}[]`
  );

  // Fix 9c: Remove incorrect stylus_sdk::storage imports
  fixed = fixed.replace(
    /^use stylus_sdk::storage(?:::(?:StorageString|StorageMap|StorageVec|StorageU\d+|StorageBool|StorageAddress))?;\s*$/gm,
    ""
  );

  // Fix 9d: Add `use alloc::string::String;` if String is used but not imported
  if ((fixed.includes("-> String") || fixed.includes(": String")) &&
      !fixed.includes("alloc::string::String") && !fixed.includes("alloc::string::")) {
    fixed = fixed.replace(
      /(use alloc::\{vec, vec::Vec\};)/,
      "$1\nuse alloc::string::String;"
    );
  }

  // Fix 10: Fix wrong transfer_eth import paths
  // Wrong: use stylus_sdk::call::transfer_eth;
  // Correct: use stylus_sdk::call::transfer::transfer_eth;
  fixed = fixed.replace(
    /use stylus_sdk::call::transfer_eth;/g,
    "use stylus_sdk::call::transfer::transfer_eth;"
  );
  // Wrong: use stylus_sdk::call::{transfer_eth, ...};
  // Split into separate imports
  fixed = fixed.replace(
    /use stylus_sdk::call::\{([^}]*)\btransfer_eth\b([^}]*)\};/g,
    (_match, before: string, after: string) => {
      const others = (before.replace("transfer_eth", "").trim().replace(/^,|,$/g, "").trim()
        + ", " + after.trim().replace(/^,|,$/g, "").trim()).replace(/^,\s*|,\s*$/g, "").trim();
      const transferLine = "use stylus_sdk::call::transfer::transfer_eth;";
      if (others) {
        return `${transferLine}\nuse stylus_sdk::call::{${others}};`;
      }
      return transferLine;
    }
  );

  // Fix 11: self.transfer_eth(to, amount) → transfer_eth(self.vm(), to, amount)
  fixed = fixed.replace(
    /self\.transfer_eth\(([^)]+)\)/g,
    "transfer_eth(self.vm(), $1)"
  );

  // Fix 12: transfer_eth(self, ...) → transfer_eth(self.vm(), ...)
  // LLMs write self instead of self.vm() — must be the vm Host context
  fixed = fixed.replace(
    /transfer_eth\(self,\s*/g,
    "transfer_eth(self.vm(), "
  );

  // Fix 16: Enforce .get() on bare storage field reads
  // Extract field names from sol_storage! block
  const storageFields = new Set<string>();
  // Match Solidity-type field declarations: type field_name;
  const typeFieldPattern = /\b(?:uint\d*|int\d*|address|bool|string|bytes\d*)\s+(\w+)\s*;/g;
  let fieldMatch;
  while ((fieldMatch = typeFieldPattern.exec(fixed)) !== null) {
    storageFields.add(fieldMatch[1]);
  }
  // Match mapping fields: mapping(...) field_name;
  const mappingFieldPattern = /mapping\([^)]*\)\s+(\w+)\s*;/g;
  while ((fieldMatch = mappingFieldPattern.exec(fixed)) !== null) {
    storageFields.add(fieldMatch[1]);
  }
  // For each storage field, fix bare <var>.<field> reads (not followed by . or ()
  // This catches both self.<field> AND nested struct fields like market.<field>
  // where market = self.markets.get(id) returns a storage accessor
  // Use \b word boundary to prevent matching field prefixes (e.g., "owner" matching "owners")
  for (const field of storageFields) {
    const bareFieldPattern = new RegExp(`(\\w+)\\.${field}\\b(?!\\s*[.(])`, "g");
    fixed = fixed.replace(bareFieldPattern, `$1.${field}.get()`);
  }

  // Fix 17: self.vm().address() → self.vm().contract_address()
  fixed = fixed.replace(/self\.vm\(\)\.address\(\)/g, "self.vm().contract_address()");

  // Fix 18: U256::zero() / U128::zero() → U256::ZERO / U128::ZERO
  fixed = fixed.replace(/U256::zero\(\)/g, "U256::ZERO");
  fixed = fixed.replace(/U128::zero\(\)/g, "U128::ZERO");
  fixed = fixed.replace(/U64::zero\(\)/g, "U64::ZERO");

  // Fix 19: StorageString - .set() → .set_str(), .get() → .get_string()
  const stringFields = new Set<string>();
  const stringFieldPattern = /\bstring\s+(\w+)\s*;/g;
  let stringFieldMatch;
  while ((stringFieldMatch = stringFieldPattern.exec(fixed)) !== null) {
    stringFields.add(stringFieldMatch[1]);
  }
  for (const sf of stringFields) {
    fixed = fixed.replace(new RegExp(`\\.${sf}\\.set\\(`, "g"), `.${sf}.set_str(`);
    fixed = fixed.replace(new RegExp(`\\.${sf}\\.get\\(\\)`, "g"), `.${sf}.get_string()`);
  }

  // Fix 20: std::time::SystemTime — not available in no_std WASM
  fixed = fixed.replace(/^use std::time.*;\s*$/gm, "");
  fixed = fixed.replace(
    /std::time::SystemTime::now\(\)[^;]*/g,
    "self.vm().block_timestamp()"
  );

  // Fix 21: Remove incorrect `use stylus_sdk::call::Call;` import
  // Call is available from prelude::* — no separate import needed
  fixed = fixed.replace(/^use stylus_sdk::call::Call;\s*$/gm, "");

  // Fix 22: StorageVec .setter(i).set(v) → .setter(i).unwrap().set(v)
  // StorageVec::setter(usize) returns Option, needs unwrap.
  // BUT mapping .setter(key) does NOT return Option — no unwrap needed.
  // Only add .unwrap() on dynamic array fields (type[] in sol_storage!).
  const arrayFields = new Set<string>();
  const arrayFieldPattern = /\b\w+\[\]\s+(\w+)\s*;/g;
  let arrayFieldMatch;
  while ((arrayFieldMatch = arrayFieldPattern.exec(fixed)) !== null) {
    arrayFields.add(arrayFieldMatch[1]);
  }
  for (const af of arrayFields) {
    // Use balanced-paren pattern to handle nested parens
    // e.g. setter(U256::from(idx as u64))
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

  // Fix 24: .unwrap_or_else(VALUE) → .unwrap_or(VALUE)
  // unwrap_or_else takes a closure, not a value.
  fixed = fixed.replace(
    /\.unwrap_or_else\((\w+::(?:ZERO|MAX|MIN|ONE))\)/g,
    ".unwrap_or($1)"
  );

  // Fix 25: self.vm().log(...)? → self.vm().log(...)
  // vm().log() returns (), not Result — cannot use ? operator
  fixed = fixed.replace(
    /(self\.vm\(\)\.log\([^;]*\))\?/g,
    "$1"
  );

  // Fix 26: .as_usize() → .to::<usize>()
  // U256 does not have as_usize(). Use Uint::to() method.
  fixed = fixed.replace(
    /\.as_usize\(\)/g,
    ".to::<usize>()"
  );

  // Fix 13: Remove deprecated stylus_sdk::evm and stylus_sdk::msg imports
  fixed = fixed.replace(/^use stylus_sdk::evm.*;\s*$/gm, "");
  fixed = fixed.replace(/^use stylus_sdk::msg.*;\s*$/gm, "");

  // Fix 14: Fix deprecated msg::sender() → self.vm().msg_sender()
  fixed = fixed.replace(/msg::sender\(\)/g, "self.vm().msg_sender()");
  fixed = fixed.replace(/msg::value\(\)/g, "self.vm().msg_value()");

  // Fix 15: Fix deprecated evm::log(...) → self.vm().log(...)
  fixed = fixed.replace(/evm::log\(/g, "self.vm().log(");

  return fixed;
}

/**
 * Derive a snake_case project name from the user prompt.
 * Mirrors Python _derive_project_name() in generate_stylus_code.py.
 */
function deriveProjectName(prompt: string): string {
  const stopWords = new Set([
    "a", "an", "the", "for", "with", "and", "or", "that", "this",
    "create", "build", "make", "generate", "implement",
  ]);
  const words = (prompt.match(/[a-zA-Z]+/g) || [])
    .map((w) => w.toLowerCase())
    .filter((w) => !stopWords.has(w));
  const nameWords = words.length > 0 ? words.slice(0, 3) : ["stylus", "contract"];
  return nameWords.join("_");
}

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

export const TEMPLATE_DISCLAIMER =
  "This generated code is a starting entrypoint — a working foundation for you to build upon. " +
  "Review, customize, and extend it to match your specific requirements before deploying.";

export interface GenerateStylusCodeOutput {
  code: string;
  cargoToml: string;
  mainRs: string; // For ABI export: cargo run --features export-abi
  explanation: string;
  dependencies: string[];
  warnings: string[];
  contextUsed: string[];
  tokensUsed: number;
  /** The stylus-sdk version used for code generation. */
  targetVersion: string;
  /** The base template that was used. */
  templateUsed: string;
  disclaimer: string;
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

  // Select the best template based on contract type and prompt
  const template = selectTemplate(contractType, prompt);

  // Get relevant context from knowledge base for additional patterns
  const searchQuery = contextQuery || `${contractType} contract ${prompt}`;
  const contextResult = await getStylusContext(vectorize, ai, {
    query: searchQuery,
    nResults: 3, // Reduced since we have a template as base
    rerank: true,
    targetVersion,
  });

  // Build context string (for additional patterns only)
  const contextStr = contextResult.contexts
    .map((c, i) => `[${i + 1}] (${c.source})\n${c.content}`)
    .join("\n\n---\n\n");

  // Enhance prompt with test request if needed
  let enhancedPrompt = prompt;
  if (includeTests) {
    enhancedPrompt +=
      "\n\nKeep the #[cfg(test)] module and update the tests to match the new functionality.";
  } else {
    enhancedPrompt += "\n\nYou may remove the #[cfg(test)] module if not needed.";
  }

  // Generate code using LLM with template as base
  const response = await generateCodeFromTemplate(
    openrouterApiKey,
    enhancedPrompt,
    template,
    contextStr,
    targetVersion
  );

  // Parse response - extract code blocks and explanation
  const codeMatch = response.content.match(/```rust\n([\s\S]*?)```/);
  let code = codeMatch ? codeMatch[1].trim() : response.content;

  // Safety net: if LLM returned empty content, fall back to template
  if (!code || code.trim().length === 0) {
    code = template.libRs;
    warnings.push("LLM returned empty content — using template code as fallback");
  }

  // ALWAYS use template's Cargo.toml - don't trust LLM-generated Cargo.toml
  // LLM often makes typos (alloy-sol_types) or misses deps (ruint)
  let generatedCargo = template.cargoToml;
  let mainRs = template.mainRs;

  // Derive project name from prompt and fix Cargo.toml/main.rs references
  const projectName = deriveProjectName(prompt);
  generatedCargo = generatedCargo.replace(
    /name\s*=\s*"[^"]+"/g,
    `name = "${projectName}"`
  );
  mainRs = mainRs.replace(
    /(\w+)::print_from_args\b/,
    `${projectName}::print_from_args`
  );

  // Validate and fix common LLM mistakes in code
  code = validateAndFixCode(code, template);

  // Extract explanation (text before or after code blocks)
  const explanation = response.content
    .replace(/```(?:rust|toml)\n[\s\S]*?```/g, "")
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
    cargoToml: generatedCargo,
    mainRs,
    explanation: explanation || "Contract generated based on your requirements.",
    dependencies,
    warnings,
    contextUsed: contextResult.contexts.map((c) => c.source),
    tokensUsed: response.usage.totalTokens,
    targetVersion,
    templateUsed: template.name,
    disclaimer: TEMPLATE_DISCLAIMER,
  };
}

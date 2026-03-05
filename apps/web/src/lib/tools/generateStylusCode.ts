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
 *
 * CF Workers cannot run `cargo check` (no Docker), so ALL regex fixes stay
 * here as the only validation layer. The Python MCP server has a trimmed
 * set (16 deterministic fixes) because it uses cargo check for semantic
 * validation.
 *
 * Fix categories:
 *   STRUCTURAL (1-3, 5-8): Empty sol_storage!, cfg_attr, extern crate,
 *     Vec imports, alloc::vec, single sol_storage!, entrypoint placement
 *   BEHAVIORAL (9, 9b-9d, 29, 32): sol! → sol_interface!, Rust Storage*
 *     types → Solidity types, camelCase → snake_case, self.vm() host arg
 *   API MIGRATION (10-15, 17-18, 20-21): transfer_eth path, remove
 *     evm/msg modules, deprecated API replacements
 *   SEMANTIC (16, 19, 22, 27-28, 30-31, 33-36, 38): Storage .get()
 *     enforcement, StorageString API, StorageVec unwrap, nested mapping
 *     borrow, mapping unwrap_or_default, B256 conversion, const U256,
 *     string mapping reads, abi_encode on enum, StorageString bare access,
 *     pub const in impl — Python removes these (cargo check catches them)
 *   IMPORT MGMT (37/9d): alloc::string imports dedup + insertion
 *   CLEANUP (24-26, 39): unwrap_or_else, vm().log()?, as_usize, garbled output
 */
/**
 * Structurally sanitize the sol_storage! block.
 * Strips `= value` defaults, removes garbled lines, validates field syntax.
 * Falls back to template's sol_storage! if the block is unsalvageable.
 */
function sanitizeSolStorage(code: string, template: StylusTemplate): string {
  const blockMatch = code.match(/sol_storage!\s*\{/);
  if (!blockMatch || blockMatch.index === undefined) return code;

  const blockStart = blockMatch.index;
  const braceStart = code.indexOf("{", blockStart);

  // Find matching closing brace
  let depth = 0;
  let i = braceStart;
  while (i < code.length) {
    if (code[i] === "{") depth++;
    else if (code[i] === "}") {
      depth--;
      if (depth === 0) break;
    }
    i++;
  }

  if (depth !== 0) {
    // Unbalanced — fall back to template
    const tmplMatch = template.libRs.match(/sol_storage!\s*\{[\s\S]*?\n\}/);
    if (tmplMatch) return code.slice(0, blockStart) + tmplMatch[0] + code.slice(i + 1);
    return code;
  }

  const blockEnd = i + 1;
  const blockContent = code.slice(braceStart + 1, i);

  // Valid field type pattern
  const validTypeRe = /^\s*(?:(?:u?int(?:8|16|32|64|128|256))|address|bool|string|bytes\d*|mapping\(.*\)|[\w]+\[\])\s+\w+\s*;$/;

  // Find the inner struct
  const structMatch = blockContent.match(/pub\s+struct\s+\w+\s*\{/);
  if (!structMatch || structMatch.index === undefined) {
    const tmplMatch = template.libRs.match(/sol_storage!\s*\{[\s\S]*?\n\}/);
    if (tmplMatch) return code.slice(0, blockStart) + tmplMatch[0] + code.slice(blockEnd);
    return code;
  }

  const structBrace = blockContent.indexOf("{", structMatch.index);
  let sDepth = 0;
  let j = structBrace;
  while (j < blockContent.length) {
    if (blockContent[j] === "{") sDepth++;
    else if (blockContent[j] === "}") {
      sDepth--;
      if (sDepth === 0) break;
    }
    j++;
  }

  const structInner = blockContent.slice(structBrace + 1, j);
  const lines = structInner.split("\n");
  const cleanLines: string[] = [];
  let garbledCount = 0;
  let totalLines = 0;

  for (const line of lines) {
    const stripped = line.trim();
    if (!stripped) continue;
    totalLines++;

    // Allow comments
    if (stripped.startsWith("//")) {
      cleanLines.push(line);
      continue;
    }

    // Strip default value assignments: `uint256 x = 0;` → `uint256 x;`
    // Negative lookahead (?!>) avoids matching `=>` in mapping declarations
    let cleaned = stripped.replace(/(\w+)\s*=\s*(?!>)[^;]*;/, "$1;");

    // Remove pure garbage lines (only punctuation/numbers)
    if (/^[;=\s\[\]0-9,]+$/.test(cleaned)) {
      garbledCount++;
      continue;
    }

    // Validate it looks like a field declaration
    if (validTypeRe.test(cleaned)) {
      cleanLines.push(`        ${cleaned}`);
    } else if (/^\s*mapping\(/.test(cleaned)) {
      cleaned = cleaned.replace(/\s*=\s*(?!>)[^;]*;/, ";");
      if (cleaned.endsWith(";")) {
        cleanLines.push(`        ${cleaned}`);
      } else {
        garbledCount++;
      }
    } else {
      garbledCount++;
    }
  }

  // If more than half garbled, fall back to template
  if (totalLines > 0 && garbledCount > totalLines / 2) {
    const tmplMatch = template.libRs.match(/sol_storage!\s*\{[\s\S]*?\n\}/);
    if (tmplMatch) return code.slice(0, blockStart) + tmplMatch[0] + code.slice(blockEnd);
  }

  // Check for missing fields: scan code for self.xxx.get/set/setter
  // references and auto-declare any missing fields
  const declaredFields = new Set<string>();
  const dfPattern = /(?:uint\d+|int\d+|address|bool|string|bytes\d*|mapping\([^)]*\)|[\w]+\[\])\s+(\w+)\s*;/g;
  let dfMatch;
  const allClean = cleanLines.join("\n");
  while ((dfMatch = dfPattern.exec(allClean)) !== null) {
    declaredFields.add(dfMatch[1]);
  }
  const restOfCode = code.slice(blockEnd);
  const refPattern = /self\.(\w+)\s*\.(?:get|set|setter|getter|push|len|grow)\b/g;
  const referencedFields = new Set<string>();
  let refMatch;
  while ((refMatch = refPattern.exec(restOfCode)) !== null) {
    if (refMatch[1] !== "vm") referencedFields.add(refMatch[1]);
  }
  for (const field of [...referencedFields].sort()) {
    if (declaredFields.has(field)) continue;
    // Infer type from usage
    let fieldType = "uint256";
    if (new RegExp(`self\\.${field}\\.setter\\([^)]+\\)\\.setter\\(`).test(restOfCode)) {
      fieldType = "mapping(uint256 => mapping(address => bool))";
    } else if (new RegExp(`self\\.${field}\\.setter\\([^)]+\\)\\.set\\(`).test(restOfCode)) {
      fieldType = new RegExp(`self\\.${field}\\.(?:get|setter)\\([^)]*Address`).test(restOfCode)
        ? "mapping(address => uint256)" : "mapping(uint256 => uint256)";
    } else if (new RegExp(`self\\.${field}\\.push\\(`).test(restOfCode)) {
      fieldType = "uint256[]";
    } else if (new RegExp(`self\\.${field}\\.get_string\\(`).test(restOfCode)) {
      fieldType = "string";
    }
    cleanLines.push(`        ${fieldType} ${field};`);
  }

  // Reconstruct
  const preStruct = blockContent.slice(0, structBrace + 1);
  const postStruct = blockContent.slice(j);
  const newStructInner = "\n" + cleanLines.join("\n") + "\n    ";
  const newBlock = "sol_storage! {" + preStruct + newStructInner + postStruct + "\n}";
  return code.slice(0, blockStart) + newBlock + code.slice(blockEnd);
}

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

  // Fix 52: Sanitize sol_storage! block — structural validation.
  // Strips `= value` defaults, removes garbled lines, validates fields.
  fixed = sanitizeSolStorage(fixed, template);

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

  // Fix 9d + Fix 37 (N31): Ensure correct alloc::string imports.
  // Detect what's needed, remove ALL existing alloc::string imports, add one combined line.
  {
    const needsString = fixed.includes("-> String") || fixed.includes(": String") || fixed.includes(".to_string()") || fixed.includes("String::new") || fixed.includes("String::from");
    const needsToString = fixed.includes(".to_string()");
    if (needsString || needsToString) {
      // Remove all existing alloc::string imports to avoid duplicates
      fixed = fixed.replace(/^use alloc::string::\{[^}]*\};\s*\n?/gm, "");
      fixed = fixed.replace(/^use alloc::string::\w+;\s*\n?/gm, "");
      // Build combined import
      const parts: string[] = [];
      if (needsString) parts.push("String");
      if (needsToString) parts.push("ToString");
      if (parts.length > 0) {
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
  // Match mapping fields: mapping(...) field_name; (balanced parens for nested mappings)
  const mappingFieldPattern = /mapping\(((?:[^()]*|\([^()]*\))*)\)\s+(\w+)\s*;/g;
  while ((fieldMatch = mappingFieldPattern.exec(fixed)) !== null) {
    storageFields.add(fieldMatch[2]);
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
    // Allow optional whitespace/newlines between field name, .setter(), and .set()
    // for multiline chains like self.field\n    .setter(x)\n    .set(v).
    fixed = fixed.replace(
      new RegExp(`\\.${af}\\s*\\.setter\\(((?:[^()]*|\\([^()]*\\))*)\\)\\s*\\.set\\(`, "g"),
      `.${af}.setter($1).unwrap().set(`
    );
  }

  // Fix 27: .get/.getter(k1).setter(k2) → .setter(k1).setter(k2)
  // Nested mapping writes: .get()/.getter() return immutable ref, can't
  // call .setter() on it. Must chain .setter() for writes.
  fixed = fixed.replace(
    /\.get\(((?:[^()]*|\([^()]*\))*)\)\s*\.setter\(/g,
    ".setter($1).setter("
  );
  fixed = fixed.replace(
    /\.getter\(((?:[^()]*|\([^()]*\))*)\)\s*\.setter\(/g,
    ".setter($1).setter("
  );

  // Fix 45: .get(key).field.setter( → .setter(key).field.setter(
  // Nested struct writes: .get(key) on mapping returns immutable
  // StorageGuard, can't call .setter() on struct fields through it.
  // e.g. self.roles.get(role).members.setter(account).set(true)
  //   → self.roles.setter(role).members.setter(account).set(true)
  fixed = fixed.replace(
    /\.get\(((?:[^()]*|\([^()]*\))*)\)((?:\.\w+)+)\.setter\(/g,
    ".setter($1)$2.setter("
  );

  // Fix 46: .field.set(key, value) → .field.setter(key).set(value)
  // StorageMap has no .set(k,v) method — must use .setter(k).set(v).
  // Only matches two-arg .set() calls (single-arg is valid on StorageGuardMut).
  fixed = fixed.replace(
    /(\.\w+)\.set\(\s*((?:[^,()]*|\([^()]*\))*)\s*,\s*((?:[^,()]*|\([^()]*\))*)\s*\)/g,
    "$1.setter($2).set($3)"
  );

  // Fix 47: .get(key).getter(key) → .getter(key).get_string()
  // LLM generates double key access on mapping(... => string).
  // .get() returns StorageGuard, .getter() is the correct read accessor.
  fixed = fixed.replace(
    /\.get\(((?:[^()]*|\([^()]*\))*)\)\.getter\(((?:[^()]*|\([^()]*\))*)\)/g,
    ".getter($1).get_string()"
  );

  // Fix 48: B32 → B256 for bytes32
  // LLM sometimes generates B32 (non-existent) instead of B256.
  // bytes32 maps to FixedBytes<32> which is aliased as B256.
  fixed = fixed.replace(/\bB32\b/g, "B256");

  // Fix 23: REMOVED — corrupts sol! event/error declarations.

  // Fix 28: Remove spurious .unwrap_or_default() on mapping reads.
  // StorageMap::get() returns value directly (zero-default), NOT Option.
  // Use balanced-paren regex for nested mapping declarations like
  // mapping(address => mapping(address => uint256)) allowances;
  const mapFields28 = new Set<string>();
  const mapFieldPattern28 = /mapping\(((?:[^()]*|\([^()]*\))*)\)\s+(\w+)\s*;/g;
  let mapFieldMatch28;
  while ((mapFieldMatch28 = mapFieldPattern28.exec(fixed)) !== null) {
    mapFields28.add(mapFieldMatch28[2]);
  }
  for (const mf of mapFields28) {
    // Direct: .field.get(key).unwrap_or_default()
    fixed = fixed.replace(
      new RegExp(`\\.${mf}\\.get\\(([^)]*)\\)\\.unwrap_or_default\\(\\)`, "g"),
      `.${mf}.get($1)`
    );
    // Nested via .getter(): .field.getter(k1).get(k2).unwrap_or_default()
    fixed = fixed.replace(
      new RegExp(`\\.${mf}\\.getter\\(([^)]*)\\)\\.get\\(([^)]*)\\)\\.unwrap_or_default\\(\\)`, "g"),
      `.${mf}.getter($1).get($2)`
    );
  }

  // Fix 29: sol_interface! generates snake_case Rust methods from
  // Solidity camelCase function names. Only apply when followed by
  // (self.vm(), which signals a sol_interface! call.
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

  // Fix 30: B256::from_uint(&expr) does not exist in alloy-primitives.
  // Use B256::from(expr.to_be_bytes::<32>()) instead.
  fixed = fixed.replace(
    /B256::from_uint\(&(\w+)\)/g,
    "B256::from($1.to_be_bytes::<32>())"
  );

  // Fix 31: U256::from(N) in const context → U256::from_limbs([N, 0, 0, 0])
  // U256::from() is not const-compatible in alloy-primitives 1.3.1.
  fixed = fixed.replace(
    /(const\s+\w+\s*:\s*U256\s*=\s*)U256::from\((\d+)\)/g,
    "$1U256::from_limbs([$2, 0, 0, 0])"
  );

  // Fix 32: sol_interface! calls must have self.vm() as first host argument.
  // LLMs often omit self.vm() and pass the Call context as the first argument.
  // Pattern A: Call::new() as first argument
  fixed = fixed.replace(
    /\b(\w+)\.(\w+)\(Call::new\(\)/g,
    "$1.$2(self.vm(), Call::new()"
  );
  // Pattern B: Call::new_mutating(self) as first argument
  fixed = fixed.replace(
    /\b(\w+)\.(\w+)\(Call::new_mutating\(self\)/g,
    "$1.$2(self.vm(), Call::new_mutating(self)"
  );
  // Pattern C: Named Call variable as first argument
  const callVarPattern = /let\s+(?:mut\s+)?(\w+)\s*=\s*Call::new/g;
  let callVarMatch;
  while ((callVarMatch = callVarPattern.exec(fixed)) !== null) {
    const cvar = callVarMatch[1];
    fixed = fixed.replace(
      new RegExp(`\\b(\\w+)\\.(\\w+)\\(${cvar},\\s*`, "g"),
      `$1.$2(self.vm(), ${cvar}, `
    );
  }

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

  // Fix 33: B256::from_limbs([...]) → B256::from(U256::from_limbs([...]).to_be_bytes::<32>())
  // B256 is FixedBytes<32>, NOT Uint. from_limbs is a Uint method.
  fixed = fixed.replace(
    /B256::from_limbs\((\[[^\]]*\])\)/g,
    "B256::from(U256::from_limbs($1).to_be_bytes::<32>())"
  );

  // Fix 34: mapping(... => string) .get(key) returns StorageGuard<StorageString>.
  // Two-pass: first fix .get(k).get_string(), then fix bare .get(k).
  const stringMapFields = new Set<string>();
  const stringMapPattern = /mapping\([^=]+=>\s*string\)\s+(\w+)\s*;/g;
  let stringMapMatch;
  while ((stringMapMatch = stringMapPattern.exec(fixed)) !== null) {
    stringMapFields.add(stringMapMatch[1]);
  }
  for (const smf of stringMapFields) {
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
  // Cleanup: doubled .get_string() chains (LLM garbage)
  fixed = fixed.replace(
    /\.get_string\(\)(?:\.getter\([^)]*\))?\.get_string\(\)/g,
    ".get_string()"
  );
  // Cleanup: local_var.get_string() is always wrong.
  // .get_string() is only valid on StorageString (self.field...).
  fixed = fixed.replace(
    /\b([a-z_]\w*)\.get_string\(\)/g,
    (_match: string, varName: string) => varName === "self" ? _match : varName
  );

  // Fix 35: .abi_encode() on SolidityError enum wrapper.
  // Enum::Variant(Inner{..}).abi_encode() → Inner{..}.abi_encode()
  fixed = fixed.replace(
    /(\w+)::(\w+)\((\2\s*\{[^}]*\})\)\.abi_encode\(\)/g,
    "$3.abi_encode()"
  );

  // Fix 36: StorageString returned directly without .get_string().
  // `string name;` in sol_storage! → self.name is StorageString.
  // self.name (not followed by . or word char) → self.name.get_string()
  const strFields = new Set<string>();
  const strFieldPattern = /\bstring\s+(\w+)\s*;/g;
  let strFieldMatch;
  while ((strFieldMatch = strFieldPattern.exec(fixed)) !== null) {
    strFields.add(strFieldMatch[1]);
  }
  for (const sf of strFields) {
    fixed = fixed.replace(
      new RegExp(`self\\.${sf}(?![.\\w])`, "g"),
      `self.${sf}.get_string()`
    );
  }

  // Fix 38 (N32): Move `pub const` out of #[public] impl blocks.
  // The #[public] proc macro doesn't support associated constants.
  // Extract them to module-level constants above the impl block.
  {
    const constInImplPattern = /^([ \t]*)pub const\s+(\w+)\s*:\s*(\w+)\s*=\s*([^;]+);/gm;
    const consts: Array<{ full: string; name: string; ty: string; val: string }> = [];
    let constMatch;
    while ((constMatch = constInImplPattern.exec(fixed)) !== null) {
      // Only if inside a #[public] impl block (check if preceded by #[public])
      const beforeMatch = fixed.slice(0, constMatch.index);
      const lastPublicImpl = beforeMatch.lastIndexOf("#[public]");
      const lastClosingBrace = beforeMatch.lastIndexOf("\n}\n");
      if (lastPublicImpl > -1 && lastPublicImpl > lastClosingBrace) {
        consts.push({
          full: constMatch[0],
          name: constMatch[2],
          ty: constMatch[3],
          val: constMatch[4].trim(),
        });
      }
    }
    for (const c of consts) {
      // Remove from impl block
      fixed = fixed.replace(c.full + "\n", "");
      fixed = fixed.replace(c.full, "");
      // Add as module-level const before #[public]
      const moduleConst = `const ${c.name}: ${c.ty} = ${c.val};`;
      fixed = fixed.replace(
        /(\n#\[public\])/,
        `\n${moduleConst}\n$1`
      );
    }
  }

  // Fix 39 (N36): Clean up garbled LLM output — natural language mid-code
  // and repeated return type fragments like `-> U256) -> U256) -> U256)`.
  {
    // Remove lines that contain natural language markers inside code
    fixed = fixed.replace(
      /^.*(?:<<\s*\?\?\?|Wait,\s+we\s+need|Correction:|should be:|Let me (?:re)?write|I'll fix|Actually,|Hmm,|Oops).*$/gm,
      ""
    );

    // Fix garbled function signatures: `-> Type) -> Type) -> Type)` → `-> Type`
    // This pattern catches repeated `) -> Type)` fragments
    fixed = fixed.replace(
      /(->\s*\w+(?:<[^>]*>)?)\s*\)\s*(?:->\s*\w+(?:<[^>]*>)?\s*\)\s*)+/g,
      "$1"
    );

    // Clean up stray `>?` or `?>` fragments (LLM thinking markers)
    fixed = fixed.replace(/\s*<+\s*\?\?\?\s*>+\s*\??\s*/g, "");

    // Remove empty lines left by the above cleanups
    fixed = fixed.replace(/\n{3,}/g, "\n\n");
  }

  // Fix 40: Remove Debug from derives containing SolidityError.
  // sol! types don't implement Debug.
  fixed = fixed.replace(
    /#\[derive\(([^)]+)\)\]/g,
    (match, content: string) => {
      if (content.includes("SolidityError") && content.includes("Debug")) {
        const parts = content.split(",").map((p: string) => p.trim()).filter((p: string) => p !== "Debug");
        return `#[derive(${parts.join(", ")})]`;
      }
      return match;
    }
  );

  // Fix 41: Rename underscore-prefixed methods conflicting with public methods.
  // #[public] macro strips leading underscores for ABI selectors, so
  // fn _grant_role and fn grant_role produce the same selector.
  {
    const allFnDefs = [...fixed.matchAll(/\bfn\s+([a-z_]\w+)\s*\(/g)].map(m => m[1]);
    const publicFns = new Set(allFnDefs.filter(n => !n.startsWith("_")));
    const underscoreFns = new Set(allFnDefs.filter(n => n.startsWith("_")));
    for (const ufn of underscoreFns) {
      const base = ufn.slice(1);
      if (publicFns.has(base)) {
        fixed = fixed.replace(
          new RegExp(`\\b${ufn.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "g"),
          `${base}_internal`
        );
      }
    }
  }

  // Fix 42: address[] array deref returns FixedBytes<20>, not Address.
  // Wrap with Address::from(...) for correct type.
  {
    const addrArrayFields = [...fixed.matchAll(/\baddress\[\]\s+(\w+)/g)].map(m => m[1]);
    for (const field of addrArrayFields) {
      fixed = fixed.replace(
        new RegExp(`(?<!Address::from\\()\\*self\\.${field}\\.get\\(([^)]+)\\)\\.unwrap\\(\\)`, "g"),
        `Address::from(*self.${field}.get($1).unwrap())`
      );
    }
  }

  // Fix 43: Remove extra .setter() on string mapping writes.
  // .setter(key).setter().set_str(val) → .setter(key).set_str(val)
  fixed = fixed.replace(
    /\.setter\(([^)]+)\)\.setter\(\)\.set_str\(/g,
    ".setter($1).set_str("
  );

  // Fix 53: .get_string().unwrap_or_default() → .get_string()
  // get_string() returns String (not Option<String>), unwrap is wrong.
  fixed = fixed.replace(/\.get_string\(\)\.unwrap_or_default\(\)/g, ".get_string()");
  // Also: .get_string().unwrap() — same issue
  fixed = fixed.replace(/\.get_string\(\)\.unwrap\(\)/g, ".get_string()");

  // Fix 54: const X: U256 = U256::from(N) → const X: U256 = U256::from_limbs([N, 0, 0, 0])
  // From::from() is not a const fn. U256::from_limbs is the const-compatible alternative.
  fixed = fixed.replace(
    /const\s+(\w+)\s*:\s*U256\s*=\s*U256::from\((\d+)\)\s*;/g,
    "const $1: U256 = U256::from_limbs([$2, 0, 0, 0]);"
  );

  // Fix 55: .setter(key).unwrap().set(val) → .setter(key).set(val)
  // StorageMap .setter(key) returns StorageGuardMut (NOT Option).
  // Only StorageVec .setter(idx) returns Option needing .unwrap().
  {
    const mapFields55 = new Set<string>();
    const mfPattern55 = /mapping\([^)]*\)\s+(\w+)\s*;/g;
    let mfMatch55;
    while ((mfMatch55 = mfPattern55.exec(fixed)) !== null) {
      mapFields55.add(mfMatch55[1]);
    }
    for (const mf of mapFields55) {
      const esc = mf.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      fixed = fixed.replace(
        new RegExp(`\\.${esc}\\.setter\\(([^)]+)\\)\\.unwrap\\(\\)`, "g"),
        `.${mf}.setter($1)`
      );
    }
  }

  // Fix 44: Remove phantom variable self-assignments (let x = x;).
  // LLM sometimes generates `let role = role;` in helpers where `role` is not
  // a parameter — always a compile error. Even if it IS a parameter, it's a
  // redundant shadow. Safe to remove.
  fixed = fixed.replace(/^\s*let\s+(mut\s+)?([a-z_]\w*)\s*=\s*\2\s*;\s*$/gm, "");

  // Fix 49: Remove duplicate function definitions.
  // Rust doesn't support overloading — two `fn foo(...)` in the same impl is
  // a compile error. LLM sometimes re-defines a helper with a different
  // signature. Keep the LAST definition (LLM refines on second attempt).
  {
    const fnDefPattern = /(\n[ \t]*)(pub\s+)?fn\s+(\w+)\s*\(/g;
    const fnPositions: Array<{ name: string; pos: number }> = [];
    let fnMatch;
    while ((fnMatch = fnDefPattern.exec(fixed)) !== null) {
      fnPositions.push({ name: fnMatch[3], pos: fnMatch.index });
    }
    // Group positions by name
    const seenFns = new Map<string, number[]>();
    for (const { name, pos } of fnPositions) {
      const arr = seenFns.get(name) ?? [];
      arr.push(pos);
      seenFns.set(name, arr);
    }
    // Collect earlier duplicate spans to remove
    const toRemove: Array<[number, number]> = [];
    for (const [, positions] of seenFns) {
      if (positions.length < 2) continue;
      for (const dupPos of positions.slice(0, -1)) {
        const braceStart = fixed.indexOf("{", dupPos);
        if (braceStart === -1) continue;
        let depth = 0;
        let i = braceStart;
        while (i < fixed.length) {
          if (fixed[i] === "{") depth++;
          else if (fixed[i] === "}") {
            depth--;
            if (depth === 0) break;
          }
          i++;
        }
        if (depth === 0) {
          let lineStart = fixed.lastIndexOf("\n", dupPos);
          if (lineStart === -1) lineStart = 0;
          toRemove.push([lineStart, i + 1]);
        }
      }
    }
    // Remove in reverse order to preserve indices
    toRemove.sort((a, b) => b[0] - a[0]);
    for (const [start, end] of toRemove) {
      fixed = fixed.slice(0, start) + fixed.slice(end);
    }
  }

  // Fix 50: .setter().set() on simple (non-mapping) fields.
  // StorageUint/StorageAddress/StorageBool have .set(val) directly.
  // .setter(key) is ONLY for StorageMap.
  {
    const simpleFieldTypes = [
      "uint256", "uint128", "uint64", "uint32", "uint16", "uint8",
      "int256", "int128", "int64", "int32", "int16", "int8",
      "address", "bool", "bytes32",
    ];
    const sfPattern = new RegExp(
      `(?:${simpleFieldTypes.join("|")})\\s+(\\w+)\\s*;`, "g"
    );
    const simpleFields = new Set<string>();
    let sfMatch;
    while ((sfMatch = sfPattern.exec(fixed)) !== null) {
      simpleFields.add(sfMatch[1]);
    }
    for (const sf of simpleFields) {
      const esc = sf.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      // self.field.setter().set(val) → self.field.set(val)
      fixed = fixed.replace(
        new RegExp(`self\\.${esc}\\.setter\\(\\)\\.set\\(`, "g"),
        `self.${sf}.set(`
      );
      // self.field.setter(val).set(val) → self.field.set(val)
      fixed = fixed.replace(
        new RegExp(`self\\.${esc}\\.setter\\(([^)]+)\\)\\.set\\(\\1\\)`, "g"),
        `self.${sf}.set($1)`
      );
    }
  }

  // Fix 51: Spurious .get() / .get_string() on mapping reads.
  // (a) .get(key).get() → .get(key) — mapping .get(key) returns value directly
  fixed = fixed.replace(
    /\.get\(((?:[^()]*|\([^()]*\))*)\)\.get\(\)/g,
    ".get($1)"
  );
  // (b) .get_string().get() → .get_string()
  fixed = fixed.replace(/\.get_string\(\)\.get\(\)/g, ".get_string()");
  // (c) .getter(key).get_string() on non-string mappings → .get(key)
  {
    const stringMapFields = new Set<string>();
    const smfPattern = /mapping\([^)]*=>\s*string\)\s+(\w+)\s*;/g;
    let smfMatch;
    while ((smfMatch = smfPattern.exec(fixed)) !== null) {
      stringMapFields.add(smfMatch[1]);
    }
    const getterStringPattern = /self\.(\w+)\.getter\(([^)]+)\)\.get_string\(\)/g;
    let gsMatch;
    // Collect replacements first to avoid modifying during iteration
    const gsReplacements: Array<[string, string]> = [];
    while ((gsMatch = getterStringPattern.exec(fixed)) !== null) {
      if (!stringMapFields.has(gsMatch[1])) {
        gsReplacements.push([gsMatch[0], `self.${gsMatch[1]}.get(${gsMatch[2]})`]);
      }
    }
    for (const [from, to] of gsReplacements) {
      fixed = fixed.replace(from, to);
    }
  }

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

  // Build context string (for additional patterns only, capped to prevent token overflow)
  const MAX_CONTEXT_CHARS = 2000;
  const contextStr = contextResult.contexts
    .map((c, i) => `[${i + 1}] (${c.source})\n${c.content.slice(0, MAX_CONTEXT_CHARS)}`)
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
  // chatCompletion() handles retry internally (primary model + fallback model)
  const response = await generateCodeFromTemplate(
    openrouterApiKey,
    enhancedPrompt,
    template,
    contextStr,
    targetVersion
  );

  // Parse response - extract code blocks and explanation
  const codeMatch = response.content.match(/```rust\n([\s\S]*?)```/);
  let code = codeMatch ? codeMatch[1].trim() : response.content.trim();

  // If LLM returned empty after both attempts, fall back to template immediately
  if (!code || code.length === 0) {
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

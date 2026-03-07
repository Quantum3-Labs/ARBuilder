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
  for (const cl of cleanLines) {
    const clStripped = cl.trim();
    if (clStripped.startsWith("//")) continue;
    const fnameMatch = clStripped.match(/(\w+)\s*;$/);
    if (fnameMatch) declaredFields.add(fnameMatch[1]);
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

// ─── Field Type Map ────────────────────────────────────────────────
// Parsed once from sol_storage!, shared across all fix phases.

interface FieldInfo {
  name: string;
  type: "primitive" | "mapping" | "string" | "string_mapping" | "array" | "nested_mapping" | "address_array";
  solType: string;
  valueType?: string;
  keyType?: string;
}
type FieldMap = Map<string, FieldInfo>;

interface FixContext {
  fields: FieldMap;
  template: StylusTemplate;
  structName: string;
}

/** Parse sol_storage! block and classify each field by type. */
function parseFieldMap(code: string): FieldMap {
  const fields: FieldMap = new Map();
  const blockMatch = code.match(/sol_storage!\s*\{[\s\S]*?#\[entrypoint\][\s\S]*?pub\s+struct\s+\w+\s*\{([\s\S]*?)\n\s*\}/);
  if (!blockMatch) return fields;
  const body = blockMatch[1];
  for (const line of body.split("\n")) {
    const stripped = line.trim();
    if (!stripped || stripped.startsWith("//")) continue;
    // Extract field name: last word before `;`
    const nameMatch = stripped.match(/(\w+)\s*;$/);
    if (!nameMatch) continue;
    const name = nameMatch[1];
    // Extract type: everything before the field name
    const typeStr = stripped.slice(0, stripped.lastIndexOf(name)).trim();
    if (!typeStr) continue;

    if (/^mapping\(/.test(typeStr)) {
      // Check for nested mapping: mapping(K1 => mapping(K2 => V))
      const nestedMatch = typeStr.match(/^mapping\(\s*(\w+)\s*=>\s*mapping\(/);
      if (nestedMatch) {
        fields.set(name, { name, type: "nested_mapping", solType: typeStr, keyType: nestedMatch[1] });
      } else {
        // Check if value type is string
        const mapMatch = typeStr.match(/^mapping\(\s*(\w+)\s*=>\s*(\w+)\s*\)$/);
        if (mapMatch && mapMatch[2] === "string") {
          fields.set(name, { name, type: "string_mapping", solType: typeStr, keyType: mapMatch[1], valueType: "string" });
        } else {
          const keyMatch = typeStr.match(/^mapping\(\s*(\w+)/);
          fields.set(name, { name, type: "mapping", solType: typeStr, keyType: keyMatch?.[1], valueType: mapMatch?.[2] });
        }
      }
    } else if (typeStr === "string") {
      fields.set(name, { name, type: "string", solType: "string" });
    } else if (/\[\]$/.test(typeStr)) {
      if (typeStr === "address[]") {
        fields.set(name, { name, type: "address_array", solType: typeStr });
      } else {
        fields.set(name, { name, type: "array", solType: typeStr });
      }
    } else {
      fields.set(name, { name, type: "primitive", solType: typeStr });
    }
  }
  return fields;
}

/** Build fix context with field map and struct name. */
function buildFixContext(code: string, template: StylusTemplate): FixContext {
  const fields = parseFieldMap(code);
  const structMatch = code.match(/pub\s+struct\s+(\w+)\s*\{/);
  return { fields, template, structName: structMatch?.[1] ?? "Contract" };
}

// ─── Phase 1: Structural Validation ───────────────────────────────
// Ensures boilerplate, cfg_attr, entrypoint, sol_storage! block integrity.
// Hard fallback to template if irrecoverable.

function structuralValidate(code: string, template: StylusTemplate): string {
  let fixed = code;

  // Remove empty sol_storage! blocks
  fixed = fixed.replace(/sol_storage!\s*\{\s*\}/g, "");

  // Ensure proper cfg_attr if missing
  if (!fixed.includes('#![cfg_attr(not(any(test')) {
    const templateStart = template.libRs.split("extern crate alloc")[0];
    if (!fixed.startsWith("#![cfg_attr")) {
      fixed = templateStart + fixed;
    } else {
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

  // Ensure extern crate alloc if missing
  if (!fixed.includes("extern crate alloc")) {
    fixed = fixed.replace(
      /^(#!\[cfg_attr.*\n)+/m,
      "$&#[macro_use]\nextern crate alloc;\n\n"
    );
  }

  // Ensure at least one sol_storage! block (hard fallback)
  const solStorageCount = (fixed.match(/sol_storage!\s*\{/g) || []).length;
  if (solStorageCount === 0) {
    return template.libRs;
  }

  // Ensure #[entrypoint] is inside sol_storage! if missing
  if (!fixed.includes("#[entrypoint]")) {
    fixed = fixed.replace(
      /sol_storage!\s*\{\s*(\n?\s*pub struct)/,
      "sol_storage! {\n    #[entrypoint]$1"
    );
  }

  // Sanitize sol_storage! block (structural validation, garbled line removal)
  fixed = sanitizeSolStorage(fixed, template);

  return fixed;
}

// ─── Phase 2: Import Normalization ────────────────────────────────
// Single pass over all `use` statements. Add missing, remove deprecated, deduplicate.

function normalizeImports(code: string, _ctx: FixContext): string {
  let fixed = code;

  // Vec import deduplication
  if (fixed.includes("use alloc::vec::Vec;") && fixed.includes("use alloc::{") && fixed.includes("vec::Vec")) {
    fixed = fixed.replace(/use alloc::vec::Vec;\n?/g, "");
  }
  if (fixed.includes("Vec<u8>") && !fixed.includes("alloc::vec::Vec") && !fixed.includes("alloc::{")) {
    fixed = fixed.replace(/(extern crate alloc;)/, "$1\n\nuse alloc::vec::Vec;");
  }

  // Ensure use alloc::vec (sol_storage! needs vec module)
  if (!fixed.includes("use alloc::vec;") && !fixed.includes("use alloc::{")) {
    fixed = fixed.replace(/(extern crate alloc;\s*\n)/, "$1\nuse alloc::{vec, vec::Vec};\n");
  } else if (fixed.includes("use alloc::vec::Vec;") && !fixed.includes("use alloc::vec;") && !fixed.includes("alloc::{")) {
    fixed = fixed.replace("use alloc::vec::Vec;", "use alloc::{vec, vec::Vec};");
  }

  // Remove incorrect stylus_sdk::storage imports
  fixed = fixed.replace(
    /^use stylus_sdk::storage(?:::(?:StorageString|StorageMap|StorageVec|StorageU\d+|StorageBool|StorageAddress))?;\s*$/gm,
    ""
  );

  // Ensure correct alloc::string imports
  {
    const needsString = fixed.includes("-> String") || fixed.includes(": String") || fixed.includes(".to_string()") || fixed.includes("String::new") || fixed.includes("String::from");
    const needsToString = fixed.includes(".to_string()");
    if (needsString || needsToString) {
      fixed = fixed.replace(/^use alloc::string::\{[^}]*\};\s*\n?/gm, "");
      fixed = fixed.replace(/^use alloc::string::\w+;\s*\n?/gm, "");
      const parts: string[] = [];
      if (needsString) parts.push("String");
      if (needsToString) parts.push("ToString");
      if (parts.length > 0) {
        const importLine = parts.length === 1
          ? `use alloc::string::${parts[0]};`
          : `use alloc::string::{${parts.join(", ")}};`;
        fixed = fixed.replace(/(use alloc::\{vec, vec::Vec\};)/, `$1\n${importLine}`);
      }
    }
  }

  // Fix wrong transfer_eth import paths
  fixed = fixed.replace(/use stylus_sdk::call::transfer_eth;/g, "use stylus_sdk::call::transfer::transfer_eth;");
  fixed = fixed.replace(
    /use stylus_sdk::call::\{([^}]*)\btransfer_eth\b([^}]*)\};/g,
    (_match, before: string, after: string) => {
      const others = (before.replace("transfer_eth", "").trim().replace(/^,|,$/g, "").trim()
        + ", " + after.trim().replace(/^,|,$/g, "").trim()).replace(/^,\s*|,\s*$/g, "").trim();
      const transferLine = "use stylus_sdk::call::transfer::transfer_eth;";
      return others ? `${transferLine}\nuse stylus_sdk::call::{${others}};` : transferLine;
    }
  );

  // Remove deprecated imports
  fixed = fixed.replace(/^use stylus_sdk::evm.*;\s*$/gm, "");
  fixed = fixed.replace(/^use stylus_sdk::msg.*;\s*$/gm, "");
  fixed = fixed.replace(/^use std::time.*;\s*$/gm, "");
  fixed = fixed.replace(/^use stylus_sdk::call::Call;\s*$/gm, "");

  return fixed;
}

// ─── Phase 3: Storage Accessor Normalization ──────────────────────
// THE BIG WIN: Type-aware normalization of all storage accessor patterns
// using the FieldMap parsed in Phase 1. Replaces 16 scattered fixes.

function normalizeStorageAccessors(code: string, ctx: FixContext): string {
  let fixed = code;

  // --- Per-field-type rules ---

  for (const [, field] of ctx.fields) {
    const esc = field.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

    switch (field.type) {
      case "primitive": {
        // Bare field read → .get()
        const bareFieldPattern = new RegExp(`(\\w+)\\.${esc}\\b(?!\\s*[.(])`, "g");
        fixed = fixed.replace(bareFieldPattern, `$1.${field.name}.get()`);
        // .setter().set(val) → .set(val) (setter is for mappings only)
        fixed = fixed.replace(
          new RegExp(`self\\.${esc}\\.setter\\(\\)\\.set\\(`, "g"),
          `self.${field.name}.set(`
        );
        // .setter(val).set(val) → .set(val) (same value repeated)
        fixed = fixed.replace(
          new RegExp(`self\\.${esc}\\.setter\\(([^)]+)\\)\\.set\\(\\1\\)`, "g"),
          `self.${field.name}.set($1)`
        );
        break;
      }

      case "string": {
        // .set() → .set_str()
        fixed = fixed.replace(new RegExp(`\\.${esc}\\.set\\(`, "g"), `.${field.name}.set_str(`);
        // .get() → .get_string()
        fixed = fixed.replace(new RegExp(`\\.${esc}\\.get\\(\\)`, "g"), `.${field.name}.get_string()`);
        // Bare self.field → .get_string()
        fixed = fixed.replace(
          new RegExp(`self\\.${esc}(?![.\\w])`, "g"),
          `self.${field.name}.get_string()`
        );
        break;
      }

      case "mapping":
      case "nested_mapping": {
        // .get(key).unwrap_or_default() → .get(key)
        fixed = fixed.replace(
          new RegExp(`\\.${esc}\\.get\\(([^)]*)\\)\\.unwrap_or_default\\(\\)`, "g"),
          `.${field.name}.get($1)`
        );
        // Nested .getter(k1).get(k2).unwrap_or_default()
        fixed = fixed.replace(
          new RegExp(`\\.${esc}\\.getter\\(([^)]*)\\)\\.get\\(([^)]*)\\)\\.unwrap_or_default\\(\\)`, "g"),
          `.${field.name}.getter($1).get($2)`
        );
        // .setter(key).unwrap().set(val) → .setter(key).set(val) (unwrap is for StorageVec only)
        fixed = fixed.replace(
          new RegExp(`\\.${esc}\\.setter\\(([^)]+)\\)\\.unwrap\\(\\)`, "g"),
          `.${field.name}.setter($1)`
        );
        // .set(key, value) → .setter(key).set(value) (two-arg set doesn't exist)
        // Note: this is applied field-specifically to avoid false positives
        break;
      }

      case "string_mapping": {
        // .setter(key).setter().set_str(val) → .setter(key).set_str(val)
        fixed = fixed.replace(
          new RegExp(`\\.${esc}\\.setter\\(([^)]+)\\)\\.setter\\(\\)\\.set_str\\(`, "g"),
          `.${field.name}.setter($1).set_str(`
        );
        // .setter(key).unwrap().set(val) → .setter(key).set(val)
        fixed = fixed.replace(
          new RegExp(`\\.${esc}\\.setter\\(([^)]+)\\)\\.unwrap\\(\\)`, "g"),
          `.${field.name}.setter($1)`
        );
        break;
      }

      case "array": {
        // .setter(i).set(v) → .setter(i).unwrap().set(v) (StorageVec returns Option)
        fixed = fixed.replace(
          new RegExp(`\\.${esc}\\s*\\.setter\\(((?:[^()]*|\\([^()]*\\))*)\\)\\s*\\.set\\(`, "g"),
          `.${field.name}.setter($1).unwrap().set(`
        );
        break;
      }

      case "address_array": {
        // .setter(i).set(v) → .setter(i).unwrap().set(v)
        fixed = fixed.replace(
          new RegExp(`\\.${esc}\\s*\\.setter\\(((?:[^()]*|\\([^()]*\\))*)\\)\\s*\\.set\\(`, "g"),
          `.${field.name}.setter($1).unwrap().set(`
        );
        // *self.field.get(i).unwrap() → Address::from(*self.field.get(i).unwrap())
        fixed = fixed.replace(
          new RegExp(`(?<!Address::from\\()\\*self\\.${esc}\\.get\\(([^)]+)\\)\\.unwrap\\(\\)`, "g"),
          `Address::from(*self.${field.name}.get($1).unwrap())`
        );
        break;
      }
    }
  }

  // --- Cross-field accessor patterns (not field-specific) ---

  // .get(k).setter(...) → .setter(k).setter(...) (nested mapping immutable→mutable)
  fixed = fixed.replace(
    /\.get\(((?:[^()]*|\([^()]*\))*)\)\s*\.setter\(/g,
    ".setter($1).setter("
  );
  fixed = fixed.replace(
    /\.getter\(((?:[^()]*|\([^()]*\))*)\)\s*\.setter\(/g,
    ".setter($1).setter("
  );

  // .get(key).field.setter( → .setter(key).field.setter( (nested struct writes)
  fixed = fixed.replace(
    /\.get\(((?:[^()]*|\([^()]*\))*)\)((?:\.\w+)+)\.setter\(/g,
    ".setter($1)$2.setter("
  );

  // .field.set(key, value) → .field.setter(key).set(value) (two-arg .set doesn't exist on StorageMap)
  fixed = fixed.replace(
    /(\.\w+)\.set\(\s*((?:[^,()]*|\([^()]*\))*)\s*,\s*((?:[^,()]*|\([^()]*\))*)\s*\)/g,
    "$1.setter($2).set($3)"
  );

  // --- String mapping read normalization ---
  // .get(key).getter() → .getter(key) (inject key into empty getter)
  fixed = fixed.replace(
    /\.get\(((?:[^()]*|\([^()]*\))+)\)\s*\.getter\(\)/g,
    ".getter($1)"
  );
  // .get(key).getter(key2) → .getter(key2) (strip redundant .get)
  fixed = fixed.replace(
    /\.get\(((?:[^()]*|\([^()]*\))*)\)\s*\.getter\(/g,
    ".getter("
  );

  // Per-field string mapping read normalization
  for (const [, field] of ctx.fields) {
    if (field.type !== "string_mapping") continue;
    const esc = field.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    // Pass 1: .field.get(k).get_string() → .field.getter(k).get_string()
    fixed = fixed.replace(
      new RegExp(`\\.${esc}\\.get\\(([^)]+)\\)\\.get_string\\(\\)`, "g"),
      `.${field.name}.getter($1).get_string()`
    );
    // Pass 2: bare .field.get(k) → .field.getter(k).get_string()
    fixed = fixed.replace(
      new RegExp(`\\.${esc}\\.get\\(([^)]+)\\)`, "g"),
      `.${field.name}.getter($1).get_string()`
    );
    // Pass 3: bare .field.getter(k) without .get_string() → append
    fixed = fixed.replace(
      new RegExp(`\\.${esc}\\.getter\\(([^)]+)\\)(?!\\.get_string\\(\\))`, "g"),
      `.${field.name}.getter($1).get_string()`
    );
  }

  // --- Overcorrection cleanup ---

  // .get_string().unwrap_or_default() / .unwrap() → .get_string()
  fixed = fixed.replace(/\.get_string\(\)\.unwrap_or_default\(\)/g, ".get_string()");
  fixed = fixed.replace(/\.get_string\(\)\.unwrap\(\)/g, ".get_string()");

  // Doubled .get_string() chains
  fixed = fixed.replace(/\.get_string\(\)\s*\.get_string\(\)/g, ".get_string()");

  // local_var.get_string() → local_var (only valid on self.field...)
  fixed = fixed.replace(
    /\b([a-z_]\w*)\.get_string\(\)/g,
    (_match: string, varName: string) => varName === "self" ? _match : varName
  );

  // .get(key).get() → .get(key) (double .get on mapping)
  fixed = fixed.replace(
    /\.get\(((?:[^()]*|\([^()]*\))*)\)\.get\(\)/g,
    ".get($1)"
  );
  // .get_string().get() → .get_string()
  fixed = fixed.replace(/\.get_string\(\)\.get\(\)/g, ".get_string()");

  // .getter(key).get_string() on non-string-mapping fields → .get(key)
  {
    const stringMapFieldNames = new Set<string>();
    for (const [, f] of ctx.fields) {
      if (f.type === "string_mapping") stringMapFieldNames.add(f.name);
    }
    const getterStringPattern = /self\.(\w+)\.getter\(([^)]+)\)\.get_string\(\)/g;
    const gsReplacements: Array<[string, string]> = [];
    let gsMatch;
    while ((gsMatch = getterStringPattern.exec(fixed)) !== null) {
      if (!stringMapFieldNames.has(gsMatch[1])) {
        gsReplacements.push([gsMatch[0], `self.${gsMatch[1]}.get(${gsMatch[2]})`]);
      }
    }
    for (const [from, to] of gsReplacements) {
      fixed = fixed.replace(from, to);
    }
  }

  return fixed;
}

// ─── Phase 4: API Migration ──────────────────────────────────────
// SDK 0.10.0 migration patterns: deprecated APIs, sol_interface!, etc.

function migrateApi(code: string, _ctx: FixContext): string {
  let fixed = code;

  // sol! { interface } → sol_interface! { interface }
  fixed = fixed.replace(/sol!\s*\{\s*(interface\b)/g, "sol_interface! { $1");

  // Rust Storage* types → Solidity types in sol_storage!
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

  // transfer_eth: self.transfer_eth(args) → transfer_eth(self.vm(), args)
  fixed = fixed.replace(/self\.transfer_eth\(([^)]+)\)/g, "transfer_eth(self.vm(), $1)");
  // transfer_eth(self, ...) → transfer_eth(self.vm(), ...)
  fixed = fixed.replace(/transfer_eth\(self,\s*/g, "transfer_eth(self.vm(), ");

  // Deprecated API replacements
  fixed = fixed.replace(/msg::sender\(\)/g, "self.vm().msg_sender()");
  fixed = fixed.replace(/msg::value\(\)/g, "self.vm().msg_value()");
  fixed = fixed.replace(/evm::log\(/g, "self.vm().log(");
  fixed = fixed.replace(/self\.vm\(\)\.address\(\)/g, "self.vm().contract_address()");
  fixed = fixed.replace(/U256::zero\(\)/g, "U256::ZERO");
  fixed = fixed.replace(/U128::zero\(\)/g, "U128::ZERO");
  fixed = fixed.replace(/U64::zero\(\)/g, "U64::ZERO");

  // std::time → block_timestamp
  fixed = fixed.replace(/std::time::SystemTime::now\(\)[^;]*/g, "self.vm().block_timestamp()");

  // sol_interface! camelCase → snake_case call sites
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

  // sol_interface! missing self.vm() host arg
  fixed = fixed.replace(/\b(\w+)\.(\w+)\(Call::new\(\)/g, "$1.$2(self.vm(), Call::new()");
  fixed = fixed.replace(/\b(\w+)\.(\w+)\(Call::new_mutating\(self\)/g, "$1.$2(self.vm(), Call::new_mutating(self)");
  // Named Call variable pattern
  const callVarPattern = /let\s+(?:mut\s+)?(\w+)\s*=\s*Call::new/g;
  let callVarMatch;
  while ((callVarMatch = callVarPattern.exec(fixed)) !== null) {
    const cvar = callVarMatch[1];
    fixed = fixed.replace(
      new RegExp(`\\b(\\w+)\\.(\\w+)\\(${cvar},\\s*`, "g"),
      `$1.$2(self.vm(), ${cvar}, `
    );
  }

  return fixed;
}

// ─── Phase 5: Type Corrections ───────────────────────────────────
// B256, U256 const, I256 suffix, unwrap semantics, etc.

function correctTypes(code: string, _ctx: FixContext): string {
  let fixed = code;

  // B256::from_uint(&x) → B256::from(x.to_be_bytes::<32>())
  fixed = fixed.replace(/B256::from_uint\(&(\w+)\)/g, "B256::from($1.to_be_bytes::<32>())");

  // B256::from_limbs([...]) → B256::from(U256::from_limbs([...]).to_be_bytes::<32>())
  fixed = fixed.replace(
    /B256::from_limbs\((\[[^\]]*\])\)/g,
    "B256::from(U256::from_limbs($1).to_be_bytes::<32>())"
  );

  // B32 → B256
  fixed = fixed.replace(/\bB32\b/g, "B256");

  // const U256 = U256::from(N) → U256::from_limbs([N, 0, 0, 0]) (merged Fix 31+54)
  fixed = fixed.replace(
    /(const\s+\w+\s*:\s*U256\s*=\s*)U256::from\((\d+)\)/g,
    "$1U256::from_limbs([$2, 0, 0, 0])"
  );
  // Second pass: catch full statements the prefix-capture missed
  fixed = fixed.replace(
    /const\s+(\w+)\s*:\s*U256\s*=\s*U256::from\((\d+)\)\s*;/g,
    "const $1: U256 = U256::from_limbs([$2, 0, 0, 0]);"
  );

  // I256::from(N_i128) and other suffixes → I256::from(N)
  fixed = fixed.replace(/I256::from\((-?\d+)_i128\)/g, "I256::from($1)");
  fixed = fixed.replace(/I256::from\((-?\d+)_[iu]\d+\)/g, "I256::from($1)");

  // .unwrap_or_else(VALUE) → .unwrap_or(VALUE)
  fixed = fixed.replace(/\.unwrap_or_else\((\w+::(?:ZERO|MAX|MIN|ONE))\)/g, ".unwrap_or($1)");

  // self.vm().log(...)? → self.vm().log(...) (returns (), not Result)
  fixed = fixed.replace(/(self\.vm\(\)\.log\([^;]*\))\?/g, "$1");

  // .as_usize() → .to::<usize>()
  fixed = fixed.replace(/\.as_usize\(\)/g, ".to::<usize>()");

  // N57: .as_u64() → .to::<u64>(), .as_u32() → .to::<u32>(), .as_u128() → .to::<u128>()
  // alloy-primitives 1.x Uint does not have .as_T() methods. Use .to::<T>().
  fixed = fixed.replace(/\.as_u64\(\)/g, ".to::<u64>()");
  fixed = fixed.replace(/\.as_u32\(\)/g, ".to::<u32>()");
  fixed = fixed.replace(/\.as_u128\(\)/g, ".to::<u128>()");

  // Errors::Variant(Inner{..}).abi_encode() → Inner{..}.abi_encode()
  fixed = fixed.replace(
    /(\w+)::(\w+)\((\2\s*\{[^}]*\})\)\.abi_encode\(\)/g,
    "$3.abi_encode()"
  );

  return fixed;
}

// ─── Phase 6: Output Sanitization ────────────────────────────────
// Clean up LLM output artifacts: garbled text, duplicate functions,
// proc macro conflicts, phantom variables.

function sanitizeOutput(code: string, _ctx: FixContext): string {
  let fixed = code;

  // Move pub const out of #[public] impl blocks
  {
    const constInImplPattern = /^([ \t]*)pub const\s+(\w+)\s*:\s*(\w+)\s*=\s*([^;]+);/gm;
    const consts: Array<{ full: string; name: string; ty: string; val: string }> = [];
    let constMatch;
    while ((constMatch = constInImplPattern.exec(fixed)) !== null) {
      const beforeMatch = fixed.slice(0, constMatch.index);
      const lastPublicImpl = beforeMatch.lastIndexOf("#[public]");
      const lastClosingBrace = beforeMatch.lastIndexOf("\n}\n");
      if (lastPublicImpl > -1 && lastPublicImpl > lastClosingBrace) {
        consts.push({ full: constMatch[0], name: constMatch[2], ty: constMatch[3], val: constMatch[4].trim() });
      }
    }
    for (const c of consts) {
      fixed = fixed.replace(c.full + "\n", "");
      fixed = fixed.replace(c.full, "");
      const moduleConst = `const ${c.name}: ${c.ty} = ${c.val};`;
      fixed = fixed.replace(/(\n#\[public\])/, `\n${moduleConst}\n$1`);
    }
  }

  // Strip garbled natural language from code
  fixed = fixed.replace(
    /^.*(?:<<\s*\?\?\?|Wait,\s+we\s+need|Correction:|should be:|Let me (?:re)?write|I'll fix|Actually,|Hmm,|Oops).*$/gm,
    ""
  );
  // Fix garbled function signatures: -> Type) -> Type) → -> Type
  fixed = fixed.replace(
    /(->\s*\w+(?:<[^>]*>)?)\s*\)\s*(?:->\s*\w+(?:<[^>]*>)?\s*\)\s*)+/g,
    "$1"
  );
  // Clean up stray `>?` fragments
  fixed = fixed.replace(/\s*<+\s*\?\?\?\s*>+\s*\??\s*/g, "");
  fixed = fixed.replace(/\n{3,}/g, "\n\n");

  // Remove Debug from #[derive(SolidityError, Debug)]
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

  // Rename underscore-prefixed methods conflicting with public methods
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

  // Remove phantom self-assignments (let x = x;)
  fixed = fixed.replace(/^\s*let\s+(mut\s+)?([a-z_]\w*)\s*=\s*\2\s*;\s*$/gm, "");

  // N58: camelCase shorthand in struct initializers → explicit field: snake_case
  // sol! event/error structs have camelCase fields (Solidity convention), but Rust
  // variables are snake_case. LLM uses shorthand `MyError { newCap }` which fails
  // because no local `newCap` exists — should be `MyError { newCap: new_cap }`.
  // Match: ident { ... camelField ... } where camelField has no `:` after it.
  fixed = fixed.replace(
    /\b([A-Z]\w*)\s*\{([^}]*)\}/g,
    (match, _structName: string, fields: string) => {
      // Skip sol! blocks (they define types, not initialize them)
      if (/^\s*(?:event|error|interface|function)\s/.test(fields)) return match;
      let changed = false;
      const fixedFields = fields.replace(
        /\b([a-z][a-zA-Z]*[A-Z]\w*)\s*(?=[,}\n])/g,
        (fieldMatch: string, camelName: string) => {
          // Skip if already has `:` assignment (check preceding context)
          // Convert camelCase to snake_case
          const snakeName = camelName.replace(/([A-Z])/g, "_$1").toLowerCase();
          changed = true;
          return `${camelName}: ${snakeName}`;
        }
      );
      return changed ? `${_structName} { ${fixedFields.trim()} }` : match;
    }
  );

  // Remove duplicate function definitions (keep last)
  {
    const fnDefPattern = /(\n[ \t]*)(pub\s+)?fn\s+(\w+)\s*\(/g;
    const fnPositions: Array<{ name: string; pos: number }> = [];
    let fnMatch;
    while ((fnMatch = fnDefPattern.exec(fixed)) !== null) {
      fnPositions.push({ name: fnMatch[3], pos: fnMatch.index });
    }
    const seenFns = new Map<string, number[]>();
    for (const { name, pos } of fnPositions) {
      const arr = seenFns.get(name) ?? [];
      arr.push(pos);
      seenFns.set(name, arr);
    }
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
          else if (fixed[i] === "}") { depth--; if (depth === 0) break; }
          i++;
        }
        if (depth === 0) {
          let lineStart = fixed.lastIndexOf("\n", dupPos);
          if (lineStart === -1) lineStart = 0;
          toRemove.push([lineStart, i + 1]);
        }
      }
    }
    toRemove.sort((a, b) => b[0] - a[0]);
    for (const [start, end] of toRemove) {
      fixed = fixed.slice(0, start) + fixed.slice(end);
    }
  }

  return fixed;
}

// ─── Main Entry Point ────────────────────────────────────────────

function validateAndFixCode(code: string, template: StylusTemplate): string {
  // Phase 1: Structural validation (may fallback to template)
  let fixed = structuralValidate(code, template);

  // Parse field type map from cleaned sol_storage! block
  const ctx = buildFixContext(fixed, template);

  // Phase 2: Import normalization
  fixed = normalizeImports(fixed, ctx);

  // Phase 3: Storage accessor normalization (type-aware, replaces 16 scattered fixes)
  fixed = normalizeStorageAccessors(fixed, ctx);

  // Phase 4: SDK 0.10.0 API migration
  fixed = migrateApi(fixed, ctx);

  // Phase 5: Type corrections
  fixed = correctTypes(fixed, ctx);

  // Phase 6: Output sanitization
  fixed = sanitizeOutput(fixed, ctx);

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

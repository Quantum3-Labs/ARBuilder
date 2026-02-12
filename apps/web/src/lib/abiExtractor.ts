/**
 * ABI extractor for Stylus (Rust) smart contracts.
 *
 * Parses #[public] impl blocks from lib.rs to produce a JSON ABI
 * compatible with viem's parseAbi format and Ethereum standard ABI.
 *
 * Works in CF Workers — pure regex parsing, no native deps.
 */

// Rust → Solidity type mapping
const RUST_TO_SOL: Record<string, string> = {
  U256: "uint256",
  U128: "uint128",
  U64: "uint64",
  U32: "uint32",
  U16: "uint16",
  U8: "uint8",
  I256: "int256",
  I128: "int128",
  I64: "int64",
  I32: "int32",
  I16: "int16",
  I8: "int8",
  Address: "address",
  bool: "bool",
  String: "string",
  "Vec<u8>": "bytes",
  u8: "uint8",
  u16: "uint16",
  u32: "uint32",
  u64: "uint64",
  u128: "uint128",
};

function rustTypeToSol(rustType: string): string {
  const t = rustType.trim();
  if (RUST_TO_SOL[t]) return RUST_TO_SOL[t];

  // Vec<T> → T[]
  const vecMatch = t.match(/^Vec<(.+)>$/);
  if (vecMatch) return `${rustTypeToSol(vecMatch[1])}[]`;

  // FixedBytes<N> → bytesN
  const fbMatch = t.match(/^FixedBytes<(\d+)>$/);
  if (fbMatch) return `bytes${fbMatch[1]}`;

  return "uint256"; // fallback
}

interface AbiParam {
  name: string;
  type: string;
  indexed?: boolean;
}

interface AbiEntry {
  type: "function" | "event" | "error";
  name: string;
  inputs: AbiParam[];
  outputs?: AbiParam[];
  stateMutability?: string;
}

function parseFnParams(paramsStr: string): AbiParam[] {
  const params: AbiParam[] = [];
  if (!paramsStr.trim()) return params;

  // Split on commas respecting generics
  const parts: string[] = [];
  let depth = 0;
  let current = "";
  for (const ch of paramsStr) {
    if (ch === "<" || ch === "(") depth++;
    else if (ch === ">" || ch === ")") depth--;
    else if (ch === "," && depth === 0) {
      parts.push(current.trim());
      current = "";
      continue;
    }
    current += ch;
  }
  if (current.trim()) parts.push(current.trim());

  for (const part of parts) {
    const p = part.trim();
    if (p === "&self" || p === "&mut self" || p === "self") continue;
    if (p.includes(":")) {
      const [name, typeStr] = p.split(":", 2);
      params.push({
        name: name.trim(),
        type: rustTypeToSol(typeStr.trim()),
      });
    }
  }
  return params;
}

function parseReturnType(returnStr: string): AbiParam[] {
  const r = returnStr.trim();
  if (!r || r === "()" || r === "") return [];

  // Handle Result<T, Vec<u8>>
  const resultMatch = r.match(/^Result<(.+),\s*Vec<u8>>$/);
  const inner = resultMatch ? resultMatch[1].trim() : r;

  // Tuple
  if (inner.startsWith("(") && inner.endsWith(")")) {
    const types: string[] = [];
    let depth = 0;
    let current = "";
    for (const ch of inner.slice(1, -1)) {
      if (ch === "<" || ch === "(") depth++;
      else if (ch === ">" || ch === ")") depth--;
      else if (ch === "," && depth === 0) {
        types.push(current.trim());
        current = "";
        continue;
      }
      current += ch;
    }
    if (current.trim()) types.push(current.trim());
    return types.map((t) => ({ name: "", type: rustTypeToSol(t) }));
  }

  return [{ name: "", type: rustTypeToSol(inner) }];
}

/**
 * Extract a JSON ABI from Stylus lib.rs source code.
 */
export function extractAbiFromCode(libRs: string): AbiEntry[] {
  const abi: AbiEntry[] = [];

  // 1. Parse events from sol! blocks
  const eventRe = /sol!\s*\{[^}]*?event\s+(\w+)\s*\(([^)]*)\)\s*;/gs;
  for (const match of libRs.matchAll(eventRe)) {
    const inputs: AbiParam[] = [];
    if (match[2].trim()) {
      for (const param of match[2].split(",")) {
        const p = param.trim();
        const indexed = p.includes("indexed");
        const clean = p.replace("indexed", "").trim();
        const parts = clean.split(/\s+/);
        inputs.push({
          name: parts[1] || "",
          type: parts[0],
          indexed,
        });
      }
    }
    abi.push({ type: "event", name: match[1], inputs });
  }

  // 2. Parse errors from sol! blocks
  const errorRe = /sol!\s*\{[^}]*?error\s+(\w+)\s*\(([^)]*)\)\s*;/gs;
  for (const match of libRs.matchAll(errorRe)) {
    const inputs: AbiParam[] = [];
    if (match[2].trim()) {
      for (const param of match[2].split(",")) {
        const parts = param.trim().split(/\s+/);
        inputs.push({ name: parts[1] || "", type: parts[0] });
      }
    }
    abi.push({ type: "error", name: match[1], inputs });
  }

  // 3. Parse functions from #[public] impl blocks
  const implRe = /#\[public\]\s*impl\s+\w+\s*\{([\s\S]*?)^\}/gm;
  for (const implMatch of libRs.matchAll(implRe)) {
    const implBody = implMatch[1];
    const fnRe = /(#\[payable\]\s*)?pub\s+fn\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^{]+))?\s*\{/g;

    for (const fnMatch of implBody.matchAll(fnRe)) {
      const isPayable = !!fnMatch[1];
      const fnName = fnMatch[2];
      const paramsStr = fnMatch[3];
      const returnStr = fnMatch[4] || "";

      let stateMutability: string;
      if (isPayable) stateMutability = "payable";
      else if (paramsStr.includes("&mut self")) stateMutability = "nonpayable";
      else if (paramsStr.includes("&self")) stateMutability = "view";
      else stateMutability = "nonpayable";

      abi.push({
        type: "function",
        name: fnName,
        inputs: parseFnParams(paramsStr),
        outputs: parseReturnType(returnStr.trim()),
        stateMutability,
      });
    }
  }

  return abi;
}

/**
 * Convert JSON ABI to viem human-readable format.
 */
export function abiToViemHumanReadable(abi: AbiEntry[]): string[] {
  return abi.map((entry) => {
    if (entry.type === "function") {
      const inputs = entry.inputs
        .map((p) => (p.name ? `${p.type} ${p.name}` : p.type))
        .join(", ");
      const outputs = (entry.outputs || [])
        .map((p) => (p.name ? `${p.type} ${p.name}` : p.type))
        .join(", ");
      let sig = `function ${entry.name}(${inputs})`;
      if (entry.stateMutability === "view" || entry.stateMutability === "pure")
        sig += ` ${entry.stateMutability}`;
      if (outputs) sig += ` returns (${outputs})`;
      return sig;
    }
    if (entry.type === "event") {
      const inputs = entry.inputs
        .map((p) => `${p.type}${p.indexed ? " indexed" : ""} ${p.name}`.trim())
        .join(", ");
      return `event ${entry.name}(${inputs})`;
    }
    if (entry.type === "error") {
      const inputs = entry.inputs
        .map((p) => `${p.type} ${p.name}`.trim())
        .join(", ");
      return `error ${entry.name}(${inputs})`;
    }
    return "";
  });
}

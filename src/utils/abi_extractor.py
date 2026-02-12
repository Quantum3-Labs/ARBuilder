"""
ABI extractor for Stylus (Rust) smart contracts.

Parses #[public] impl blocks from lib.rs to produce a JSON ABI
compatible with viem's parseAbi format and Ethereum standard ABI.

Works without Docker — pure regex parsing.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple


# Rust → Solidity type mapping
RUST_TO_SOL_TYPES = {
    "U256": "uint256",
    "U128": "uint128",
    "U64": "uint64",
    "U32": "uint32",
    "U16": "uint16",
    "U8": "uint8",
    "I256": "int256",
    "I128": "int128",
    "I64": "int64",
    "I32": "int32",
    "I16": "int16",
    "I8": "int8",
    "Address": "address",
    "bool": "bool",
    "String": "string",
    "Vec<u8>": "bytes",
    "FixedBytes<32>": "bytes32",
    "FixedBytes<20>": "bytes20",
    "FixedBytes<4>": "bytes4",
    "u8": "uint8",
    "u16": "uint16",
    "u32": "uint32",
    "u64": "uint64",
    "u128": "uint128",
    "i8": "int8",
    "i16": "int16",
    "i32": "int32",
    "i64": "int64",
    "i128": "int128",
}


def _rust_type_to_sol(rust_type: str) -> str:
    """Convert a Rust type to its Solidity equivalent."""
    rust_type = rust_type.strip()

    # Direct mapping
    if rust_type in RUST_TO_SOL_TYPES:
        return RUST_TO_SOL_TYPES[rust_type]

    # Vec<T> → T[]
    vec_match = re.match(r"Vec<(.+)>", rust_type)
    if vec_match:
        inner = _rust_type_to_sol(vec_match.group(1))
        return f"{inner}[]"

    # FixedBytes<N> → bytesN
    fb_match = re.match(r"FixedBytes<(\d+)>", rust_type)
    if fb_match:
        return f"bytes{fb_match.group(1)}"

    # Fallback: assume uint256 for unknown types
    return "uint256"


def _parse_fn_params(params_str: str) -> List[Dict[str, str]]:
    """Parse function parameters, skipping &self/&mut self."""
    params = []
    if not params_str.strip():
        return params

    # Split on commas, respecting generics
    parts = []
    depth = 0
    current = ""
    for ch in params_str:
        if ch in "<(":
            depth += 1
        elif ch in ">)":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(current.strip())
            current = ""
            continue
        current += ch
    if current.strip():
        parts.append(current.strip())

    for part in parts:
        part = part.strip()
        # Skip self references
        if part in ("&self", "&mut self", "self"):
            continue

        # Parse "name: Type"
        if ":" in part:
            name, type_str = part.split(":", 1)
            name = name.strip()
            type_str = type_str.strip()
            sol_type = _rust_type_to_sol(type_str)
            params.append({"name": name, "type": sol_type})

    return params


def _parse_return_type(return_str: str) -> List[Dict[str, str]]:
    """Parse return type to Solidity output types."""
    return_str = return_str.strip()

    if not return_str or return_str == "()" or return_str == "":
        return []

    # Handle Result<T, Vec<u8>> — extract T
    result_match = re.match(r"Result<(.+),\s*Vec<u8>>", return_str)
    if result_match:
        return_str = result_match.group(1).strip()

    # Handle tuple returns (T1, T2, ...)
    if return_str.startswith("(") and return_str.endswith(")"):
        inner = return_str[1:-1]
        types = []
        depth = 0
        current = ""
        for ch in inner:
            if ch in "<(":
                depth += 1
            elif ch in ">)":
                depth -= 1
            elif ch == "," and depth == 0:
                types.append(current.strip())
                current = ""
                continue
            current += ch
        if current.strip():
            types.append(current.strip())

        return [{"name": "", "type": _rust_type_to_sol(t)} for t in types]

    # Single return
    sol_type = _rust_type_to_sol(return_str)
    return [{"name": "", "type": sol_type}]


def extract_abi_from_code(lib_rs: str) -> List[Dict[str, Any]]:
    """Extract a JSON ABI from Stylus lib.rs source code.

    Scans #[public] impl blocks for pub fn signatures and determines
    mutability from &self vs &mut self vs #[payable].

    Also parses sol! { event ... } and sol! { error ... } blocks.

    Args:
        lib_rs: Contents of the Stylus lib.rs file.

    Returns:
        List of ABI entries compatible with Ethereum JSON ABI format.
    """
    abi: List[Dict[str, Any]] = []

    # 1. Parse events from sol! blocks
    # Match sol! { event Name(type1 indexed param1, ...); }
    event_pattern = re.compile(
        r"sol!\s*\{[^}]*?event\s+(\w+)\s*\(([^)]*)\)\s*;",
        re.DOTALL,
    )
    for match in event_pattern.finditer(lib_rs):
        event_name = match.group(1)
        params_str = match.group(2).strip()
        inputs = []
        if params_str:
            for param in params_str.split(","):
                param = param.strip()
                indexed = "indexed" in param
                param = param.replace("indexed", "").strip()
                parts = param.split()
                if len(parts) >= 2:
                    sol_type = parts[0]
                    name = parts[1]
                    inputs.append({
                        "name": name,
                        "type": sol_type,
                        "indexed": indexed,
                    })
                elif len(parts) == 1:
                    inputs.append({
                        "name": "",
                        "type": parts[0],
                        "indexed": indexed,
                    })
        abi.append({
            "type": "event",
            "name": event_name,
            "inputs": inputs,
        })

    # 2. Parse errors from sol! blocks
    error_pattern = re.compile(
        r"sol!\s*\{[^}]*?error\s+(\w+)\s*\(([^)]*)\)\s*;",
        re.DOTALL,
    )
    for match in error_pattern.finditer(lib_rs):
        error_name = match.group(1)
        params_str = match.group(2).strip()
        inputs = []
        if params_str:
            for param in params_str.split(","):
                param = param.strip()
                parts = param.split()
                if len(parts) >= 2:
                    inputs.append({"name": parts[1], "type": parts[0]})
                elif len(parts) == 1:
                    inputs.append({"name": "", "type": parts[0]})
        abi.append({
            "type": "error",
            "name": error_name,
            "inputs": inputs,
        })

    # 3. Parse functions from #[public] impl blocks
    # Find all #[public] impl blocks
    public_impl_pattern = re.compile(
        r"#\[public\]\s*impl\s+\w+\s*\{([\s\S]*?)^\}",
        re.MULTILINE,
    )
    for impl_match in public_impl_pattern.finditer(lib_rs):
        impl_body = impl_match.group(1)

        # Find all pub fn declarations
        # Handles: #[payable] pub fn name(&self, ...) -> ReturnType {
        fn_pattern = re.compile(
            r"(#\[payable\]\s*)?pub\s+fn\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^\{]+))?\s*\{",
        )
        for fn_match in fn_pattern.finditer(impl_body):
            is_payable = fn_match.group(1) is not None
            fn_name = fn_match.group(2)
            params_str = fn_match.group(3)
            return_str = fn_match.group(4) or ""

            # Determine state mutability
            if is_payable:
                state_mutability = "payable"
            elif "&mut self" in params_str:
                state_mutability = "nonpayable"
            elif "&self" in params_str:
                state_mutability = "view"
            else:
                state_mutability = "nonpayable"

            inputs = _parse_fn_params(params_str)
            outputs = _parse_return_type(return_str.strip())

            abi.append({
                "type": "function",
                "name": fn_name,
                "inputs": inputs,
                "outputs": outputs,
                "stateMutability": state_mutability,
            })

    return abi


def abi_to_viem_human_readable(abi: List[Dict[str, Any]]) -> List[str]:
    """Convert JSON ABI to viem human-readable format for parseAbi().

    Args:
        abi: Standard Ethereum JSON ABI list.

    Returns:
        List of human-readable ABI strings for viem's parseAbi().
    """
    lines = []
    for entry in abi:
        entry_type = entry.get("type", "function")

        if entry_type == "function":
            name = entry["name"]
            inputs = ", ".join(
                f"{p['type']} {p['name']}" if p.get("name") else p["type"]
                for p in entry.get("inputs", [])
            )
            outputs = entry.get("outputs", [])
            mutability = entry.get("stateMutability", "nonpayable")

            sig = f"function {name}({inputs})"
            if mutability in ("view", "pure"):
                sig += f" {mutability}"
            if outputs:
                out_types = ", ".join(
                    f"{p['type']} {p['name']}" if p.get("name") else p["type"]
                    for p in outputs
                )
                sig += f" returns ({out_types})"
            lines.append(sig)

        elif entry_type == "event":
            name = entry["name"]
            inputs = ", ".join(
                f"{p['type']} {'indexed ' if p.get('indexed') else ''}{p.get('name', '')}".strip()
                for p in entry.get("inputs", [])
            )
            lines.append(f"event {name}({inputs})")

        elif entry_type == "error":
            name = entry["name"]
            inputs = ", ".join(
                f"{p['type']} {p.get('name', '')}".strip()
                for p in entry.get("inputs", [])
            )
            lines.append(f"error {name}({inputs})")

    return lines


def abi_to_json_string(abi: List[Dict[str, Any]], indent: int = 2) -> str:
    """Serialize ABI to JSON string."""
    return json.dumps(abi, indent=indent)

"""
Stylus SDK Version Manager - Single source of truth loader.

This module provides utilities for managing Stylus SDK versions across
both Python (local ChromaDB) and TypeScript (Cloudflare Vectorize) codebases.
Both systems read from the same shared/stylus-versions.json config file.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

# Path to shared config (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent
SHARED_CONFIG_PATH = PROJECT_ROOT / "shared" / "stylus-versions.json"


@lru_cache(maxsize=1)
def load_version_config() -> dict:
    """
    Load version configuration from shared JSON file.

    Returns:
        Dict containing version configuration.

    Raises:
        FileNotFoundError: If config file doesn't exist.
    """
    if not SHARED_CONFIG_PATH.exists():
        raise FileNotFoundError(f"Version config not found: {SHARED_CONFIG_PATH}")

    with open(SHARED_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_main_version() -> str:
    """Get the main (default) supported SDK version."""
    return load_version_config()["main_version"]


def get_minimum_version() -> str:
    """Get the minimum supported SDK version."""
    return load_version_config()["minimum_version"]


def is_version_supported(version: str) -> bool:
    """
    Check if a version is at or above minimum.

    Args:
        version: Version string to check (e.g., "0.8.4")

    Returns:
        True if version >= minimum_version
    """
    config = load_version_config()
    return compare_versions(version, config["minimum_version"]) >= 0


def is_version_deprecated(version: str) -> bool:
    """
    Check if a version is below minimum (deprecated).

    Args:
        version: Version string to check

    Returns:
        True if version < deprecated_below threshold
    """
    config = load_version_config()
    return compare_versions(version, config["deprecated_below"]) < 0


def get_version_patterns(version: str) -> dict:
    """
    Get code patterns for a specific SDK version.

    Args:
        version: Target SDK version (e.g., "0.9.0")

    Returns:
        Dict with patterns: attributes, imports, error_handling, cfg_attr, etc.
    """
    config = load_version_config()
    # Map version to major.minor
    major_minor = ".".join(version.split(".")[:2])
    patterns = config["version_patterns"].get(major_minor)

    if patterns:
        return patterns

    # Default to main version's patterns
    main_version = config["main_version"]
    main_major_minor = ".".join(main_version.split(".")[:2])
    return config["version_patterns"].get(main_major_minor, config["version_patterns"]["0.9"])


def get_alloy_primitives_version(sdk_version: str) -> str:
    """
    Get compatible alloy-primitives version for SDK version.

    Args:
        sdk_version: Stylus SDK version

    Returns:
        Compatible alloy-primitives version string
    """
    config = load_version_config()
    version_info = config["versions"].get(sdk_version)

    if version_info:
        return version_info["alloy_primitives"]

    # Default to main version's alloy-primitives
    main = config["main_version"]
    return config["versions"][main]["alloy_primitives"]


def get_alloy_sol_types_version(sdk_version: str) -> str:
    """
    Get compatible alloy-sol-types version for SDK version.

    Args:
        sdk_version: Stylus SDK version

    Returns:
        Compatible alloy-sol-types version string
    """
    config = load_version_config()
    version_info = config["versions"].get(sdk_version)

    if version_info:
        return version_info.get("alloy_sol_types", version_info["alloy_primitives"])

    # Default to main version's alloy-sol-types
    main = config["main_version"]
    return config["versions"][main].get(
        "alloy_sol_types", config["versions"][main]["alloy_primitives"]
    )


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two semantic versions.

    Args:
        v1: First version string
        v2: Second version string

    Returns:
        -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
    """

    def parse(v: str) -> tuple:
        # Strip version prefixes like ^, ~, >=, etc.
        cleaned = re.sub(r"^[\^~>=<]+", "", v)
        parts = cleaned.split(".")
        return tuple(int(x) for x in parts[:3] if x.isdigit())

    p1, p2 = parse(v1), parse(v2)

    # Pad with zeros for comparison
    while len(p1) < 3:
        p1 = p1 + (0,)
    while len(p2) < 3:
        p2 = p2 + (0,)

    if p1 < p2:
        return -1
    elif p1 > p2:
        return 1
    return 0


def detect_version_from_cargo_toml(cargo_content: str) -> Optional[str]:
    """
    Detect stylus-sdk version from Cargo.toml content.

    Supports multiple formats:
    - Simple: stylus-sdk = "0.9.0"
    - Complex: stylus-sdk = { version = "0.9.0", features = [...] }
    - Workspace: stylus-sdk.workspace = true (returns None, needs workspace lookup)

    Args:
        cargo_content: Raw content of Cargo.toml file

    Returns:
        Version string if found, None otherwise
    """
    if not cargo_content:
        return None

    # Pattern 1: Simple format - stylus-sdk = "0.9.0"
    simple_pattern = r'stylus-sdk\s*=\s*"([^"]+)"'
    match = re.search(simple_pattern, cargo_content)
    if match:
        return match.group(1)

    # Pattern 2: Complex format - stylus-sdk = { version = "0.9.0", ... }
    complex_pattern = r'stylus-sdk\s*=\s*\{[^}]*version\s*=\s*"([^"]+)"'
    match = re.search(complex_pattern, cargo_content, re.DOTALL)
    if match:
        return match.group(1)

    # Pattern 3: Check workspace root for version
    # stylus-sdk = { workspace = true } in member Cargo.toml
    # [workspace.dependencies] stylus-sdk = "0.9.0" in root
    workspace_member_pattern = r"stylus-sdk\s*=\s*\{[^}]*workspace\s*=\s*true"
    if re.search(workspace_member_pattern, cargo_content):
        # Look for workspace dependencies section
        workspace_dep_pattern = r'\[workspace\.dependencies\][^\[]*stylus-sdk\s*=\s*"([^"]+)"'
        match = re.search(workspace_dep_pattern, cargo_content, re.DOTALL)
        if match:
            return match.group(1)

        # Also try complex workspace dependency format
        workspace_dep_complex = (
            r'\[workspace\.dependencies\][^\[]*stylus-sdk\s*=\s*\{[^}]*version\s*=\s*"([^"]+)"'
        )
        match = re.search(workspace_dep_complex, cargo_content, re.DOTALL)
        if match:
            return match.group(1)

    return None


def get_deprecation_warning(version: str) -> Optional[str]:
    """
    Get deprecation warning message for a version.

    Args:
        version: SDK version to check

    Returns:
        Warning message if deprecated, None otherwise
    """
    if not is_version_deprecated(version):
        return None

    config = load_version_config()
    template = config.get("deprecation_warnings", {}).get("below_minimum", "")

    if template:
        return template.format(version=version, minimum=config["minimum_version"])

    return f"SDK version {version} is deprecated. Minimum supported: {config['minimum_version']}"


def get_version_info(version: str) -> Optional[dict]:
    """
    Get full version info for a specific version.

    Args:
        version: SDK version

    Returns:
        Version info dict or None if not found
    """
    config = load_version_config()
    return config["versions"].get(version)


def list_supported_versions() -> list[str]:
    """
    Get list of all known SDK versions.

    Returns:
        List of version strings, sorted newest first
    """
    config = load_version_config()
    versions = list(config["versions"].keys())
    versions.sort(key=lambda v: tuple(int(x) for x in v.split(".")), reverse=True)
    return versions


# ──────────────────────────────────────────────────────────────
# VERSION TRANSFORMS
# Centralized transform rules consumed by processor, templates,
# fix_code, and fork_and_migrate.
# ──────────────────────────────────────────────────────────────

# Storage type mapping: 0.9.x StorageX names ↔ 0.10.x Solidity names
STORAGE_TYPE_MAP_FORWARD = {
    "StorageAddress": "address",
    "StorageU256": "uint256",
    "StorageU128": "uint128",
    "StorageU64": "uint64",
    "StorageU32": "uint32",
    "StorageU16": "uint16",
    "StorageU8": "uint8",
    "StorageI256": "int256",
    "StorageBool": "bool",
    "StorageB256": "bytes32",
    "StorageString": "string",
    "StorageBytes": "bytes",
}

STORAGE_TYPE_MAP_REVERSE = {v: k for k, v in STORAGE_TYPE_MAP_FORWARD.items()}

# Transform rules from 0.9.x → 0.10.x
VERSION_TRANSFORMS: dict[tuple[str, str], list[dict]] = {
    ("0.9", "0.10"): [
        # 1. msg::sender() → self.vm().msg_sender()
        {"pattern": r"msg::sender\(\)", "replacement": "self.vm().msg_sender()"},
        # 2. msg::value() → self.vm().msg_value()
        {"pattern": r"msg::value\(\)", "replacement": "self.vm().msg_value()"},
        # 3. evm::log( → self.vm().log(
        {"pattern": r"evm::log\(", "replacement": "self.vm().log("},
        # 4. Remove use stylus_sdk::evm / use stylus_sdk::msg
        {"pattern": r"^use stylus_sdk::evm.*;\s*$", "replacement": "", "flags": "multiline"},
        {"pattern": r"^use stylus_sdk::msg.*;\s*$", "replacement": "", "flags": "multiline"},
        # 5. sol! { interface → sol_interface! { interface
        {"pattern": r"sol!\s*\{\s*(interface\b)", "replacement": r"sol_interface! { \1"},
        # 6. Fix transfer_eth import path
        {
            "pattern": r"use stylus_sdk::call::transfer_eth;",
            "replacement": "use stylus_sdk::call::transfer::transfer_eth;",
        },
        # 7. self.transfer_eth(to, amount) → transfer_eth(self.vm(), to, amount)
        {
            "pattern": r"self\.transfer_eth\(([^)]+)\)",
            "replacement": r"transfer_eth(self.vm(), \1)",
        },
        # 8. transfer_eth(self, ...) → transfer_eth(self.vm(), ...)
        {"pattern": r"transfer_eth\(self,\s*", "replacement": "transfer_eth(self.vm(), "},
        # 9. .getter( → .get(
        {"pattern": r"\.getter\(", "replacement": ".get("},
        # 10. print_abi() → print_from_args()
        {"pattern": r"print_abi\(\)", "replacement": "print_from_args()"},
        # 11. Storage type transforms (handled specially)
        {"type": "storage_type_forward"},
    ],
}


def _to_major_minor(version: str) -> str:
    """Convert a version string to major.minor format."""
    parts = re.sub(r"^[\^~>=<]+", "", version).split(".")
    return f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else version


def is_at_least_010(version: str) -> bool:
    """Check if a major.minor or full version string is >= 0.10.

    Use this instead of string comparison (\"0.9\" >= \"0.10\" is True
    in Python due to lexicographic ordering, which is wrong).
    """
    mm = _to_major_minor(version)
    parts = mm.split(".")
    try:
        return (int(parts[0]), int(parts[1])) >= (0, 10)
    except (ValueError, IndexError):
        return True  # Default to assuming 0.10+


def get_version_transforms(from_version: str, to_version: str) -> list[dict]:
    """Get transform rules between two SDK versions.

    Args:
        from_version: Source SDK version (e.g., "0.9.0", "0.9.2")
        to_version: Target SDK version (e.g., "0.10.0")

    Returns:
        List of transform rule dicts. Empty list if no transforms needed.
    """
    from_mm = _to_major_minor(from_version)
    to_mm = _to_major_minor(to_version)

    if from_mm == to_mm:
        return []

    return VERSION_TRANSFORMS.get((from_mm, to_mm), [])


def _apply_storage_type_forward(code: str) -> str:
    """Transform 0.9.x StorageX types to 0.10.x Solidity types.

    Handles: StorageMap<K, V> → mapping(k => v), StorageVec<T> → t[],
    and standalone StorageX → solidity_type.
    """

    # StorageMap<K, V> → mapping(k => v)
    def _replace_storage_map(match: re.Match) -> str:
        key_type = match.group(1).strip()
        val_type = match.group(2).strip()
        for old, new in STORAGE_TYPE_MAP_FORWARD.items():
            key_type = key_type.replace(old, new)
            val_type = val_type.replace(old, new)
        return f"mapping({key_type} => {val_type})"

    code = re.sub(
        r"StorageMap\s*<\s*([^,>]+)\s*,\s*([^>]+)\s*>",
        _replace_storage_map,
        code,
    )

    # StorageVec<T> → t[]
    def _replace_storage_vec(match: re.Match) -> str:
        inner = match.group(1).strip()
        for old, new in STORAGE_TYPE_MAP_FORWARD.items():
            inner = inner.replace(old, new)
        return f"{inner}[]"

    code = re.sub(
        r"StorageVec\s*<\s*([^>]+)\s*>",
        _replace_storage_vec,
        code,
    )

    # Standalone StorageX → solidity_type
    for old, new in STORAGE_TYPE_MAP_FORWARD.items():
        code = re.sub(rf"\b{old}\b", new, code)

    return code


def _apply_storage_type_reverse(code: str) -> str:
    """Transform 0.10.x Solidity types back to 0.9.x StorageX types.

    Only applies inside sol_storage! blocks. Handles:
    mapping(K => V) → StorageMap<StorageK, StorageV>,
    T[] → StorageVec<StorageT>,
    and simple types like address → StorageAddress.
    """
    # Find sol_storage! block boundaries
    sol_storage_match = re.search(r"(sol_storage!\s*\{)", code)
    if not sol_storage_match:
        return code

    start = sol_storage_match.start()
    # Find matching closing brace
    depth = 0
    end = start
    for i in range(start, len(code)):
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    before = code[:start]
    block = code[start:end]
    after = code[end:]

    # mapping(K => V) → StorageMap<StorageK, StorageV>
    def _reverse_mapping(match: re.Match) -> str:
        key_type = match.group(1).strip()
        val_type = match.group(2).strip()
        for sol, storage in STORAGE_TYPE_MAP_REVERSE.items():
            key_type = re.sub(rf"\b{re.escape(sol)}\b", storage, key_type)
            val_type = re.sub(rf"\b{re.escape(sol)}\b", storage, val_type)
        return f"StorageMap<{key_type}, {val_type}>"

    block = re.sub(
        r"mapping\(\s*(\w+)\s*=>\s*(\w+)\s*\)",
        _reverse_mapping,
        block,
    )

    # T[] → StorageVec<StorageT>
    def _reverse_vec(match: re.Match) -> str:
        inner = match.group(1).strip()
        for sol, storage in STORAGE_TYPE_MAP_REVERSE.items():
            inner = re.sub(rf"\b{re.escape(sol)}\b", storage, inner)
        return f"StorageVec<{inner}>"

    block = re.sub(
        r"\b(\w+)\[\]",
        _reverse_vec,
        block,
    )

    # Simple types: address → StorageAddress, uint256 → StorageU256, etc.
    # Only inside field declarations (type fieldname;)
    for sol, storage in STORAGE_TYPE_MAP_REVERSE.items():
        block = re.sub(
            rf"\b{re.escape(sol)}\b(\s+\w+\s*;)",
            rf"{storage}\1",
            block,
        )

    return before + block + after


def apply_version_transforms(code: str, from_version: str, to_version: str) -> str:
    """Apply version transforms to code.

    Args:
        code: Source code to transform.
        from_version: Source SDK version (e.g., "0.9.0").
        to_version: Target SDK version (e.g., "0.10.0").

    Returns:
        Transformed code string.
    """
    from_mm = _to_major_minor(from_version)
    to_mm = _to_major_minor(to_version)

    if from_mm == to_mm:
        return code

    # Forward transforms (0.9 → 0.10)
    transforms = VERSION_TRANSFORMS.get((from_mm, to_mm))
    if transforms:
        for rule in transforms:
            if rule.get("type") == "storage_type_forward":
                code = _apply_storage_type_forward(code)
            elif "pattern" in rule:
                flags = re.MULTILINE if rule.get("flags") == "multiline" else 0
                code = re.sub(rule["pattern"], rule["replacement"], code, flags=flags)
        return code

    # Reverse transforms (0.10 → 0.9): apply inverse of forward rules
    reverse_key = (to_mm, from_mm)
    transforms = VERSION_TRANSFORMS.get(reverse_key)
    if transforms:
        for rule in reversed(transforms):
            if rule.get("type") == "storage_type_forward":
                code = _apply_storage_type_reverse(code)
            elif "pattern" in rule:
                # Swap pattern and replacement for reverse
                # For simple literal replacements, swap directly
                search = rule["replacement"]
                # The original "pattern" is a regex string — unescape it
                # to get the literal text for use as a replacement value.
                replace_with = (
                    rule["pattern"]
                    .replace(r"\(", "(")
                    .replace(r"\)", ")")
                    .replace(r"\.", ".")
                    .replace(r"\{", "{")
                    .replace(r"\}", "}")
                    .replace(r"\[", "[")
                    .replace(r"\]", "]")
                )

                # Skip rules that can't be reversed (regex groups, empty replacements)
                if not search or r"\1" in search or r"\g<" in search:
                    continue
                # For multiline rules (import removal), reverse = add back, handled below
                if rule.get("flags") == "multiline" and not search:
                    continue
                code = code.replace(search, replace_with)

        # Add back evm/msg imports if they were removed
        if "self.vm().msg_sender()" not in code and "msg::sender()" in code:
            if "use stylus_sdk::msg" not in code:
                code = re.sub(
                    r"(use stylus_sdk::prelude::\*;)",
                    r"\1\nuse stylus_sdk::msg;",
                    code,
                )
        if "self.vm().log(" not in code and "evm::log(" in code:
            if "use stylus_sdk::evm" not in code:
                code = re.sub(
                    r"(use stylus_sdk::prelude::\*;)",
                    r"\1\nuse stylus_sdk::evm;",
                    code,
                )

        return code

    # No transforms found
    return code


def get_cargo_deps_for_version(version: str) -> dict:
    """Get Cargo.toml dependency versions for a given SDK version.

    Args:
        version: Target stylus-sdk version (e.g., "0.10.0", "0.9.0").

    Returns:
        Dict with keys: stylus_sdk, alloy_primitives, alloy_sol_types, crate_type.
    """
    config = load_version_config()
    version_info = config["versions"].get(version)
    mm = _to_major_minor(version)
    patterns = config["version_patterns"].get(mm, {})

    alloy_prim = version_info["alloy_primitives"] if version_info else "1.0.1"
    alloy_sol = version_info.get("alloy_sol_types", alloy_prim) if version_info else "1.0.1"
    crate_type = patterns.get("crate_type", ["lib", "cdylib"])

    return {
        "stylus_sdk": version,
        "alloy_primitives": alloy_prim,
        "alloy_sol_types": alloy_sol,
        "crate_type": crate_type,
    }

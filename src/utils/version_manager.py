"""
Stylus SDK Version Manager - Single source of truth loader.

This module provides utilities for managing Stylus SDK versions across
both Python (local ChromaDB) and TypeScript (Cloudflare Vectorize) codebases.
Both systems read from the same shared/stylus-versions.json config file.
"""

import json
import re
from pathlib import Path
from typing import Optional
from functools import lru_cache


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
    return config["versions"][main].get("alloy_sol_types", config["versions"][main]["alloy_primitives"])


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
        cleaned = re.sub(r'^[\^~>=<]+', '', v)
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
    workspace_member_pattern = r'stylus-sdk\s*=\s*\{[^}]*workspace\s*=\s*true'
    if re.search(workspace_member_pattern, cargo_content):
        # Look for workspace dependencies section
        workspace_dep_pattern = r'\[workspace\.dependencies\][^\[]*stylus-sdk\s*=\s*"([^"]+)"'
        match = re.search(workspace_dep_pattern, cargo_content, re.DOTALL)
        if match:
            return match.group(1)

        # Also try complex workspace dependency format
        workspace_dep_complex = r'\[workspace\.dependencies\][^\[]*stylus-sdk\s*=\s*\{[^}]*version\s*=\s*"([^"]+)"'
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
        return template.format(
            version=version,
            minimum=config["minimum_version"]
        )

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

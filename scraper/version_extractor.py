"""
Version Extractor for ARBuilder.
Extracts SDK versions from crates.io and Cargo.toml files,
and detects deprecated patterns in Stylus code.
"""

import re
from pathlib import Path
from typing import Optional

import httpx
import toml
from rich.console import Console

console = Console()

CRATES_IO_API = "https://crates.io/api/v1/crates"

# Deprecated patterns and their replacements (pattern, message)
DEPRECATED_PATTERNS = [
    (r"#\[external\]", "#[external] is deprecated, use #[public] (since v0.7)"),
    (r'stylus-sdk\s*=\s*"0\.[0-5]\.', "stylus-sdk < 0.6 is deprecated"),
    (r'mini-alloc\s*=\s*"', "mini-alloc is deprecated, use stylus-sdk/mini-alloc feature"),
    (r"use stylus_sdk::storage::StorageVec;", "StorageVec import path may have changed"),
]

# Current known good patterns
CURRENT_PATTERNS = [
    "#[public]",
    "#[entrypoint]",
    "stylus_sdk::prelude::*",
]


async def get_latest_sdk_version() -> Optional[str]:
    """Fetch the latest stylus-sdk version from crates.io."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CRATES_IO_API}/stylus-sdk",
                headers={"User-Agent": "ARBuilder/1.0"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            version = data["crate"]["max_stable_version"]
            console.print(f"[green]Latest stylus-sdk version: {version}[/green]")
            return version
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Failed to fetch from crates.io: {e}[/red]")
        return None
    except Exception as e:
        console.print(f"[red]Error fetching SDK version: {e}[/red]")
        return None


def get_latest_sdk_version_sync() -> Optional[str]:
    """Synchronous version of get_latest_sdk_version."""
    try:
        with httpx.Client() as client:
            response = client.get(
                f"{CRATES_IO_API}/stylus-sdk",
                headers={"User-Agent": "ARBuilder/1.0"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            version = data["crate"]["max_stable_version"]
            return version
    except Exception as e:
        console.print(f"[red]Error fetching SDK version: {e}[/red]")
        return None


def extract_sdk_version_from_cargo(cargo_path: Path) -> Optional[str]:
    """
    Extract stylus-sdk version from a Cargo.toml file.

    Args:
        cargo_path: Path to Cargo.toml file

    Returns:
        Version string (e.g., "0.9.0") or None if not found
    """
    try:
        data = toml.load(cargo_path)
        deps = data.get("dependencies", {})

        # Check for stylus-sdk dependency
        sdk_dep = deps.get("stylus-sdk")

        if sdk_dep is None:
            return None

        if isinstance(sdk_dep, str):
            # Simple version string: stylus-sdk = "0.9.0"
            return sdk_dep.strip('"\'')
        elif isinstance(sdk_dep, dict):
            # Complex dependency: stylus-sdk = { version = "0.9.0", features = [...] }
            version = sdk_dep.get("version", "")
            return version.strip('"\'') if version else None

        return None
    except Exception as e:
        console.print(f"[yellow]Could not parse {cargo_path}: {e}[/yellow]")
        return None


def extract_sdk_version_from_repo(repo_dir: Path) -> Optional[str]:
    """
    Find and extract stylus-sdk version from any Cargo.toml in the repository.
    Prefers root Cargo.toml, falls back to any found in the tree.

    Args:
        repo_dir: Path to repository root

    Returns:
        Version string or None if not found
    """
    # Try root Cargo.toml first
    root_cargo = repo_dir / "Cargo.toml"
    if root_cargo.exists():
        version = extract_sdk_version_from_cargo(root_cargo)
        if version:
            return version

    # Search for Cargo.toml files in subdirectories
    for cargo_path in repo_dir.rglob("Cargo.toml"):
        if "target" in cargo_path.parts:
            continue
        version = extract_sdk_version_from_cargo(cargo_path)
        if version:
            return version

    return None


def detect_deprecated_patterns(content: str) -> list[str]:
    """
    Detect deprecated Stylus patterns in code content.

    Args:
        content: Source code content to analyze

    Returns:
        List of deprecation warning messages
    """
    warnings = []

    for pattern, message in DEPRECATED_PATTERNS:
        if re.search(pattern, content):
            warnings.append(message)

    return warnings


def has_current_patterns(content: str) -> bool:
    """
    Check if content uses current/modern Stylus patterns.

    Args:
        content: Source code content to analyze

    Returns:
        True if any current patterns are found
    """
    for pattern in CURRENT_PATTERNS:
        if pattern in content:
            return True
    return False


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two semantic version strings.

    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2
    """
    def parse_version(v: str) -> tuple[int, ...]:
        # Remove any prefix like ^ or ~ and parse
        v = v.lstrip("^~>=<")
        parts = v.split(".")
        return tuple(int(p) for p in parts[:3])

    try:
        v1 = parse_version(version1)
        v2 = parse_version(version2)

        for a, b in zip(v1, v2):
            if a < b:
                return -1
            elif a > b:
                return 1
        return 0
    except (ValueError, IndexError):
        return 0


def is_version_current(version: str, latest: str, max_minor_behind: int = 2) -> bool:
    """
    Check if a version is considered current (not too old).

    Args:
        version: Version to check
        latest: Latest available version
        max_minor_behind: How many minor versions behind is acceptable

    Returns:
        True if version is current enough
    """
    try:
        v_parts = version.lstrip("^~>=<").split(".")
        l_parts = latest.lstrip("^~>=<").split(".")

        v_major, v_minor = int(v_parts[0]), int(v_parts[1])
        l_major, l_minor = int(l_parts[0]), int(l_parts[1])

        # Must be same major version
        if v_major != l_major:
            return False

        # Must be within max_minor_behind of latest
        return (l_minor - v_minor) <= max_minor_behind

    except (ValueError, IndexError):
        return True  # Assume current if we can't parse


if __name__ == "__main__":
    import asyncio

    async def test():
        # Test fetching latest version
        latest = await get_latest_sdk_version()
        print(f"Latest SDK: {latest}")

        # Test deprecated pattern detection
        test_code = '''
        #[external]
        fn old_style() {}

        stylus-sdk = "0.5.0"
        '''
        warnings = detect_deprecated_patterns(test_code)
        print(f"Deprecation warnings: {warnings}")

    asyncio.run(test())

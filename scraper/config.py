"""
Configuration for ARBuilder data scraping.

Thin wrapper around sources.json — the single source of truth for all data sources.
This module loads sources.json and provides backward-compatible helpers for existing
consumers (scraper.py, github_scraper.py, processor.py, etc.).

See sources.json for the full source registry and
docs/plans/2026-02-22-single-source-of-truth-design.md for the design rationale.
"""

import json
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# LOAD SOURCES.JSON
# ──────────────────────────────────────────────────────────────

_SOURCES_PATH = Path(__file__).parent.parent / "sources.json"
_DATA = json.loads(_SOURCES_PATH.read_text())
SOURCES = _DATA["sources"]

# SDK version constants
_SDK_CONFIG = _DATA.get("sdkConfig", {})
MAIN_STYLUS_SDK_VERSION = _SDK_CONFIG.get("mainVersion", "0.10.0")
MIN_STYLUS_SDK_VERSION = _SDK_CONFIG.get("minVersion", "0.8.0")
DEPRECATED_BELOW = _SDK_CONFIG.get("deprecatedBelow", "0.8.0")


# ──────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────


def get_all_config_repo_urls() -> set[str]:
    """Return the set of all GitHub repo URLs from sources.json."""
    return {s["url"] for s in SOURCES if s["type"] == "github"}


def get_config_repo_info() -> dict[str, dict]:
    """Return a mapping of repo URL -> config info.

    Each value contains: category, subcategory,
    sdk_version, verified, forked_from, versions.
    """
    info = {}
    for s in SOURCES:
        if s["type"] != "github":
            continue
        # For versioned repos, use the first version's sdkVersion
        versions = s.get("versions", [])
        sdk_version = ""
        if versions:
            sdk_version = versions[0].get("sdkVersion", "")
        elif s.get("sdkVersion"):
            sdk_version = s["sdkVersion"]
        info[s["url"]] = {
            "category": s["category"],
            "subcategory": s["subcategory"],
            "sdk_version": sdk_version,
            "verified": s.get("verified", ""),
            "forked_from": s.get("forkedFrom", ""),
            "versions": versions,
        }
    return info


def get_sources_by_milestone(milestone: str) -> list[dict]:
    """Return all sources for a given milestone."""
    return [s for s in SOURCES if s["milestone"] == milestone]


def get_sources_by_type(source_type: str) -> list[dict]:
    """Return all sources of a given type ('documentation' or 'github')."""
    return [s for s in SOURCES if s["type"] == source_type]


# ──────────────────────────────────────────────────────────────
# BACKWARD COMPATIBILITY
# Reconstructed dicts for existing consumers
# ──────────────────────────────────────────────────────────────


def _build_docs_dict(category: str) -> dict[str, list[str]]:
    """Build a {subcategory: [url, ...]} dict for documentation sources."""
    result: dict[str, list[str]] = {}
    for s in SOURCES:
        if s["type"] == "documentation" and s["category"] == category:
            subcat = s["subcategory"]
            if subcat not in result:
                result[subcat] = []
            result[subcat].append(s["url"])
    return result


def _build_project_examples_dict(category: str) -> dict[str, list[dict]]:
    """Build a {subcategory: [{url, sdk_version, ...}, ...]} dict for GitHub repos."""
    result: dict[str, list[dict]] = {}
    for s in SOURCES:
        if s["type"] != "github" or s["category"] != category:
            continue
        subcat = s["subcategory"]
        if subcat not in result:
            result[subcat] = []
        versions = s.get("versions", [])
        sdk_version = ""
        if versions:
            sdk_version = versions[0].get("sdkVersion", "")
        elif s.get("sdkVersion"):
            sdk_version = s["sdkVersion"]
        entry = {
            "url": s["url"],
            "sdk_version": sdk_version,
        }
        if s.get("verified"):
            entry["verified"] = s["verified"]
        if s.get("forkedFrom"):
            entry["forked_from"] = s["forkedFrom"]
        if s.get("note"):
            entry["note"] = s["note"]
        result[subcat].append(entry)
    return result


def _build_project_urls_dict(category: str) -> dict[str, list[str]]:
    """Build a {subcategory: [url, ...]} dict for GitHub repos (URL-only)."""
    result: dict[str, list[str]] = {}
    for s in SOURCES:
        if s["type"] == "github" and s["category"] == category:
            subcat = s["subcategory"]
            if subcat not in result:
                result[subcat] = []
            result[subcat].append(s["url"])
    return result


def _build_m3_sources_dict() -> dict[str, dict[str, list[str]]]:
    """Build the M3_SOURCES dict (documentation only, grouped by category/subcategory)."""
    result: dict[str, dict[str, list[str]]] = {}
    for s in SOURCES:
        if s["milestone"] != "m3" or s["type"] != "documentation":
            continue
        cat = s["category"]
        subcat = s["subcategory"]
        if cat not in result:
            result[cat] = {}
        if subcat not in result[cat]:
            result[cat][subcat] = []
        result[cat][subcat].append(s["url"])
    return result


def _build_m3_github_repos_dict() -> dict[str, list[str]]:
    """Build the M3_GITHUB_REPOS dict (repos only, grouped by category)."""
    result: dict[str, list[str]] = {}
    for s in SOURCES:
        if s["milestone"] != "m3" or s["type"] != "github":
            continue
        cat = s["category"]
        if cat not in result:
            result[cat] = []
        result[cat].append(s["url"])
    return result


# Reconstructed top-level dicts
DOCS = {
    "stylus": _build_docs_dict("stylus"),
    "arbitrum_sdk": _build_docs_dict("arbitrum_sdk"),
    "orbit_sdk": _build_docs_dict("orbit_sdk"),
    "arbitrum_general": _build_docs_dict("arbitrum_general"),
}

PROJECT_EXAMPLES = {
    "stylus": _build_project_examples_dict("stylus"),
    "arbitrum_sdk": _build_project_examples_dict("arbitrum_sdk"),
    "orbit_sdk": _build_project_examples_dict("orbit_sdk"),
}

# Legacy flat URL dicts
STYLUS_SOURCES = {**_build_docs_dict("stylus"), **_build_project_urls_dict("stylus")}
ARBITRUM_SDK_SOURCES = {
    **_build_docs_dict("arbitrum_sdk"),
    **_build_project_urls_dict("arbitrum_sdk"),
}
ORBIT_SDK_SOURCES = {
    **_build_docs_dict("orbit_sdk"),
    **_build_project_urls_dict("orbit_sdk"),
}
ARBITRUM_DOCS = _build_docs_dict("arbitrum_general")

# M3 dicts
M3_SOURCES = _build_m3_sources_dict()
M3_GITHUB_REPOS = _build_m3_github_repos_dict()

# All sources combined
ALL_SOURCES = {
    "stylus": STYLUS_SOURCES,
    "arbitrum_sdk": ARBITRUM_SDK_SOURCES,
    "orbit_sdk": ORBIT_SDK_SOURCES,
    "arbitrum_docs": ARBITRUM_DOCS,
    "m3_docs": M3_SOURCES,
    "m3_repos": M3_GITHUB_REPOS,
}

"""Utility modules for ARBuilder."""

from .version_manager import (
    load_version_config,
    get_main_version,
    get_minimum_version,
    is_version_supported,
    is_version_deprecated,
    get_version_patterns,
    get_alloy_primitives_version,
    get_alloy_sol_types_version,
    compare_versions,
    detect_version_from_cargo_toml,
    get_deprecation_warning,
)

__all__ = [
    "load_version_config",
    "get_main_version",
    "get_minimum_version",
    "is_version_supported",
    "is_version_deprecated",
    "get_version_patterns",
    "get_alloy_primitives_version",
    "get_alloy_sol_types_version",
    "compare_versions",
    "detect_version_from_cargo_toml",
    "get_deprecation_warning",
]

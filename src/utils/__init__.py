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

from .env_config import (
    generate_env_template,
    BACKEND_PORT,
    FRONTEND_PORT,
    NETWORK_CONFIGS,
)

from .abi_extractor import (
    extract_abi_from_code,
    abi_to_viem_human_readable,
    abi_to_json_string,
)

from .compiler_verifier import (
    CompilerVerifier,
    CompileResult,
    CompileError,
    format_errors_for_llm,
)

__all__ = [
    # version_manager
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
    # env_config
    "generate_env_template",
    "BACKEND_PORT",
    "FRONTEND_PORT",
    "NETWORK_CONFIGS",
    # abi_extractor
    "extract_abi_from_code",
    "abi_to_viem_human_readable",
    "abi_to_json_string",
    # compiler_verifier
    "CompilerVerifier",
    "CompileResult",
    "CompileError",
    "format_errors_for_llm",
]

"""
Configuration for ARBuilder data scraping.
Contains all target URLs organized by type: Documentation vs Project Examples.

FORK STRATEGY:
All Stylus repos are sourced from the ARBuilder-Forks GitHub org
(https://github.com/ARBuilder-Forks) to ensure resilience against upstream
deletions. Each entry includes a `forked_from` field tracking the original repo.
- 6 forks are fully migrated to SDK 0.10.0
- 7 forks retain original code (blocked by upstream dependency conflicts)
  and rely on the dual-chunk strategy for 0.10.0 coverage

CURATION POLICY:
- Only include sources verified to work with current SDK version
- Official docs: Always include (maintained by Arbitrum team)
- Code repos: Must compile with stylus-sdk >= 0.8.0
- No meta-lists (awesome-stylus) - causes outdated code ingestion
- No unverified community submissions
- All repos verified with scripts/verify_source.py (SDK version + compile + tests)

INCLUSION CRITERIA:
- Docs: Official Arbitrum/Stylus documentation pages, blog articles
- Projects (official_examples): Maintained by OffchainLabs/ArbitrumFoundation, SDK >= 0.8.0
- Projects (verified_production): Reputable orgs (OpenZeppelin, Gnosis, Oak Security), SDK >= 0.8.0
- Projects (community_projects): Verified compilation with SDK >= 0.8.0, date-stamped
- Projects (scaffold_projects): scaffold-stylus based, SDK 0.9.0, must compile
- Projects (official_repos): SDK/tutorial repos maintained by OffchainLabs
- Projects (community_examples): Third-party @arbitrum/sdk usage, verified SDK version

LAST VERIFICATION: 2026-02-16
  Migrated all Stylus repos to ARBuilder-Forks org.
  6/13 forks compile with SDK 0.10.0; 7 reverted to original code.
"""

# SDK version requirements (from shared/stylus-versions.json)
MAIN_STYLUS_SDK_VERSION = "0.10.0"
MIN_STYLUS_SDK_VERSION = "0.8.0"  # Minimum supported
DEPRECATED_BELOW = "0.8.0"  # Anything below this is deprecated

# ──────────────────────────────────────────────────────────────
# DOCUMENTATION SOURCES
# Pure documentation pages (no runnable code to version-track)
# ──────────────────────────────────────────────────────────────
DOCS = {
    "stylus": {
        "official": [
            "https://docs.arbitrum.io/stylus/stylus-overview",
            "https://docs.arbitrum.io/stylus/quickstart",
            "https://docs.arbitrum.io/stylus/cli-tools-overview",
            "https://docs.arbitrum.io/stylus/reference/rust-sdk-guide",
            "https://docs.arbitrum.io/stylus/gentle-introduction",
            "https://docs.arbitrum.io/stylus/reference/overview",
            "https://docs.arbitrum.io/stylus/concepts/gas-metering",
        ],
        "articles": [
            "https://blog.arbitrum.io/how-thirdweb-uses-arbitrum-stylus-to-power-the-next-wave-of-onchain-apps/",
        ],
    },
    "arbitrum_sdk": {
        "official": [
            "https://docs.arbitrum.io/build-decentralized-apps/token-bridging/overview",
            "https://docs.arbitrum.io/build-decentralized-apps/token-bridging/token-bridge-erc20",
            "https://docs.arbitrum.io/build-decentralized-apps/cross-chain-messaging",
            "https://docs.arbitrum.io/sdk",
            "https://docs.arbitrum.io/build-decentralized-apps/precompiles/reference",
            "https://docs.arbitrum.io/build-decentralized-apps/precompiles/overview",
        ],
    },
    "orbit_sdk": {
        "docs": [
            "https://docs.superposition.so/",
        ],
    },
    "arbitrum_general": {
        "general": [
            "https://docs.arbitrum.io/welcome/get-started",
            "https://docs.arbitrum.io/for-devs/quickstart-solidity-hardhat",
        ],
    },
}

# ──────────────────────────────────────────────────────────────
# PROJECT EXAMPLES
# Repositories with runnable code — each entry tracks SDK version
# ──────────────────────────────────────────────────────────────
PROJECT_EXAMPLES = {
    "stylus": {
        "official_examples": [
            # Official examples forked to ARBuilder-Forks org
            # hello-world & vending-machine: fully migrated to SDK 0.10.0
            # workshop-gol: reverted to original (OZ alloy-primitives conflict)
            {"url": "https://github.com/ARBuilder-Forks/stylus-hello-world",
             "sdk_version": "0.10.0", "verified": "2026-02-16",
             "forked_from": "OffchainLabs/stylus-hello-world"},
            {"url": "https://github.com/ARBuilder-Forks/stylus-quickstart-vending-machine",
             "sdk_version": "0.10.0", "verified": "2026-02-16",
             "forked_from": "OffchainLabs/stylus-quickstart-vending-machine"},
            {"url": "https://github.com/ARBuilder-Forks/stylus-workshop-gol",
             "sdk_version": "0.9.0", "verified": "2026-02-16",
             "forked_from": "ArbitrumFoundation/stylus-workshop-gol",
             "note": "Reverted to original — OZ alloy-primitives conflict blocks 0.10.0 migration"},
        ],
        "verified_production": [
            # Production codebases forked to ARBuilder-Forks org
            # All reverted to original code — blocked by c-kzg/alloy version conflicts
            {"url": "https://github.com/ARBuilder-Forks/rust-contracts-stylus",
             "sdk_version": "0.9.0", "verified": "2026-02-16",
             "forked_from": "OpenZeppelin/rust-contracts-stylus",
             "note": "Reverted to original — c-kzg + alloy version conflict blocks 0.10.0"},
            {"url": "https://github.com/ARBuilder-Forks/stylus-test-helpers",
             "sdk_version": "0.9.0", "verified": "2026-02-16",
             "forked_from": "OpenZeppelin/stylus-test-helpers",
             "note": "Reverted to original — c-kzg native library conflict blocks 0.10.0"},
            {"url": "https://github.com/ARBuilder-Forks/stylusport",
             "sdk_version": "0.9.0", "verified": "2026-02-16",
             "forked_from": "oak-security/stylusport",
             "note": "Reverted to original — c-kzg native library conflict blocks 0.10.0"},
            {"url": "https://github.com/ARBuilder-Forks/stylus-provider",
             "sdk_version": "0.8.4", "verified": "2026-02-16",
             "forked_from": "gnosisguild/stylus-provider",
             "note": "Reverted to original — c-kzg native library conflict blocks 0.10.0"},
        ],
        "community_projects": [
            # Community projects forked to ARBuilder-Forks org
            # All 3 fully migrated to SDK 0.10.0
            {"url": "https://github.com/ARBuilder-Forks/ethbuc2025-gyges",
             "sdk_version": "0.10.0", "verified": "2026-02-16",
             "forked_from": "philogicae/ethbuc2025-gyges"},
            {"url": "https://github.com/ARBuilder-Forks/erc6909-with-arbitrum-stylus",
             "sdk_version": "0.10.0", "verified": "2026-02-16",
             "forked_from": "Oluwatobilobaoke/erc6909-with-arbitrum-stylus"},
            {"url": "https://github.com/ARBuilder-Forks/fortune-generator",
             "sdk_version": "0.10.0", "verified": "2026-02-16",
             "forked_from": "hummusonrails/fortune-generator"},
        ],
        "scaffold_projects": [
            # Scaffold-stylus projects forked to ARBuilder-Forks org
            # WalletNaming: fully migrated to 0.10.0
            # scaffold-stylus & cross-protocol-defi-tracker: reverted (OZ conflict)
            {"url": "https://github.com/ARBuilder-Forks/scaffold-stylus",
             "sdk_version": "0.9.0", "verified": "2026-02-16",
             "forked_from": "Arb-Stylus/scaffold-stylus",
             "note": "Reverted to original — OZ v0.3.0 incompatible with SDK 0.10.0"},
            {"url": "https://github.com/ARBuilder-Forks/cross-protocol-defi-tracker",
             "sdk_version": "0.9.0", "verified": "2026-02-16",
             "forked_from": "iyansr/cross-protocol-defi-tracker",
             "note": "Reverted to original — OZ alloy-primitives conflict blocks 0.10.0"},
            {"url": "https://github.com/ARBuilder-Forks/WalletNaming-scaffold-stylus",
             "sdk_version": "0.10.0", "verified": "2026-02-16",
             "forked_from": "Einarmig/WalletNaming-scaffold-stylus"},
        ],
    },
    "arbitrum_sdk": {
        "official_repos": [
            # VERIFIED 2026-02-10 with verify_source.py --steps 1,2,4:
            # SDK repo - contains library code (npm install fails in monorepo, expected)
            {"url": "https://github.com/OffchainLabs/arbitrum-sdk", "sdk_version": "N/A", "verified": "2026-02-10"},
            # Tutorials - working examples for bridging/messaging (@arbitrum/sdk 4.0.1)
            {"url": "https://github.com/OffchainLabs/arbitrum-tutorials", "sdk_version": "4.0.1", "verified": "2026-02-10"},
        ],
        "community_examples": [
            # VERIFIED 2026-02-10 with verify_source.py --steps 1,2,4:
            # Production REST API wrapping EthBridger/Erc20Bridger (32 stars, active)
            {"url": "https://github.com/kevinb1003/arbitrum-api", "sdk_version": "4.0.4", "verified": "2026-02-10",
             "note": "Tests need env vars (DB, API keys) — SDK version verified, active repo"},
            # Orbit chain deposit/withdrawal scripts using @arbitrum/sdk
            {"url": "https://github.com/gelatodigital/how-tos-18-arbitrum-orbit-bridging", "sdk_version": "4.0.2", "verified": "2026-02-10",
             "note": "Orbit bridging examples — no tests, active repo"},
            # Cross-chain messaging examples (L1↔L2, L2↔L3)
            {"url": "https://github.com/gelatodigital/clink-bridging-cross-messaging", "sdk_version": "4.0.2", "verified": "2026-02-10",
             "note": "Cross-chain messaging patterns — no tests, abandoned but unique value"},
        ],
    },
    "orbit_sdk": {
        "sdk_repo": [
            # VERIFIED 2026-02-10: builds successfully, @arbitrum/sdk 4.0.4
            {"url": "https://github.com/OffchainLabs/arbitrum-orbit-sdk", "sdk_version": "4.0.4", "verified": "2026-02-10"},
        ],
    },
}


def get_all_config_repo_urls() -> set[str]:
    """Return the set of all GitHub repo URLs configured in PROJECT_EXAMPLES."""
    urls = set()
    for _category, subcategories in PROJECT_EXAMPLES.items():
        for _subcat, entries in subcategories.items():
            for entry in entries:
                urls.add(entry["url"])
    return urls


def get_config_repo_info() -> dict[str, dict]:
    """Return a mapping of repo URL -> {category, subcategory, sdk_version, verified, forked_from}."""
    info = {}
    for category, subcategories in PROJECT_EXAMPLES.items():
        for subcategory, entries in subcategories.items():
            for entry in entries:
                info[entry["url"]] = {
                    "category": category,
                    "subcategory": subcategory,
                    "sdk_version": entry.get("sdk_version", ""),
                    "verified": entry.get("verified", ""),
                    "forked_from": entry.get("forked_from", ""),
                }
    return info


# ──────────────────────────────────────────────────────────────
# BACKWARD COMPATIBILITY
# Flat URL lists for existing consumers (scraper.py web scraping)
# ──────────────────────────────────────────────────────────────

def _flatten_docs(category: str) -> dict[str, list[str]]:
    """Flatten DOCS[category] to {subcategory: [url, ...]}."""
    return DOCS.get(category, {})


def _flatten_projects(category: str) -> dict[str, list[str]]:
    """Flatten PROJECT_EXAMPLES[category] to {subcategory: [url, ...]}."""
    result = {}
    for subcat, entries in PROJECT_EXAMPLES.get(category, {}).items():
        result[subcat] = [e["url"] for e in entries]
    return result


# Legacy names used by scraper.py and github_scraper.py
STYLUS_SOURCES = {**_flatten_docs("stylus"), **_flatten_projects("stylus")}
ARBITRUM_SDK_SOURCES = {**_flatten_docs("arbitrum_sdk"), **_flatten_projects("arbitrum_sdk")}
ORBIT_SDK_SOURCES = {**_flatten_docs("orbit_sdk"), **_flatten_projects("orbit_sdk")}
ARBITRUM_DOCS = _flatten_docs("arbitrum_general")

# M3: Full dApp Builder Sources
# Documentation and examples for backend, frontend, indexer, and oracle components
M3_SOURCES = {
    "backend": {
        "nestjs": [
            "https://docs.nestjs.com/first-steps",
            "https://docs.nestjs.com/modules",
            "https://docs.nestjs.com/providers",
            "https://docs.nestjs.com/controllers",
            "https://docs.nestjs.com/techniques/configuration",
        ],
        "express": [
            "https://expressjs.com/en/starter/basic-routing.html",
            "https://expressjs.com/en/guide/routing.html",
            "https://expressjs.com/en/guide/error-handling.html",
        ],
    },
    "frontend": {
        "wagmi": [
            "https://wagmi.sh/react/getting-started",
            "https://wagmi.sh/react/guides/connect-wallet",
            "https://wagmi.sh/react/guides/read-from-contract",
            "https://wagmi.sh/react/guides/write-to-contract",
            "https://wagmi.sh/react/guides/transactions",
        ],
        "viem": [
            "https://viem.sh/docs/getting-started.html",
            "https://viem.sh/docs/contract/readContract.html",
            "https://viem.sh/docs/contract/writeContract.html",
            "https://viem.sh/docs/actions/public/waitForTransactionReceipt.html",
        ],
        "rainbowkit": [
            "https://www.rainbowkit.com/docs/introduction",
            "https://www.rainbowkit.com/docs/installation",
            "https://www.rainbowkit.com/docs/connect-button",
            "https://www.rainbowkit.com/docs/custom-chains",
        ],
        "daisyui": [
            "https://daisyui.com/docs/install/",
            "https://daisyui.com/components/button/",
            "https://daisyui.com/components/card/",
            "https://daisyui.com/components/modal/",
            "https://daisyui.com/components/input/",
        ],
    },
    "indexer": {
        "the_graph": [
            "https://thegraph.com/docs/en/developing/creating-a-subgraph/",
            "https://thegraph.com/docs/en/developing/assemblyscript-api/",
            "https://thegraph.com/docs/en/developing/graph-ts/api/",
            "https://thegraph.com/docs/en/cookbook/arweave/",
            "https://thegraph.com/docs/en/developing/unit-testing-framework/",
        ],
    },
    "oracle": {
        "chainlink": [
            "https://docs.chain.link/data-feeds/price-feeds",
            "https://docs.chain.link/vrf/v2-5/subscription/get-a-random-number",
            "https://docs.chain.link/chainlink-automation/overview/getting-started",
            "https://docs.chain.link/chainlink-functions/getting-started",
            "https://docs.chain.link/data-feeds/price-feeds/addresses?network=arbitrum&page=1",
        ],
    },
}

# M3: GitHub repositories for code examples
M3_GITHUB_REPOS = {
    "frontend": [
        # wagmi examples and patterns
        "https://github.com/wevm/wagmi",
        "https://github.com/wevm/viem",
        # RainbowKit
        "https://github.com/rainbow-me/rainbowkit",
        # DaisyUI
        "https://github.com/saadeghi/daisyui",
        # Scaffold-ETH 2 (full-stack template)
        "https://github.com/scaffold-eth/scaffold-eth-2",
    ],
    "indexer": [
        # The Graph tooling
        "https://github.com/graphprotocol/graph-tooling",
        # Subgraph examples
        "https://github.com/messari/subgraphs",
        # Arbitrum subgraphs
        "https://github.com/OffchainLabs/arbitrum-subgraphs",
    ],
    "oracle": [
        # Chainlink examples
        "https://github.com/smartcontractkit/smart-contract-examples",
        "https://github.com/smartcontractkit/chainlink",
    ],
    "backend": [
        # NestJS
        "https://github.com/nestjs/nest",
        # Arbitrum token bridge (for integration patterns)
        "https://github.com/OffchainLabs/arbitrum-token-bridge",
    ],
}

# All sources combined for easy iteration
ALL_SOURCES = {
    "stylus": STYLUS_SOURCES,
    "arbitrum_sdk": ARBITRUM_SDK_SOURCES,
    "orbit_sdk": ORBIT_SDK_SOURCES,
    "arbitrum_docs": ARBITRUM_DOCS,
    "m3_docs": M3_SOURCES,
    "m3_repos": M3_GITHUB_REPOS,
}

"""
Configuration for ARBuilder data scraping.
Contains all target URLs organized by type: Documentation vs Project Examples.

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

LAST VERIFICATION: 2026-02-10
  Tool: scripts/verify_source.py --all --steps 1,2,4
  Before: 34 repos | After cleanup: 16 repos
  Removed: 10 challenge submissions (98% identical), 5 broken scaffold forks,
           2 broken community projects, 1 broken verified_production repo
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
            # Official examples maintained by OffchainLabs/ArbitrumFoundation
            # VERIFIED 2026-02-10 with verify_source.py --steps 1,2,4:
            {"url": "https://github.com/OffchainLabs/stylus-hello-world", "sdk_version": "0.9.0", "verified": "2026-02-10"},
            {"url": "https://github.com/OffchainLabs/stylus-quickstart-vending-machine", "sdk_version": "0.8.4", "verified": "2026-02-10"},
            {"url": "https://github.com/ArbitrumFoundation/stylus-workshop-gol", "sdk_version": "0.9.0", "verified": "2026-02-10",
             "note": "Compiles but tests fail (0 passed) — workshop format, test setup requires devnode"},
        ],
        "verified_production": [
            # Production codebases verified to use current SDK
            # VERIFIED 2026-02-10 with verify_source.py --steps 1,2,4:
            {"url": "https://github.com/OpenZeppelin/rust-contracts-stylus", "sdk_version": "0.9.0", "verified": "2026-02-10"},
            {"url": "https://github.com/OpenZeppelin/stylus-test-helpers", "sdk_version": "0.9.0", "verified": "2026-02-10",
             "note": "Helper library — no direct stylus-sdk dep but compiles and has 47 tests"},
            {"url": "https://github.com/oak-security/stylusport", "sdk_version": "0.9.0", "verified": "2026-02-10",
             "note": "Linker error on native arm64 — may compile to wasm32 target"},
            {"url": "https://github.com/gnosisguild/stylus-provider", "sdk_version": "0.8.4", "verified": "2026-02-10",
             "note": "Compiles but tests fail — production library"},
            # REMOVED 2026-02-10: stylus-developers-guild/reentrancy-transient-storage — compile fails (trait bound error)
        ],
        "community_projects": [
            # VERIFIED 2026-02-10 with verify_source.py --steps 1,2,4:
            {"url": "https://github.com/philogicae/ethbuc2025-gyges", "sdk_version": "0.8.4", "verified": "2026-02-10"},
            {"url": "https://github.com/Oluwatobilobaoke/erc6909-with-arbitrum-stylus", "sdk_version": "0.9.0", "verified": "2026-02-10"},
            {"url": "https://github.com/hummusonrails/fortune-generator", "sdk_version": "0.8.0", "verified": "2026-02-10"},
            # REMOVED 2026-02-10: IndexMaker/vaultworks — archived, no stylus-sdk detected
            # REMOVED 2026-02-10: Inteli-Club5/EdCation — compile fails (StorageAddress::new wrong args)
        ],
        "scaffold_projects": [
            # VERIFIED 2026-02-10 with verify_source.py --steps 1,2,4:
            {"url": "https://github.com/Arb-Stylus/scaffold-stylus", "sdk_version": "0.9.0", "verified": "2026-02-10",
             "note": "Canonical scaffold — OZ 0.3.0 incompatible with sdk 0.9.0, own contract compiles"},
            {"url": "https://github.com/iyansr/cross-protocol-defi-tracker", "sdk_version": "0.9.0", "verified": "2026-02-10"},
            {"url": "https://github.com/Einarmig/WalletNaming-scaffold-stylus", "sdk_version": "0.9.0", "verified": "2026-02-10"},
            # REMOVED 2026-02-10: mavix21/poap-scaffold-stylus — compile fails (openzeppelin-stylus 0.3.0 incompatible)
            # REMOVED 2026-02-10: dchagast/scaffold-stylus-staking — compile fails (linker errors on arm64)
            # REMOVED 2026-02-10: cidkagenow/EmersonApp-scaffold-stylus — compile fails (non-exhaustive patterns)
            # REMOVED 2026-02-10: autodidacttrade/DeFi-Project-ERC20 — compile fails (linker errors)
            # REMOVED 2026-02-10: ByteToHex/VRF-scaffold-stylus — compile fails (linker errors)
        ],
        # REMOVED 2026-02-10: All 10 challenge submissions removed — 98% identical template code,
        # zero unique value, adds 4700+ duplicate chunks that pollute retrieval results.
        # Repos: Huygon764, Fnz11, ndrewlex, athallarizky, dimasd-angga, ammar-rasyidi,
        # rizkianakbar, math-marcellino, lucky-ivanius (x2), dante4rt (404)
    },
    "arbitrum_sdk": {
        "official_repos": [
            # VERIFIED 2026-02-10 with verify_source.py --steps 1,2,4:
            # SDK repo - contains library code (npm install fails in monorepo, expected)
            {"url": "https://github.com/OffchainLabs/arbitrum-sdk", "sdk_version": "N/A", "verified": "2026-02-10"},
            # Tutorials - working examples for bridging/messaging (@arbitrum/sdk 4.0.1)
            {"url": "https://github.com/OffchainLabs/arbitrum-tutorials", "sdk_version": "4.0.1", "verified": "2026-02-10"},
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
    """Return a mapping of repo URL -> {category, subcategory, sdk_version, verified}."""
    info = {}
    for category, subcategories in PROJECT_EXAMPLES.items():
        for subcategory, entries in subcategories.items():
            for entry in entries:
                info[entry["url"]] = {
                    "category": category,
                    "subcategory": subcategory,
                    "sdk_version": entry.get("sdk_version", ""),
                    "verified": entry.get("verified", ""),
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

"""
Configuration for ARBuilder data scraping.
Contains all target URLs organized by milestone.

CURATION POLICY:
- Only include sources verified to work with current SDK version
- Official docs: Always include (maintained by Arbitrum team)
- Code repos: Must compile with stylus-sdk >= 0.9.0
- No meta-lists (awesome-stylus) - causes outdated code ingestion
- No unverified community submissions
"""

# SDK version requirements (from shared/stylus-versions.json)
MAIN_STYLUS_SDK_VERSION = "0.9.2"
MIN_STYLUS_SDK_VERSION = "0.8.0"  # Minimum supported
DEPRECATED_BELOW = "0.8.0"  # Anything below this is deprecated

# M1: Stylus Documentation and Code Sources
# VERIFIED: All code sources tested to compile with SDK 0.9.x
STYLUS_SOURCES = {
    "official_docs": [
        # Official Arbitrum docs - always current
        "https://docs.arbitrum.io/stylus/stylus-overview",
        "https://docs.arbitrum.io/stylus/quickstart",
        "https://docs.arbitrum.io/stylus/cli-tools-overview",
        "https://docs.arbitrum.io/stylus/reference/rust-sdk-guide",
        "https://docs.arbitrum.io/stylus/gentle-introduction",
        "https://docs.arbitrum.io/stylus/reference/overview",
        "https://docs.arbitrum.io/stylus/concepts/gas-metering",
    ],
    # NOTE: Removed "curated" section - awesome-stylus contains many outdated projects
    "official_examples": [
        # Official examples maintained by OffchainLabs/ArbitrumFoundation
        # VERIFIED 2025-01-25 (all >= 0.8.0 minimum):
        "https://github.com/OffchainLabs/stylus-hello-world",  # SDK 0.9.0
        "https://github.com/OffchainLabs/stylus-quickstart-vending-machine",  # SDK 0.8.4
        "https://github.com/ArbitrumFoundation/stylus-workshop-gol",  # SDK 0.9.0
    ],
    "verified_production": [
        # Production codebases verified to use current SDK
        # OpenZeppelin: Actively maintained, follows latest SDK
        "https://github.com/OpenZeppelin/rust-contracts-stylus",  # SDK 0.9.0
        "https://github.com/stylus-developers-guild/reentrancy-transient-storage",  # SDK 0.9.0
    ],
    "community_projects": [
        # VERIFIED 2025-01-25 (all >= 0.8.0):
        "https://github.com/philogicae/ethbuc2025-gyges",  # SDK 0.8.4
        "https://github.com/Oluwatobilobaoke/erc6909-with-arbitrum-stylus",  # SDK 0.9.0
        "https://github.com/hummusonrails/fortune-generator",  # SDK 0.8.0
    ],
    "scaffold_projects": [
        # VERIFIED 2025-01-25 - scaffold-stylus based projects (all SDK 0.9.0):
        "https://github.com/iyansr/cross-protocol-defi-tracker",
        "https://github.com/Einarmig/WalletNaming-scaffold-stylus",
        "https://github.com/mavix21/poap-scaffold-stylus",
        "https://github.com/dchagast/scaffold-stylus-staking",
        "https://github.com/cidkagenow/EmersonApp-scaffold-stylus",
        "https://github.com/autodidacttrade/DeFi-Project-ERC20-scaffold-stylus",
        "https://github.com/ByteToHex/VRF-scaffold-stylus",
        # NOTE: Oyase-shinobi/scaffold-stylus excluded - has mixed SDK versions (0.9.0 + 0.6.1)
    ],
    "challenge_submissions": [
        # VERIFIED 2025-01-25 - Arbitrum challenge submissions (all SDK 0.9.0):
        "https://github.com/dante4rt/challenge-001",
        "https://github.com/Huygon764/challenge-001",
        "https://github.com/Fnz11/challenge-001",
        "https://github.com/ndrewlex/challenge-001",
        "https://github.com/athallarizky/challenge-001",
        "https://github.com/dimasd-angga/challenge-001",
        "https://github.com/ammar-rasyidi/challenge-001",
        "https://github.com/rizkianakbar/challenge-001",
        "https://github.com/math-marcellino/challenge-002",
        "https://github.com/lucky-ivanius/challenge-001",
        "https://github.com/lucky-ivanius/challenge-002",
    ],
    "articles": [
        "https://blog.arbitrum.io/how-thirdweb-uses-arbitrum-stylus-to-power-the-next-wave-of-onchain-apps/",
    ],
}

# M2: Arbitrum SDK Sources - Cross-chain messaging and bridging
# NOTE: SDK repos contain docs/examples but no standalone "project" to verify
# The tutorials repo has working examples we can use
ARBITRUM_SDK_SOURCES = {
    "official_docs": [
        "https://docs.arbitrum.io/build-decentralized-apps/token-bridging/overview",
        "https://docs.arbitrum.io/build-decentralized-apps/token-bridging/token-bridge-erc20",
        "https://docs.arbitrum.io/build-decentralized-apps/cross-chain-messaging",
        "https://docs.arbitrum.io/sdk",
        "https://docs.arbitrum.io/build-decentralized-apps/precompiles/reference",
        "https://docs.arbitrum.io/build-decentralized-apps/precompiles/overview",
    ],
    "official_repos": [
        # SDK repo - contains library code and some examples
        "https://github.com/OffchainLabs/arbitrum-sdk",
        # Tutorials - VERIFIED working examples for bridging/messaging
        "https://github.com/OffchainLabs/arbitrum-tutorials",
    ],
    # NOTE: token-bridge repo is the bridge UI, not SDK examples
    # Removed as it doesn't provide reusable code patterns
}

# M4: Orbit SDK Sources
ORBIT_SDK_SOURCES = {
    "sdk_repo": [
        "https://github.com/OffchainLabs/arbitrum-orbit-sdk",
    ],
    "docs": [
        "https://docs.superposition.so/",
    ],
}

# Arbitrum General Documentation
ARBITRUM_DOCS = {
    "general": [
        "https://docs.arbitrum.io/welcome/get-started",
        "https://docs.arbitrum.io/for-devs/quickstart-solidity-hardhat",
        # Note: /build-decentralized-apps/01-overview is 404, no direct replacement found
    ],
}

# All sources combined for easy iteration
ALL_SOURCES = {
    "stylus": STYLUS_SOURCES,
    "arbitrum_sdk": ARBITRUM_SDK_SOURCES,
    "orbit_sdk": ORBIT_SDK_SOURCES,
    "arbitrum_docs": ARBITRUM_DOCS,
}

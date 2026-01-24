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

# Current SDK version requirement
REQUIRED_STYLUS_SDK_VERSION = "0.9.0"

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
        # VERIFIED: These repos use SDK 0.9.x or are actively maintained
        "https://github.com/OffchainLabs/stylus-hello-world",
        "https://github.com/OffchainLabs/stylus-quickstart-vending-machine",
        "https://github.com/ArbitrumFoundation/stylus-workshop-gol",
    ],
    "verified_production": [
        # Production codebases verified to use current SDK
        # OpenZeppelin: Actively maintained, follows latest SDK
        "https://github.com/OpenZeppelin/rust-contracts-stylus",
    ],
    # NOTE: Removed community_projects and community_challenges
    # These were unverified and many used deprecated SDK versions
    # TODO: Re-add after manual verification of SDK compatibility
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

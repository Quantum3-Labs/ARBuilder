"""
Configuration for ARBuilder data scraping.
Contains all target URLs organized by milestone.
"""

# M1: Stylus Documentation and Code Sources
# NOTE: Only include sources using Stylus SDK >= 0.8.0
STYLUS_SOURCES = {
    "official_docs": [
        # arbitrum.io/stylus returns 403 - skipped
        "https://docs.arbitrum.io/stylus/stylus-overview",
        "https://docs.arbitrum.io/stylus/quickstart",  # was: write-stylus-contracts
        "https://docs.arbitrum.io/stylus/cli-tools-overview",  # was: local-stylus-dev
        "https://docs.arbitrum.io/stylus/reference/rust-sdk-guide",  # was: stylus-sdk
        "https://docs.arbitrum.io/stylus/gentle-introduction",
        "https://docs.arbitrum.io/stylus/reference/overview",
        "https://docs.arbitrum.io/stylus/concepts/gas-metering",  # gas and ink concepts
    ],
    "curated": [
        "https://github.com/OffchainLabs/awesome-stylus",
    ],
    "official_examples": [
        # Removed: stylus-chess (v0.4.2), stylus-by-example (v0.6.0) - deprecated SDK
        "https://github.com/OffchainLabs/stylus-hello-world",
        "https://github.com/OffchainLabs/stylus-quickstart-vending-machine",
        "https://github.com/ArbitrumFoundation/stylus-workshop-gol",
    ],
    "production_codebases": [
        # Removed: 9lives.so (v0.7.0), long.so (v0.7.0) - deprecated SDK
        "https://github.com/OpenZeppelin/rust-contracts-stylus",
        "https://github.com/renegade-fi/renegade-contracts",
        "https://github.com/stylus-developers-guild/reentrancy-transient-storage",
    ],
    "community_projects": [
        # Removed: ArbitrumOnchainAgent (v0.7.0) - deprecated SDK
        "https://github.com/philogicae/ethbuc2025-gyges",
        "https://github.com/Oluwatobilobaoke/erc6909-with-arbitrum-stylus",
        "https://github.com/hummusonrails/fortune-generator",
    ],
    "community_challenges": [
        # Cross-protocol and scaffold-stylus projects
        "https://github.com/iyansr/cross-protocol-defi-tracker",
        "https://github.com/Oyase-shinobi/scaffold-stylus",
        "https://github.com/Einarmig/WalletNaming-scaffold-stylus",
        "https://github.com/mavix21/poap-scaffold-stylus",
        "https://github.com/dchagast/scaffold-stylus-staking",
        "https://github.com/cidkagenow/EmersonApp-scaffold-stylus",
        "https://github.com/autodidacttrade/DeFi-Project-ERC20-scaffold-stylus",
        "https://github.com/ByteToHex/VRF-scaffold-stylus",
        # Challenge submissions
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
ARBITRUM_SDK_SOURCES = {
    "sdk_repo": [
        "https://github.com/OffchainLabs/arbitrum-sdk",
    ],
    "tutorials": [
        "https://github.com/OffchainLabs/arbitrum-tutorials",
    ],
    "token_bridge": [
        "https://github.com/OffchainLabs/arbitrum-token-bridge",
    ],
    "docs_bridging": [
        "https://docs.arbitrum.io/build-decentralized-apps/token-bridging/overview",  # token bridging intro
        "https://docs.arbitrum.io/build-decentralized-apps/token-bridging/token-bridge-erc20",
        "https://docs.arbitrum.io/build-decentralized-apps/cross-chain-messaging",
        "https://docs.arbitrum.io/sdk",  # was: 02-use-arbitrum-sdk
        "https://docs.arbitrum.io/build-decentralized-apps/precompiles/reference",  # was: precompiles/02-reference
        "https://docs.arbitrum.io/build-decentralized-apps/precompiles/overview",
    ],
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

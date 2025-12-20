"""
Configuration for ARBuilder data scraping.
Contains all target URLs organized by milestone.
"""

# M1: Stylus Documentation and Code Sources
STYLUS_SOURCES = {
    "official_docs": [
        "https://arbitrum.io/stylus",
        "https://docs.arbitrum.io/stylus/stylus-overview",
        "https://docs.arbitrum.io/stylus/how-tos/write-stylus-contracts",
        "https://docs.arbitrum.io/stylus/how-tos/local-stylus-dev",
        "https://docs.arbitrum.io/stylus/reference/stylus-sdk",
    ],
    "curated": [
        "https://github.com/OffchainLabs/awesome-stylus",
    ],
    "official_examples": [
        "https://github.com/OffchainLabs/stylus-chess",
        "https://github.com/OffchainLabs/stylus-by-example",
        "https://github.com/OffchainLabs/stylus-hello-world",
        "https://github.com/OffchainLabs/stylus-quickstart-vending-machine",
        "https://github.com/ArbitrumFoundation/stylus-workshop-gol",
    ],
    "production_codebases": [
        "https://github.com/fluidity-money/9lives.so",
        "https://github.com/fluidity-money/long.so",
        "https://github.com/OpenZeppelin/rust-contracts-stylus",
        "https://github.com/renegade-fi/renegade-contracts",
        "https://github.com/stylus-developers-guild/reentrancy-transient-storage",
    ],
    "community_projects": [
        "https://github.com/hammertoe/ArbitrumOnchainAgent",
        "https://github.com/philogicae/ethbuc2025-gyges",
        "https://github.com/Oluwatobilobaoke/erc6909-with-arbitrum-stylus",
        "https://github.com/hummusonrails/fortune-generator",
    ],
    "articles": [
        "https://blog.arbitrum.io/how-thirdweb-uses-arbitrum-stylus-to-power-the-next-wave-of-onchain-apps/",
    ],
}

# M2: Arbitrum SDK Sources
ARBITRUM_SDK_SOURCES = {
    "sdk_repo": [
        "https://github.com/OffchainLabs/arbitrum-sdk",
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
        "https://docs.arbitrum.io/build-decentralized-apps/01-overview",
    ],
}

# All sources combined for easy iteration
ALL_SOURCES = {
    "stylus": STYLUS_SOURCES,
    "arbitrum_sdk": ARBITRUM_SDK_SOURCES,
    "orbit_sdk": ORBIT_SDK_SOURCES,
    "arbitrum_docs": ARBITRUM_DOCS,
}

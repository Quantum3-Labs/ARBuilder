"""
Configuration for ARBuilder data scraping.
Contains all target URLs organized by milestone.
"""

# =============================================================================
# M1: Stylus Documentation and Code Sources
# =============================================================================
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

# =============================================================================
# M2: Arbitrum SDK Sources
# =============================================================================
ARBITRUM_SDK_SOURCES = {
    "sdk_repo": [
        "https://github.com/OffchainLabs/arbitrum-sdk",
    ],
}

# =============================================================================
# M3: Full dApp Builder Sources
# =============================================================================

# Backend Framework Sources (NestJS/Express with Web3)
DAPP_BACKEND_SOURCES = {
    "arbitrum_tutorials": [
        "https://github.com/OffchainLabs/arbitrum-tutorials",
    ],
    "web3_backend_patterns": [
        "https://github.com/scaffold-eth/scaffold-eth-2",  # Full-stack reference
    ],
    "nestjs_examples": [
        "https://github.com/nestjs/nest",  # NestJS framework patterns
    ],
}

# Frontend & Wallet Integration Sources
DAPP_FRONTEND_SOURCES = {
    "wallet_libraries": [
        "https://github.com/wevm/wagmi",  # React hooks for Ethereum
        "https://github.com/wevm/viem",  # TypeScript Ethereum library
        "https://github.com/rainbow-me/rainbowkit",  # Wallet connection UI
    ],
    "arbitrum_frontends": [
        "https://github.com/OffchainLabs/arbitrum-token-bridge",  # Official bridge UI
    ],
    "production_dapps": [
        "https://github.com/gmx-io/gmx-interface",  # Arbitrum-native DEX
    ],
    "ui_components": [
        "https://github.com/saadeghi/daisyui",  # DaisyUI components
    ],
}

# Indexer & Subgraph Sources
DAPP_INDEXER_SOURCES = {
    "the_graph_tooling": [
        "https://github.com/graphprotocol/graph-tooling",  # Graph CLI & tools
    ],
    "arbitrum_subgraphs": [
        "https://github.com/OffchainLabs/arbitrum-subgraphs",  # Official Arb subgraphs
    ],
    "production_subgraphs": [
        "https://github.com/messari/subgraphs",  # Production subgraph examples
    ],
}

# Oracle Integration Sources
DAPP_ORACLE_SOURCES = {
    "chainlink": [
        "https://github.com/smartcontractkit/chainlink",  # Chainlink core
        "https://github.com/smartcontractkit/smart-contract-examples",  # Examples
    ],
}

# =============================================================================
# M4: Orbit SDK Sources
# =============================================================================
ORBIT_SDK_SOURCES = {
    "sdk_repo": [
        "https://github.com/OffchainLabs/arbitrum-orbit-sdk",
    ],
    "docs": [
        "https://docs.superposition.so/",
    ],
}

# =============================================================================
# Arbitrum General Documentation
# =============================================================================
ARBITRUM_DOCS = {
    "general": [
        "https://docs.arbitrum.io/welcome/get-started",
        "https://docs.arbitrum.io/for-devs/quickstart-solidity-hardhat",
        "https://docs.arbitrum.io/build-decentralized-apps/01-overview",
    ],
}

# =============================================================================
# Data Categories for Clustering
# =============================================================================
DATA_CATEGORIES = {
    "stylus_contracts": {
        "description": "Stylus smart contracts in Rust",
        "file_patterns": ["*.rs"],
        "sources": ["stylus"],
    },
    "backend_api": {
        "description": "Backend API patterns (NestJS/Express)",
        "file_patterns": ["*.ts", "*.js"],
        "keywords": ["controller", "service", "module", "route", "middleware"],
        "sources": ["dapp_backend"],
    },
    "frontend_react": {
        "description": "Frontend React/Next.js components",
        "file_patterns": ["*.tsx", "*.jsx"],
        "keywords": ["component", "hook", "page", "layout"],
        "sources": ["dapp_frontend"],
    },
    "wallet_integration": {
        "description": "Wallet connection and Web3 hooks",
        "file_patterns": ["*.ts", "*.tsx"],
        "keywords": ["wagmi", "viem", "wallet", "connect", "useAccount", "useContractRead"],
        "sources": ["dapp_frontend"],
    },
    "subgraph_indexer": {
        "description": "Subgraph schemas and mappings",
        "file_patterns": ["*.yaml", "*.graphql", "*.ts"],
        "keywords": ["subgraph", "entity", "handler", "event"],
        "sources": ["dapp_indexer"],
    },
    "oracle_integration": {
        "description": "Oracle patterns (Chainlink)",
        "file_patterns": ["*.sol", "*.ts"],
        "keywords": ["oracle", "pricefeed", "chainlink", "aggregator"],
        "sources": ["dapp_oracle"],
    },
    "documentation": {
        "description": "Documentation and guides",
        "file_patterns": ["*.md", "*.mdx"],
        "sources": ["arbitrum_docs"],
    },
}

# =============================================================================
# All sources combined for easy iteration
# =============================================================================
ALL_SOURCES = {
    "stylus": STYLUS_SOURCES,
    "arbitrum_sdk": ARBITRUM_SDK_SOURCES,
    "dapp_backend": DAPP_BACKEND_SOURCES,
    "dapp_frontend": DAPP_FRONTEND_SOURCES,
    "dapp_indexer": DAPP_INDEXER_SOURCES,
    "dapp_oracle": DAPP_ORACLE_SOURCES,
    "orbit_sdk": ORBIT_SDK_SOURCES,
    "arbitrum_docs": ARBITRUM_DOCS,
}

# M3 specific sources for targeted scraping
M3_SOURCES = {
    "dapp_backend": DAPP_BACKEND_SOURCES,
    "dapp_frontend": DAPP_FRONTEND_SOURCES,
    "dapp_indexer": DAPP_INDEXER_SOURCES,
    "dapp_oracle": DAPP_ORACLE_SOURCES,
}

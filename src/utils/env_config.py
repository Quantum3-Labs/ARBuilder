"""
Centralized environment variable configuration for ARBuilder dApps.

Single source of truth for all env var names used across contract, backend,
and frontend components. Prevents mismatches between components.
"""

from typing import Dict, List, Optional


# Canonical env var names per component
CONTRACT_ENV_VARS = {
    "CONTRACT_ADDRESS": "Deployed contract address (0x...)",
    "PRIVATE_KEY": "Deployer wallet private key (0x...)",
    "RPC_URL": "Arbitrum RPC endpoint",
}

BACKEND_ENV_VARS = {
    "CONTRACT_ADDRESS": "Deployed contract address (0x...)",
    "PRIVATE_KEY": "Wallet private key for write operations (0x...)",
    "RPC_URL": "Arbitrum RPC endpoint",
    "PORT": "Backend server port (default: 3001)",
    "FRONTEND_URL": "Frontend origin for CORS (default: http://localhost:3000)",
    "NETWORK": "Target network: arbitrumSepolia or arbitrum",
    "CHAIN_ID": "Chain ID (421614 for Sepolia, 42161 for mainnet)",
}

FRONTEND_ENV_VARS = {
    "NEXT_PUBLIC_CONTRACT_ADDRESS": "Deployed contract address (0x...)",
    "NEXT_PUBLIC_BACKEND_URL": "Backend API URL (default: http://localhost:3001)",
    "NEXT_PUBLIC_WALLET_CONNECT_ID": "WalletConnect project ID (from cloud.walletconnect.com)",
}

INDEXER_ENV_VARS = {
    "GRAPH_DEPLOY_KEY": "The Graph Studio deploy key (from thegraph.com/studio)",
    "SUBGRAPH_NAME": "Subgraph name in The Graph Studio",
}

ORACLE_ENV_VARS = {
    "ORACLE_CONTRACT_ADDRESS": "Deployed oracle consumer contract address",
}

# Network presets
NETWORK_CONFIGS = {
    "arbitrumSepolia": {
        "CHAIN_ID": "421614",
        "RPC_URL": "https://sepolia-rollup.arbitrum.io/rpc",
        "NETWORK": "arbitrumSepolia",
    },
    "arbitrum": {
        "CHAIN_ID": "42161",
        "RPC_URL": "https://arb1.arbitrum.io/rpc",
        "NETWORK": "arbitrum",
    },
}

# Default ports
BACKEND_PORT = "3001"
FRONTEND_PORT = "3000"


def generate_env_template(
    components: List[str],
    network: str = "arbitrumSepolia",
) -> str:
    """Generate a .env.example file with all required variables.

    Args:
        components: List of components (contract, backend, frontend, indexer, oracle).
        network: Target network for default values.

    Returns:
        String content for .env.example.
    """
    net_cfg = NETWORK_CONFIGS.get(network, NETWORK_CONFIGS["arbitrumSepolia"])
    lines = ["# ARBuilder dApp Environment Configuration", ""]

    # Shared / network
    lines.append("# Network")
    lines.append(f"NETWORK={net_cfg['NETWORK']}")
    lines.append(f"CHAIN_ID={net_cfg['CHAIN_ID']}")
    lines.append(f"RPC_URL={net_cfg['RPC_URL']}")
    lines.append("")

    # Contract
    if "contract" in components:
        lines.append("# Contract")
        lines.append("CONTRACT_ADDRESS=0x_DEPLOY_ADDRESS_HERE")
        lines.append("PRIVATE_KEY=0x_YOUR_PRIVATE_KEY_HERE")
        lines.append("")

    # Backend
    if "backend" in components:
        lines.append("# Backend")
        lines.append(f"PORT={BACKEND_PORT}")
        lines.append(f"FRONTEND_URL=http://localhost:{FRONTEND_PORT}")
        lines.append("")

    # Frontend
    if "frontend" in components:
        lines.append("# Frontend")
        lines.append("NEXT_PUBLIC_CONTRACT_ADDRESS=0x_DEPLOY_ADDRESS_HERE")
        lines.append(f"NEXT_PUBLIC_BACKEND_URL=http://localhost:{BACKEND_PORT}")
        lines.append("NEXT_PUBLIC_WALLET_CONNECT_ID=YOUR_WALLETCONNECT_PROJECT_ID")
        lines.append("")

    # Frontend — subgraph URL when indexer is present
    if "indexer" in components and "frontend" in components:
        lines.append("# Frontend — Subgraph")
        lines.append("NEXT_PUBLIC_SUBGRAPH_URL=https://api.thegraph.com/subgraphs/name/YOUR_SUBGRAPH")
        lines.append("")

    # Indexer
    if "indexer" in components:
        lines.append("# Indexer (The Graph)")
        lines.append("GRAPH_DEPLOY_KEY=YOUR_GRAPH_STUDIO_DEPLOY_KEY")
        lines.append("SUBGRAPH_NAME=my-subgraph")
        lines.append("")

    # Oracle
    if "oracle" in components:
        lines.append("# Oracle (Chainlink)")
        lines.append("ORACLE_CONTRACT_ADDRESS=0x_ORACLE_ADDRESS_HERE")
        lines.append("")

    return "\n".join(lines)

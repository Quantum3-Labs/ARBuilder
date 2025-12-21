"""
Arbitrum Network Configurations.

This resource provides network configurations for all Arbitrum networks
that Stylus contracts can be deployed to.
"""

NETWORK_CONFIGS = {
    "networks": {
        "arbitrum_sepolia": {
            "name": "Arbitrum Sepolia",
            "type": "testnet",
            "chain_id": 421614,
            "parent_chain": "Ethereum Sepolia",
            "rpc_endpoints": {
                "primary": "https://sepolia-rollup.arbitrum.io/rpc",
                "alternatives": [
                    "https://arbitrum-sepolia.blockpi.network/v1/rpc/public",
                    "https://arbitrum-sepolia.public.blastapi.io",
                ],
            },
            "explorer": {
                "url": "https://sepolia.arbiscan.io",
                "api": "https://api-sepolia.arbiscan.io/api",
            },
            "faucets": [
                {"name": "QuickNode", "url": "https://faucet.quicknode.com/arbitrum/sepolia"},
                {"name": "Alchemy", "url": "https://sepoliafaucet.com"},
                {"name": "Chainlink", "url": "https://faucets.chain.link/arbitrum-sepolia"},
            ],
            "native_currency": {
                "name": "Ethereum",
                "symbol": "ETH",
                "decimals": 18,
            },
            "stylus_support": True,
            "recommended_for": ["development", "testing", "staging"],
        },
        "arbitrum_one": {
            "name": "Arbitrum One",
            "type": "mainnet",
            "chain_id": 42161,
            "parent_chain": "Ethereum Mainnet",
            "rpc_endpoints": {
                "primary": "https://arb1.arbitrum.io/rpc",
                "alternatives": [
                    "https://arbitrum.llamarpc.com",
                    "https://arbitrum-one.public.blastapi.io",
                    "https://arbitrum.blockpi.network/v1/rpc/public",
                ],
            },
            "explorer": {
                "url": "https://arbiscan.io",
                "api": "https://api.arbiscan.io/api",
            },
            "bridge": {
                "url": "https://bridge.arbitrum.io",
                "token_bridge": "0x72Ce9c846789fdB6fC1f34aC4AD25Dd9ef7031ef",
            },
            "native_currency": {
                "name": "Ethereum",
                "symbol": "ETH",
                "decimals": 18,
            },
            "stylus_support": True,
            "recommended_for": ["production"],
            "warnings": [
                "MAINNET - Real funds at risk",
                "Thoroughly test on Sepolia before deploying",
                "Audit smart contracts before production deployment",
            ],
        },
        "arbitrum_nova": {
            "name": "Arbitrum Nova",
            "type": "mainnet",
            "chain_id": 42170,
            "parent_chain": "Ethereum Mainnet",
            "rpc_endpoints": {
                "primary": "https://nova.arbitrum.io/rpc",
                "alternatives": [
                    "https://arbitrum-nova.public.blastapi.io",
                ],
            },
            "explorer": {
                "url": "https://nova.arbiscan.io",
                "api": "https://api-nova.arbiscan.io/api",
            },
            "native_currency": {
                "name": "Ethereum",
                "symbol": "ETH",
                "decimals": 18,
            },
            "data_availability": "AnyTrust (DAC)",
            "stylus_support": True,
            "recommended_for": ["gaming", "social", "high-volume-low-value"],
            "notes": [
                "Lower fees than Arbitrum One",
                "Uses AnyTrust for data availability",
                "Best for applications with high transaction volume",
            ],
        },
    },
    "orbit_chains": {
        "description": "Custom L3 chains built on Arbitrum using Orbit",
        "examples": [
            {
                "name": "XAI",
                "chain_id": 660279,
                "type": "Gaming L3",
                "parent": "Arbitrum One",
            },
            {
                "name": "Degen Chain",
                "chain_id": 666666666,
                "type": "Social L3",
                "parent": "Base (Custom)",
            },
        ],
        "deploy_orbit": {
            "docs": "https://docs.arbitrum.io/launch-orbit-chain/orbit-gentle-introduction",
            "sdk": "npm install @arbitrum/orbit-sdk",
        },
    },
    "local_development": {
        "nitro_devnode": {
            "name": "Arbitrum Nitro Devnode",
            "description": "Local Arbitrum node for development",
            "docker_command": "docker run --rm -it -p 8547:8547 -p 8548:8548 offchainlabs/nitro-node:latest --dev",
            "rpc": "http://localhost:8547",
            "chain_id": 412346,
            "prefunded_accounts": [
                {
                    "address": "0x3f1Eae7D46d88F08fc2F8ed27FCb2AB183EB2d0E",
                    "private_key": "0xb6b15c8cb491557369f3c7d2c287b053eb229daa9c22138887752191c9520659",
                    "balance": "10000 ETH",
                },
            ],
        },
        "anvil_fork": {
            "name": "Anvil Fork",
            "description": "Fork Arbitrum Sepolia locally using Foundry",
            "command": "anvil --fork-url https://sepolia-rollup.arbitrum.io/rpc",
            "rpc": "http://localhost:8545",
            "notes": "State matches forked block, useful for integration testing",
        },
    },
    "gas_estimation": {
        "stylus_benefits": [
            "10-100x cheaper compute costs for WASM vs EVM",
            "Same storage costs as Solidity contracts",
            "One-time activation cost (compiles WASM to native)",
        ],
        "typical_costs": {
            "deployment": "0.001 - 0.01 ETH (depends on contract size)",
            "activation": "0.001 - 0.005 ETH (one-time)",
            "function_call": "Same as Solidity for storage, cheaper for compute",
        },
    },
    "common_rpc_methods": [
        {"method": "eth_chainId", "description": "Get chain ID", "example": "cast chain-id --rpc-url <RPC>"},
        {"method": "eth_blockNumber", "description": "Get latest block", "example": "cast block-number --rpc-url <RPC>"},
        {"method": "eth_getBalance", "description": "Get account balance", "example": "cast balance <ADDRESS> --rpc-url <RPC>"},
        {"method": "eth_call", "description": "Call contract function", "example": "cast call <ADDRESS> 'fn()' --rpc-url <RPC>"},
        {"method": "eth_sendRawTransaction", "description": "Send signed transaction", "example": "cast send <ADDRESS> 'fn()' --private-key <KEY> --rpc-url <RPC>"},
    ],
}

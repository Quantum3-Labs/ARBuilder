"""
Orbit Chain Development Rules Resource.

Provides rules, constraints, and patterns for deploying and configuring
Arbitrum Orbit chains using the Orbit SDK.
"""

ORBIT_RULES = {
    "name": "Orbit Chain Rules",
    "version": "1.0.0",
    "description": "Rules and constraints for Arbitrum Orbit chain deployment and configuration",

    "parent_chains": {
        "description": "An Orbit chain must be deployed on a supported parent chain",
        "supported_mainnets": {
            "ethereum_mainnet": {"chain_id": 1, "type": "L1"},
            "arbitrum_one": {"chain_id": 42161, "type": "L2"},
            "arbitrum_nova": {"chain_id": 42170, "type": "L2"},
            "base": {"chain_id": 8453, "type": "L2"},
        },
        "supported_testnets": {
            "sepolia": {"chain_id": 11155111, "type": "L1"},
            "arbitrum_sepolia": {"chain_id": 421614, "type": "L2"},
            "base_sepolia": {"chain_id": 84532, "type": "L2"},
        },
        "custom_parent_chains": {
            "description": "Custom parent chains can be registered via registerCustomParentChain()",
            "requirements": [
                "Must provide contracts.rollupCreator address (non-zero)",
                "Must provide contracts.tokenBridgeCreator address (non-zero)",
                "Must be a valid Chain object with RPC URLs",
            ],
        },
        "rules": [
            "L2 Orbit chains settle on Ethereum L1 (mainnet or sepolia)",
            "L3 Orbit chains settle on Arbitrum L2 (One, Sepolia, Nova, or Base)",
            "validateParentChain() is called automatically during createRollup()",
            "Deploying on an unsupported parent chain throws 'Parent chain not supported' error",
        ],
    },

    "chain_types": {
        "rollup": {
            "description": "Posts all transaction data to parent chain (L1)",
            "data_availability": "On-chain (parent chain calldata)",
            "security": "Inherits full parent chain security",
            "cost": "Higher — pays for L1 calldata",
            "config": "DataAvailabilityCommittee: false",
            "use_when": [
                "Maximum security needed",
                "High-value DeFi applications",
                "Trustless data availability required",
            ],
        },
        "anytrust": {
            "description": "Uses a Data Availability Committee (DAC) for off-chain data",
            "data_availability": "Off-chain via DAC; data availability certificate posted on-chain",
            "security": "Trust assumption: at least 1 DAC member is honest",
            "cost": "Lower — only posts certificates to L1, not full data",
            "config": "DataAvailabilityCommittee: true",
            "use_when": [
                "Cost-sensitive applications",
                "Gaming and social dApps",
                "High throughput needed",
                "Acceptable trust assumptions on DAC",
            ],
            "dac_setup": [
                "DAC members store full transaction data",
                "Minimum 1 honest DAC member guarantees data availability",
                "Configure DAC keyset after chain deployment",
                "Arbitrum Nova uses AnyTrust with a 6-member DAC",
            ],
        },
    },

    "custom_gas_tokens": {
        "description": "Orbit chains can use a custom ERC20 token as the native gas token instead of ETH",
        "requirements": [
            "Token MUST be an ERC20 on the parent chain",
            "Token MUST implement standard ERC20 interface (transfer, approve, balanceOf, totalSupply, decimals)",
            "Token decimals are handled — SDK scales from 18 decimals to native token decimals",
            "Must approve RollupCreator contract to spend tokens BEFORE calling createRollup",
            "Must also approve TokenBridgeCreator for token bridge deployment",
        ],
        "approval_flow": {
            "description": "The SDK handles approval checks and transactions automatically",
            "steps": [
                "1. createRollup() checks allowance via createRollupEnoughCustomFeeTokenAllowance()",
                "2. If insufficient, SDK sends approval transaction automatically",
                "3. Allowance must cover retryable ticket fees for factory deployment",
                "4. Same pattern applies for createTokenBridge()",
            ],
        },
        "config": {
            "param": "nativeToken",
            "default": "zeroAddress (ETH)",
            "note": "Pass the ERC20 token address on the parent chain",
        },
        "common_errors": [
            "Insufficient fee token allowance — approve RollupCreator first",
            "Token does not implement standard ERC20 — check transfer/approve functions",
            "Wrong token address — must be the address on the PARENT chain, not the Orbit chain",
        ],
    },

    "validators": {
        "description": "Validators assert state correctness and participate in challenge protocol",
        "rules": [
            "Minimum 1 validator required for createRollup()",
            "Validators array passed as required param: validators: [address1, address2, ...]",
            "Validators need ETH on the parent chain for staking",
            "v2.1: baseStake defaults to 0.1 ETH",
            "v3.1 (BoLD): uses assertion staking with buffer config",
            "Validators post assertions about the chain state",
            "If an assertion is challenged, validator must respond within challenge period",
            "Incorrect assertions result in stake being slashed",
        ],
        "v2_1_config": {
            "baseStake": "0.1 ETH (default)",
            "stakeToken": "zeroAddress (ETH by default)",
            "loserStakeEscrow": "zeroAddress (default)",
            "extraChallengeTimeBlocks": 0,
        },
        "v3_1_config": {
            "description": "BoLD (Bounded Liquidity Delay) challenge protocol",
            "bufferConfig": {
                "threshold": "2^32",
                "max": "2^32",
                "replenishRateInBasis": 500,
            },
            "layerZeroBlockEdgeHeight": "2^26",
            "layerZeroBigStepEdgeHeight": "2^19",
            "layerZeroSmallStepEdgeHeight": "2^23",
            "numBigStepLevel": 1,
        },
    },

    "batch_posters": {
        "description": "Batch posters collect transactions and post them to the parent chain",
        "rules": [
            "v3.1: supports MULTIPLE batch posters (batchPosters: Address[])",
            "v2.1: supports MULTIPLE batch posters (batchPosters: Address[])",
            "v1.1 (legacy): only supports ONE batch poster (batchPoster: Address)",
            "Batch posters sequence user transactions into batches",
            "Batch posters need ETH on the parent chain to pay for posting data",
            "Multiple batch posters provide redundancy and liveness guarantees",
        ],
        "note": "Both v2.1 and v3.1 accept batchPosters as an array; v1.1 used singular batchPoster",
    },

    "token_bridge": {
        "description": "Token bridge enables moving assets between parent and Orbit chain",
        "deployment_order": [
            "1. Deploy rollup first via createRollup()",
            "2. Wait for rollup to be confirmed and synced",
            "3. Deploy token bridge via createTokenBridge()",
            "4. Optionally set WETH gateway via createTokenBridgePrepareSetWethGatewayTransactionRequest()",
        ],
        "required_params": {
            "rollupOwner": "Address of the rollup owner",
            "rollupAddress": "Address of the deployed Rollup contract",
            "account": "PrivateKeyAccount for signing transactions",
            "parentChainPublicClient": "Viem PublicClient connected to parent chain",
            "orbitChainPublicClient": "Viem PublicClient connected to Orbit chain",
        },
        "optional_params": {
            "rollupDeploymentBlockNumber": "Block number of rollup deployment (for efficient log queries)",
            "nativeTokenAddress": "Custom gas token address if not ETH",
            "gasOverrides": "Custom gas settings",
            "retryableGasOverrides": "Override retryable ticket gas params",
        },
        "weth_gateway": {
            "description": "Optional WETH gateway for wrapping/unwrapping native ETH",
            "note": "Only deploy if the chain uses ETH as native token and WETH bridging is needed",
            "function": "createTokenBridgePrepareSetWethGatewayTransactionRequest()",
        },
        "checks": {
            "isTokenBridgeDeployed": "Check if token bridge is already deployed before attempting deployment",
        },
        "common_errors": [
            "Deploying bridge before rollup is confirmed",
            "Orbit chain node not synced — bridge deployment requires both chains accessible",
            "Missing custom fee token approval for TokenBridgeCreator",
            "Wrong rollupAddress — must be the Rollup proxy address from core contracts",
        ],
    },

    "chain_config": {
        "description": "On-chain genesis configuration embedded in the rollup creation",
        "required_params": {
            "chainId": "Unique chain ID for the Orbit chain (must not conflict with existing chains)",
            "InitialChainOwner": "REQUIRED — address that controls UpgradeExecutor and chain admin functions",
        },
        "defaults": {
            "EnableArbOS": True,
            "AllowDebugPrecompiles": False,
            "DataAvailabilityCommittee": False,
            "InitialArbOSVersion": 51,
            "GenesisBlockNum": 0,
            "MaxCodeSize": 24576,
            "MaxInitCodeSize": 49152,
        },
        "function": "prepareChainConfig({ chainId, arbitrum: { InitialChainOwner, ... } })",
        "rules": [
            "chainId must be unique — do not reuse existing chain IDs",
            "InitialChainOwner is REQUIRED and cannot be omitted",
            "DataAvailabilityCommittee=true for AnyTrust, false for Rollup",
            "MaxCodeSize=24576 (24KB) is the default contract size limit",
            "Chain config is immutable once deployed — cannot be changed after creation",
        ],
    },

    "node_config": {
        "description": "Nitro node configuration (separate from on-chain chain config)",
        "format": "JSON configuration file",
        "distinction": [
            "Chain config: on-chain genesis state, set during createRollup()",
            "Node config: off-chain node parameters, used when running a Nitro node",
            "Chain config is immutable; node config can be changed by restarting the node",
        ],
        "key_settings": [
            "RPC endpoints and ports",
            "Sequencer configuration",
            "Batch poster settings",
            "Validator and staker settings",
            "Data availability configuration",
            "Parent chain connection details",
        ],
        "note": "The Orbit SDK generates node config via NodeConfig types — see NodeConfig.generated.ts",
    },

    "rollup_creator_versions": {
        "v3_1": {
            "description": "Latest version with BoLD challenge protocol and multi-batch-poster support",
            "features": [
                "BoLD (Bounded Liquidity Delay) challenge protocol",
                "Multiple batch posters (batchPosters: Address[])",
                "Buffer configuration for challenge timing",
                "Assertion state management",
                "anyTrustFastConfirmer support",
            ],
            "default": True,
            "unique_params": [
                "bufferConfig (threshold, max, replenishRateInBasis)",
                "genesisAssertionState",
                "genesisInboxCount",
                "layerZeroBlockEdgeHeight",
                "layerZeroBigStepEdgeHeight",
                "layerZeroSmallStepEdgeHeight",
                "numBigStepLevel",
                "anyTrustFastConfirmer",
            ],
        },
        "v2_1": {
            "description": "Stable version with classic challenge protocol",
            "features": [
                "Classic challenge protocol",
                "Multiple batch posters (batchPosters: Address[])",
                "Simple stake-based validation",
            ],
            "unique_params": [
                "extraChallengeTimeBlocks",
                "stakeToken",
                "baseStake",
                "loserStakeEscrow",
            ],
        },
        "v1_1": {
            "description": "Legacy version (not supported for new deployments)",
            "note": "Uses singular batchPoster instead of batchPosters array",
            "supported": False,
        },
        "selection": "Defaults to v3.1 if not specified; pass rollupCreatorVersion: 'v2.1' for stable",
    },

    "initial_chain_owner": {
        "description": "The address that controls the UpgradeExecutor and chain admin functions",
        "rules": [
            "REQUIRED field in prepareChainConfig() — deployment will fail without it",
            "In production, MUST be a multisig (e.g., Gnosis Safe) for security",
            "Controls UpgradeExecutor which can upgrade chain contracts",
            "Can add/remove validators and batch posters",
            "Can modify chain parameters via admin functions",
            "Single point of control — compromise means full chain compromise",
        ],
        "best_practices": [
            "Use a multisig wallet (Gnosis Safe) in production",
            "Use timelock for upgrade delays",
            "Document the owner address and recovery procedures",
            "Test with EOA on testnet, then transfer to multisig before mainnet",
        ],
    },

    "common_errors": {
        "insufficient_fee_token_allowance": {
            "error": "Custom fee token allowance insufficient",
            "cause": "RollupCreator or TokenBridgeCreator not approved to spend custom gas token",
            "fix": "SDK handles this automatically, but if using low-level functions, call createRollupPrepareCustomFeeTokenApprovalTransactionRequest() first",
        },
        "wrong_parent_chain_id": {
            "error": "Parent chain not supported: <chainId>",
            "cause": "Attempting to deploy on an unsupported parent chain",
            "fix": "Use a supported parent chain or register custom chain via registerCustomParentChain()",
        },
        "missing_validator_staking": {
            "error": "Insufficient validator stake",
            "cause": "Validator address does not have enough ETH for staking on parent chain",
            "fix": "Fund validator address with at least baseStake amount (default 0.1 ETH) on parent chain",
        },
        "node_not_synced": {
            "error": "Token bridge deployment fails or hangs",
            "cause": "Orbit chain node not fully synced when deploying token bridge",
            "fix": "Wait for Orbit chain node to sync fully before deploying token bridge; verify with eth_blockNumber RPC call",
        },
        "chain_id_conflict": {
            "error": "Chain ID already in use",
            "cause": "Chosen chainId conflicts with an existing network",
            "fix": "Choose a unique chainId that does not conflict with any known chain",
        },
        "deploy_factories_failure": {
            "error": "Factory deployment via retryable tickets fails",
            "cause": "deployFactoriesToL2 (default: true) requires sufficient gas for retryable tickets",
            "fix": "Ensure parent chain account has enough ETH for retryable ticket fees; or set deployFactoriesToL2: false and deploy manually",
        },
    },

    "deployment_flow": {
        "description": "End-to-end Orbit chain deployment sequence",
        "steps": [
            "1. Choose chain type: Rollup (DataAvailabilityCommittee: false) or AnyTrust (true)",
            "2. Prepare chain config: prepareChainConfig({ chainId, arbitrum: { InitialChainOwner, ... } })",
            "3. Prepare deployment params: createRollupPrepareDeploymentParamsConfig()",
            "4. If custom gas token: SDK auto-approves RollupCreator spending",
            "5. Deploy rollup: createRollup({ params, account, parentChainPublicClient })",
            "6. Extract core contracts: txReceipt.getCoreContracts()",
            "7. Start Orbit chain node with generated node config",
            "8. Wait for node to sync",
            "9. Deploy token bridge: createTokenBridge({ rollupAddress, ... })",
            "10. Optionally set WETH gateway",
            "11. Configure DAC keyset (AnyTrust only)",
        ],
    },

    "sdk_usage": {
        "install": "npm install @arbitrum/orbit-sdk viem",
        "import_example": '''import {
  createRollup,
  prepareChainConfig,
  createRollupPrepareDeploymentParamsConfig,
  createTokenBridge,
  createTokenBridgePrepareSetWethGatewayTransactionRequest,
} from '@arbitrum/orbit-sdk';
import { createPublicClient, http } from 'viem';
import { arbitrumSepolia } from 'viem/chains';''',
        "minimal_example": '''import { createRollup, prepareChainConfig } from '@arbitrum/orbit-sdk';
import { createPublicClient, http } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { arbitrumSepolia } from 'viem/chains';

const deployer = privateKeyToAccount('0x...');

const parentChainPublicClient = createPublicClient({
  chain: arbitrumSepolia,
  transport: http(),
});

const chainConfig = prepareChainConfig({
  chainId: 94692,
  arbitrum: {
    InitialChainOwner: deployer.address,
    DataAvailabilityCommittee: false,  // Rollup mode
  },
});

const { coreContracts } = await createRollup({
  params: {
    config: createRollupPrepareDeploymentParamsConfig(parentChainPublicClient, {
      chainId: BigInt(94692),
      owner: deployer.address,
      chainConfig,
    }),
    batchPosters: [deployer.address],
    validators: [deployer.address],
  },
  account: deployer,
  parentChainPublicClient,
});

console.log('Rollup deployed:', coreContracts.rollup);''',
    },

    "key_contracts": {
        "core": {
            "rollup": "Main Rollup contract — manages assertions and challenges",
            "bridge": "Bridge contract — holds funds and routes messages",
            "inbox": "Inbox contract — receives L1-to-L2 messages and transactions",
            "outbox": "Outbox contract — processes L2-to-L1 messages after challenge period",
            "sequencerInbox": "SequencerInbox — receives batched transactions from batch poster",
            "rollupEventInbox": "RollupEventInbox — processes chain initialization events",
            "upgradeExecutor": "UpgradeExecutor — controlled by InitialChainOwner, manages upgrades",
        },
        "token_bridge": {
            "parentGatewayRouter": "Routes token deposits to correct gateway on parent chain",
            "childGatewayRouter": "Routes token operations on Orbit chain",
            "parentErc20Gateway": "Standard ERC20 gateway on parent chain",
            "childErc20Gateway": "Standard ERC20 gateway on Orbit chain",
            "parentWethGateway": "WETH-specific gateway on parent chain (optional)",
            "childWethGateway": "WETH-specific gateway on Orbit chain (optional)",
        },
    },

    "documentation": {
        "orbit_sdk": "https://docs.arbitrum.io/launch-orbit-chain/orbit-sdk-introduction",
        "orbit_quickstart": "https://docs.arbitrum.io/launch-orbit-chain/orbit-quickstart",
        "chain_config": "https://docs.arbitrum.io/launch-orbit-chain/reference/additional-configuration-parameters",
        "custom_gas_token": "https://docs.arbitrum.io/launch-orbit-chain/concepts/custom-gas-token-sdk",
        "github_repo": "https://github.com/OffchainLabs/arbitrum-orbit-sdk",
    },
}

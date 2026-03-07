"""
Orbit chain templates for Arbitrum L3 deployment.

These templates provide scaffolding for deploying and managing
Orbit chains (L3s) using the @arbitrum/orbit-sdk.

Templates:
- Chain Config: Prepare chain configuration
- Deploy Rollup: Deploy rollup contracts
- Deploy Token Bridge: Deploy token bridge
- Custom Gas Token: Deploy with custom gas token
- Validator Management: Manage validators and batch posters
- Governance: UpgradeExecutor operations
- Node Config: Nitro node configuration
- AnyTrust Config: DAC keyset management
- Orchestration: Full project scaffold (package.json, scripts, etc.)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class OrbitTemplate:
    """A curated Orbit chain template."""

    name: str
    description: str
    template_type: str  # "config" | "deployment" | "management" | "orchestration"
    features: List[str]
    code: str  # TypeScript code
    dependencies: Dict[str, str]
    env_vars: List[str] = field(default_factory=list)
    files: Dict[str, str] = field(default_factory=dict)


# Default dependencies shared by all Orbit templates
ORBIT_DEPENDENCIES = {
    "@arbitrum/orbit-sdk": "^0.25.0",
    "viem": "^1.20.0",
    "dotenv": "^16.4.0",
}

# Parent chain RPC URLs
PARENT_CHAIN_RPCS = {
    "arbitrum-one": "https://arb1.arbitrum.io/rpc",
    "arbitrum-sepolia": "https://sepolia-rollup.arbitrum.io/rpc",
    "ethereum-mainnet": "https://eth.llamarpc.com",
    "ethereum-sepolia": "https://rpc.sepolia.org",
}


# 1. Chain Config Template
CHAIN_CONFIG_TEMPLATE = OrbitTemplate(
    name="Orbit Chain Config",
    description="Prepare chain configuration for an Orbit chain using prepareChainConfig()",
    template_type="config",
    features=[
        "Chain ID configuration",
        "Initial chain owner setup",
        "Rollup vs AnyTrust selection",
        "Data availability mode",
    ],
    code='''import 'dotenv/config';
import { prepareChainConfig } from '@arbitrum/orbit-sdk';

/**
 * Prepare the chain configuration for a new Orbit chain.
 *
 * This generates the chainConfig JSON that will be passed to createRollup().
 * It defines the core parameters of your Orbit chain.
 */
async function main() {
  const chainConfig = prepareChainConfig({
    chainId: {chain_id},
    arbitrum: {
      InitialChainOwner: '{owner}' as `0x${{string}}`,
      DataAvailabilityCommittee: {is_anytrust},
    },
  });

  console.log('Chain Config:');
  console.log(JSON.stringify(chainConfig, null, 2));
  return chainConfig;
}

main().catch(console.error);
''',
    dependencies=ORBIT_DEPENDENCIES,
    env_vars=["DEPLOYER_PRIVATE_KEY", "PARENT_CHAIN_RPC"],
)


# 2. Deploy Rollup Template
DEPLOY_ROLLUP_TEMPLATE = OrbitTemplate(
    name="Orbit Deploy Rollup",
    description="Deploy a new Orbit rollup chain using createRollup()",
    template_type="deployment",
    features=[
        "Full rollup deployment",
        "Validator configuration",
        "Batch poster setup",
        "Native token support",
        "Rollup version selection (v2.1/v3.1)",
        "Saves deployment output to deployment.json",
    ],
    code='''import 'dotenv/config';
import * as fs from 'fs';
import {{
  createPublicClient,
  createWalletClient,
  http,
  parseEther,
  Chain,
}} from 'viem';
import {{ privateKeyToAccount }} from 'viem/accounts';
import {{
  prepareChainConfig,
  createRollup,
  createRollupPrepareDeploymentParamsConfig,
}} from '@arbitrum/orbit-sdk';

// Parent chain configuration
const parentChain: Chain = {{
  id: {parent_chain_id},
  name: '{parent_chain_name}',
  nativeCurrency: {{ name: 'Ether', symbol: 'ETH', decimals: 18 }},
  rpcUrls: {{
    default: {{ http: [process.env.PARENT_CHAIN_RPC!] }},
  }},
}};

async function main() {{
  const account = privateKeyToAccount(
    process.env.DEPLOYER_PRIVATE_KEY! as `0x${{string}}`
  );

  const publicClient = createPublicClient({{
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  }});

  const walletClient = createWalletClient({{
    account,
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  }});

  // Prepare chain config
  const chainConfig = prepareChainConfig({{
    chainId: {chain_id},
    arbitrum: {{
      InitialChainOwner: account.address,
      DataAvailabilityCommittee: {is_anytrust},
    }},
  }});

  console.log('Deploying Orbit chain...');
  console.log('  Chain ID:', {chain_id});
  console.log('  Owner:', account.address);
  console.log('  AnyTrust:', {is_anytrust});

  // Deploy rollup
  const deployResult = await createRollup({{
    params: {{
      config: createRollupPrepareDeploymentParamsConfig(publicClient, {{
        chainId: BigInt({chain_id}),
        owner: account.address,
        chainConfig,
      }}),
      validators: {validators_array},
      batchPosters: {batch_posters_array},
      batchPosterManager: account.address,{native_token_line}
    }},
    account,
    publicClient,
    walletClient,
  }});

  console.log('\\nRollup deployed successfully!');
  console.log('Transaction hash:', deployResult.transactionHash);
  console.log('\\nCore contracts:');
  console.log('  Rollup:', deployResult.coreContracts.rollup);
  console.log('  Inbox:', deployResult.coreContracts.inbox);
  console.log('  Outbox:', deployResult.coreContracts.outbox);
  console.log('  Bridge:', deployResult.coreContracts.bridge);
  console.log('  SequencerInbox:', deployResult.coreContracts.sequencerInbox);
  console.log('  RollupEventInbox:', deployResult.coreContracts.rollupEventInbox);
  console.log('  UpgradeExecutor:', deployResult.coreContracts.upgradeExecutor);

  // Save deployment output for downstream scripts
  const deployment = {{
    chainId: {chain_id},
    parentChainId: {parent_chain_id},
    transactionHash: deployResult.transactionHash,
    chainConfig,
    coreContracts: deployResult.coreContracts,
    deployer: account.address,
    timestamp: new Date().toISOString(),
  }};
  fs.writeFileSync('deployment.json', JSON.stringify(deployment, null, 2));
  console.log('\\nDeployment saved to deployment.json');
}}

main().catch(console.error);
''',
    dependencies=ORBIT_DEPENDENCIES,
    env_vars=["DEPLOYER_PRIVATE_KEY", "PARENT_CHAIN_RPC"],
)


# 3. Deploy Token Bridge Template
DEPLOY_TOKEN_BRIDGE_TEMPLATE = OrbitTemplate(
    name="Orbit Token Bridge",
    description="Deploy a token bridge for an Orbit chain using createTokenBridge()",
    template_type="deployment",
    features=[
        "Token bridge deployment",
        "Reads rollup address from deployment.json",
        "L2/L3 bridge contracts",
        "Gateway router setup",
        "Standard ERC20 gateway",
    ],
    code='''import 'dotenv/config';
import * as fs from 'fs';
import {
  createPublicClient,
  createWalletClient,
  http,
  Chain,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { createTokenBridge } from '@arbitrum/orbit-sdk';

// Parent chain configuration
const parentChain: Chain = {
  id: {parent_chain_id},
  name: '{parent_chain_name}',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: {
    default: { http: [process.env.PARENT_CHAIN_RPC!] },
  },
};

async function main() {
  // Read rollup address from deployment.json (output of deploy-rollup.ts)
  let rollupAddress: `0x${string}` = '{rollup_address}' as `0x${string}`;
  let orbitChainId = {chain_id};

  if (fs.existsSync('deployment.json')) {
    const deployment = JSON.parse(fs.readFileSync('deployment.json', 'utf-8'));
    rollupAddress = deployment.coreContracts.rollup as `0x${string}`;
    orbitChainId = deployment.chainId ?? orbitChainId;
    console.log('Loaded deployment.json — rollup:', rollupAddress);
  } else {
    console.log('Warning: deployment.json not found, using placeholder rollup address.');
    console.log('Run deploy-rollup.ts first, or set rollupAddress manually.');
  }

  // Orbit chain configuration
  const orbitChain: Chain = {
    id: orbitChainId,
    name: '{chain_name}',
    nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
    rpcUrls: {
      default: { http: [process.env.ORBIT_CHAIN_RPC!] },
    },
  };

  const account = privateKeyToAccount(
    process.env.DEPLOYER_PRIVATE_KEY! as `0x${string}`
  );

  const parentPublicClient = createPublicClient({
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  });

  const parentWalletClient = createWalletClient({
    account,
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  });

  const orbitPublicClient = createPublicClient({
    chain: orbitChain,
    transport: http(process.env.ORBIT_CHAIN_RPC),
  });

  console.log('Deploying token bridge...');
  console.log('  Rollup address:', rollupAddress);

  const tokenBridgeResult = await createTokenBridge({
    rollupAddress,
    rollupOwner: account.address,
    parentChainPublicClient: parentPublicClient,
    orbitChainPublicClient: orbitPublicClient,
    account,
    parentChainWalletClient: parentWalletClient,
  });

  console.log('\\nToken bridge deployed successfully!');
  console.log('\\nParent chain contracts:');
  console.log('  Router:', tokenBridgeResult.parentChainContracts.router);
  console.log('  StandardGateway:', tokenBridgeResult.parentChainContracts.standardGateway);
  console.log('\\nOrbit chain contracts:');
  console.log('  Router:', tokenBridgeResult.orbitChainContracts.router);
  console.log('  StandardGateway:', tokenBridgeResult.orbitChainContracts.standardGateway);

  // Update deployment.json with token bridge contracts
  if (fs.existsSync('deployment.json')) {
    const deployment = JSON.parse(fs.readFileSync('deployment.json', 'utf-8'));
    deployment.tokenBridgeContracts = {
      parentChain: tokenBridgeResult.parentChainContracts,
      orbitChain: tokenBridgeResult.orbitChainContracts,
    };
    fs.writeFileSync('deployment.json', JSON.stringify(deployment, null, 2));
    console.log('\\nUpdated deployment.json with token bridge contracts');
  }
}

main().catch(console.error);
''',
    dependencies=ORBIT_DEPENDENCIES,
    env_vars=["DEPLOYER_PRIVATE_KEY", "PARENT_CHAIN_RPC", "ORBIT_CHAIN_RPC"],
)


# 4. Custom Gas Token Template
CUSTOM_GAS_TOKEN_TEMPLATE = OrbitTemplate(
    name="Orbit Custom Gas Token",
    description="Deploy an Orbit chain with a custom ERC20 gas token",
    template_type="deployment",
    features=[
        "Custom gas token approval",
        "ERC20 native token rollup",
        "Token approval flow",
        "Gas token configuration",
    ],
    code='''import 'dotenv/config';
import {
  createPublicClient,
  createWalletClient,
  http,
  parseUnits,
  Chain,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import {
  prepareChainConfig,
  createRollup,
  createRollupPrepareDeploymentParamsConfig,
} from '@arbitrum/orbit-sdk';

// ERC20 ABI for token approval
const erc20Abi = [
  {
    name: 'approve',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'spender', type: 'address' },
      { name: 'amount', type: 'uint256' },
    ],
    outputs: [{ name: '', type: 'bool' }],
  },
  {
    name: 'allowance',
    type: 'function',
    stateMutability: 'view',
    inputs: [
      { name: 'owner', type: 'address' },
      { name: 'spender', type: 'address' },
    ],
    outputs: [{ name: '', type: 'uint256' }],
  },
] as const;

const parentChain: Chain = {
  id: {parent_chain_id},
  name: '{parent_chain_name}',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: {
    default: { http: [process.env.PARENT_CHAIN_RPC!] },
  },
};

async function main() {
  const account = privateKeyToAccount(
    process.env.DEPLOYER_PRIVATE_KEY! as `0x${string}`
  );

  const nativeToken = '{native_token}' as `0x${string}`;

  const publicClient = createPublicClient({
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  });

  const walletClient = createWalletClient({
    account,
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  });

  // Step 1: Approve the native token for the rollup creator
  console.log('Approving native token for rollup deployment...');
  console.log('  Token:', nativeToken);

  // The rollup creator needs allowance to transfer the native token
  // Approve a large amount for deployment
  const approvalAmount = parseUnits('1000000', 18);

  const approveHash = await walletClient.writeContract({
    address: nativeToken,
    abi: erc20Abi,
    functionName: 'approve',
    args: [
      // RollupCreator address — consult SDK docs for the correct address
      '0x0000000000000000000000000000000000000000' as `0x${string}`,
      approvalAmount,
    ],
  });

  await publicClient.waitForTransactionReceipt({ hash: approveHash });
  console.log('Token approved');

  // Step 2: Prepare chain config
  const chainConfig = prepareChainConfig({
    chainId: {chain_id},
    arbitrum: {
      InitialChainOwner: account.address,
      DataAvailabilityCommittee: {is_anytrust},
    },
  });

  // Step 3: Deploy rollup with native token
  console.log('Deploying Orbit chain with custom gas token...');

  const deployResult = await createRollup({
    params: {
      config: createRollupPrepareDeploymentParamsConfig(publicClient, {
        chainId: BigInt({chain_id}),
        owner: account.address,
        chainConfig,
      }),
      validators: {validators_array},
      batchPosters: {batch_posters_array},
      batchPosterManager: account.address,
      nativeToken,
    },
    account,
    publicClient,
    walletClient,
  });

  console.log('\\nOrbit chain with custom gas token deployed!');
  console.log('Transaction hash:', deployResult.transactionHash);
  console.log('Native token:', nativeToken);
  console.log('\\nCore contracts:');
  console.log('  Rollup:', deployResult.coreContracts.rollup);
  console.log('  Inbox:', deployResult.coreContracts.inbox);
  console.log('  Bridge:', deployResult.coreContracts.bridge);
}

main().catch(console.error);
''',
    dependencies=ORBIT_DEPENDENCIES,
    env_vars=["DEPLOYER_PRIVATE_KEY", "PARENT_CHAIN_RPC"],
)


# 5. Validator Management Template
VALIDATOR_MANAGEMENT_TEMPLATE = OrbitTemplate(
    name="Orbit Validator Management",
    description="Query and manage validators and batch posters for an Orbit chain",
    template_type="management",
    features=[
        "List validators",
        "List batch posters",
        "Add/remove validators",
        "Batch poster management",
    ],
    code='''import 'dotenv/config';
import {
  createPublicClient,
  createWalletClient,
  http,
  Chain,
  getAddress,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';

// Rollup contract ABI (subset for validator/batch poster queries)
const rollupAbi = [
  {
    name: 'isValidator',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'validator', type: 'address' }],
    outputs: [{ name: '', type: 'bool' }],
  },
] as const;

// SequencerInbox ABI for batch poster queries
const sequencerInboxAbi = [
  {
    name: 'isBatchPoster',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'addr', type: 'address' }],
    outputs: [{ name: '', type: 'bool' }],
  },
] as const;

const parentChain: Chain = {
  id: {parent_chain_id},
  name: '{parent_chain_name}',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: {
    default: { http: [process.env.PARENT_CHAIN_RPC!] },
  },
};

async function main() {
  const account = privateKeyToAccount(
    process.env.DEPLOYER_PRIVATE_KEY! as `0x${string}`
  );

  const publicClient = createPublicClient({
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  });

  const rollupAddress = '{rollup_address}' as `0x${string}`;
  const sequencerInboxAddress = '{sequencer_inbox}' as `0x${string}`;

  // Check if specific addresses are validators
  const addressesToCheck: `0x${string}`[] = {addresses_array};

  console.log('=== Validator Status ===');
  for (const addr of addressesToCheck) {
    const isValidator = await publicClient.readContract({
      address: rollupAddress,
      abi: rollupAbi,
      functionName: 'isValidator',
      args: [addr],
    });
    console.log(`  ${addr}: ${isValidator ? 'VALIDATOR' : 'not a validator'}`);
  }

  console.log('\\n=== Batch Poster Status ===');
  for (const addr of addressesToCheck) {
    const isBatchPoster = await publicClient.readContract({
      address: sequencerInboxAddress,
      abi: sequencerInboxAbi,
      functionName: 'isBatchPoster',
      args: [addr],
    });
    console.log(`  ${addr}: ${isBatchPoster ? 'BATCH POSTER' : 'not a batch poster'}`);
  }
}

main().catch(console.error);
''',
    dependencies=ORBIT_DEPENDENCIES,
    env_vars=["DEPLOYER_PRIVATE_KEY", "PARENT_CHAIN_RPC"],
)


# 6. Governance Template
GOVERNANCE_TEMPLATE = OrbitTemplate(
    name="Orbit Governance",
    description="Execute governance operations via UpgradeExecutor",
    template_type="management",
    features=[
        "UpgradeExecutor operations",
        "Role-based access control",
        "Contract upgrades",
        "Admin operations",
    ],
    code='''import 'dotenv/config';
import {
  createPublicClient,
  createWalletClient,
  http,
  encodeFunctionData,
  Chain,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';

// UpgradeExecutor ABI
const upgradeExecutorAbi = [
  {
    name: 'execute',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'target', type: 'address' },
      { name: 'data', type: 'bytes' },
    ],
    outputs: [],
  },
  {
    name: 'executeCall',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'target', type: 'address' },
      { name: 'data', type: 'bytes' },
    ],
    outputs: [],
  },
  {
    name: 'hasRole',
    type: 'function',
    stateMutability: 'view',
    inputs: [
      { name: 'role', type: 'bytes32' },
      { name: 'account', type: 'address' },
    ],
    outputs: [{ name: '', type: 'bool' }],
  },
] as const;

// Role identifiers
const EXECUTOR_ROLE = '0xd8aa0f3194971a2a116679f7c2090f6939c8d4e01a2a8d7e41d55e5351469e63';
const ADMIN_ROLE = '0xa49807205ce4d355092ef5a8a18f56e8913cf4a201fbe287825b095693c21775';

const parentChain: Chain = {
  id: {parent_chain_id},
  name: '{parent_chain_name}',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: {
    default: { http: [process.env.PARENT_CHAIN_RPC!] },
  },
};

async function main() {
  const account = privateKeyToAccount(
    process.env.DEPLOYER_PRIVATE_KEY! as `0x${string}`
  );

  const publicClient = createPublicClient({
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  });

  const walletClient = createWalletClient({
    account,
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  });

  const upgradeExecutorAddress = '{upgrade_executor}' as `0x${string}`;

  // Check roles
  const hasExecutorRole = await publicClient.readContract({
    address: upgradeExecutorAddress,
    abi: upgradeExecutorAbi,
    functionName: 'hasRole',
    args: [EXECUTOR_ROLE as `0x${string}`, account.address],
  });

  console.log('Has executor role:', hasExecutorRole);

  if (!hasExecutorRole) {
    console.error('Account does not have executor role on UpgradeExecutor');
    process.exit(1);
  }

  // Example: Execute a call through the UpgradeExecutor
  // This can be used for contract upgrades, parameter changes, etc.
  const targetContract = '{target_contract}' as `0x${string}`;
  const callData = '{call_data}' as `0x${string}`;

  console.log('Executing governance action...');
  console.log('  Target:', targetContract);

  const txHash = await walletClient.writeContract({
    address: upgradeExecutorAddress,
    abi: upgradeExecutorAbi,
    functionName: 'executeCall',
    args: [targetContract, callData],
  });

  const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
  console.log('Governance action executed!');
  console.log('  Transaction:', receipt.transactionHash);
  console.log('  Status:', receipt.status);
}

main().catch(console.error);
''',
    dependencies=ORBIT_DEPENDENCIES,
    env_vars=["DEPLOYER_PRIVATE_KEY", "PARENT_CHAIN_RPC"],
)


# 7. Node Config Template
NODE_CONFIG_TEMPLATE = OrbitTemplate(
    name="Orbit Node Config",
    description="Generate Nitro node configuration for an Orbit chain",
    template_type="config",
    features=[
        "Nitro node configuration",
        "Reads deployment.json from deploy-rollup output",
        "Private key handling (strips 0x prefix for Nitro)",
        "Sequencer configuration",
    ],
    code='''import 'dotenv/config';
import * as fs from 'fs';
import { prepareNodeConfig } from '@arbitrum/orbit-sdk';
import { zeroAddress } from 'viem';

/**
 * Generate Nitro node configuration from deployment output.
 *
 * Reads deployment.json (created by deploy-rollup.ts) and generates
 * the nodeConfig.json required by the Nitro node.
 */
async function main() {
  // Read deployment output
  if (!fs.existsSync('deployment.json')) {
    console.error('Error: deployment.json not found.');
    console.error('Run deploy-rollup.ts first to create it.');
    process.exit(1);
  }

  const deployment = JSON.parse(fs.readFileSync('deployment.json', 'utf-8'));
  console.log('Loaded deployment.json');
  console.log('  Chain ID:', deployment.chainId);
  console.log('  Rollup:', deployment.coreContracts.rollup);

  // Private keys for batch poster and validator (strip 0x prefix for Nitro)
  const batchPosterKey = (process.env.BATCH_POSTER_PRIVATE_KEY ?? process.env.DEPLOYER_PRIVATE_KEY!).replace(/^0x/, '');
  const validatorKey = (process.env.VALIDATOR_PRIVATE_KEY ?? process.env.DEPLOYER_PRIVATE_KEY!).replace(/^0x/, '');

  // Generate node configuration using the actual SDK API
  const nodeConfig = prepareNodeConfig({
    chainName: '{chain_name}',
    chainConfig: deployment.chainConfig,
    coreContracts: deployment.coreContracts,
    batchPosterPrivateKey: batchPosterKey,
    validatorPrivateKey: validatorKey,
    stakeToken: zeroAddress,
    parentChainId: {parent_chain_id},
    parentChainIsArbitrum: {parent_chain_is_arbitrum},
    parentChainRpcUrl: process.env.PARENT_CHAIN_RPC!,
  });

  console.log('\\nNode Configuration:');
  console.log(JSON.stringify(nodeConfig, null, 2));

  fs.writeFileSync('nodeConfig.json', JSON.stringify(nodeConfig, null, 2));
  console.log('\\nSaved to nodeConfig.json');
  console.log('\\nNext: Start the Nitro node with this config.');
  console.log('  docker-compose up -d  (if using docker-compose.yml)');
}

main().catch(console.error);
''',
    dependencies=ORBIT_DEPENDENCIES,
    env_vars=["DEPLOYER_PRIVATE_KEY", "PARENT_CHAIN_RPC", "BATCH_POSTER_PRIVATE_KEY", "VALIDATOR_PRIVATE_KEY"],
)


# 8. AnyTrust Config Template
ANYTRUST_CONFIG_TEMPLATE = OrbitTemplate(
    name="Orbit AnyTrust Config",
    description="Configure AnyTrust Data Availability Committee (DAC) keyset",
    template_type="config",
    features=[
        "DAC keyset management",
        "Keyset validation",
        "setValidKeyset() operations",
        "AnyTrust committee setup",
    ],
    code='''import 'dotenv/config';
import {
  createPublicClient,
  createWalletClient,
  http,
  encodeAbiParameters,
  Chain,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';

// SequencerInbox ABI for keyset management
const sequencerInboxAbi = [
  {
    name: 'setValidKeyset',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [{ name: 'keysetBytes', type: 'bytes' }],
    outputs: [],
  },
  {
    name: 'isValidKeysetHash',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'ksHash', type: 'bytes32' }],
    outputs: [{ name: '', type: 'bool' }],
  },
] as const;

const parentChain: Chain = {
  id: {parent_chain_id},
  name: '{parent_chain_name}',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: {
    default: { http: [process.env.PARENT_CHAIN_RPC!] },
  },
};

async function main() {
  const account = privateKeyToAccount(
    process.env.DEPLOYER_PRIVATE_KEY! as `0x${string}`
  );

  const publicClient = createPublicClient({
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  });

  const walletClient = createWalletClient({
    account,
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  });

  const sequencerInboxAddress = '{sequencer_inbox}' as `0x${string}`;

  // DAC member public keys (BLS keys)
  // Replace with actual DAC member keys
  const dacMembers = {dac_members_array};

  // Construct keyset bytes
  // Format: [numMembers (uint64), ...member BLS pubkeys]
  // This is a simplified example — consult Orbit SDK docs for exact format
  const keysetBytes = '{keyset_bytes}' as `0x${string}`;

  console.log('Setting valid keyset on SequencerInbox...');
  console.log('  SequencerInbox:', sequencerInboxAddress);
  console.log('  DAC members:', dacMembers.length);

  // Set the valid keyset
  // Note: This must be called through the UpgradeExecutor if access-controlled
  const txHash = await walletClient.writeContract({
    address: sequencerInboxAddress,
    abi: sequencerInboxAbi,
    functionName: 'setValidKeyset',
    args: [keysetBytes],
  });

  const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
  console.log('\\nKeyset set successfully!');
  console.log('  Transaction:', receipt.transactionHash);
  console.log('  Status:', receipt.status);
}

main().catch(console.error);
''',
    dependencies=ORBIT_DEPENDENCIES,
    env_vars=["DEPLOYER_PRIVATE_KEY", "PARENT_CHAIN_RPC"],
)


# 9. Orchestration Template (project scaffold files)
ORCHESTRATION_TEMPLATE = OrbitTemplate(
    name="Orbit Full Orchestration",
    description="Full Orbit chain deployment project scaffold",
    template_type="orchestration",
    features=[
        "Complete project scaffold",
        "Package.json with all dependencies",
        "TypeScript configuration",
        "Environment template",
        "Setup and deploy scripts",
    ],
    code="",  # No single code file — uses files dict
    dependencies=ORBIT_DEPENDENCIES,
    env_vars=[
        "DEPLOYER_PRIVATE_KEY",
        "PARENT_CHAIN_RPC",
        "ORBIT_CHAIN_RPC",
    ],
    files={
        "package.json": '''{
  "name": "{project_name}",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "setup": "bash setup.sh",
    "deploy:rollup": "npx tsx scripts/deploy-rollup.ts",
    "deploy:token-bridge": "npx tsx scripts/deploy-token-bridge.ts",
    "config:chain": "npx tsx scripts/prepare-chain-config.ts",
    "config:node": "npx tsx scripts/prepare-node-config.ts",
    "manage:validators": "npx tsx scripts/manage-validators.ts",
    "deploy": "bash deploy.sh"
  },
  "dependencies": {
    "@arbitrum/orbit-sdk": "^0.25.0",
    "viem": "^1.20.0",
    "dotenv": "^16.4.0"
  },
  "devDependencies": {
    "tsx": "^4.7.0",
    "typescript": "^5.3.0",
    "@types/node": "^20.0.0"
  }
}
''',
        "tsconfig.json": '''{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "strict": true,
    "outDir": "dist",
    "rootDir": "scripts",
    "resolveJsonModule": true,
    "declaration": true,
    "skipLibCheck": true
  },
  "include": ["scripts/**/*.ts"],
  "exclude": ["node_modules", "dist"]
}
''',
        ".env.example": '''# Deployer private key (with 0x prefix)
DEPLOYER_PRIVATE_KEY=0x...

# Parent chain RPC URL
# Ethereum Sepolia: https://rpc.sepolia.org
# Arbitrum Sepolia: https://sepolia-rollup.arbitrum.io/rpc
# Ethereum Mainnet: https://eth.llamarpc.com
# Arbitrum One: https://arb1.arbitrum.io/rpc
PARENT_CHAIN_RPC={parent_chain_rpc}

# Orbit chain RPC (after deployment)
ORBIT_CHAIN_RPC=http://localhost:8449

# Chain configuration
CHAIN_ID={chain_id}
CHAIN_NAME={chain_name}
''',
        "setup.sh": '''#!/usr/bin/env bash
set -euo pipefail

echo "=== Orbit Chain Setup ==="

# Install dependencies
echo "Installing dependencies..."
npm install

# Copy env template if .env doesn't exist
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from template - edit it with your keys before deploying."
fi

echo ""
echo "Setup complete!"
echo "Next steps:"
echo "  1. Edit .env with your DEPLOYER_PRIVATE_KEY and PARENT_CHAIN_RPC"
echo "  2. Run: npm run config:chain   (prepare chain config)"
echo "  3. Run: npm run deploy:rollup  (deploy rollup contracts)"
echo "  4. Run: npm run deploy:token-bridge (deploy token bridge)"
echo "  5. Run: npm run config:node    (generate node config)"
''',
        "deploy.sh": '''#!/usr/bin/env bash
set -euo pipefail

# Load environment variables
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

echo "=== Orbit Chain Full Deployment ==="

echo ""
echo "Step 1: Prepare chain config..."
npx tsx scripts/prepare-chain-config.ts

echo ""
echo "Step 2: Deploy rollup contracts..."
npx tsx scripts/deploy-rollup.ts

if [ ! -f deployment.json ]; then
  echo "ERROR: deployment.json not created. Rollup deployment may have failed."
  exit 1
fi

echo ""
echo "Step 3: Generate node config..."
npx tsx scripts/prepare-node-config.ts

echo ""
echo "Step 4: Start node (manual step)..."
echo "  Run: docker-compose up -d"
echo "  Wait for the node to sync, then continue with token bridge deployment."
echo "  Press ENTER to continue when the node is ready, or Ctrl+C to stop."
read -r

echo ""
echo "Step 5: Deploy token bridge..."
npx tsx scripts/deploy-token-bridge.ts

echo ""
echo "=== Deployment complete! ==="
echo "Deployment output saved to deployment.json"
echo "Node config saved to nodeConfig.json"
''',
    },
)


# All templates indexed by type
ORBIT_TEMPLATES: Dict[str, OrbitTemplate] = {
    "chain_config": CHAIN_CONFIG_TEMPLATE,
    "deploy_rollup": DEPLOY_ROLLUP_TEMPLATE,
    "deploy_token_bridge": DEPLOY_TOKEN_BRIDGE_TEMPLATE,
    "custom_gas_token": CUSTOM_GAS_TOKEN_TEMPLATE,
    "validator_management": VALIDATOR_MANAGEMENT_TEMPLATE,
    "governance": GOVERNANCE_TEMPLATE,
    "node_config": NODE_CONFIG_TEMPLATE,
    "anytrust_config": ANYTRUST_CONFIG_TEMPLATE,
    "orchestration": ORCHESTRATION_TEMPLATE,
}


def select_orbit_template(prompt: str) -> OrbitTemplate:
    """Select the best Orbit template based on prompt keywords."""
    lower_prompt = prompt.lower()

    if any(kw in lower_prompt for kw in [
        "deploy rollup", "create rollup", "launch chain", "deploy chain",
        "deploy a new", "deploy orbit", "createrollup",
    ]):
        return DEPLOY_ROLLUP_TEMPLATE

    if any(kw in lower_prompt for kw in ["token bridge", "bridge deploy", "create bridge"]):
        return DEPLOY_TOKEN_BRIDGE_TEMPLATE

    if any(kw in lower_prompt for kw in ["custom gas", "native token", "gas token", "erc20 gas"]):
        return CUSTOM_GAS_TOKEN_TEMPLATE

    if any(kw in lower_prompt for kw in ["validator", "batch poster", "sequencer"]):
        return VALIDATOR_MANAGEMENT_TEMPLATE

    if any(kw in lower_prompt for kw in ["governance", "upgrade", "executor", "admin"]):
        return GOVERNANCE_TEMPLATE

    if any(kw in lower_prompt for kw in ["node config", "nitro", "node setup"]):
        return NODE_CONFIG_TEMPLATE

    if any(kw in lower_prompt for kw in ["anytrust", "dac", "keyset", "data availability"]):
        return ANYTRUST_CONFIG_TEMPLATE

    if any(kw in lower_prompt for kw in ["full", "scaffold", "orchestrate", "complete"]):
        return ORCHESTRATION_TEMPLATE

    if any(kw in lower_prompt for kw in ["chain config", "prepare config", "configure chain"]):
        return CHAIN_CONFIG_TEMPLATE

    # Default to chain config as starting point
    return CHAIN_CONFIG_TEMPLATE


def get_orbit_template(name: str) -> Optional[OrbitTemplate]:
    """Get a specific Orbit template by name."""
    return ORBIT_TEMPLATES.get(name)


def list_orbit_templates() -> List[OrbitTemplate]:
    """List all available Orbit templates."""
    return list(ORBIT_TEMPLATES.values())

/**
 * Generate Orbit chain deployment code (M4 tool)
 *
 * Supports:
 * - Rollup deployment (createRollup)
 * - Token bridge deployment (createTokenBridge)
 * - Full deployment (rollup + token bridge)
 */

import {
  ORBIT_DEPENDENCIES,
  PARENT_CHAIN_RPCS,
  PARENT_CHAIN_IDS,
  TEMPLATE_DISCLAIMER,
} from "./generateOrbitConfig";

// Types
type ParentChain =
  | "arbitrum-one"
  | "arbitrum-sepolia"
  | "ethereum-mainnet"
  | "ethereum-sepolia";

type DeploymentType = "rollup" | "token_bridge" | "full";

interface GenerateOrbitDeploymentInput {
  prompt: string;
  deploymentType?: DeploymentType;
  validators?: string[];
  batchPosters?: string[];
  nativeToken?: string;
  parentChain?: ParentChain;
  rollupVersion?: "v2.1" | "v3.1";
  chainId?: number;
  isAnyTrust?: boolean;
  rollupAddress?: string;
}

interface GenerateOrbitDeploymentOutput {
  templateUsed: string;
  deploymentType: DeploymentType;
  rollupVersion: string;
  files: Record<string, string>;
  dependencies: Record<string, string>;
  parentChain: {
    name: string;
    chainId: number;
    rpc: string;
  };
  chainConfig: {
    chainId: number;
    isAnyTrust: boolean;
    nativeToken: string | undefined;
    validators: string[];
    batchPosters: string[];
  };
  setupInstructions: string[];
  notes: string[];
  disclaimer: string;
}

// --- Templates ---

// Known RollupCreator contract addresses from @arbitrum/chain-sdk
const ROLLUP_CREATOR_ADDRESSES = {
  'v2.1': {
    1: '0x8c88430658a03497D13cDff7684D37b15aA2F3e1',       // Ethereum Mainnet
    42161: '0x79607f00e61E6d7C0E6330bd7E9c4AC320D50FC9',   // Arbitrum One
    421614: '0xd2Ec8376B1dF436fAb18120E416d3F2BeC61275b',  // Arbitrum Sepolia
    11155111: '0xfb774eA8A92ae528A596c8D90CBCF1bdBC4Cee79', // Ethereum Sepolia
  },
  'v3.1': {
    1: '0x43698080f40dB54DEE6871540037b8AB8fD0AB44',       // Ethereum Mainnet
    42161: '0xB90e53fd945Cd28Ec4728cBfB566981dD571eB8b',   // Arbitrum One
    421614: '0x5F45675AC8DDF7d45713b2c7D191B287475C16cF',  // Arbitrum Sepolia
    11155111: '0x687Bc1D23390875a868Db158DA1cDC8998E31640', // Ethereum Sepolia
  },
} as const;

const DEPLOY_ROLLUP_V3_TEMPLATE = `import 'dotenv/config';
import * as fs from 'fs';
import {
  createPublicClient,
  createWalletClient,
  http,
  maxUint256,
  Chain,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import {
  prepareChainConfig,
  createRollup,
  createRollupPrepareDeploymentParamsConfig,
} from '@arbitrum/chain-sdk';
{tokenApprovalConstants}
/**
 * v3.1 Orbit Rollup Deployment — BoLD Challenge Protocol
 *
 * Uses the v3.1 RollupCreator at {rollupCreatorAddress}
 * BoLD (Bounded Liquidity Delay) features:
 *   - Assertion staking with configurable buffer
 *   - Multi-level challenge resolution
 *   - Permissionless validation support
 */
const parentChain: Chain = {
  id: {parentChainId},
  name: '{parentChainName}',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: {
    default: { http: [process.env.PARENT_CHAIN_RPC!] },
  },
};

async function main() {
  const account = privateKeyToAccount(
    process.env.DEPLOYER_PRIVATE_KEY! as \`0x\${string}\`
  );

  const parentChainPublicClient = createPublicClient({
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  });
{tokenApprovalBlock}
  const chainConfig = prepareChainConfig({
    chainId: {chainId},
    arbitrum: {
      InitialChainOwner: account.address,
      DataAvailabilityCommittee: {isAnyTrust},
    },
  });

  console.log('Deploying Orbit chain...');
  console.log('  Version: v3.1 (BoLD challenge protocol)');
  console.log('  RollupCreator: {rollupCreatorAddress}');
  console.log('  Chain ID:', {chainId});
  console.log('  AnyTrust:', {isAnyTrust});

  const deployResult = await createRollup({
    params: {
      config: createRollupPrepareDeploymentParamsConfig(parentChainPublicClient, {
        chainId: BigInt({chainId}),
        owner: account.address,
        chainConfig,
      }),
      validators: {validatorsArray},
      batchPosters: {batchPostersArray},
      batchPosterManager: account.address,
      deployFactoriesToL2: true,{nativeTokenLine}
    },
    account,
    parentChainPublicClient,
    rollupCreatorVersion: 'v3.1',
  });

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

  // Get deployment block number (needed for node config deployed-at)
  const receipt = await parentChainPublicClient.getTransactionReceipt({
    hash: deployResult.transactionHash,
  });

  // Save deployment output for downstream scripts
  const deployment = {
    chainId: {chainId},
    parentChainId: {parentChainId},
    rollupVersion: 'v3.1',
    transactionHash: deployResult.transactionHash,
    deployedAtBlock: Number(receipt.blockNumber),
    chainConfig,
    coreContracts: deployResult.coreContracts,
    deployer: account.address,
    timestamp: new Date().toISOString(),
  };
  fs.writeFileSync('deployment.json', JSON.stringify(deployment, null, 2));
  console.log('\\nDeployment saved to deployment.json');
  console.log('  Deployed at block:', deployment.deployedAtBlock);
}

main().catch(console.error);
`;

const DEPLOY_ROLLUP_V2_TEMPLATE = `import 'dotenv/config';
import * as fs from 'fs';
import {
  createPublicClient,
  createWalletClient,
  http,
  maxUint256,
  Chain,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import {
  prepareChainConfig,
  createRollup,
  createRollupPrepareDeploymentParamsConfig,
} from '@arbitrum/chain-sdk';
{tokenApprovalConstants}
/**
 * v2.1 Orbit Rollup Deployment — Classic Challenge Protocol
 *
 * Uses the v2.1 RollupCreator at {rollupCreatorAddress}
 * Classic challenge features:
 *   - Fixed base stake: 0.1 ETH (validators must lock on parent chain)
 *   - Stake token: ETH (zeroAddress)
 *   - Single-round interactive challenge
 *   - extraChallengeTimeBlocks: 0
 */
const parentChain: Chain = {
  id: {parentChainId},
  name: '{parentChainName}',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: {
    default: { http: [process.env.PARENT_CHAIN_RPC!] },
  },
};

async function main() {
  const account = privateKeyToAccount(
    process.env.DEPLOYER_PRIVATE_KEY! as \`0x\${string}\`
  );

  const parentChainPublicClient = createPublicClient({
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  });
{tokenApprovalBlock}
  const chainConfig = prepareChainConfig({
    chainId: {chainId},
    arbitrum: {
      InitialChainOwner: account.address,
      DataAvailabilityCommittee: {isAnyTrust},
    },
  });

  console.log('Deploying Orbit chain...');
  console.log('  Version: v2.1 (classic challenge protocol)');
  console.log('  RollupCreator: {rollupCreatorAddress}');
  console.log('  Chain ID:', {chainId});
  console.log('  AnyTrust:', {isAnyTrust});
  console.log('  Validator base stake: 0.1 ETH');

  const deployResult = await createRollup({
    params: {
      config: createRollupPrepareDeploymentParamsConfig(parentChainPublicClient, {
        chainId: BigInt({chainId}),
        owner: account.address,
        chainConfig,
      }),
      validators: {validatorsArray},
      batchPosters: {batchPostersArray},
      batchPosterManager: account.address,
      deployFactoriesToL2: true,{nativeTokenLine}
    },
    account,
    parentChainPublicClient,
    rollupCreatorVersion: 'v2.1',
  });

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
  console.log('\\nv2.1 staking config:');
  console.log('  Base stake: 0.1 ETH');
  console.log('  Stake token: ETH (zeroAddress)');
  console.log('  Extra challenge time blocks: 0');

  // Get deployment block number (needed for node config deployed-at)
  const receipt = await parentChainPublicClient.getTransactionReceipt({
    hash: deployResult.transactionHash,
  });

  // Save deployment output for downstream scripts
  const deployment = {
    chainId: {chainId},
    parentChainId: {parentChainId},
    rollupVersion: 'v2.1',
    transactionHash: deployResult.transactionHash,
    deployedAtBlock: Number(receipt.blockNumber),
    chainConfig,
    coreContracts: deployResult.coreContracts,
    deployer: account.address,
    timestamp: new Date().toISOString(),
  };
  fs.writeFileSync('deployment.json', JSON.stringify(deployment, null, 2));
  console.log('\\nDeployment saved to deployment.json');
  console.log('  Deployed at block:', deployment.deployedAtBlock);
}

main().catch(console.error);
`;

const DEPLOY_TOKEN_BRIDGE_TEMPLATE = `import 'dotenv/config';
import * as fs from 'fs';
import {
  createPublicClient,
  createWalletClient,
  http,
  Chain,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { createTokenBridge } from '@arbitrum/chain-sdk';

// Parent chain configuration
const parentChain: Chain = {
  id: {parentChainId},
  name: '{parentChainName}',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: {
    default: { http: [process.env.PARENT_CHAIN_RPC!] },
  },
};

async function main() {
  // Read rollup address from deployment.json (output of deploy-rollup.ts)
  let rollupAddress: \`0x\${string}\` = '{rollupAddress}' as \`0x\${string}\`;
  let orbitChainId = {chainId};

  if (fs.existsSync('deployment.json')) {
    const deployment = JSON.parse(fs.readFileSync('deployment.json', 'utf-8'));
    rollupAddress = deployment.coreContracts.rollup as \`0x\${string}\`;
    orbitChainId = deployment.chainId ?? orbitChainId;
    console.log('Loaded deployment.json — rollup:', rollupAddress);
  } else {
    console.log('Warning: deployment.json not found, using placeholder rollup address.');
    console.log('Run deploy-rollup.ts first, or set rollupAddress manually.');
  }

  // Orbit chain configuration
  const orbitChain: Chain = {
    id: orbitChainId,
    name: '{chainName}',
    nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
    rpcUrls: {
      default: { http: [process.env.ORBIT_CHAIN_RPC!] },
    },
  };

  const account = privateKeyToAccount(
    process.env.DEPLOYER_PRIVATE_KEY! as \`0x\${string}\`
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
`;

// Token approval script — generated when nativeToken is set
const APPROVE_TOKEN_TEMPLATE = `import 'dotenv/config';
import {
  createPublicClient,
  createWalletClient,
  http,
  Chain,
  maxUint256,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';

// Known RollupCreator addresses (v3.1)
// See: https://docs.arbitrum.io/launch-orbit-chain/orbit-sdk-introduction
const ROLLUP_CREATOR: Record<number, \`0x\${string}\`> = {
  1: '0x43698080f40dB54DEE6871540037b8AB8fD0AB44',       // Ethereum Mainnet
  42161: '0xB90e53fd945Cd28Ec4728cBfB566981dD571eB8b',   // Arbitrum One
  421614: '0x5F45675AC8DDF7d45713b2c7D191B287475C16cF',  // Arbitrum Sepolia
  11155111: '0x687Bc1D23390875a868Db158DA1cDC8998E31640', // Ethereum Sepolia
};

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
  {
    name: 'symbol',
    type: 'function',
    stateMutability: 'view',
    inputs: [],
    outputs: [{ name: '', type: 'string' }],
  },
  {
    name: 'decimals',
    type: 'function',
    stateMutability: 'view',
    inputs: [],
    outputs: [{ name: '', type: 'uint8' }],
  },
] as const;

const parentChain: Chain = {
  id: {parentChainId},
  name: '{parentChainName}',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: {
    default: { http: [process.env.PARENT_CHAIN_RPC!] },
  },
};

/**
 * Approve the custom gas token for the RollupCreator.
 *
 * This MUST be run before deploy-rollup.ts when using a custom gas token.
 * The RollupCreator needs allowance to transfer the token during deployment.
 *
 * If you don't have a token yet, deploy an ERC-20 on the parent chain first:
 *   - Foundry: forge create src/MyToken.sol:MyToken --rpc-url $PARENT_CHAIN_RPC --private-key $DEPLOYER_PRIVATE_KEY
 *   - Hardhat: npx hardhat run scripts/deploy-token.ts --network <parent-chain>
 *   - Or use any existing ERC-20 on the parent chain
 */
async function main() {
  const account = privateKeyToAccount(
    process.env.DEPLOYER_PRIVATE_KEY! as \`0x\${string}\`
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

  const nativeToken = '{nativeToken}' as \`0x\${string}\`;
  const rollupCreator = ROLLUP_CREATOR[{parentChainId}];

  if (!rollupCreator) {
    console.error('No known RollupCreator for chain ID {parentChainId}.');
    console.error('Set the correct RollupCreator address manually.');
    process.exit(1);
  }

  // Check token info
  const [symbol, decimals] = await Promise.all([
    publicClient.readContract({ address: nativeToken, abi: erc20Abi, functionName: 'symbol' }),
    publicClient.readContract({ address: nativeToken, abi: erc20Abi, functionName: 'decimals' }),
  ]);

  console.log('=== Token Approval for Custom Gas Token ===');
  console.log('  Token:', nativeToken);
  console.log('  Symbol:', symbol);
  console.log('  Decimals:', decimals);
  console.log('  RollupCreator:', rollupCreator);

  // Check current allowance
  const currentAllowance = await publicClient.readContract({
    address: nativeToken,
    abi: erc20Abi,
    functionName: 'allowance',
    args: [account.address, rollupCreator],
  });

  console.log('  Current allowance:', currentAllowance.toString());

  if (currentAllowance > 0n) {
    console.log('\\nToken already approved. You can proceed with deployment.');
    console.log('  Run: npx tsx scripts/deploy-rollup.ts');
    return;
  }

  // Approve max amount
  console.log('\\nApproving token for RollupCreator...');
  const txHash = await walletClient.writeContract({
    address: nativeToken,
    abi: erc20Abi,
    functionName: 'approve',
    args: [rollupCreator, maxUint256],
  });

  const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
  console.log('\\nToken approved!');
  console.log('  Transaction:', receipt.transactionHash);
  console.log('  Status:', receipt.status);
  console.log('\\nNext: Run npx tsx scripts/deploy-rollup.ts');
}

main().catch(console.error);
`;

// --- Helpers ---

function formatAddressArray(addresses: string[]): string {
  if (!addresses || addresses.length === 0) {
    return "[account.address] as `0x${string}`[]";
  }
  const formatted = addresses
    .map((addr) => `'${addr}' as \`0x\${string}\``)
    .join(", ");
  return `[${formatted}]`;
}

function getSetupInstructions(deploymentType: DeploymentType, nativeToken?: string): string[] {
  const instructions = [
    "1. Install dependencies: npm install",
    "2. Copy .env.example to .env and configure",
    "3. Ensure deployer account has sufficient funds on parent chain",
  ];

  if (deploymentType === "rollup") {
    if (nativeToken) {
      instructions.push("4. Deploy or obtain your ERC-20 gas token on the parent chain");
      instructions.push("5. Run: npx tsx scripts/approve-token.ts (approve token for RollupCreator)");
      instructions.push("6. Run: npx tsx scripts/deploy-rollup.ts");
      instructions.push("7. Save the output contract addresses for next steps");
    } else {
      instructions.push("4. Run: npx tsx scripts/deploy-rollup.ts");
      instructions.push("5. Save the output contract addresses for next steps");
    }
  } else if (deploymentType === "token_bridge") {
    instructions.push("4. Update ORBIT_CHAIN_RPC and rollup address in the script");
    instructions.push("5. Run: npx tsx scripts/deploy-token-bridge.ts");
  } else if (deploymentType === "full") {
    if (nativeToken) {
      instructions.push("4. Deploy or obtain your ERC-20 gas token on the parent chain");
      instructions.push("5. Run: npx tsx scripts/approve-token.ts (approve token for RollupCreator)");
      instructions.push("6. Run: npx tsx scripts/deploy-rollup.ts");
    } else {
      instructions.push("4. Run: npx tsx scripts/deploy-rollup.ts");
    }
    const nextStep = nativeToken ? 7 : 5;
    instructions.push(`${nextStep}. Start the Orbit chain node with the rollup contracts`);
    instructions.push(`${nextStep + 1}. Update ORBIT_CHAIN_RPC and rollup address`);
    instructions.push(`${nextStep + 2}. Run: npx tsx scripts/deploy-token-bridge.ts`);
  }

  return instructions;
}

function getDeploymentNotes(
  deploymentType: DeploymentType,
  nativeToken: string | undefined,
  isAnyTrust: boolean,
  rollupVersion: string = "v3.1"
): string[] {
  const notes = [
    "Deployment requires significant gas - ensure sufficient funds",
    "Save all contract addresses from deployment output",
  ];

  if (rollupVersion === "v2.1") {
    notes.push("v2.1 (classic): baseStake = 0.1 ETH, classic challenge protocol");
    notes.push("v2.1 uses the classic RollupCreator via rollupCreatorVersion: 'v2.1'");
  } else {
    notes.push("v3.1 (BoLD): uses assertion staking with bounded liquidity delay challenge protocol");
  }

  if (nativeToken) {
    notes.push("Custom gas token requires ERC20 approval before deployment");
    notes.push("The native token must be deployed on the parent chain");
  }

  if (isAnyTrust) {
    notes.push("AnyTrust chains require DAC keyset configuration after deployment");
  }

  if (deploymentType === "full") {
    notes.push("Token bridge deployment requires the Orbit chain to be running");
  }

  return notes;
}

/**
 * Generate Orbit chain deployment code.
 *
 * Produces TypeScript scripts for deploying rollup contracts and/or
 * token bridge using the @arbitrum/chain-sdk.
 */
export function generateOrbitDeployment(
  input: GenerateOrbitDeploymentInput
): GenerateOrbitDeploymentOutput {
  const {
    prompt,
    deploymentType = "rollup",
    validators = [],
    batchPosters = [],
    nativeToken,
    parentChain = "arbitrum-sepolia",
    rollupVersion = "v3.1",
    chainId = 412346,
    isAnyTrust = false,
    rollupAddress = "0x0000000000000000000000000000000000000000",
  } = input;

  // Get parent chain info
  const parentRpc = PARENT_CHAIN_RPCS[parentChain] ?? PARENT_CHAIN_RPCS["arbitrum-sepolia"];
  const parentChainId = PARENT_CHAIN_IDS[parentChain] ?? 421614;
  const parentChainName = parentChain.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  const validatorsStr = formatAddressArray(validators);
  const batchPostersStr = formatAddressArray(batchPosters);

  const files: Record<string, string> = {};

  // Generate rollup deployment
  if (deploymentType === "rollup" || deploymentType === "full") {
    let code = rollupVersion === "v2.1" ? DEPLOY_ROLLUP_V2_TEMPLATE : DEPLOY_ROLLUP_V3_TEMPLATE;
    code = code.replace(/\{chainId\}/g, String(chainId));
    code = code.replace(/\{parentChainId\}/g, String(parentChainId));
    code = code.replace(/\{parentChainName\}/g, parentChainName);
    code = code.replace(/\{isAnyTrust\}/g, isAnyTrust ? "true" : "false");
    code = code.replace(/\{validatorsArray\}/g, validatorsStr);
    code = code.replace(/\{batchPostersArray\}/g, batchPostersStr);

    // Look up the known RollupCreator address for this version + parent chain
    const versionAddresses = ROLLUP_CREATOR_ADDRESSES[rollupVersion === "v2.1" ? "v2.1" : "v3.1"];
    const rollupCreatorAddress = versionAddresses[parentChainId as keyof typeof versionAddresses]
      ?? "0x0000000000000000000000000000000000000000";
    code = code.replace(/\{rollupCreatorAddress\}/g, rollupCreatorAddress);

    if (nativeToken) {
      code = code.replace(
        /\{nativeTokenLine\}/g,
        `\n      nativeToken: '${nativeToken}' as \`0x\${string}\`,`
      );
      // Inline token approval: ABI constant + walletClient + approve() before createRollup
      code = code.replace(/\{tokenApprovalConstants\}/g, `
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
`);
      code = code.replace(/\{tokenApprovalBlock\}/g, `
  // --- Token approval for custom gas token ---
  const nativeToken = '${nativeToken}' as \\\`0x\\\${string}\\\`;
  const rollupCreator = '${rollupCreatorAddress}' as \\\`0x\\\${string}\\\`;

  const walletClient = createWalletClient({
    account,
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  });

  const currentAllowance = await parentChainPublicClient.readContract({
    address: nativeToken,
    abi: erc20Abi,
    functionName: 'allowance',
    args: [account.address, rollupCreator],
  });

  if (currentAllowance === 0n) {
    console.log('Approving native token for RollupCreator...');
    const approveTx = await walletClient.writeContract({
      address: nativeToken,
      abi: erc20Abi,
      functionName: 'approve',
      args: [rollupCreator, maxUint256],
    });
    await parentChainPublicClient.waitForTransactionReceipt({ hash: approveTx });
    console.log('  Token approved');
  } else {
    console.log('Native token already approved for RollupCreator');
  }
`);
    } else {
      code = code.replace(/\{nativeTokenLine\}/g, "");
      code = code.replace(/\{tokenApprovalConstants\}/g, "");
      code = code.replace(/\{tokenApprovalBlock\}/g, "");
    }

    files["scripts/deploy-rollup.ts"] = code;

    // Generate token approval script when using custom gas token
    if (nativeToken) {
      let approveCode = APPROVE_TOKEN_TEMPLATE;
      approveCode = approveCode.replace(/\{parentChainId\}/g, String(parentChainId));
      approveCode = approveCode.replace(/\{parentChainName\}/g, parentChainName);
      approveCode = approveCode.replace(/\{nativeToken\}/g, nativeToken);
      files["scripts/approve-token.ts"] = approveCode;
    }
  }

  // Generate token bridge deployment
  if (deploymentType === "token_bridge" || deploymentType === "full") {
    let code = DEPLOY_TOKEN_BRIDGE_TEMPLATE;
    code = code.replace(/\{chainId\}/g, String(chainId));
    code = code.replace(/\{chainName\}/g, `orbit-chain-${chainId}`);
    code = code.replace(/\{parentChainId\}/g, String(parentChainId));
    code = code.replace(/\{parentChainName\}/g, parentChainName);
    code = code.replace(/\{rollupAddress\}/g, rollupAddress);
    files["scripts/deploy-token-bridge.ts"] = code;
  }

  // Add .env.example
  const envVars = [`DEPLOYER_PRIVATE_KEY=0x...`, `PARENT_CHAIN_RPC=${parentRpc}`];
  if (rollupVersion === "v2.1") {
    envVars.push("# Using v2.1 RollupCreator (classic challenge protocol)");
  }
  if (deploymentType === "token_bridge" || deploymentType === "full") {
    envVars.push("ORBIT_CHAIN_RPC=http://localhost:8449");
  }
  files[".env.example"] = envVars.join("\n") + "\n";

  return {
    templateUsed: `deploy_${deploymentType}`,
    deploymentType,
    rollupVersion,
    files,
    dependencies: ORBIT_DEPENDENCIES,
    parentChain: {
      name: parentChain,
      chainId: parentChainId,
      rpc: parentRpc,
    },
    chainConfig: {
      chainId,
      isAnyTrust,
      nativeToken,
      validators,
      batchPosters,
    },
    setupInstructions: getSetupInstructions(deploymentType, nativeToken),
    notes: getDeploymentNotes(deploymentType, nativeToken, isAnyTrust, rollupVersion),
    disclaimer: TEMPLATE_DISCLAIMER,
  };
}

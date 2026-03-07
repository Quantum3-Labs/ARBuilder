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

const DEPLOY_ROLLUP_V3_TEMPLATE = `import 'dotenv/config';
import {
  createPublicClient,
  createWalletClient,
  http,
  parseEther,
  Chain,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import {
  prepareChainConfig,
  createRollup,
  createRollupPrepareDeploymentParamsConfig,
} from '@arbitrum/orbit-sdk';

// v3.1 RollupCreator (BoLD challenge protocol)
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

  // Prepare chain config
  const chainConfig = prepareChainConfig({
    chainId: {chainId},
    arbitrum: {
      InitialChainOwner: account.address,
      DataAvailabilityCommittee: {isAnyTrust},
    },
  });

  console.log('Deploying Orbit chain (v3.1 / BoLD)...');
  console.log('  Chain ID:', {chainId});
  console.log('  Owner:', account.address);
  console.log('  AnyTrust:', {isAnyTrust});

  // Deploy rollup using v3.1 RollupCreator (BoLD)
  const deployResult = await createRollup({
    params: {
      config: createRollupPrepareDeploymentParamsConfig(publicClient, {
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
    publicClient,
    walletClient,
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
}

main().catch(console.error);
`;

const DEPLOY_ROLLUP_V2_TEMPLATE = `import 'dotenv/config';
import {
  createPublicClient,
  createWalletClient,
  http,
  parseEther,
  Chain,
  zeroAddress,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import {
  prepareChainConfig,
  createRollup,
  createRollupPrepareDeploymentParamsConfig,
} from '@arbitrum/orbit-sdk';

// v2.1 RollupCreator (classic challenge protocol)
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

  // Prepare chain config (v2.1 classic)
  const chainConfig = prepareChainConfig({
    chainId: {chainId},
    arbitrum: {
      InitialChainOwner: account.address,
      DataAvailabilityCommittee: {isAnyTrust},
    },
  });

  console.log('Deploying Orbit chain (v2.1 / classic)...');
  console.log('  Chain ID:', {chainId});
  console.log('  Owner:', account.address);
  console.log('  AnyTrust:', {isAnyTrust});

  // Deploy rollup using v2.1 RollupCreator (classic challenge protocol)
  // v2.1 defaults: baseStake = 0.1 ETH, stakeToken = zeroAddress (ETH)
  const deployResult = await createRollup({
    params: {
      config: createRollupPrepareDeploymentParamsConfig(publicClient, {
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
    publicClient,
    walletClient,
    // Use v2.1 RollupCreator (classic challenge, not BoLD)
    rollupCreatorAddressOverride: process.env.ROLLUP_CREATOR_V2_ADDRESS as \`0x\${string}\` | undefined,
  });

  console.log('\\nRollup deployed successfully! (v2.1 classic)');
  console.log('Transaction hash:', deployResult.transactionHash);
  console.log('\\nCore contracts:');
  console.log('  Rollup:', deployResult.coreContracts.rollup);
  console.log('  Inbox:', deployResult.coreContracts.inbox);
  console.log('  Outbox:', deployResult.coreContracts.outbox);
  console.log('  Bridge:', deployResult.coreContracts.bridge);
  console.log('  SequencerInbox:', deployResult.coreContracts.sequencerInbox);
  console.log('  RollupEventInbox:', deployResult.coreContracts.rollupEventInbox);
  console.log('  UpgradeExecutor:', deployResult.coreContracts.upgradeExecutor);

  // v2.1 note: baseStake is 0.1 ETH by default
  // Validators must stake this amount on the parent chain
  console.log('\\nv2.1 validator config:');
  console.log('  Base stake: 0.1 ETH (default)');
  console.log('  Stake token: ETH (zeroAddress)');
}

main().catch(console.error);
`;

const DEPLOY_TOKEN_BRIDGE_TEMPLATE = `import 'dotenv/config';
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
  id: {parentChainId},
  name: '{parentChainName}',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: {
    default: { http: [process.env.PARENT_CHAIN_RPC!] },
  },
};

// Orbit chain configuration
const orbitChain: Chain = {
  id: {chainId},
  name: '{chainName}',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: {
    default: { http: [process.env.ORBIT_CHAIN_RPC!] },
  },
};

async function main() {
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
  console.log('  Rollup address:', '{rollupAddress}');

  const tokenBridgeResult = await createTokenBridge({
    rollupAddress: '{rollupAddress}' as \`0x\${string}\`,
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

function getSetupInstructions(deploymentType: DeploymentType): string[] {
  const instructions = [
    "1. Install dependencies: npm install @arbitrum/orbit-sdk viem dotenv",
    "2. Copy .env.example to .env and configure",
    "3. Ensure deployer account has sufficient funds on parent chain",
  ];

  if (deploymentType === "rollup") {
    instructions.push("4. Run: npx tsx scripts/deploy-rollup.ts");
    instructions.push("5. Save the output contract addresses for next steps");
  } else if (deploymentType === "token_bridge") {
    instructions.push("4. Update ORBIT_CHAIN_RPC and rollup address in the script");
    instructions.push("5. Run: npx tsx scripts/deploy-token-bridge.ts");
  } else if (deploymentType === "full") {
    instructions.push("4. Run: npx tsx scripts/deploy-rollup.ts");
    instructions.push("5. Start the Orbit chain node with the rollup contracts");
    instructions.push("6. Update ORBIT_CHAIN_RPC and rollup address");
    instructions.push("7. Run: npx tsx scripts/deploy-token-bridge.ts");
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
    notes.push("v2.1 uses the legacy RollupCreator — set ROLLUP_CREATOR_V2_ADDRESS if needed");
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
 * token bridge using the @arbitrum/orbit-sdk.
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

    if (nativeToken) {
      code = code.replace(
        /\{nativeTokenLine\}/g,
        `\n      nativeToken: '${nativeToken}' as \`0x\${string}\`,`
      );
    } else {
      code = code.replace(/\{nativeTokenLine\}/g, "");
    }

    files["scripts/deploy-rollup.ts"] = code;
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
    envVars.push("# Optional: override v2.1 RollupCreator address (defaults to SDK builtin)");
    envVars.push("# ROLLUP_CREATOR_V2_ADDRESS=0x...");
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
    setupInstructions: getSetupInstructions(deploymentType),
    notes: getDeploymentNotes(deploymentType, nativeToken, isAnyTrust, rollupVersion),
    disclaimer: TEMPLATE_DISCLAIMER,
  };
}

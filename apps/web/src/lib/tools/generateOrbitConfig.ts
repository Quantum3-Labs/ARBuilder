/**
 * Generate Orbit chain configuration code (M4 tool)
 *
 * Supports:
 * - Chain configuration (prepareChainConfig)
 * - AnyTrust DAC keyset setup
 * - Custom gas token configuration
 */

// Template disclaimer
export const TEMPLATE_DISCLAIMER =
  "This code is generated from curated templates. Review and test thoroughly before deploying to production.";

// Types
type ParentChain =
  | "arbitrum-one"
  | "arbitrum-sepolia"
  | "ethereum-mainnet"
  | "ethereum-sepolia";

interface GenerateOrbitConfigInput {
  prompt: string;
  chainId?: number;
  owner?: string;
  isAnyTrust?: boolean;
  nativeToken?: string;
  parentChain?: ParentChain;
}

interface GenerateOrbitConfigOutput {
  templateUsed: string;
  files: Record<string, string>;
  dependencies: Record<string, string>;
  envVars: string[];
  parentChain: {
    name: string;
    chainId: number;
    rpc: string;
  };
  chainConfig: {
    chainId: number;
    owner: string;
    isAnyTrust: boolean;
    nativeToken: string | undefined;
  };
  setupInstructions: string[];
  disclaimer: string;
}

// Dependencies shared by all Orbit tools
export const ORBIT_DEPENDENCIES: Record<string, string> = {
  "@arbitrum/orbit-sdk": "^0.27.0",
  viem: "^2.23.0",
  dotenv: "^16.4.0",
};

// Parent chain RPC URLs
export const PARENT_CHAIN_RPCS: Record<ParentChain, string> = {
  "arbitrum-one": "https://arb1.arbitrum.io/rpc",
  "arbitrum-sepolia": "https://sepolia-rollup.arbitrum.io/rpc",
  "ethereum-mainnet": "https://eth.llamarpc.com",
  "ethereum-sepolia": "https://rpc.sepolia.org",
};

// Chain IDs by parent chain
export const PARENT_CHAIN_IDS: Record<ParentChain, number> = {
  "ethereum-mainnet": 1,
  "ethereum-sepolia": 11155111,
  "arbitrum-one": 42161,
  "arbitrum-sepolia": 421614,
};

// --- Templates ---

const CHAIN_CONFIG_TEMPLATE = `import 'dotenv/config';
import { prepareChainConfig } from '@arbitrum/orbit-sdk';

/**
 * Prepare the chain configuration for a new Orbit chain.
 *
 * This generates the chainConfig JSON that will be passed to createRollup().
 * It defines the core parameters of your Orbit chain.
 */
async function main() {
  const chainConfig = prepareChainConfig({
    chainId: {chainId},
    arbitrum: {
      InitialChainOwner: '{owner}' as \`0x\${string}\`,
      DataAvailabilityCommittee: {isAnyTrust},
    },
  });

  console.log('Chain Config:');
  console.log(JSON.stringify(chainConfig, null, 2));
  return chainConfig;
}

main().catch(console.error);
`;

const ANYTRUST_CONFIG_TEMPLATE = `import 'dotenv/config';
import {
  createPublicClient,
  createWalletClient,
  http,
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

  const sequencerInboxAddress = '{sequencerInbox}' as \`0x\${string}\`;

  // DAC member public keys (BLS keys)
  const dacMembers: string[] = [];

  // Construct keyset bytes
  const keysetBytes = '0x' as \`0x\${string}\`;

  console.log('Setting valid keyset on SequencerInbox...');
  console.log('  SequencerInbox:', sequencerInboxAddress);
  console.log('  DAC members:', dacMembers.length);

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
`;

const CUSTOM_GAS_TOKEN_TEMPLATE = `import 'dotenv/config';
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
] as const;

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

  const nativeToken = '{nativeToken}' as \`0x\${string}\`;

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
  const approvalAmount = parseUnits('1000000', 18);

  const approveHash = await walletClient.writeContract({
    address: nativeToken,
    abi: erc20Abi,
    functionName: 'approve',
    args: [
      '0x0000000000000000000000000000000000000000' as \`0x\${string}\`,
      approvalAmount,
    ],
  });

  await publicClient.waitForTransactionReceipt({ hash: approveHash });
  console.log('Token approved');

  // Step 2: Prepare chain config
  const chainConfig = prepareChainConfig({
    chainId: {chainId},
    arbitrum: {
      InitialChainOwner: account.address,
      DataAvailabilityCommittee: {isAnyTrust},
    },
  });

  // Step 3: Deploy rollup with native token
  console.log('Deploying Orbit chain with custom gas token...');

  const deployResult = await createRollup({
    params: {
      config: createRollupPrepareDeploymentParamsConfig(publicClient, {
        chainId: BigInt({chainId}),
        owner: account.address,
        chainConfig,
      }),
      validators: [account.address] as \`0x\${string}\`[],
      batchPosters: [account.address] as \`0x\${string}\`[],
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
`;

/**
 * Generate Orbit chain configuration code.
 *
 * Selects a template based on input parameters and prompt keywords,
 * substitutes placeholders, and returns a complete project scaffold.
 */
export function generateOrbitConfig(
  input: GenerateOrbitConfigInput
): GenerateOrbitConfigOutput {
  const {
    prompt,
    chainId = 412346,
    owner = "0x0000000000000000000000000000000000000000",
    isAnyTrust = false,
    nativeToken,
    parentChain = "arbitrum-sepolia",
  } = input;

  const lowerPrompt = prompt.toLowerCase();

  // Select template
  let templateName: string;
  let code: string;

  if (nativeToken || lowerPrompt.includes("gas token") || lowerPrompt.includes("native token")) {
    templateName = "Orbit Custom Gas Token";
    code = CUSTOM_GAS_TOKEN_TEMPLATE;
  } else if (isAnyTrust || lowerPrompt.includes("anytrust") || lowerPrompt.includes("dac")) {
    templateName = "Orbit AnyTrust Config";
    code = ANYTRUST_CONFIG_TEMPLATE;
  } else {
    templateName = "Orbit Chain Config";
    code = CHAIN_CONFIG_TEMPLATE;
  }

  // Get parent chain info
  const parentRpc = PARENT_CHAIN_RPCS[parentChain] ?? PARENT_CHAIN_RPCS["arbitrum-sepolia"];
  const parentChainId = PARENT_CHAIN_IDS[parentChain] ?? 421614;
  const parentChainName = parentChain.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  // Substitute placeholders
  code = code.replace(/\{chainId\}/g, String(chainId));
  code = code.replace(/\{owner\}/g, owner);
  code = code.replace(/\{isAnyTrust\}/g, isAnyTrust ? "true" : "false");
  code = code.replace(/\{parentChainId\}/g, String(parentChainId));
  code = code.replace(/\{parentChainName\}/g, parentChainName);
  code = code.replace(/\{parentChainRpc\}/g, parentRpc);

  if (nativeToken) {
    code = code.replace(/\{nativeToken\}/g, nativeToken);
  }

  code = code.replace(/\{sequencerInbox\}/g, "0x0000000000000000000000000000000000000000");

  // Build files dict
  const files: Record<string, string> = {};
  if (templateName === "Orbit Chain Config") {
    files["scripts/prepare-chain-config.ts"] = code;
  } else if (templateName.includes("AnyTrust")) {
    files["scripts/configure-anytrust.ts"] = code;
  } else if (templateName.includes("Gas Token")) {
    files["scripts/deploy-custom-gas-token.ts"] = code;
  } else {
    files["scripts/configure.ts"] = code;
  }

  // Add .env.example
  files[".env.example"] = [
    "# Deployer private key (with 0x prefix)",
    "DEPLOYER_PRIVATE_KEY=0x...",
    "",
    "# Parent chain RPC URL",
    `PARENT_CHAIN_RPC=${parentRpc}`,
    "",
    "# Chain configuration",
    `CHAIN_ID=${chainId}`,
    "",
  ].join("\n");

  const firstFile = Object.keys(files)[0];

  return {
    templateUsed: templateName,
    files,
    dependencies: ORBIT_DEPENDENCIES,
    envVars: ["DEPLOYER_PRIVATE_KEY", "PARENT_CHAIN_RPC"],
    parentChain: {
      name: parentChain,
      chainId: parentChainId,
      rpc: parentRpc,
    },
    chainConfig: {
      chainId,
      owner,
      isAnyTrust,
      nativeToken,
    },
    setupInstructions: [
      "1. Install dependencies: npm install @arbitrum/orbit-sdk viem dotenv",
      "2. Copy .env.example to .env and fill in your private key",
      `3. Run the script: npx tsx ${firstFile}`,
    ],
    disclaimer: TEMPLATE_DISCLAIMER,
  };
}

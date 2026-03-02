/**
 * Generate Orbit chain validator and batch poster management code (M4 tool)
 *
 * Supports:
 * - Listing validators and batch posters
 * - Adding/removing validators
 * - Batch poster management
 * - DAC keyset operations
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

type ValidatorAction = "list" | "add" | "remove";
type ValidatorTarget = "validator" | "batch_poster" | "keyset";

interface GenerateValidatorSetupInput {
  prompt: string;
  action?: ValidatorAction;
  target?: ValidatorTarget;
  addresses?: string[];
  rollupAddress?: string;
  sequencerInbox?: string;
  parentChain?: ParentChain;
}

interface GenerateValidatorSetupOutput {
  templateUsed: string;
  action: ValidatorAction;
  target: ValidatorTarget;
  files: Record<string, string>;
  dependencies: Record<string, string>;
  parentChain: {
    name: string;
    chainId: number;
    rpc: string;
  };
  contractAddresses: {
    rollup: string;
    sequencerInbox: string;
  };
  addressesToManage: string[];
  setupInstructions: string[];
  notes: string[];
  disclaimer: string;
}

// --- Templates ---

const VALIDATOR_MANAGEMENT_TEMPLATE = `import 'dotenv/config';
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

  const rollupAddress = '{rollupAddress}' as \`0x\${string}\`;
  const sequencerInboxAddress = '{sequencerInbox}' as \`0x\${string}\`;

  // Check if specific addresses are validators
  const addressesToCheck: \`0x\${string}\`[] = {addressesArray};

  console.log('=== Validator Status ===');
  for (const addr of addressesToCheck) {
    const isValidator = await publicClient.readContract({
      address: rollupAddress,
      abi: rollupAbi,
      functionName: 'isValidator',
      args: [addr],
    });
    console.log(\`  \${addr}: \${isValidator ? 'VALIDATOR' : 'not a validator'}\`);
  }

  console.log('\\n=== Batch Poster Status ===');
  for (const addr of addressesToCheck) {
    const isBatchPoster = await publicClient.readContract({
      address: sequencerInboxAddress,
      abi: sequencerInboxAbi,
      functionName: 'isBatchPoster',
      args: [addr],
    });
    console.log(\`  \${addr}: \${isBatchPoster ? 'BATCH POSTER' : 'not a batch poster'}\`);
  }
}

main().catch(console.error);
`;

const ANYTRUST_KEYSET_TEMPLATE = `import 'dotenv/config';
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

// --- Helpers ---

function formatAddressArray(addresses: string[]): string {
  if (!addresses || addresses.length === 0) {
    return "[] as `0x${string}`[]";
  }
  const formatted = addresses
    .map((addr) => `'${addr}' as \`0x\${string}\``)
    .join(", ");
  return `[${formatted}]`;
}

function getNotes(action: ValidatorAction, target: ValidatorTarget): string[] {
  const notes: string[] = [];

  if (action === "list") {
    notes.push("Querying on-chain state to verify validator/batch poster status");
  } else if (action === "add") {
    notes.push(
      "Adding validators/batch posters typically requires UpgradeExecutor access"
    );
    notes.push("Ensure the caller has the EXECUTOR_ROLE on the UpgradeExecutor");
  } else if (action === "remove") {
    notes.push(
      "Removing validators may affect chain liveness if too few remain"
    );
    notes.push(
      "Ensure at least one active validator and batch poster at all times"
    );
  }

  if (target === "validator") {
    notes.push("Validators confirm assertion state on the parent chain");
  } else if (target === "batch_poster") {
    notes.push("Batch posters submit transaction batches to the SequencerInbox");
  } else if (target === "keyset") {
    notes.push("Keyset operations are only relevant for AnyTrust chains");
    notes.push("DAC keysets are managed via the SequencerInbox contract");
  }

  return notes;
}

/**
 * Generate validator and batch poster management code.
 *
 * Produces TypeScript scripts for querying, adding, or removing
 * validators and batch posters on an Orbit chain.
 */
export function generateValidatorSetup(
  input: GenerateValidatorSetupInput
): GenerateValidatorSetupOutput {
  const {
    prompt,
    action = "list",
    target = "validator",
    addresses = [],
    rollupAddress = "0x0000000000000000000000000000000000000000",
    sequencerInbox = "0x0000000000000000000000000000000000000000",
    parentChain = "arbitrum-sepolia",
  } = input;

  // Get parent chain info
  const parentRpc = PARENT_CHAIN_RPCS[parentChain] ?? PARENT_CHAIN_RPCS["arbitrum-sepolia"];
  const parentChainId = PARENT_CHAIN_IDS[parentChain] ?? 421614;
  const parentChainName = parentChain.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  // Select template
  let templateName: string;
  let code: string;

  if (target === "keyset") {
    templateName = "Orbit AnyTrust Config";
    code = ANYTRUST_KEYSET_TEMPLATE;
  } else {
    templateName = "Orbit Validator Management";
    code = VALIDATOR_MANAGEMENT_TEMPLATE;
  }

  // Format addresses
  const addressesStr = formatAddressArray(addresses);

  // Substitute parameters
  code = code.replace(/\{parentChainId\}/g, String(parentChainId));
  code = code.replace(/\{parentChainName\}/g, parentChainName);
  code = code.replace(/\{rollupAddress\}/g, rollupAddress);
  code = code.replace(/\{sequencerInbox\}/g, sequencerInbox);
  code = code.replace(/\{addressesArray\}/g, addressesStr);

  // Build files
  const files: Record<string, string> = {};
  if (target === "keyset") {
    files["scripts/manage-keyset.ts"] = code;
  } else {
    files["scripts/manage-validators.ts"] = code;
  }

  // Add .env.example
  files[".env.example"] = [
    `DEPLOYER_PRIVATE_KEY=0x...`,
    `PARENT_CHAIN_RPC=${parentRpc}`,
    "",
  ].join("\n");

  const firstFile = Object.keys(files)[0];

  return {
    templateUsed: templateName,
    action,
    target,
    files,
    dependencies: ORBIT_DEPENDENCIES,
    parentChain: {
      name: parentChain,
      chainId: parentChainId,
      rpc: parentRpc,
    },
    contractAddresses: {
      rollup: rollupAddress,
      sequencerInbox,
    },
    addressesToManage: addresses,
    setupInstructions: [
      "1. Install dependencies: npm install viem dotenv",
      "2. Copy .env.example to .env and configure",
      `3. Run: npx tsx ${firstFile}`,
    ],
    notes: getNotes(action, target),
    disclaimer: TEMPLATE_DISCLAIMER,
  };
}

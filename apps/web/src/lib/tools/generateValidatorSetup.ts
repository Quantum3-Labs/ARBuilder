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
  validateTemplateOutput,
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

const MUTATE_VALIDATOR_TEMPLATE = `import 'dotenv/config';
import * as fs from 'fs';
import {
  createPublicClient,
  createWalletClient,
  http,
  encodeFunctionData,
  Chain,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';

// Rollup ABI — setValidator + isValidator
const rollupAbi = [
  {
    name: 'setValidator',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'validators', type: 'address[]' },
      { name: 'vals', type: 'bool[]' },
    ],
    outputs: [],
  },
  {
    name: 'isValidator',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'validator', type: 'address' }],
    outputs: [{ name: '', type: 'bool' }],
  },
] as const;

// SequencerInbox ABI — setIsBatchPoster + isBatchPoster
const sequencerInboxAbi = [
  {
    name: 'setIsBatchPoster',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'addr', type: 'address' },
      { name: 'isBatchPoster', type: 'bool' },
    ],
    outputs: [],
  },
  {
    name: 'isBatchPoster',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'addr', type: 'address' }],
    outputs: [{ name: '', type: 'bool' }],
  },
] as const;

// UpgradeExecutor ABI — executeCall
const upgradeExecutorAbi = [
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
 * {actionVerb} validators and/or batch posters on an Orbit chain.
 *
 * Routes through UpgradeExecutor since only the executor has permission
 * to call setValidator() on the Rollup and setIsBatchPoster() on SequencerInbox.
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

  // Read deployment.json for contract addresses
  if (!fs.existsSync('deployment.json')) {
    console.error('Error: deployment.json not found. Run deploy-rollup.ts first.');
    process.exit(1);
  }
  const deployment = JSON.parse(fs.readFileSync('deployment.json', 'utf-8'));
  const rollupAddress = deployment.coreContracts.rollup as \`0x\${string}\`;
  const sequencerInboxAddress = deployment.coreContracts.sequencerInbox as \`0x\${string}\`;
  const upgradeExecutorAddress = deployment.coreContracts.upgradeExecutor as \`0x\${string}\`;

  console.log('Rollup:', rollupAddress);
  console.log('SequencerInbox:', sequencerInboxAddress);
  console.log('UpgradeExecutor:', upgradeExecutorAddress);

  const addresses: \`0x\${string}\`[] = {addressesArray};
  if (addresses.length === 0) {
    console.error('Error: No addresses specified. Add addresses to the array above.');
    process.exit(1);
  }

  // --- {actionVerb} Validators ---
  console.log('\\n=== {actionVerb} Validators ===');
  const validatorCalldata = encodeFunctionData({
    abi: rollupAbi,
    functionName: 'setValidator',
    args: [addresses, addresses.map(() => {actionBool})],
  });

  const validatorTxHash = await walletClient.writeContract({
    address: upgradeExecutorAddress,
    abi: upgradeExecutorAbi,
    functionName: 'executeCall',
    args: [rollupAddress, validatorCalldata],
  });
  console.log('  Tx:', validatorTxHash);
  const validatorReceipt = await publicClient.waitForTransactionReceipt({ hash: validatorTxHash });
  console.log('  Status:', validatorReceipt.status);

  // --- {actionVerb} Batch Posters ---
  console.log('\\n=== {actionVerb} Batch Posters ===');
  for (const addr of addresses) {
    const batchPosterCalldata = encodeFunctionData({
      abi: sequencerInboxAbi,
      functionName: 'setIsBatchPoster',
      args: [addr, {actionBool}],
    });

    const bpTxHash = await walletClient.writeContract({
      address: upgradeExecutorAddress,
      abi: upgradeExecutorAbi,
      functionName: 'executeCall',
      args: [sequencerInboxAddress, batchPosterCalldata],
    });
    console.log(\`  \${addr} tx: \${bpTxHash}\`);
    const bpReceipt = await publicClient.waitForTransactionReceipt({ hash: bpTxHash });
    console.log(\`  Status: \${bpReceipt.status}\`);
  }

  // --- Verify final state ---
  console.log('\\n=== Verification ===');
  for (const addr of addresses) {
    const isValidator = await publicClient.readContract({
      address: rollupAddress,
      abi: rollupAbi,
      functionName: 'isValidator',
      args: [addr],
    });
    const isBatchPoster = await publicClient.readContract({
      address: sequencerInboxAddress,
      abi: sequencerInboxAbi,
      functionName: 'isBatchPoster',
      args: [addr],
    });
    console.log(\`  \${addr}: validator=\${isValidator}, batchPoster=\${isBatchPoster}\`);
  }
}

main().catch(console.error);
`;

const VALIDATOR_MANAGEMENT_TEMPLATE = `import 'dotenv/config';
import * as fs from 'fs';
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

  // Read contract addresses from deployment.json if available
  let rollupAddress: \`0x\${string}\` = '{rollupAddress}' as \`0x\${string}\`;
  let sequencerInboxAddress: \`0x\${string}\` = '{sequencerInbox}' as \`0x\${string}\`;

  if (fs.existsSync('deployment.json')) {
    const deployment = JSON.parse(fs.readFileSync('deployment.json', 'utf-8'));
    rollupAddress = deployment.coreContracts.rollup as \`0x\${string}\`;
    sequencerInboxAddress = deployment.coreContracts.sequencerInbox as \`0x\${string}\`;
    console.log('Loaded contract addresses from deployment.json');
  }

  // Check if specific addresses are validators
  const addressesToCheck: \`0x\${string}\`[] = {addressesArray};

  console.log('=== Validator Status ===');
  console.log('  Rollup:', rollupAddress);
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
  console.log('  SequencerInbox:', sequencerInboxAddress);
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
import * as fs from 'fs';
import {
  createPublicClient,
  createWalletClient,
  http,
  keccak256,
  Chain,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { prepareKeyset, setValidKeyset } from '@arbitrum/chain-sdk';

// SequencerInbox ABI for keyset verification only
const sequencerInboxAbi = [
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

/**
 * Configure AnyTrust DAC keyset on the SequencerInbox.
 *
 * Uses SDK's prepareKeyset() + buildSetValidKeyset() for correct encoding
 * and UpgradeExecutor routing.
 *
 * Prerequisites:
 *   1. Deploy rollup: npm run deploy:rollup (creates deployment.json)
 *   2. Generate BLS keys: npm run generate:das-keys
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

  // Read from deployment.json
  if (!fs.existsSync('deployment.json')) {
    console.error('Error: deployment.json not found. Run deploy-rollup.ts first.');
    process.exit(1);
  }
  const deployment = JSON.parse(fs.readFileSync('deployment.json', 'utf-8'));
  const sequencerInboxAddress = deployment.coreContracts.sequencerInbox as \`0x\${string}\`;
  console.log('SequencerInbox:', sequencerInboxAddress);
  console.log('UpgradeExecutor:', deployment.coreContracts.upgradeExecutor);

  // Load BLS key — das_bls.pub is base64-encoded, must decode
  const dasKeyPath = 'das-keys/das_bls.pub';
  if (!fs.existsSync(dasKeyPath)) {
    console.error('Error: No BLS key at', dasKeyPath);
    console.error('Generate: npm run generate:das-keys');
    process.exit(1);
  }
  const blsPubKeyBase64 = fs.readFileSync(dasKeyPath, 'utf-8').trim();
  console.log('BLS key (base64):', blsPubKeyBase64.length, 'chars');

  // Encode keyset via SDK — takes base64 strings, handles decoding + encoding internally
  const keyset = prepareKeyset([blsPubKeyBase64], 1);

  // Register via SDK — handles UpgradeExecutor routing, returns receipt directly
  console.log('\\nRegistering keyset via setValidKeyset()...');
  const receipt = await setValidKeyset({
    coreContracts: deployment.coreContracts,
    keyset,
    publicClient,
    walletClient,
  });
  console.log('  Tx:', receipt.transactionHash, '- Status:', receipt.status);

  // Verify
  const keysetHash = keccak256(keyset);
  const isValid = await publicClient.readContract({
    address: sequencerInboxAddress,
    abi: sequencerInboxAbi,
    functionName: 'isValidKeysetHash',
    args: [keysetHash],
  });
  console.log('\\nKeyset hash:', keysetHash, isValid ? '(VALID)' : '(NOT FOUND — check UpgradeExecutor role)');
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
  } else if (action === "add") {
    templateName = "Orbit Add Validators";
    code = MUTATE_VALIDATOR_TEMPLATE;
  } else if (action === "remove") {
    templateName = "Orbit Remove Validators";
    code = MUTATE_VALIDATOR_TEMPLATE;
  } else {
    templateName = "Orbit Validator Management";
    code = VALIDATOR_MANAGEMENT_TEMPLATE;
  }

  // Format addresses
  const addressesStr = formatAddressArray(addresses);

  // Substitute parameters
  const actionVerb = action === "remove" ? "Removing" : "Adding";
  const actionBool = action === "remove" ? "false" : "true";
  code = code.replace(/\{parentChainId\}/g, String(parentChainId));
  code = code.replace(/\{parentChainName\}/g, parentChainName);
  code = code.replace(/\{rollupAddress\}/g, rollupAddress);
  code = code.replace(/\{sequencerInbox\}/g, sequencerInbox);
  code = code.replace(/\{addressesArray\}/g, addressesStr);
  code = code.replace(/\{actionVerb\}/g, actionVerb);
  code = code.replace(/\{actionBool\}/g, actionBool);

  // Build files
  const files: Record<string, string> = {};
  if (target === "keyset") {
    files["scripts/manage-keyset.ts"] = validateTemplateOutput(code, "manage-keyset");
  } else {
    files["scripts/manage-validators.ts"] = validateTemplateOutput(code, "manage-validators");
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

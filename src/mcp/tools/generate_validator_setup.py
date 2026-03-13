"""
Generate Orbit chain validator and batch poster management code.

Supports:
- Listing validators and batch posters
- Adding/removing validators
- Batch poster management
- DAC keyset operations
"""

from typing import Any

from ...templates.orbit_templates import (
    ORBIT_DEPENDENCIES,
    PARENT_CHAIN_RPCS,
    get_orbit_template,
    validate_template_output,
)
from .base import BaseTool
from .generate_stylus_code import TEMPLATE_DISCLAIMER

# Inline template for add/remove validator operations via UpgradeExecutor
MUTATE_VALIDATOR_TEMPLATE_CODE = r"""import 'dotenv/config';
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
  id: {parent_chain_id},
  name: '{parent_chain_name}',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: {
    default: { http: [process.env.PARENT_CHAIN_RPC!] },
  },
};

/**
 * {action_verb} validators and/or batch posters on an Orbit chain.
 *
 * Routes through UpgradeExecutor since only the executor has permission
 * to call setValidator() on the Rollup and setIsBatchPoster() on SequencerInbox.
 */
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

  // Read deployment.json for contract addresses
  if (!fs.existsSync('deployment.json')) {
    console.error('Error: deployment.json not found. Run deploy-rollup.ts first.');
    process.exit(1);
  }
  const deployment = JSON.parse(fs.readFileSync('deployment.json', 'utf-8'));
  const rollupAddress = deployment.coreContracts.rollup as `0x${string}`;
  const sequencerInboxAddress = deployment.coreContracts.sequencerInbox as `0x${string}`;
  const upgradeExecutorAddress = deployment.coreContracts.upgradeExecutor as `0x${string}`;

  console.log('Rollup:', rollupAddress);
  console.log('SequencerInbox:', sequencerInboxAddress);
  console.log('UpgradeExecutor:', upgradeExecutorAddress);

  const addresses: `0x${string}`[] = {addresses_array};
  if (addresses.length === 0) {
    console.error('Error: No addresses specified. Add addresses to the array above.');
    process.exit(1);
  }

  // --- {action_verb} Validators ---
  console.log('\n=== {action_verb} Validators ===');
  const validatorCalldata = encodeFunctionData({
    abi: rollupAbi,
    functionName: 'setValidator',
    args: [addresses, addresses.map(() => {action_bool})],
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

  // --- {action_verb} Batch Posters ---
  console.log('\n=== {action_verb} Batch Posters ===');
  for (const addr of addresses) {
    const batchPosterCalldata = encodeFunctionData({
      abi: sequencerInboxAbi,
      functionName: 'setIsBatchPoster',
      args: [addr, {action_bool}],
    });

    const bpTxHash = await walletClient.writeContract({
      address: upgradeExecutorAddress,
      abi: upgradeExecutorAbi,
      functionName: 'executeCall',
      args: [sequencerInboxAddress, batchPosterCalldata],
    });
    console.log(`  ${addr} tx: ${bpTxHash}`);
    const bpReceipt = await publicClient.waitForTransactionReceipt({ hash: bpTxHash });
    console.log(`  Status: ${bpReceipt.status}`);
  }

  // --- Verify final state ---
  console.log('\n=== Verification ===');
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
    console.log(`  ${addr}: validator=${isValidator}, batchPoster=${isBatchPoster}`);
  }
}

main().catch(console.error);
"""


class GenerateValidatorSetupTool(BaseTool):
    """Generate validator and batch poster management scripts."""

    name = "generate_validator_setup"
    description = """Generate code for managing Orbit chain validators and batch posters.

Supports:
- Listing current validators and batch posters
- Checking validator/batch poster status
- Adding validators via UpgradeExecutor
- Managing batch posters on SequencerInbox
- AnyTrust DAC keyset management

Generates TypeScript scripts using viem for contract interaction."""

    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Description of the validator management action",
            },
            "action": {
                "type": "string",
                "enum": ["list", "add", "remove"],
                "description": "Action to perform",
                "default": "list",
            },
            "target": {
                "type": "string",
                "enum": ["validator", "batch_poster", "keyset"],
                "description": "Target entity to manage",
                "default": "validator",
            },
            "addresses": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Addresses to check, add, or remove",
            },
            "rollup_address": {
                "type": "string",
                "description": "Rollup contract address on parent chain",
            },
            "sequencer_inbox": {
                "type": "string",
                "description": "SequencerInbox contract address on parent chain",
            },
            "parent_chain": {
                "type": "string",
                "enum": [
                    "arbitrum-one",
                    "arbitrum-sepolia",
                    "ethereum-mainnet",
                    "ethereum-sepolia",
                ],
                "description": "Parent chain where contracts are deployed",
                "default": "arbitrum-sepolia",
            },
        },
        "required": ["prompt"],
    }

    def __init__(self, vectordb=None):
        """Initialize with optional vector database."""
        self.vectordb = vectordb

    def execute(self, **kwargs) -> dict[str, Any]:
        """Generate validator/batch poster management code."""
        prompt = kwargs.get("prompt", "")
        action = kwargs.get("action", "list")
        target = kwargs.get("target", "validator")
        addresses = kwargs.get("addresses", [])
        rollup_address = kwargs.get(
            "rollup_address", "0x0000000000000000000000000000000000000000"
        )
        sequencer_inbox = kwargs.get(
            "sequencer_inbox", "0x0000000000000000000000000000000000000000"
        )
        parent_chain = kwargs.get("parent_chain", "arbitrum-sepolia")

        if not prompt:
            return {"error": "prompt is required"}

        # Get parent chain info
        parent_rpc = PARENT_CHAIN_RPCS.get(
            parent_chain, PARENT_CHAIN_RPCS["arbitrum-sepolia"]
        )
        parent_chain_id = self._get_parent_chain_id(parent_chain)
        parent_chain_name = parent_chain.replace("-", " ").title()

        # Select appropriate template based on target and action
        template_name: str
        if target == "keyset":
            template = get_orbit_template("anytrust_config")
            template_name = template.name if template else "Orbit AnyTrust Config"
        elif action in ("add", "remove"):
            template = None  # Use inline mutate template
            template_name = (
                "Orbit Add Validators"
                if action == "add"
                else "Orbit Remove Validators"
            )
        else:
            template = get_orbit_template("validator_management")
            template_name = template.name if template else "Orbit Validator Management"

        if target == "keyset" and not template:
            return {"error": "Template not found for keyset target"}
        if action == "list" and target != "keyset" and not template:
            return {"error": "Template not found for validator list"}

        # Format addresses array
        addresses_str = self._format_address_array(addresses)

        # Get code from the appropriate source
        if action in ("add", "remove"):
            code = MUTATE_VALIDATOR_TEMPLATE_CODE
        else:
            code = template.code  # type: ignore[union-attr]

        # Substitute parameters
        action_verb = "Removing" if action == "remove" else "Adding"
        action_bool = "false" if action == "remove" else "true"
        code = code.replace("{parent_chain_id}", str(parent_chain_id))
        code = code.replace("{parent_chain_name}", parent_chain_name)
        code = code.replace("{rollup_address}", rollup_address)
        code = code.replace("{sequencer_inbox}", sequencer_inbox)
        code = code.replace("{addresses_array}", addresses_str)
        code = code.replace("{action_verb}", action_verb)
        code = code.replace("{action_bool}", action_bool)

        # Build files
        files = {}
        if target == "keyset":
            files["scripts/manage-keyset.ts"] = validate_template_output(
                code, "manage-keyset"
            )
        else:
            files["scripts/manage-validators.ts"] = validate_template_output(
                code, "manage-validators"
            )

        # Add .env.example
        files[".env.example"] = (
            f"DEPLOYER_PRIVATE_KEY=0x...\n"
            f"PARENT_CHAIN_RPC={parent_rpc}\n"
        )

        result = {
            "template_used": template_name,
            "action": action,
            "target": target,
            "files": files,
            "dependencies": ORBIT_DEPENDENCIES,
            "parent_chain": {
                "name": parent_chain,
                "chain_id": parent_chain_id,
                "rpc": parent_rpc,
            },
            "contract_addresses": {
                "rollup": rollup_address,
                "sequencer_inbox": sequencer_inbox,
            },
            "addresses_to_manage": addresses,
            "setup_instructions": [
                "1. Install dependencies: npm install viem dotenv",
                "2. Copy .env.example to .env and configure",
                f"3. Run: npx tsx {list(files.keys())[0]}",
            ],
            "notes": self._get_notes(action, target),
            "disclaimer": TEMPLATE_DISCLAIMER,
        }

        return result

    @staticmethod
    def _format_address_array(addresses: list[str]) -> str:
        """Format a list of addresses as a TypeScript array literal."""
        if not addresses:
            return "[] as `0x${string}`[]"
        formatted = ", ".join(
            f"'{addr}' as `0x${{string}}`" for addr in addresses
        )
        return f"[{formatted}]"

    @staticmethod
    def _get_parent_chain_id(parent_chain: str) -> int:
        """Get chain ID for the parent chain."""
        chain_ids = {
            "ethereum-mainnet": 1,
            "ethereum-sepolia": 11155111,
            "arbitrum-one": 42161,
            "arbitrum-sepolia": 421614,
        }
        return chain_ids.get(parent_chain, 421614)

    @staticmethod
    def _get_notes(action: str, target: str) -> list[str]:
        """Get relevant notes for the action and target."""
        notes = []

        if action == "list":
            notes.append(
                "Querying on-chain state to verify validator/batch poster status"
            )
        elif action == "add":
            notes.append(
                "Adding validators/batch posters typically requires UpgradeExecutor access"
            )
            notes.append(
                "Ensure the caller has the EXECUTOR_ROLE on the UpgradeExecutor"
            )
        elif action == "remove":
            notes.append(
                "Removing validators may affect chain liveness if too few remain"
            )
            notes.append(
                "Ensure at least one active validator and batch poster at all times"
            )

        if target == "validator":
            notes.append(
                "Validators confirm assertion state on the parent chain"
            )
        elif target == "batch_poster":
            notes.append(
                "Batch posters submit transaction batches to the SequencerInbox"
            )
        elif target == "keyset":
            notes.append(
                "Keyset operations are only relevant for AnyTrust chains"
            )
            notes.append(
                "DAC keysets are managed via the SequencerInbox contract"
            )

        return notes

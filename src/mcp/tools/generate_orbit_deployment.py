"""
Generate Orbit chain deployment code.

Supports:
- Rollup deployment (createRollup)
- Token bridge deployment (createTokenBridge)
- Full deployment (rollup + token bridge)
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

# Known RollupCreator contract addresses from @arbitrum/orbit-sdk
ROLLUP_CREATOR_ADDRESSES = {
    "v2.1": {
        1: "0x8c88430658a03497D13cDff7684D37b15aA2F3e1",       # Ethereum Mainnet
        42161: "0x79607f00e61E6d7C0E6330bd7E9c4AC320D50FC9",   # Arbitrum One
        421614: "0xd2Ec8376B1dF436fAb18120E416d3F2BeC61275b",  # Arbitrum Sepolia
        11155111: "0xfb774eA8A92ae528A596c8D90CBCF1bdBC4Cee79", # Ethereum Sepolia
    },
    "v3.1": {
        1: "0x43698080f40dB54DEE6871540037b8AB8fD0AB44",       # Ethereum Mainnet
        42161: "0xB90e53fd945Cd28Ec4728cBfB566981dD571eB8b",   # Arbitrum One
        421614: "0x5F45675AC8DDF7d45713b2c7D191B287475C16cF",  # Arbitrum Sepolia
        11155111: "0x687Bc1D23390875a868Db158DA1cDC8998E31640", # Ethereum Sepolia
    },
}

# Known TokenBridgeCreator addresses (for custom gas token approval)
TOKEN_BRIDGE_CREATOR_ADDRESSES = {
    421614: "0x56C486D3786fA26cc61473C499A36Eb9CC1FbD8E",  # Arbitrum Sepolia
    42161: "0x2f5624dc8800dfA0A82AC03509Ef8bb8E7Ac000e",   # Arbitrum One
    11155111: "0xB1CB026025d32bAe5D0A5B3d905a22B31E8aD7Bc",  # Ethereum Sepolia
    1: "0x60D9A46F24D5a35b95A3F6c4f96074d44c1a3f3c",       # Ethereum Mainnet
}

# Standalone approve-token.ts script — generated when nativeToken is set
# Uses .replace() placeholders: {parent_chain_id}, {parent_chain_name}, {native_token}
APPROVE_TOKEN_TEMPLATE = """import 'dotenv/config';
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
const ROLLUP_CREATOR: Record<number, `0x${string}`> = {
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
  id: {parent_chain_id},
  name: '{parent_chain_name}',
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

  const nativeToken = '{native_token}' as `0x${string}`;
  const rollupCreator = ROLLUP_CREATOR[{parent_chain_id}];

  if (!rollupCreator) {
    console.error('No known RollupCreator for chain ID {parent_chain_id}.');
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
"""


class GenerateOrbitDeploymentTool(BaseTool):
    """Generate Orbit chain deployment scripts."""

    name = "generate_orbit_deployment"
    description = """Generate deployment code for Orbit chains.

Supports:
- Rollup deployment with createRollup()
- Token bridge deployment with createTokenBridge()
- Full deployment (rollup + token bridge in sequence)

Configures validators, batch posters, native tokens, and rollup versions.
Generates TypeScript scripts using @arbitrum/orbit-sdk."""

    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Description of the deployment requirements",
            },
            "deployment_type": {
                "type": "string",
                "enum": ["rollup", "token_bridge", "full"],
                "description": "Type of deployment to generate",
                "default": "rollup",
            },
            "validators": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Validator addresses for the rollup",
            },
            "batch_posters": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Batch poster addresses",
            },
            "native_token": {
                "type": "string",
                "description": "Custom gas token address (for custom gas token chains)",
            },
            "parent_chain": {
                "type": "string",
                "enum": [
                    "arbitrum-one",
                    "arbitrum-sepolia",
                    "ethereum-mainnet",
                    "ethereum-sepolia",
                ],
                "description": "Parent chain for deployment",
                "default": "arbitrum-sepolia",
            },
            "rollup_version": {
                "type": "string",
                "enum": ["v2.1", "v3.1"],
                "description": "Rollup version to deploy",
                "default": "v3.1",
            },
            "chain_id": {
                "type": "integer",
                "description": "Chain ID for the new Orbit chain",
                "default": 412346,
            },
            "is_anytrust": {
                "type": "boolean",
                "description": "Whether to deploy as AnyTrust chain",
                "default": False,
            },
            "rollup_address": {
                "type": "string",
                "description": "Existing rollup address (for token_bridge deployment)",
            },
        },
        "required": ["prompt"],
    }

    def __init__(self, vectordb=None):
        """Initialize with optional vector database."""
        self.vectordb = vectordb

    def execute(self, **kwargs) -> dict[str, Any]:
        """Generate Orbit chain deployment code."""
        prompt = kwargs.get("prompt", "")
        deployment_type = kwargs.get("deployment_type", "rollup")
        validators = kwargs.get("validators", [])
        batch_posters = kwargs.get("batch_posters", [])
        native_token = kwargs.get("native_token")
        parent_chain = kwargs.get("parent_chain", "arbitrum-sepolia")
        rollup_version = kwargs.get("rollup_version", "v3.1")
        chain_id = kwargs.get("chain_id", 412346)
        is_anytrust = kwargs.get("is_anytrust", False)
        rollup_address = kwargs.get("rollup_address", "0x0000000000000000000000000000000000000000")

        if not prompt:
            return {"error": "prompt is required"}

        # Get parent chain info
        parent_rpc = PARENT_CHAIN_RPCS.get(parent_chain, PARENT_CHAIN_RPCS["arbitrum-sepolia"])
        parent_chain_id = self._get_parent_chain_id(parent_chain)
        parent_chain_name = parent_chain.replace("-", " ").title()

        # Format validator/batch poster arrays
        validators_str = self._format_address_array(validators)
        batch_posters_str = self._format_address_array(batch_posters)

        files = {}

        # Generate rollup deployment
        if deployment_type in ("rollup", "full"):
            rollup_template = get_orbit_template("deploy_rollup")
            if rollup_template:
                code = rollup_template.code
                code = self._substitute_params(
                    code,
                    chain_id=chain_id,
                    parent_chain_id=parent_chain_id,
                    parent_chain_name=parent_chain_name,
                    is_anytrust=is_anytrust,
                    validators_str=validators_str,
                    batch_posters_str=batch_posters_str,
                    native_token=native_token,
                )
                # Look up the known RollupCreator address for this version + parent chain
                version_addresses = ROLLUP_CREATOR_ADDRESSES.get(
                    rollup_version, ROLLUP_CREATOR_ADDRESSES["v3.1"]
                )
                rollup_creator_address = version_addresses.get(
                    parent_chain_id, "0x0000000000000000000000000000000000000000"
                )

                # Apply version-specific modifications
                version_label = "v2.1 / classic" if rollup_version == "v2.1" else "v3.1 / BoLD"
                code = code.replace(
                    "console.log('Deploying Orbit chain...');",
                    f"console.log('Deploying Orbit chain ({version_label})...');\n"
                    f"  console.log('  RollupCreator: {rollup_creator_address}');",
                )
                if rollup_version == "v2.1":
                    code = code.replace(
                        "  // Deploy rollup\n",
                        f"  // Deploy rollup — v2.1 uses classic challenge protocol\n"
                        f"  // RollupCreator: {rollup_creator_address}\n"
                        "  // baseStake = 0.1 ETH, stakeToken = ETH (default)\n",
                    )
                    code = code.replace(
                        "    walletClient,\n  }});",
                        "    parentChainPublicClient: publicClient,\n"
                        "    // v2.1: classic challenge protocol (stable, non-BoLD)\n"
                        "    rollupCreatorVersion: 'v2.1',\n"
                        "  }});",
                    )
                    code = code.replace(
                        "console.log('\\nRollup deployed successfully!');",
                        "console.log('\\nRollup deployed successfully! (v2.1 classic)');\n"
                        "  console.log('\\nv2.1 validator config:');\n"
                        "  console.log('  Base stake: 0.1 ETH (default)');\n"
                        "  console.log('  Stake token: ETH');",
                    )
                else:
                    code = code.replace(
                        "  // Deploy rollup\n",
                        f"  // Deploy rollup — v3.1 uses BoLD challenge protocol\n"
                        f"  // RollupCreator: {rollup_creator_address}\n",
                    )
                    code = code.replace(
                        "    walletClient,\n  }});",
                        "    parentChainPublicClient: publicClient,\n"
                        "    // v3.1: BoLD challenge protocol (default)\n"
                        "    rollupCreatorVersion: 'v3.1',\n"
                        "  }});",
                    )
                    code = code.replace(
                        "console.log('\\nRollup deployed successfully!');",
                        "console.log('\\nRollup deployed successfully! (v3.1 BoLD)');",
                    )
                files["scripts/deploy-rollup.ts"] = validate_template_output(
                    code, "deploy-rollup"
                )

            # Generate standalone approve-token.ts when using custom gas token
            if native_token:
                approve_code = APPROVE_TOKEN_TEMPLATE
                approve_code = approve_code.replace(
                    "{parent_chain_id}", str(parent_chain_id)
                )
                approve_code = approve_code.replace(
                    "{parent_chain_name}", parent_chain_name
                )
                approve_code = approve_code.replace(
                    "{native_token}", native_token
                )
                files["scripts/approve-token.ts"] = validate_template_output(
                    approve_code, "approve-token"
                )

        # Generate token bridge deployment
        if deployment_type in ("token_bridge", "full"):
            bridge_template = get_orbit_template("deploy_token_bridge")
            if bridge_template:
                code = bridge_template.code
                code = code.replace("{chain_id}", str(chain_id))
                code = code.replace("{chain_name}", f"orbit-chain-{chain_id}")
                code = code.replace("{parent_chain_id}", str(parent_chain_id))
                code = code.replace("{parent_chain_name}", parent_chain_name)
                code = code.replace("{rollup_address}", rollup_address)

                # Inject token approval for TokenBridgeCreator when using custom gas token
                if native_token:
                    tbc_address = TOKEN_BRIDGE_CREATOR_ADDRESSES.get(
                        parent_chain_id, "0x0000000000000000000000000000000000000000"
                    )

                    # Add maxUint256 to the viem import
                    code = code.replace(
                        "  createWalletClient,\n  http,\n  Chain,\n} from 'viem';",
                        "  createWalletClient,\n  http,\n  maxUint256,\n  Chain,\n} from 'viem';",
                    )

                    # Add ERC20 ABI after the chain-sdk import
                    erc20_abi_block = (
                        "\n// ERC20 ABI for token approval\n"
                        "const erc20Abi = [\n"
                        "  {\n"
                        "    name: 'approve',\n"
                        "    type: 'function',\n"
                        "    stateMutability: 'nonpayable',\n"
                        "    inputs: [\n"
                        "      { name: 'spender', type: 'address' },\n"
                        "      { name: 'amount', type: 'uint256' },\n"
                        "    ],\n"
                        "    outputs: [{ name: '', type: 'bool' }],\n"
                        "  },\n"
                        "  {\n"
                        "    name: 'allowance',\n"
                        "    type: 'function',\n"
                        "    stateMutability: 'view',\n"
                        "    inputs: [\n"
                        "      { name: 'owner', type: 'address' },\n"
                        "      { name: 'spender', type: 'address' },\n"
                        "    ],\n"
                        "    outputs: [{ name: '', type: 'uint256' }],\n"
                        "  },\n"
                        "] as const;\n"
                    )
                    code = code.replace(
                        "import { createTokenBridge } from '@arbitrum/chain-sdk';",
                        "import { createTokenBridge } from '@arbitrum/chain-sdk';\n"
                        + erc20_abi_block,
                    )

                    # Inject approval block right before "console.log('Deploying token bridge...')"
                    approval_block = (
                        "  // --- Approve native token for TokenBridgeCreator ---\n"
                        "  // Custom gas token chains require the TokenBridgeCreator to spend the native token\n"
                        "  if (nativeToken) {\n"
                        f"    const tokenBridgeCreator = '{tbc_address}' as `0x${{string}}`;\n"
                        "    console.log('Approving native token for TokenBridgeCreator...');\n"
                        "    console.log('  Token:', nativeToken);\n"
                        "    console.log('  TokenBridgeCreator:', tokenBridgeCreator);\n"
                        "\n"
                        "    const currentAllowance = await parentPublicClient.readContract({\n"
                        "      address: nativeToken,\n"
                        "      abi: erc20Abi,\n"
                        "      functionName: 'allowance',\n"
                        "      args: [account.address, tokenBridgeCreator],\n"
                        "    });\n"
                        "\n"
                        "    if (currentAllowance === 0n) {\n"
                        "      const approveTx = await parentWalletClient.writeContract({\n"
                        "        address: nativeToken,\n"
                        "        abi: erc20Abi,\n"
                        "        functionName: 'approve',\n"
                        "        args: [tokenBridgeCreator, maxUint256],\n"
                        "      });\n"
                        "      await parentPublicClient.waitForTransactionReceipt({ hash: approveTx });\n"
                        "      console.log('  Token approved for TokenBridgeCreator');\n"
                        "    } else {\n"
                        "      console.log('  Token already approved for TokenBridgeCreator');\n"
                        "    }\n"
                        "  }\n"
                        "\n"
                    )

                    # Also read nativeToken from deployment.json — add after the existing deployment.json read
                    code = code.replace(
                        "    console.log('Loaded deployment.json — rollup:', rollupAddress);",
                        "    nativeToken = deployment.nativeToken as `0x${string}` | undefined;\n"
                        "    console.log('Loaded deployment.json — rollup:', rollupAddress);\n"
                        "    if (nativeToken) console.log('  Native token:', nativeToken);",
                    )
                    # Add nativeToken variable declaration after orbitChainId
                    # Note: {chain_id} was already replaced above, so match the actual value
                    code = code.replace(
                        f"  let orbitChainId = {chain_id};",
                        f"  let orbitChainId = {chain_id};\n"
                        "  let nativeToken: `0x${string}` | undefined;",
                    )

                    code = code.replace(
                        "  console.log('Deploying token bridge...');",
                        approval_block + "  console.log('Deploying token bridge...');",
                    )

                files["scripts/deploy-token-bridge.ts"] = validate_template_output(
                    code, "deploy-token-bridge"
                )

        # Add .env.example
        env_vars = [
            "DEPLOYER_PRIVATE_KEY=0x...",
            f"PARENT_CHAIN_RPC={parent_rpc}",
        ]
        if rollup_version == "v2.1":
            env_vars.append("# Using v2.1 RollupCreator (classic challenge protocol)")
        if deployment_type in ("token_bridge", "full"):
            env_vars.append("ORBIT_CHAIN_RPC=http://localhost:8449")
        files[".env.example"] = "\n".join(env_vars) + "\n"

        # Build response
        result = {
            "template_used": f"deploy_{deployment_type}",
            "deployment_type": deployment_type,
            "rollup_version": rollup_version,
            "files": files,
            "dependencies": ORBIT_DEPENDENCIES,
            "parent_chain": {
                "name": parent_chain,
                "chain_id": parent_chain_id,
                "rpc": parent_rpc,
            },
            "chain_config": {
                "chain_id": chain_id,
                "is_anytrust": is_anytrust,
                "native_token": native_token,
                "validators": validators,
                "batch_posters": batch_posters,
            },
            "setup_instructions": self._get_setup_instructions(deployment_type, native_token),
            "notes": self._get_notes(deployment_type, native_token, is_anytrust, rollup_version),
            "disclaimer": TEMPLATE_DISCLAIMER,
        }

        return result

    def _substitute_params(
        self,
        code: str,
        chain_id: int,
        parent_chain_id: int,
        parent_chain_name: str,
        is_anytrust: bool,
        validators_str: str,
        batch_posters_str: str,
        native_token: str | None,
    ) -> str:
        """Substitute template parameters in code."""
        code = code.replace("{chain_id}", str(chain_id))
        code = code.replace("{parent_chain_id}", str(parent_chain_id))
        code = code.replace("{parent_chain_name}", parent_chain_name)
        code = code.replace("{is_anytrust}", "true" if is_anytrust else "false")
        code = code.replace("{validators_array}", validators_str)
        code = code.replace("{batch_posters_array}", batch_posters_str)

        if native_token:
            code = code.replace(
                "{native_token_line}",
                f"\n      nativeToken: '{native_token}' as `0x${{string}}`,",
            )
        else:
            code = code.replace("{native_token_line}", "")

        return code

    @staticmethod
    def _format_address_array(addresses: list[str]) -> str:
        """Format a list of addresses as a TypeScript array literal."""
        if not addresses:
            return "[account.address] as `0x${string}`[]"
        formatted = ", ".join(f"'{addr}' as `0x${{string}}`" for addr in addresses)
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
    def _get_setup_instructions(
        deployment_type: str, native_token: str | None = None,
    ) -> list[str]:
        """Get setup instructions for the deployment type."""
        instructions = [
            "1. Install dependencies: npm install",
            "2. Copy .env.example to .env and configure",
            "3. Ensure deployer account has sufficient funds on parent chain",
        ]

        if deployment_type == "rollup":
            if native_token:
                instructions.append("4. Deploy or obtain your ERC-20 gas token on the parent chain")
                instructions.append("5. Run: npx tsx scripts/approve-token.ts (approve token for RollupCreator)")
                instructions.append("6. Run: npx tsx scripts/deploy-rollup.ts")
                instructions.append("7. Save the output contract addresses for next steps")
            else:
                instructions.append("4. Run: npx tsx scripts/deploy-rollup.ts")
                instructions.append("5. Save the output contract addresses for next steps")
        elif deployment_type == "token_bridge":
            instructions.append("4. Update ORBIT_CHAIN_RPC and rollup address in the script")
            instructions.append("5. Run: npx tsx scripts/deploy-token-bridge.ts")
        elif deployment_type == "full":
            if native_token:
                instructions.append("4. Deploy or obtain your ERC-20 gas token on the parent chain")
                instructions.append("5. Run: npx tsx scripts/approve-token.ts (approve token for RollupCreator)")
                instructions.append("6. Run: npx tsx scripts/deploy-rollup.ts")
                next_step = 7
            else:
                instructions.append("4. Run: npx tsx scripts/deploy-rollup.ts")
                next_step = 5
            instructions.append(f"{next_step}. Start the Orbit chain node with the rollup contracts")
            instructions.append(f"{next_step + 1}. Update ORBIT_CHAIN_RPC and rollup address")
            instructions.append(f"{next_step + 2}. Run: npx tsx scripts/deploy-token-bridge.ts")

        return instructions

    @staticmethod
    def _get_notes(
        deployment_type: str, native_token: str | None, is_anytrust: bool,
        rollup_version: str = "v3.1",
    ) -> list[str]:
        """Get deployment notes."""
        notes = [
            "Deployment requires significant gas — ensure sufficient funds",
            "Save all contract addresses from deployment output",
        ]

        if rollup_version == "v2.1":
            notes.append("v2.1 (classic): baseStake = 0.1 ETH, classic challenge protocol")
            notes.append("v2.1 uses the classic RollupCreator via rollupCreatorVersion: 'v2.1'")
        else:
            notes.append("v3.1 (BoLD): uses assertion staking with bounded liquidity delay challenge protocol")

        if native_token:
            notes.append(
                "Custom gas token requires ERC20 approval before deployment"
            )
            notes.append(
                "The native token must be deployed on the parent chain"
            )

        if is_anytrust:
            notes.append(
                "AnyTrust chains require DAC keyset configuration after deployment"
            )

        if deployment_type == "full":
            notes.append(
                "Token bridge deployment requires the Orbit chain to be running"
            )

        return notes

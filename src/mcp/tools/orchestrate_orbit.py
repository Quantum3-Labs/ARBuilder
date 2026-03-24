"""
Orchestrate full Orbit chain deployment project scaffold.

This tool coordinates the generation of a complete Orbit chain
deployment project by combining templates for:
1. Chain configuration
2. Rollup deployment
3. Token bridge deployment
4. Validator management
5. Node configuration
6. Project scaffold (package.json, scripts, etc.)
"""

from typing import Any

from ...templates.orbit_templates import (
    ORBIT_DEPENDENCIES,
    PARENT_CHAIN_RPCS,
    generate_docker_compose,
    get_orbit_template,
    validate_template_output,
)
from .base import BaseTool
from .generate_stylus_code import TEMPLATE_DISCLAIMER


class OrchestrateOrbitTool(BaseTool):
    """Orchestrate generation of complete Orbit chain deployment projects."""

    name = "orchestrate_orbit"
    description = """Scaffold a complete Orbit chain deployment project.

Generates a production-ready project with all scripts needed to:
- Configure and deploy a new Orbit chain (Rollup or AnyTrust)
- Deploy token bridge contracts
- Configure validators and batch posters
- Generate Nitro node configuration
- Set up AnyTrust DAC (if applicable)

Includes package.json, tsconfig.json, .env.example, setup.sh, and deploy.sh."""

    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Description of the Orbit chain project",
            },
            "chain_name": {
                "type": "string",
                "description": "Name for the Orbit chain",
                "default": "my-orbit-chain",
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
            "native_token": {
                "type": "string",
                "description": "Custom gas token address (ERC20)",
            },
            "parent_chain": {
                "type": "string",
                "enum": [
                    "arbitrum-one",
                    "arbitrum-sepolia",
                    "ethereum-mainnet",
                    "ethereum-sepolia",
                ],
                "description": "Parent chain for the Orbit chain",
                "default": "arbitrum-sepolia",
            },
            "validators": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Validator addresses",
            },
            "batch_posters": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Batch poster addresses",
            },
        },
        "required": ["prompt"],
    }

    def __init__(self, vectordb=None):
        """Initialize with optional vector database."""
        super().__init__()
        self.vectordb = vectordb

    def execute(self, **kwargs) -> dict[str, Any]:
        """Generate a complete Orbit chain deployment project."""
        prompt = kwargs.get("prompt", "")
        chain_name = kwargs.get("chain_name", "my-orbit-chain")
        chain_id = kwargs.get("chain_id", 412346)
        is_anytrust = kwargs.get("is_anytrust", False)
        native_token = kwargs.get("native_token")
        parent_chain = kwargs.get("parent_chain", "arbitrum-sepolia")
        validators = kwargs.get("validators", [])
        batch_posters = kwargs.get("batch_posters", [])

        if not prompt:
            return {"error": "prompt is required"}

        # Get parent chain info
        parent_rpc = PARENT_CHAIN_RPCS.get(
            parent_chain, PARENT_CHAIN_RPCS["arbitrum-sepolia"]
        )
        parent_chain_id = self._get_parent_chain_id(parent_chain)
        parent_chain_name = parent_chain.replace("-", " ").title()

        # Format addresses
        validators_str = self._format_address_array(validators)
        batch_posters_str = self._format_address_array(batch_posters)

        # Build project files
        files = {}

        # 1. Chain config script
        config_template = get_orbit_template("chain_config")
        if config_template:
            code = config_template.code
            code = code.replace("{chain_id}", str(chain_id))
            code = code.replace("{owner}", "0x0000000000000000000000000000000000000000")
            code = code.replace("{is_anytrust}", "true" if is_anytrust else "false")
            files["scripts/prepare-chain-config.ts"] = validate_template_output(
                code, "prepare-chain-config"
            )

        # 2. Deploy rollup script
        rollup_template = get_orbit_template("deploy_rollup")
        if rollup_template:
            code = rollup_template.code
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
            files["scripts/deploy-rollup.ts"] = validate_template_output(
                code, "deploy-rollup"
            )

        # 3. Token bridge script
        bridge_template = get_orbit_template("deploy_token_bridge")
        if bridge_template:
            code = bridge_template.code
            code = code.replace("{chain_id}", str(chain_id))
            code = code.replace("{chain_name}", chain_name)
            code = code.replace("{parent_chain_id}", str(parent_chain_id))
            code = code.replace("{parent_chain_name}", parent_chain_name)
            code = code.replace(
                "{rollup_address}",
                "0x0000000000000000000000000000000000000000",
            )
            files["scripts/deploy-token-bridge.ts"] = validate_template_output(
                code, "deploy-token-bridge"
            )

        # 4. Validator management script
        validator_template = get_orbit_template("validator_management")
        if validator_template:
            code = validator_template.code
            code = code.replace("{parent_chain_id}", str(parent_chain_id))
            code = code.replace("{parent_chain_name}", parent_chain_name)
            code = code.replace(
                "{rollup_address}",
                "0x0000000000000000000000000000000000000000",
            )
            code = code.replace(
                "{sequencer_inbox}",
                "0x0000000000000000000000000000000000000000",
            )
            code = code.replace("{addresses_array}", validators_str)
            files["scripts/manage-validators.ts"] = validate_template_output(
                code, "manage-validators"
            )

        # 5. Node config script
        node_template = get_orbit_template("node_config")
        if node_template:
            code = node_template.code
            code = code.replace("{chain_id}", str(chain_id))
            code = code.replace("{chain_name}", chain_name)
            code = code.replace("{parent_chain_id}", str(parent_chain_id))
            code = code.replace("{parent_chain_name}", parent_chain_name)
            # Set parentChainIsArbitrum based on parent chain type
            parent_is_arbitrum = parent_chain_id in (42161, 421614)
            code = code.replace(
                "{parent_chain_is_arbitrum}",
                "true" if parent_is_arbitrum else "false",
            )
            files["scripts/prepare-node-config.ts"] = validate_template_output(
                code, "prepare-node-config"
            )

        # 6. AnyTrust keyset config (if applicable)
        if is_anytrust:
            anytrust_template = get_orbit_template("anytrust_config")
            if anytrust_template:
                code = anytrust_template.code
                code = code.replace("{parent_chain_id}", str(parent_chain_id))
                code = code.replace("{parent_chain_name}", parent_chain_name)
                files["scripts/configure-anytrust.ts"] = validate_template_output(
                    code, "configure-anytrust"
                )

        # 6b. ERC-20 test token for custom gas token chains
        if native_token:
            files["contracts/TestToken.sol"] = self._generate_test_token_sol(
                chain_name
            )
            files["scripts/deploy-test-token.sh"] = (
                self._generate_deploy_token_sh()
            )

        # 6c. BLS key generation for AnyTrust
        if is_anytrust:
            files["scripts/generate-das-keys.sh"] = (
                self._generate_das_keys_script()
            )

        # 6d. Test chain health check
        files["scripts/test-chain.ts"] = self._generate_test_chain_script(
            chain_id, chain_name, parent_chain_id
        )

        # 6e. Governance management
        files["scripts/manage-governance.ts"] = (
            self._generate_governance_script(parent_chain_id, parent_chain_name)
        )

        # 7. Orchestration scaffold files
        orchestration_template = get_orbit_template("orchestration")
        if orchestration_template:
            for filename, content in orchestration_template.files.items():
                content = content.replace("{project_name}", chain_name)
                content = content.replace("{chain_id}", str(chain_id))
                content = content.replace("{chain_name}", chain_name)
                content = content.replace("{parent_chain_rpc}", parent_rpc)
                files[filename] = content

        # 8. Docker compose
        files["docker-compose.yml"] = generate_docker_compose(
            chain_name, chain_id, parent_chain_id, is_anytrust
        )

        # 9. README
        files["README.md"] = self._generate_readme(
            chain_name, chain_id, is_anytrust, native_token, parent_chain
        )

        # Build project structure description
        project_structure = {
            "scripts/": [
                "prepare-chain-config.ts",
                "deploy-rollup.ts",
                "deploy-token-bridge.ts",
                "manage-validators.ts",
                "prepare-node-config.ts",
                "test-chain.ts",
                "manage-governance.ts",
            ],
            "root": [
                "package.json",
                "tsconfig.json",
                ".env.example",
                "setup.sh",
                "deploy.sh",
                "docker-compose.yml",
                "README.md",
            ],
        }
        if native_token:
            project_structure["scripts/"].append("deploy-test-token.sh")
            project_structure["contracts/"] = ["TestToken.sol"]
        if is_anytrust:
            project_structure["scripts/"].append("configure-anytrust.ts")
            project_structure["scripts/"].append("generate-das-keys.sh")

        result = {
            "name": chain_name,
            "description": prompt,
            "files": files,
            "project_structure": project_structure,
            "dependencies": ORBIT_DEPENDENCIES,
            "chain_config": {
                "chain_id": chain_id,
                "chain_name": chain_name,
                "is_anytrust": is_anytrust,
                "native_token": native_token,
                "parent_chain": parent_chain,
                "parent_chain_id": parent_chain_id,
                "parent_rpc": parent_rpc,
            },
            "validators": validators,
            "batch_posters": batch_posters,
            "setup_instructions": [
                "1. Run: bash setup.sh",
                "2. Edit .env with DEPLOYER_PRIVATE_KEY"
                " (and optionally separate BATCH_POSTER/VALIDATOR keys)",
                *(
                    [
                        "3. Deploy or obtain your ERC-20 gas token"
                        " on the parent chain",
                        "4. Run: npx tsx scripts/approve-token.ts"
                        " (approve token for RollupCreator)",
                        "5. Run: npm run config:chain",
                        "6. Run: npm run deploy:rollup"
                        " (output saved to deployment.json)",
                        "7. Run: npm run config:node"
                        " (reads deployment.json)",
                        "8. Start Nitro node: docker-compose up -d",
                        "9. Run: npm run deploy:token-bridge"
                        " (reads deployment.json)",
                        "10. Run: npm run test:chain"
                        " (verify chain health)",
                    ]
                    if native_token
                    else [
                        "3. Run: npm run config:chain",
                        "4. Run: npm run deploy:rollup"
                        " (output saved to deployment.json)",
                        "5. Run: npm run config:node"
                        " (reads deployment.json)",
                        "6. Start Nitro node: docker-compose up -d",
                        "7. Run: npm run deploy:token-bridge"
                        " (reads deployment.json)",
                        "8. Run: npm run test:chain"
                        " (verify chain health)",
                    ]
                ),
            ],
            "development_workflow": self._generate_workflow(is_anytrust),
            "disclaimer": TEMPLATE_DISCLAIMER,
        }

        return result

    @staticmethod
    def _generate_test_chain_script(
        chain_id: int,
        chain_name: str,
        parent_chain_id: int,
    ) -> str:
        """Generate scripts/test-chain.ts — chain verification and health check."""
        code = (
            "import 'dotenv/config';\n"
            "import * as fs from 'fs';\n"
            "import {\n"
            "  createPublicClient,\n"
            "  createWalletClient,\n"
            "  http,\n"
            "  parseEther,\n"
            "  formatEther,\n"
            "  maxUint256,\n"
            "  Chain,\n"
            "} from 'viem';\n"
            "import { privateKeyToAccount } from 'viem/accounts';\n"
            "\n"
            "// ERC-20 ABI for custom gas token approval\n"
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
            "    name: 'balanceOf',\n"
            "    type: 'function',\n"
            "    stateMutability: 'view',\n"
            "    inputs: [{ name: 'account', type: 'address' }],\n"
            "    outputs: [{ name: '', type: 'uint256' }],\n"
            "  },\n"
            "] as const;\n"
            "\n"
            "// Inbox ABI for ERC-20 deposit (custom gas token chains)\n"
            "const inboxAbi = [\n"
            "  {\n"
            "    name: 'depositERC20',\n"
            "    type: 'function',\n"
            "    stateMutability: 'nonpayable',\n"
            "    inputs: [{ name: 'amount', type: 'uint256' }],\n"
            "    outputs: [],\n"
            "  },\n"
            "] as const;\n"
            "\n"
            "const orbitChain: Chain = {\n"
            "  id: CHAIN_ID_PLACEHOLDER,\n"
            "  name: 'CHAIN_NAME_PLACEHOLDER',\n"
            "  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },\n"
            "  rpcUrls: {\n"
            "    default: { http: [process.env.ORBIT_CHAIN_RPC ?? 'http://localhost:8449'] },\n"
            "  },\n"
            "};\n"
            "\n"
            "const parentChain: Chain = {\n"
            "  id: PARENT_CHAIN_ID_PLACEHOLDER,\n"
            "  name: 'Parent Chain',\n"
            "  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },\n"
            "  rpcUrls: {\n"
            "    default: { http: [process.env.PARENT_CHAIN_RPC!] },\n"
            "  },\n"
            "};\n"
            "\n"
            "/**\n"
            " * Test chain connectivity and basic operations.\n"
            " *\n"
            " * Checks:\n"
            " *   1. L3 RPC connectivity and chain ID\n"
            " *   2. Balances on both parent and orbit chain\n"
            " *   3. Test transfer on L3\n"
            " *   4. Simple contract deployment\n"
            " *   5. Deposit test (parent -> L3)\n"
            " */\n"
            "async function main() {\n"
            "  const account = privateKeyToAccount(\n"
            "    process.env.DEPLOYER_PRIVATE_KEY! as `0x${string}`\n"
            "  );\n"
            "\n"
            "  console.log('=== Orbit Chain Health Check ===');\n"
            "  console.log('Account:', account.address);\n"
            "\n"
            "  // 1. Test L3 RPC connectivity\n"
            "  console.log('\\n--- L3 RPC Connectivity ---');\n"
            "  const orbitClient = createPublicClient({\n"
            "    chain: orbitChain,\n"
            "    transport: http(process.env.ORBIT_CHAIN_RPC ?? 'http://localhost:8449'),\n"
            "  });\n"
            "\n"
            "  try {\n"
            "    const chainId = await orbitClient.getChainId();\n"
            "    console.log('  Chain ID:', chainId,"
            " chainId === CHAIN_ID_PLACEHOLDER"
            " ? '(correct)'"
            " : '(MISMATCH — expected CHAIN_ID_PLACEHOLDER)');\n"
            "\n"
            "    const blockNumber = await orbitClient.getBlockNumber();\n"
            "    console.log('  Latest block:', blockNumber.toString());\n"
            "  } catch (err) {\n"
            "    console.error('  FAILED: Cannot connect to L3 RPC');\n"
            "    console.error('  Error:', (err as Error).message);\n"
            "    console.error('  Is the Nitro node running? Try: docker-compose up -d');\n"
            "    process.exit(1);\n"
            "  }\n"
            "\n"
            "  // 2. Check balances\n"
            "  console.log('\\n--- Balances ---');\n"
            "  const parentClient = createPublicClient({\n"
            "    chain: parentChain,\n"
            "    transport: http(process.env.PARENT_CHAIN_RPC),\n"
            "  });\n"
            "\n"
            "  const parentBalance = await parentClient.getBalance({ address: account.address });\n"
            "  console.log('  Parent chain:', formatEther(parentBalance), 'ETH');\n"
            "\n"
            "  const orbitBalance = await orbitClient.getBalance({ address: account.address });\n"
            "  console.log('  Orbit chain: ', formatEther(orbitBalance), 'ETH/gas token');\n"
            "\n"
            "  // 3. Test transfer on L3 (if balance > 0)\n"
            "  console.log('\\n--- Test Transfer (L3) ---');\n"
            "  if (orbitBalance > 0n) {\n"
            "    const walletClient = createWalletClient({\n"
            "      account,\n"
            "      chain: orbitChain,\n"
            "      transport: http(process.env.ORBIT_CHAIN_RPC ?? 'http://localhost:8449'),\n"
            "    });\n"
            "\n"
            "    try {\n"
            "      const txHash = await walletClient.sendTransaction({\n"
            "        to: account.address,\n"
            "        value: 0n,\n"
            "      });\n"
            "      const receipt = await orbitClient.waitForTransactionReceipt({ hash: txHash });\n"
            "      console.log('  Self-transfer:',"
            " receipt.status === 'success'"
            " ? 'SUCCESS' : 'FAILED');\n"
            "      console.log('  Tx:', txHash);\n"
            "      console.log('  Gas used:', receipt.gasUsed.toString());\n"
            "    } catch (err) {\n"
            "      console.error('  FAILED:', (err as Error).message);\n"
            "    }\n"
            "  } else {\n"
            "    console.log('  Skipped — no balance on L3. Deposit funds first.');\n"
            "  }\n"
            "\n"
            "  // 4. Contract deployment test\n"
            "  console.log('\\n--- Contract Deployment Test ---');\n"
            "  if (orbitBalance > 0n) {\n"
            "    const walletClient = createWalletClient({\n"
            "      account,\n"
            "      chain: orbitChain,\n"
            "      transport: http(process.env.ORBIT_CHAIN_RPC ?? 'http://localhost:8449'),\n"
            "    });\n"
            "\n"
            "    try {\n"
            "      // Minimal contract: PUSH1 0x00 PUSH1 0x00 RETURN (returns empty)\n"
            "      const txHash = await walletClient.deployContract({\n"
            "        abi: [],\n"
            "        bytecode: '0x60006000f3',\n"
            "      });\n"
            "      const receipt = await orbitClient.waitForTransactionReceipt({ hash: txHash });\n"
            "      console.log('  Deploy:', receipt.status === 'success' ? 'SUCCESS' : 'FAILED');\n"
            "      console.log('  Contract:', receipt.contractAddress);\n"
            "    } catch (err) {\n"
            "      console.error('  FAILED:', (err as Error).message);\n"
            "    }\n"
            "  } else {\n"
            "    console.log('  Skipped — no balance on L3.');\n"
            "  }\n"
            "\n"
            "  // 5. Deposit test (parent chain -> L3)\n"
            "  console.log('\\n--- Deposit Test (Parent -> L3) ---');\n"
            "  if (fs.existsSync('deployment.json')) {\n"
            "    const deployment = JSON.parse(fs.readFileSync('deployment.json', 'utf-8'));\n"
            "    const inboxAddress = deployment.coreContracts?.inbox as `0x${string}`;\n"
            "\n"
            "    if (inboxAddress) {\n"
            "      const parentWalletClient = createWalletClient({\n"
            "        account,\n"
            "        chain: parentChain,\n"
            "        transport: http(process.env.PARENT_CHAIN_RPC),\n"
            "      });\n"
            "\n"
            "      if (deployment.nativeToken) {\n"
            "        // Custom gas token chain: approve Inbox, then depositERC20\n"
            "        const nativeToken = deployment.nativeToken as `0x${string}`;\n"
            "        console.log('  Custom gas token:', nativeToken);\n"
            "\n"
            "        const tokenBalance = await parentClient.readContract({\n"
            "          address: nativeToken,\n"
            "          abi: erc20Abi,\n"
            "          functionName: 'balanceOf',\n"
            "          args: [account.address],\n"
            "        });\n"
            "        const depositAmount = tokenBalance / 100n; // 1% of balance\n"
            "\n"
            "        if (depositAmount > 0n) {\n"
            "          try {\n"
            "            // Approve Inbox (NOT Bridge) for the token\n"
            "            console.log('  Approving Inbox for token spend...');\n"
            "            const approveHash = await parentWalletClient.writeContract({\n"
            "              address: nativeToken,\n"
            "              abi: erc20Abi,\n"
            "              functionName: 'approve',\n"
            "              args: [inboxAddress, maxUint256],\n"
            "            });\n"
            "            await parentClient.waitForTransactionReceipt({ hash: approveHash });\n"
            "\n"
            "            // Deposit via Inbox.depositERC20(amount)\n"
            "            console.log('  Depositing',"
            " depositAmount.toString(),"
            " 'tokens to L3 via Inbox...');\n"
            "            const depositHash ="
            " await parentWalletClient.writeContract({\n"
            "              address: inboxAddress,\n"
            "              abi: inboxAbi,\n"
            "              functionName: 'depositERC20',\n"
            "              args: [depositAmount],\n"
            "            });\n"
            "            const depositReceipt ="
            " await parentClient"
            ".waitForTransactionReceipt("
            "{ hash: depositHash });\n"
            "            console.log('  Deposit:',"
            " depositReceipt.status === 'success'"
            " ? 'SUCCESS' : 'FAILED');\n"
            "            console.log('  Tx:', depositHash);\n"
            "            console.log('  Note: L3 balance updates"
            " after ~15 min"
            " (retryable ticket processing)');\n"
            "          } catch (err) {\n"
            "            console.error('  FAILED:', (err as Error).message);\n"
            "          }\n"
            "        } else {\n"
            "          console.log('  Skipped — no token balance on parent chain');\n"
            "        }\n"
            "      } else {\n"
            "        // ETH chain: send ETH directly to the Inbox\n"
            "        const depositAmount = parseEther('0.001');\n"
            "        if (parentBalance >= depositAmount + parseEther('0.01')) {\n"
            "          try {\n"
            "            console.log('  Depositing 0.001 ETH to L3 via Inbox...');\n"
            "            const txHash = await parentWalletClient.sendTransaction({\n"
            "              to: inboxAddress,\n"
            "              value: depositAmount,\n"
            "            });\n"
            "            const receipt ="
            " await parentClient"
            ".waitForTransactionReceipt("
            "{ hash: txHash });\n"
            "            console.log('  Deposit:',"
            " receipt.status === 'success'"
            " ? 'SUCCESS' : 'FAILED');\n"
            "            console.log('  Tx:', txHash);\n"
            "            console.log('  Note: L3 balance"
            " updates after ~15 min"
            " (retryable ticket processing)');\n"
            "          } catch (err) {\n"
            "            console.error("
            "'  FAILED:', (err as Error).message);\n"
            "          }\n"
            "        } else {\n"
            "          console.log("
            "'  Skipped — insufficient parent chain"
            " balance (need 0.011 ETH)');\n"
            "        }\n"
            "      }\n"
            "    } else {\n"
            "      console.log('  Skipped — no Inbox address in deployment.json');\n"
            "    }\n"
            "  } else {\n"
            "    console.log('  Skipped — no deployment.json');\n"
            "  }\n"
            "\n"
            "  // 6. Load deployment info if available\n"
            "  if (fs.existsSync('deployment.json')) {\n"
            "    console.log('\\n--- Deployment Info ---');\n"
            "    const deployment = JSON.parse(fs.readFileSync('deployment.json', 'utf-8'));\n"
            "    console.log('  Rollup:', deployment.coreContracts?.rollup);\n"
            "    console.log('  Inbox:', deployment.coreContracts?.inbox);\n"
            "    console.log('  Bridge:', deployment.coreContracts?.bridge);\n"
            "    if (deployment.tokenBridgeContracts) {\n"
            "      console.log("
            "'  Token Bridge Router (parent):',"
            " deployment.tokenBridgeContracts"
            ".parentChain?.router);\n"
            "      console.log("
            "'  Token Bridge Router (orbit):',"
            " deployment.tokenBridgeContracts"
            ".orbitChain?.router);\n"
            "    }\n"
            "  }\n"
            "\n"
            "  console.log('\\n=== Health Check Complete ===');\n"
            "}\n"
            "\n"
            "main().catch(console.error);\n"
        )
        # Replace PARENT_ first — CHAIN_ID_PLACEHOLDER is a substring of PARENT_CHAIN_ID_PLACEHOLDER
        code = code.replace("PARENT_CHAIN_ID_PLACEHOLDER", str(parent_chain_id))
        code = code.replace("CHAIN_ID_PLACEHOLDER", str(chain_id))
        code = code.replace("CHAIN_NAME_PLACEHOLDER", chain_name)
        return code

    @staticmethod
    def _generate_governance_script(
        parent_chain_id: int,
        parent_chain_name: str,
    ) -> str:
        """Generate scripts/manage-governance.ts — governance operations."""
        code = (
            "import 'dotenv/config';\n"
            "import * as fs from 'fs';\n"
            "import {\n"
            "  createPublicClient,\n"
            "  createWalletClient,\n"
            "  http,\n"
            "  encodeFunctionData,\n"
            "  Chain,\n"
            "} from 'viem';\n"
            "import { privateKeyToAccount } from 'viem/accounts';\n"
            "\n"
            "// UpgradeExecutor ABI\n"
            "const upgradeExecutorAbi = [\n"
            "  {\n"
            "    name: 'executeCall',\n"
            "    type: 'function',\n"
            "    stateMutability: 'nonpayable',\n"
            "    inputs: [\n"
            "      { name: 'target', type: 'address' },\n"
            "      { name: 'data', type: 'bytes' },\n"
            "    ],\n"
            "    outputs: [],\n"
            "  },\n"
            "  {\n"
            "    name: 'hasRole',\n"
            "    type: 'function',\n"
            "    stateMutability: 'view',\n"
            "    inputs: [\n"
            "      { name: 'role', type: 'bytes32' },\n"
            "      { name: 'account', type: 'address' },\n"
            "    ],\n"
            "    outputs: [{ name: '', type: 'bool' }],\n"
            "  },\n"
            "  {\n"
            "    name: 'grantRole',\n"
            "    type: 'function',\n"
            "    stateMutability: 'nonpayable',\n"
            "    inputs: [\n"
            "      { name: 'role', type: 'bytes32' },\n"
            "      { name: 'account', type: 'address' },\n"
            "    ],\n"
            "    outputs: [],\n"
            "  },\n"
            "  {\n"
            "    name: 'revokeRole',\n"
            "    type: 'function',\n"
            "    stateMutability: 'nonpayable',\n"
            "    inputs: [\n"
            "      { name: 'role', type: 'bytes32' },\n"
            "      { name: 'account', type: 'address' },\n"
            "    ],\n"
            "    outputs: [],\n"
            "  },\n"
            "] as const;\n"
            "\n"
            "const EXECUTOR_ROLE ="
            " '0xd8aa0f3194971a2a116679f7c2090f6939c8d4"
            "e01a2a8d7e41d55e5351469e63'"
            " as `0x${string}`;\n"
            "const ADMIN_ROLE ="
            " '0xa49807205ce4d355092ef5a8a18f56e8913cf4a"
            "201fbe287825b095693c21775'"
            " as `0x${string}`;\n"
            "\n"
            "const parentChain: Chain = {\n"
            "  id: PARENT_CHAIN_ID_PLACEHOLDER,\n"
            "  name: 'PARENT_CHAIN_NAME_PLACEHOLDER',\n"
            "  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },\n"
            "  rpcUrls: {\n"
            "    default: { http: [process.env.PARENT_CHAIN_RPC!] },\n"
            "  },\n"
            "};\n"
            "\n"
            "/**\n"
            " * Manage governance roles on the UpgradeExecutor.\n"
            " *\n"
            " * Usage:\n"
            " *   npx tsx scripts/manage-governance.ts status\n"
            " *   npx tsx scripts/manage-governance.ts grant <address>\n"
            " *   npx tsx scripts/manage-governance.ts revoke <address>\n"
            " */\n"
            "async function main() {\n"
            "  const command = process.argv[2] ?? 'status';\n"
            "  const targetAddress = process.argv[3] as `0x${string}` | undefined;\n"
            "\n"
            "  const account = privateKeyToAccount(\n"
            "    process.env.DEPLOYER_PRIVATE_KEY! as `0x${string}`\n"
            "  );\n"
            "\n"
            "  // Read UpgradeExecutor from deployment.json\n"
            "  if (!fs.existsSync('deployment.json')) {\n"
            "    console.error('Error: deployment.json not found. Run deploy-rollup.ts first.');\n"
            "    process.exit(1);\n"
            "  }\n"
            "  const deployment = JSON.parse(fs.readFileSync('deployment.json', 'utf-8'));\n"
            "  const upgradeExecutor = deployment.coreContracts.upgradeExecutor as `0x${string}`;\n"
            "\n"
            "  const publicClient = createPublicClient({\n"
            "    chain: parentChain,\n"
            "    transport: http(process.env.PARENT_CHAIN_RPC),\n"
            "  });\n"
            "\n"
            "  const walletClient = createWalletClient({\n"
            "    account,\n"
            "    chain: parentChain,\n"
            "    transport: http(process.env.PARENT_CHAIN_RPC),\n"
            "  });\n"
            "\n"
            "  console.log('=== Governance Management ===');\n"
            "  console.log('UpgradeExecutor:', upgradeExecutor);\n"
            "  console.log('Caller:', account.address);\n"
            "\n"
            "  if (command === 'status') {\n"
            "    // Check roles for the caller and optionally a target\n"
            "    const addresses = [account.address];\n"
            "    if (targetAddress) addresses.push(targetAddress);\n"
            "\n"
            "    for (const addr of addresses) {\n"
            "      const hasExecutor = await publicClient.readContract({\n"
            "        address: upgradeExecutor,\n"
            "        abi: upgradeExecutorAbi,\n"
            "        functionName: 'hasRole',\n"
            "        args: [EXECUTOR_ROLE, addr],\n"
            "      });\n"
            "      const hasAdmin = await publicClient.readContract({\n"
            "        address: upgradeExecutor,\n"
            "        abi: upgradeExecutorAbi,\n"
            "        functionName: 'hasRole',\n"
            "        args: [ADMIN_ROLE, addr],\n"
            "      });\n"
            "      console.log(`\\n  ${addr}:`);\n"
            "      console.log(`    EXECUTOR_ROLE: ${hasExecutor}`);\n"
            "      console.log(`    ADMIN_ROLE:    ${hasAdmin}`);\n"
            "    }\n"
            "  } else if (command === 'grant' && targetAddress) {\n"
            "    console.log('\\nGranting EXECUTOR_ROLE to:', targetAddress);\n"
            "    // Grant must go through executeCall if caller has EXECUTOR_ROLE\n"
            "    const grantCalldata = encodeFunctionData({\n"
            "      abi: upgradeExecutorAbi,\n"
            "      functionName: 'grantRole',\n"
            "      args: [EXECUTOR_ROLE, targetAddress],\n"
            "    });\n"
            "    const txHash = await walletClient.writeContract({\n"
            "      address: upgradeExecutor,\n"
            "      abi: upgradeExecutorAbi,\n"
            "      functionName: 'executeCall',\n"
            "      args: [upgradeExecutor, grantCalldata],\n"
            "    });\n"
            "    const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });\n"
            "    console.log('  Tx:', receipt.transactionHash, '- Status:', receipt.status);\n"
            "  } else if (command === 'revoke' && targetAddress) {\n"
            "    console.log('\\nRevoking EXECUTOR_ROLE from:', targetAddress);\n"
            "    const revokeCalldata = encodeFunctionData({\n"
            "      abi: upgradeExecutorAbi,\n"
            "      functionName: 'revokeRole',\n"
            "      args: [EXECUTOR_ROLE, targetAddress],\n"
            "    });\n"
            "    const txHash = await walletClient.writeContract({\n"
            "      address: upgradeExecutor,\n"
            "      abi: upgradeExecutorAbi,\n"
            "      functionName: 'executeCall',\n"
            "      args: [upgradeExecutor, revokeCalldata],\n"
            "    });\n"
            "    const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });\n"
            "    console.log('  Tx:', receipt.transactionHash, '- Status:', receipt.status);\n"
            "  } else {\n"
            "    console.log('\\nUsage:');\n"
            "    console.log('  npx tsx scripts/manage-governance.ts status [address]');\n"
            "    console.log('  npx tsx scripts/manage-governance.ts grant <address>');\n"
            "    console.log('  npx tsx scripts/manage-governance.ts revoke <address>');\n"
            "  }\n"
            "}\n"
            "\n"
            "main().catch(console.error);\n"
        )
        code = code.replace(
            "PARENT_CHAIN_ID_PLACEHOLDER", str(parent_chain_id)
        )
        code = code.replace(
            "PARENT_CHAIN_NAME_PLACEHOLDER", parent_chain_name
        )
        return code

    @staticmethod
    def _generate_das_keys_script() -> str:
        """Generate scripts/generate-das-keys.sh — BLS key generation for AnyTrust."""
        nitro_image = "offchainlabs/nitro-node:v3.9.4-7f582c3"
        return (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "\n"
            'echo "=== Generate DAS BLS Keys ==="\n'
            "\n"
            "# Create output directory\n"
            "mkdir -p das-keys\n"
            "\n"
            "# Generate BLS key pair using the datool from the Nitro image\n"
            "docker run --rm \\\n"
            "  --entrypoint /usr/local/bin/datool \\\n"
            '  -v "$(pwd)/das-keys:/keys" \\\n'
            f"  {nitro_image} \\\n"
            "  keygen --dir /keys\n"
            "\n"
            'echo ""\n'
            'echo "BLS keys generated in das-keys/"\n'
            'echo "  das_bls      — private key (keep secret!)"\n'
            'echo "  das_bls.pub  — public key (used for keyset registration)"\n'
            'echo ""\n'
            'echo "Next steps:"\n'
            'echo "  1. Start DAS + Nitro node: docker-compose up -d"\n'
            'echo "  2. Register keyset: npm run configure:anytrust"\n'
        )

    @staticmethod
    def _generate_test_token_sol(chain_name: str) -> str:
        """Generate contracts/TestToken.sol — test ERC20 for custom gas token."""
        # Convert chain-name to PascalCase token name
        token_name = "".join(
            word.capitalize() for word in chain_name.split("-")
        )
        symbol = token_name[:4].upper()
        return (
            "// SPDX-License-Identifier: MIT\n"
            "pragma solidity ^0.8.20;\n"
            "\n"
            'import "@openzeppelin/contracts/token/ERC20/ERC20.sol";\n'
            "\n"
            "/**\n"
            " * Minimal ERC-20 for testing as a custom gas token"
            " on an Orbit chain.\n"
            " *\n"
            " * Deploy with Foundry:\n"
            f" *   forge create contracts/TestToken.sol:{token_name}Token \\\\\n"
            " *     --rpc-url $PARENT_CHAIN_RPC \\\\\n"
            " *     --private-key $DEPLOYER_PRIVATE_KEY \\\\\n"
            ' *     --constructor-args "$(cast address $DEPLOYER_PRIVATE_KEY)"\n'
            " *\n"
            " * Or use the deploy script:\n"
            " *   bash scripts/deploy-test-token.sh\n"
            " */\n"
            f"contract {token_name}Token is ERC20 {{\n"
            f'    constructor(address initialHolder) ERC20("{token_name}'
            f' Gas Token", "{symbol}") {{\n'
            "        // Mint 1 billion tokens to the deployer for testing\n"
            "        _mint(initialHolder, 1_000_000_000 * 10 ** decimals());\n"
            "    }\n"
            "}\n"
        )

    @staticmethod
    def _generate_deploy_token_sh() -> str:
        """Generate scripts/deploy-test-token.sh — deploy test ERC20 token."""
        return (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "\n"
            "# Load environment variables\n"
            "if [ -f .env ]; then\n"
            "  set -a\n"
            "  source .env\n"
            "  set +a\n"
            "fi\n"
            "\n"
            'echo "=== Deploy Test ERC-20 Gas Token ==="\n'
            "\n"
            "# Check for Foundry\n"
            "if ! command -v forge &> /dev/null; then\n"
            '  echo "Error: Foundry not installed."\n'
            '  echo "Install: curl -L https://foundry.paradigm.xyz'
            ' | bash && foundryup"\n'
            "  exit 1\n"
            "fi\n"
            "\n"
            "# Install OpenZeppelin (if not already)\n"
            'if [ ! -d "lib/openzeppelin-contracts" ]; then\n'
            '  echo "Installing OpenZeppelin contracts..."\n'
            "  forge install OpenZeppelin/openzeppelin-contracts"
            " --no-commit\n"
            "fi\n"
            "\n"
            "# Get deployer address from private key\n"
            'DEPLOYER_ADDRESS=$(cast wallet address "$DEPLOYER_PRIVATE_KEY")\n'
            "\n"
            'echo "Deploying test token..."\n'
            'echo "  Deployer: $DEPLOYER_ADDRESS"\n'
            'echo "  RPC: $PARENT_CHAIN_RPC"\n'
            "\n"
            "# Deploy\n"
            "DEPLOY_OUTPUT=$(forge create contracts/TestToken.sol:*Token \\\\\n"
            '  --rpc-url "$PARENT_CHAIN_RPC" \\\\\n'
            '  --private-key "$DEPLOYER_PRIVATE_KEY" \\\\\n'
            '  --constructor-args "$DEPLOYER_ADDRESS" \\\\\n'
            "  --json)\n"
            "\n"
            "TOKEN_ADDRESS=$(echo \"$DEPLOY_OUTPUT\" | jq -r '.deployedTo')\n"
            "\n"
            'echo ""\n'
            'echo "Token deployed!"\n'
            'echo "  Address: $TOKEN_ADDRESS"\n'
            'echo ""\n'
            'echo "Add to your .env:"\n'
            'echo "  NATIVE_TOKEN=$TOKEN_ADDRESS"\n'
            'echo ""\n'
            'echo "Next steps:"\n'
            'echo "  1. Set NATIVE_TOKEN=$TOKEN_ADDRESS in .env"\n'
            'echo "  2. Run: npx tsx scripts/approve-token.ts"\n'
            'echo "  3. Run: npm run deploy:rollup"\n'
        )

    @staticmethod
    def _format_address_array(addresses: list[str]) -> str:
        """Format a list of addresses as a TypeScript array literal."""
        if not addresses:
            return "[account.address] as `0x${string}`[]"
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
    def _generate_readme(
        chain_name: str,
        chain_id: int,
        is_anytrust: bool,
        native_token: str | None,
        parent_chain: str,
    ) -> str:
        """Generate README.md for the project."""
        chain_type = "AnyTrust" if is_anytrust else "Rollup"
        gas_token = f"Custom ({native_token})" if native_token else "ETH"

        return f"""# {chain_name.replace('-', ' ').title()}

> Orbit {chain_type} chain deployment project

## Configuration

| Parameter | Value |
|-----------|-------|
| Chain ID | {chain_id} |
| Chain Type | {chain_type} |
| Gas Token | {gas_token} |
| Parent Chain | {parent_chain} |

## Quick Start

```bash
# 1. Install dependencies
bash setup.sh

# 2. Configure environment
# Edit .env with your DEPLOYER_PRIVATE_KEY and other settings

# 3. Deploy everything
bash deploy.sh
```

## Step-by-Step Deployment

```bash
# 1. Prepare chain configuration
npm run config:chain

# 2. Deploy rollup contracts
npm run deploy:rollup

# 3. Start your Nitro node (see docs)
# Use the contract addresses from step 2

# 4. Deploy token bridge
npm run deploy:token-bridge

# 5. Generate node configuration
npm run config:node

# 6. Manage validators
npm run manage:validators
```

## Project Structure

```
{chain_name}/
  scripts/
    prepare-chain-config.ts   # Chain configuration
    deploy-rollup.ts          # Rollup contract deployment
    deploy-token-bridge.ts    # Token bridge deployment
    manage-validators.ts      # Validator/batch poster management
    prepare-node-config.ts    # Nitro node configuration
  package.json
  tsconfig.json
  .env.example
  setup.sh
  deploy.sh
```

## References

- [Orbit Chain Documentation](https://docs.arbitrum.io/launch-orbit-chain/orbit-gentle-introduction)
- [Orbit SDK Reference](https://github.com/OffchainLabs/arbitrum-orbit-sdk)
- [Nitro Node Setup](https://docs.arbitrum.io/run-arbitrum-node/run-full-node)

---
Built with [ARBuilder](https://github.com/arbbuilder)
"""

    @staticmethod
    def _generate_workflow(is_anytrust: bool) -> dict:
        """Generate development workflow guide."""
        steps = [
            {
                "step": 1,
                "component": "Chain Configuration",
                "actions": [
                    "Run setup.sh to install dependencies",
                    "Edit .env with deployer key and parent chain RPC",
                    "Run npm run config:chain to prepare configuration",
                ],
            },
            {
                "step": 2,
                "component": "Rollup Deployment",
                "actions": [
                    "Run npm run deploy:rollup",
                    "Save all contract addresses from output",
                    "Fund the rollup contracts if needed",
                ],
            },
            {
                "step": 3,
                "component": "Node Setup",
                "actions": [
                    "Run npm run config:node to generate nodeConfig.json (reads deployment.json)",
                    "Start Nitro node: docker-compose up -d",
                    "Verify node is syncing with parent chain",
                ],
            },
            {
                "step": 4,
                "component": "Token Bridge",
                "actions": [
                    "Update ORBIT_CHAIN_RPC in .env",
                    "Run npm run deploy:token-bridge",
                    "Verify bridge contracts on both chains",
                ],
            },
        ]

        if is_anytrust:
            steps.append({
                "step": 5,
                "component": "AnyTrust DAC Setup",
                "actions": [
                    "Generate BLS keys: docker run --rm"
                    " -v $(pwd)/das-keys:/keys"
                    " offchainlabs/nitro-node:v3.9.4-7f582c3"
                    " datool keygen --dir /keys",
                    "Configure DAC member BLS keys in the keyset script",
                    "Run npm run configure:anytrust",
                    "Verify keyset is active on SequencerInbox",
                ],
            })

        return {
            "steps": steps,
            "tips": [
                "Deploy to testnet (Arbitrum Sepolia) before mainnet",
                "Ensure deployer has sufficient ETH on parent chain",
                "Save all deployment output — contract addresses are needed for node config",
                "Use a multi-sig for chain owner in production",
                "Monitor validator and batch poster uptime",
            ],
        }

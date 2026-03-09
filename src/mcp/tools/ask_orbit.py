"""
Q&A tool for Orbit chain deployment and management questions.

Uses a curated knowledge base and optional LLM for accurate answers
about Orbit chain configuration, deployment, and operations.
"""

from typing import Any  # noqa: I001

from .base import BaseTool


# Pre-built knowledge base for common Orbit chain questions
ORBIT_KNOWLEDGE = {
    "chain_config": {
        "description": "Chain configuration for Orbit chains",
        "function": "prepareChainConfig()",
        "key_params": [
            "chainId — unique chain ID for the Orbit chain",
            "InitialChainOwner — address that controls chain admin operations",
            "DataAvailabilityCommittee — true for AnyTrust, false for Rollup",
        ],
        "notes": [
            "Chain config is passed to createRollup() during deployment",
            "The chain owner can modify chain parameters via UpgradeExecutor",
            "Chain ID must not conflict with existing chains",
        ],
    },
    "deployment": {
        "description": "Deploying Orbit chain rollup contracts",
        "function": "createRollup()",
        "steps": [
            "1. Prepare chain config with prepareChainConfig()",
            "2. Configure validators and batch posters",
            "3. Call createRollup() with deployment params",
            "4. Save output contract addresses (rollup, inbox, outbox, bridge, etc.)",
            "5. Start the Nitro node with the deployed contract addresses",
            "6. Deploy token bridge with createTokenBridge()",
        ],
        "requirements": [
            "Sufficient ETH on parent chain for gas",
            "At least one validator address",
            "At least one batch poster address",
            "Parent chain RPC endpoint",
        ],
    },
    "validators": {
        "description": "Validator and batch poster management",
        "validators": {
            "role": "Confirm state assertions on the parent chain",
            "minimum": "At least 1 validator required",
            "management": "Add/remove via UpgradeExecutor with EXECUTOR_ROLE",
        },
        "batch_posters": {
            "role": "Submit transaction batches to the SequencerInbox",
            "minimum": "At least 1 batch poster required",
            "management": "Managed via SequencerInbox contract",
        },
    },
    "gas_tokens": {
        "description": "Custom gas token configuration for Orbit chains",
        "mechanism": [
            "Orbit chains can use any ERC20 as the native gas token",
            "The token must be deployed on the parent chain",
            "Token approval is required before createRollup()",
            "Users pay gas in the custom token instead of ETH",
        ],
        "setup": [
            "1. Deploy (or use existing) ERC20 on parent chain (Foundry: forge create, Hardhat: npx hardhat run)",
            "2. Approve the RollupCreator to spend the token (use maxUint256 for convenience)",
            "3. Pass nativeToken address to createRollup()",
            "RollupCreator addresses (v3.1): Arb Sepolia 0x5F45...16cF, Arb One 0xB90e...eB8b, Eth Mainnet 0x4369...AB44",
        ],
        "considerations": [
            "Token must have standard ERC20 interface",
            "Token decimals affect gas pricing",
            "Bridging requires token approval flow",
        ],
    },
    "anytrust": {
        "description": "AnyTrust Data Availability Committee (DAC) chains",
        "mechanism": [
            "AnyTrust stores data with a DAC instead of on-chain",
            "Cheaper than Rollup mode but requires DAC trust assumption",
            "At least 2-of-N DAC members must be honest",
        ],
        "keyset": [
            "DAC members have BLS public keys (generated via datool keygen) — BLS keys are BN254 (289 bytes), NOT BLS-12-381 (48 bytes)",
            "Generate BLS keys: docker run --rm --entrypoint /usr/local/bin/datool -v $(pwd)/das-keys:/keys offchainlabs/nitro-node:v3.9.4-7f582c3 keygen --dir /keys",
            "das_bls.pub is base64-encoded — pass base64 strings directly to the SDK (it decodes internally)",
            "prepareKeyset() takes POSITIONAL args: prepareKeyset([base64Str], assumedHonest) — NOT an object like prepareKeyset({ publicKeys, assumedHonest })",
            "setValidKeyset({ coreContracts, keyset, publicClient, walletClient }) — returns TransactionReceipt directly",
            "setValidKeyset() handles UpgradeExecutor routing automatically",
            "WRONG: prepareKeyset({ assumedHonest, publicKeys }) — this is NOT the SDK API",
            "Read BLS key file with fs.readFileSync(path, 'utf-8') — ASCII hyphen, NOT unicode dash",
            "Verify registration: sequencerInbox.isValidKeysetHash(keccak256(keyset)) should return true",
            "Keyset binary format: [uint64 assumedHonest BE][uint64 numMembers BE][uint16 keyLen BE][keyBytes]... — do NOT encode manually, use SDK",
        ],
        "das_server": [
            "DAS runs from the same nitro-node image with entrypoint /usr/local/bin/daserver",
            "Required flags: --data-availability.parent-chain-node-url, --data-availability.sequencer-inbox-address, --data-availability.key.key-dir",
            "In Docker Compose, use service names for inter-container URLs (das-server:9877, not localhost:9877)",
            "DAS must be running and accessible BEFORE the Nitro node starts batch posting",
        ],
        "vs_rollup": {
            "Rollup": "All data posted on-chain (full Ethereum security)",
            "AnyTrust": "Data stored by DAC (cheaper, N/2+1 trust assumption)",
        },
    },
    "node_setup": {
        "description": "Setting up a Nitro node for an Orbit chain",
        "function": "prepareNodeConfig()",
        "components": [
            "Nitro node — executes transactions and produces blocks",
            "Validator node — posts assertions to parent chain",
            "Batch poster — submits transaction batches",
            "DAS server (AnyTrust only) — runs from same nitro-node image with daserver entrypoint",
        ],
        "config_params": [
            "chainConfig — JSON from prepareChainConfig()",
            "coreContracts — addresses from createRollup() output",
            "batchPosterPrivateKey — raw hex WITHOUT 0x prefix",
            "validatorPrivateKey — raw hex WITHOUT 0x prefix",
            "stakeToken — zeroAddress for ETH",
            "parentChainId — parent chain ID",
            "parentChainIsArbitrum — true if parent is Arbitrum L2",
            "parentChainRpcUrl — parent chain RPC endpoint",
            "dasServerUrl — DAS endpoint (AnyTrust only)",
        ],
        "docker": {
            "image": "offchainlabs/nitro-node:v3.9.4-7f582c3 (pinned stable)",
            "das": "DAS uses same image with entrypoint /usr/local/bin/daserver (NOT offchainlabs/das)",
            "testnet_flag": "For single-node testnet: --node.dangerous.no-sequencer-coordinator",
            "permissions": "Do NOT use 'user: root' — use bind mounts (./data/arbitrum:/home/user/.arbitrum) with mkdir -p data/arbitrum",
            "no_dev_init": "Do NOT use --init.dev-init — that flag is for local devnodes only, not Orbit chains",
            "wasm_roots": "Add --validation.wasm.allowed-wasm-module-roots=/home/user/nitro-legacy/machines,/home/user/target/machines",
        },
    },
    "node_troubleshooting": {
        "description": "Common issues and fixes when spinning up a Nitro devnode for an Orbit chain",
        "startup_issues": [
            "Node exits immediately — check docker logs: usually missing or malformed nodeConfig.json",
            "no sequencer coordinator error — add --node.dangerous.no-sequencer-coordinator for single-node testnet",
            "Permission denied on volumes — use bind mounts (./data/arbitrum:/home/user/.arbitrum) with mkdir -p data/arbitrum; do NOT use 'user: root'",
            "Node can't connect to parent chain — verify PARENT_CHAIN_RPC is reachable from inside the container",
            "deployed-at block 0 causes full rescan — ensure deployedAtBlock in deployment.json matches actual rollup deployment block",
            "DAS server fails — use same nitro-node image with entrypoint /usr/local/bin/daserver, NOT offchainlabs/das",
            "checkEmptyDatabaseDir crash-loop — add --validation.wasm.allowed-wasm-module-roots=/home/user/nitro-legacy/machines,/home/user/target/machines",
            "Staker and batch poster same address error (Nitro v3.9+) — use separate keys, or disable staker: node.staker.enable=false",
            "DAS URL double-port (http://host:9877:9877) — prepareNodeConfig() may produce malformed URLs; post-process to fix",
            "Do NOT use --init.dev-init — creates devnode test accounts, not for Orbit chain deployment",
        ],
        "config_issues": [
            "Wrong chainConfig format — must be exact JSON from prepareChainConfig(), not a subset",
            "Private keys masked as '...' — prepareNodeConfig() masks them for security; post-process to restore actual keys",
            "Private keys must NOT have 0x prefix in nodeConfig — Nitro expects raw hex",
            "Placeholder env vars (BATCH_POSTER_PRIVATE_KEY=0x...) override DEPLOYER_PRIVATE_KEY fallback — comment them out if not using separate keys",
            "parentChainIsArbitrum must be true if parent is Arbitrum One (42161) or Sepolia (421614)",
            "stakeToken should be zeroAddress for ETH-staked chains",
            "Missing coreContracts — nodeConfig needs ALL addresses from createRollup output",
        ],
        "docker_tips": [
            "Use pinned image: offchainlabs/nitro-node:v3.9.4-7f582c3 (not :latest)",
            "Mount nodeConfig.json as read-only: ./nodeConfig.json:/config/nodeConfig.json:ro",
            "Use bind mounts, not named volumes: ./data/arbitrum:/home/user/.arbitrum",
            "Check node health: curl -s http://localhost:8449 -X POST -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"eth_chainId\",\"params\":[],\"id\":1}'",
            "View logs: docker logs -f <container-name>",
            "For AnyTrust: DAS must be running and accessible BEFORE the node starts batch posting",
            "Common ports: 8449 (RPC), 8548 (WS), 9642 (metrics), 9877 (DAS REST)",
        ],
        "networking": [
            "If both parent chain and Orbit node are in Docker, use Docker network (not localhost)",
            "Rate limits on public RPCs can cause node sync failures — use a dedicated RPC provider for production",
            "WebSocket endpoint needed for real-time parent chain event monitoring in production",
        ],
    },
    "governance": {
        "description": "Governance and admin operations via UpgradeExecutor",
        "roles": [
            "EXECUTOR_ROLE — can execute arbitrary calls through UpgradeExecutor",
            "ADMIN_ROLE — can manage roles on the UpgradeExecutor",
        ],
        "operations": [
            "Add/remove validators",
            "Update chain parameters",
            "Upgrade contract implementations",
            "Manage batch posters",
            "Update DAC keyset (AnyTrust)",
        ],
        "api": [
            "UpgradeExecutor has both execute() and executeCall() — both exist in the contract, neither is deprecated",
            "The SDK uses executeCall(target, data) — prefer this for consistency",
            "Do NOT claim execute() was renamed or is deprecated — both have always existed",
        ],
        "security": [
            "UpgradeExecutor is the admin proxy for all chain contracts",
            "Multi-sig recommended for production chains",
            "Role assignments should be carefully managed",
        ],
    },
    "code_standards": {
        "description": "Code standards for Orbit chain tooling",
        "libraries": [
            "Use viem (^1.20.0) for all blockchain interactions — NOT ethers.js",
            "Use @arbitrum/chain-sdk (^0.25.0, renamed from @arbitrum/orbit-sdk) for Orbit-specific operations",
            "Use dotenv/config for environment variable loading",
            "TypeScript with ESNext modules",
        ],
        "patterns": [
            "Read contract addresses from deployment.json (created by deploy-rollup.ts)",
            "Save all deployment outputs to deployment.json for downstream scripts",
            "Use viem's createPublicClient/createWalletClient, NOT ethers.Provider",
            "Use encodeFunctionData() for building calldata, NOT ethers.utils.defaultAbiCoder",
            "Access-controlled operations route through UpgradeExecutor.executeCall(target, calldata)",
            "Private keys: strip 0x prefix for Nitro nodeConfig (Nitro expects raw hex)",
            "DAC keyset: use prepareKeyset([base64String], N) + setValidKeyset({ coreContracts, keyset, publicClient, walletClient }) from @arbitrum/chain-sdk — do NOT encode keyset bytes manually",
        ],
    },
    "token_bridge": {
        "description": "Token bridge deployment for Orbit chains",
        "function": "createTokenBridge()",
        "components": [
            "GatewayRouter — routes token bridging to correct gateway",
            "StandardGateway — handles standard ERC20 bridging",
            "CustomGateway — for tokens with custom bridging logic",
        ],
        "prerequisites": [
            "Rollup contracts must be deployed first",
            "Orbit chain node must be running",
            "Both parent and orbit chain RPCs must be accessible",
        ],
        "process": [
            "1. Deploy rollup (createRollup)",
            "2. Start Orbit chain node",
            "3. Deploy token bridge (createTokenBridge)",
            "4. Verify bridge contracts on both chains",
        ],
    },
}


class AskOrbitTool(BaseTool):
    """Answer questions about Orbit chain deployment and management."""

    name = "ask_orbit"
    description = """Answer questions about Arbitrum Orbit chain deployment and management.

Topics covered:
- Chain configuration (prepareChainConfig, Rollup vs AnyTrust)
- Rollup deployment (createRollup, validators, batch posters)
- Token bridge deployment (createTokenBridge)
- Custom gas tokens (ERC20 native tokens)
- AnyTrust DAC configuration (keysets, committees)
- Node setup (prepareNodeConfig, Nitro nodes)
- Governance (UpgradeExecutor, roles, admin operations)

Uses curated knowledge base and optional LLM for detailed answers."""

    input_schema = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "Question about Orbit chain deployment or management",
            },
            "question_type": {
                "type": "string",
                "enum": [
                    "general",
                    "deployment",
                    "config",
                    "validator",
                    "troubleshooting",
                ],
                "description": "Type of question for optimized response",
                "default": "general",
            },
        },
        "required": ["question"],
    }

    def __init__(self, context_tool=None, llm_client=None):
        """Initialize with optional context tool and LLM client."""
        self.context_tool = context_tool
        self.llm_client = llm_client

    def execute(self, **kwargs) -> dict[str, Any]:
        """Answer an Orbit chain question."""
        question = kwargs.get("question", "").strip()
        _question_type = kwargs.get("question_type", "general")  # reserved for future use

        if not question:
            return {"error": "Question is required and cannot be empty"}

        q_lower = question.lower()

        # Match against knowledge base topics
        answer_parts = []
        relevant_topics = []

        # Chain config questions
        if any(kw in q_lower for kw in [
            "chain config", "prepare config", "configure chain",
            "chain id", "chain owner", "chainconfig",
        ]):
            relevant_topics.append("chain_config")

        # Deployment questions
        if any(kw in q_lower for kw in [
            "deploy", "create rollup", "launch", "setup chain",
            "deployment", "createrollup",
        ]):
            relevant_topics.append("deployment")

        # Validator questions
        if any(kw in q_lower for kw in [
            "validator", "batch poster", "sequencer", "assertion",
        ]):
            relevant_topics.append("validators")

        # Gas token questions
        if any(kw in q_lower for kw in [
            "gas token", "native token", "custom token", "erc20 gas",
            "custom gas",
        ]):
            relevant_topics.append("gas_tokens")

        # AnyTrust questions
        if any(kw in q_lower for kw in [
            "anytrust", "dac", "keyset", "data availability",
            "committee", "any trust",
        ]):
            relevant_topics.append("anytrust")

        # Node setup questions
        if any(kw in q_lower for kw in [
            "node", "nitro", "node config", "run node", "start node",
            "devnode", "docker",
        ]):
            relevant_topics.append("node_setup")

        # Node troubleshooting questions
        if any(kw in q_lower for kw in [
            "error", "fail", "not working", "troubleshoot",
            "can't start", "won't start", "permission denied", "crash",
        ]) or ("node" in q_lower and any(kw in q_lower for kw in [
            "issue", "problem", "fix",
        ])):
            relevant_topics.append("node_troubleshooting")

        # Governance questions
        if any(kw in q_lower for kw in [
            "governance", "upgrade", "executor", "admin", "role",
            "permission",
        ]):
            relevant_topics.append("governance")

        # Code standards questions (include when question involves code examples)
        if any(kw in q_lower for kw in [
            "code", "script", "example", "how to",
            "register", "keyset", "deploy",
        ]):
            relevant_topics.append("code_standards")

        # Token bridge questions
        if any(kw in q_lower for kw in [
            "token bridge", "bridge", "gateway", "create bridge",
            "createtokenbridge",
        ]):
            relevant_topics.append("token_bridge")

        # Build answer from matched topics
        if relevant_topics:
            for topic in dict.fromkeys(relevant_topics):  # preserve order, deduplicate
                if topic in ORBIT_KNOWLEDGE:
                    info = ORBIT_KNOWLEDGE[topic]
                    answer_parts.append(
                        f"## {topic.replace('_', ' ').title()}"
                    )
                    for key, value in info.items():
                        if isinstance(value, list):
                            answer_parts.append(
                                f"**{key.replace('_', ' ').title()}:**"
                            )
                            for item in value:
                                answer_parts.append(f"  - {item}")
                        elif isinstance(value, dict):
                            answer_parts.append(
                                f"**{key.replace('_', ' ').title()}:**"
                            )
                            for sub_key, sub_value in value.items():
                                answer_parts.append(
                                    f"  - **{sub_key}:** {sub_value}"
                                )
                        else:
                            answer_parts.append(
                                f"**{key.replace('_', ' ').title()}:** {value}"
                            )
                    answer_parts.append("")

        # Try RAG context if available
        rag_context = ""
        if self.context_tool:
            try:
                ctx_result = self.context_tool.execute(
                    query=question,
                    n_results=3,
                    rerank=True,
                    category_boosts={
                        "orbit_sdk": 1.5,
                        "arbitrum_docs": 1.3,
                        "arbitrum_sdk": 1.0,
                        "stylus": 0.5,
                    },
                )
                if ctx_result.get("contexts"):
                    rag_context = "\n\n".join(
                        c.get("content", "")
                        for c in ctx_result["contexts"][:2]
                    )
            except Exception:
                pass  # RAG is optional

        # Build final answer
        if answer_parts:
            answer = "\n".join(answer_parts)
        else:
            answer = self._get_generic_answer(question)

        result = {
            "answer": answer,
            "topics": list(dict.fromkeys(relevant_topics)) if relevant_topics else ["general"],
            "references": self._get_references(relevant_topics),
        }

        if rag_context:
            result["additional_context"] = rag_context[:1000]

        return result

    def _get_generic_answer(self, question: str) -> str:
        """Get a generic answer for unmatched questions."""
        return """## Arbitrum Orbit Chain Overview

Orbit chains are customizable L3 chains built on top of Arbitrum L2.
They use the @arbitrum/chain-sdk for deployment and management.

**Key Concepts:**
- **Rollup mode**: All data posted on-chain (full Ethereum security)
- **AnyTrust mode**: Data stored by DAC (cheaper, trust assumption)
- **Custom gas tokens**: Use any ERC20 as the native gas token

**Deployment Flow:**
1. Prepare chain config (`prepareChainConfig()`)
2. Deploy rollup contracts (`createRollup()`)
3. Start Nitro node with deployment output
4. Deploy token bridge (`createTokenBridge()`)
5. Configure validators and batch posters

**Key SDK Functions:**
- `prepareChainConfig()` — Build chain configuration
- `createRollup()` — Deploy rollup contracts
- `createTokenBridge()` — Deploy token bridge
- `prepareNodeConfig()` — Generate Nitro node config

**Tools Available:**
- `generate_orbit_config` — Generate configuration scripts
- `generate_orbit_deployment` — Generate deployment scripts
- `generate_validator_setup` — Manage validators/batch posters
- `orchestrate_orbit` — Full project scaffold

For specific questions, try asking about:
- "How do I deploy an Orbit chain?"
- "What is the difference between Rollup and AnyTrust?"
- "How do I set up a custom gas token?"
- "How do I configure validators?"
"""

    @staticmethod
    def _get_references(topics: list) -> list[str]:
        """Get documentation references for topics."""
        refs = [
            "https://docs.arbitrum.io/launch-orbit-chain/orbit-gentle-introduction",
        ]

        if "deployment" in topics or "chain_config" in topics:
            refs.append(
                "https://docs.arbitrum.io/launch-orbit-chain/how-tos/orbit-sdk-deploying-rollup-chain"
            )

        if "token_bridge" in topics:
            refs.append(
                "https://docs.arbitrum.io/launch-orbit-chain/how-tos/orbit-sdk-deploying-token-bridge"
            )

        if "gas_tokens" in topics:
            refs.append(
                "https://docs.arbitrum.io/launch-orbit-chain/how-tos/orbit-sdk-deploying-custom-gas-token-chain"
            )

        if "anytrust" in topics:
            refs.append(
                "https://docs.arbitrum.io/launch-orbit-chain/how-tos/orbit-sdk-deploying-anytrust-chain"
            )

        if "node_setup" in topics:
            refs.append(
                "https://docs.arbitrum.io/run-arbitrum-node/run-full-node"
            )

        if "governance" in topics:
            refs.append(
                "https://docs.arbitrum.io/launch-orbit-chain/how-tos/orbit-sdk-managing-fee-routing"
            )

        if "validators" in topics:
            refs.append(
                "https://docs.arbitrum.io/launch-orbit-chain/concepts/chain-ownership"
            )

        if "code_standards" in topics:
            refs.append(
                "https://viem.sh/docs/getting-started"
            )

        return refs

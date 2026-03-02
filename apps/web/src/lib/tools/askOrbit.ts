/**
 * Ask Orbit Tool (M4 tool)
 *
 * Answers questions about Arbitrum Orbit chain deployment and management
 * using a curated knowledge base, RAG context retrieval, and LLM.
 */

import { answerOrbitQuestion } from "../openrouter";
import { getBridgingContext } from "./getBridgingContext";

export interface AskOrbitInput {
  question: string;
  questionType?: "general" | "deployment" | "config" | "validator" | "troubleshooting";
}

export interface AskOrbitOutput {
  answer: string;
  codeExamples: Array<{
    title: string;
    code: string;
    language: string;
  }>;
  references: string[];
  topics: string[];
  followUpQuestions: string[];
  tokensUsed: number;
}

// Pre-built knowledge base for Orbit chain topics
const ORBIT_KNOWLEDGE: Record<string, Record<string, string | string[]>> = {
  chain_config: {
    description: "Chain configuration for Orbit chains",
    function: "prepareChainConfig()",
    key_params: [
      "chainId - unique chain ID for the Orbit chain",
      "InitialChainOwner - address that controls chain admin operations",
      "DataAvailabilityCommittee - true for AnyTrust, false for Rollup",
    ],
    notes: [
      "Chain config is passed to createRollup() during deployment",
      "The chain owner can modify chain parameters via UpgradeExecutor",
      "Chain ID must not conflict with existing chains",
    ],
  },
  deployment: {
    description: "Deploying Orbit chain rollup contracts",
    function: "createRollup()",
    steps: [
      "1. Prepare chain config with prepareChainConfig()",
      "2. Configure validators and batch posters",
      "3. Call createRollup() with deployment params",
      "4. Save output contract addresses (rollup, inbox, outbox, bridge, etc.)",
      "5. Start the Nitro node with the deployed contract addresses",
      "6. Deploy token bridge with createTokenBridge()",
    ],
    requirements: [
      "Sufficient ETH on parent chain for gas",
      "At least one validator address",
      "At least one batch poster address",
      "Parent chain RPC endpoint",
    ],
  },
  validators: {
    description: "Validator and batch poster management",
    validator_role: "Confirm state assertions on the parent chain",
    validator_minimum: "At least 1 validator required",
    validator_management: "Add/remove via UpgradeExecutor with EXECUTOR_ROLE",
    batch_poster_role: "Submit transaction batches to the SequencerInbox",
    batch_poster_minimum: "At least 1 batch poster required",
    batch_poster_management: "Managed via SequencerInbox contract",
  },
  gas_tokens: {
    description: "Custom gas token configuration for Orbit chains",
    mechanism: [
      "Orbit chains can use any ERC20 as the native gas token",
      "The token must be deployed on the parent chain",
      "Token approval is required before createRollup()",
      "Users pay gas in the custom token instead of ETH",
    ],
    setup: [
      "1. Deploy (or use existing) ERC20 on parent chain",
      "2. Approve the RollupCreator to spend the token",
      "3. Pass nativeToken address to createRollup()",
    ],
    considerations: [
      "Token must have standard ERC20 interface",
      "Token decimals affect gas pricing",
      "Bridging requires token approval flow",
    ],
  },
  anytrust: {
    description: "AnyTrust Data Availability Committee (DAC) chains",
    mechanism: [
      "AnyTrust stores data with a DAC instead of on-chain",
      "Cheaper than Rollup mode but requires DAC trust assumption",
      "At least 2-of-N DAC members must be honest",
    ],
    keyset: [
      "DAC members have BLS public keys",
      "Keyset is registered via setValidKeyset() on SequencerInbox",
      "Keyset changes require UpgradeExecutor access",
    ],
    rollup_comparison: "All data posted on-chain (full Ethereum security)",
    anytrust_comparison: "Data stored by DAC (cheaper, N/2+1 trust assumption)",
  },
  node_setup: {
    description: "Setting up a Nitro node for an Orbit chain",
    function: "prepareNodeConfig()",
    components: [
      "Nitro node - executes transactions and produces blocks",
      "Validator node - posts assertions to parent chain",
      "Batch poster - submits transaction batches",
    ],
    config_params: [
      "chainId - Orbit chain ID",
      "parentChainId - parent chain ID",
      "coreContracts - addresses from deployment output",
      "parentChainRpcUrl - parent chain RPC endpoint",
    ],
    docker: "Nitro nodes are typically run via Docker images from OffchainLabs",
  },
  governance: {
    description: "Governance and admin operations via UpgradeExecutor",
    roles: [
      "EXECUTOR_ROLE - can execute arbitrary calls through UpgradeExecutor",
      "ADMIN_ROLE - can manage roles on the UpgradeExecutor",
    ],
    operations: [
      "Add/remove validators",
      "Update chain parameters",
      "Upgrade contract implementations",
      "Manage batch posters",
      "Update DAC keyset (AnyTrust)",
    ],
    security: [
      "UpgradeExecutor is the admin proxy for all chain contracts",
      "Multi-sig recommended for production chains",
      "Role assignments should be carefully managed",
    ],
  },
  token_bridge: {
    description: "Token bridge deployment for Orbit chains",
    function: "createTokenBridge()",
    components: [
      "GatewayRouter - routes token bridging to correct gateway",
      "StandardGateway - handles standard ERC20 bridging",
      "CustomGateway - for tokens with custom bridging logic",
    ],
    prerequisites: [
      "Rollup contracts must be deployed first",
      "Orbit chain node must be running",
      "Both parent and orbit chain RPCs must be accessible",
    ],
    process: [
      "1. Deploy rollup (createRollup)",
      "2. Start Orbit chain node",
      "3. Deploy token bridge (createTokenBridge)",
      "4. Verify bridge contracts on both chains",
    ],
  },
};

/**
 * RAG-powered Orbit chain Q&A tool.
 * Uses Vectorize for context retrieval and LLM for answer generation.
 */
export async function askOrbit(
  vectorize: VectorizeIndex,
  ai: Ai,
  openrouterApiKey: string,
  input: AskOrbitInput
): Promise<AskOrbitOutput> {
  const { question, questionType = "general" } = input;

  // Build enhanced search query based on question type
  let searchQuery = question;
  if (questionType === "deployment") {
    searchQuery = `orbit sdk createRollup deploy chain ${question}`;
  } else if (questionType === "config") {
    searchQuery = `orbit prepareChainConfig chain configuration ${question}`;
  } else if (questionType === "validator") {
    searchQuery = `orbit validator batch poster sequencer ${question}`;
  } else if (questionType === "troubleshooting") {
    searchQuery = `orbit deployment error fix troubleshoot ${question}`;
  } else {
    searchQuery = `arbitrum orbit chain l3 ${question}`;
  }

  // Get relevant context from Vectorize (graceful fallback on failure)
  let contextResult: Awaited<ReturnType<typeof getBridgingContext>>;
  try {
    contextResult = await getBridgingContext(vectorize, ai, {
      query: searchQuery,
      nResults: 5,
      rerank: true,
    });
  } catch (e) {
    console.warn("getBridgingContext failed, proceeding without RAG:", e);
    contextResult = { contexts: [], totalResults: 0, query: searchQuery };
  }

  // Build context string for LLM (cap per-item to prevent token overflow)
  const MAX_CONTEXT_CHARS = 2000;
  let contextStr = contextResult.contexts
    .slice(0, 3) // Top 3 most relevant
    .map((c, i) => `[${i + 1}] (${c.source})\n${c.content.slice(0, MAX_CONTEXT_CHARS)}`)
    .join("\n\n---\n\n");

  // Enrich with knowledge base if relevant topics detected
  const qLower = question.toLowerCase();
  const enrichments: string[] = [];
  const relevantTopics: string[] = [];

  if (
    qLower.includes("chain config") ||
    qLower.includes("prepare config") ||
    qLower.includes("configure chain") ||
    qLower.includes("chain id") ||
    qLower.includes("chainconfig")
  ) {
    relevantTopics.push("chain_config");
    enrichments.push(formatKnowledge("chain_config"));
  }

  if (
    qLower.includes("deploy") ||
    qLower.includes("create rollup") ||
    qLower.includes("launch") ||
    qLower.includes("createrollup")
  ) {
    relevantTopics.push("deployment");
    enrichments.push(formatKnowledge("deployment"));
  }

  if (
    qLower.includes("validator") ||
    qLower.includes("batch poster") ||
    qLower.includes("sequencer")
  ) {
    relevantTopics.push("validators");
    enrichments.push(formatKnowledge("validators"));
  }

  if (
    qLower.includes("gas token") ||
    qLower.includes("native token") ||
    qLower.includes("custom gas") ||
    qLower.includes("erc20 gas")
  ) {
    relevantTopics.push("gas_tokens");
    enrichments.push(formatKnowledge("gas_tokens"));
  }

  if (
    qLower.includes("anytrust") ||
    qLower.includes("dac") ||
    qLower.includes("keyset") ||
    qLower.includes("data availability")
  ) {
    relevantTopics.push("anytrust");
    enrichments.push(formatKnowledge("anytrust"));
  }

  if (
    qLower.includes("node") ||
    qLower.includes("nitro") ||
    qLower.includes("run node")
  ) {
    relevantTopics.push("node_setup");
    enrichments.push(formatKnowledge("node_setup"));
  }

  if (
    qLower.includes("governance") ||
    qLower.includes("upgrade") ||
    qLower.includes("executor") ||
    qLower.includes("admin") ||
    qLower.includes("permission")
  ) {
    relevantTopics.push("governance");
    enrichments.push(formatKnowledge("governance"));
  }

  if (
    qLower.includes("token bridge") ||
    qLower.includes("bridge") ||
    qLower.includes("gateway") ||
    qLower.includes("createtokenbridge")
  ) {
    relevantTopics.push("token_bridge");
    enrichments.push(formatKnowledge("token_bridge"));
  }

  if (enrichments.length > 0) {
    contextStr = `Quick Reference:\n${enrichments.join("\n")}\n\n---\n\n${contextStr}`;
  }

  // Get answer from LLM
  const response = await answerOrbitQuestion(openrouterApiKey, question, contextStr);

  // Fallback: if LLM returned empty after all retries, use knowledge base + RAG context
  let answerContent = response.content;
  if (!answerContent || answerContent.trim().length === 0) {
    const parts: string[] = [];

    // Use knowledge base enrichments first (structured data)
    if (enrichments.length > 0) {
      parts.push(`Here's what I know about this topic:\n\n${enrichments.join("\n\n")}`);
    }

    // Add RAG context excerpts
    const ctxSummary = contextResult.contexts
      .slice(0, 3)
      .map((c) => `From ${c.source}:\n${c.content.slice(0, 800)}`)
      .join("\n\n---\n\n");
    if (ctxSummary) {
      parts.push(`Relevant excerpts from the documentation:\n\n${ctxSummary}`);
    }

    if (parts.length > 0) {
      answerContent =
        parts.join("\n\n---\n\n") +
        `\n\nFor more details, see https://docs.arbitrum.io/launch-orbit-chain/orbit-gentle-introduction`;
    } else {
      answerContent = getGenericAnswer(question);
    }
  }

  // Extract code examples from response
  const codeExamples: Array<{ title: string; code: string; language: string }> = [];
  const codeBlockRegex = /```(typescript|javascript|ts|js)?\n([\s\S]*?)```/g;
  let match;
  let exampleIndex = 1;
  while ((match = codeBlockRegex.exec(answerContent)) !== null) {
    codeExamples.push({
      title: `Example ${exampleIndex++}`,
      code: match[2].trim(),
      language: match[1] || "typescript",
    });
  }

  // Generate follow-up questions
  const followUpQuestions = generateFollowUpQuestions(questionType);

  // Deduplicate topics
  const uniqueTopics = [...new Set(relevantTopics)];

  return {
    answer: answerContent
      .replace(/```(?:typescript|javascript|ts|js)?\n[\s\S]*?```/g, "[Code example above]")
      .trim(),
    codeExamples,
    references: getReferences(uniqueTopics),
    topics: uniqueTopics.length > 0 ? uniqueTopics : ["general"],
    followUpQuestions,
    tokensUsed: response.usage.totalTokens,
  };
}

function formatKnowledge(topic: string): string {
  const info = ORBIT_KNOWLEDGE[topic];
  if (!info) return "";

  const lines: string[] = [`**${topic.replace(/_/g, " ").toUpperCase()}**`];
  for (const [key, value] of Object.entries(info)) {
    if (Array.isArray(value)) {
      lines.push(`- ${key}: ${value.join(", ")}`);
    } else {
      lines.push(`- ${key}: ${value}`);
    }
  }
  return lines.join("\n");
}

function getGenericAnswer(question: string): string {
  return `Regarding "${question}":

Orbit chains are customizable L3 chains built on top of Arbitrum L2.
They use the @arbitrum/orbit-sdk for deployment and management.

**Key Concepts:**
- **Rollup mode**: All data posted on-chain (full Ethereum security)
- **AnyTrust mode**: Data stored by DAC (cheaper, trust assumption)
- **Custom gas tokens**: Use any ERC20 as the native gas token

**Deployment Flow:**
1. Prepare chain config (\`prepareChainConfig()\`)
2. Deploy rollup contracts (\`createRollup()\`)
3. Start Nitro node with deployment output
4. Deploy token bridge (\`createTokenBridge()\`)
5. Configure validators and batch posters

**Key SDK Functions:**
- \`prepareChainConfig()\` - Build chain configuration
- \`createRollup()\` - Deploy rollup contracts
- \`createTokenBridge()\` - Deploy token bridge
- \`prepareNodeConfig()\` - Generate Nitro node config

For detailed guidance, see https://docs.arbitrum.io/launch-orbit-chain/orbit-gentle-introduction`;
}

function getReferences(topics: string[]): string[] {
  const refs = [
    "https://docs.arbitrum.io/launch-orbit-chain/orbit-gentle-introduction",
  ];

  if (topics.includes("deployment") || topics.includes("chain_config")) {
    refs.push(
      "https://docs.arbitrum.io/launch-orbit-chain/how-tos/orbit-sdk-deploying-rollup-chain"
    );
  }
  if (topics.includes("token_bridge")) {
    refs.push(
      "https://docs.arbitrum.io/launch-orbit-chain/how-tos/orbit-sdk-deploying-token-bridge"
    );
  }
  if (topics.includes("gas_tokens")) {
    refs.push(
      "https://docs.arbitrum.io/launch-orbit-chain/how-tos/orbit-sdk-deploying-custom-gas-token-chain"
    );
  }
  if (topics.includes("anytrust")) {
    refs.push(
      "https://docs.arbitrum.io/launch-orbit-chain/how-tos/orbit-sdk-deploying-anytrust-chain"
    );
  }
  if (topics.includes("node_setup")) {
    refs.push(
      "https://docs.arbitrum.io/run-arbitrum-node/run-full-node"
    );
  }
  if (topics.includes("governance")) {
    refs.push(
      "https://docs.arbitrum.io/launch-orbit-chain/how-tos/orbit-sdk-managing-fee-routing"
    );
  }
  if (topics.includes("validators")) {
    refs.push(
      "https://docs.arbitrum.io/launch-orbit-chain/concepts/chain-ownership"
    );
  }

  return refs;
}

function generateFollowUpQuestions(questionType: string): string[] {
  const followUps: Record<string, string[]> = {
    general: [
      "How do I deploy an Orbit chain?",
      "What is the difference between Rollup and AnyTrust?",
      "How do I set up a custom gas token?",
    ],
    deployment: [
      "How do I deploy a token bridge for my Orbit chain?",
      "How do I configure validators after deployment?",
      "What contract addresses do I need to save from deployment?",
    ],
    config: [
      "What is the difference between Rollup and AnyTrust?",
      "How do I set up a custom gas token?",
      "What chain ID should I use?",
    ],
    validator: [
      "How do I add a new validator to my Orbit chain?",
      "What is the minimum number of validators?",
      "How do I manage batch posters?",
    ],
    troubleshooting: [
      "Why did my deployment transaction fail?",
      "How do I verify my Orbit chain contracts?",
      "What if my validator is not posting assertions?",
    ],
  };

  return followUps[questionType] || followUps.general;
}

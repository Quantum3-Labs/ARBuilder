import type { OpenAIToolDef } from "./types";
import { CHAT_TOOL_NAMES, runTool, type ToolEnv } from "@/lib/tools/dispatch";

/**
 * 14 OpenAI-format tool definitions exposed to the chat agent.
 * The 4 large scaffolders (generate_backend, generate_frontend,
 * orchestrate_dapp, orchestrate_orbit) are intentionally excluded —
 * their multi-file outputs blow context budgets in a ReAct loop.
 *
 * Schemas are lifted from apps/web/src/app/mcp/route.ts TOOLS array,
 * filtered to chat-friendly names and reformatted per OpenAI's
 * `{type:"function", function:{...}}` envelope.
 */
export const ARBBUILDER_TOOL_DEFS: OpenAIToolDef[] = [
  {
    type: "function",
    function: {
      name: "get_stylus_context",
      description:
        "Search for relevant Stylus documentation, code examples, and patterns. Use this to find information about Stylus SDK, Rust smart contract development, and Arbitrum.",
      parameters: {
        type: "object",
        properties: {
          query: { type: "string", description: "The search query to find relevant context" },
          nResults: { type: "number", description: "Number of results to return (default: 5)" },
          contentType: {
            type: "string",
            enum: ["code", "documentation", "all"],
            description: "Type of content to search for",
          },
          rerank: { type: "boolean", description: "Whether to rerank results for better relevance" },
        },
        required: ["query"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_stylus_code",
      description:
        "Generate Stylus (Rust) smart contract code based on a description. Produces production-ready code using stylus-sdk.",
      parameters: {
        type: "object",
        properties: {
          prompt: { type: "string", description: "Description of the contract or code to generate" },
          contractType: {
            type: "string",
            enum: ["token", "nft", "defi", "utility", "custom"],
            description: "Type of contract",
          },
          includeTests: { type: "boolean", description: "Whether to include test code" },
        },
        required: ["prompt"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "ask_stylus",
      description:
        "Ask questions about Stylus development, debugging, optimization, or security. Gets context-aware answers with code examples.",
      parameters: {
        type: "object",
        properties: {
          question: { type: "string", description: "The question to ask about Stylus development" },
          codeContext: { type: "string", description: "Optional code context for more specific answers" },
          questionType: {
            type: "string",
            enum: ["general", "debugging", "optimization", "security"],
            description: "Type of question",
          },
        },
        required: ["question"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_tests",
      description:
        "Generate comprehensive tests for Stylus contract code. Supports Rust native tests and Foundry Solidity tests.",
      parameters: {
        type: "object",
        properties: {
          contractCode: { type: "string", description: "The Stylus contract code to generate tests for" },
          testFramework: {
            type: "string",
            enum: ["rust_native", "foundry"],
            description: "Test framework",
          },
        },
        required: ["contractCode"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "get_workflow",
      description:
        "Get step-by-step workflow instructions for building, deploying, or testing Stylus contracts.",
      parameters: {
        type: "object",
        properties: {
          workflowType: { type: "string", enum: ["build", "deploy", "test"] },
          network: {
            type: "string",
            enum: ["arbitrum_sepolia", "arbitrum_one", "arbitrum_nova"],
            description: "Target network",
          },
          includeTroubleshooting: { type: "boolean" },
        },
        required: ["workflowType"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_bridge_code",
      description:
        "Generate TypeScript code for bridging ETH or ERC20 tokens between L1, L2, and L3 (Orbit chains). Supports deposits, withdrawals, and L1->L3 bridging.",
      parameters: {
        type: "object",
        properties: {
          bridgeType: {
            type: "string",
            enum: [
              "eth_deposit", "eth_deposit_to", "eth_withdraw",
              "erc20_deposit", "erc20_withdraw", "eth_l1_l3", "erc20_l1_l3",
            ],
          },
          amount: { type: "string", description: "Amount to bridge (e.g., '0.1' for ETH)" },
          tokenAddress: { type: "string", description: "ERC20 token address" },
          destinationAddress: { type: "string", description: "Destination address (for depositTo)" },
        },
        required: ["bridgeType"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_messaging_code",
      description:
        "Generate TypeScript code for Arbitrum cross-chain messaging. Supports L1->L2 messaging via retryable tickets, L2->L1 messaging via ArbSys, and message status checking.",
      parameters: {
        type: "object",
        properties: {
          messageType: {
            type: "string",
            enum: ["l1_to_l2", "l2_to_l1", "l2_to_l1_claim", "check_status"],
          },
          includeExample: { type: "boolean" },
        },
        required: ["messageType"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "ask_bridging",
      description:
        "Answer questions about Arbitrum bridging and cross-chain messaging using RAG. Topics: ETH/ERC20 bridging, L1->L3 bridging, retryable tickets, challenge periods, gas estimation.",
      parameters: {
        type: "object",
        properties: {
          question: { type: "string", description: "Question about Arbitrum bridging or messaging" },
          questionType: {
            type: "string",
            enum: ["general", "bridging", "messaging", "l3"],
          },
        },
        required: ["question"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_indexer",
      description:
        "Generate a The Graph subgraph for indexing Arbitrum smart contract events. Supports ERC20, ERC721, DeFi, and custom event patterns.",
      parameters: {
        type: "object",
        properties: {
          contractAddress: { type: "string", description: "Contract address to index" },
          subgraphType: {
            type: "string",
            enum: ["erc20", "erc721", "defi", "custom"],
          },
          abi: { type: "string", description: "Contract ABI JSON for custom event handling" },
          events: { type: "array", items: { type: "string" }, description: "Event signatures to index" },
          network: { type: "string", description: "Target network" },
        },
        required: ["contractAddress"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_oracle",
      description:
        "Generate Chainlink oracle integration code for Arbitrum. Supports Price Feeds, VRF (randomness), Automation (keepers), and Functions.",
      parameters: {
        type: "object",
        properties: {
          oracleType: {
            type: "string",
            enum: ["price_feed", "vrf", "automation", "functions"],
          },
          network: { type: "string", enum: ["arbitrum-one", "arbitrum-sepolia"] },
          feeds: { type: "array", items: { type: "string" }, description: "Price feed pairs" },
        },
        required: ["oracleType"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_orbit_config",
      description:
        "Generate configuration code for Orbit chain deployment. Supports chain config, AnyTrust DAC setup, and custom gas token configuration using @arbitrum/orbit-sdk.",
      parameters: {
        type: "object",
        properties: {
          prompt: { type: "string", description: "Description of the configuration needed" },
          chainId: { type: "number", description: "Chain ID for the new Orbit chain" },
          owner: { type: "string", description: "Initial chain owner address" },
          isAnyTrust: { type: "boolean", description: "AnyTrust (vs Rollup)" },
          nativeToken: { type: "string", description: "Custom gas token address (ERC20)" },
          parentChain: {
            type: "string",
            enum: ["arbitrum-one", "arbitrum-sepolia", "ethereum-mainnet", "ethereum-sepolia"],
          },
        },
        required: ["prompt"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_orbit_deployment",
      description:
        "Generate deployment code for Orbit chains. Supports rollup deployment (createRollup), token bridge deployment (createTokenBridge), or full deployment with both.",
      parameters: {
        type: "object",
        properties: {
          prompt: { type: "string", description: "Description of the deployment needed" },
          deploymentType: { type: "string", enum: ["rollup", "token_bridge", "full"] },
          validators: { type: "array", items: { type: "string" } },
          batchPosters: { type: "array", items: { type: "string" } },
          nativeToken: { type: "string" },
          parentChain: {
            type: "string",
            enum: ["arbitrum-one", "arbitrum-sepolia", "ethereum-mainnet", "ethereum-sepolia"],
          },
          rollupVersion: { type: "string", enum: ["v2.1", "v3.1"] },
          chainId: { type: "number" },
          isAnyTrust: { type: "boolean" },
          rollupAddress: { type: "string", description: "Existing rollup contract address" },
        },
        required: ["prompt"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "generate_validator_setup",
      description:
        "Generate code for managing Orbit chain validators, batch posters, and AnyTrust DAC keysets. Supports listing, adding, and removing validators.",
      parameters: {
        type: "object",
        properties: {
          prompt: { type: "string", description: "Description of the validator management needed" },
          action: { type: "string", enum: ["list", "add", "remove"] },
          target: { type: "string", enum: ["validator", "batch_poster", "keyset"] },
          addresses: { type: "array", items: { type: "string" } },
          rollupAddress: { type: "string" },
          sequencerInbox: { type: "string" },
          parentChain: {
            type: "string",
            enum: ["arbitrum-one", "arbitrum-sepolia", "ethereum-mainnet", "ethereum-sepolia"],
          },
        },
        required: ["prompt"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "ask_orbit",
      description:
        "Answer questions about Arbitrum Orbit chain deployment, configuration, and management. Covers chain config, deployment, validators, gas tokens, AnyTrust, node setup, governance, and token bridges.",
      parameters: {
        type: "object",
        properties: {
          question: { type: "string", description: "Question about Orbit chain deployment or management" },
          questionType: {
            type: "string",
            enum: ["general", "deployment", "config", "validator", "troubleshooting"],
          },
        },
        required: ["question"],
      },
    },
  },
];

/**
 * Tool result serialization for the role:tool message fed back to the model.
 * Soft-cap at 32_000 chars (~8000 tokens). Past the cap, return a structured
 * truncation marker so the model can still reason about the call's outcome.
 */
const TOOL_RESULT_MAX_CHARS = 32_000;

function serializeToolResult(data: unknown): string {
  const json = typeof data === "string" ? data : JSON.stringify(data, null, 2);
  if (json.length <= TOOL_RESULT_MAX_CHARS) return json;
  return JSON.stringify({
    truncated: true,
    note: `Result was ${json.length} chars; truncated to first ${TOOL_RESULT_MAX_CHARS} for context budget.`,
    preview: json.slice(0, TOOL_RESULT_MAX_CHARS),
  });
}

/**
 * Execute a single OpenAI-format tool_call, returning the tool message
 * to append to the conversation. Errors during tool execution are returned
 * as a structured error so the model can react rather than crashing the loop.
 */
export async function executeToolCall(
  toolCall: { id: string; function: { name: string; arguments: string } },
  env: ToolEnv,
): Promise<{ tool_call_id: string; content: string; toolName: string; success: boolean }> {
  const { name, arguments: argsJson } = toolCall.function;

  // Reject tools that aren't in the chat surface.
  if (!CHAT_TOOL_NAMES.includes(name as (typeof CHAT_TOOL_NAMES)[number])) {
    return {
      tool_call_id: toolCall.id,
      toolName: name,
      success: false,
      content: JSON.stringify({ error: `Tool '${name}' is not available in chat surface.` }),
    };
  }

  let args: Record<string, unknown>;
  try {
    args = JSON.parse(argsJson || "{}");
  } catch (e) {
    return {
      tool_call_id: toolCall.id,
      toolName: name,
      success: false,
      content: JSON.stringify({ error: `Invalid JSON in tool arguments: ${(e as Error).message}` }),
    };
  }

  try {
    const result = await runTool(name, args, env);
    return {
      tool_call_id: toolCall.id,
      toolName: name,
      success: true,
      content: serializeToolResult(result.data),
    };
  } catch (e) {
    return {
      tool_call_id: toolCall.id,
      toolName: name,
      success: false,
      content: JSON.stringify({ error: (e as Error).message || String(e) }),
    };
  }
}

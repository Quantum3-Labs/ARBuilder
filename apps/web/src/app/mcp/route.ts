/**
 * MCP (Model Context Protocol) HTTP Endpoint
 *
 * Implements the MCP protocol over HTTP for mcp-remote clients.
 * Supports the Streamable HTTP transport used by Cursor, Claude Desktop, etc.
 */

import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { runTool, type ToolEnv, type ToolResult } from "@/lib/tools/dispatch";

// MCP Protocol Types
interface JsonRpcRequest {
  jsonrpc: "2.0";
  id: string | number;
  method: string;
  params?: Record<string, unknown>;
}

interface JsonRpcResponse {
  jsonrpc: "2.0";
  id: string | number | null;
  result?: unknown;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
}

// Tool definitions for MCP
const TOOLS = [
  {
    name: "get_stylus_context",
    description:
      "Search for relevant Stylus documentation, code examples, and patterns. Use this to find information about Stylus SDK, Rust smart contract development, and Arbitrum.",
    inputSchema: {
      type: "object" as const,
      properties: {
        query: {
          type: "string",
          description: "The search query to find relevant context",
        },
        nResults: {
          type: "number",
          description: "Number of results to return (default: 5)",
          default: 5,
        },
        contentType: {
          type: "string",
          enum: ["code", "documentation", "all"],
          description: "Type of content to search for",
          default: "all",
        },
        rerank: {
          type: "boolean",
          description: "Whether to rerank results for better relevance",
          default: true,
        },
      },
      required: ["query"],
    },
  },
  {
    name: "generate_stylus_code",
    description:
      "Generate Stylus (Rust) smart contract code based on a description. Produces production-ready code using stylus-sdk.",
    inputSchema: {
      type: "object" as const,
      properties: {
        prompt: {
          type: "string",
          description: "Description of the contract or code to generate",
        },
        contractType: {
          type: "string",
          enum: ["token", "nft", "defi", "utility", "custom"],
          description: "Type of contract to generate",
          default: "utility",
        },
        includeTests: {
          type: "boolean",
          description: "Whether to include test code",
          default: false,
        },
      },
      required: ["prompt"],
    },
  },
  {
    name: "ask_stylus",
    description:
      "Ask questions about Stylus development, debugging, optimization, or security. Gets context-aware answers with code examples.",
    inputSchema: {
      type: "object" as const,
      properties: {
        question: {
          type: "string",
          description: "The question to ask about Stylus development",
        },
        codeContext: {
          type: "string",
          description: "Optional code context for more specific answers",
        },
        questionType: {
          type: "string",
          enum: ["general", "debugging", "optimization", "security"],
          description: "Type of question for better context",
          default: "general",
        },
      },
      required: ["question"],
    },
  },
  {
    name: "generate_tests",
    description:
      "Generate comprehensive tests for Stylus contract code. Supports Rust native tests and Foundry Solidity tests.",
    inputSchema: {
      type: "object" as const,
      properties: {
        contractCode: {
          type: "string",
          description: "The Stylus contract code to generate tests for",
        },
        testFramework: {
          type: "string",
          enum: ["rust_native", "foundry"],
          description: "Test framework to use",
          default: "rust_native",
        },
      },
      required: ["contractCode"],
    },
  },
  {
    name: "get_workflow",
    description:
      "Get step-by-step workflow instructions for building, deploying, or testing Stylus contracts.",
    inputSchema: {
      type: "object" as const,
      properties: {
        workflowType: {
          type: "string",
          enum: ["build", "deploy", "test"],
          description: "Type of workflow to get",
        },
        network: {
          type: "string",
          enum: ["arbitrum_sepolia", "arbitrum_one", "arbitrum_nova"],
          description: "Target network for deploy workflows",
          default: "arbitrum_sepolia",
        },
        includeTroubleshooting: {
          type: "boolean",
          description: "Include troubleshooting tips",
          default: true,
        },
      },
      required: ["workflowType"],
    },
  },
  // M2: Arbitrum SDK Tools
  {
    name: "generate_bridge_code",
    description:
      "Generate TypeScript code for bridging ETH or ERC20 tokens between L1, L2, and L3 (Orbit chains). Supports deposits, withdrawals, and L1->L3 bridging.",
    inputSchema: {
      type: "object" as const,
      properties: {
        bridgeType: {
          type: "string",
          enum: [
            "eth_deposit",
            "eth_deposit_to",
            "eth_withdraw",
            "erc20_deposit",
            "erc20_withdraw",
            "eth_l1_l3",
            "erc20_l1_l3",
          ],
          description: "Type of bridging operation to generate code for",
        },
        amount: {
          type: "string",
          description: "Amount to bridge (e.g., '0.1' for ETH)",
          default: "0.1",
        },
        tokenAddress: {
          type: "string",
          description: "ERC20 token address (required for token bridging)",
        },
        destinationAddress: {
          type: "string",
          description: "Destination address (required for depositTo)",
        },
      },
      required: ["bridgeType"],
    },
  },
  {
    name: "generate_messaging_code",
    description:
      "Generate TypeScript code for Arbitrum cross-chain messaging. Supports L1->L2 messaging via retryable tickets, L2->L1 messaging via ArbSys, and message status checking.",
    inputSchema: {
      type: "object" as const,
      properties: {
        messageType: {
          type: "string",
          enum: ["l1_to_l2", "l2_to_l1", "l2_to_l1_claim", "check_status"],
          description: "Type of messaging operation to generate code for",
        },
        includeExample: {
          type: "boolean",
          description: "Include example usage with sample contract call",
          default: true,
        },
      },
      required: ["messageType"],
    },
  },
  {
    name: "ask_bridging",
    description:
      "Answer questions about Arbitrum bridging and cross-chain messaging using RAG. Topics: ETH/ERC20 bridging, L1->L3 bridging, retryable tickets, challenge periods, gas estimation.",
    inputSchema: {
      type: "object" as const,
      properties: {
        question: {
          type: "string",
          description: "Question about Arbitrum bridging or messaging",
        },
        questionType: {
          type: "string",
          enum: ["general", "bridging", "messaging", "l3"],
          description: "Type of question for better context retrieval",
          default: "general",
        },
      },
      required: ["question"],
    },
  },
  // M3: Full dApp Builder Tools
  {
    name: "generate_backend",
    description:
      "Generate a Web3 backend using NestJS or Express with viem integration for Arbitrum. Includes contract interaction services, API endpoints, and TypeScript configuration.",
    inputSchema: {
      type: "object" as const,
      properties: {
        prompt: {
          type: "string",
          description: "Description of the backend to generate",
        },
        framework: {
          type: "string",
          enum: ["nestjs", "express"],
          description: "Backend framework to use",
          default: "nestjs",
        },
        contractAbi: {
          type: "string",
          description: "Contract ABI JSON for generating typed services",
        },
        features: {
          type: "array",
          items: { type: "string" },
          description: "Additional features (websocket, caching)",
        },
      },
      required: ["prompt"],
    },
  },
  {
    name: "generate_frontend",
    description:
      "Generate a Next.js frontend with wagmi, RainbowKit, and DaisyUI for Arbitrum dApps. Includes wallet connection, contract hooks, and responsive UI components.",
    inputSchema: {
      type: "object" as const,
      properties: {
        prompt: {
          type: "string",
          description: "Description of the frontend to generate",
        },
        contractAbi: {
          type: "string",
          description: "Contract ABI JSON for generating typed hooks",
        },
        uiFramework: {
          type: "string",
          enum: ["daisyui", "shadcn", "none"],
          description: "UI component library to use",
          default: "daisyui",
        },
        template: {
          type: "string",
          enum: ["base", "dashboard", "token"],
          description: "Template to start from",
          default: "base",
        },
      },
      required: ["prompt"],
    },
  },
  {
    name: "generate_indexer",
    description:
      "Generate a The Graph subgraph for indexing Arbitrum smart contract events. Supports ERC20, ERC721, DeFi, and custom event patterns.",
    inputSchema: {
      type: "object" as const,
      properties: {
        contractAddress: {
          type: "string",
          description: "Contract address to index",
        },
        subgraphType: {
          type: "string",
          enum: ["erc20", "erc721", "defi", "custom"],
          description: "Type of subgraph template",
          default: "erc20",
        },
        abi: {
          type: "string",
          description: "Contract ABI JSON for custom event handling",
        },
        events: {
          type: "array",
          items: { type: "string" },
          description: "Event signatures to index (for custom type)",
        },
        network: {
          type: "string",
          description: "Target network",
          default: "arbitrum-sepolia",
        },
      },
      required: ["contractAddress"],
    },
  },
  {
    name: "generate_oracle",
    description:
      "Generate Chainlink oracle integration code for Arbitrum. Supports Price Feeds, VRF (randomness), Automation (keepers), and Functions.",
    inputSchema: {
      type: "object" as const,
      properties: {
        oracleType: {
          type: "string",
          enum: ["price_feed", "vrf", "automation", "functions"],
          description: "Type of Chainlink oracle to integrate",
        },
        network: {
          type: "string",
          enum: ["arbitrum-one", "arbitrum-sepolia"],
          description: "Target network",
          default: "arbitrum-sepolia",
        },
        feeds: {
          type: "array",
          items: { type: "string" },
          description: "Price feed pairs (e.g., ETH/USD, BTC/USD)",
        },
      },
      required: ["oracleType"],
    },
  },
  {
    name: "orchestrate_dapp",
    description:
      "Scaffold a template-based dApp monorepo with starter components: Stylus contract, backend, frontend, indexer, and oracle. Creates a project structure with generic templates to customize.",
    inputSchema: {
      type: "object" as const,
      properties: {
        prompt: {
          type: "string",
          description: "Description of the dApp to build",
        },
        components: {
          type: "array",
          items: {
            type: "string",
            enum: ["contract", "backend", "frontend", "indexer", "oracle"],
          },
          description: "Components to include in the dApp",
          default: ["contract", "frontend"],
        },
        network: {
          type: "string",
          enum: ["arbitrum-sepolia", "arbitrum-one"],
          description: "Target network for deployment",
          default: "arbitrum-sepolia",
        },
        contractAddress: {
          type: "string",
          description: "Existing contract address (if not generating new)",
        },
        contractAbi: {
          type: "string",
          description: "Contract ABI for integration",
        },
      },
      required: ["prompt"],
    },
  },
  // M4: Orbit Chain Tools
  {
    name: "generate_orbit_config",
    description:
      "Generate configuration code for Orbit chain deployment. Supports chain config, AnyTrust DAC setup, and custom gas token configuration using @arbitrum/orbit-sdk.",
    inputSchema: {
      type: "object" as const,
      properties: {
        prompt: {
          type: "string",
          description: "Description of the configuration needed",
        },
        chainId: {
          type: "number",
          description: "Chain ID for the new Orbit chain",
          default: 412346,
        },
        owner: {
          type: "string",
          description: "Initial chain owner address (0x...)",
        },
        isAnyTrust: {
          type: "boolean",
          description: "Whether this is an AnyTrust chain (vs Rollup)",
          default: false,
        },
        nativeToken: {
          type: "string",
          description: "Custom gas token address (ERC20)",
        },
        parentChain: {
          type: "string",
          enum: ["arbitrum-one", "arbitrum-sepolia", "ethereum-mainnet", "ethereum-sepolia"],
          description: "Parent chain for the Orbit chain",
          default: "arbitrum-sepolia",
        },
      },
      required: ["prompt"],
    },
  },
  {
    name: "generate_orbit_deployment",
    description:
      "Generate deployment code for Orbit chains. Supports rollup deployment (createRollup), token bridge deployment (createTokenBridge), or full deployment with both.",
    inputSchema: {
      type: "object" as const,
      properties: {
        prompt: {
          type: "string",
          description: "Description of the deployment needed",
        },
        deploymentType: {
          type: "string",
          enum: ["rollup", "token_bridge", "full"],
          description: "Type of deployment to generate",
          default: "rollup",
        },
        validators: {
          type: "array",
          items: { type: "string" },
          description: "Validator addresses for the chain",
        },
        batchPosters: {
          type: "array",
          items: { type: "string" },
          description: "Batch poster addresses for the chain",
        },
        nativeToken: {
          type: "string",
          description: "Custom gas token address (ERC20)",
        },
        parentChain: {
          type: "string",
          enum: ["arbitrum-one", "arbitrum-sepolia", "ethereum-mainnet", "ethereum-sepolia"],
          description: "Parent chain for the Orbit chain",
          default: "arbitrum-sepolia",
        },
        rollupVersion: {
          type: "string",
          enum: ["v2.1", "v3.1"],
          description: "RollupCreator version to use",
          default: "v3.1",
        },
        chainId: {
          type: "number",
          description: "Chain ID for the new Orbit chain",
          default: 412346,
        },
        isAnyTrust: {
          type: "boolean",
          description: "Whether this is an AnyTrust chain",
          default: false,
        },
        rollupAddress: {
          type: "string",
          description: "Existing rollup contract address (for token bridge deployment)",
        },
      },
      required: ["prompt"],
    },
  },
  {
    name: "generate_validator_setup",
    description:
      "Generate code for managing Orbit chain validators, batch posters, and AnyTrust DAC keysets. Supports listing, adding, and removing validators.",
    inputSchema: {
      type: "object" as const,
      properties: {
        prompt: {
          type: "string",
          description: "Description of the validator management needed",
        },
        action: {
          type: "string",
          enum: ["list", "add", "remove"],
          description: "Action to perform",
          default: "list",
        },
        target: {
          type: "string",
          enum: ["validator", "batch_poster", "keyset"],
          description: "Target to manage",
          default: "validator",
        },
        addresses: {
          type: "array",
          items: { type: "string" },
          description: "Addresses to add/remove",
        },
        rollupAddress: {
          type: "string",
          description: "Rollup contract address",
        },
        sequencerInbox: {
          type: "string",
          description: "SequencerInbox contract address",
        },
        parentChain: {
          type: "string",
          enum: ["arbitrum-one", "arbitrum-sepolia", "ethereum-mainnet", "ethereum-sepolia"],
          description: "Parent chain",
          default: "arbitrum-sepolia",
        },
      },
      required: ["prompt"],
    },
  },
  {
    name: "ask_orbit",
    description:
      "Answer questions about Arbitrum Orbit chain deployment, configuration, and management. Covers chain config, deployment, validators, gas tokens, AnyTrust, node setup, governance, and token bridges.",
    inputSchema: {
      type: "object" as const,
      properties: {
        question: {
          type: "string",
          description: "Question about Orbit chain deployment or management",
        },
        questionType: {
          type: "string",
          enum: ["general", "deployment", "config", "validator", "troubleshooting"],
          description: "Type of question for better context",
          default: "general",
        },
      },
      required: ["question"],
    },
  },
  {
    name: "orchestrate_orbit",
    description:
      "Scaffold a complete Orbit chain deployment project with all scripts, configuration, and documentation. Generates deploy-rollup, deploy-token-bridge, manage-validators, and node config scripts.",
    inputSchema: {
      type: "object" as const,
      properties: {
        prompt: {
          type: "string",
          description: "Description of the Orbit chain project",
        },
        chainName: {
          type: "string",
          description: "Name for the Orbit chain",
          default: "my-orbit-chain",
        },
        chainId: {
          type: "number",
          description: "Chain ID for the new Orbit chain",
          default: 412346,
        },
        isAnyTrust: {
          type: "boolean",
          description: "Whether this is an AnyTrust chain",
          default: false,
        },
        nativeToken: {
          type: "string",
          description: "Custom gas token address (ERC20)",
        },
        parentChain: {
          type: "string",
          enum: ["arbitrum-one", "arbitrum-sepolia", "ethereum-mainnet", "ethereum-sepolia"],
          description: "Parent chain for the Orbit chain",
          default: "arbitrum-sepolia",
        },
        validators: {
          type: "array",
          items: { type: "string" },
          description: "Validator addresses",
        },
        batchPosters: {
          type: "array",
          items: { type: "string" },
          description: "Batch poster addresses",
        },
      },
      required: ["prompt"],
    },
  },
];

// Server info for MCP
const SERVER_INFO = {
  name: "arbbuilder",
  version: "1.3.0", // M4: Added Orbit Chain tools
  protocolVersion: "2024-11-05",
};

// Validate API key from Authorization header
async function validateApiKey(
  request: NextRequest,
  db: D1Database
): Promise<{ valid: boolean; keyId?: string; userId?: string; error?: string }> {
  const authHeader = request.headers.get("Authorization");
  if (!authHeader?.startsWith("Bearer ")) {
    return { valid: false, error: "Missing or invalid Authorization header" };
  }

  const apiKey = authHeader.slice(7);
  if (!apiKey.startsWith("arb_")) {
    return { valid: false, error: "Invalid API key format" };
  }

  // Hash the API key for lookup
  const encoder = new TextEncoder();
  const data = encoder.encode(apiKey);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const keyHash = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");

  // Look up the key
  const keyRecord = await db
    .prepare(
      `SELECT id, user_id FROM api_keys WHERE key_hash = ? AND revoked_at IS NULL`
    )
    .bind(keyHash)
    .first<{ id: string; user_id: string }>();

  if (!keyRecord) {
    return { valid: false, error: "Invalid or revoked API key" };
  }

  // Update last used timestamp
  await db
    .prepare(`UPDATE api_keys SET last_used_at = ? WHERE id = ?`)
    .bind(new Date().toISOString(), keyRecord.id)
    .run();

  return { valid: true, keyId: keyRecord.id, userId: keyRecord.user_id };
}

// Log usage to database
async function logUsage(
  db: D1Database,
  apiKeyId: string,
  tool: string,
  latencyMs: number,
  tokensUsed: number = 0,
  success: boolean = true
): Promise<void> {
  try {
    const id = crypto.randomUUID();
    await db
      .prepare(
        `INSERT INTO usage_logs (id, api_key_id, tool, tokens_used, latency_ms, success, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)`
      )
      .bind(
        id,
        apiKeyId,
        tool,
        tokensUsed,
        latencyMs,
        success ? 1 : 0,
        new Date().toISOString()
      )
      .run();
  } catch (err) {
    console.error("Failed to log usage:", err);
  }
}

// Thin wrapper around the shared dispatch — kept named handleToolCall so
// processRequest below doesn't need to change.
async function handleToolCall(
  toolName: string,
  args: Record<string, unknown>,
  env: ToolEnv,
): Promise<ToolResult> {
  return runTool(toolName, args, env);
}

// Process JSON-RPC request with usage logging
async function processRequest(
  request: JsonRpcRequest,
  env: {
    VECTORIZE: VectorizeIndex;
    AI: Ai;
    DB: D1Database;
    OPENROUTER_API_KEY?: string;
  },
  apiKeyId?: string
): Promise<JsonRpcResponse> {
  try {
    switch (request.method) {
      case "initialize":
        return {
          jsonrpc: "2.0",
          id: request.id,
          result: {
            protocolVersion: SERVER_INFO.protocolVersion,
            serverInfo: {
              name: SERVER_INFO.name,
              version: SERVER_INFO.version,
            },
            capabilities: {
              tools: {},
            },
          },
        };

      case "initialized":
        return {
          jsonrpc: "2.0",
          id: request.id,
          result: {},
        };

      case "tools/list":
        return {
          jsonrpc: "2.0",
          id: request.id,
          result: {
            tools: TOOLS,
          },
        };

      case "tools/call": {
        const params = request.params as {
          name: string;
          arguments?: Record<string, unknown>;
        };
        if (!params?.name) {
          return {
            jsonrpc: "2.0",
            id: request.id,
            error: {
              code: -32602,
              message: "Missing tool name",
            },
          };
        }

        const startTime = Date.now();
        let toolResult: ToolResult;

        try {
          toolResult = await handleToolCall(
            params.name,
            params.arguments ?? {},
            env
          );
        } catch (err) {
          const latencyMs = Date.now() - startTime;

          // Log failed call
          if (apiKeyId) {
            await logUsage(env.DB, apiKeyId, params.name, latencyMs, 0, false);
          }

          throw err;
        }

        const latencyMs = Date.now() - startTime;

        // Log successful call
        if (apiKeyId) {
          await logUsage(
            env.DB,
            apiKeyId,
            params.name,
            latencyMs,
            toolResult.tokensUsed || 0,
            true
          );
        }

        return {
          jsonrpc: "2.0",
          id: request.id,
          result: {
            content: [
              {
                type: "text",
                text:
                  typeof toolResult.data === "string"
                    ? toolResult.data
                    : JSON.stringify(toolResult.data, null, 2),
              },
            ],
          },
        };
      }

      case "ping":
        return {
          jsonrpc: "2.0",
          id: request.id,
          result: {},
        };

      default:
        return {
          jsonrpc: "2.0",
          id: request.id,
          error: {
            code: -32601,
            message: `Method not found: ${request.method}`,
          },
        };
    }
  } catch (error) {
    return {
      jsonrpc: "2.0",
      id: request.id,
      error: {
        code: -32603,
        message: error instanceof Error ? error.message : "Internal error",
      },
    };
  }
}

export async function POST(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();

    // Validate API key
    const authResult = await validateApiKey(request, env.DB);
    if (!authResult.valid) {
      return NextResponse.json(
        {
          jsonrpc: "2.0",
          id: null,
          error: {
            code: -32001,
            message: authResult.error,
          },
        },
        { status: 401 }
      );
    }

    // Parse request body
    const body = await request.json();

    const envObj = {
      VECTORIZE: env.VECTORIZE,
      AI: env.AI,
      DB: env.DB,
      OPENROUTER_API_KEY: env.OPENROUTER_API_KEY,
    };

    // Handle single request or batch
    if (Array.isArray(body)) {
      // Batch request
      const responses = await Promise.all(
        body.map((req: JsonRpcRequest) =>
          processRequest(req, envObj, authResult.keyId)
        )
      );
      return NextResponse.json(responses);
    } else {
      // Single request
      const response = await processRequest(
        body as JsonRpcRequest,
        envObj,
        authResult.keyId
      );
      return NextResponse.json(response);
    }
  } catch (error) {
    console.error("MCP endpoint error:", error);
    return NextResponse.json(
      {
        jsonrpc: "2.0",
        id: null,
        error: {
          code: -32700,
          message: "Parse error",
        },
      },
      { status: 400 }
    );
  }
}

// Handle OPTIONS for CORS
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    },
  });
}

// Handle GET for health check
export async function GET() {
  return NextResponse.json({
    name: SERVER_INFO.name,
    version: SERVER_INFO.version,
    status: "ok",
    tools: TOOLS.length,
  });
}

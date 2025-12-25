/**
 * MCP (Model Context Protocol) HTTP Endpoint
 *
 * Implements the MCP protocol over HTTP for mcp-remote clients.
 * Supports the Streamable HTTP transport used by Cursor, Claude Desktop, etc.
 */

import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { getStylusContext } from "@/lib/tools/getStylusContext";
import { askStylus } from "@/lib/tools/askStylus";
import { generateStylusCode } from "@/lib/tools/generateStylusCode";
import { generateTests } from "@/lib/tools/generateTests";
import { getWorkflow } from "@/lib/tools/getWorkflow";

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
];

// Server info for MCP
const SERVER_INFO = {
  name: "arbbuilder",
  version: "1.0.0",
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

// Tool result with optional token tracking
interface ToolResult {
  data: unknown;
  tokensUsed?: number;
}

// Handle tool calls
async function handleToolCall(
  toolName: string,
  args: Record<string, unknown>,
  env: {
    VECTORIZE: VectorizeIndex;
    AI: Ai;
    DB: D1Database;
    OPENROUTER_API_KEY?: string;
  }
): Promise<ToolResult> {
  const { VECTORIZE, AI, OPENROUTER_API_KEY } = env;

  switch (toolName) {
    case "get_stylus_context": {
      const result = await getStylusContext(VECTORIZE, AI, {
        query: args.query as string,
        nResults: (args.nResults as number) ?? 5,
        contentType: (args.contentType as "code" | "documentation" | "all") ?? "all",
        rerank: (args.rerank as boolean) ?? true,
      });
      return { data: result, tokensUsed: 0 };
    }

    case "generate_stylus_code": {
      if (!OPENROUTER_API_KEY) {
        throw new Error("OpenRouter API key not configured");
      }
      const result = await generateStylusCode(VECTORIZE, AI, OPENROUTER_API_KEY, {
        prompt: args.prompt as string,
        contractType:
          (args.contractType as "token" | "nft" | "defi" | "utility" | "custom") ??
          "utility",
        includeTests: (args.includeTests as boolean) ?? false,
      });
      return { data: result, tokensUsed: result.tokensUsed || 0 };
    }

    case "ask_stylus": {
      if (!OPENROUTER_API_KEY) {
        throw new Error("OpenRouter API key not configured");
      }
      const result = await askStylus(VECTORIZE, AI, OPENROUTER_API_KEY, {
        question: args.question as string,
        codeContext: args.codeContext as string | undefined,
        questionType:
          (args.questionType as
            | "general"
            | "debugging"
            | "optimization"
            | "security") ?? "general",
      });
      return { data: result, tokensUsed: result.tokensUsed || 0 };
    }

    case "generate_tests": {
      if (!OPENROUTER_API_KEY) {
        throw new Error("OpenRouter API key not configured");
      }
      const result = await generateTests(OPENROUTER_API_KEY, {
        contractCode: args.contractCode as string,
        testFramework:
          (args.testFramework as "rust_native" | "foundry") ?? "rust_native",
      });
      return { data: result, tokensUsed: result.tokensUsed || 0 };
    }

    case "get_workflow": {
      const result = getWorkflow({
        workflowType: args.workflowType as "build" | "deploy" | "test",
        network:
          (args.network as
            | "arbitrum_sepolia"
            | "arbitrum_one"
            | "arbitrum_nova") ?? "arbitrum_sepolia",
        includeTroubleshooting: (args.includeTroubleshooting as boolean) ?? true,
      });
      return { data: result, tokensUsed: 0 };
    }

    default:
      throw new Error(`Unknown tool: ${toolName}`);
  }
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

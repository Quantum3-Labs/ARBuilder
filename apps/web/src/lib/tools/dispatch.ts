/**
 * Shared tool dispatch — single source of truth for invoking an MCP tool by name.
 * Used by:
 *   - apps/web/src/app/mcp/route.ts (JSON-RPC MCP endpoint)
 *   - apps/web/src/lib/chat/toolDefs.ts (chat ReAct agent)
 */

// M1: Stylus
import { getStylusContext } from "./getStylusContext";
import { askStylus } from "./askStylus";
import { generateStylusCode } from "./generateStylusCode";
import { generateTests } from "./generateTests";
import { getWorkflow } from "./getWorkflow";
// M2: SDK
import { generateBridgeCode } from "./generateBridgeCode";
import { generateMessagingCode } from "./generateMessagingCode";
import { askBridging } from "./askBridging";
// M3: dApp
import { generateBackend } from "./generateBackend";
import { generateFrontend } from "./generateFrontend";
import { generateIndexer } from "./generateIndexer";
import { generateOracle } from "./generateOracle";
import { orchestrateDapp } from "./orchestrateDapp";
// M4: Orbit
import { generateOrbitConfig } from "./generateOrbitConfig";
import { generateOrbitDeployment } from "./generateOrbitDeployment";
import { generateValidatorSetup } from "./generateValidatorSetup";
import { askOrbit } from "./askOrbit";
import { orchestrateOrbit } from "./orchestrateOrbit";

export interface ToolEnv {
  VECTORIZE: VectorizeIndex;
  AI: Ai;
  DB: D1Database;
  OPENROUTER_API_KEY?: string;
}

export interface ToolResult {
  data: unknown;
  tokensUsed?: number;
}

/**
 * The 4 large scaffolders that produce 50–200KB of files.
 * Excluded from the chat agent surface but exposed to /mcp and /api/v1/tools/*.
 */
export const CHAT_EXCLUDED_TOOLS = [
  "generate_backend",
  "generate_frontend",
  "orchestrate_dapp",
  "orchestrate_orbit",
] as const;

export const ALL_TOOL_NAMES = [
  // M1
  "get_stylus_context",
  "generate_stylus_code",
  "ask_stylus",
  "generate_tests",
  "get_workflow",
  // M2
  "generate_bridge_code",
  "generate_messaging_code",
  "ask_bridging",
  // M3
  "generate_backend",
  "generate_frontend",
  "generate_indexer",
  "generate_oracle",
  "orchestrate_dapp",
  // M4
  "generate_orbit_config",
  "generate_orbit_deployment",
  "generate_validator_setup",
  "ask_orbit",
  "orchestrate_orbit",
] as const;

export const CHAT_TOOL_NAMES = ALL_TOOL_NAMES.filter(
  (n) => !CHAT_EXCLUDED_TOOLS.includes(n as (typeof CHAT_EXCLUDED_TOOLS)[number]),
);

export type ToolName = (typeof ALL_TOOL_NAMES)[number];

export async function runTool(
  toolName: string,
  args: Record<string, unknown>,
  env: ToolEnv,
): Promise<ToolResult> {
  const { VECTORIZE, AI, OPENROUTER_API_KEY } = env;
  const requireOpenRouter = () => {
    if (!OPENROUTER_API_KEY) throw new Error("OpenRouter API key not configured");
    return OPENROUTER_API_KEY;
  };

  switch (toolName) {
    case "get_stylus_context": {
      const r = await getStylusContext(VECTORIZE, AI, {
        query: args.query as string,
        nResults: (args.nResults as number) ?? 5,
        contentType: (args.contentType as "code" | "documentation" | "all") ?? "all",
        rerank: (args.rerank as boolean) ?? true,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_stylus_code": {
      const r = await generateStylusCode(VECTORIZE, AI, requireOpenRouter(), {
        prompt: args.prompt as string,
        contractType:
          (args.contractType as "token" | "nft" | "defi" | "utility" | "custom") ?? "utility",
        includeTests: (args.includeTests as boolean) ?? false,
      });
      return { data: r, tokensUsed: r.tokensUsed || 0 };
    }
    case "ask_stylus": {
      const r = await askStylus(VECTORIZE, AI, requireOpenRouter(), {
        question: args.question as string,
        codeContext: args.codeContext as string | undefined,
        questionType:
          (args.questionType as "general" | "debugging" | "optimization" | "security") ??
          "general",
      });
      return { data: r, tokensUsed: r.tokensUsed || 0 };
    }
    case "generate_tests": {
      const r = await generateTests(requireOpenRouter(), {
        contractCode: args.contractCode as string,
        testFramework: (args.testFramework as "rust_native" | "foundry") ?? "rust_native",
      });
      return { data: r, tokensUsed: r.tokensUsed || 0 };
    }
    case "get_workflow": {
      const r = getWorkflow({
        workflowType: args.workflowType as "build" | "deploy" | "test",
        network:
          (args.network as "arbitrum_sepolia" | "arbitrum_one" | "arbitrum_nova") ??
          "arbitrum_sepolia",
        includeTroubleshooting: (args.includeTroubleshooting as boolean) ?? true,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_bridge_code": {
      const r = generateBridgeCode({
        bridgeType: args.bridgeType as
          | "eth_deposit" | "eth_deposit_to" | "eth_withdraw"
          | "erc20_deposit" | "erc20_withdraw" | "eth_l1_l3" | "erc20_l1_l3",
        amount: args.amount as string | undefined,
        tokenAddress: args.tokenAddress as string | undefined,
        destinationAddress: args.destinationAddress as string | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_messaging_code": {
      const r = generateMessagingCode({
        messageType: args.messageType as "l1_to_l2" | "l2_to_l1" | "l2_to_l1_claim" | "check_status",
        includeExample: (args.includeExample as boolean) ?? true,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "ask_bridging": {
      const r = await askBridging(VECTORIZE, AI, requireOpenRouter(), {
        question: args.question as string,
        questionType: (args.questionType as "general" | "bridging" | "messaging" | "l3") ?? "general",
      });
      return { data: r, tokensUsed: r.tokensUsed || 0 };
    }
    case "generate_backend": {
      const r = generateBackend({
        prompt: args.prompt as string,
        framework: (args.framework as "nestjs" | "express") ?? "nestjs",
        contractAbi: args.contractAbi as string | undefined,
        features: args.features as string[] | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_frontend": {
      const r = generateFrontend({
        prompt: args.prompt as string,
        contractAbi: args.contractAbi as string | undefined,
        uiFramework: (args.uiFramework as "daisyui" | "shadcn" | "none") ?? "daisyui",
        template: (args.template as "base" | "dashboard" | "token") ?? "base",
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_indexer": {
      const r = generateIndexer({
        contractAddress: args.contractAddress as string,
        subgraphType: (args.subgraphType as "erc20" | "erc721" | "defi" | "custom") ?? "erc20",
        abi: args.abi as string | undefined,
        events: args.events as string[] | undefined,
        network: args.network as string | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_oracle": {
      const r = generateOracle({
        oracleType: args.oracleType as "price_feed" | "vrf" | "automation" | "functions",
        network: (args.network as "arbitrum-one" | "arbitrum-sepolia") ?? "arbitrum-sepolia",
        feeds: args.feeds as string[] | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "orchestrate_dapp": {
      const r = orchestrateDapp({
        prompt: args.prompt as string,
        components: args.components as ("contract" | "backend" | "frontend" | "indexer" | "oracle")[] | undefined,
        network: (args.network as "arbitrum-sepolia" | "arbitrum-one") ?? "arbitrum-sepolia",
        contractAddress: args.contractAddress as string | undefined,
        contractAbi: args.contractAbi as string | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_orbit_config": {
      const r = generateOrbitConfig({
        prompt: args.prompt as string,
        chainId: args.chainId as number | undefined,
        owner: args.owner as string | undefined,
        isAnyTrust: args.isAnyTrust as boolean | undefined,
        nativeToken: args.nativeToken as string | undefined,
        parentChain: args.parentChain as
          | "arbitrum-one" | "arbitrum-sepolia" | "ethereum-mainnet" | "ethereum-sepolia" | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_orbit_deployment": {
      const r = generateOrbitDeployment({
        prompt: args.prompt as string,
        deploymentType: (args.deploymentType as "rollup" | "token_bridge" | "full") ?? "rollup",
        validators: args.validators as string[] | undefined,
        batchPosters: args.batchPosters as string[] | undefined,
        nativeToken: args.nativeToken as string | undefined,
        parentChain: args.parentChain as
          | "arbitrum-one" | "arbitrum-sepolia" | "ethereum-mainnet" | "ethereum-sepolia" | undefined,
        rollupVersion: (args.rollupVersion as "v2.1" | "v3.1") ?? "v3.1",
        chainId: args.chainId as number | undefined,
        isAnyTrust: args.isAnyTrust as boolean | undefined,
        rollupAddress: args.rollupAddress as string | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "generate_validator_setup": {
      const r = generateValidatorSetup({
        prompt: args.prompt as string,
        action: (args.action as "list" | "add" | "remove") ?? "list",
        target: (args.target as "validator" | "batch_poster" | "keyset") ?? "validator",
        addresses: args.addresses as string[] | undefined,
        rollupAddress: args.rollupAddress as string | undefined,
        sequencerInbox: args.sequencerInbox as string | undefined,
        parentChain: args.parentChain as
          | "arbitrum-one" | "arbitrum-sepolia" | "ethereum-mainnet" | "ethereum-sepolia" | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    case "ask_orbit": {
      const r = await askOrbit(VECTORIZE, AI, requireOpenRouter(), {
        question: args.question as string,
        questionType:
          (args.questionType as "general" | "deployment" | "config" | "validator" | "troubleshooting") ??
          "general",
      });
      return { data: r, tokensUsed: r.tokensUsed || 0 };
    }
    case "orchestrate_orbit": {
      const r = orchestrateOrbit({
        prompt: args.prompt as string,
        chainName: args.chainName as string | undefined,
        chainId: args.chainId as number | undefined,
        isAnyTrust: args.isAnyTrust as boolean | undefined,
        nativeToken: args.nativeToken as string | undefined,
        parentChain: args.parentChain as
          | "arbitrum-one" | "arbitrum-sepolia" | "ethereum-mainnet" | "ethereum-sepolia" | undefined,
        validators: args.validators as string[] | undefined,
        batchPosters: args.batchPosters as string[] | undefined,
      });
      return { data: r, tokensUsed: 0 };
    }
    default:
      throw new Error(`Unknown tool: ${toolName}`);
  }
}

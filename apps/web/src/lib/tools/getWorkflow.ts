/**
 * Get Workflow Tool
 *
 * Returns structured workflow information for build, deploy,
 * and test operations.
 */

import {
  BUILD_WORKFLOW,
  DEPLOY_WORKFLOW,
  TEST_WORKFLOW,
  NETWORK_CONFIGS,
} from "@/data/resources";

export interface GetWorkflowInput {
  workflowType: "build" | "deploy" | "test";
  network?: "arbitrum_sepolia" | "arbitrum_one" | "arbitrum_nova";
  includeTroubleshooting?: boolean;
}

export interface GetWorkflowOutput {
  workflowType: string;
  network?: string;
  workflow: {
    name: string;
    description: string;
    prerequisites?: unknown[];
    steps: unknown[];
    troubleshooting?: unknown;
  };
  targetNetwork?: {
    name: string;
    type: string;
    chainId: number;
    rpcEndpoints: Record<string, string>;
    explorer: Record<string, string>;
  };
  quickCommands?: Record<string, string>;
}

export function getWorkflow(input: GetWorkflowInput): GetWorkflowOutput {
  const {
    workflowType,
    network = "arbitrum_sepolia",
    includeTroubleshooting = true,
  } = input;

  // Get network config
  const networkConfig = NETWORK_CONFIGS.networks[network];

  // Select workflow based on type
  let workflow: {
    name: string;
    description: string;
    prerequisites?: unknown[];
    steps: unknown[];
    troubleshooting?: unknown;
  };

  switch (workflowType) {
    case "build":
      workflow = {
        name: BUILD_WORKFLOW.name,
        description: BUILD_WORKFLOW.description,
        prerequisites: BUILD_WORKFLOW.prerequisites,
        steps: BUILD_WORKFLOW.steps,
      };
      break;

    case "deploy":
      workflow = {
        name: DEPLOY_WORKFLOW.name,
        description: DEPLOY_WORKFLOW.description,
        prerequisites: DEPLOY_WORKFLOW.prerequisites,
        steps: DEPLOY_WORKFLOW.steps,
        troubleshooting: includeTroubleshooting
          ? DEPLOY_WORKFLOW.commonIssues
          : undefined,
      };
      break;

    case "test":
      workflow = {
        name: TEST_WORKFLOW.name,
        description: TEST_WORKFLOW.description,
        steps: TEST_WORKFLOW.steps,
        troubleshooting: includeTroubleshooting
          ? TEST_WORKFLOW.debugging
          : undefined,
      };
      break;

    default:
      throw new Error(`Unknown workflow type: ${workflowType}`);
  }

  // Generate quick commands for deploy workflow
  let quickCommands: Record<string, string> | undefined;
  if (workflowType === "deploy" && networkConfig) {
    const rpcUrl = networkConfig.rpcEndpoints.primary;
    quickCommands = {
      prepare_key: "echo 'YOUR_PRIVATE_KEY' > key.txt && chmod 600 key.txt",
      check_balance: `cast balance YOUR_ADDRESS --rpc-url ${rpcUrl}`,
      estimate_gas: `cargo stylus deploy --estimate-gas --private-key-path=./key.txt --endpoint=${rpcUrl}`,
      deploy: `cargo stylus deploy --private-key-path=./key.txt --endpoint=${rpcUrl}`,
      verify: `cargo stylus verify --deployment-tx TX_HASH --endpoint=${rpcUrl}`,
      call_contract: `cast call CONTRACT_ADDRESS 'functionName()' --rpc-url ${rpcUrl}`,
    };
  }

  return {
    workflowType,
    network: networkConfig?.name,
    workflow,
    targetNetwork: networkConfig
      ? {
          name: networkConfig.name,
          type: networkConfig.type,
          chainId: networkConfig.chainId,
          rpcEndpoints: networkConfig.rpcEndpoints,
          explorer: networkConfig.explorer,
        }
      : undefined,
    quickCommands,
  };
}

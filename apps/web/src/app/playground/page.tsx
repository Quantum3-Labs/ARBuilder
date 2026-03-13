"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

type Tool =
  | "context" | "generate" | "ask" | "tests" | "workflow"
  | "bridge" | "messaging" | "askBridging"
  | "backend" | "frontend" | "indexer" | "oracle" | "orchestrate"
  | "orbitConfig" | "orbitDeploy" | "orbitValidator" | "askOrbit" | "orchestrateOrbit";

interface ToolConfig {
  name: string;
  description: string;
  endpoint: string;
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
  inputs: {
    name: string;
    label: string;
    type: "text" | "textarea" | "select";
    placeholder?: string;
    options?: { value: string; label: string }[];
    required?: boolean;
  }[];
}

const tools: Record<Tool, ToolConfig> = {
  context: {
    name: "Get Stylus Context",
    description: "Search documentation and code examples",
    endpoint: "/api/v1/tools/context",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    ),
    iconBg: "bg-blue-100",
    iconColor: "text-blue-600",
    inputs: [
      {
        name: "query",
        label: "Search Query",
        type: "textarea",
        placeholder: "What are you looking for? e.g., 'How to implement ERC20 in Stylus'",
        required: true,
      },
      {
        name: "nResults",
        label: "Number of Results",
        type: "select",
        options: [
          { value: "5", label: "5 results" },
          { value: "10", label: "10 results" },
          { value: "20", label: "20 results" },
        ],
      },
    ],
  },
  generate: {
    name: "Generate Stylus Code",
    description: "Generate contract code from description",
    endpoint: "/api/v1/tools/generate",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
    ),
    iconBg: "bg-emerald-100",
    iconColor: "text-emerald-600",
    inputs: [
      {
        name: "prompt",
        label: "Contract Description",
        type: "textarea",
        placeholder: "Describe the contract you want to generate...",
        required: true,
      },
      {
        name: "contextQuery",
        label: "Additional Context",
        type: "textarea",
        placeholder: "Additional context or requirements (optional)",
      },
    ],
  },
  ask: {
    name: "Ask Stylus",
    description: "Ask questions about Stylus development",
    endpoint: "/api/v1/tools/ask",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    ),
    iconBg: "bg-violet-100",
    iconColor: "text-violet-600",
    inputs: [
      {
        name: "question",
        label: "Your Question",
        type: "textarea",
        placeholder: "What do you want to know about Stylus?",
        required: true,
      },
    ],
  },
  tests: {
    name: "Generate Tests",
    description: "Generate tests for your contracts",
    endpoint: "/api/v1/tools/tests",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    ),
    iconBg: "bg-amber-100",
    iconColor: "text-amber-600",
    inputs: [
      {
        name: "contractCode",
        label: "Contract Code",
        type: "textarea",
        placeholder: "Paste your Stylus contract code here...",
        required: true,
      },
      {
        name: "testTypes",
        label: "Test Type",
        type: "select",
        options: [
          { value: "unit", label: "Unit Tests" },
          { value: "integration", label: "Integration Tests" },
          { value: "both", label: "Both" },
        ],
      },
    ],
  },
  workflow: {
    name: "Get Workflow",
    description: "Get step-by-step workflow guides",
    endpoint: "/api/v1/tools/workflow",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    ),
    iconBg: "bg-rose-100",
    iconColor: "text-rose-600",
    inputs: [
      {
        name: "workflowType",
        label: "Workflow Type",
        type: "select",
        options: [
          { value: "build", label: "Build" },
          { value: "test", label: "Test" },
          { value: "deploy", label: "Deploy" },
          { value: "verify", label: "Verify" },
        ],
        required: true,
      },
      {
        name: "network",
        label: "Network",
        type: "select",
        options: [
          { value: "arbitrum_sepolia", label: "Arbitrum Sepolia (Testnet)" },
          { value: "arbitrum_one", label: "Arbitrum One (Mainnet)" },
        ],
      },
    ],
  },
  bridge: {
    name: "Generate Bridge Code",
    description: "ETH/ERC20 bridging L1↔L2 and L1→L3",
    endpoint: "/api/v1/tools/bridge",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
    ),
    iconBg: "bg-purple-100",
    iconColor: "text-purple-600",
    inputs: [
      {
        name: "bridgeType",
        label: "Bridge Type",
        type: "select",
        options: [
          { value: "eth_deposit", label: "ETH Deposit (L1→L2)" },
          { value: "eth_withdraw", label: "ETH Withdraw (L2→L1)" },
          { value: "erc20_deposit", label: "ERC20 Deposit (L1→L2)" },
          { value: "erc20_withdraw", label: "ERC20 Withdraw (L2→L1)" },
          { value: "eth_l1_l3", label: "ETH L1→L3" },
          { value: "erc20_l1_l3", label: "ERC20 L1→L3" },
        ],
        required: true,
      },
      {
        name: "amount",
        label: "Amount",
        type: "text",
        placeholder: "e.g., 0.1",
      },
      {
        name: "tokenAddress",
        label: "Token Address (for ERC20)",
        type: "text",
        placeholder: "0x...",
      },
    ],
  },
  messaging: {
    name: "Generate Messaging Code",
    description: "Cross-chain messaging via retryables",
    endpoint: "/api/v1/tools/messaging",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    ),
    iconBg: "bg-cyan-100",
    iconColor: "text-cyan-600",
    inputs: [
      {
        name: "messageType",
        label: "Message Type",
        type: "select",
        options: [
          { value: "l1_to_l2", label: "L1→L2 (Retryable Ticket)" },
          { value: "l2_to_l1", label: "L2→L1 (ArbSys)" },
          { value: "l2_to_l1_claim", label: "L2→L1 Claim" },
          { value: "check_status", label: "Check Status" },
        ],
        required: true,
      },
    ],
  },
  askBridging: {
    name: "Ask Bridging",
    description: "Q&A about bridging patterns and timing",
    endpoint: "/api/v1/tools/ask-bridging",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    ),
    iconBg: "bg-teal-100",
    iconColor: "text-teal-600",
    inputs: [
      {
        name: "question",
        label: "Your Question",
        type: "textarea",
        placeholder: "e.g., How long does an L2→L1 withdrawal take?",
        required: true,
      },
      {
        name: "includeCodeExample",
        label: "Include Code Example",
        type: "select",
        options: [
          { value: "false", label: "No" },
          { value: "true", label: "Yes" },
        ],
      },
    ],
  },
  backend: {
    name: "Generate Backend",
    description: "NestJS/Express backend with viem integration",
    endpoint: "/api/v1/tools/backend",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
    ),
    iconBg: "bg-orange-100",
    iconColor: "text-orange-600",
    inputs: [
      {
        name: "prompt",
        label: "Backend Description",
        type: "textarea",
        placeholder: "Describe the backend you want to generate...",
        required: true,
      },
      {
        name: "framework",
        label: "Framework",
        type: "select",
        options: [
          { value: "nestjs", label: "NestJS" },
          { value: "express", label: "Express" },
        ],
      },
      {
        name: "contractAbi",
        label: "Contract ABI (optional)",
        type: "textarea",
        placeholder: "Paste contract ABI JSON for auto-generated endpoints...",
      },
    ],
  },
  frontend: {
    name: "Generate Frontend",
    description: "Next.js + wagmi + RainbowKit frontend",
    endpoint: "/api/v1/tools/frontend",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    ),
    iconBg: "bg-sky-100",
    iconColor: "text-sky-600",
    inputs: [
      {
        name: "prompt",
        label: "Frontend Description",
        type: "textarea",
        placeholder: "Describe the frontend you want to generate...",
        required: true,
      },
      {
        name: "uiFramework",
        label: "UI Framework",
        type: "select",
        options: [
          { value: "daisyui", label: "DaisyUI (Tailwind)" },
          { value: "shadcn", label: "shadcn/ui" },
          { value: "none", label: "None (plain Tailwind)" },
        ],
      },
      {
        name: "contractAbi",
        label: "Contract ABI (optional)",
        type: "textarea",
        placeholder: "Paste contract ABI JSON for auto-generated hooks...",
      },
    ],
  },
  indexer: {
    name: "Generate Indexer",
    description: "The Graph subgraph for on-chain data",
    endpoint: "/api/v1/tools/indexer",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
    ),
    iconBg: "bg-indigo-100",
    iconColor: "text-indigo-600",
    inputs: [
      {
        name: "contractAddress",
        label: "Contract Address",
        type: "text",
        placeholder: "0x...",
        required: true,
      },
      {
        name: "subgraphType",
        label: "Subgraph Type",
        type: "select",
        options: [
          { value: "erc20", label: "ERC20 Token" },
          { value: "erc721", label: "ERC721 NFT" },
          { value: "defi", label: "DeFi Protocol" },
          { value: "custom", label: "Custom" },
        ],
      },
      {
        name: "network",
        label: "Network",
        type: "select",
        options: [
          { value: "arbitrum-sepolia", label: "Arbitrum Sepolia" },
          { value: "arbitrum-one", label: "Arbitrum One" },
        ],
      },
    ],
  },
  oracle: {
    name: "Generate Oracle",
    description: "Chainlink oracle integrations",
    endpoint: "/api/v1/tools/oracle",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    ),
    iconBg: "bg-yellow-100",
    iconColor: "text-yellow-600",
    inputs: [
      {
        name: "oracleType",
        label: "Oracle Type",
        type: "select",
        options: [
          { value: "price_feed", label: "Price Feed" },
          { value: "vrf", label: "VRF (Random Numbers)" },
          { value: "automation", label: "Automation (Keepers)" },
          { value: "functions", label: "Functions (Off-chain Compute)" },
        ],
        required: true,
      },
      {
        name: "network",
        label: "Network",
        type: "select",
        options: [
          { value: "arbitrum-sepolia", label: "Arbitrum Sepolia" },
          { value: "arbitrum-one", label: "Arbitrum One" },
        ],
      },
    ],
  },
  orchestrate: {
    name: "Orchestrate dApp",
    description: "Full-stack dApp scaffolding",
    endpoint: "/api/v1/tools/orchestrate",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
    ),
    iconBg: "bg-pink-100",
    iconColor: "text-pink-600",
    inputs: [
      {
        name: "prompt",
        label: "dApp Description",
        type: "textarea",
        placeholder: "Describe your full-stack dApp (e.g., 'A token vending machine with admin dashboard')...",
        required: true,
      },
      {
        name: "network",
        label: "Network",
        type: "select",
        options: [
          { value: "arbitrum-sepolia", label: "Arbitrum Sepolia" },
          { value: "arbitrum-one", label: "Arbitrum One" },
        ],
      },
      {
        name: "contractAbi",
        label: "Contract ABI (optional)",
        type: "textarea",
        placeholder: "Paste contract ABI JSON to auto-inject into backend and frontend...",
      },
    ],
  },
  orbitConfig: {
    name: "Orbit Chain Config",
    description: "Generate Orbit L3 chain configuration",
    endpoint: "/api/v1/tools/orbit-config",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    ),
    iconBg: "bg-cyan-100",
    iconColor: "text-cyan-600",
    inputs: [
      {
        name: "prompt",
        label: "Chain Requirements",
        type: "textarea",
        placeholder: "Describe your Orbit chain (e.g., 'Gaming L3 with custom gas token')...",
        required: true,
      },
      {
        name: "chainId",
        label: "Chain ID",
        type: "text",
        placeholder: "412346",
      },
      {
        name: "owner",
        label: "Chain Owner Address",
        type: "text",
        placeholder: "0x...",
      },
      {
        name: "parentChain",
        label: "Parent Chain",
        type: "select",
        options: [
          { value: "arbitrum-sepolia", label: "Arbitrum Sepolia" },
          { value: "arbitrum-one", label: "Arbitrum One" },
          { value: "ethereum-sepolia", label: "Ethereum Sepolia" },
          { value: "ethereum-mainnet", label: "Ethereum Mainnet" },
        ],
      },
    ],
  },
  orbitDeploy: {
    name: "Orbit Deployment",
    description: "Generate rollup and token bridge deployment scripts",
    endpoint: "/api/v1/tools/orbit-deploy",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
    ),
    iconBg: "bg-cyan-100",
    iconColor: "text-cyan-600",
    inputs: [
      {
        name: "prompt",
        label: "Deployment Description",
        type: "textarea",
        placeholder: "Describe your deployment (e.g., 'Deploy AnyTrust chain with custom gas token')...",
        required: true,
      },
      {
        name: "deploymentType",
        label: "Deployment Type",
        type: "select",
        options: [
          { value: "full", label: "Full (Rollup + Token Bridge)" },
          { value: "rollup", label: "Rollup Only" },
          { value: "token_bridge", label: "Token Bridge Only" },
        ],
      },
      {
        name: "parentChain",
        label: "Parent Chain",
        type: "select",
        options: [
          { value: "arbitrum-sepolia", label: "Arbitrum Sepolia" },
          { value: "arbitrum-one", label: "Arbitrum One" },
          { value: "ethereum-sepolia", label: "Ethereum Sepolia" },
        ],
      },
    ],
  },
  orbitValidator: {
    name: "Validator Setup",
    description: "Manage validators and batch posters",
    endpoint: "/api/v1/tools/orbit-validator",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    ),
    iconBg: "bg-cyan-100",
    iconColor: "text-cyan-600",
    inputs: [
      {
        name: "prompt",
        label: "Validator Setup Description",
        type: "textarea",
        placeholder: "Describe what you need (e.g., 'List all validators for my rollup')...",
        required: true,
      },
      {
        name: "action",
        label: "Action",
        type: "select",
        options: [
          { value: "list", label: "List" },
          { value: "add", label: "Add" },
          { value: "remove", label: "Remove" },
        ],
      },
      {
        name: "target",
        label: "Target",
        type: "select",
        options: [
          { value: "validator", label: "Validator" },
          { value: "batch_poster", label: "Batch Poster" },
          { value: "keyset", label: "Keyset (AnyTrust)" },
        ],
      },
    ],
  },
  askOrbit: {
    name: "Ask Orbit",
    description: "Q&A about Orbit chain deployment",
    endpoint: "/api/v1/tools/ask-orbit",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    ),
    iconBg: "bg-cyan-100",
    iconColor: "text-cyan-600",
    inputs: [
      {
        name: "question",
        label: "Your Question",
        type: "textarea",
        placeholder: "Ask about Orbit chains (e.g., 'How do custom gas tokens work?')...",
        required: true,
      },
    ],
  },
  orchestrateOrbit: {
    name: "Orchestrate Orbit Chain",
    description: "Full Orbit chain project scaffold",
    endpoint: "/api/v1/tools/orchestrate-orbit",
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
    ),
    iconBg: "bg-cyan-100",
    iconColor: "text-cyan-600",
    inputs: [
      {
        name: "prompt",
        label: "Chain Description",
        type: "textarea",
        placeholder: "Describe your Orbit chain project (e.g., 'Gaming L3 with custom token on Arbitrum Sepolia')...",
        required: true,
      },
      {
        name: "chainName",
        label: "Chain Name",
        type: "text",
        placeholder: "my-orbit-chain",
      },
      {
        name: "parentChain",
        label: "Parent Chain",
        type: "select",
        options: [
          { value: "arbitrum-sepolia", label: "Arbitrum Sepolia" },
          { value: "arbitrum-one", label: "Arbitrum One" },
          { value: "ethereum-sepolia", label: "Ethereum Sepolia" },
        ],
      },
    ],
  },
};

interface ApiKey {
  id: string;
  keyPrefix: string;
  name: string | null;
  createdAt: string;
  lastUsedAt: string | null;
}

interface SessionUser {
  id: string;
  email: string;
  name?: string | null;
}

type AuthMode = "session" | "apikey";

export default function PlaygroundPage() {
  const [selectedTool, setSelectedTool] = useState<Tool>("context");
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Auth state
  const [sessionUser, setSessionUser] = useState<SessionUser | null>(null);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [userKeys, setUserKeys] = useState<ApiKey[]>([]);
  const [selectedKeyId, setSelectedKeyId] = useState<string>("session");
  const [authMode, setAuthMode] = useState<AuthMode>("session");

  // Check session and fetch keys on mount
  useEffect(() => {
    async function init() {
      try {
        const res = await fetch("/api/auth/session");
        const data = (await res.json()) as { user: SessionUser | null };
        if (data.user) {
          setSessionUser(data.user);
          setAuthMode("session");
          // Fetch user's API keys
          const keysRes = await fetch("/api/keys");
          if (keysRes.ok) {
            const keysData = (await keysRes.json()) as { keys: ApiKey[] };
            setUserKeys(keysData.keys || []);
          }
        } else {
          setAuthMode("apikey");
        }
      } catch {
        setAuthMode("apikey");
      } finally {
        setSessionLoading(false);
      }
    }
    init();
  }, []);

  const currentTool = tools[selectedTool];

  function handleInputChange(name: string, value: string) {
    setInputs((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit() {
    // Determine effective auth: if API key mode with a stored key (no raw value),
    // fall back to session auth since the user is logged in
    const useApiKeyAuth = authMode === "apikey" && apiKey;
    const useSessionAuth = authMode === "session" || (authMode === "apikey" && !apiKey && sessionUser);

    // Block only if truly unauthenticated: no session AND no API key
    if (!useApiKeyAuth && !useSessionAuth) {
      setError("Please enter your API key or sign in");
      return;
    }

    // Check required fields
    for (const input of currentTool.inputs) {
      if (input.required && !inputs[input.name]) {
        setError(`${input.label} is required`);
        return;
      }
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };

      // Use API key auth only if a raw key value is available
      if (useApiKeyAuth) {
        headers["Authorization"] = `Bearer ${apiKey}`;
      }
      // Otherwise session auth: cookies are sent automatically

      const res = await fetch(currentTool.endpoint, {
        method: "POST",
        headers,
        credentials: "include", // Ensure cookies are sent for session auth
        body: JSON.stringify(inputs),
      });

      // Handle auth expiration: try to refresh session and retry once
      if (res.status === 401 && !useApiKeyAuth && sessionUser) {
        // Access token may have expired — try refreshing the session
        const refreshRes = await fetch("/api/auth/session");
        const refreshData = (await refreshRes.json()) as { user: SessionUser | null; refreshed?: boolean };
        if (refreshData.user && refreshData.refreshed) {
          // Session refreshed — retry the request with new cookies
          const retryRes = await fetch(currentTool.endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify(inputs),
          });
          const retryData = (await retryRes.json()) as { error?: string; warning?: string; [key: string]: unknown };
          if (!retryRes.ok) {
            throw new Error(retryData.error || `Request failed (${retryRes.status})`);
          }
          const retryKeys = Object.keys(retryData).filter((k) => k !== "disclaimer" && k !== "warning");
          const retryEmpty = retryKeys.length === 0 || retryKeys.every((k) => {
            const v = retryData[k];
            return v === null || v === undefined || v === "" || (typeof v === "object" && Object.keys(v as object).length === 0);
          });
          if (retryEmpty) {
            setError(retryData.warning as string || "Tool completed but produced no output. Try adjusting your inputs.");
          } else {
            setResult(JSON.stringify(retryData, null, 2));
          }
          return;
        } else {
          // Session truly expired — clear session state
          setSessionUser(null);
          setAuthMode("apikey");
          throw new Error("Session expired. Please sign in again or use an API key.");
        }
      }

      const data = (await res.json()) as { error?: string; warning?: string; [key: string]: unknown };

      if (!res.ok) {
        throw new Error(data.error || `Request failed (${res.status})`);
      }

      // Detect empty or near-empty tool results
      const keys = Object.keys(data).filter((k) => k !== "disclaimer" && k !== "warning");
      const isEmpty = keys.length === 0 || keys.every((k) => {
        const v = data[k];
        return v === null || v === undefined || v === "" || (typeof v === "object" && Object.keys(v as object).length === 0);
      });

      if (isEmpty) {
        setError(data.warning as string || "Tool completed but produced no output. Try adjusting your inputs.");
      } else {
        setResult(JSON.stringify(data, null, 2));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">AR</span>
              </div>
              <span className="text-xl font-bold text-gray-900 hidden sm:block">ARBuilder</span>
            </Link>
            <span className="text-gray-300 hidden sm:block">/</span>
            <span className="text-gray-600 font-medium">Playground</span>
          </div>
          {sessionUser ? (
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-600 hidden sm:block">{sessionUser.email}</span>
              <Link
                href="/dashboard/keys"
                className="text-blue-600 hover:text-blue-700 font-medium transition-colors text-sm"
              >
                Manage Keys
              </Link>
            </div>
          ) : (
            <Link
              href="/login"
              className="text-blue-600 hover:text-blue-700 font-medium transition-colors"
            >
              Sign In
            </Link>
          )}
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Sidebar */}
          <div className="lg:col-span-4 space-y-4">
            {/* Tool Selector */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
              <h2 className="font-semibold text-gray-900 mb-4 px-2">Select Tool</h2>
              <div className="space-y-1">
                {(Object.keys(tools) as Tool[]).map((tool) => (
                  <button
                    key={tool}
                    onClick={() => {
                      setSelectedTool(tool);
                      setInputs({});
                      setResult(null);
                      setError(null);
                    }}
                    className={`w-full text-left px-4 py-3 rounded-xl transition-all ${
                      selectedTool === tool
                        ? "bg-blue-50 border-2 border-blue-200"
                        : "hover:bg-gray-50 border-2 border-transparent"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-9 h-9 ${tools[tool].iconBg} rounded-lg flex items-center justify-center flex-shrink-0`}>
                        <svg className={`w-5 h-5 ${tools[tool].iconColor}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          {tools[tool].icon}
                        </svg>
                      </div>
                      <div>
                        <p className={`font-medium ${selectedTool === tool ? "text-blue-700" : "text-gray-900"}`}>
                          {tools[tool].name}
                        </p>
                        <p className="text-sm text-gray-500 mt-0.5">
                          {tools[tool].description}
                        </p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Authentication */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
              <h2 className="font-semibold text-gray-900 mb-4 px-2">Authentication</h2>
              {sessionLoading ? (
                <div className="flex items-center gap-2 px-2 py-2 text-sm text-gray-500">
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Checking session...
                </div>
              ) : sessionUser ? (
                <div className="space-y-3">
                  {/* Auth mode selector */}
                  <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
                    <button
                      onClick={() => setAuthMode("session")}
                      className={`flex-1 text-xs font-medium py-1.5 rounded-md transition-all ${
                        authMode === "session"
                          ? "bg-white text-gray-900 shadow-sm"
                          : "text-gray-500 hover:text-gray-700"
                      }`}
                    >
                      Session
                    </button>
                    <button
                      onClick={() => setAuthMode("apikey")}
                      className={`flex-1 text-xs font-medium py-1.5 rounded-md transition-all ${
                        authMode === "apikey"
                          ? "bg-white text-gray-900 shadow-sm"
                          : "text-gray-500 hover:text-gray-700"
                      }`}
                    >
                      API Key
                    </button>
                  </div>

                  {authMode === "session" ? (
                    <div className="flex items-center gap-2 px-2 py-2 bg-green-50 border border-green-100 rounded-xl">
                      <svg className="w-4 h-4 text-green-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                      </svg>
                      <span className="text-sm text-green-700">Signed in as {sessionUser.email}</span>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {userKeys.length > 0 ? (
                        <>
                          <select
                            value={selectedKeyId}
                            onChange={(e) => {
                              setSelectedKeyId(e.target.value);
                              if (e.target.value !== "manual") {
                                setApiKey("");
                              }
                            }}
                            className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all bg-white"
                          >
                            {userKeys.map((key) => (
                              <option key={key.id} value={key.id}>
                                {key.name || key.keyPrefix}
                              </option>
                            ))}
                            <option value="manual">Enter key manually...</option>
                          </select>
                          {selectedKeyId === "manual" ? (
                            <input
                              type="password"
                              value={apiKey}
                              onChange={(e) => setApiKey(e.target.value)}
                              placeholder="arb_..."
                              className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                            />
                          ) : (
                            <div className="flex items-center gap-1.5 px-2 py-1.5 bg-blue-50 border border-blue-100 rounded-lg">
                              <svg className="w-3.5 h-3.5 text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              <p className="text-xs text-blue-600">
                                Using your session to authenticate (key selected for tracking).
                              </p>
                            </div>
                          )}
                          <p className="text-xs text-gray-500 px-2">
                            <Link href="/dashboard/keys" className="text-blue-600 hover:text-blue-700">
                              Manage keys
                            </Link>
                          </p>
                        </>
                      ) : (
                        <div className="space-y-2">
                          <input
                            type="password"
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            placeholder="arb_..."
                            className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                          />
                          <p className="text-xs text-gray-500 px-2">
                            No keys yet.{" "}
                            <Link href="/dashboard/keys" className="text-blue-600 hover:text-blue-700">
                              Create one
                            </Link>
                            {" "}or use session mode.
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="px-2 py-3 bg-amber-50 border border-amber-100 rounded-xl">
                    <p className="text-sm text-amber-800 font-medium">Sign in to get started</p>
                    <p className="text-xs text-amber-600 mt-1">
                      Sign in to use the playground with your session, or enter an API key manually.
                    </p>
                  </div>
                  <Link
                    href="/login"
                    className="block w-full text-center bg-blue-600 text-white py-2.5 rounded-xl text-sm font-medium hover:bg-blue-700 transition-all"
                  >
                    Sign In
                  </Link>
                  <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-gray-200" />
                    </div>
                    <div className="relative flex justify-center text-xs">
                      <span className="bg-white px-2 text-gray-500">or use API key</span>
                    </div>
                  </div>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="arb_..."
                    className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Main Panel */}
          <div className="lg:col-span-8">
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
              {/* Tool Header */}
              <div className="px-6 py-5 border-b border-gray-100 flex items-center gap-3">
                <div className={`w-10 h-10 ${currentTool.iconBg} rounded-xl flex items-center justify-center`}>
                  <svg className={`w-5 h-5 ${currentTool.iconColor}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    {currentTool.icon}
                  </svg>
                </div>
                <div>
                  <h2 className="font-semibold text-gray-900">{currentTool.name}</h2>
                  <p className="text-sm text-gray-500">{currentTool.description}</p>
                </div>
              </div>

              {/* Inputs */}
              <div className="p-6 space-y-5">
                {currentTool.inputs.map((input) => (
                  <div key={input.name}>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {input.label}
                      {input.required && (
                        <span className="text-red-500 ml-1">*</span>
                      )}
                    </label>
                    {input.type === "textarea" ? (
                      <textarea
                        value={inputs[input.name] || ""}
                        onChange={(e) => handleInputChange(input.name, e.target.value)}
                        placeholder={input.placeholder}
                        rows={4}
                        className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all resize-none"
                      />
                    ) : input.type === "select" ? (
                      <select
                        value={inputs[input.name] || ""}
                        onChange={(e) => handleInputChange(input.name, e.target.value)}
                        className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all bg-white"
                      >
                        <option value="">Select...</option>
                        {input.options?.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={inputs[input.name] || ""}
                        onChange={(e) => handleInputChange(input.name, e.target.value)}
                        placeholder={input.placeholder}
                        className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                      />
                    )}
                  </div>
                ))}

                <button
                  onClick={handleSubmit}
                  disabled={loading}
                  className="w-full bg-blue-600 text-white py-3.5 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 hover:shadow-lg hover:shadow-blue-600/25"
                >
                  {loading ? (
                    <>
                      <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Running...
                    </>
                  ) : (
                    <>
                      Run Tool
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                      </svg>
                    </>
                  )}
                </button>
              </div>

              {/* Error */}
              {error && (
                <div className="mx-6 mb-6 bg-red-50 border border-red-100 text-red-700 px-4 py-3 rounded-xl flex items-center gap-2 animate-fade-in">
                  <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {error}
                </div>
              )}

              {/* Result */}
              {result && (
                <div className="border-t border-gray-100 p-6 animate-fade-in">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-gray-900">Result</h3>
                    <button
                      onClick={() => navigator.clipboard.writeText(result)}
                      className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1.5 transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                      </svg>
                      Copy
                    </button>
                  </div>
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-xl overflow-x-auto text-sm max-h-96 overflow-y-auto shadow-lg">
                    <code>{result}</code>
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

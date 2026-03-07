/**
 * Orchestrate Orbit Tool (M4 tool)
 *
 * Scaffolds a complete Orbit chain deployment project by combining
 * outputs from configuration, deployment, and validator management tools.
 */

import {
  ORBIT_DEPENDENCIES,
  PARENT_CHAIN_RPCS,
  PARENT_CHAIN_IDS,
  TEMPLATE_DISCLAIMER,
} from "./generateOrbitConfig";
import { generateOrbitConfig } from "./generateOrbitConfig";
import { generateOrbitDeployment } from "./generateOrbitDeployment";
import { generateValidatorSetup } from "./generateValidatorSetup";

// Types
type ParentChain =
  | "arbitrum-one"
  | "arbitrum-sepolia"
  | "ethereum-mainnet"
  | "ethereum-sepolia";

interface OrchestrateOrbitInput {
  prompt: string;
  chainName?: string;
  chainId?: number;
  isAnyTrust?: boolean;
  nativeToken?: string;
  parentChain?: ParentChain;
  validators?: string[];
  batchPosters?: string[];
}

interface OrchestrateOrbitOutput {
  name: string;
  description: string;
  files: Record<string, string>;
  projectStructure: Record<string, string[]>;
  dependencies: Record<string, string>;
  chainConfig: {
    chainId: number;
    chainName: string;
    isAnyTrust: boolean;
    nativeToken: string | undefined;
    parentChain: string;
    parentChainId: number;
    parentRpc: string;
  };
  validators: string[];
  batchPosters: string[];
  setupInstructions: string[];
  developmentWorkflow: {
    steps: Array<{
      step: number;
      component: string;
      actions: string[];
    }>;
    tips: string[];
  };
  disclaimer: string;
}

// --- Scaffold templates ---

function generatePackageJson(chainName: string): string {
  return `{
  "name": "${chainName}",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "setup": "bash setup.sh",
    "deploy:rollup": "npx tsx scripts/deploy-rollup.ts",
    "deploy:token-bridge": "npx tsx scripts/deploy-token-bridge.ts",
    "config:chain": "npx tsx scripts/prepare-chain-config.ts",
    "config:node": "npx tsx scripts/prepare-node-config.ts",
    "manage:validators": "npx tsx scripts/manage-validators.ts",
    "deploy": "bash deploy.sh"
  },
  "dependencies": {
    "@arbitrum/chain-sdk": "^0.25.0",
    "viem": "^1.20.0",
    "dotenv": "^16.4.0"
  },
  "devDependencies": {
    "tsx": "^4.7.0",
    "typescript": "^5.3.0",
    "@types/node": "^20.0.0"
  }
}
`;
}

function generateTsconfig(): string {
  return `{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "strict": true,
    "outDir": "dist",
    "rootDir": "scripts",
    "resolveJsonModule": true,
    "declaration": true,
    "skipLibCheck": true
  },
  "include": ["scripts/**/*.ts"],
  "exclude": ["node_modules", "dist"]
}
`;
}

function generateEnvExample(parentRpc: string, chainId: number, chainName: string, isAnyTrust: boolean, nativeToken?: string): string {
  let env = `# Deployer private key (with 0x prefix)
DEPLOYER_PRIVATE_KEY=0x...

# Separate keys for batch poster and validator (recommended for production)
# If not set, DEPLOYER_PRIVATE_KEY is used for both
# IMPORTANT: Uncomment ONLY if you have separate keys — placeholder values
# will override the DEPLOYER_PRIVATE_KEY fallback and cause errors
# BATCH_POSTER_PRIVATE_KEY=0x...
# VALIDATOR_PRIVATE_KEY=0x...

# Parent chain RPC URL
# Ethereum Sepolia: https://rpc.sepolia.org
# Arbitrum Sepolia: https://sepolia-rollup.arbitrum.io/rpc
# Ethereum Mainnet: https://eth.llamarpc.com
# Arbitrum One: https://arb1.arbitrum.io/rpc
PARENT_CHAIN_RPC=${parentRpc}

# Orbit chain RPC (after deployment)
ORBIT_CHAIN_RPC=http://localhost:8449

# Chain configuration
CHAIN_ID=${chainId}
CHAIN_NAME=${chainName}
`;

  if (nativeToken) {
    env += `
# Custom gas token (ERC-20 address on parent chain)
# Deploy your own ERC-20 or use an existing one
NATIVE_TOKEN=${nativeToken}
`;
  }

  if (isAnyTrust) {
    env += `
# DAS (Data Availability Server) — required for AnyTrust chains
DAS_SERVER_URL=http://localhost:9877
`;
  }

  return env;
}

function generateSetupSh(): string {
  return `#!/usr/bin/env bash
set -euo pipefail

echo "=== Orbit Chain Setup ==="

# Install dependencies
echo "Installing dependencies..."
npm install

# Create data directories for Docker bind mounts
mkdir -p data/arbitrum data/das

# Copy env template if .env doesn't exist
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from template - edit it with your keys before deploying."
fi

echo ""
echo "Setup complete!"
echo "Next steps:"
echo "  1. Edit .env with your DEPLOYER_PRIVATE_KEY and PARENT_CHAIN_RPC"
echo "  2. Run: npm run config:chain   (prepare chain config)"
echo "  3. Run: npm run deploy:rollup  (deploy rollup contracts)"
echo "  4. Run: npm run config:node    (generate node config)"
echo "  5. Run: docker-compose up -d   (start Nitro node)"
echo "  6. Run: npm run deploy:token-bridge (deploy token bridge)"
`;
}

function generateDeploySh(): string {
  return `#!/usr/bin/env bash
set -euo pipefail

# Load environment variables
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

echo "=== Orbit Chain Full Deployment ==="

echo ""
echo "Step 1: Prepare chain config..."
npx tsx scripts/prepare-chain-config.ts

echo ""
echo "Step 2: Deploy rollup contracts..."
npx tsx scripts/deploy-rollup.ts

if [ ! -f deployment.json ]; then
  echo "ERROR: deployment.json not created. Rollup deployment may have failed."
  exit 1
fi

echo ""
echo "Step 3: Generate node config..."
npx tsx scripts/prepare-node-config.ts

echo ""
echo "Step 4: Start node (manual step)..."
echo "  Run: docker-compose up -d"
echo "  Wait for the node to sync, then continue with token bridge deployment."
echo "  Press ENTER to continue when the node is ready, or Ctrl+C to stop."
read -r

echo ""
echo "Step 5: Deploy token bridge..."
npx tsx scripts/deploy-token-bridge.ts

echo ""
echo "=== Deployment complete! ==="
echo "Deployment output saved to deployment.json"
echo "Node config saved to nodeConfig.json"
`;
}

function generateDockerCompose(
  chainName: string,
  chainId: number,
  parentChainId: number,
  isAnyTrust: boolean
): string {
  // Use a specific known-good Nitro image tag
  const nitroImage = 'offchainlabs/nitro-node:v3.9.7-75e084e';

  let compose = `version: '3.8'

services:
  nitro-node:
    image: ${nitroImage}
    container_name: ${chainName}-node
    restart: unless-stopped
    ports:
      - "8449:8449"   # L3 RPC
      - "8548:8548"   # L3 WebSocket
      - "9642:9642"   # Metrics
    volumes:
      - ./nodeConfig.json:/config/nodeConfig.json
      - ./data/arbitrum:/home/user/.arbitrum
    command:
      - --conf.file=/config/nodeConfig.json
      - --node.dangerous.no-sequencer-coordinator
      - --validation.wasm.allowed-wasm-module-roots=/home/user/nitro-legacy/machines,/home/user/target/machines
      # Do NOT use --init.dev-init — that flag is for local devnodes only, not Orbit chains
    environment:
      - NITRO_NODE_CONFIG=/config/nodeConfig.json
`;

  if (isAnyTrust) {
    compose += `
  # Generate BLS keys for DAC members before starting:
  #   docker run --rm -v $(pwd)/das-keys:/keys ${nitroImage} datool keygen --dir /keys
  das-server:
    image: ${nitroImage}
    container_name: ${chainName}-das
    restart: unless-stopped
    ports:
      - "9877:9877"   # DAS REST API
    volumes:
      - ./data/das:/home/user/das-data
    entrypoint: /usr/local/bin/daserver
    command:
      - --data-availability.local-file-storage.enable
      - --data-availability.local-file-storage.data-dir=/home/user/das-data
      - --enable-rest
      - --rest-addr=0.0.0.0
      - --rest-port=9877
      - --log-level=3
`;
  }

  compose += `
# Using bind mounts (./data/) instead of named volumes for easier inspection.
# Create data directories before starting: mkdir -p data/arbitrum${isAnyTrust ? ' data/das' : ''}
`;

  return compose;
}

function generateNodeConfigScript(
  chainId: number,
  chainName: string,
  parentChainId: number,
  parentChainName: string,
  isAnyTrust: boolean = false
): string {
  // Determine if parent is an Arbitrum chain (L2 → L3)
  const parentIsArbitrum = parentChainId === 42161 || parentChainId === 421614;
  const dasLine = isAnyTrust ? `\n    dasServerUrl: process.env.DAS_SERVER_URL ?? 'http://localhost:9877',` : '';

  return `import 'dotenv/config';
import * as fs from 'fs';
import { prepareNodeConfig } from '@arbitrum/chain-sdk';
import { zeroAddress } from 'viem';

/**
 * Generate Nitro node configuration from deployment output.
 *
 * Reads deployment.json (created by deploy-rollup.ts) and generates
 * the nodeConfig.json required by the Nitro node.
 *
 * prepareNodeConfig() requires:
 *   - chainConfig (JSON from prepareChainConfig)
 *   - coreContracts (from createRollup output)
 *   - batchPosterPrivateKey (WITHOUT 0x prefix — Nitro expects raw hex)
 *   - validatorPrivateKey (WITHOUT 0x prefix)
 *   - stakeToken (zeroAddress for ETH)
 *   - parentChainId, parentChainRpcUrl
 */
async function main() {
  // Read deployment output
  if (!fs.existsSync('deployment.json')) {
    console.error('Error: deployment.json not found.');
    console.error('Run deploy-rollup.ts first to create it.');
    process.exit(1);
  }

  const deployment = JSON.parse(fs.readFileSync('deployment.json', 'utf-8'));
  console.log('Loaded deployment.json');
  console.log('  Chain ID:', deployment.chainId);
  console.log('  Rollup:', deployment.coreContracts.rollup);

  // Private keys for batch poster and validator (strip 0x prefix for Nitro)
  // IMPORTANT: Only use env vars that are actually set (not placeholder "0x...")
  function resolveKey(envName: string): string {
    const val = process.env[envName];
    if (val && val.length > 10) return val.replace(/^0x/, '');
    return process.env.DEPLOYER_PRIVATE_KEY!.replace(/^0x/, '');
  }
  const batchPosterKey = resolveKey('BATCH_POSTER_PRIVATE_KEY');
  const validatorKey = resolveKey('VALIDATOR_PRIVATE_KEY');

  // Generate node configuration using the actual SDK API
  const nodeConfig = prepareNodeConfig({
    chainName: '${chainName}',
    chainConfig: deployment.chainConfig,
    coreContracts: deployment.coreContracts,
    batchPosterPrivateKey: batchPosterKey,
    validatorPrivateKey: validatorKey,
    stakeToken: zeroAddress,
    parentChainId: ${parentChainId},
    parentChainIsArbitrum: ${parentIsArbitrum},
    parentChainRpcUrl: process.env.PARENT_CHAIN_RPC!,${dasLine}
  });

  // --- Post-process nodeConfig ---

  // 1. prepareNodeConfig() masks private keys with "..." — restore actual keys
  function deepSet(obj: any, path: string[], val: string | boolean) {
    let current = obj;
    for (let i = 0; i < path.length - 1; i++) {
      if (!current?.[path[i]]) return;
      current = current[path[i]];
    }
    if (current) current[path[path.length - 1]] = val;
  }
  deepSet(nodeConfig, ['node', 'batch-poster', 'parent-chain-wallet', 'private-key'], batchPosterKey);
  deepSet(nodeConfig, ['node', 'staker', 'parent-chain-wallet', 'private-key'], validatorKey);

  // 2. Nitro v3.9+ rejects same address for batch poster and staker.
  //    For single-key testnet setups, disable the staker to avoid startup error.
  if (batchPosterKey === validatorKey) {
    console.warn('Warning: Batch poster and staker share the same key.');
    console.warn('  Disabling staker (set separate BATCH_POSTER_PRIVATE_KEY and VALIDATOR_PRIVATE_KEY for production).');
    deepSet(nodeConfig, ['node', 'staker', 'enable'], false);
  }

  // 3. Fix malformed DAS URLs — SDK may produce double-port like http://host:9877:9877
  let configJson = JSON.stringify(nodeConfig, null, 2);
  configJson = configJson.replace(/:(\\d+):\\1/g, ':$1');

  console.log('\\nNode Configuration:');
  console.log(configJson);

  fs.writeFileSync('nodeConfig.json', configJson);
  console.log('\\nSaved to nodeConfig.json');
  console.log('\\nNext steps:');
  console.log('  1. Create data directory: mkdir -p data/arbitrum');
  console.log('  2. Start Nitro node: docker-compose up -d');
}

main().catch(console.error);
`;
}

function generateReadme(
  chainName: string,
  chainId: number,
  isAnyTrust: boolean,
  nativeToken: string | undefined,
  parentChain: string
): string {
  const chainType = isAnyTrust ? "AnyTrust" : "Rollup";
  const gasToken = nativeToken ? `Custom (${nativeToken})` : "ETH";

  return `# ${chainName.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}

> Orbit ${chainType} chain deployment project

## Configuration

| Parameter | Value |
|-----------|-------|
| Chain ID | ${chainId} |
| Chain Type | ${chainType} |
| Gas Token | ${gasToken} |
| Parent Chain | ${parentChain} |

## Quick Start

\`\`\`bash
# 1. Install dependencies
bash setup.sh

# 2. Configure environment
# Edit .env with your DEPLOYER_PRIVATE_KEY and other settings

# 3. Deploy everything
bash deploy.sh
\`\`\`

## Step-by-Step Deployment

\`\`\`bash
# 1. Prepare chain configuration
npm run config:chain

# 2. Deploy rollup contracts (saves to deployment.json)
npm run deploy:rollup

# 3. Generate node config (reads deployment.json)
npm run config:node

# 4. Start Nitro node
docker-compose up -d

# 5. Deploy token bridge (reads deployment.json for rollup address)
npm run deploy:token-bridge

# 6. Manage validators
npm run manage:validators
\`\`\`

## Deployment Output

All deployment data is persisted to \`deployment.json\`. Downstream scripts
(token bridge, node config) automatically read from this file — no need
to copy-paste contract addresses between steps.

## Project Structure

\`\`\`
${chainName}/
  scripts/
    prepare-chain-config.ts   # Chain configuration
    deploy-rollup.ts          # Rollup deployment → deployment.json
    deploy-token-bridge.ts    # Token bridge (reads deployment.json)
    manage-validators.ts      # Validator/batch poster management
    prepare-node-config.ts    # Node config (reads deployment.json)
  docker-compose.yml          # Nitro node (+ DAS for AnyTrust)
  package.json
  tsconfig.json
  .env.example
  setup.sh
  deploy.sh
\`\`\`

## References

- [Orbit Chain Documentation](https://docs.arbitrum.io/launch-orbit-chain/orbit-gentle-introduction)
- [Orbit SDK Reference](https://github.com/OffchainLabs/arbitrum-orbit-sdk)
- [Nitro Node Setup](https://docs.arbitrum.io/run-arbitrum-node/run-full-node)

---
Built with [ARBuilder](https://github.com/arbbuilder)
`;
}

function generateDevelopmentWorkflow(isAnyTrust: boolean) {
  const steps = [
    {
      step: 1,
      component: "Chain Configuration",
      actions: [
        "Run setup.sh to install dependencies",
        "Edit .env with deployer key and parent chain RPC",
        "Run npm run config:chain to prepare configuration",
      ],
    },
    {
      step: 2,
      component: "Rollup Deployment",
      actions: [
        "Run npm run deploy:rollup",
        "Save all contract addresses from output",
        "Fund the rollup contracts if needed",
      ],
    },
    {
      step: 3,
      component: "Node Setup",
      actions: [
        "Run npm run config:node to generate nodeConfig.json (reads deployment.json)",
        "Start Nitro node: docker-compose up -d",
        "Verify node is syncing: curl http://localhost:8449 -X POST -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"eth_chainId\",\"params\":[],\"id\":1}'",
      ],
    },
    {
      step: 4,
      component: "Token Bridge",
      actions: [
        "Update ORBIT_CHAIN_RPC in .env",
        "Run npm run deploy:token-bridge",
        "Verify bridge contracts on both chains",
      ],
    },
  ];

  if (isAnyTrust) {
    steps.push({
      step: 5,
      component: "AnyTrust DAC Setup",
      actions: [
        "Generate BLS keys: docker run --rm -v $(pwd)/das-keys:/keys offchainlabs/nitro-node:v3.9.7-75e084e datool keygen --dir /keys",
        "Configure DAC member BLS keys in the keyset script",
        "Run npm run configure:anytrust",
        "Verify keyset is active on SequencerInbox",
      ],
    });
  }

  return {
    steps,
    tips: [
      "Deploy to testnet (Arbitrum Sepolia) before mainnet",
      "Ensure deployer has sufficient ETH on parent chain",
      "Save all deployment output - contract addresses are needed for node config",
      "Use a multi-sig for chain owner in production",
      "Monitor validator and batch poster uptime",
    ],
  };
}

function generateTestTokenSol(chainName: string): string {
  const tokenName = chainName
    .replace(/-/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\s+/g, "");
  return `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * Minimal ERC-20 for testing as a custom gas token on an Orbit chain.
 *
 * Deploy with Foundry:
 *   forge create contracts/TestToken.sol:${tokenName}Token \\
 *     --rpc-url $PARENT_CHAIN_RPC \\
 *     --private-key $DEPLOYER_PRIVATE_KEY \\
 *     --constructor-args "$(cast address $DEPLOYER_PRIVATE_KEY)"
 *
 * Or use the deploy script:
 *   bash scripts/deploy-test-token.sh
 */
contract ${tokenName}Token is ERC20 {
    constructor(address initialHolder) ERC20("${tokenName} Gas Token", "${tokenName.substring(0, 4).toUpperCase()}") {
        // Mint 1 billion tokens to the deployer for testing
        _mint(initialHolder, 1_000_000_000 * 10 ** decimals());
    }
}
`;
}

function generateDeployTokenSh(): string {
  return `#!/usr/bin/env bash
set -euo pipefail

# Load environment variables
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

echo "=== Deploy Test ERC-20 Gas Token ==="

# Check for Foundry
if ! command -v forge &> /dev/null; then
  echo "Error: Foundry not installed."
  echo "Install: curl -L https://foundry.paradigm.xyz | bash && foundryup"
  exit 1
fi

# Install OpenZeppelin (if not already)
if [ ! -d "lib/openzeppelin-contracts" ]; then
  echo "Installing OpenZeppelin contracts..."
  forge install OpenZeppelin/openzeppelin-contracts --no-commit
fi

# Get deployer address from private key
DEPLOYER_ADDRESS=$(cast wallet address "$DEPLOYER_PRIVATE_KEY")

echo "Deploying test token..."
echo "  Deployer: $DEPLOYER_ADDRESS"
echo "  RPC: $PARENT_CHAIN_RPC"

# Deploy
DEPLOY_OUTPUT=$(forge create contracts/TestToken.sol:*Token \\
  --rpc-url "$PARENT_CHAIN_RPC" \\
  --private-key "$DEPLOYER_PRIVATE_KEY" \\
  --constructor-args "$DEPLOYER_ADDRESS" \\
  --json)

TOKEN_ADDRESS=$(echo "$DEPLOY_OUTPUT" | jq -r '.deployedTo')

echo ""
echo "Token deployed!"
echo "  Address: $TOKEN_ADDRESS"
echo ""
echo "Add to your .env:"
echo "  NATIVE_TOKEN=$TOKEN_ADDRESS"
echo ""
echo "Next steps:"
echo "  1. Set NATIVE_TOKEN=$TOKEN_ADDRESS in .env"
echo "  2. Run: npx tsx scripts/approve-token.ts"
echo "  3. Run: npm run deploy:rollup"
`;
}

/**
 * Orchestrate generation of a complete Orbit chain deployment project.
 *
 * Combines chain configuration, rollup deployment, token bridge deployment,
 * validator management, and node configuration scripts into a single project
 * scaffold with package.json, setup scripts, and documentation.
 */
export function orchestrateOrbit(
  input: OrchestrateOrbitInput
): OrchestrateOrbitOutput {
  const {
    prompt,
    chainName = "my-orbit-chain",
    chainId = 412346,
    isAnyTrust = false,
    nativeToken,
    parentChain = "arbitrum-sepolia",
    validators = [],
    batchPosters = [],
  } = input;

  // Get parent chain info
  const parentRpc = PARENT_CHAIN_RPCS[parentChain] ?? PARENT_CHAIN_RPCS["arbitrum-sepolia"];
  const parentChainId = PARENT_CHAIN_IDS[parentChain] ?? 421614;
  const parentChainName = parentChain.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  // Collect all files
  const files: Record<string, string> = {};

  // 1. Chain config script
  const configResult = generateOrbitConfig({
    prompt: "prepare chain config",
    chainId,
    owner: "0x0000000000000000000000000000000000000000",
    isAnyTrust,
    parentChain,
  });
  const configFile = Object.entries(configResult.files).find(([k]) =>
    k.startsWith("scripts/")
  );
  if (configFile) {
    files["scripts/prepare-chain-config.ts"] = configFile[1];
  }

  // 2. Deploy rollup script (+ token approval if custom gas token)
  const deployResult = generateOrbitDeployment({
    prompt: "deploy rollup",
    deploymentType: "rollup",
    chainId,
    isAnyTrust,
    validators,
    batchPosters,
    nativeToken,
    parentChain,
  });
  if (deployResult.files["scripts/deploy-rollup.ts"]) {
    files["scripts/deploy-rollup.ts"] = deployResult.files["scripts/deploy-rollup.ts"];
  }
  if (deployResult.files["scripts/approve-token.ts"]) {
    files["scripts/approve-token.ts"] = deployResult.files["scripts/approve-token.ts"];
  }

  // 3. Token bridge script
  const bridgeResult = generateOrbitDeployment({
    prompt: "deploy token bridge",
    deploymentType: "token_bridge",
    chainId,
    parentChain,
    rollupAddress: "0x0000000000000000000000000000000000000000",
  });
  if (bridgeResult.files["scripts/deploy-token-bridge.ts"]) {
    files["scripts/deploy-token-bridge.ts"] =
      bridgeResult.files["scripts/deploy-token-bridge.ts"];
  }

  // 4. Validator management script
  const validatorResult = generateValidatorSetup({
    prompt: "manage validators",
    action: "list",
    target: "validator",
    addresses: validators,
    parentChain,
  });
  if (validatorResult.files["scripts/manage-validators.ts"]) {
    files["scripts/manage-validators.ts"] =
      validatorResult.files["scripts/manage-validators.ts"];
  }

  // 5. Node config script
  files["scripts/prepare-node-config.ts"] = generateNodeConfigScript(
    chainId,
    chainName,
    parentChainId,
    parentChainName,
    isAnyTrust
  );

  // 6. AnyTrust keyset config (if applicable)
  if (isAnyTrust) {
    const keysetResult = generateValidatorSetup({
      prompt: "manage keyset",
      target: "keyset",
      parentChain,
    });
    if (keysetResult.files["scripts/manage-keyset.ts"]) {
      files["scripts/configure-anytrust.ts"] =
        keysetResult.files["scripts/manage-keyset.ts"];
    }
  }

  // 6b. ERC-20 test token for custom gas token chains
  if (nativeToken) {
    files["contracts/TestToken.sol"] = generateTestTokenSol(chainName);
    files["scripts/deploy-test-token.sh"] = generateDeployTokenSh();
  }

  // 7. Scaffold files
  files["package.json"] = generatePackageJson(chainName);
  files["tsconfig.json"] = generateTsconfig();
  files[".env.example"] = generateEnvExample(parentRpc, chainId, chainName, isAnyTrust, nativeToken);
  files["setup.sh"] = generateSetupSh();
  files["deploy.sh"] = generateDeploySh();

  // 8. Docker compose
  files["docker-compose.yml"] = generateDockerCompose(
    chainName,
    chainId,
    parentChainId,
    isAnyTrust
  );

  // 9. README
  files["README.md"] = generateReadme(
    chainName,
    chainId,
    isAnyTrust,
    nativeToken,
    parentChain
  );

  // Build project structure description
  const projectStructure: Record<string, string[]> = {
    "scripts/": [
      "prepare-chain-config.ts",
      "deploy-rollup.ts",
      "deploy-token-bridge.ts",
      "manage-validators.ts",
      "prepare-node-config.ts",
    ],
    root: [
      "package.json",
      "tsconfig.json",
      ".env.example",
      "setup.sh",
      "deploy.sh",
      "docker-compose.yml",
      "README.md",
    ],
  };
  if (nativeToken) {
    projectStructure["scripts/"].push("approve-token.ts");
    projectStructure["scripts/"].push("deploy-test-token.sh");
    projectStructure["contracts/"] = ["TestToken.sol"];
  }
  if (isAnyTrust) {
    projectStructure["scripts/"].push("configure-anytrust.ts");
  }

  return {
    name: chainName,
    description: prompt,
    files,
    projectStructure,
    dependencies: ORBIT_DEPENDENCIES,
    chainConfig: {
      chainId,
      chainName,
      isAnyTrust,
      nativeToken,
      parentChain,
      parentChainId,
      parentRpc,
    },
    validators,
    batchPosters,
    setupInstructions: nativeToken
      ? [
          "1. Run: bash setup.sh",
          "2. Edit .env with DEPLOYER_PRIVATE_KEY, NATIVE_TOKEN, and optionally separate BATCH_POSTER/VALIDATOR keys",
          "3. Deploy or obtain your ERC-20 gas token on the parent chain",
          "4. Run: npx tsx scripts/approve-token.ts (approve token for RollupCreator)",
          "5. Run: npm run config:chain",
          "6. Run: npm run deploy:rollup (output saved to deployment.json)",
          "7. Run: npm run config:node (reads deployment.json)",
          "8. Start Nitro node: docker-compose up -d",
          "9. Run: npm run deploy:token-bridge (reads deployment.json)",
        ]
      : [
          "1. Run: bash setup.sh",
          "2. Edit .env with DEPLOYER_PRIVATE_KEY (and optionally separate BATCH_POSTER/VALIDATOR keys)",
          "3. Run: npm run config:chain",
          "4. Run: npm run deploy:rollup (output saved to deployment.json)",
          "5. Run: npm run config:node (reads deployment.json)",
          "6. Start Nitro node: docker-compose up -d",
          "7. Run: npm run deploy:token-bridge (reads deployment.json)",
        ],
    developmentWorkflow: generateDevelopmentWorkflow(isAnyTrust),
    disclaimer: TEMPLATE_DISCLAIMER,
  };
}

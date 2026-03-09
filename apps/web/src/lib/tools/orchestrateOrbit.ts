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

function generatePackageJson(chainName: string, isAnyTrust: boolean): string {
  const anytrustScripts = isAnyTrust ? `
    "generate:das-keys": "bash scripts/generate-das-keys.sh",
    "configure:anytrust": "npx tsx scripts/configure-anytrust.ts",` : '';
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
    "manage:governance": "npx tsx scripts/manage-governance.ts",
    "test:chain": "npx tsx scripts/test-chain.ts",${anytrustScripts}
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
# In Docker Compose, use the service name: http://das-server:9877
DAS_SERVER_URL=http://das-server:9877

# SequencerInbox address (from deployment.json, needed by DAS server)
# Set after running deploy-rollup.ts
SEQUENCER_INBOX_ADDRESS=0x0000000000000000000000000000000000000000
`;
  }

  return env;
}

function generateSetupSh(isAnyTrust: boolean): string {
  const dirs = isAnyTrust ? 'data/arbitrum data/das das-keys' : 'data/arbitrum';
  return `#!/usr/bin/env bash
set -euo pipefail

echo "=== Orbit Chain Setup ==="

# Install dependencies
echo "Installing dependencies..."
npm install

# Create data directories for Docker bind mounts
mkdir -p ${dirs}

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
  const nitroImage = 'offchainlabs/nitro-node:v3.9.4-7f582c3';
  // DAS URL: use Docker service name for inter-container communication
  const dasUrl = isAnyTrust ? 'http://das-server:9877' : '';

  let compose = `services:
  nitro-node:
    image: ${nitroImage}
    container_name: ${chainName}-node
    restart: unless-stopped
    ports:
      - "8449:8449"   # L3 RPC (HTTP)
      - "8548:8548"   # L3 WebSocket
      - "9642:9642"   # Metrics
    volumes:
      - ./nodeConfig.json:/config/nodeConfig.json:ro
      - ./data/arbitrum:/home/user/.arbitrum
    entrypoint: /bin/bash
    command:
      - -c
      - |
        # Clean stale WASM files that cause checkEmptyDatabaseDir crash-loops
        rm -rf /home/user/.arbitrum/*/nitro/wasm
        exec /usr/local/bin/nitro \\
          --conf.file=/config/nodeConfig.json \\
          --node.dangerous.no-sequencer-coordinator \\
          --validation.wasm.allowed-wasm-module-roots=/home/user/nitro-legacy/machines,/home/user/target/machines \\
          --http.addr=0.0.0.0 \\
          --http.port=8449 \\
          --http.vhosts=* \\
          --http.corsdomain=* \\
          --http.api=net,web3,eth,debug,txpool,arb \\
          --ws.addr=0.0.0.0 \\
          --ws.port=8548 \\
          --ws.origins=* \\
          --ws.api=net,web3,eth,debug,txpool,arb \\
          --metrics \\
          --metrics-server.addr=0.0.0.0 \\
          --metrics-server.port=9642
    # Do NOT use --init.dev-init — that flag is for local devnodes only, not Orbit chains
    environment:
      - NITRO_NODE_CONFIG=/config/nodeConfig.json
`;

  if (isAnyTrust) {
    compose += `
    depends_on:
      das-server:
        condition: service_started

  # DAS (Data Availability Server) — must be running before nitro-node starts batch posting
  # Generate BLS keys first: npm run generate:das-keys
  das-server:
    image: ${nitroImage}
    container_name: ${chainName}-das
    restart: unless-stopped
    ports:
      - "9876:9876"   # DAS RPC (batch poster data submission)
      - "9877:9877"   # DAS REST API
    volumes:
      - ./data/das:/home/user/das-data
      - ./das-keys:/home/user/das-keys:ro
    entrypoint: /usr/local/bin/daserver
    command:
      - --data-availability.local-file-storage.enable
      - --data-availability.local-file-storage.data-dir=/home/user/das-data
      - --data-availability.parent-chain-node-url=\${PARENT_CHAIN_RPC}
      - --data-availability.sequencer-inbox-address=\${SEQUENCER_INBOX_ADDRESS:-0x0000000000000000000000000000000000000000}
      - --data-availability.key.key-dir=/home/user/das-keys
      - --enable-rest
      - --rest-addr=0.0.0.0
      - --rest-port=9877
      - --log-level=3
    env_file:
      - .env
`;
  }

  compose += `
# Using bind mounts (./data/) instead of named volumes for easier inspection.
# Create data directories before starting: mkdir -p data/arbitrum${isAnyTrust ? ' data/das das-keys' : ''}
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
  // In Docker, DAS runs as a sibling service — use service name, not localhost
  const dasLine = isAnyTrust ? `\n    dasServerUrl: process.env.DAS_SERVER_URL ?? 'http://das-server:9877',` : '';

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

  // 3. Inject deployed-at block number into chain info-json.
  //    Without this, the node can't find the rollup genesis on L1.
  if (deployment.deployedAtBlock) {
    // The chain info-json is typically at chain.info-json[0].rollup
    if (!nodeConfig.chain) nodeConfig.chain = {};
    if (!nodeConfig.chain['info-json']) {
      // Build the info-json structure that Nitro expects
      nodeConfig.chain['info-json'] = JSON.stringify([{
        'chain-id': deployment.chainId,
        'chain-name': '${chainName}',
        'parent-chain-id': ${parentChainId},
        'chain-config': deployment.chainConfig,
        'rollup': {
          ...deployment.coreContracts,
          'deployed-at': deployment.deployedAtBlock,
        },
      }]);
    } else {
      // info-json already exists (from prepareNodeConfig) — patch deployed-at into it
      try {
        let infoJson = typeof nodeConfig.chain['info-json'] === 'string'
          ? JSON.parse(nodeConfig.chain['info-json'])
          : nodeConfig.chain['info-json'];
        if (Array.isArray(infoJson) && infoJson[0]?.rollup) {
          infoJson[0].rollup['deployed-at'] = deployment.deployedAtBlock;
        }
        nodeConfig.chain['info-json'] = JSON.stringify(infoJson);
      } catch {
        console.warn('  Could not patch deployed-at into existing info-json');
      }
    }
    console.log('  Injected deployed-at block:', deployment.deployedAtBlock);
  } else {
    console.warn('Warning: deployment.json has no deployedAtBlock.');
    console.warn('  Node may fail with "failed to get init message". Re-run deploy-rollup.ts to fix.');
  }

  // 4. Fix malformed DAS URLs — SDK may produce double-port like http://host:9877:9877
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
        "Generate BLS keys: docker run --rm -v $(pwd)/das-keys:/keys offchainlabs/nitro-node:v3.9.4-7f582c3 datool keygen --dir /keys",
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

function generateDasKeysScript(): string {
  const nitroImage = 'offchainlabs/nitro-node:v3.9.4-7f582c3';
  return `#!/usr/bin/env bash
set -euo pipefail

echo "=== Generate DAS BLS Keys ==="

# Create output directory
mkdir -p das-keys

# Generate BLS key pair using the datool from the Nitro image
docker run --rm \\
  --entrypoint /usr/local/bin/datool \\
  -v "$(pwd)/das-keys:/keys" \\
  ${nitroImage} \\
  keygen --dir /keys

echo ""
echo "BLS keys generated in das-keys/"
echo "  das_bls      — private key (keep secret!)"
echo "  das_bls.pub  — public key (used for keyset registration)"
echo ""
echo "Next steps:"
echo "  1. Start DAS + Nitro node: docker-compose up -d"
echo "  2. Register keyset: npm run configure:anytrust"
`;
}

function generateTestChainScript(chainId: number, chainName: string, parentChainId: number): string {
  return `import 'dotenv/config';
import * as fs from 'fs';
import {
  createPublicClient,
  createWalletClient,
  http,
  parseEther,
  formatEther,
  maxUint256,
  Chain,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';

// ERC-20 ABI for custom gas token approval
const erc20Abi = [
  {
    name: 'approve',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'spender', type: 'address' },
      { name: 'amount', type: 'uint256' },
    ],
    outputs: [{ name: '', type: 'bool' }],
  },
  {
    name: 'balanceOf',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
] as const;

// Inbox ABI for ERC-20 deposit (custom gas token chains)
const inboxAbi = [
  {
    name: 'depositERC20',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [{ name: 'amount', type: 'uint256' }],
    outputs: [],
  },
] as const;

const orbitChain: Chain = {
  id: ${chainId},
  name: '${chainName}',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: {
    default: { http: [process.env.ORBIT_CHAIN_RPC ?? 'http://localhost:8449'] },
  },
};

const parentChain: Chain = {
  id: ${parentChainId},
  name: 'Parent Chain',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: {
    default: { http: [process.env.PARENT_CHAIN_RPC!] },
  },
};

/**
 * Test chain connectivity and basic operations.
 *
 * Checks:
 *   1. L3 RPC connectivity and chain ID
 *   2. Balances on both parent and orbit chain
 *   3. Test transfer on L3
 *   4. Simple contract deployment
 */
async function main() {
  const account = privateKeyToAccount(
    process.env.DEPLOYER_PRIVATE_KEY! as \\\`0x\\\${string}\\\`
  );

  console.log('=== Orbit Chain Health Check ===');
  console.log('Account:', account.address);

  // 1. Test L3 RPC connectivity
  console.log('\\n--- L3 RPC Connectivity ---');
  const orbitClient = createPublicClient({
    chain: orbitChain,
    transport: http(process.env.ORBIT_CHAIN_RPC ?? 'http://localhost:8449'),
  });

  try {
    const chainId = await orbitClient.getChainId();
    console.log('  Chain ID:', chainId, chainId === ${chainId} ? '(correct)' : '(MISMATCH — expected ${chainId})');

    const blockNumber = await orbitClient.getBlockNumber();
    console.log('  Latest block:', blockNumber.toString());
  } catch (err) {
    console.error('  FAILED: Cannot connect to L3 RPC');
    console.error('  Error:', (err as Error).message);
    console.error('  Is the Nitro node running? Try: docker-compose up -d');
    process.exit(1);
  }

  // 2. Check balances
  console.log('\\n--- Balances ---');
  const parentClient = createPublicClient({
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  });

  const parentBalance = await parentClient.getBalance({ address: account.address });
  console.log('  Parent chain:', formatEther(parentBalance), 'ETH');

  const orbitBalance = await orbitClient.getBalance({ address: account.address });
  console.log('  Orbit chain: ', formatEther(orbitBalance), 'ETH/gas token');

  // 3. Test transfer on L3 (if balance > 0)
  console.log('\\n--- Test Transfer (L3) ---');
  if (orbitBalance > 0n) {
    const walletClient = createWalletClient({
      account,
      chain: orbitChain,
      transport: http(process.env.ORBIT_CHAIN_RPC ?? 'http://localhost:8449'),
    });

    try {
      const txHash = await walletClient.sendTransaction({
        to: account.address,
        value: 0n,
      });
      const receipt = await orbitClient.waitForTransactionReceipt({ hash: txHash });
      console.log('  Self-transfer:', receipt.status === 'success' ? 'SUCCESS' : 'FAILED');
      console.log('  Tx:', txHash);
      console.log('  Gas used:', receipt.gasUsed.toString());
    } catch (err) {
      console.error('  FAILED:', (err as Error).message);
    }
  } else {
    console.log('  Skipped — no balance on L3. Deposit funds first.');
  }

  // 4. Contract deployment test
  console.log('\\n--- Contract Deployment Test ---');
  if (orbitBalance > 0n) {
    const walletClient = createWalletClient({
      account,
      chain: orbitChain,
      transport: http(process.env.ORBIT_CHAIN_RPC ?? 'http://localhost:8449'),
    });

    try {
      // Minimal contract: PUSH1 0x00 PUSH1 0x00 RETURN (returns empty)
      const txHash = await walletClient.deployContract({
        abi: [],
        bytecode: '0x60006000f3',
      });
      const receipt = await orbitClient.waitForTransactionReceipt({ hash: txHash });
      console.log('  Deploy:', receipt.status === 'success' ? 'SUCCESS' : 'FAILED');
      console.log('  Contract:', receipt.contractAddress);
    } catch (err) {
      console.error('  FAILED:', (err as Error).message);
    }
  } else {
    console.log('  Skipped — no balance on L3.');
  }

  // 5. Deposit test (parent chain → L3)
  console.log('\\n--- Deposit Test (Parent → L3) ---');
  if (fs.existsSync('deployment.json')) {
    const deployment = JSON.parse(fs.readFileSync('deployment.json', 'utf-8'));
    const inboxAddress = deployment.coreContracts?.inbox as \\\`0x\\\${string}\\\`;

    if (inboxAddress) {
      const parentWalletClient = createWalletClient({
        account,
        chain: parentChain,
        transport: http(process.env.PARENT_CHAIN_RPC),
      });

      if (deployment.nativeToken) {
        // Custom gas token chain: approve Inbox, then depositERC20
        const nativeToken = deployment.nativeToken as \\\`0x\\\${string}\\\`;
        console.log('  Custom gas token:', nativeToken);

        const tokenBalance = await parentClient.readContract({
          address: nativeToken,
          abi: erc20Abi,
          functionName: 'balanceOf',
          args: [account.address],
        });
        const depositAmount = tokenBalance / 100n; // 1% of balance

        if (depositAmount > 0n) {
          try {
            // Approve Inbox (NOT Bridge) for the token
            console.log('  Approving Inbox for token spend...');
            const approveHash = await parentWalletClient.writeContract({
              address: nativeToken,
              abi: erc20Abi,
              functionName: 'approve',
              args: [inboxAddress, maxUint256],
            });
            await parentClient.waitForTransactionReceipt({ hash: approveHash });

            // Deposit via Inbox.depositERC20(amount)
            console.log('  Depositing', depositAmount.toString(), 'tokens to L3 via Inbox...');
            const depositHash = await parentWalletClient.writeContract({
              address: inboxAddress,
              abi: inboxAbi,
              functionName: 'depositERC20',
              args: [depositAmount],
            });
            const depositReceipt = await parentClient.waitForTransactionReceipt({ hash: depositHash });
            console.log('  Deposit:', depositReceipt.status === 'success' ? 'SUCCESS' : 'FAILED');
            console.log('  Tx:', depositHash);
            console.log('  Note: L3 balance updates after ~15 min (retryable ticket processing)');
          } catch (err) {
            console.error('  FAILED:', (err as Error).message);
          }
        } else {
          console.log('  Skipped — no token balance on parent chain');
        }
      } else {
        // ETH chain: send ETH directly to the Inbox
        const depositAmount = parseEther('0.001');
        if (parentBalance >= depositAmount + parseEther('0.01')) {
          try {
            console.log('  Depositing 0.001 ETH to L3 via Inbox...');
            const txHash = await parentWalletClient.sendTransaction({
              to: inboxAddress,
              value: depositAmount,
            });
            const receipt = await parentClient.waitForTransactionReceipt({ hash: txHash });
            console.log('  Deposit:', receipt.status === 'success' ? 'SUCCESS' : 'FAILED');
            console.log('  Tx:', txHash);
            console.log('  Note: L3 balance updates after ~15 min (retryable ticket processing)');
          } catch (err) {
            console.error('  FAILED:', (err as Error).message);
          }
        } else {
          console.log('  Skipped — insufficient parent chain balance (need 0.011 ETH)');
        }
      }
    } else {
      console.log('  Skipped — no Inbox address in deployment.json');
    }
  } else {
    console.log('  Skipped — no deployment.json');
  }

  // 6. Load deployment info if available
  if (fs.existsSync('deployment.json')) {
    console.log('\\n--- Deployment Info ---');
    const deployment = JSON.parse(fs.readFileSync('deployment.json', 'utf-8'));
    console.log('  Rollup:', deployment.coreContracts?.rollup);
    console.log('  Inbox:', deployment.coreContracts?.inbox);
    console.log('  Bridge:', deployment.coreContracts?.bridge);
    if (deployment.tokenBridgeContracts) {
      console.log('  Token Bridge Router (parent):', deployment.tokenBridgeContracts.parentChain?.router);
      console.log('  Token Bridge Router (orbit):', deployment.tokenBridgeContracts.orbitChain?.router);
    }
  }

  console.log('\\n=== Health Check Complete ===');
}

main().catch(console.error);
`;
}

function generateGovernanceScript(parentChainId: number, parentChainName: string): string {
  return `import 'dotenv/config';
import * as fs from 'fs';
import {
  createPublicClient,
  createWalletClient,
  http,
  encodeFunctionData,
  Chain,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';

// UpgradeExecutor ABI
const upgradeExecutorAbi = [
  {
    name: 'executeCall',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'target', type: 'address' },
      { name: 'data', type: 'bytes' },
    ],
    outputs: [],
  },
  {
    name: 'hasRole',
    type: 'function',
    stateMutability: 'view',
    inputs: [
      { name: 'role', type: 'bytes32' },
      { name: 'account', type: 'address' },
    ],
    outputs: [{ name: '', type: 'bool' }],
  },
  {
    name: 'grantRole',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'role', type: 'bytes32' },
      { name: 'account', type: 'address' },
    ],
    outputs: [],
  },
  {
    name: 'revokeRole',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'role', type: 'bytes32' },
      { name: 'account', type: 'address' },
    ],
    outputs: [],
  },
] as const;

const EXECUTOR_ROLE = '0xd8aa0f3194971a2a116679f7c2090f6939c8d4e01a2a8d7e41d55e5351469e63' as \\\`0x\\\${string}\\\`;
const ADMIN_ROLE = '0xa49807205ce4d355092ef5a8a18f56e8913cf4a201fbe287825b095693c21775' as \\\`0x\\\${string}\\\`;

const parentChain: Chain = {
  id: ${parentChainId},
  name: '${parentChainName}',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: {
    default: { http: [process.env.PARENT_CHAIN_RPC!] },
  },
};

/**
 * Manage governance roles on the UpgradeExecutor.
 *
 * Usage:
 *   npx tsx scripts/manage-governance.ts status
 *   npx tsx scripts/manage-governance.ts grant <address>
 *   npx tsx scripts/manage-governance.ts revoke <address>
 */
async function main() {
  const command = process.argv[2] ?? 'status';
  const targetAddress = process.argv[3] as \\\`0x\\\${string}\\\` | undefined;

  const account = privateKeyToAccount(
    process.env.DEPLOYER_PRIVATE_KEY! as \\\`0x\\\${string}\\\`
  );

  // Read UpgradeExecutor from deployment.json
  if (!fs.existsSync('deployment.json')) {
    console.error('Error: deployment.json not found. Run deploy-rollup.ts first.');
    process.exit(1);
  }
  const deployment = JSON.parse(fs.readFileSync('deployment.json', 'utf-8'));
  const upgradeExecutor = deployment.coreContracts.upgradeExecutor as \\\`0x\\\${string}\\\`;

  const publicClient = createPublicClient({
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  });

  const walletClient = createWalletClient({
    account,
    chain: parentChain,
    transport: http(process.env.PARENT_CHAIN_RPC),
  });

  console.log('=== Governance Management ===');
  console.log('UpgradeExecutor:', upgradeExecutor);
  console.log('Caller:', account.address);

  if (command === 'status') {
    // Check roles for the caller and optionally a target
    const addresses = [account.address];
    if (targetAddress) addresses.push(targetAddress);

    for (const addr of addresses) {
      const hasExecutor = await publicClient.readContract({
        address: upgradeExecutor,
        abi: upgradeExecutorAbi,
        functionName: 'hasRole',
        args: [EXECUTOR_ROLE, addr],
      });
      const hasAdmin = await publicClient.readContract({
        address: upgradeExecutor,
        abi: upgradeExecutorAbi,
        functionName: 'hasRole',
        args: [ADMIN_ROLE, addr],
      });
      console.log(\\\`\\\\n  \\\${addr}:\\\`);
      console.log(\\\`    EXECUTOR_ROLE: \\\${hasExecutor}\\\`);
      console.log(\\\`    ADMIN_ROLE:    \\\${hasAdmin}\\\`);
    }
  } else if (command === 'grant' && targetAddress) {
    console.log('\\\\nGranting EXECUTOR_ROLE to:', targetAddress);
    // Grant must go through executeCall if caller has EXECUTOR_ROLE (not ADMIN_ROLE directly)
    const grantCalldata = encodeFunctionData({
      abi: upgradeExecutorAbi,
      functionName: 'grantRole',
      args: [EXECUTOR_ROLE, targetAddress],
    });
    const txHash = await walletClient.writeContract({
      address: upgradeExecutor,
      abi: upgradeExecutorAbi,
      functionName: 'executeCall',
      args: [upgradeExecutor, grantCalldata],
    });
    const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
    console.log('  Tx:', receipt.transactionHash, '- Status:', receipt.status);
  } else if (command === 'revoke' && targetAddress) {
    console.log('\\\\nRevoking EXECUTOR_ROLE from:', targetAddress);
    const revokeCalldata = encodeFunctionData({
      abi: upgradeExecutorAbi,
      functionName: 'revokeRole',
      args: [EXECUTOR_ROLE, targetAddress],
    });
    const txHash = await walletClient.writeContract({
      address: upgradeExecutor,
      abi: upgradeExecutorAbi,
      functionName: 'executeCall',
      args: [upgradeExecutor, revokeCalldata],
    });
    const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
    console.log('  Tx:', receipt.transactionHash, '- Status:', receipt.status);
  } else {
    console.log('\\\\nUsage:');
    console.log('  npx tsx scripts/manage-governance.ts status [address]');
    console.log('  npx tsx scripts/manage-governance.ts grant <address>');
    console.log('  npx tsx scripts/manage-governance.ts revoke <address>');
  }
}

main().catch(console.error);
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
  // Always get the basic chain config (not AnyTrust keyset — that's step 6)
  const configResult = generateOrbitConfig({
    prompt: "prepare chain config",
    chainId,
    owner: "0x0000000000000000000000000000000000000000",
    parentChain,
  });
  const configFile = Object.entries(configResult.files).find(([k]) =>
    k.startsWith("scripts/")
  );
  if (configFile) {
    let configCode = configFile[1];
    // generateOrbitConfig defaults isAnyTrust to false (to avoid template collision),
    // but AnyTrust chains need DataAvailabilityCommittee: true in the chain config
    if (isAnyTrust) {
      configCode = configCode.replace("DataAvailabilityCommittee: false", "DataAvailabilityCommittee: true");
    }
    files["scripts/prepare-chain-config.ts"] = configCode;
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

  // 6c. BLS key generation for AnyTrust
  if (isAnyTrust) {
    files["scripts/generate-das-keys.sh"] = generateDasKeysScript();
  }

  // 6d. Test chain health check
  files["scripts/test-chain.ts"] = generateTestChainScript(chainId, chainName, parentChainId);

  // 6e. Governance management
  files["scripts/manage-governance.ts"] = generateGovernanceScript(parentChainId, parentChainName);

  // 7. Scaffold files
  files["package.json"] = generatePackageJson(chainName, isAnyTrust);
  files["tsconfig.json"] = generateTsconfig();
  files[".env.example"] = generateEnvExample(parentRpc, chainId, chainName, isAnyTrust, nativeToken);
  files["setup.sh"] = generateSetupSh(isAnyTrust);
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
      "test-chain.ts",
      "manage-governance.ts",
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
    projectStructure["scripts/"].push("generate-das-keys.sh");
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

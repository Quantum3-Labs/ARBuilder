/**
 * Orchestrate full dApp scaffolding (M3 tool)
 *
 * Generates complete dApps with:
 * - Contract ABI auto-extracted and injected into backend/frontend
 * - Centralized env var configuration
 * - Executable setup.sh, deploy.sh, start.sh scripts
 */

import { generateBackend } from "./generateBackend";
import { generateFrontend } from "./generateFrontend";
import { generateIndexer } from "./generateIndexer";
import { generateOracle } from "./generateOracle";
import { extractAbiFromCode, abiToViemHumanReadable } from "../abiExtractor";

export const TEMPLATE_DISCLAIMER =
  "This generated code is a starting entrypoint — a working foundation for you to build upon. " +
  "Review, customize, and extend it to match your specific requirements before deploying.";

type Component = "contract" | "backend" | "frontend" | "indexer" | "oracle";
type Network = "arbitrum-sepolia" | "arbitrum-one";

interface OrchestrateDappArgs {
  prompt: string;
  components?: Component[];
  network?: Network;
  contractAddress?: string;
  contractAbi?: string;
}

interface ComponentResult {
  files: Record<string, string>;
  dependencies?: Record<string, string>;
  setupInstructions?: string[];
}

interface OrchestrateDappResult {
  projectName: string;
  structure: Record<string, ComponentResult>;
  rootFiles: Record<string, string>;
  setupInstructions: string[];
  disclaimer: string;
}

const BACKEND_PORT = "3001";
const FRONTEND_PORT = "3000";

// Stylus contract template
const STYLUS_CONTRACT_TEMPLATE = `#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(not(any(test, feature = "export-abi")), no_std)]
#[macro_use]
extern crate alloc;

use alloc::{vec, vec::Vec};

use stylus_sdk::{
    alloy_primitives::{Address, U256},
    prelude::*,
    storage::{StorageAddress, StorageU256, StorageMap},
};

sol_storage! {
    #[entrypoint]
    pub struct MyContract {
        address owner;
        uint256 value;
        mapping(address => uint256) balances;
    }
}

#[public]
impl MyContract {
    pub fn owner(&self) -> Address {
        self.owner.get()
    }

    pub fn get_value(&self) -> U256 {
        self.value.get()
    }

    pub fn set_value(&mut self, new_value: U256) {
        self.value.set(new_value);
    }

    pub fn balance_of(&self, account: Address) -> U256 {
        self.balances.get(account)
    }

    pub fn deposit(&mut self) {
        let sender = self.vm().msg_sender();
        let amount = self.vm().msg_value();
        let current = self.balances.get(sender);
        self.balances.setter(sender).set(current + amount);
    }

    pub fn withdraw(&mut self, amount: U256) {
        let sender = self.vm().msg_sender();
        let current = self.balances.get(sender);
        if current >= amount {
            self.balances.setter(sender).set(current - amount);
            // Transfer would go here
        }
    }
}
`;

const CARGO_TOML = `[package]
name = "my_contract"
version = "0.1.0"
edition = "2021"

[dependencies]
stylus-sdk = "0.10.0"
alloy-primitives = "1.0.1"
alloy-sol-types = "1.0.1"

[features]
export-abi = ["stylus-sdk/export-abi"]

[lib]
crate-type = ["lib", "cdylib"]

[[bin]]
name = "my_contract"
path = "src/main.rs"

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"
`;

const STYLUS_TOML = `[workspace]

[workspace.networks]

[contract]
`;

const RUST_TOOLCHAIN_TOML = `[toolchain]
channel = "1.88.0"
targets = ["wasm32-unknown-unknown"]
`;

const MAIN_RS = `#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]

#[cfg(not(any(test, feature = "export-abi")))]
#[unsafe(no_mangle)]
pub extern "C" fn main() {}

#[cfg(feature = "export-abi")]
fn main() {
    my_contract::print_from_args();
}
`;

function generateProjectName(prompt: string): string {
  const words = prompt.toLowerCase().split(/\s+/);
  const keywords = words.filter(
    (w) => w.length > 3 && !["create", "build", "make", "with", "using", "dapp", "app"].includes(w)
  );
  const name = keywords.slice(0, 2).join("-") || "my-dapp";
  return name.replace(/[^a-z0-9-]/g, "");
}

function generateEnvTemplate(
  components: Component[],
  network: Network
): string {
  const rpcUrl = network === "arbitrum-one"
    ? "https://arb1.arbitrum.io/rpc"
    : "https://sepolia-rollup.arbitrum.io/rpc";
  const chainId = network === "arbitrum-one" ? "42161" : "421614";

  const lines = ["# ARBuilder dApp Environment Configuration", ""];
  lines.push("# Network");
  lines.push(`NETWORK=${network}`);
  lines.push(`CHAIN_ID=${chainId}`);
  lines.push(`RPC_URL=${rpcUrl}`);
  lines.push("");

  if (components.includes("contract")) {
    lines.push("# Contract");
    lines.push("CONTRACT_ADDRESS=0x_DEPLOY_ADDRESS_HERE");
    lines.push("PRIVATE_KEY=0x_YOUR_PRIVATE_KEY_HERE");
    lines.push("");
  }

  if (components.includes("backend")) {
    lines.push("# Backend");
    lines.push(`PORT=${BACKEND_PORT}`);
    lines.push(`FRONTEND_URL=http://localhost:${FRONTEND_PORT}`);
    lines.push("");
  }

  if (components.includes("frontend")) {
    lines.push("# Frontend");
    lines.push("NEXT_PUBLIC_CONTRACT_ADDRESS=0x_DEPLOY_ADDRESS_HERE");
    lines.push(`NEXT_PUBLIC_BACKEND_URL=http://localhost:${BACKEND_PORT}`);
    lines.push("NEXT_PUBLIC_WALLET_CONNECT_ID=YOUR_WALLETCONNECT_PROJECT_ID");
    lines.push("");
  }

  if (components.includes("indexer") && components.includes("frontend")) {
    lines.push("# Frontend — Subgraph");
    lines.push("NEXT_PUBLIC_SUBGRAPH_URL=https://api.thegraph.com/subgraphs/name/YOUR_SUBGRAPH");
    lines.push("");
  }

  if (components.includes("indexer")) {
    lines.push("# Indexer (The Graph)");
    lines.push("GRAPH_DEPLOY_KEY=YOUR_GRAPH_STUDIO_DEPLOY_KEY");
    lines.push("SUBGRAPH_NAME=my-subgraph");
    lines.push("");
  }

  if (components.includes("oracle")) {
    lines.push("# Oracle (Chainlink)");
    lines.push("ORACLE_CONTRACT_ADDRESS=0x_ORACLE_ADDRESS_HERE");
    lines.push("");
  }

  return lines.join("\n");
}

function generateSetupScript(components: Component[]): string {
  const lines = [
    "#!/usr/bin/env bash",
    "set -euo pipefail",
    "",
    'echo "=== ARBuilder dApp Setup ==="',
    "",
    'if [ ! -f .env ]; then',
    '  cp .env.example .env',
    '  echo "Created .env from template — edit it with your keys before deploying."',
    "fi",
    "",
    "# --- Scaffold helper ---",
    "# Copies only files that do NOT already exist in the target dir.",
    "# src/ is always skipped — our generated code is authoritative.",
    "backfill_from_scaffold() {",
    '  local scaffold_dir="$1"',
    '  local target_dir="$2"',
    '  if [ ! -d "$scaffold_dir" ]; then return 0; fi',
    '  find "$scaffold_dir" -type f | while read -r f; do',
    '    rel="${f#$scaffold_dir/}"',
    '    case "$rel" in src/*) continue ;; esac',
    '    if [ ! -f "$target_dir/$rel" ]; then',
    '      mkdir -p "$target_dir/$(dirname "$rel")"',
    '      cp "$f" "$target_dir/$rel"',
    "    fi",
    "  done",
    "}",
    "",
  ];

  if (components.includes("contract")) {
    lines.push('echo "Installing Rust toolchain..."');
    lines.push("rustup target add wasm32-unknown-unknown 2>/dev/null || true");
    lines.push("cargo install cargo-stylus 2>/dev/null || true");
    lines.push("");
    lines.push("# Scaffold contract baseline with cargo stylus new");
    lines.push("if command -v cargo-stylus &>/dev/null || cargo stylus --version &>/dev/null 2>&1; then");
    lines.push('  echo "  Scaffolding contract config from cargo stylus new..."');
    lines.push("  SCAFFOLD_TMP=$(mktemp -d)");
    lines.push('  cargo stylus new "$SCAFFOLD_TMP/scaffold" 2>/dev/null && \\');
    lines.push('    backfill_from_scaffold "$SCAFFOLD_TMP/scaffold" packages/contracts || \\');
    lines.push('    echo "  (scaffold skipped — cargo stylus new failed)"');
    lines.push('  rm -rf "$SCAFFOLD_TMP"');
    lines.push("else");
    lines.push('  echo "  (scaffold skipped — cargo-stylus not available)"');
    lines.push("fi");
    lines.push("");
  }

  if (components.includes("backend")) {
    // TS always uses NestJS, so always include NestJS scaffold
    lines.push("# Scaffold backend baseline with @nestjs/cli");
    lines.push("if command -v npx &>/dev/null; then");
    lines.push('  echo "  Scaffolding backend config from @nestjs/cli..."');
    lines.push("  SCAFFOLD_TMP=$(mktemp -d)");
    lines.push('  npx @nestjs/cli@latest new scaffold --package-manager npm --skip-git --skip-install --directory "$SCAFFOLD_TMP" 2>/dev/null && \\');
    lines.push('    backfill_from_scaffold "$SCAFFOLD_TMP/scaffold" packages/backend || \\');
    lines.push('    echo "  (scaffold skipped — @nestjs/cli failed)"');
    lines.push('  rm -rf "$SCAFFOLD_TMP"');
    lines.push("else");
    lines.push('  echo "  (scaffold skipped — npx not available)"');
    lines.push("fi");
    lines.push("");
    lines.push('echo "Installing backend dependencies..."');
    lines.push("cd packages/backend && npm install && cd ../..");
    lines.push("");
  }

  if (components.includes("frontend")) {
    lines.push("# Scaffold frontend baseline with create-next-app");
    lines.push("if command -v npx &>/dev/null; then");
    lines.push('  echo "  Scaffolding frontend config from create-next-app..."');
    lines.push("  SCAFFOLD_TMP=$(mktemp -d)");
    lines.push('  npx create-next-app@latest "$SCAFFOLD_TMP/scaffold" --ts --tailwind --app --src-dir --use-npm --no-git --no-eslint --skip-install 2>/dev/null && \\');
    lines.push('    backfill_from_scaffold "$SCAFFOLD_TMP/scaffold" packages/frontend || \\');
    lines.push('    echo "  (scaffold skipped — create-next-app failed)"');
    lines.push('  rm -rf "$SCAFFOLD_TMP"');
    lines.push("else");
    lines.push('  echo "  (scaffold skipped — npx not available)"');
    lines.push("fi");
    lines.push("");
    lines.push('echo "Installing frontend dependencies..."');
    lines.push("cd packages/frontend && npm install && cd ../..");
    lines.push("");
  }

  if (components.includes("indexer")) {
    lines.push('echo "Installing indexer dependencies..."');
    lines.push("cd packages/indexer && npm install && cd ../..");
    lines.push("");
  }

  if (components.includes("oracle")) {
    lines.push('echo "Installing oracle dependencies..."');
    lines.push("cd packages/oracle && npm install && cd ../..");
    lines.push("");
  }

  lines.push('echo "Setup complete! Edit .env, then run ./deploy.sh"');
  return lines.join("\n");
}

function generateDeployScript(components: Component[]): string {
  const lines = [
    "#!/usr/bin/env bash",
    "set -euo pipefail",
    "",
    "if [ -f .env ]; then set -a; source .env; set +a; fi",
    "",
    'echo "=== ARBuilder dApp Deploy ==="',
    "",
  ];

  if (components.includes("contract")) {
    lines.push('echo "Building Stylus contract..."');
    lines.push("cd packages/contracts");
    lines.push("cargo build --target wasm32-unknown-unknown --release");
    lines.push("");
    lines.push('echo "Deploying..."');
    lines.push('DEPLOY_OUTPUT=$(cargo stylus deploy --private-key "$PRIVATE_KEY" --endpoint "$RPC_URL" 2>&1) || {');
    lines.push('  echo "Deploy failed:"; echo "$DEPLOY_OUTPUT"; exit 1');
    lines.push("}");
    lines.push("");
    lines.push("DEPLOYED_ADDRESS=$(echo \"$DEPLOY_OUTPUT\" | grep -oE '0x[a-fA-F0-9]{40}' | head -1)");
    lines.push('if [ -n "$DEPLOYED_ADDRESS" ]; then');
    lines.push('  echo "Contract deployed at: $DEPLOYED_ADDRESS"');
    lines.push("  cd ../..");
    lines.push('  sed -i.bak "s|CONTRACT_ADDRESS=.*|CONTRACT_ADDRESS=$DEPLOYED_ADDRESS|" .env');
    lines.push('  sed -i.bak "s|NEXT_PUBLIC_CONTRACT_ADDRESS=.*|NEXT_PUBLIC_CONTRACT_ADDRESS=$DEPLOYED_ADDRESS|" .env');
    lines.push("  rm -f .env.bak");
    lines.push("else");
    lines.push('  echo "Could not extract address. Update .env manually."');
    lines.push("  cd ../..");
    lines.push("fi");
    lines.push("");
  }

  if (components.includes("oracle")) {
    lines.push("# Oracle deploy");
    lines.push('if [ -d "packages/oracle" ]; then');
    lines.push('  echo "Deploying oracle contract..."');
    lines.push("  cd packages/oracle");
    lines.push('  npx hardhat run scripts/deploy.ts --network ${NETWORK:-arbitrumSepolia}');
    lines.push("  cd ../..");
    lines.push("fi");
    lines.push("");
  }

  if (components.includes("indexer")) {
    lines.push("# Indexer deploy");
    lines.push('if [ -d "packages/indexer" ]; then');
    lines.push('  echo "Building subgraph..."');
    lines.push("  cd packages/indexer");
    lines.push("  npm run codegen");
    lines.push("  npm run build");
    lines.push('  if [ -n "${GRAPH_DEPLOY_KEY:-}" ]; then');
    lines.push('    echo "Deploying subgraph..."');
    lines.push('    graph deploy --studio ${SUBGRAPH_NAME:-my-subgraph} --deploy-key "$GRAPH_DEPLOY_KEY"');
    lines.push("  else");
    lines.push('    echo "Skipping subgraph deploy (set GRAPH_DEPLOY_KEY and SUBGRAPH_NAME in .env to auto-deploy)"');
    lines.push("  fi");
    lines.push("  cd ../..");
    lines.push("fi");
    lines.push("");
  }

  lines.push('echo "Deploy complete! Run ./start.sh to launch."');
  return lines.join("\n");
}

function generateStartScript(components: Component[]): string {
  const lines = [
    "#!/usr/bin/env bash",
    "set -euo pipefail",
    "",
    "if [ -f .env ]; then set -a; source .env; set +a; fi",
    "",
    'echo "=== ARBuilder dApp Start ==="',
    "",
    "PIDS=()",
    "cleanup() { for pid in \"${PIDS[@]}\"; do kill $pid 2>/dev/null || true; done; exit 0; }",
    "trap cleanup SIGINT SIGTERM",
    "",
  ];

  if (components.includes("backend")) {
    lines.push(`echo "Starting backend on port \${PORT:-${BACKEND_PORT}}..."`);
    lines.push("cd packages/backend && npm run start:dev & PIDS+=($!); cd ../..");
    lines.push("");
  }

  if (components.includes("frontend")) {
    lines.push(`echo "Starting frontend on port ${FRONTEND_PORT}..."`);
    lines.push("cd packages/frontend && npm run dev & PIDS+=($!); cd ../..");
    lines.push("");
  }

  lines.push('echo ""');
  lines.push('echo "Services running:"');
  if (components.includes("backend"))
    lines.push(`echo "  Backend:  http://localhost:\${PORT:-${BACKEND_PORT}}"`);
  if (components.includes("frontend"))
    lines.push(`echo "  Frontend: http://localhost:${FRONTEND_PORT}"`);
  lines.push('echo "Press Ctrl+C to stop."');
  lines.push("wait");

  return lines.join("\n");
}

export function orchestrateDapp(args: OrchestrateDappArgs): OrchestrateDappResult {
  const {
    prompt,
    components = ["contract", "frontend"],
    network = "arbitrum-sepolia",
    contractAddress,
    contractAbi: providedAbi,
  } = args;

  const projectName = generateProjectName(prompt);
  const structure: Record<string, ComponentResult> = {};
  const setupInstructions: string[] = [];

  // Extract ABI from contract template (or use provided ABI)
  let contractAbiJson: string | undefined = providedAbi;
  let abiHumanReadable: string[] = [];

  // Generate contract
  if (components.includes("contract")) {
    structure["packages/contracts"] = {
      files: {
        "src/lib.rs": STYLUS_CONTRACT_TEMPLATE,
        "src/main.rs": MAIN_RS,
        "Cargo.toml": CARGO_TOML,
        "Stylus.toml": STYLUS_TOML,
        "rust-toolchain.toml": RUST_TOOLCHAIN_TOML,
        ".cargo/config.toml": `[build]
target = "wasm32-unknown-unknown"

[target.wasm32-unknown-unknown]
rustflags = ["-C", "link-arg=-zstack-size=32768"]
`,
      },
      setupInstructions: [
        "./setup.sh",
        "Edit .env with your keys",
        "./deploy.sh",
      ],
    };
    setupInstructions.push("1. Run ./setup.sh to install dependencies");

    // Auto-extract ABI from the contract template
    if (!contractAbiJson) {
      const abi = extractAbiFromCode(STYLUS_CONTRACT_TEMPLATE);
      abiHumanReadable = abiToViemHumanReadable(abi);
      contractAbiJson = JSON.stringify(abi);
    }
  }

  // If we have provided ABI but no human-readable version, generate it
  if (contractAbiJson && abiHumanReadable.length === 0) {
    try {
      const parsed = JSON.parse(contractAbiJson);
      abiHumanReadable = abiToViemHumanReadable(parsed);
    } catch {
      // Invalid ABI, skip
    }
  }

  if (components.includes("backend")) {
    const backendResult = generateBackend({
      prompt,
      framework: "nestjs",
      contractAbi: contractAbiJson,
    });
    structure["packages/backend"] = {
      files: backendResult.files,
      dependencies: backendResult.dependencies,
      setupInstructions: backendResult.setupInstructions,
    };
    setupInstructions.push("2. Run ./deploy.sh to build and deploy the contract");
  }

  if (components.includes("frontend")) {
    const frontendResult = generateFrontend({
      prompt,
      contractAbi: contractAbiJson,
      uiFramework: "daisyui",
      template: "dashboard",
    });
    structure["packages/frontend"] = {
      files: frontendResult.files,
      dependencies: frontendResult.dependencies,
      setupInstructions: frontendResult.setupInstructions,
    };
    setupInstructions.push("3. Run ./start.sh to launch backend + frontend");
  }

  if (components.includes("indexer")) {
    const address = contractAddress || "0x0000000000000000000000000000000000000000";
    const indexerResult = generateIndexer({
      contractAddress: address,
      subgraphType: "erc20",
      network: network === "arbitrum-one" ? "arbitrum-one" : "arbitrum-sepolia",
    });
    structure["packages/indexer"] = {
      files: indexerResult.files,
      dependencies: indexerResult.dependencies,
      setupInstructions: indexerResult.setupInstructions,
    };
    setupInstructions.push("4. Deploy indexer: cd packages/indexer && npm install && npm run deploy");
  }

  if (components.includes("oracle")) {
    const oracleResult = generateOracle({
      oracleType: "price_feed",
      network: network === "arbitrum-one" ? "arbitrum-one" : "arbitrum-sepolia",
      feeds: ["ETH/USD"],
    });
    structure["packages/oracle"] = {
      files: oracleResult.files,
      dependencies: oracleResult.dependencies,
      setupInstructions: oracleResult.setupInstructions,
    };
    setupInstructions.push("5. Deploy oracle: cd packages/oracle && npm install && npm run deploy");
  }

  // Generate root files with scripts
  const rootFiles: Record<string, string> = {
    "package.json": JSON.stringify(
      {
        name: projectName,
        version: "1.0.0",
        private: true,
        workspaces: ["packages/*"],
        scripts: {
          setup: "bash setup.sh",
          deploy: "bash deploy.sh",
          start: "bash start.sh",
          "dev:frontend": "npm run dev --workspace=packages/frontend",
          "dev:backend": "npm run dev --workspace=packages/backend",
          "build:contracts": "cd packages/contracts && cargo build --release --target wasm32-unknown-unknown",
        },
      },
      null,
      2
    ),

    "README.md": `# ${projectName}

Full-stack Arbitrum dApp generated with ARBuilder.

## Quick Start

\`\`\`bash
# 1. Install all dependencies
./setup.sh

# 2. Configure .env with your keys, then deploy contract
./deploy.sh

# 3. Start backend + frontend
./start.sh
\`\`\`

## Project Structure

\`\`\`
${projectName}/
├── packages/
${Object.keys(structure)
  .map((pkg) => `│   ├── ${pkg.replace("packages/", "")}/`)
  .join("\n")}
├── setup.sh
├── deploy.sh
├── start.sh
└── .env.example
\`\`\`

## Network

Target network: ${network}

## Generated with ARBuilder

https://arbbuilder.whymelabs.com
`,

    ".gitignore": `# Dependencies
node_modules/
.pnpm-store/

# Build outputs
dist/
.next/
target/

# Environment
.env
.env.local
*.pem

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db
`,

    ".env.example": generateEnvTemplate(components, network),
    "setup.sh": generateSetupScript(components),
    "deploy.sh": generateDeployScript(components),
    "start.sh": generateStartScript(components),
  };

  return {
    projectName,
    structure,
    rootFiles,
    setupInstructions: [
      `Project: ${projectName}`,
      `Network: ${network}`,
      "",
      "Quick Start:",
      "1. ./setup.sh   — install all dependencies",
      "2. Edit .env with your PRIVATE_KEY and RPC_URL",
      "3. ./deploy.sh  — build and deploy the contract",
      "4. ./start.sh   — launch backend + frontend",
    ],
    disclaimer: TEMPLATE_DISCLAIMER,
  };
}

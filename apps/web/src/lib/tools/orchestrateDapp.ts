/**
 * Orchestrate full dApp scaffolding (M3 tool)
 */

import { generateBackend } from "./generateBackend";
import { generateFrontend } from "./generateFrontend";
import { generateIndexer } from "./generateIndexer";
import { generateOracle } from "./generateOracle";

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
}

// Stylus contract template (simplified)
const STYLUS_CONTRACT_TEMPLATE = `#![cfg_attr(not(any(feature = "export-abi", test)), no_std)]
#![cfg_attr(not(test), no_main)]
extern crate alloc;

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
        let sender = msg::sender();
        let amount = msg::value();
        let current = self.balances.get(sender);
        self.balances.insert(sender, current + amount);
    }

    pub fn withdraw(&mut self, amount: U256) {
        let sender = msg::sender();
        let current = self.balances.get(sender);
        if current >= amount {
            self.balances.insert(sender, current - amount);
            // Transfer would go here
        }
    }
}
`;

const CARGO_TOML = `[package]
name = "my-contract"
version = "0.1.0"
edition = "2021"

[dependencies]
stylus-sdk = "0.9.2"
alloy-primitives = "=0.8.20"
alloy-sol-types = "=0.8.20"

[features]
export-abi = ["stylus-sdk/export-abi"]

[lib]
crate-type = ["cdylib"]

[profile.release]
codegen-units = 1
strip = true
lto = true
panic = "abort"
opt-level = "s"
`;

function generateProjectName(prompt: string): string {
  // Extract a simple name from the prompt
  const words = prompt.toLowerCase().split(/\s+/);
  const keywords = words.filter(
    (w) => w.length > 3 && !["create", "build", "make", "with", "using", "dapp", "app"].includes(w)
  );
  const name = keywords.slice(0, 2).join("-") || "my-dapp";
  return name.replace(/[^a-z0-9-]/g, "");
}

export function orchestrateDapp(args: OrchestrateDappArgs): OrchestrateDappResult {
  const {
    prompt,
    components = ["contract", "frontend"],
    network = "arbitrum-sepolia",
    contractAddress,
    contractAbi,
  } = args;

  const projectName = generateProjectName(prompt);
  const structure: Record<string, ComponentResult> = {};
  const setupInstructions: string[] = [];

  // Generate each component
  if (components.includes("contract")) {
    structure["packages/contracts"] = {
      files: {
        "src/lib.rs": STYLUS_CONTRACT_TEMPLATE,
        "Cargo.toml": CARGO_TOML,
        ".cargo/config.toml": `[build]
target = "wasm32-unknown-unknown"

[target.wasm32-unknown-unknown]
rustflags = ["-C", "link-arg=-zstack-size=32768"]
`,
      },
      setupInstructions: [
        "cd packages/contracts",
        "cargo build --release --target wasm32-unknown-unknown",
        "cargo stylus check",
        "cargo stylus deploy --private-key-path=./key.txt",
      ],
    };
    setupInstructions.push("1. Deploy contract: cd packages/contracts && cargo stylus deploy");
  }

  if (components.includes("backend")) {
    const backendResult = generateBackend({
      prompt,
      framework: "nestjs",
      contractAbi,
    });
    structure["packages/backend"] = {
      files: backendResult.files,
      dependencies: backendResult.dependencies,
      setupInstructions: backendResult.setupInstructions,
    };
    setupInstructions.push("2. Start backend: cd packages/backend && npm install && npm run dev");
  }

  if (components.includes("frontend")) {
    const frontendResult = generateFrontend({
      prompt,
      contractAbi,
      uiFramework: "daisyui",
      template: "dashboard",
    });
    structure["packages/frontend"] = {
      files: frontendResult.files,
      dependencies: frontendResult.dependencies,
      setupInstructions: frontendResult.setupInstructions,
    };
    setupInstructions.push("3. Start frontend: cd packages/frontend && npm install && npm run dev");
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

  // Generate root files for monorepo
  const rootFiles: Record<string, string> = {
    "package.json": JSON.stringify(
      {
        name: projectName,
        version: "1.0.0",
        private: true,
        workspaces: ["packages/*"],
        scripts: {
          "dev:frontend": "npm run dev --workspace=packages/frontend",
          "dev:backend": "npm run dev --workspace=packages/backend",
          "build:contracts": "cd packages/contracts && cargo build --release --target wasm32-unknown-unknown",
          "deploy:contracts": "cd packages/contracts && cargo stylus deploy",
          "deploy:indexer": "npm run deploy --workspace=packages/indexer",
        },
        devDependencies: {
          "turbo": "^2.0.0",
        },
      },
      null,
      2
    ),

    "turbo.json": JSON.stringify(
      {
        $schema: "https://turbo.build/schema.json",
        pipeline: {
          build: {
            dependsOn: ["^build"],
            outputs: ["dist/**", ".next/**"],
          },
          dev: {
            cache: false,
            persistent: true,
          },
        },
      },
      null,
      2
    ),

    "README.md": `# ${projectName}

Full-stack Arbitrum dApp generated with ARBuilder.

## Project Structure

\`\`\`
${projectName}/
├── packages/
${Object.keys(structure)
  .map((pkg) => `│   ├── ${pkg.replace("packages/", "")}/`)
  .join("\n")}
├── package.json
└── turbo.json
\`\`\`

## Setup

${setupInstructions.map((step, i) => `${step}`).join("\n")}

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

    ".env.example": `# Network
NETWORK=${network}

# Contract (update after deployment)
CONTRACT_ADDRESS=0x...

# Frontend
NEXT_PUBLIC_WALLET_CONNECT_ID=your-project-id
NEXT_PUBLIC_CONTRACT_ADDRESS=0x...

# Backend
RPC_URL=https://${network === "arbitrum-one" ? "arb1" : "sepolia-rollup"}.arbitrum.io/rpc
PRIVATE_KEY=your-private-key
`,
  };

  return {
    projectName,
    structure,
    rootFiles,
    setupInstructions: [
      `Project: ${projectName}`,
      `Network: ${network}`,
      "",
      "Setup Steps:",
      ...setupInstructions,
      "",
      "Quick Start:",
      "1. npm install (in root)",
      "2. Copy .env.example to .env and configure",
      "3. Deploy contracts first, then update addresses",
      "4. Start frontend and backend",
    ],
  };
}

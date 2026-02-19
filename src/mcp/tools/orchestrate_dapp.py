"""
Orchestrate full dApp generation.

This tool coordinates the generation of complete dApps by:
1. Generating Stylus smart contracts
2. Extracting ABI from generated contract
3. Generating backend services (with contract ABI injected)
4. Generating frontend applications (with contract ABI injected)
5. Generating subgraph indexers
6. Generating oracle integrations
7. Generating executable setup/deploy/start scripts

It acts as a high-level coordinator that calls other tools.
"""

import json
from typing import Any, List, Optional

from .base import BaseTool
from .generate_stylus_code import TEMPLATE_DISCLAIMER
from ...templates import (
    select_stylus_template,
    select_backend_template,
    select_frontend_template,
    select_indexer_template,
    select_oracle_template,
)
from ...templates.backend_templates import render_with_abi as render_backend_abi
from ...templates.frontend_templates import render_with_abi as render_frontend_abi
from ...utils.abi_extractor import extract_abi_from_code, abi_to_viem_human_readable
from ...utils.env_config import generate_env_template, BACKEND_PORT, FRONTEND_PORT


class OrchestrateDappTool(BaseTool):
    """Orchestrate generation of complete dApps."""

    name = "orchestrate_dapp"
    description = """Scaffold a template-based dApp monorepo with starter components.

Generates a production-ready project structure with generic templates for:
- Smart contracts (Stylus Rust/WASM) — selected by contract_type parameter
- Backend services (NestJS/Express with viem)
- Frontend applications (Next.js with wagmi/RainbowKit)
- Subgraph indexers (The Graph)
- Oracle integrations (Chainlink)

Generates executable setup.sh, deploy.sh, and start.sh scripts.
ABI is auto-extracted from the contract and injected into backend/frontend.
Templates provide a working starting point — customize for your specific use case."""

    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Description of the dApp to generate",
            },
            "components": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["contract", "backend", "frontend", "indexer", "oracle"],
                },
                "description": "Components to generate (default: all)",
                "default": ["contract", "backend", "frontend"],
            },
            "network": {
                "type": "string",
                "enum": ["arbitrum", "arbitrumSepolia"],
                "description": "Target network",
                "default": "arbitrumSepolia",
            },
            "backend_framework": {
                "type": "string",
                "enum": ["nestjs", "express"],
                "description": "Backend framework to use",
                "default": "nestjs",
            },
            "include_tests": {
                "type": "boolean",
                "description": "Include test files for all components",
                "default": False,
            },
            "contract_type": {
                "type": "string",
                "enum": ["counter", "token", "nft", "defi", "custom"],
                "description": "Type of smart contract",
                "default": "custom",
            },
        },
        "required": ["prompt"],
    }

    def __init__(self, vectordb=None):
        """Initialize with optional vector database."""
        super().__init__()
        self.vectordb = vectordb

    def execute(self, **kwargs) -> dict[str, Any]:
        """Generate a complete dApp with the specified components."""
        prompt = kwargs.get("prompt", "")
        components = kwargs.get("components", ["contract", "backend", "frontend"])
        network = kwargs.get("network", "arbitrumSepolia")
        backend_framework = kwargs.get("backend_framework", "nestjs")
        include_tests = kwargs.get("include_tests", False)
        contract_type = kwargs.get("contract_type", "custom")

        # Validate inputs
        if not prompt:
            return {"error": "prompt is required"}

        # Context retrieval (template-based generation doesn't require RAG)
        context = []

        # Generate project structure
        project = {
            "name": self._generate_project_name(prompt),
            "description": prompt,
            "network": network,
            "components": {},
            "shared_config": self._generate_shared_config(network),
            "monorepo_structure": self._generate_monorepo_structure(components),
            "setup_instructions": [],
        }

        # Extract ABI from contract for injection into backend/frontend
        abi_json = []
        abi_human_readable = []

        # Generate each component
        if "contract" in components:
            project["components"]["contract"] = self._generate_contract(
                prompt, contract_type, include_tests
            )
            project["setup_instructions"].append("1. Run ./setup.sh to install dependencies")

            # Extract ABI from contract lib.rs
            lib_rs = project["components"]["contract"]["files"].get("src/lib.rs", "")
            if lib_rs:
                abi_json = extract_abi_from_code(lib_rs)
                abi_human_readable = abi_to_viem_human_readable(abi_json)
                project["components"]["contract"]["abi"] = abi_json
                project["components"]["contract"]["abi_human_readable"] = abi_human_readable

        if "backend" in components:
            project["components"]["backend"] = self._generate_backend(
                prompt, backend_framework, include_tests, abi_json, abi_human_readable
            )
            project["setup_instructions"].append("2. Run ./deploy.sh to build and deploy the contract")

        if "frontend" in components:
            project["components"]["frontend"] = self._generate_frontend(
                prompt, include_tests, abi_human_readable
            )
            project["setup_instructions"].append("3. Run ./start.sh to launch backend + frontend")

        if "indexer" in components:
            project["components"]["indexer"] = self._generate_indexer(
                prompt, network, abi_json=abi_json, abi_human_readable=abi_human_readable
            )
            project["setup_instructions"].append("4. Deploy the subgraph to index contract events")

        if "oracle" in components:
            project["components"]["oracle"] = self._generate_oracle(
                prompt, network, abi_json=abi_json
            )
            project["setup_instructions"].append("5. Set up Chainlink oracle integration")

        # Generate root configuration files (includes scripts)
        project["root_files"] = self._generate_root_files(
            project, components, network, backend_framework
        )

        # Add development workflow
        project["development_workflow"] = self._generate_dev_workflow(components)

        if context:
            project["references"] = [
                {
                    "source": c.get("metadata", {}).get("source", "Unknown"),
                    "relevance": c.get("distance", 0),
                }
                for c in context[:5]
            ]

        project["disclaimer"] = TEMPLATE_DISCLAIMER
        return project

    def _generate_project_name(self, prompt: str) -> str:
        """Generate a project name from the prompt."""
        words = prompt.lower().split()[:3]
        name = "-".join(w for w in words if w.isalnum())[:30]
        return name or "dapp"

    def _generate_shared_config(self, network: str) -> dict:
        """Generate shared configuration for all components."""
        networks = {
            "arbitrum": {
                "chainId": 42161,
                "rpcUrl": "https://arb1.arbitrum.io/rpc",
                "blockExplorer": "https://arbiscan.io",
            },
            "arbitrumSepolia": {
                "chainId": 421614,
                "rpcUrl": "https://sepolia-rollup.arbitrum.io/rpc",
                "blockExplorer": "https://sepolia.arbiscan.io",
            },
        }

        return {
            "network": networks.get(network, networks["arbitrumSepolia"]),
        }

    def _generate_monorepo_structure(self, components: List[str]) -> dict:
        """Generate monorepo directory structure."""
        structure = {
            "root": [
                ".env.example", ".gitignore", "README.md", "package.json",
                "setup.sh", "deploy.sh", "start.sh",
            ],
        }

        if "contract" in components:
            structure["packages/contract"] = [
                "src/lib.rs",
                "Cargo.toml",
                "src/main.rs",
                "Stylus.toml",
                "rust-toolchain.toml",
            ]

        if "backend" in components:
            structure["packages/backend"] = [
                "src/",
                "package.json",
                "tsconfig.json",
                ".env.example",
            ]

        if "frontend" in components:
            structure["packages/frontend"] = [
                "src/",
                "public/",
                "package.json",
                "next.config.js",
                ".env.example",
            ]

        if "indexer" in components:
            structure["packages/indexer"] = [
                "src/",
                "schema.graphql",
                "subgraph.yaml",
                "package.json",
            ]

        if "oracle" in components:
            structure["packages/oracle"] = [
                "contracts/",
                "scripts/",
                "hardhat.config.ts",
                "package.json",
            ]

        return structure

    def _generate_contract(self, prompt: str, contract_type: str, include_tests: bool) -> dict:
        """Generate smart contract component."""
        template = select_stylus_template(contract_type, prompt)

        files = {
            "src/lib.rs": template.lib_rs,
            "Cargo.toml": template.cargo_toml,
            "src/main.rs": template.main_rs,
        }

        # SDK 0.10.0+ requires Stylus.toml and rust-toolchain.toml
        if template.stylus_toml:
            files["Stylus.toml"] = template.stylus_toml
        if template.rust_toolchain_toml:
            files["rust-toolchain.toml"] = template.rust_toolchain_toml

        result = {
            "template": template.name,
            "type": contract_type,
            "files": files,
            "sdk_version": template.sdk_version,
            "features": template.features,
            "build_commands": {
                "check": "cargo build --target wasm32-unknown-unknown --release",
                "export_abi": "cargo run --features export-abi",
                "deploy": "cargo stylus deploy --private-key $PRIVATE_KEY",
            },
        }

        return result

    def _generate_backend(
        self,
        prompt: str,
        framework: str,
        include_tests: bool,
        abi_json: list,
        abi_human_readable: list,
    ) -> dict:
        """Generate backend component with ABI injected."""
        template = select_backend_template(framework, prompt)

        # Render files with actual ABI replacing placeholders
        files = template.files
        if abi_json:
            files = render_backend_abi(files, abi_json, abi_human_readable)

        return {
            "template": template.name,
            "framework": framework,
            "files": files,
            "dependencies": template.dependencies,
            "dev_dependencies": template.dev_dependencies,
            "scripts": template.scripts,
            "env_vars": template.env_vars,
        }

    def _generate_frontend(
        self,
        prompt: str,
        include_tests: bool,
        abi_human_readable: list,
    ) -> dict:
        """Generate frontend component with ABI injected."""
        template = select_frontend_template(prompt)

        # Render files with actual ABI replacing placeholders
        files = template.files
        if abi_human_readable:
            files = render_frontend_abi(files, abi_human_readable)

        return {
            "template": template.name,
            "framework": "nextjs",
            "files": files,
            "dependencies": template.dependencies,
            "dev_dependencies": template.dev_dependencies,
            "scripts": template.scripts,
            "env_vars": template.env_vars,
        }

    def _generate_indexer(
        self,
        prompt: str,
        network: str,
        abi_json: Optional[list] = None,
        abi_human_readable: Optional[list] = None,
    ) -> dict:
        """Generate indexer component with optional ABI-aware schema."""
        template = select_indexer_template(prompt)
        files = dict(template.files)

        # If ABI is available, generate custom schema and mapping from events
        if abi_json:
            events = [e for e in abi_json if e.get("type") == "event"]
            if events:
                files["schema.graphql"] = self._generate_indexer_schema(events)
                files["src/mapping.ts"] = self._generate_indexer_mapping(events)

        return {
            "template": template.name,
            "type": template.template_type,
            "files": files,
            "dependencies": template.dependencies,
            "networks": template.networks,
            "commands": {
                "codegen": "graph codegen",
                "build": "graph build",
                "deploy": "graph deploy --studio <subgraph-name>",
            },
        }

    @staticmethod
    def _generate_indexer_schema(events: list) -> str:
        """Generate schema.graphql entities from contract events."""
        entities = []
        for event in events:
            name = event.get("name", "UnknownEvent")
            fields = []
            for inp in event.get("inputs", []):
                field_name = inp.get("name", "field")
                sol_type = inp.get("type", "uint256")
                gql_type = "BigInt" if "int" in sol_type else ("Bytes" if sol_type == "address" else "String")
                fields.append(f"  {field_name}: {gql_type}!")
            fields_str = "\n".join(fields)
            entities.append(
                f"type {name}Event @entity {{\n  id: ID!\n  blockNumber: BigInt!\n  blockTimestamp: BigInt!\n  transactionHash: Bytes!\n{fields_str}\n}}"
            )
        return "\n\n".join(entities) + "\n"

    @staticmethod
    def _generate_indexer_mapping(events: list) -> str:
        """Generate mapping.ts handlers from contract events."""
        imports = []
        handlers = []
        for event in events:
            name = event.get("name", "UnknownEvent")
            imports.append(f"  {name} as {name}Event")
            field_assignments = []
            for inp in event.get("inputs", []):
                field_name = inp.get("name", "field")
                field_assignments.append(f"  entity.{field_name} = event.params.{field_name};")
            assignments_str = "\n".join(field_assignments)
            handlers.append(
                f"export function handle{name}(event: {name}Event): void {{\n"
                f"  let entity = new {name}EventEntity(\n"
                f"    event.transaction.hash.concatI32(event.logIndex.toI32())\n"
                f"  );\n"
                f"  entity.blockNumber = event.block.number;\n"
                f"  entity.blockTimestamp = event.block.timestamp;\n"
                f"  entity.transactionHash = event.transaction.hash;\n"
                f"{assignments_str}\n"
                f"  entity.save();\n"
                f"}}"
            )
        imports_str = ",\n".join(imports)
        handlers_str = "\n\n".join(handlers)
        return (
            f'import {{\n{imports_str}\n}} from "../generated/Contract/Contract";\n'
            f'import {{\n'
            + ",\n".join(f"  {e.get('name', '')}Event as {e.get('name', '')}EventEntity" for e in events)
            + f'\n}} from "../generated/schema";\n\n'
            f"{handlers_str}\n"
        )

    def _generate_oracle(
        self,
        prompt: str,
        network: str,
        abi_json: Optional[list] = None,
    ) -> dict:
        """Generate oracle component with deployable Hardhat scaffold."""
        template = select_oracle_template(prompt)
        network_key = "arbitrumSepolia" if network == "arbitrumSepolia" else "arbitrum"
        network_config = template.networks.get(network_key, {})

        # Build deployable files
        files = {}
        files["contracts/OracleConsumer.sol"] = template.solidity_code
        files["scripts/deploy.ts"] = self._generate_oracle_deploy_script(
            template, network
        )
        files["hardhat.config.ts"] = self._generate_oracle_hardhat_config()
        files["package.json"] = self._generate_oracle_package_json(network)
        files[".env.example"] = "PRIVATE_KEY=your-private-key-without-0x-prefix\n"

        if template.frontend_hook:
            files["src/hooks/useOracle.ts"] = template.frontend_hook

        return {
            "template": template.name,
            "type": template.oracle_type,
            "files": files,
            "solidity_code": template.solidity_code,
            "stylus_code": template.stylus_code,
            "frontend_hook": template.frontend_hook,
            "network_config": network_config,
            "features": template.features,
        }

    @staticmethod
    def _generate_oracle_deploy_script(template, network: str) -> str:
        """Generate a Hardhat deploy script for the oracle contract."""
        network_key = "arbitrumSepolia" if network == "arbitrumSepolia" else "arbitrum"
        network_config = template.networks.get(network_key, {})

        if template.oracle_type == "price_feed":
            feed_address = network_config.get("ETH/USD", "0x...")
            return f'''import {{ ethers }} from "hardhat";

async function main() {{
  const priceFeedAddress = "{feed_address}";
  const PriceFeedConsumer = await ethers.getContractFactory("PriceFeedConsumer");
  const consumer = await PriceFeedConsumer.deploy(priceFeedAddress);
  await consumer.waitForDeployment();
  console.log("PriceFeedConsumer deployed to:", await consumer.getAddress());
}}

main().catch((error) => {{
  console.error(error);
  process.exitCode = 1;
}});
'''
        # Default deploy script for other oracle types
        contract_name = template.name.replace(" ", "")
        return f'''import {{ ethers }} from "hardhat";

async function main() {{
  const {contract_name} = await ethers.getContractFactory("{contract_name}");
  const contract = await {contract_name}.deploy();
  await contract.waitForDeployment();
  console.log("{contract_name} deployed to:", await contract.getAddress());
}}

main().catch((error) => {{
  console.error(error);
  process.exitCode = 1;
}});
'''

    @staticmethod
    def _generate_oracle_hardhat_config() -> str:
        """Generate Hardhat config for oracle package."""
        return '''import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import "dotenv/config";

const config: HardhatUserConfig = {
  solidity: "0.8.19",
  networks: {
    arbitrumSepolia: {
      url: "https://sepolia-rollup.arbitrum.io/rpc",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
    },
    arbitrumOne: {
      url: "https://arb1.arbitrum.io/rpc",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
    },
  },
};

export default config;
'''

    @staticmethod
    def _generate_oracle_package_json(network: str) -> str:
        """Generate package.json for oracle package."""
        network_flag = "arbitrumSepolia" if network == "arbitrumSepolia" else "arbitrumOne"
        pkg = {
            "name": "arbbuilder-oracle",
            "version": "1.0.0",
            "scripts": {
                "compile": "hardhat compile",
                "deploy": f"hardhat run scripts/deploy.ts --network {network_flag}",
                "test": "hardhat test",
            },
            "devDependencies": {
                "@nomicfoundation/hardhat-toolbox": "^4.0.0",
                "hardhat": "^2.19.0",
                "@chainlink/contracts": "^1.1.0",
                "dotenv": "^16.0.0",
            },
        }
        return json.dumps(pkg, indent=2)

    def _generate_root_files(
        self,
        project: dict,
        components: List[str],
        network: str,
        backend_framework: str = "nestjs",
    ) -> dict[str, str]:
        """Generate root-level configuration files including executable scripts."""
        files = {}

        # README.md
        readme_lines = [
            f"# {project['name'].replace('-', ' ').title()}",
            "",
            f"> {project['description']}",
            "",
            "## Quick Start",
            "",
            "```bash",
            "# 1. Install all dependencies",
            "./setup.sh",
            "",
            "# 2. Configure .env with your keys, then deploy contract",
            "./deploy.sh",
            "",
            "# 3. Start backend + frontend",
            "./start.sh",
            "```",
            "",
            "## Project Structure",
            "",
            "```",
        ]
        for path, contents in project["monorepo_structure"].items():
            readme_lines.append(f"{path}/")
            for item in contents[:5]:
                readme_lines.append(f"  {item}")
        readme_lines.extend([
            "```",
            "",
            "## Setup",
            "",
        ])
        for instruction in project["setup_instructions"]:
            readme_lines.append(instruction)
        readme_lines.extend([
            "",
            "## Development",
            "",
            "See individual package READMEs for detailed instructions.",
            "",
            "---",
            "Built with [ARBuilder](https://github.com/arbbuilder)",
        ])
        files["README.md"] = "\n".join(readme_lines)

        # .gitignore
        files[".gitignore"] = """# Dependencies
node_modules/
.pnp
.pnp.js

# Build outputs
dist/
build/
.next/
out/
target/

# Environment
.env
.env.local
.env.*.local

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Testing
coverage/

# Rust
Cargo.lock
*.wasm

# Logs
*.log
npm-debug.log*
"""

        # Root package.json for monorepo
        workspaces = []
        if "contract" in components:
            workspaces.append("packages/contract")
        if "backend" in components:
            workspaces.append("packages/backend")
        if "frontend" in components:
            workspaces.append("packages/frontend")
        if "indexer" in components:
            workspaces.append("packages/indexer")
        if "oracle" in components:
            workspaces.append("packages/oracle")

        files["package.json"] = json.dumps({
            "name": project["name"],
            "private": True,
            "workspaces": workspaces,
            "scripts": {
                "setup": "bash setup.sh",
                "deploy": "bash deploy.sh",
                "start": "bash start.sh",
                "dev:backend": "npm run dev --workspace=packages/backend",
                "dev:frontend": "npm run dev --workspace=packages/frontend",
                "build": "npm run build --workspaces",
                "test": "npm run test --workspaces --if-present",
            },
        }, indent=2)

        # .env.example — from centralized config
        files[".env.example"] = generate_env_template(components, network)

        # Executable scripts
        files["setup.sh"] = self._generate_setup_script(components, backend_framework)
        files["deploy.sh"] = self._generate_deploy_script(components)
        files["start.sh"] = self._generate_start_script(components)

        return files

    def _generate_setup_script(
        self, components: List[str], backend_framework: str = "nestjs"
    ) -> str:
        """Generate setup.sh that installs all dependencies.

        Uses a scaffold-first, backfill pattern: official CLI tools scaffold
        into a temp dir, then only config files missing from the project are
        copied over.  Custom business-logic files (lib.rs, pages, etc.) that
        were already written by the MCP tool always take precedence.
        """
        lines = [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            'echo "=== ARBuilder dApp Setup ==="',
            "",
            "# Copy env template if .env doesn't exist",
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
        ]

        if "contract" in components:
            lines.extend([
                "# Contract dependencies",
                'echo "Installing Rust toolchain..."',
                "rustup target add wasm32-unknown-unknown 2>/dev/null || true",
                "cargo install cargo-stylus 2>/dev/null || true",
                "",
                "# Scaffold contract baseline with cargo stylus new",
                "if command -v cargo-stylus &>/dev/null || cargo stylus --version &>/dev/null 2>&1; then",
                '  echo "  Scaffolding contract config from cargo stylus new..."',
                "  SCAFFOLD_TMP=$(mktemp -d)",
                '  cargo stylus new "$SCAFFOLD_TMP/scaffold" 2>/dev/null && \\',
                '    backfill_from_scaffold "$SCAFFOLD_TMP/scaffold" packages/contract || \\',
                '    echo "  (scaffold skipped — cargo stylus new failed)"',
                '  rm -rf "$SCAFFOLD_TMP"',
                "else",
                '  echo "  (scaffold skipped — cargo-stylus not available)"',
                "fi",
                "",
            ])

        if "backend" in components:
            # NestJS gets scaffold; Express does not
            if backend_framework == "nestjs":
                lines.extend([
                    "# Scaffold backend baseline with @nestjs/cli",
                    "if command -v npx &>/dev/null; then",
                    '  echo "  Scaffolding backend config from @nestjs/cli..."',
                    "  SCAFFOLD_TMP=$(mktemp -d)",
                    '  npx @nestjs/cli@latest new scaffold --package-manager npm --skip-git --skip-install --directory "$SCAFFOLD_TMP" 2>/dev/null && \\',
                    '    backfill_from_scaffold "$SCAFFOLD_TMP/scaffold" packages/backend || \\',
                    '    echo "  (scaffold skipped — @nestjs/cli failed)"',
                    '  rm -rf "$SCAFFOLD_TMP"',
                    "else",
                    '  echo "  (scaffold skipped — npx not available)"',
                    "fi",
                    "",
                ])

            lines.extend([
                "# Backend dependencies",
                'echo "Installing backend dependencies..."',
                "cd packages/backend",
                "npm install",
                "cd ../..",
                "",
            ])

        if "frontend" in components:
            lines.extend([
                "# Scaffold frontend baseline with create-next-app",
                "if command -v npx &>/dev/null; then",
                '  echo "  Scaffolding frontend config from create-next-app..."',
                "  SCAFFOLD_TMP=$(mktemp -d)",
                '  npx create-next-app@latest "$SCAFFOLD_TMP/scaffold" --ts --tailwind --app --src-dir --use-npm --no-git --no-eslint --skip-install 2>/dev/null && \\',
                '    backfill_from_scaffold "$SCAFFOLD_TMP/scaffold" packages/frontend || \\',
                '    echo "  (scaffold skipped — create-next-app failed)"',
                '  rm -rf "$SCAFFOLD_TMP"',
                "else",
                '  echo "  (scaffold skipped — npx not available)"',
                "fi",
                "",
                "# Frontend dependencies",
                'echo "Installing frontend dependencies..."',
                "cd packages/frontend",
                "npm install",
                "cd ../..",
                "",
            ])

        if "indexer" in components:
            lines.extend([
                "# Indexer dependencies",
                'echo "Installing indexer dependencies..."',
                "cd packages/indexer",
                "npm install",
                "cd ../..",
                "",
            ])

        if "oracle" in components:
            lines.extend([
                "# Oracle dependencies",
                'echo "Installing oracle dependencies..."',
                "cd packages/oracle",
                "npm install",
                "cd ../..",
                "",
            ])

        lines.extend([
            'echo ""',
            'echo "Setup complete!"',
            'echo "Next: edit .env with your PRIVATE_KEY and RPC_URL, then run ./deploy.sh"',
        ])

        return "\n".join(lines)

    def _generate_deploy_script(self, components: List[str]) -> str:
        """Generate deploy.sh that builds and deploys the contract."""
        lines = [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            "# Load environment variables",
            "if [ -f .env ]; then",
            "  set -a",
            "  source .env",
            "  set +a",
            "fi",
            "",
            'echo "=== ARBuilder dApp Deploy ==="',
            "",
        ]

        if "contract" in components:
            lines.extend([
                "# Build contract",
                'echo "Building Stylus contract..."',
                "cd packages/contract",
                "cargo build --target wasm32-unknown-unknown --release",
                "",
                "# Deploy contract",
                'echo "Deploying to ${NETWORK:-arbitrumSepolia}..."',
                'DEPLOY_OUTPUT=$(cargo stylus deploy \\',
                '  --private-key "$PRIVATE_KEY" \\',
                '  --endpoint "$RPC_URL" 2>&1) || {',
                '  echo "Deployment failed:"',
                '  echo "$DEPLOY_OUTPUT"',
                '  exit 1',
                "}",
                "",
                "# Capture deployed address",
                "DEPLOYED_ADDRESS=$(echo \"$DEPLOY_OUTPUT\" | grep -oE '0x[a-fA-F0-9]{40}' | head -1)",
                "",
                'if [ -n "$DEPLOYED_ADDRESS" ]; then',
                '  echo "Contract deployed at: $DEPLOYED_ADDRESS"',
                "",
                "  # Update .env files with deployed address",
                "  cd ../..",
                '  sed -i.bak "s|CONTRACT_ADDRESS=.*|CONTRACT_ADDRESS=$DEPLOYED_ADDRESS|" .env',
                '  sed -i.bak "s|NEXT_PUBLIC_CONTRACT_ADDRESS=.*|NEXT_PUBLIC_CONTRACT_ADDRESS=$DEPLOYED_ADDRESS|" .env',
                "  rm -f .env.bak",
                "",
                '  echo "Updated .env with CONTRACT_ADDRESS=$DEPLOYED_ADDRESS"',
                "else",
                '  echo "Could not extract contract address from deploy output."',
                '  echo "Please update CONTRACT_ADDRESS in .env manually."',
                '  echo "Deploy output:"',
                '  echo "$DEPLOY_OUTPUT"',
                '  cd ../..',
                "fi",
                "",
            ])

        if "oracle" in components:
            lines.extend([
                "# Oracle deploy",
                'if [ -d "packages/oracle" ]; then',
                '  echo "Deploying oracle contract..."',
                "  cd packages/oracle",
                '  npx hardhat run scripts/deploy.ts --network ${NETWORK:-arbitrumSepolia}',
                "  cd ../..",
                "fi",
                "",
            ])

        if "indexer" in components:
            lines.extend([
                "# Indexer deploy",
                'if [ -d "packages/indexer" ]; then',
                '  echo "Building subgraph..."',
                "  cd packages/indexer",
                "  npm run codegen",
                "  npm run build",
                '  if [ -n "${GRAPH_DEPLOY_KEY:-}" ]; then',
                '    echo "Deploying subgraph..."',
                '    graph deploy --studio ${SUBGRAPH_NAME:-my-subgraph} --deploy-key "$GRAPH_DEPLOY_KEY"',
                "  else",
                '    echo "Skipping subgraph deploy (set GRAPH_DEPLOY_KEY and SUBGRAPH_NAME in .env to auto-deploy)"',
                "  fi",
                "  cd ../..",
                "fi",
                "",
            ])

        lines.extend([
            'echo ""',
            'echo "Deploy complete! Run ./start.sh to launch the dApp."',
        ])

        return "\n".join(lines)

    def _generate_start_script(self, components: List[str]) -> str:
        """Generate start.sh that launches backend + frontend."""
        lines = [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            "# Load environment variables",
            "if [ -f .env ]; then",
            "  set -a",
            "  source .env",
            "  set +a",
            "fi",
            "",
            'echo "=== ARBuilder dApp Start ==="',
            "",
            "# Track background PIDs for cleanup",
            "PIDS=()",
            "",
            "cleanup() {",
            '  echo ""',
            '  echo "Shutting down services..."',
            '  for pid in "${PIDS[@]}"; do',
            "    kill $pid 2>/dev/null || true",
            "  done",
            '  echo "All services stopped."',
            "  exit 0",
            "}",
            "",
            "trap cleanup SIGINT SIGTERM",
            "",
        ]

        if "backend" in components:
            lines.extend([
                "# Start backend",
                f'echo "Starting backend on port ${{PORT:-{BACKEND_PORT}}}..."',
                "cd packages/backend",
                "npm run start:dev &",
                "PIDS+=($!)",
                "cd ../..",
                "",
            ])

        if "frontend" in components:
            lines.extend([
                "# Start frontend",
                f'echo "Starting frontend on port {FRONTEND_PORT}..."',
                "cd packages/frontend",
                "npm run dev &",
                "PIDS+=($!)",
                "cd ../..",
                "",
            ])

        lines.extend([
            "# Print service URLs",
            'echo ""',
            'echo "Services running:"',
        ])

        if "backend" in components:
            lines.append(f'echo "  Backend:  http://localhost:${{PORT:-{BACKEND_PORT}}}"')

        if "frontend" in components:
            lines.append(f'echo "  Frontend: http://localhost:{FRONTEND_PORT}"')

        lines.extend([
            'echo ""',
            'echo "Press Ctrl+C to stop all services."',
            "",
            "# Wait for all background processes",
            "wait",
        ])

        return "\n".join(lines)

    def _generate_dev_workflow(self, components: List[str]) -> dict:
        """Generate development workflow guide."""
        steps = []

        if "contract" in components:
            steps.append({
                "step": 1,
                "component": "Smart Contract",
                "actions": [
                    "./setup.sh",
                    "Edit .env with your PRIVATE_KEY and RPC_URL",
                    "./deploy.sh",
                ],
            })

        if "backend" in components or "frontend" in components:
            steps.append({
                "step": 2,
                "component": "Backend + Frontend",
                "actions": [
                    "./start.sh",
                    f"Backend runs on http://localhost:{BACKEND_PORT}",
                    f"Frontend runs on http://localhost:{FRONTEND_PORT}",
                ],
            })

        if "indexer" in components:
            steps.append({
                "step": 3,
                "component": "Subgraph Indexer",
                "actions": [
                    "cd packages/indexer",
                    "Update contract address in subgraph.yaml",
                    "npm run codegen && npm run deploy",
                ],
            })

        return {
            "steps": steps,
            "tips": [
                "Use a local test network like Anvil for development",
                "Deploy to Arbitrum Sepolia before mainnet",
                "Always test bridging flows on testnet first",
                "Keep private keys secure and never commit them",
            ],
        }

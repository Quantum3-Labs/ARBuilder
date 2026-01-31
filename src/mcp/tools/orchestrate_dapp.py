"""
Orchestrate full dApp generation.

This tool coordinates the generation of complete dApps by:
1. Generating Stylus smart contracts
2. Generating backend services
3. Generating frontend applications
4. Generating subgraph indexers
5. Generating oracle integrations

It acts as a high-level coordinator that calls other tools.
"""

import json
from typing import Any, List, Optional

from .base import BaseTool
from ...templates import (
    select_stylus_template,
    select_backend_template,
    select_frontend_template,
    select_indexer_template,
    select_oracle_template,
)
# Removed: agentic_rag import (template-based generation)


class OrchestrateDappTool(BaseTool):
    """Orchestrate generation of complete dApps."""

    name = "orchestrate_dapp"
    description = """Generate a complete dApp with multiple components.

This tool coordinates the generation of:
- Smart contracts (Stylus Rust/WASM)
- Backend services (NestJS/Express with viem)
- Frontend applications (Next.js with wagmi/RainbowKit)
- Subgraph indexers (The Graph)
- Oracle integrations (Chainlink)

Use this for full-stack dApp scaffolding with coordinated configurations."""

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

        # Generate each component
        if "contract" in components:
            project["components"]["contract"] = self._generate_contract(
                prompt, contract_type, include_tests
            )
            project["setup_instructions"].append("1. Deploy the smart contract first")

        if "backend" in components:
            project["components"]["backend"] = self._generate_backend(
                prompt, backend_framework, include_tests
            )
            project["setup_instructions"].append("2. Set up the backend with the contract address")

        if "frontend" in components:
            project["components"]["frontend"] = self._generate_frontend(
                prompt, include_tests
            )
            project["setup_instructions"].append("3. Configure the frontend with contract and backend URLs")

        if "indexer" in components:
            project["components"]["indexer"] = self._generate_indexer(prompt, network)
            project["setup_instructions"].append("4. Deploy the subgraph to index contract events")

        if "oracle" in components:
            project["components"]["oracle"] = self._generate_oracle(prompt, network)
            project["setup_instructions"].append("5. Set up Chainlink oracle integration")

        # Generate root configuration files
        project["root_files"] = self._generate_root_files(project, components)

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
            "env_template": f"""# Shared Environment Variables
NETWORK={network}
RPC_URL={networks.get(network, networks["arbitrumSepolia"])["rpcUrl"]}

# Contract (deployed address)
CONTRACT_ADDRESS=0x...

# Wallet (for deployment and transactions)
PRIVATE_KEY=0x...

# WalletConnect (for frontend)
NEXT_PUBLIC_WALLET_CONNECT_ID=...
""",
        }

    def _generate_monorepo_structure(self, components: List[str]) -> dict:
        """Generate monorepo directory structure."""
        structure = {
            "root": [".env.example", ".gitignore", "README.md", "package.json"],
        }

        if "contract" in components:
            structure["packages/contract"] = [
                "src/lib.rs",
                "Cargo.toml",
                "src/main.rs",
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

        return structure

    def _generate_contract(self, prompt: str, contract_type: str, include_tests: bool) -> dict:
        """Generate smart contract component."""
        template = select_stylus_template(contract_type, prompt)

        result = {
            "template": template.name,
            "type": contract_type,
            "files": {
                "src/lib.rs": template.lib_rs,
                "Cargo.toml": template.cargo_toml,
                "src/main.rs": template.main_rs,
            },
            "sdk_version": template.sdk_version,
            "features": template.features,
            "build_commands": {
                "check": "cargo +nightly build --target wasm32-unknown-unknown --release",
                "export_abi": "cargo run --features export-abi",
                "deploy": "cargo stylus deploy --private-key $PRIVATE_KEY",
            },
        }

        return result

    def _generate_backend(self, prompt: str, framework: str, include_tests: bool) -> dict:
        """Generate backend component."""
        template = select_backend_template(framework, prompt)

        return {
            "template": template.name,
            "framework": framework,
            "files": template.files,
            "dependencies": template.dependencies,
            "dev_dependencies": template.dev_dependencies,
            "scripts": template.scripts,
            "env_vars": template.env_vars,
        }

    def _generate_frontend(self, prompt: str, include_tests: bool) -> dict:
        """Generate frontend component."""
        template = select_frontend_template(prompt)

        return {
            "template": template.name,
            "framework": "nextjs",
            "files": template.files,
            "dependencies": template.dependencies,
            "dev_dependencies": template.dev_dependencies,
            "scripts": template.scripts,
            "env_vars": template.env_vars,
        }

    def _generate_indexer(self, prompt: str, network: str) -> dict:
        """Generate indexer component."""
        template = select_indexer_template(prompt)

        return {
            "template": template.name,
            "type": template.template_type,
            "files": template.files,
            "dependencies": template.dependencies,
            "networks": template.networks,
            "commands": {
                "codegen": "graph codegen",
                "build": "graph build",
                "deploy": "graph deploy --studio <subgraph-name>",
            },
        }

    def _generate_oracle(self, prompt: str, network: str) -> dict:
        """Generate oracle component."""
        template = select_oracle_template(prompt)

        return {
            "template": template.name,
            "type": template.oracle_type,
            "solidity_code": template.solidity_code,
            "stylus_code": template.stylus_code,
            "frontend_hook": template.frontend_hook,
            "network_config": template.networks.get(
                "arbitrumSepolia" if network == "arbitrumSepolia" else "arbitrum",
                {},
            ),
            "features": template.features,
        }

    def _generate_root_files(self, project: dict, components: List[str]) -> dict[str, str]:
        """Generate root-level configuration files."""
        files = {}

        # README.md
        readme_lines = [
            f"# {project['name'].replace('-', ' ').title()}",
            "",
            f"> {project['description']}",
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

        files["package.json"] = json.dumps({
            "name": project["name"],
            "private": True,
            "workspaces": workspaces,
            "scripts": {
                "dev:backend": "npm run dev --workspace=packages/backend",
                "dev:frontend": "npm run dev --workspace=packages/frontend",
                "build": "npm run build --workspaces",
                "test": "npm run test --workspaces --if-present",
            },
        }, indent=2)

        # .env.example
        files[".env.example"] = project["shared_config"]["env_template"]

        return files

    def _generate_dev_workflow(self, components: List[str]) -> dict:
        """Generate development workflow guide."""
        steps = []

        if "contract" in components:
            steps.append({
                "step": 1,
                "component": "Smart Contract",
                "actions": [
                    "cd packages/contract",
                    "cargo +nightly build --target wasm32-unknown-unknown --release",
                    "cargo stylus deploy --private-key $PRIVATE_KEY",
                    "Save the deployed contract address",
                ],
            })

        if "indexer" in components:
            steps.append({
                "step": 2,
                "component": "Subgraph Indexer",
                "actions": [
                    "cd packages/indexer",
                    "Update contract address in subgraph.yaml",
                    "npm run codegen",
                    "npm run deploy",
                ],
            })

        if "backend" in components:
            steps.append({
                "step": 3,
                "component": "Backend",
                "actions": [
                    "cd packages/backend",
                    "Copy .env.example to .env",
                    "Set CONTRACT_ADDRESS from step 1",
                    "npm install && npm run start:dev",
                ],
            })

        if "frontend" in components:
            steps.append({
                "step": 4,
                "component": "Frontend",
                "actions": [
                    "cd packages/frontend",
                    "Copy .env.example to .env.local",
                    "Set CONTRACT_ADDRESS and WALLET_CONNECT_ID",
                    "npm install && npm run dev",
                    "Open http://localhost:3000",
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

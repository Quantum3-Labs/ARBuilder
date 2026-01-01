"""
generate_dapp MCP Tool.

Orchestrates full-stack dApp generation by combining contract, backend,
frontend, and indexer generation tools.
"""

import json
from typing import Optional

from .base import BaseTool
from .generate_stylus_code import GenerateStylusCodeTool
from .generate_backend import GenerateBackendTool
from .generate_frontend import GenerateFrontendTool
from .generate_indexer import GenerateIndexerTool
from .get_stylus_context import GetStylusContextTool


SYSTEM_PROMPT = """You are an expert full-stack Web3 architect specializing in Arbitrum dApps.

Your role is to:
1. Analyze the user's dApp requirements
2. Design the overall architecture
3. Create a coherent integration plan
4. Ensure all components work together

Key considerations:
- Smart contracts should be the source of truth
- Backend should serve as API layer and handle off-chain logic
- Frontend should provide excellent UX with wallet integration
- Indexer should track important events for efficient queries

Output a JSON plan with:
1. contract_spec: Smart contract requirements
2. backend_spec: Backend API requirements
3. frontend_spec: Frontend UI requirements
4. indexer_spec: Indexer requirements (if needed)
5. integration_notes: How components connect
"""


class GenerateDappTool(BaseTool):
    """
    Orchestrates full-stack dApp generation.

    Combines contract, backend, frontend, and indexer generation
    into a coherent full-stack application.
    """

    def __init__(
        self,
        context_tool: Optional[GetStylusContextTool] = None,
        contract_tool: Optional[GenerateStylusCodeTool] = None,
        backend_tool: Optional[GenerateBackendTool] = None,
        frontend_tool: Optional[GenerateFrontendTool] = None,
        indexer_tool: Optional[GenerateIndexerTool] = None,
        **kwargs,
    ):
        """
        Initialize the tool.

        Args:
            context_tool: Context retrieval tool.
            contract_tool: Contract generation tool.
            backend_tool: Backend generation tool.
            frontend_tool: Frontend generation tool.
            indexer_tool: Indexer generation tool.
        """
        super().__init__(**kwargs)
        self.context_tool = context_tool or GetStylusContextTool(**kwargs)
        self.contract_tool = contract_tool or GenerateStylusCodeTool(
            context_tool=self.context_tool, **kwargs
        )
        self.backend_tool = backend_tool or GenerateBackendTool(
            context_tool=self.context_tool, **kwargs
        )
        self.frontend_tool = frontend_tool or GenerateFrontendTool(
            context_tool=self.context_tool, **kwargs
        )
        self.indexer_tool = indexer_tool or GenerateIndexerTool(
            context_tool=self.context_tool, **kwargs
        )

    def execute(
        self,
        prompt: str,
        name: str = "my-dapp",
        include: Optional[dict] = None,
        contract_type: str = "custom",
        backend_framework: str = "nestjs",
        wallet_kit: str = "rainbowkit",
        ui_library: str = "daisyui",
        network: str = "arbitrum-sepolia",
        temperature: float = 0.3,
        **kwargs,
    ) -> dict:
        """
        Generate a complete full-stack dApp.

        Args:
            prompt: Full dApp description.
            name: Project name.
            include: Dict specifying which components to generate:
                - contract: bool (default: True)
                - backend: bool (default: True)
                - frontend: bool (default: True)
                - indexer: bool (default: False)
            contract_type: Type of contract (erc20, erc721, erc1155, custom).
            backend_framework: Backend framework (nestjs, express).
            wallet_kit: Wallet kit (rainbowkit, connectkit, web3modal).
            ui_library: UI library (daisyui, shadcn).
            network: Target network (arbitrum-one, arbitrum-sepolia).
            temperature: Generation temperature.

        Returns:
            Dict with project structure, all generated files, and integration guide.
        """
        if not prompt or not prompt.strip():
            return {"error": "Prompt is required and cannot be empty"}

        prompt = prompt.strip()

        # Default include settings
        include = include or {}
        include_contract = include.get("contract", True)
        include_backend = include.get("backend", True)
        include_frontend = include.get("frontend", True)
        include_indexer = include.get("indexer", False)

        warnings = []
        results = {}

        try:
            # Step 1: Generate architecture plan
            plan = self._generate_plan(
                prompt=prompt,
                include_contract=include_contract,
                include_backend=include_backend,
                include_frontend=include_frontend,
                include_indexer=include_indexer,
                contract_type=contract_type,
                temperature=temperature,
            )

            results["plan"] = plan

            # Step 2: Generate smart contract
            if include_contract:
                contract_prompt = plan.get("contract_spec", prompt)
                if isinstance(contract_prompt, dict):
                    contract_prompt = contract_prompt.get("description", prompt)

                contract_result = self.contract_tool.execute(
                    prompt=contract_prompt,
                    contract_type=contract_type,
                    include_tests=True,
                    temperature=temperature,
                )

                if "error" in contract_result:
                    warnings.append(f"Contract generation warning: {contract_result['error']}")
                else:
                    results["contract"] = {
                        "path": f"{name}/contracts",
                        "files": self._prefix_paths(
                            [{"path": "src/lib.rs", "content": contract_result.get("code", "")}],
                            f"{name}/contracts"
                        ),
                        "dependencies": contract_result.get("dependencies", []),
                        "explanation": contract_result.get("explanation", ""),
                    }

                    # Extract ABI placeholder for other components
                    results["contract_abi"] = self._extract_abi_placeholder(
                        contract_result.get("code", "")
                    )

            # Step 3: Generate backend
            if include_backend:
                backend_prompt = plan.get("backend_spec", prompt)
                if isinstance(backend_prompt, dict):
                    backend_prompt = backend_prompt.get("description", prompt)

                backend_result = self.backend_tool.execute(
                    prompt=backend_prompt,
                    framework=backend_framework,
                    features=["api", "web3"],
                    contract_abi=results.get("contract_abi"),
                    temperature=temperature,
                )

                if "error" in backend_result:
                    warnings.append(f"Backend generation warning: {backend_result['error']}")
                else:
                    results["backend"] = {
                        "path": f"{name}/backend",
                        "files": self._prefix_paths(
                            backend_result.get("files", []),
                            f"{name}/backend"
                        ),
                        "package_json": backend_result.get("package_json", {}),
                        "explanation": backend_result.get("explanation", ""),
                    }

            # Step 4: Generate frontend
            if include_frontend:
                frontend_prompt = plan.get("frontend_spec", prompt)
                if isinstance(frontend_prompt, dict):
                    frontend_prompt = frontend_prompt.get("description", prompt)

                frontend_result = self.frontend_tool.execute(
                    prompt=frontend_prompt,
                    wallet_kit=wallet_kit,
                    ui_library=ui_library,
                    features=["wallet", "contract-read", "contract-write"],
                    contract_abi=results.get("contract_abi"),
                    networks=[network.replace("-", "_")],
                    app_name=name,
                    temperature=temperature,
                )

                if "error" in frontend_result:
                    warnings.append(f"Frontend generation warning: {frontend_result['error']}")
                else:
                    results["frontend"] = {
                        "path": f"{name}/frontend",
                        "files": self._prefix_paths(
                            frontend_result.get("files", []),
                            f"{name}/frontend"
                        ),
                        "package_json": frontend_result.get("package_json", {}),
                        "explanation": frontend_result.get("explanation", ""),
                    }

            # Step 5: Generate indexer
            if include_indexer:
                indexer_prompt = plan.get("indexer_spec", prompt)
                if isinstance(indexer_prompt, dict):
                    indexer_prompt = indexer_prompt.get("description", prompt)

                indexer_result = self.indexer_tool.execute(
                    prompt=indexer_prompt,
                    contract_name=name.replace("-", "").replace("_", "").title(),
                    network=network,
                    temperature=temperature,
                )

                if "error" in indexer_result:
                    warnings.append(f"Indexer generation warning: {indexer_result['error']}")
                else:
                    results["indexer"] = {
                        "path": f"{name}/indexer",
                        "files": self._prefix_paths(
                            indexer_result.get("files", []),
                            f"{name}/indexer"
                        ),
                        "package_json": indexer_result.get("package_json", {}),
                        "explanation": indexer_result.get("explanation", ""),
                    }

            # Step 6: Generate project root files
            root_files = self._generate_root_files(
                name=name,
                include_contract=include_contract,
                include_backend=include_backend,
                include_frontend=include_frontend,
                include_indexer=include_indexer,
                network=network,
            )
            results["root_files"] = root_files

            # Step 7: Generate integration guide
            integration_guide = self._generate_integration_guide(
                name=name,
                results=results,
                plan=plan,
            )
            results["integration_guide"] = integration_guide

            # Build prerequisites based on included components
            prerequisites = {
                "required": [],
                "install": {},
                "verify": [],
            }

            if include_contract:
                prerequisites["required"].extend(["rustup", "cargo", "cargo-stylus"])
                prerequisites["install"]["rust"] = "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
                prerequisites["install"]["cargo-stylus"] = "cargo install cargo-stylus"
                prerequisites["verify"].append("cargo --version && cargo stylus --version")

            if include_backend or include_frontend or include_indexer:
                prerequisites["required"].extend(["node >= 18", "npm >= 9"])
                prerequisites["install"]["node"] = {
                    "macos": "brew install node",
                    "linux": "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs",
                    "windows": "Download from https://nodejs.org/",
                }
                prerequisites["verify"].append("node --version && npm --version")

            if include_indexer:
                prerequisites["required"].append("graph-cli")
                prerequisites["install"]["graph-cli"] = "npm install -g @graphprotocol/graph-cli"
                prerequisites["verify"].append("graph --version")

            return {
                "name": name,
                "components": results,
                "warnings": warnings,
                "project_structure": self._generate_project_structure(name, results),
                "prerequisites": prerequisites,
            }

        except Exception as e:
            return {"error": f"dApp generation failed: {str(e)}"}

    def _generate_plan(
        self,
        prompt: str,
        include_contract: bool,
        include_backend: bool,
        include_frontend: bool,
        include_indexer: bool,
        contract_type: str,
        temperature: float,
    ) -> dict:
        """Generate architecture plan for the dApp."""
        components = []
        if include_contract:
            components.append("smart contract")
        if include_backend:
            components.append("backend API")
        if include_frontend:
            components.append("frontend UI")
        if include_indexer:
            components.append("event indexer")

        user_prompt = f"""Analyze this dApp requirement and create specifications for each component:

dApp Description:
{prompt}

Components to generate: {', '.join(components)}
Contract type: {contract_type}

Provide a JSON object with these keys (only for components being generated):
- contract_spec: {{ "description": "...", "features": [...] }}
- backend_spec: {{ "description": "...", "endpoints": [...] }}
- frontend_spec: {{ "description": "...", "pages": [...] }}
- indexer_spec: {{ "description": "...", "entities": [...] }}
- integration_notes: "How the components connect"

Respond with valid JSON only."""

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        response = self._call_llm(
            messages=messages,
            temperature=temperature,
            max_tokens=2048,
        )

        # Parse JSON from response
        try:
            # Try to extract JSON from response
            json_match = response
            if "```json" in response:
                json_match = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_match = response.split("```")[1].split("```")[0]

            return json.loads(json_match.strip())
        except json.JSONDecodeError:
            # Return basic plan if parsing fails
            return {
                "contract_spec": {"description": prompt},
                "backend_spec": {"description": f"API for {prompt}"},
                "frontend_spec": {"description": f"UI for {prompt}"},
                "indexer_spec": {"description": f"Index events from {prompt}"},
                "integration_notes": "Standard Web3 dApp integration",
            }

    def _extract_abi_placeholder(self, contract_code: str) -> str:
        """Extract a placeholder ABI from contract code."""
        # For now, return a placeholder. In a real implementation,
        # this would parse the contract and generate an ABI.
        return None

    def _prefix_paths(self, files: list[dict], prefix: str) -> list[dict]:
        """Prefix all file paths with the given directory."""
        return [
            {**f, "path": f"{prefix}/{f['path']}"}
            for f in files
        ]

    def _generate_root_files(
        self,
        name: str,
        include_contract: bool,
        include_backend: bool,
        include_frontend: bool,
        include_indexer: bool,
        network: str,
    ) -> list[dict]:
        """Generate project root files."""
        files = []

        # Root package.json for monorepo
        workspaces = []
        if include_contract:
            workspaces.append("contracts")
        if include_backend:
            workspaces.append("backend")
        if include_frontend:
            workspaces.append("frontend")
        if include_indexer:
            workspaces.append("indexer")

        package_json = {
            "name": name,
            "private": True,
            "workspaces": workspaces,
            "scripts": {
                "dev": "concurrently \"npm:dev:*\"",
            },
        }

        if include_backend:
            package_json["scripts"]["dev:backend"] = "npm run dev --workspace=backend"
        if include_frontend:
            package_json["scripts"]["dev:frontend"] = "npm run dev --workspace=frontend"

        files.append({
            "path": f"{name}/package.json",
            "content": json.dumps(package_json, indent=2),
        })

        # Root .gitignore
        gitignore = """node_modules/
.env
.env.local
dist/
build/
.next/
target/
"""
        files.append({
            "path": f"{name}/.gitignore",
            "content": gitignore,
        })

        # Root .env.example
        env_content = f"""# Network configuration
NETWORK={network}

# Contract address (after deployment)
CONTRACT_ADDRESS=

# Backend
BACKEND_PORT=3001

# Frontend
NEXT_PUBLIC_WALLET_CONNECT_PROJECT_ID=
NEXT_PUBLIC_CONTRACT_ADDRESS=
"""
        files.append({
            "path": f"{name}/.env.example",
            "content": env_content,
        })

        return files

    def _generate_integration_guide(
        self,
        name: str,
        results: dict,
        plan: dict,
    ) -> str:
        """Generate integration guide for connecting components."""
        guide = f"""# {name} Integration Guide

## Architecture Overview

{plan.get('integration_notes', 'This dApp follows a standard Web3 architecture.')}

## Getting Started

1. Install dependencies:
   ```bash
   cd {name}
   npm install
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

"""
        if "contract" in results:
            guide += """
## Smart Contract

### Build
```bash
cd contracts
cargo build --release
```

### Deploy
```bash
cargo stylus deploy --private-key $PRIVATE_KEY
```

After deployment, copy the contract address to your .env file.
"""

        if "backend" in results:
            guide += """
## Backend

### Run Development Server
```bash
cd backend
npm run start:dev
```

The API will be available at http://localhost:3001
"""

        if "frontend" in results:
            guide += """
## Frontend

### Run Development Server
```bash
cd frontend
npm run dev
```

The app will be available at http://localhost:3000
"""

        if "indexer" in results:
            guide += """
## Indexer (Subgraph)

### Deploy to The Graph Studio
1. Create a subgraph at https://thegraph.com/studio/
2. Authenticate: `graph auth --studio YOUR_DEPLOY_KEY`
3. Deploy: `npm run deploy`
"""

        guide += """
## Environment Variables

| Variable | Description |
|----------|-------------|
| NETWORK | Target network (arbitrum-one, arbitrum-sepolia) |
| CONTRACT_ADDRESS | Deployed contract address |
| NEXT_PUBLIC_WALLET_CONNECT_PROJECT_ID | WalletConnect project ID |
"""

        return guide

    def _generate_project_structure(self, name: str, results: dict) -> str:
        """Generate a tree view of the project structure."""
        structure = [f"{name}/"]

        if "contract" in results:
            structure.append("├── contracts/")
            structure.append("│   ├── Cargo.toml")
            structure.append("│   └── src/")
            structure.append("│       └── lib.rs")

        if "backend" in results:
            structure.append("├── backend/")
            structure.append("│   ├── package.json")
            structure.append("│   └── src/")

        if "frontend" in results:
            structure.append("├── frontend/")
            structure.append("│   ├── package.json")
            structure.append("│   ├── app/")
            structure.append("│   └── components/")

        if "indexer" in results:
            structure.append("├── indexer/")
            structure.append("│   ├── package.json")
            structure.append("│   ├── subgraph.yaml")
            structure.append("│   ├── schema.graphql")
            structure.append("│   └── src/")

        structure.append("├── package.json")
        structure.append("├── .env.example")
        structure.append("└── .gitignore")

        return "\n".join(structure)

"""
Generate frontend code for dApps.

Supports:
- Next.js with wagmi and RainbowKit
- DaisyUI component library
- Contract Dashboard (admin panel)
- Token Interface (ERC20/721 UI)
"""

import json
from typing import Any, Optional

from .base import BaseTool
from ...templates.frontend_templates import (
    FrontendTemplate,
    select_frontend_template,
    get_frontend_template,
    list_frontend_templates,
    NEXTJS_WAGMI_TEMPLATE,
    DAISYUI_COMPONENTS_TEMPLATE,
    CONTRACT_DASHBOARD_TEMPLATE,
    TOKEN_INTERFACE_TEMPLATE,
)
from ...embeddings.agentic_rag import get_context_for_generation


class GenerateFrontendTool(BaseTool):
    """Generate frontend code for dApps with Web3 integration."""

    name = "generate_frontend"
    description = """Generate Next.js frontend code for Arbitrum dApps.

Supports:
- Next.js with wagmi v2 and RainbowKit
- DaisyUI component library with dark theme
- Contract Dashboard for admin operations
- Token Interface for ERC20/721 tokens

The generated code includes React components, hooks, and configuration."""

    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Description of the frontend functionality needed",
            },
            "template": {
                "type": "string",
                "enum": ["nextjs_wagmi", "daisyui_components", "contract_dashboard", "token_interface"],
                "description": "Specific template to use (optional, auto-selected if not provided)",
            },
            "contract_abi": {
                "type": "string",
                "description": "Contract ABI JSON string for generating hooks",
            },
            "contract_address": {
                "type": "string",
                "description": "Contract address to integrate with",
            },
            "ui_framework": {
                "type": "string",
                "enum": ["tailwind", "daisyui"],
                "description": "UI framework to use",
                "default": "daisyui",
            },
            "include_tests": {
                "type": "boolean",
                "description": "Include test files",
                "default": False,
            },
        },
        "required": ["prompt"],
    }

    def __init__(self, vectordb=None):
        """Initialize with optional vector database for context."""
        super().__init__()
        self.vectordb = vectordb

    def execute(self, **kwargs) -> dict[str, Any]:
        """Generate frontend code based on the request."""
        prompt = kwargs.get("prompt", "")
        template_name = kwargs.get("template")
        contract_abi = kwargs.get("contract_abi")
        contract_address = kwargs.get("contract_address", "0x...")
        ui_framework = kwargs.get("ui_framework", "daisyui")
        include_tests = kwargs.get("include_tests", False)

        # Validate inputs
        if not prompt:
            return {"error": "prompt is required"}

        # Select template
        if template_name:
            template = get_frontend_template(template_name)
            if not template:
                return {"error": f"Unknown template: {template_name}"}
        else:
            template = select_frontend_template(prompt)

        # Get RAG context for customization
        context = []
        if self.vectordb:
            try:
                context = get_context_for_generation(
                    f"frontend nextjs wagmi rainbowkit {prompt}",
                    vectordb=self.vectordb,
                    n_results=5,
                    use_agentic=True,
                )
            except Exception:
                pass  # Use template without context

        # Customize template based on prompt
        files = self._customize_template(template, prompt, contract_abi, contract_address)

        # Generate package.json
        package_json = self._generate_package_json(template, prompt)

        # Add test files if requested
        if include_tests:
            test_files = self._generate_tests(template, prompt)
            files.update(test_files)

        # Build response
        result = {
            "template_used": template.name,
            "framework": template.framework,
            "files": files,
            "package_json": package_json,
            "dependencies": template.dependencies,
            "dev_dependencies": template.dev_dependencies,
            "env_vars": template.env_vars,
            "scripts": template.scripts,
            "setup_instructions": self._get_setup_instructions(template),
        }

        if context:
            result["references"] = [
                {
                    "source": c.get("metadata", {}).get("source", "Unknown"),
                    "relevance": c.get("distance", 0),
                }
                for c in context[:3]
            ]

        return result

    def _customize_template(
        self,
        template: FrontendTemplate,
        prompt: str,
        contract_abi: Optional[str],
        contract_address: str,
    ) -> dict[str, str]:
        """Customize template files based on user requirements."""
        files = dict(template.files)

        # Replace placeholder contract address
        for path, content in files.items():
            if "0x..." in content:
                files[path] = content.replace("0x...", contract_address)

        # If custom ABI provided, generate contract config
        if contract_abi:
            try:
                abi = json.loads(contract_abi)
                contract_config = self._generate_contract_config(abi, contract_address)
                files["src/config/contract.ts"] = contract_config

                # Generate custom hooks based on ABI
                hooks = self._generate_hooks_from_abi(abi)
                files["src/hooks/useContract.ts"] = hooks
            except json.JSONDecodeError:
                pass  # Use default configuration

        return files

    def _generate_contract_config(self, abi: list, address: str) -> str:
        """Generate contract configuration from ABI."""
        # Extract function signatures for parseAbi
        signatures = []
        for item in abi:
            if item.get("type") == "function":
                name = item.get("name", "")
                inputs = ", ".join(
                    f"{i.get('type', '')} {i.get('name', '')}"
                    for i in item.get("inputs", [])
                )
                outputs = ", ".join(
                    i.get("type", "") for i in item.get("outputs", [])
                )
                state = item.get("stateMutability", "nonpayable")

                if state == "view" or state == "pure":
                    sig = f"function {name}({inputs}) view returns ({outputs})"
                else:
                    sig = f"function {name}({inputs})"
                    if outputs:
                        sig += f" returns ({outputs})"

                signatures.append(f"  '{sig}',")
            elif item.get("type") == "event":
                name = item.get("name", "")
                inputs = ", ".join(
                    f"{'indexed ' if i.get('indexed') else ''}{i.get('type', '')} {i.get('name', '')}"
                    for i in item.get("inputs", [])
                )
                signatures.append(f"  'event {name}({inputs})',")

        abi_strings = "\n".join(signatures)

        return f'''import {{ parseAbi }} from 'viem';

export const CONTRACT_ADDRESS = '{address}' as `0x${{string}}`;

export const CONTRACT_ABI = parseAbi([
{abi_strings}
]);
'''

    def _generate_hooks_from_abi(self, abi: list) -> str:
        """Generate React hooks from contract ABI."""
        hooks = ['''"use client";

import { useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { CONTRACT_ADDRESS, CONTRACT_ABI } from '@/config/contract';
''']

        for item in abi:
            if item.get("type") != "function":
                continue

            name = item.get("name", "")
            state = item.get("stateMutability", "nonpayable")

            if state in ["view", "pure"]:
                # Generate read hook
                hook_name = f"use{name[0].upper()}{name[1:]}"
                hooks.append(f'''
export function {hook_name}() {{
  return useReadContract({{
    address: CONTRACT_ADDRESS,
    abi: CONTRACT_ABI,
    functionName: '{name}',
  }});
}}
''')
            else:
                # Generate write hook
                hook_name = f"use{name[0].upper()}{name[1:]}"
                hooks.append(f'''
export function {hook_name}() {{
  const {{ writeContract, data: hash, isPending, error }} = useWriteContract();
  const {{ isLoading: isConfirming, isSuccess }} = useWaitForTransactionReceipt({{ hash }});

  const {name} = (args?: unknown[]) => {{
    writeContract({{
      address: CONTRACT_ADDRESS,
      abi: CONTRACT_ABI,
      functionName: '{name}',
      args: args as any,
    }});
  }};

  return {{ {name}, hash, isPending, isConfirming, isSuccess, error }};
}}
''')

        return "\n".join(hooks)

    def _generate_package_json(self, template: FrontendTemplate, prompt: str) -> dict:
        """Generate package.json content."""
        # Derive package name from prompt
        words = prompt.lower().split()[:3]
        name = "-".join(w for w in words if w.isalnum())[:20] or "dapp-frontend"

        return {
            "name": name,
            "version": "0.1.0",
            "private": True,
            "scripts": template.scripts,
            "dependencies": template.dependencies,
            "devDependencies": template.dev_dependencies,
        }

    def _generate_tests(self, template: FrontendTemplate, prompt: str) -> dict[str, str]:
        """Generate test files for the frontend."""
        return {
            "__tests__/page.test.tsx": '''import { render, screen } from '@testing-library/react';
import Home from '@/app/page';

// Mock wagmi hooks
jest.mock('wagmi', () => ({
  useAccount: () => ({ isConnected: false, address: undefined }),
  useConnect: () => ({ connect: jest.fn() }),
  useDisconnect: () => ({ disconnect: jest.fn() }),
}));

// Mock RainbowKit
jest.mock('@rainbow-me/rainbowkit', () => ({
  ConnectButton: () => <button>Connect</button>,
}));

describe('Home', () => {
  it('renders the main heading', () => {
    render(<Home />);
    expect(screen.getByRole('heading')).toBeInTheDocument();
  });
});
''',
            "jest.config.js": '''const nextJest = require('next/jest');

const createJestConfig = nextJest({
  dir: './',
});

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
};

module.exports = createJestConfig(customJestConfig);
''',
            "jest.setup.js": '''import '@testing-library/jest-dom';
''',
        }

    def _get_setup_instructions(self, template: FrontendTemplate) -> list[str]:
        """Get setup instructions for the template."""
        return [
            "1. Create a new directory and copy the generated files",
            "2. Copy .env.example to .env.local and fill in the values",
            "3. Get a WalletConnect Project ID from cloud.walletconnect.com",
            "4. Run: npm install",
            "5. Run in development: npm run dev",
            "6. Open http://localhost:3000",
        ]

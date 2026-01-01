"""
generate_frontend MCP Tool.

Generates Next.js/React frontend code with wallet integration for Arbitrum dApps.
"""

import re
from typing import Optional

from .base import BaseTool
from .get_stylus_context import GetStylusContextTool


SYSTEM_PROMPT = """You are an expert Web3 frontend developer specializing in Next.js applications for Arbitrum dApps.

Key patterns to follow:

## Next.js 14+ App Router:
1. Use app directory with layout.tsx, page.tsx structure
2. Use Server Components by default, Client Components with 'use client' directive
3. Use TypeScript for type safety
4. Use environment variables for configuration

## Wallet Integration (wagmi + viem):
1. Use WagmiProvider with proper configuration
2. Use RainbowKit or ConnectKit for wallet connection UI
3. Use wagmi hooks: useAccount, useConnect, useContractRead, useContractWrite
4. Handle loading and error states for blockchain operations
5. Support Arbitrum One and Arbitrum Sepolia networks

## DaisyUI / Tailwind:
1. Use DaisyUI components for consistent styling
2. Use Tailwind utility classes for customization
3. Support dark/light theme switching
4. Use responsive design patterns

## Best Practices:
1. Separate contract interactions into custom hooks
2. Use React Query (TanStack Query) for caching
3. Handle transaction states (pending, success, error)
4. Show proper loading states and error messages
5. Use TypeScript for contract type safety

When generating code:
- Generate complete, runnable TSX code with all imports
- Include package.json dependencies
- Add helpful comments for complex logic
- Follow React best practices
- Include proper TypeScript types
"""

WAGMI_CONFIG_TEMPLATE = '''import {{ http, createConfig }} from 'wagmi';
import {{ arbitrum, arbitrumSepolia }} from 'wagmi/chains';
import {{ getDefaultConfig }} from '@rainbow-me/rainbowkit';

export const config = getDefaultConfig({{
  appName: '{appName}',
  projectId: process.env.NEXT_PUBLIC_WALLET_CONNECT_PROJECT_ID || '',
  chains: [arbitrum, arbitrumSepolia],
  transports: {{
    [arbitrum.id]: http(),
    [arbitrumSepolia.id]: http(),
  }},
}});
'''

PROVIDERS_TEMPLATE = ''''use client';

import { WagmiProvider } from 'wagmi';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RainbowKitProvider, darkTheme } from '@rainbow-me/rainbowkit';
import { config } from '@/lib/wagmi/config';

import '@rainbow-me/rainbowkit/styles.css';

const queryClient = new QueryClient();

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <RainbowKitProvider theme={darkTheme()}>
          {children}
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}
'''

LAYOUT_TEMPLATE = '''import type {{ Metadata }} from 'next';
import {{ Inter }} from 'next/font/google';
import {{ Providers }} from './providers';
import './globals.css';

const inter = Inter({{ subsets: ['latin'] }});

export const metadata: Metadata = {{
  title: '{appName}',
  description: '{appDescription}',
}};

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode;
}}) {{
  return (
    <html lang="en" data-theme="dark">
      <body className={{inter.className}}>
        <Providers>
          {{children}}
        </Providers>
      </body>
    </html>
  );
}}
'''

NAVBAR_TEMPLATE = ''''use client';

import { ConnectButton } from '@rainbow-me/rainbowkit';
import Link from 'next/link';

export function Navbar() {
  return (
    <div className="navbar bg-base-200">
      <div className="flex-1">
        <Link href="/" className="btn btn-ghost text-xl">
          {appName}
        </Link>
      </div>
      <div className="flex-none gap-2">
        <ConnectButton />
      </div>
    </div>
  );
}
'''

CONTRACT_HOOK_TEMPLATE = ''''use client';

import { useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { parseAbi } from 'viem';

// Contract configuration - update with your contract address
const CONTRACT_ADDRESS = process.env.NEXT_PUBLIC_CONTRACT_ADDRESS as `0x${string}` || '0x0000000000000000000000000000000000000000';

// Default ERC20 ABI - customize for your contract
const CONTRACT_ABI = parseAbi([
  'function balanceOf(address owner) view returns (uint256)',
  'function transfer(address to, uint256 amount) returns (bool)',
  'function approve(address spender, uint256 amount) returns (bool)',
  'function allowance(address owner, address spender) view returns (uint256)',
]);

export function useContractData(address?: `0x${string}`) {
  const { data: balance, isLoading } = useReadContract({
    address: CONTRACT_ADDRESS,
    abi: CONTRACT_ABI,
    functionName: 'balanceOf',
    args: address ? [address] : undefined,
    query: { enabled: !!address },
  });

  return {
    balance,
    isLoading,
  };
}

export function useContractActions() {
  const { writeContract, data: hash, isPending } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  const transfer = (to: `0x${string}`, amount: bigint) => {
    writeContract({
      address: CONTRACT_ADDRESS,
      abi: CONTRACT_ABI,
      functionName: 'transfer',
      args: [to, amount],
    });
  };

  return {
    transfer,
    isPending,
    isConfirming,
    isSuccess,
    hash,
  };
}
'''


class GenerateFrontendTool(BaseTool):
    """
    Generates Next.js frontend code with wallet integration.

    Uses RAG context to inform code generation with relevant examples.
    """

    def __init__(
        self,
        context_tool: Optional[GetStylusContextTool] = None,
        **kwargs,
    ):
        """
        Initialize the tool.

        Args:
            context_tool: GetStylusContextTool for retrieving examples.
        """
        super().__init__(**kwargs)
        self.context_tool = context_tool or GetStylusContextTool(**kwargs)

    def execute(
        self,
        prompt: str,
        wallet_kit: str = "rainbowkit",
        ui_library: str = "daisyui",
        features: Optional[list[str]] = None,
        contract_abi: Optional[str] = None,
        networks: Optional[list[str]] = None,
        app_name: str = "My dApp",
        temperature: float = 0.2,
        **kwargs,
    ) -> dict:
        """
        Generate frontend code.

        Args:
            prompt: Description of the frontend to generate.
            wallet_kit: Wallet kit to use (rainbowkit, connectkit, web3modal).
            ui_library: UI library (daisyui, shadcn, none).
            features: List of features (wallet, contract-read, contract-write, tx-history).
            contract_abi: Optional ABI for typed hooks.
            networks: Networks to support (arbitrum_one, arbitrum_sepolia).
            app_name: Name of the application.
            temperature: Generation temperature (0-1).

        Returns:
            Dict with files, package_json, explanation, warnings, context_used.
        """
        if not prompt or not prompt.strip():
            return {"error": "Prompt is required and cannot be empty"}

        prompt = prompt.strip()
        features = features or ["wallet", "contract-read"]
        networks = networks or ["arbitrum_one", "arbitrum_sepolia"]
        warnings = []

        if wallet_kit not in ["rainbowkit", "connectkit", "web3modal"]:
            warnings.append(f"Unknown wallet kit '{wallet_kit}', defaulting to rainbowkit")
            wallet_kit = "rainbowkit"

        try:
            # Retrieve relevant context
            context_used = []
            context_text = ""

            context_result = self.context_tool.execute(
                query=f"react next.js wagmi viem {wallet_kit} {ui_library} arbitrum {prompt}",
                n_results=5,
                content_type="code",
                rerank=True,
            )

            if "contexts" in context_result:
                for ctx in context_result["contexts"]:
                    context_used.append({
                        "source": ctx["source"],
                        "relevance": ctx["relevance_score"],
                    })
                    context_text += f"\n--- Example from {ctx['source']} ---\n{ctx['content'][:1500]}\n"

            # Build generation prompt
            user_prompt = self._build_prompt(
                prompt=prompt,
                wallet_kit=wallet_kit,
                ui_library=ui_library,
                features=features,
                contract_abi=contract_abi,
                networks=networks,
                app_name=app_name,
                context_text=context_text,
            )

            # Generate code
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            response = self._call_llm(
                messages=messages,
                temperature=temperature,
                max_tokens=8192,
            )

            # Parse response
            files = self._parse_files(response)
            explanation = self._extract_explanation(response)

            # Generate package.json
            package_json = self._generate_package_json(wallet_kit, ui_library, features)

            # Add base files if missing
            files = self._add_base_files(files, wallet_kit, ui_library, app_name)

            return {
                "files": files,
                "package_json": package_json,
                "explanation": explanation,
                "warnings": warnings if warnings else [],
                "context_used": context_used,
                "wallet_kit": wallet_kit,
                "ui_library": ui_library,
                "prerequisites": {
                    "required": ["node >= 18", "npm >= 9"],
                    "install": {
                        "macos": "brew install node",
                        "linux": "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs",
                        "windows": "Download from https://nodejs.org/",
                    },
                    "verify": "node --version && npm --version",
                },
            }

        except Exception as e:
            return {"error": f"Frontend generation failed: {str(e)}"}

    def _build_prompt(
        self,
        prompt: str,
        wallet_kit: str,
        ui_library: str,
        features: list[str],
        contract_abi: Optional[str],
        networks: list[str],
        app_name: str,
        context_text: str,
    ) -> str:
        """Build the generation prompt."""
        parts = []

        parts.append("Generate a Next.js 14+ App Router frontend with the following configuration:")
        parts.append(f"- App name: {app_name}")
        parts.append(f"- Wallet connection: {wallet_kit}")
        parts.append(f"- UI library: {ui_library}")
        parts.append(f"- Networks: {', '.join(networks)}")
        parts.append(f"- Features: {', '.join(features)}")
        parts.append("")

        # Add base templates
        parts.append("Base wagmi configuration:")
        parts.append(f"```typescript\n{WAGMI_CONFIG_TEMPLATE.format(appName=app_name)}\n```")
        parts.append("")

        parts.append("Base providers setup:")
        parts.append(f"```typescript\n{PROVIDERS_TEMPLATE}\n```")
        parts.append("")

        # Add UI library guidance
        if ui_library == "daisyui":
            parts.append("Use DaisyUI component classes (btn, card, modal, input, etc.)")
            parts.append("Use data-theme='dark' for dark mode support")
        elif ui_library == "shadcn":
            parts.append("Use shadcn/ui components")
            parts.append("Follow shadcn component patterns")

        # Add contract ABI if provided
        if contract_abi:
            parts.append("\nContract ABI to integrate:")
            parts.append(f"```json\n{contract_abi}\n```")
            parts.append("Generate typed wagmi hooks for this contract.")

        # Add context if available
        if context_text:
            parts.append("\nHere are some relevant code examples for reference:")
            parts.append(context_text)

        # Add main request
        parts.append(f"\nGenerate frontend code for the following requirement:")
        parts.append(f"\n{prompt}\n")

        parts.append("\nProvide:")
        parts.append("1. Complete TSX code for all components and pages")
        parts.append("2. File paths as comments (e.g., // app/page.tsx)")
        parts.append("3. Any custom hooks for contract interactions")
        parts.append("4. A brief explanation of the implementation")
        parts.append("\nFormat each file with its path as a comment before the code block.")

        return "\n".join(parts)

    def _parse_files(self, response: str) -> list[dict]:
        """Parse files from LLM response."""
        files = []

        # Match code blocks with optional file path comments
        file_pattern = r'(?:\/\/\s*|#\s*)?([a-zA-Z0-9_\-\/\.]+\.(?:tsx?|jsx?|json|css|yaml|yml|env))\s*\n```(?:typescript|tsx|javascript|jsx|json|css)?\s*\n([\s\S]*?)```'

        matches = re.findall(file_pattern, response)

        for path, content in matches:
            path = path.strip()
            content = content.strip()

            # Normalize path - remove leading ./ and fix duplicate directories
            path = self._normalize_path(path)

            files.append({
                "path": path,
                "content": content,
            })

        # Also try to match standalone code blocks without file paths
        if not files:
            code_blocks = re.findall(r'```(?:typescript|tsx|javascript|jsx)?\s*\n([\s\S]*?)```', response)
            for i, content in enumerate(code_blocks):
                files.append({
                    "path": f"app/component_{i + 1}.tsx",
                    "content": content.strip(),
                })

        return files

    def _normalize_path(self, path: str) -> str:
        """Normalize file path to prevent duplicates and fix structure."""
        # Remove leading ./
        if path.startswith("./"):
            path = path[2:]

        # Fix duplicate directory patterns (e.g., components/components/, lib/lib/)
        parts = path.split("/")
        normalized_parts = []
        for i, part in enumerate(parts):
            # Skip if this part duplicates the previous part
            if i > 0 and part == parts[i - 1]:
                continue
            normalized_parts.append(part)
        path = "/".join(normalized_parts)

        # Fix wagmi path: lib/wagmi/config.ts or lib/wagmi.ts -> lib/wagmi/config.ts
        if "wagmi" in path.lower() and path.endswith(".ts"):
            if not path.startswith("lib/"):
                path = f"lib/{path}"
            # Ensure wagmi config is in proper location
            if path == "lib/wagmi.ts":
                path = "lib/wagmi/config.ts"

        # Ensure proper directory structure
        if not path.startswith(("app/", "components/", "hooks/", "lib/", "public/", "styles/")):
            filename = path.split("/")[-1]
            if filename.endswith(".tsx"):
                if "page" in filename.lower() or "layout" in filename.lower():
                    path = f"app/{filename}"
                elif "provider" in filename.lower():
                    path = f"app/{filename}"
                elif "hook" in filename.lower() or filename.startswith("use"):
                    path = f"hooks/{filename}"
                else:
                    path = f"components/{filename}"
            elif filename.endswith(".ts"):
                if "hook" in filename.lower() or filename.startswith("use"):
                    path = f"hooks/{filename}"
                else:
                    path = f"lib/{filename}"
            elif filename.endswith(".css"):
                if "global" in filename.lower():
                    path = f"app/{filename}"
            # Keep root files at root: package.json, tsconfig.json, etc.

        return path

    def _extract_explanation(self, response: str) -> str:
        """Extract explanation from response."""
        parts = response.split("```")
        if len(parts) > 1:
            explanation = parts[-1].strip()
            if explanation:
                return explanation

        return "Generated Next.js frontend code based on the provided requirements."

    def _generate_package_json(
        self,
        wallet_kit: str,
        ui_library: str,
        features: list[str],
    ) -> dict:
        """Generate package.json content."""
        package = {
            "name": "frontend",
            "version": "1.0.0",
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
                "lint": "next lint",
            },
            "dependencies": {
                "next": "^14.0.0",
                "react": "^18.0.0",
                "react-dom": "^18.0.0",
                "wagmi": "^2.0.0",
                "viem": "^2.0.0",
                "@tanstack/react-query": "^5.0.0",
            },
            "devDependencies": {
                "@types/node": "^20.0.0",
                "@types/react": "^18.0.0",
                "@types/react-dom": "^18.0.0",
                "typescript": "^5.0.0",
                "postcss": "^8.0.0",
                "tailwindcss": "^3.0.0",
                "autoprefixer": "^10.0.0",
            },
        }

        # Add wallet kit dependencies
        if wallet_kit == "rainbowkit":
            package["dependencies"]["@rainbow-me/rainbowkit"] = "^2.0.0"
        elif wallet_kit == "connectkit":
            package["dependencies"]["connectkit"] = "^1.8.0"
        elif wallet_kit == "web3modal":
            package["dependencies"]["@web3modal/wagmi"] = "^4.0.0"

        # Add UI library dependencies
        if ui_library == "daisyui":
            package["devDependencies"]["daisyui"] = "^4.0.0"
        elif ui_library == "shadcn":
            package["dependencies"]["@radix-ui/react-slot"] = "^1.0.0"
            package["dependencies"]["class-variance-authority"] = "^0.7.0"
            package["dependencies"]["clsx"] = "^2.0.0"
            package["dependencies"]["tailwind-merge"] = "^2.0.0"

        return package

    def _add_base_files(
        self,
        files: list[dict],
        wallet_kit: str,
        ui_library: str,
        app_name: str,
    ) -> list[dict]:
        """Add base files if not present in generated files."""
        file_paths = [f["path"] for f in files]

        # Add wagmi config if not present
        if not any("wagmi" in p.lower() for p in file_paths):
            files.append({
                "path": "lib/wagmi/config.ts",
                "content": WAGMI_CONFIG_TEMPLATE.format(appName=app_name),
            })

        # Add providers if not present
        if not any("provider" in p.lower() for p in file_paths):
            files.append({
                "path": "app/providers.tsx",
                "content": PROVIDERS_TEMPLATE,
            })

        # Add layout if not present
        if not any("layout" in p.lower() for p in file_paths):
            files.append({
                "path": "app/layout.tsx",
                "content": LAYOUT_TEMPLATE.format(appName=app_name, appDescription=f"{app_name} - A Web3 dApp"),
            })

        # Add contract hooks template
        if not any("hook" in p.lower() and "contract" in p.lower() for p in file_paths):
            files.append({
                "path": "hooks/useContract.ts",
                "content": CONTRACT_HOOK_TEMPLATE,
            })

        # Add globals.css if not present
        if not any("global" in p.lower() and ".css" in p for p in file_paths):
            css_content = """@tailwind base;
@tailwind components;
@tailwind utilities;
"""
            files.append({
                "path": "app/globals.css",
                "content": css_content,
            })

        # Add tailwind.config.js if using daisyui
        if ui_library == "daisyui" and not any("tailwind.config" in p for p in file_paths):
            tailwind_config = """/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: ['dark', 'light'],
  },
};
"""
            files.append({
                "path": "tailwind.config.js",
                "content": tailwind_config,
            })

        # Add .env.example
        env_content = """# WalletConnect Project ID (REQUIRED)
# Get one at https://cloud.walletconnect.com
NEXT_PUBLIC_WALLET_CONNECT_PROJECT_ID=your-project-id-here

# Contract address (if applicable)
# NEXT_PUBLIC_CONTRACT_ADDRESS=0x...
"""
        if not any(".env" in p for p in file_paths):
            files.append({
                "path": ".env.example",
                "content": env_content,
            })

        # Add tsconfig.json if not present
        if not any("tsconfig.json" in p for p in file_paths):
            tsconfig = """{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": false,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{"name": "next"}],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
"""
            files.append({
                "path": "tsconfig.json",
                "content": tsconfig,
            })

        # Add next.config.js if not present
        if not any("next.config" in p for p in file_paths):
            next_config = """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  webpack: (config) => {
    config.resolve.fallback = { fs: false, net: false, tls: false };
    config.externals.push('pino-pretty', 'lokijs', 'encoding');
    return config;
  },
};

module.exports = nextConfig;
"""
            files.append({
                "path": "next.config.js",
                "content": next_config,
            })

        # Add postcss.config.js if not present (required for Tailwind)
        if not any("postcss.config" in p for p in file_paths):
            postcss_config = """module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
"""
            files.append({
                "path": "postcss.config.js",
                "content": postcss_config,
            })

        return files

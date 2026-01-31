/**
 * Generate frontend code for Arbitrum dApps (M3 tool)
 */

type UIFramework = "daisyui" | "shadcn" | "none";
type Template = "base" | "dashboard" | "token";

interface GenerateFrontendArgs {
  prompt: string;
  contractAbi?: string;
  uiFramework?: UIFramework;
  template?: Template;
}

interface GenerateFrontendResult {
  files: Record<string, string>;
  dependencies: Record<string, string>;
  devDependencies: Record<string, string>;
  envVars: string[];
  setupInstructions: string[];
}

// Base Next.js + wagmi + RainbowKit files
const BASE_FILES = {
  "src/app/layout.tsx": `import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Arbitrum dApp',
  description: 'Built with ARBuilder',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
`,

  "src/app/providers.tsx": `'use client';

import { WagmiProvider } from 'wagmi';
import { RainbowKitProvider } from '@rainbow-me/rainbowkit';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { config } from '@/config/wagmi';
import '@rainbow-me/rainbowkit/styles.css';

const queryClient = new QueryClient();

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <RainbowKitProvider>
          {children}
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}
`,

  "src/app/page.tsx": `'use client';

import { ConnectButton } from '@rainbow-me/rainbowkit';
import { useAccount, useBalance } from 'wagmi';
import { formatEther } from 'viem';

export default function Home() {
  const { address, isConnected } = useAccount();
  const { data: balance } = useBalance({ address });

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        <header className="flex justify-between items-center mb-8">
          <h1 className="text-2xl font-bold">Arbitrum dApp</h1>
          <ConnectButton />
        </header>

        {isConnected ? (
          <div className="space-y-4">
            <div className="p-4 border rounded-lg">
              <h2 className="text-lg font-semibold mb-2">Wallet Info</h2>
              <p className="text-sm text-gray-600">Address: {address}</p>
              <p className="text-sm text-gray-600">
                Balance: {balance ? formatEther(balance.value) : '0'} ETH
              </p>
            </div>

            {/* Add your contract interactions here */}
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-600">Connect your wallet to get started</p>
          </div>
        )}
      </div>
    </main>
  );
}
`,

  "src/app/globals.css": `@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground-rgb: 0, 0, 0;
  --background-rgb: 255, 255, 255;
}

@media (prefers-color-scheme: dark) {
  :root {
    --foreground-rgb: 255, 255, 255;
    --background-rgb: 10, 10, 10;
  }
}

body {
  color: rgb(var(--foreground-rgb));
  background: rgb(var(--background-rgb));
}
`,

  "src/config/wagmi.ts": `import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import { arbitrum, arbitrumSepolia } from 'wagmi/chains';

export const config = getDefaultConfig({
  appName: 'Arbitrum dApp',
  projectId: process.env.NEXT_PUBLIC_WALLET_CONNECT_ID || 'demo',
  chains: [arbitrumSepolia, arbitrum],
  ssr: true,
});
`,

  "src/config/contract.ts": `// Contract configuration
export const CONTRACT_ADDRESS = process.env.NEXT_PUBLIC_CONTRACT_ADDRESS as \`0x\${string}\`;

// Add your contract ABI here
export const CONTRACT_ABI = [] as const;
`,
};

// Dashboard template additions
const DASHBOARD_FILES = {
  "src/app/page.tsx": `'use client';

import { ConnectButton } from '@rainbow-me/rainbowkit';
import { useAccount, useBalance } from 'wagmi';
import { formatEther } from 'viem';

export default function Dashboard() {
  const { address, isConnected, chain } = useAccount();
  const { data: balance } = useBalance({ address });

  return (
    <main className="min-h-screen bg-base-200">
      <div className="navbar bg-base-100 shadow-lg">
        <div className="flex-1">
          <span className="text-xl font-bold px-4">Dashboard</span>
        </div>
        <div className="flex-none">
          <ConnectButton />
        </div>
      </div>

      <div className="container mx-auto p-6">
        {isConnected ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="stat bg-base-100 rounded-box shadow">
              <div className="stat-title">Network</div>
              <div className="stat-value text-primary">{chain?.name || 'Unknown'}</div>
            </div>

            <div className="stat bg-base-100 rounded-box shadow">
              <div className="stat-title">Balance</div>
              <div className="stat-value">
                {balance ? parseFloat(formatEther(balance.value)).toFixed(4) : '0'} ETH
              </div>
            </div>

            <div className="stat bg-base-100 rounded-box shadow">
              <div className="stat-title">Address</div>
              <div className="stat-value text-sm truncate">{address}</div>
            </div>

            <div className="col-span-full">
              <div className="card bg-base-100 shadow-xl">
                <div className="card-body">
                  <h2 className="card-title">Contract Interactions</h2>
                  <p>Add your contract functions here</p>
                  <div className="card-actions justify-end">
                    <button className="btn btn-primary">Execute</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="hero min-h-[60vh]">
            <div className="hero-content text-center">
              <div>
                <h1 className="text-4xl font-bold">Welcome</h1>
                <p className="py-6">Connect your wallet to access the dashboard</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
`,
};

// Hook template for contract interactions
function generateContractHook(abi: unknown[]): string {
  const readFunctions = abi.filter(
    (item: any) =>
      item.type === "function" &&
      (item.stateMutability === "view" || item.stateMutability === "pure")
  );
  const writeFunctions = abi.filter(
    (item: any) =>
      item.type === "function" &&
      item.stateMutability !== "view" &&
      item.stateMutability !== "pure"
  );

  let code = `'use client';

import { useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { CONTRACT_ADDRESS, CONTRACT_ABI } from '@/config/contract';

`;

  // Generate read hooks
  for (const fn of readFunctions as any[]) {
    const hookName = `useRead${fn.name.charAt(0).toUpperCase() + fn.name.slice(1)}`;
    const hasArgs = fn.inputs && fn.inputs.length > 0;

    code += `export function ${hookName}(${hasArgs ? `args: [${fn.inputs.map((i: any) => `${i.name}: ${getTypeScriptType(i.type)}`).join(", ")}]` : ""}) {
  return useReadContract({
    address: CONTRACT_ADDRESS,
    abi: CONTRACT_ABI,
    functionName: '${fn.name}',${hasArgs ? "\n    args," : ""}
  });
}

`;
  }

  // Generate write hooks
  for (const fn of writeFunctions as any[]) {
    const hookName = `use${fn.name.charAt(0).toUpperCase() + fn.name.slice(1)}`;

    code += `export function ${hookName}() {
  const { writeContract, data: hash, isPending, error } = useWriteContract();
  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({ hash });

  const execute = (${fn.inputs?.map((i: any) => `${i.name}: ${getTypeScriptType(i.type)}`).join(", ") || ""}) => {
    writeContract({
      address: CONTRACT_ADDRESS,
      abi: CONTRACT_ABI,
      functionName: '${fn.name}',${fn.inputs?.length ? `\n      args: [${fn.inputs.map((i: any) => i.name).join(", ")}],` : ""}
    });
  };

  return { execute, hash, isPending, isConfirming, isSuccess, error };
}

`;
  }

  return code;
}

function getTypeScriptType(solidityType: string): string {
  if (solidityType.includes("int")) return "bigint";
  if (solidityType === "address") return "`0x${string}`";
  if (solidityType === "bool") return "boolean";
  if (solidityType.includes("bytes")) return "`0x${string}`";
  if (solidityType === "string") return "string";
  return "unknown";
}

const BASE_DEPS = {
  "next": "^14.0.0",
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "wagmi": "^2.5.0",
  "viem": "^2.0.0",
  "@rainbow-me/rainbowkit": "^2.0.0",
  "@tanstack/react-query": "^5.0.0",
};

const BASE_DEV_DEPS = {
  "typescript": "^5.0.0",
  "@types/node": "^20.0.0",
  "@types/react": "^18.0.0",
  "@types/react-dom": "^18.0.0",
  "tailwindcss": "^3.4.0",
  "postcss": "^8.4.0",
  "autoprefixer": "^10.4.0",
};

const DAISYUI_DEPS = {
  "daisyui": "^4.0.0",
};

export function generateFrontend(args: GenerateFrontendArgs): GenerateFrontendResult {
  const { prompt, contractAbi, uiFramework = "daisyui", template = "base" } = args;

  const files: Record<string, string> = { ...BASE_FILES };
  const dependencies = { ...BASE_DEPS };
  const devDependencies = { ...BASE_DEV_DEPS };

  // Apply template
  if (template === "dashboard") {
    Object.assign(files, DASHBOARD_FILES);
  }

  // Add DaisyUI if selected
  if (uiFramework === "daisyui") {
    Object.assign(dependencies, DAISYUI_DEPS);

    files["tailwind.config.ts"] = `import type { Config } from 'tailwindcss';
import daisyui from 'daisyui';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {},
  },
  plugins: [daisyui],
  daisyui: {
    themes: ['light', 'dark'],
  },
};

export default config;
`;
  } else {
    files["tailwind.config.ts"] = `import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
`;
  }

  // Generate contract hooks if ABI provided
  if (contractAbi) {
    try {
      const abi = JSON.parse(contractAbi);
      files["src/hooks/useContract.ts"] = generateContractHook(abi);
      files["src/config/contract.ts"] = `// Contract configuration
export const CONTRACT_ADDRESS = process.env.NEXT_PUBLIC_CONTRACT_ADDRESS as \`0x\${string}\`;

export const CONTRACT_ABI = ${JSON.stringify(abi, null, 2)} as const;
`;
    } catch {
      // Invalid ABI, skip hook generation
    }
  }

  // Add postcss config
  files["postcss.config.js"] = `module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
`;

  // Add next.config.js
  files["next.config.js"] = `/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};

module.exports = nextConfig;
`;

  // Add tsconfig.json
  files["tsconfig.json"] = JSON.stringify(
    {
      compilerOptions: {
        target: "ES2017",
        lib: ["dom", "dom.iterable", "esnext"],
        allowJs: true,
        skipLibCheck: true,
        strict: true,
        noEmit: true,
        esModuleInterop: true,
        module: "esnext",
        moduleResolution: "bundler",
        resolveJsonModule: true,
        isolatedModules: true,
        jsx: "preserve",
        incremental: true,
        plugins: [{ name: "next" }],
        paths: { "@/*": ["./src/*"] },
      },
      include: ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
      exclude: ["node_modules"],
    },
    null,
    2
  );

  // Add .env.example
  files[".env.example"] = `# WalletConnect Project ID (get from cloud.walletconnect.com)
NEXT_PUBLIC_WALLET_CONNECT_ID=your-project-id

# Contract Address (optional)
NEXT_PUBLIC_CONTRACT_ADDRESS=0x...
`;

  // Add package.json
  files["package.json"] = JSON.stringify(
    {
      name: "arbbuilder-frontend",
      version: "1.0.0",
      private: true,
      scripts: {
        dev: "next dev",
        build: "next build",
        start: "next start",
        lint: "next lint",
      },
      dependencies,
      devDependencies,
    },
    null,
    2
  );

  return {
    files,
    dependencies,
    devDependencies,
    envVars: ["NEXT_PUBLIC_WALLET_CONNECT_ID", "NEXT_PUBLIC_CONTRACT_ADDRESS"],
    setupInstructions: [
      "1. Install dependencies: npm install",
      "2. Copy .env.example to .env.local and configure",
      "3. Get WalletConnect Project ID from cloud.walletconnect.com",
      "4. Run development server: npm run dev",
    ],
  };
}

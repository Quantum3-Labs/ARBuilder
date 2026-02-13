"""
Frontend templates for Next.js applications with Web3 integration.
These templates provide scaffolding for dApp frontends with wagmi, viem, and RainbowKit.

Templates:
- Next.js + wagmi + RainbowKit: Full featured Web3 frontend
- DaisyUI Components: Pre-built Web3 UI components
- Contract Dashboard: Admin panel for contract management
- Token Interface: ERC20/ERC721 token UI
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Placeholder marker replaced at generation time with actual contract ABI
ABI_PLACEHOLDER = "__ABI_PLACEHOLDER__"


@dataclass
class FrontendTemplate:
    """A curated frontend template."""

    name: str
    description: str
    framework: str  # "nextjs"
    features: List[str]
    files: Dict[str, str]  # path -> content
    dependencies: Dict[str, str]
    dev_dependencies: Dict[str, str] = field(default_factory=dict)
    env_vars: List[str] = field(default_factory=list)
    scripts: Dict[str, str] = field(default_factory=dict)


# Next.js + wagmi + RainbowKit Base Template
NEXTJS_WAGMI_TEMPLATE = FrontendTemplate(
    name="Next.js + wagmi + RainbowKit",
    description="Full-featured Web3 frontend with wallet connection and contract interaction",
    framework="nextjs",
    features=[
        "wagmi v2",
        "viem",
        "RainbowKit",
        "TypeScript",
        "App Router",
        "TailwindCSS",
    ],
    files={
        "src/app/layout.tsx": '''import type { Metadata } from 'next';
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
''',
        "src/app/providers.tsx": '''"use client";

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WagmiProvider } from 'wagmi';
import { RainbowKitProvider, darkTheme } from '@rainbow-me/rainbowkit';
import { config } from '@/config/wagmi';
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
''',
        "src/app/page.tsx": '''"use client";

import { ConnectButton } from '@rainbow-me/rainbowkit';
import { useAccount } from 'wagmi';
import { ContractInteraction } from '@/components/ContractInteraction';

export default function Home() {
  const { isConnected } = useAccount();

  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-900 to-gray-800 text-white">
      <div className="container mx-auto px-4 py-8">
        <header className="flex justify-between items-center mb-12">
          <h1 className="text-3xl font-bold">Arbitrum dApp</h1>
          <ConnectButton />
        </header>

        <div className="max-w-2xl mx-auto">
          {isConnected ? (
            <ContractInteraction />
          ) : (
            <div className="text-center py-20">
              <h2 className="text-2xl mb-4">Welcome!</h2>
              <p className="text-gray-400 mb-8">
                Connect your wallet to interact with the contract.
              </p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
''',
        "src/app/globals.css": '''@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground-rgb: 255, 255, 255;
  --background-start-rgb: 17, 24, 39;
  --background-end-rgb: 31, 41, 55;
}

body {
  color: rgb(var(--foreground-rgb));
  background: linear-gradient(
    to bottom,
    rgb(var(--background-start-rgb)),
    rgb(var(--background-end-rgb))
  );
}
''',
        "src/config/wagmi.ts": '''import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import { arbitrum, arbitrumSepolia } from 'wagmi/chains';

export const config = getDefaultConfig({
  appName: 'Arbitrum dApp',
  projectId: process.env.NEXT_PUBLIC_WALLET_CONNECT_ID || 'YOUR_PROJECT_ID',
  chains: [arbitrumSepolia, arbitrum],
  ssr: true,
});
''',
        "src/config/contract.ts": '''import { parseAbi } from 'viem';

export const CONTRACT_ADDRESS = process.env.NEXT_PUBLIC_CONTRACT_ADDRESS as `0x${string}`;

export const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:3001';

export const CONTRACT_ABI = parseAbi(__ABI_PLACEHOLDER__);
''',
        "src/hooks/useContract.ts": '''"use client";

import { useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { CONTRACT_ADDRESS, CONTRACT_ABI } from '@/config/contract';

export function useContractNumber() {
  return useReadContract({
    address: CONTRACT_ADDRESS,
    abi: CONTRACT_ABI,
    functionName: 'number',
  });
}

export function useSetNumber() {
  const { writeContract, data: hash, isPending, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  const setNumber = (newNumber: bigint) => {
    writeContract({
      address: CONTRACT_ADDRESS,
      abi: CONTRACT_ABI,
      functionName: 'setNumber',
      args: [newNumber],
    });
  };

  return {
    setNumber,
    hash,
    isPending,
    isConfirming,
    isSuccess,
    error,
  };
}

export function useIncrement() {
  const { writeContract, data: hash, isPending, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  const increment = () => {
    writeContract({
      address: CONTRACT_ADDRESS,
      abi: CONTRACT_ABI,
      functionName: 'increment',
    });
  };

  return {
    increment,
    hash,
    isPending,
    isConfirming,
    isSuccess,
    error,
  };
}
''',
        "src/components/ContractInteraction.tsx": '''"use client";

import { useState } from 'react';
import { useContractNumber, useSetNumber, useIncrement } from '@/hooks/useContract';
import { formatUnits } from 'viem';

export function ContractInteraction() {
  const [inputValue, setInputValue] = useState('');

  const { data: number, isLoading: isReading, refetch } = useContractNumber();
  const { setNumber, isPending: isSettingNumber, isConfirming: isConfirmingSet } = useSetNumber();
  const { increment, isPending: isIncrementing, isConfirming: isConfirmingIncrement } = useIncrement();

  const handleSetNumber = () => {
    if (inputValue) {
      setNumber(BigInt(inputValue));
      setInputValue('');
    }
  };

  const handleIncrement = () => {
    increment();
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6 shadow-xl">
      <h2 className="text-xl font-semibold mb-6">Contract Interaction</h2>

      {/* Current Value */}
      <div className="mb-8 p-4 bg-gray-700 rounded-lg">
        <p className="text-gray-400 text-sm mb-1">Current Value</p>
        <p className="text-4xl font-bold">
          {isReading ? '...' : number?.toString() || '0'}
        </p>
        <button
          onClick={() => refetch()}
          className="mt-2 text-sm text-blue-400 hover:text-blue-300"
        >
          Refresh
        </button>
      </div>

      {/* Set Number */}
      <div className="mb-6">
        <label className="block text-gray-400 text-sm mb-2">Set New Value</label>
        <div className="flex gap-2">
          <input
            type="number"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter a number"
            className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={handleSetNumber}
            disabled={isSettingNumber || isConfirmingSet || !inputValue}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed px-6 py-2 rounded-lg font-medium transition-colors"
          >
            {isSettingNumber ? 'Confirming...' : isConfirmingSet ? 'Waiting...' : 'Set'}
          </button>
        </div>
      </div>

      {/* Increment */}
      <button
        onClick={handleIncrement}
        disabled={isIncrementing || isConfirmingIncrement}
        className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed py-3 rounded-lg font-medium transition-colors"
      >
        {isIncrementing ? 'Confirming...' : isConfirmingIncrement ? 'Waiting...' : 'Increment'}
      </button>
    </div>
  );
}
''',
        ".env.example": '''# WalletConnect Project ID (get from cloud.walletconnect.com)
NEXT_PUBLIC_WALLET_CONNECT_ID=

# Contract Address
NEXT_PUBLIC_CONTRACT_ADDRESS=0x...

# Backend API URL
NEXT_PUBLIC_BACKEND_URL=http://localhost:3001
''',
        "tailwind.config.ts": '''import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
export default config;
''',
        "next.config.js": '''/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config) => {
    config.externals.push('pino-pretty', 'lokijs', 'encoding');
    return config;
  },
};

module.exports = nextConfig;
''',
        "tsconfig.json": '''{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
''',
    },
    dependencies={
        "next": "^14.0.0",
        "react": "^18.2.0",
        "react-dom": "^18.2.0",
        "wagmi": "^2.5.0",
        "viem": "^2.21.0",
        "@rainbow-me/rainbowkit": "^2.0.0",
        "@tanstack/react-query": "^5.0.0",
    },
    dev_dependencies={
        "typescript": "^5.0.0",
        "@types/node": "^20.0.0",
        "@types/react": "^18.0.0",
        "@types/react-dom": "^18.0.0",
        "tailwindcss": "^3.4.0",
        "postcss": "^8.0.0",
        "autoprefixer": "^10.0.0",
    },
    env_vars=["NEXT_PUBLIC_WALLET_CONNECT_ID", "NEXT_PUBLIC_CONTRACT_ADDRESS", "NEXT_PUBLIC_BACKEND_URL"],
    scripts={
        "dev": "next dev",
        "build": "next build",
        "start": "next start",
        "lint": "next lint",
    },
)


# DaisyUI Component Library Template
DAISYUI_COMPONENTS_TEMPLATE = FrontendTemplate(
    name="DaisyUI Components",
    description="Pre-built Web3 UI components with DaisyUI styling",
    framework="nextjs",
    features=[
        "DaisyUI",
        "Web3 components",
        "Dark theme",
        "Responsive design",
    ],
    files={
        "src/components/ui/Card.tsx": '''"use client";

import { ReactNode } from 'react';

interface CardProps {
  title?: string;
  children: ReactNode;
  className?: string;
}

export function Card({ title, children, className = '' }: CardProps) {
  return (
    <div className={`card bg-base-200 shadow-xl ${className}`}>
      <div className="card-body">
        {title && <h2 className="card-title">{title}</h2>}
        {children}
      </div>
    </div>
  );
}
''',
        "src/components/ui/Button.tsx": '''"use client";

import { ReactNode } from 'react';

interface ButtonProps {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: 'primary' | 'secondary' | 'success' | 'error' | 'ghost';
  size?: 'xs' | 'sm' | 'md' | 'lg';
  className?: string;
}

export function Button({
  children,
  onClick,
  disabled = false,
  loading = false,
  variant = 'primary',
  size = 'md',
  className = '',
}: ButtonProps) {
  const variantClass = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    success: 'btn-success',
    error: 'btn-error',
    ghost: 'btn-ghost',
  }[variant];

  const sizeClass = {
    xs: 'btn-xs',
    sm: 'btn-sm',
    md: '',
    lg: 'btn-lg',
  }[size];

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`btn ${variantClass} ${sizeClass} ${className}`}
    >
      {loading && <span className="loading loading-spinner loading-sm"></span>}
      {children}
    </button>
  );
}
''',
        "src/components/ui/Input.tsx": '''"use client";

interface InputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
  type?: 'text' | 'number' | 'password' | 'email';
  disabled?: boolean;
  error?: string;
  className?: string;
}

export function Input({
  value,
  onChange,
  placeholder,
  label,
  type = 'text',
  disabled = false,
  error,
  className = '',
}: InputProps) {
  return (
    <div className={`form-control ${className}`}>
      {label && (
        <label className="label">
          <span className="label-text">{label}</span>
        </label>
      )}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className={`input input-bordered w-full ${error ? 'input-error' : ''}`}
      />
      {error && (
        <label className="label">
          <span className="label-text-alt text-error">{error}</span>
        </label>
      )}
    </div>
  );
}
''',
        "src/components/ui/Stats.tsx": '''"use client";

interface StatItem {
  title: string;
  value: string | number;
  description?: string;
}

interface StatsProps {
  items: StatItem[];
  className?: string;
}

export function Stats({ items, className = '' }: StatsProps) {
  return (
    <div className={`stats stats-vertical lg:stats-horizontal shadow ${className}`}>
      {items.map((item, index) => (
        <div key={index} className="stat">
          <div className="stat-title">{item.title}</div>
          <div className="stat-value">{item.value}</div>
          {item.description && (
            <div className="stat-desc">{item.description}</div>
          )}
        </div>
      ))}
    </div>
  );
}
''',
        "src/components/ui/Alert.tsx": '''"use client";

import { ReactNode } from 'react';

interface AlertProps {
  children: ReactNode;
  type?: 'info' | 'success' | 'warning' | 'error';
  className?: string;
}

export function Alert({ children, type = 'info', className = '' }: AlertProps) {
  const typeClass = {
    info: 'alert-info',
    success: 'alert-success',
    warning: 'alert-warning',
    error: 'alert-error',
  }[type];

  return (
    <div className={`alert ${typeClass} ${className}`}>
      <span>{children}</span>
    </div>
  );
}
''',
        "src/components/ui/Modal.tsx": '''"use client";

import { ReactNode, useRef, useEffect } from 'react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
}

export function Modal({ isOpen, onClose, title, children }: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (isOpen) {
      dialogRef.current?.showModal();
    } else {
      dialogRef.current?.close();
    }
  }, [isOpen]);

  return (
    <dialog ref={dialogRef} className="modal" onClose={onClose}>
      <div className="modal-box">
        {title && <h3 className="font-bold text-lg mb-4">{title}</h3>}
        {children}
        <div className="modal-action">
          <form method="dialog">
            <button className="btn" onClick={onClose}>
              Close
            </button>
          </form>
        </div>
      </div>
      <form method="dialog" className="modal-backdrop">
        <button onClick={onClose}>close</button>
      </form>
    </dialog>
  );
}
''',
        "src/components/ui/index.ts": '''export { Card } from './Card';
export { Button } from './Button';
export { Input } from './Input';
export { Stats } from './Stats';
export { Alert } from './Alert';
export { Modal } from './Modal';
''',
        "src/components/web3/WalletStatus.tsx": '''"use client";

import { useAccount, useBalance, useDisconnect } from 'wagmi';
import { formatEther } from 'viem';
import { Card, Button } from '../ui';

export function WalletStatus() {
  const { address, isConnected, chain } = useAccount();
  const { data: balance } = useBalance({ address });
  const { disconnect } = useDisconnect();

  if (!isConnected) {
    return null;
  }

  return (
    <Card title="Wallet Status" className="w-full max-w-md">
      <div className="space-y-4">
        <div>
          <p className="text-sm text-base-content/70">Address</p>
          <p className="font-mono text-sm truncate">{address}</p>
        </div>
        <div>
          <p className="text-sm text-base-content/70">Network</p>
          <p className="badge badge-primary">{chain?.name || 'Unknown'}</p>
        </div>
        <div>
          <p className="text-sm text-base-content/70">Balance</p>
          <p className="text-lg font-bold">
            {balance ? `${parseFloat(formatEther(balance.value)).toFixed(4)} ${balance.symbol}` : '...'}
          </p>
        </div>
        <Button variant="ghost" onClick={() => disconnect()} className="w-full">
          Disconnect
        </Button>
      </div>
    </Card>
  );
}
''',
        "src/components/web3/TransactionStatus.tsx": '''"use client";

import { useEffect, useState } from 'react';
import { useWaitForTransactionReceipt } from 'wagmi';
import { Alert } from '../ui';

interface TransactionStatusProps {
  hash?: `0x${string}`;
  onSuccess?: () => void;
}

export function TransactionStatus({ hash, onSuccess }: TransactionStatusProps) {
  const { isLoading, isSuccess, isError } = useWaitForTransactionReceipt({ hash });

  useEffect(() => {
    if (isSuccess && onSuccess) {
      onSuccess();
    }
  }, [isSuccess, onSuccess]);

  if (!hash) return null;

  return (
    <div className="space-y-2">
      {isLoading && (
        <Alert type="info">
          <span className="loading loading-spinner loading-sm mr-2"></span>
          Transaction pending...
        </Alert>
      )}
      {isSuccess && (
        <Alert type="success">Transaction confirmed!</Alert>
      )}
      {isError && (
        <Alert type="error">Transaction failed</Alert>
      )}
    </div>
  );
}
''',
        "src/components/web3/index.ts": '''export { WalletStatus } from './WalletStatus';
export { TransactionStatus } from './TransactionStatus';
''',
        "tailwind.config.ts": '''import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: ['dark', 'light'],
    darkTheme: 'dark',
  },
};
export default config;
''',
    },
    dependencies={
        "next": "^14.0.0",
        "react": "^18.2.0",
        "react-dom": "^18.2.0",
        "wagmi": "^2.5.0",
        "viem": "^2.21.0",
        "@rainbow-me/rainbowkit": "^2.0.0",
        "@tanstack/react-query": "^5.0.0",
        "daisyui": "^4.0.0",
    },
    dev_dependencies={
        "typescript": "^5.0.0",
        "@types/node": "^20.0.0",
        "@types/react": "^18.0.0",
        "tailwindcss": "^3.4.0",
        "postcss": "^8.0.0",
        "autoprefixer": "^10.0.0",
    },
    env_vars=["NEXT_PUBLIC_WALLET_CONNECT_ID"],
    scripts={
        "dev": "next dev",
        "build": "next build",
        "start": "next start",
    },
)


# Contract Dashboard Template
CONTRACT_DASHBOARD_TEMPLATE = FrontendTemplate(
    name="Contract Dashboard",
    description="Admin panel for contract management with read/write operations",
    framework="nextjs",
    features=[
        "Admin panel",
        "Contract stats",
        "Transaction history",
        "Owner functions",
    ],
    files={
        "src/app/dashboard/page.tsx": '''"use client";

import { useAccount } from 'wagmi';
import { ConnectButton } from '@rainbow-me/rainbowkit';
import { ContractStats } from '@/components/dashboard/ContractStats';
import { OwnerActions } from '@/components/dashboard/OwnerActions';
import { RecentTransactions } from '@/components/dashboard/RecentTransactions';

export default function DashboardPage() {
  const { isConnected } = useAccount();

  return (
    <div className="min-h-screen bg-base-300 p-8">
      <div className="max-w-6xl mx-auto">
        <header className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Contract Dashboard</h1>
          <ConnectButton />
        </header>

        {isConnected ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ContractStats />
            <OwnerActions />
            <div className="lg:col-span-2">
              <RecentTransactions />
            </div>
          </div>
        ) : (
          <div className="card bg-base-200 p-12 text-center">
            <h2 className="text-xl mb-4">Connect your wallet to access the dashboard</h2>
          </div>
        )}
      </div>
    </div>
  );
}
''',
        "src/components/dashboard/ContractStats.tsx": '''"use client";

import { useReadContract } from 'wagmi';
import { formatEther } from 'viem';
import { CONTRACT_ADDRESS, CONTRACT_ABI } from '@/config/contract';

export function ContractStats() {
  const { data: number } = useReadContract({
    address: CONTRACT_ADDRESS,
    abi: CONTRACT_ABI,
    functionName: 'number',
  });

  return (
    <div className="card bg-base-200">
      <div className="card-body">
        <h2 className="card-title">Contract Stats</h2>
        <div className="stats stats-vertical shadow">
          <div className="stat">
            <div className="stat-title">Current Number</div>
            <div className="stat-value">{number?.toString() || '0'}</div>
          </div>
          <div className="stat">
            <div className="stat-title">Contract Address</div>
            <div className="stat-value text-sm font-mono truncate">
              {CONTRACT_ADDRESS}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
''',
        "src/components/dashboard/OwnerActions.tsx": '''"use client";

import { useState } from 'react';
import { useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { CONTRACT_ADDRESS, CONTRACT_ABI } from '@/config/contract';

export function OwnerActions() {
  const [newValue, setNewValue] = useState('');
  const { writeContract, data: hash, isPending } = useWriteContract();
  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({ hash });

  const handleSetValue = () => {
    if (newValue) {
      writeContract({
        address: CONTRACT_ADDRESS,
        abi: CONTRACT_ABI,
        functionName: 'setNumber',
        args: [BigInt(newValue)],
      });
      setNewValue('');
    }
  };

  const handleIncrement = () => {
    writeContract({
      address: CONTRACT_ADDRESS,
      abi: CONTRACT_ABI,
      functionName: 'increment',
    });
  };

  return (
    <div className="card bg-base-200">
      <div className="card-body">
        <h2 className="card-title">Owner Actions</h2>

        <div className="form-control">
          <label className="label">
            <span className="label-text">Set New Value</span>
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              className="input input-bordered flex-1"
              placeholder="Enter value"
            />
            <button
              onClick={handleSetValue}
              disabled={isPending || isConfirming || !newValue}
              className="btn btn-primary"
            >
              {isPending ? 'Confirming...' : isConfirming ? 'Waiting...' : 'Set'}
            </button>
          </div>
        </div>

        <button
          onClick={handleIncrement}
          disabled={isPending || isConfirming}
          className="btn btn-secondary mt-4"
        >
          Increment
        </button>

        {isSuccess && (
          <div className="alert alert-success mt-4">
            Transaction confirmed!
          </div>
        )}
      </div>
    </div>
  );
}
''',
        "src/components/dashboard/RecentTransactions.tsx": '''"use client";

import { useWatchContractEvent } from 'wagmi';
import { useState, useEffect } from 'react';
import { CONTRACT_ADDRESS, CONTRACT_ABI } from '@/config/contract';

interface Transaction {
  oldNumber: string;
  newNumber: string;
  timestamp: number;
}

export function RecentTransactions() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);

  // This is a placeholder - in production, you would fetch from indexer
  // or watch events from a known block number

  return (
    <div className="card bg-base-200">
      <div className="card-body">
        <h2 className="card-title">Recent Transactions</h2>

        {transactions.length === 0 ? (
          <p className="text-base-content/70">No recent transactions</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Old Value</th>
                  <th>New Value</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx, i) => (
                  <tr key={i}>
                    <td>{tx.oldNumber}</td>
                    <td>{tx.newNumber}</td>
                    <td>{new Date(tx.timestamp).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
''',
    },
    dependencies={
        "next": "^14.0.0",
        "react": "^18.2.0",
        "react-dom": "^18.2.0",
        "wagmi": "^2.5.0",
        "viem": "^2.21.0",
        "@rainbow-me/rainbowkit": "^2.0.0",
        "@tanstack/react-query": "^5.0.0",
        "daisyui": "^4.0.0",
    },
    dev_dependencies={
        "typescript": "^5.0.0",
        "@types/node": "^20.0.0",
        "@types/react": "^18.0.0",
        "tailwindcss": "^3.4.0",
    },
    env_vars=["NEXT_PUBLIC_WALLET_CONNECT_ID", "NEXT_PUBLIC_CONTRACT_ADDRESS"],
    scripts={
        "dev": "next dev",
        "build": "next build",
        "start": "next start",
    },
)


# Token Interface Template
TOKEN_INTERFACE_TEMPLATE = FrontendTemplate(
    name="Token Interface",
    description="ERC20/ERC721 token UI with transfer, approve, and balance views",
    framework="nextjs",
    features=[
        "ERC20 support",
        "Transfer UI",
        "Approval UI",
        "Balance display",
    ],
    files={
        "src/components/token/TokenBalance.tsx": '''"use client";

import { useReadContract, useAccount } from 'wagmi';
import { formatUnits } from 'viem';
import { TOKEN_ADDRESS, TOKEN_ABI, TOKEN_DECIMALS } from '@/config/token';

export function TokenBalance() {
  const { address } = useAccount();

  const { data: balance, isLoading } = useReadContract({
    address: TOKEN_ADDRESS,
    abi: TOKEN_ABI,
    functionName: 'balanceOf',
    args: address ? [address] : undefined,
    query: { enabled: !!address },
  });

  const { data: symbol } = useReadContract({
    address: TOKEN_ADDRESS,
    abi: TOKEN_ABI,
    functionName: 'symbol',
  });

  if (!address) return null;

  return (
    <div className="card bg-base-200">
      <div className="card-body">
        <h2 className="card-title">Your Balance</h2>
        <p className="text-4xl font-bold">
          {isLoading ? '...' : balance ? formatUnits(balance as bigint, TOKEN_DECIMALS) : '0'}
          {' '}
          <span className="text-xl text-base-content/70">{symbol?.toString()}</span>
        </p>
      </div>
    </div>
  );
}
''',
        "src/components/token/TokenTransfer.tsx": '''"use client";

import { useState } from 'react';
import { useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { parseUnits, isAddress } from 'viem';
import { TOKEN_ADDRESS, TOKEN_ABI, TOKEN_DECIMALS } from '@/config/token';

export function TokenTransfer() {
  const [recipient, setRecipient] = useState('');
  const [amount, setAmount] = useState('');
  const [error, setError] = useState('');

  const { writeContract, data: hash, isPending } = useWriteContract();
  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({ hash });

  const handleTransfer = () => {
    setError('');

    if (!isAddress(recipient)) {
      setError('Invalid recipient address');
      return;
    }

    if (!amount || parseFloat(amount) <= 0) {
      setError('Invalid amount');
      return;
    }

    try {
      const parsedAmount = parseUnits(amount, TOKEN_DECIMALS);
      writeContract({
        address: TOKEN_ADDRESS,
        abi: TOKEN_ABI,
        functionName: 'transfer',
        args: [recipient as `0x${string}`, parsedAmount],
      });
    } catch (e) {
      setError('Invalid amount format');
    }
  };

  return (
    <div className="card bg-base-200">
      <div className="card-body">
        <h2 className="card-title">Transfer Tokens</h2>

        <div className="form-control">
          <label className="label">
            <span className="label-text">Recipient Address</span>
          </label>
          <input
            type="text"
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            placeholder="0x..."
            className="input input-bordered"
          />
        </div>

        <div className="form-control mt-4">
          <label className="label">
            <span className="label-text">Amount</span>
          </label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.0"
            className="input input-bordered"
          />
        </div>

        {error && (
          <div className="alert alert-error mt-4">
            <span>{error}</span>
          </div>
        )}

        {isSuccess && (
          <div className="alert alert-success mt-4">
            <span>Transfer successful!</span>
          </div>
        )}

        <button
          onClick={handleTransfer}
          disabled={isPending || isConfirming || !recipient || !amount}
          className="btn btn-primary mt-4"
        >
          {isPending ? 'Confirming...' : isConfirming ? 'Processing...' : 'Transfer'}
        </button>
      </div>
    </div>
  );
}
''',
        "src/components/token/TokenApprove.tsx": '''"use client";

import { useState } from 'react';
import { useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { parseUnits, isAddress, maxUint256 } from 'viem';
import { TOKEN_ADDRESS, TOKEN_ABI, TOKEN_DECIMALS } from '@/config/token';

export function TokenApprove() {
  const [spender, setSpender] = useState('');
  const [amount, setAmount] = useState('');
  const [unlimited, setUnlimited] = useState(false);

  const { writeContract, data: hash, isPending } = useWriteContract();
  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({ hash });

  const handleApprove = () => {
    if (!isAddress(spender)) return;

    const approvalAmount = unlimited
      ? maxUint256
      : parseUnits(amount || '0', TOKEN_DECIMALS);

    writeContract({
      address: TOKEN_ADDRESS,
      abi: TOKEN_ABI,
      functionName: 'approve',
      args: [spender as `0x${string}`, approvalAmount],
    });
  };

  return (
    <div className="card bg-base-200">
      <div className="card-body">
        <h2 className="card-title">Approve Spending</h2>

        <div className="form-control">
          <label className="label">
            <span className="label-text">Spender Address</span>
          </label>
          <input
            type="text"
            value={spender}
            onChange={(e) => setSpender(e.target.value)}
            placeholder="0x..."
            className="input input-bordered"
          />
        </div>

        <div className="form-control mt-4">
          <label className="label cursor-pointer">
            <span className="label-text">Unlimited Approval</span>
            <input
              type="checkbox"
              checked={unlimited}
              onChange={(e) => setUnlimited(e.target.checked)}
              className="checkbox"
            />
          </label>
        </div>

        {!unlimited && (
          <div className="form-control mt-2">
            <label className="label">
              <span className="label-text">Amount</span>
            </label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.0"
              className="input input-bordered"
            />
          </div>
        )}

        {isSuccess && (
          <div className="alert alert-success mt-4">
            <span>Approval successful!</span>
          </div>
        )}

        <button
          onClick={handleApprove}
          disabled={isPending || isConfirming || !spender}
          className="btn btn-secondary mt-4"
        >
          {isPending ? 'Confirming...' : isConfirming ? 'Processing...' : 'Approve'}
        </button>
      </div>
    </div>
  );
}
''',
        "src/config/token.ts": '''import { parseAbi } from 'viem';

export const TOKEN_ADDRESS = process.env.NEXT_PUBLIC_TOKEN_ADDRESS as `0x${string}`;
export const TOKEN_DECIMALS = 18;

export const TOKEN_ABI = parseAbi([
  'function name() view returns (string)',
  'function symbol() view returns (string)',
  'function decimals() view returns (uint8)',
  'function totalSupply() view returns (uint256)',
  'function balanceOf(address owner) view returns (uint256)',
  'function transfer(address to, uint256 value) returns (bool)',
  'function approve(address spender, uint256 value) returns (bool)',
  'function allowance(address owner, address spender) view returns (uint256)',
  'function transferFrom(address from, address to, uint256 value) returns (bool)',
  'event Transfer(address indexed from, address indexed to, uint256 value)',
  'event Approval(address indexed owner, address indexed spender, uint256 value)',
]);
''',
        "src/components/token/index.ts": '''export { TokenBalance } from './TokenBalance';
export { TokenTransfer } from './TokenTransfer';
export { TokenApprove } from './TokenApprove';
''',
        # Essential Next.js config files
        "tsconfig.json": '''{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
''',
        "next.config.js": '''/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  webpack: (config) => {
    config.resolve.fallback = { fs: false, net: false, tls: false };
    return config;
  },
};

module.exports = nextConfig;
''',
        "tailwind.config.js": '''/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: { extend: {} },
  plugins: [require('daisyui')],
  daisyui: { themes: ['dark'] },
};
''',
        "postcss.config.js": '''module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
''',
        "src/app/globals.css": '''@tailwind base;
@tailwind components;
@tailwind utilities;
''',
        "src/app/layout.tsx": '''import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Token Interface',
  description: 'ERC20 Token Interface',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
''',
        "src/app/providers.tsx": '''"use client";

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WagmiProvider } from 'wagmi';
import { RainbowKitProvider, darkTheme } from '@rainbow-me/rainbowkit';
import { config } from '@/config/wagmi';
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
''',
        "src/app/page.tsx": '''"use client";

import { ConnectButton } from '@rainbow-me/rainbowkit';
import { TokenBalance, TokenTransfer, TokenApprove } from '@/components/token';

export default function Home() {
  return (
    <main className="min-h-screen p-8 bg-base-100">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Token Interface</h1>
          <ConnectButton />
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          <TokenBalance />
          <TokenTransfer />
          <TokenApprove />
        </div>
      </div>
    </main>
  );
}
''',
        "src/config/wagmi.ts": '''import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import { arbitrum, arbitrumSepolia } from 'wagmi/chains';

export const config = getDefaultConfig({
  appName: 'Token Interface',
  projectId: process.env.NEXT_PUBLIC_WALLET_CONNECT_ID || '',
  chains: [arbitrumSepolia, arbitrum],
  ssr: true,
});
''',
    },
    dependencies={
        "next": "^14.0.0",
        "react": "^18.2.0",
        "react-dom": "^18.2.0",
        "wagmi": "^2.5.0",
        "viem": "^2.21.0",
        "@rainbow-me/rainbowkit": "^2.0.0",
        "@tanstack/react-query": "^5.0.0",
        "daisyui": "^4.0.0",
    },
    dev_dependencies={
        "typescript": "^5.0.0",
        "@types/node": "^20.0.0",
        "@types/react": "^18.0.0",
        "tailwindcss": "^3.4.0",
    },
    env_vars=["NEXT_PUBLIC_WALLET_CONNECT_ID", "NEXT_PUBLIC_TOKEN_ADDRESS"],
    scripts={
        "dev": "next dev",
        "build": "next build",
        "start": "next start",
    },
)


# All templates indexed by name
FRONTEND_TEMPLATES = {
    "nextjs_wagmi": NEXTJS_WAGMI_TEMPLATE,
    "daisyui_components": DAISYUI_COMPONENTS_TEMPLATE,
    "contract_dashboard": CONTRACT_DASHBOARD_TEMPLATE,
    "token_interface": TOKEN_INTERFACE_TEMPLATE,
}


def select_frontend_template(prompt: str) -> FrontendTemplate:
    """Select the best frontend template based on prompt keywords."""
    lower_prompt = prompt.lower()

    if any(kw in lower_prompt for kw in ["erc20", "token", "transfer", "approve", "balance"]):
        return TOKEN_INTERFACE_TEMPLATE

    if any(kw in lower_prompt for kw in ["dashboard", "admin", "owner", "manage"]):
        return CONTRACT_DASHBOARD_TEMPLATE

    if any(kw in lower_prompt for kw in ["component", "ui", "daisy"]):
        return DAISYUI_COMPONENTS_TEMPLATE

    return NEXTJS_WAGMI_TEMPLATE


def get_frontend_template(name: str) -> Optional[FrontendTemplate]:
    """Get a specific frontend template by name."""
    return FRONTEND_TEMPLATES.get(name)


def list_frontend_templates() -> List[FrontendTemplate]:
    """List all available frontend templates."""
    return [
        NEXTJS_WAGMI_TEMPLATE,
        DAISYUI_COMPONENTS_TEMPLATE,
        CONTRACT_DASHBOARD_TEMPLATE,
        TOKEN_INTERFACE_TEMPLATE,
    ]


def generate_hooks_from_abi(abi: List[str]) -> str:
    """Generate typed React hooks from ABI human-readable strings.

    Creates useRead<Name>() hooks for view/pure functions and
    useWrite<Name>() hooks for state-mutating functions.

    Args:
        abi: Human-readable ABI strings (e.g. "function balanceOf(address) view returns (uint256)").

    Returns:
        TypeScript source code for a hooks file.
    """
    read_hooks = []
    write_hooks = []

    for entry in abi:
        entry = entry.strip()
        if not entry.startswith("function "):
            continue

        # Parse function name
        func_part = entry[len("function "):]
        paren_idx = func_part.index("(")
        func_name = func_part[:paren_idx]

        # Determine if read or write
        is_view = " view " in entry or " pure " in entry

        # Create PascalCase hook name
        pascal_name = func_name[0].upper() + func_name[1:]

        if is_view:
            read_hooks.append(f'''export function useRead{pascal_name}(...args: readonly unknown[]) {{
  return useReadContract({{
    address: CONTRACT_ADDRESS,
    abi: CONTRACT_ABI,
    functionName: '{func_name}',
    args: args.length ? args : undefined,
  }});
}}''')
        else:
            write_hooks.append(f'''export function useWrite{pascal_name}() {{
  const {{ writeContract, data: hash, isPending, error }} = useWriteContract();
  const {{ isLoading: isConfirming, isSuccess }} = useWaitForTransactionReceipt({{ hash }});

  const {func_name} = (...args: unknown[]) => {{
    writeContract({{
      address: CONTRACT_ADDRESS,
      abi: CONTRACT_ABI,
      functionName: '{func_name}',
      args: args as never[],
    }});
  }};

  return {{ {func_name}, hash, isPending, isConfirming, isSuccess, error }};
}}''')

    all_hooks = read_hooks + write_hooks
    if not all_hooks:
        return ""

    return '''"use client";

import {{ useReadContract, useWriteContract, useWaitForTransactionReceipt }} from 'wagmi';
import {{ CONTRACT_ADDRESS, CONTRACT_ABI }} from '@/config/contract';

''' + "\n\n".join(all_hooks) + "\n"


def render_with_abi(files: Dict[str, str], abi_human_readable: List[str]) -> Dict[str, str]:
    """Replace ABI placeholders in frontend template files with actual ABI.

    If ABI is available, also generates typed hooks from the ABI entries.

    Args:
        files: Dict of path -> content from a FrontendTemplate.
        abi_human_readable: Human-readable ABI strings for viem's parseAbi().

    Returns:
        New files dict with placeholders replaced and hooks generated.
    """
    rendered = {}
    for path, content in files.items():
        if ABI_PLACEHOLDER in content:
            hr_lines = json.dumps(abi_human_readable, indent=2)
            content = content.replace(ABI_PLACEHOLDER, hr_lines)
        rendered[path] = content

    # Generate ABI-aware hooks if ABI has function entries
    if abi_human_readable:
        hooks_code = generate_hooks_from_abi(abi_human_readable)
        if hooks_code:
            rendered["src/hooks/useContract.ts"] = hooks_code

    return rendered

"""
Frontend Coding Rules Resource.

Provides coding guidelines and patterns for Next.js frontend development
with wagmi, viem, and RainbowKit for Arbitrum dApps.
"""

FRONTEND_CODING_RULES = {
    "name": "Frontend Coding Rules",
    "version": "1.0.0",
    "description": "Guidelines for generating Web3 frontend applications",

    "framework_stack": {
        "nextjs": {
            "version": "14.x",
            "router": "app",
            "description": "React framework with App Router",
        },
        "wagmi": {
            "version": "2.x",
            "description": "React hooks for Ethereum",
        },
        "viem": {
            "version": "2.x",
            "description": "TypeScript Ethereum library",
        },
        "rainbowkit": {
            "version": "2.x",
            "description": "Wallet connection UI",
        },
        "tanstack_query": {
            "version": "5.x",
            "description": "Data fetching and caching",
        },
    },

    "project_structure": {
        "directories": {
            "src/app": "Next.js app router pages",
            "src/components": "Reusable React components",
            "src/components/ui": "Base UI components",
            "src/components/web3": "Web3-specific components",
            "src/hooks": "Custom React hooks",
            "src/config": "Configuration files (wagmi, contract ABIs)",
            "src/lib": "Utility functions",
            "src/types": "TypeScript type definitions",
        },
    },

    "wagmi_setup": {
        "config": '''import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import { arbitrum, arbitrumSepolia } from 'wagmi/chains';

export const config = getDefaultConfig({
  appName: 'My dApp',
  projectId: process.env.NEXT_PUBLIC_WALLET_CONNECT_ID!,
  chains: [arbitrumSepolia, arbitrum],
  ssr: true, // Required for Next.js
});''',

        "provider": '''"use client";

import { WagmiProvider } from 'wagmi';
import { RainbowKitProvider } from '@rainbow-me/rainbowkit';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { config } from '@/config/wagmi';

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
}''',
    },

    "patterns": {
        "read_contract": {
            "description": "Read data from smart contracts",
            "hook": '''import { useReadContract } from 'wagmi';
import { CONTRACT_ABI, CONTRACT_ADDRESS } from '@/config/contract';

export function useBalance(address?: `0x${string}`) {
  return useReadContract({
    address: CONTRACT_ADDRESS,
    abi: CONTRACT_ABI,
    functionName: 'balanceOf',
    args: address ? [address] : undefined,
    query: {
      enabled: !!address, // Only run when address is available
      refetchInterval: 10000, // Refetch every 10 seconds
    },
  });
}''',
        },

        "write_contract": {
            "description": "Write to smart contracts with transaction tracking",
            "hook": '''import { useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { CONTRACT_ABI, CONTRACT_ADDRESS } from '@/config/contract';

export function useTransfer() {
  const { writeContract, data: hash, isPending, error } = useWriteContract();

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
    hash,
    isPending,
    isConfirming,
    isSuccess,
    error,
  };
}''',
        },

        "account_state": {
            "description": "Access connected wallet state",
            "example": '''import { useAccount, useBalance, useDisconnect } from 'wagmi';

function WalletInfo() {
  const { address, isConnected, chain } = useAccount();
  const { data: balance } = useBalance({ address });
  const { disconnect } = useDisconnect();

  if (!isConnected) return <ConnectButton />;

  return (
    <div>
      <p>Address: {address}</p>
      <p>Balance: {formatEther(balance?.value ?? 0n)} ETH</p>
      <p>Chain: {chain?.name}</p>
      <button onClick={() => disconnect()}>Disconnect</button>
    </div>
  );
}''',
        },

        "error_handling": {
            "description": "Handle Web3 errors gracefully",
            "example": '''function TransactionButton() {
  const { transfer, isPending, isConfirming, isSuccess, error } = useTransfer();

  return (
    <div>
      <button
        onClick={() => transfer(address, amount)}
        disabled={isPending || isConfirming}
      >
        {isPending ? 'Confirm in wallet...' :
         isConfirming ? 'Waiting for confirmation...' :
         'Transfer'}
      </button>

      {isSuccess && <Alert type="success">Transaction confirmed!</Alert>}

      {error && (
        <Alert type="error">
          {error.message.includes('User rejected')
            ? 'Transaction cancelled'
            : 'Transaction failed'}
        </Alert>
      )}
    </div>
  );
}''',
        },

        "loading_states": {
            "description": "Handle loading states properly",
            "example": '''function TokenBalance() {
  const { address } = useAccount();
  const { data, isLoading, error, refetch } = useBalance({ address });

  if (isLoading) return <Skeleton className="h-8 w-32" />;
  if (error) return <ErrorDisplay error={error} />;

  return (
    <div>
      <span>{formatEther(data?.value ?? 0n)} ETH</span>
      <button onClick={() => refetch()}>Refresh</button>
    </div>
  );
}''',
        },
    },

    "ui_components": {
        "daisyui": {
            "description": "Tailwind CSS component library",
            "setup": '''// tailwind.config.ts
import daisyui from 'daisyui';

export default {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  plugins: [daisyui],
  daisyui: {
    themes: ['dark', 'light'],
    darkTheme: 'dark',
  },
};''',
            "components": [
                "btn - Buttons with variants",
                "card - Content containers",
                "modal - Dialog boxes",
                "alert - Notifications",
                "input - Form inputs",
                "stats - Statistics display",
                "skeleton - Loading placeholders",
            ],
        },
    },

    "best_practices": [
        "Always use 'use client' directive for components with hooks",
        "Handle all loading, error, and success states",
        "Use BigInt for all token amounts",
        "Format values with viem utilities (formatEther, formatUnits)",
        "Validate addresses with isAddress before use",
        "Implement proper TypeScript types for contract interactions",
        "Use environment variables for configuration",
        "Add refetch intervals for real-time data",
        "Handle wallet disconnection gracefully",
        "Support multiple chains with chain switching",
    ],

    "security": {
        "rules": [
            "Never expose private keys in frontend code",
            "Validate all user inputs before transactions",
            "Use checksummed addresses",
            "Display transaction details before confirmation",
            "Implement slippage protection for DeFi operations",
            "Warn users about high-value transactions",
        ],
    },

    "dependencies": {
        "core": {
            "next": "^14.0.0",
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "wagmi": "^2.5.0",
            "viem": "^2.0.0",
            "@rainbow-me/rainbowkit": "^2.0.0",
            "@tanstack/react-query": "^5.0.0",
        },
        "ui": {
            "tailwindcss": "^3.4.0",
            "daisyui": "^4.0.0",
        },
        "dev": {
            "typescript": "^5.0.0",
            "@types/react": "^18.0.0",
        },
    },

    "environment_variables": {
        "public": [
            "NEXT_PUBLIC_WALLET_CONNECT_ID - WalletConnect project ID",
            "NEXT_PUBLIC_CONTRACT_ADDRESS - Deployed contract address",
        ],
        "note": "All frontend env vars must be prefixed with NEXT_PUBLIC_",
    },
}

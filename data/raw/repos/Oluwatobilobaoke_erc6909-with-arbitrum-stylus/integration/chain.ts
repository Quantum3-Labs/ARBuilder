import { createWalletClient, defineChain, http, publicActions } from "viem";
import { privateKeyToAccount } from "viem/accounts";

// Arbitrum Sepolia RPC URL
export const ARBITRUM_SEPOLIA_RPC_URL = "https://sepolia-rollup.arbitrum.io/rpc";

// Get private key from environment variable
const privateKey = process.env.PRIVATE_KEY;
if (!privateKey) {
  throw new Error("Please set PRIVATE_KEY environment variable");
}

// Ensure private key has 0x prefix
const formattedPrivateKey = privateKey.startsWith('0x') 
  ? privateKey as `0x${string}`
  : `0x${privateKey}` as `0x${string}`;

// Define the Arbitrum Sepolia chain object
export const arbitrumSepolia = defineChain({
  id: 421614,
  name: "Arbitrum Sepolia",
  nativeCurrency: {
    name: "Ether",
    symbol: "ETH",
    decimals: 18,
  },
  rpcUrls: {
    default: {
      http: [ARBITRUM_SEPOLIA_RPC_URL],
    },
  },
  blockExplorers: {
    default: {
      name: "Arbiscan",
      url: "https://sepolia.arbiscan.io",
    },
  },
});

// Create a wallet client that can be used to send transactions and make calls to Arbitrum Sepolia
export const walletClient = createWalletClient({
  chain: arbitrumSepolia,
  transport: http(),
  account: privateKeyToAccount(formattedPrivateKey),
}).extend(publicActions);
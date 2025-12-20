// Define custom Stylus chain
import { defineChain } from 'viem'

export const localhost = defineChain({
  id: 412346,
  name: 'Nitro Localhost',
  network: 'Nitro localhost',
  nativeCurrency: {
    decimals: 18,
    name: 'ETH',
    symbol: 'ETH',
  },
  rpcUrls: {
    default: {
      // In Codespaces: use the forwarded URL from the Ports tab for browser/wallet connections. For CLI tools inside the Codespace terminal, localhost works.
      http: ['http://localhost:8547'],
      // In Codespaces: use the forwarded WebSocket URL from the Ports tab for browser/wallet connections. For CLI tools inside the Codespace terminal, localhost works.
      webSocket: ['ws://localhost:8547']
    },
    public: {
      // In Codespaces: use the forwarded URL from the Ports tab for browser/wallet connections. For CLI tools inside the Codespace terminal, localhost works.
      http: ['http://localhost:8547'],
      // In Codespaces: use the forwarded WebSocket URL from the Ports tab for browser/wallet connections. For CLI tools inside the Codespace terminal, localhost works.
      webSocket: ['ws://localhost:8547']
    },
  },
  testnet: false,
})
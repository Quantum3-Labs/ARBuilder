interface Window {
  ethereum?: {
    isMetaMask?: boolean;
    isConnected: () => boolean;
    request: (request: { method: string; params?: any[] }) => Promise<any>;
    selectedAddress?: string;
    chainId?: string;
    networkVersion?: string;
    on?: (event: string, callback: (...args: any[]) => void) => void;
    removeListener?: (event: string, callback: (...args: any[]) => void) => void;
  };
}

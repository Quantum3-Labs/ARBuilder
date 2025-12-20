import { useState, useEffect } from 'react';
import { WalletClient, PublicClient, formatEther } from 'viem';

interface ETHBalanceProps {
  walletClient?: WalletClient;
  publicClient?: PublicClient;
  account?: string;
}

export default function ETHBalance({ publicClient, account }: ETHBalanceProps) {
  const [balance, setBalance] = useState<bigint>(0n);

  useEffect(() => {
    const fetchBalance = async () => {
      if (!publicClient || !account) return;
      
      try {
        const balance = await publicClient.getBalance({
          address: account as `0x${string}`
        });
        setBalance(balance);
      } catch (error) {
        console.error('Failed to fetch balance', error);
      }
    };

    fetchBalance();
    const interval = setInterval(fetchBalance, 5000); // Update every 5 seconds
    return () => clearInterval(interval);
  }, [publicClient, account]);

  return (
    <div className="balance-container">
      <h2>Balance {account && <small className='text-gray-500 text-sm'>{account.slice(0, 6)}...{account.slice(-4)}</small>}</h2>
      <p className="balance-display">
        {formatEther(balance)} ETH
      </p>
    </div>
  );
}

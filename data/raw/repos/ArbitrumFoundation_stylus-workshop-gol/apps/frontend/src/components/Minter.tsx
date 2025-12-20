import React, { useState, useEffect, useCallback } from 'react';
import GameOfLifeNFTAbi from '../abi/GameOfLifeNFT.json';
import { useWeb3 } from '../contexts/Web3Context';
import { localhost } from '../constants';


interface TokenData {
  id: bigint;
  uri: string;
}

interface MinterProps {
  contractAddress: string;
  name: string;
  abi?: any;
}

const Minter: React.FC<MinterProps> = ({ contractAddress, name, abi }) => {
  const usedAbi = abi || GameOfLifeNFTAbi;
  const { publicClient, walletClient, address: account, isConnected, connect } = useWeb3();

  React.useEffect(() => {
    if (!isConnected && typeof window !== 'undefined' && (window as any).ethereum) {
      connect();
    }
  }, [isConnected, connect]);
  const [tokenData, setTokenData] = useState<TokenData[]>([]);
  
  const [isLoading, setIsLoading] = useState(false);
  const [isMinting, setIsMinting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchUserMints = useCallback(async () => {
    if (!publicClient || !account) return;
    if (!contractAddress || contractAddress.length !== 42) {
      console.error('[Minter] Invalid contract address:', contractAddress);
      setError('Invalid contract address: ' + contractAddress);
      setTokenData([]);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const logs = await publicClient.getLogs({
        address: contractAddress as `0x${string}`,
        event: usedAbi.find((e: any) => e.type === 'event' && e.name === 'Transfer') as any,
        fromBlock: 0n,
        toBlock: 'latest',
      });
      // Only keep tokens minted to this user
      const tokenIds = logs
        .filter((log: any) => log.args && log.args.to && log.args.to.toLowerCase() === account.toLowerCase())
        .map((log: any) => log.args.tokenId as bigint);
      
      if (tokenIds.length === 0) {
        setTokenData([]);
        setIsLoading(false);
        return;
      }
      const tokenDataPromises = tokenIds.map(async (id: bigint) => {
        try {
          const uri = await publicClient.readContract({
            address: contractAddress as `0x${string}`,
            abi: usedAbi,
            functionName: 'tokenURI',
            args: [id]
          });
          return { id, uri: uri as string };
        } catch (e) {
          console.error('[Minter] Error reading tokenURI for', id.toString(), e);
          return { id, uri: 'ERROR' };
        }
      });
      const tokenDataResults = await Promise.all(tokenDataPromises);
      setTokenData(tokenDataResults);
      
    } catch (error) {
      console.error('[Minter] Error fetching NFTs:', error);
      setError('Failed to fetch NFTs: ' + (error instanceof Error ? error.message : String(error)));
      setTokenData([]);
    } finally {
      setIsLoading(false);
    }
  }, [account, publicClient, contractAddress, abi]);

  // Mint NFT
  const handleMint = useCallback(async () => {
    if (!contractAddress || contractAddress.length !== 42) {
      setError('Invalid contract address: ' + contractAddress);
      console.error('[Minter] Invalid contract address:', contractAddress);
      return;
    }
    if (!walletClient || !account) {
      console.error('[Minter] Not connected to wallet');
      return;
    }
    try {
      setError(null);
      setIsMinting(true);
      try {
        await Promise.race([
          walletClient.writeContract({
            address: contractAddress as `0x${string}`,
            abi: usedAbi,
            functionName: 'mint',
            account: account as `0x${string}`,
            args: [],
            chain: localhost
          }),
          new Promise((_, reject) => setTimeout(() => {
            reject(new Error('writeContract timed out after 30s'));
          }, 30000))
        ]);
        console.log('[Minter] Mint transaction sent!');
      } catch (err) {
        console.error('[Minter] Error during mint:', err);
        throw err;
      }
      setTimeout(() => fetchUserMints(), 2000);
    } catch (error) {
      console.error('[Minter] Mint failed:', error);
      setError('Mint failed');
    } finally {
      setIsMinting(false);
    }
  }, [walletClient, account, contractAddress, abi, fetchUserMints]);

  useEffect(() => {
    if (isConnected && account && publicClient) {
      fetchUserMints();
      const interval = setInterval(fetchUserMints, 10000); // Refresh every 10 seconds
      return () => clearInterval(interval);
    } else {
      setTokenData([]);
      (0n);
    }
  }, [isConnected, account, publicClient, fetchUserMints]);

  return (
    <div className="minter-container p-6 max-w-2xl mx-auto bg-gray-800 rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold text-white mb-2 text-center">Game of Life NFT Minter</h2>
      {name && (
        <h3 className="text-lg font-semibold text-blue-300 mb-6 text-center">{name}</h3>
      )}
      {!isConnected || !account ? (
        <div className="flex flex-col items-center">
          <p className="text-gray-300 text-center">Please connect your wallet to mint an NFT</p>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="flex flex-col items-center">
            <button
              onClick={handleMint}
              disabled={isMinting || !isConnected}
              className={`px-6 py-3 rounded-lg font-medium text-white ${
                isMinting || !isConnected
                  ? 'bg-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              } transition-colors`}
            >
              {isMinting ? 'Minting...' : 'Mint NFT'}
            </button>
            {error && <p className="mt-2 text-red-400 text-sm">{error}</p>}
          </div>

          {isLoading ? (
            <div className="text-center text-gray-400">Loading your NFTs...</div>
          ) : (
            <React.Fragment>
              {tokenData.length > 0 ? (
                <div>
                  <h3 className="text-xl font-semibold text-white mb-4">
                    Your NFTs ({tokenData.length.toString()}):
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {tokenData.map(({ id, uri }) => (
                      <div key={id.toString()} className="bg-gray-700 p-4 rounded-lg">
                        <div
                          className="aspect-square bg-white rounded mb-2 flex items-center justify-center overflow-hidden p-2"
                          dangerouslySetInnerHTML={{ __html: uri }}
                        />
                        <p className="text-white text-center">Token ID: {id.toString()}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-gray-400">No NFTs found for your account.</p>
              )}
            </React.Fragment>
          )}
        </div>
      )}
    </div>
  );
};

export default Minter;

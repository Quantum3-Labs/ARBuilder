import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import FortuneAbi from './abi/Fortune.json';
import { Sparkles, Cookie } from 'lucide-react';

const contractAddress = '0xa6e41ffd769491a42a6e5ce453259b93983a22ef';

const fortunesList: string[] = [
  "You call that decentralization? Put your trust in consensus, not in bubkes!",
  "A hard fork in life is coming, pick the right chain, or you’ll be schvitzing for years!",
  "Be open to new opportunities! But read the smart contract twice, you don’t want surprises.",
  "A joyful event is coming your way! Hopefully, it's an airdrop and not a rug pull!",
  "You want security? Don’t trust, verify. Even your own mother checks the receipts!",
  "One day, your portfolio will moon. Today is not that day. HODL, bubbeleh.",
  "A pleasant surprise is waiting for you! Unless it’s gas fees—then, it’s just highway robbery.",
  "Hard work pays off in the future! So does staking, just don’t lock it for 100 years, nu?",
  "Remember, life is like a smart contract: no take-backs once it's deployed!",
  "You’re worried about volatility? Feh! Try raising children, then we’ll talk!",
  "Mazal tov, you found a new NFT! Now if only someone wanted to buy it.",
  "Your next trade will be legendary! Or a shanda. There is no in-between.",
  "Why do you need a DAO for everything? Just call your mother, she’ll tell you what to do!",
  "If you get scammed, don't kvetch, next time, don’t sign transactions without checking!",
  "The best time to buy was yesterday. The second-best time? After calling your mother.",
  "Patience is a virtue, so is cold storage. You want to keep your tokens or what?",
  "A bear market is just a long Shabbat, relax, eat something, and don’t panic-sell!",
];


const App: React.FC = () => {
  const [provider, setProvider] = useState<ethers.JsonRpcProvider | null>(null);
  const [contract, setContract] = useState<ethers.Contract | null>(null);
  const [fortuneText, setFortuneText] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    // Using a local rpc provider. If deployed with real funds to Arbitrum, you could just use
    // window.ethereum to connect to the user's wallet.
    const rpcUrl = 'http://localhost:8547';
    const prov = new ethers.JsonRpcProvider(rpcUrl);
    setProvider(prov);
    // Create a contract instance using the provider
    const contractInstance = new ethers.Contract(contractAddress, FortuneAbi, prov);
    setContract(contractInstance);
  }, []);

  const generateFortune = async () => {
    if (!contract) return;
    setIsGenerating(true);
    
    try {
      const total: bigint = await contract.totalMintedValue();
      const totalValue = Number(total);
      if (totalValue === 0) {
        setFortuneText("No fortunes minted yet");
        return;
      }
  
      const randomIndex = Math.floor(Math.random() * totalValue);
      const fortuneRaw: bigint = await contract.getFortune(randomIndex);
      const fortuneNumber = Number(fortuneRaw);
      
      const mappedFortune = fortunesList[fortuneNumber % fortunesList.length];
      setFortuneText(mappedFortune);
    } catch (error) {
      console.error("Error generating fortune:", error);
      setFortuneText("Error generating fortune. Please try again.");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0B0C2A] via-[#141654] to-[#1C1E78] flex flex-col items-center justify-center p-4 md:p-8">
      <div className="w-full max-w-lg bg-[#0B0C2A]/60 border border-[#2D31A6]/20 backdrop-blur-xl shadow-2xl rounded-xl">
        <div className="p-6 md:p-8 space-y-8">
          <div className="space-y-2 text-center">
            <div className="flex justify-center">
              <div className="relative">
                <Cookie className="w-12 h-12 text-[#2D31A6]" />
                <div className="absolute -top-1 -right-1">
                  <Sparkles className="w-4 h-4 text-[#7B7EF4]" />
                </div>
              </div>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-[#7B7EF4] to-[#2D31A6]">
              Fortune Generator
            </h1>
            <p className="text-sm text-white/60 flex items-center justify-center gap-2">
              Discover a piece of timeless advice powered by
              <img src="/arb-logo.png" alt="Arbitrum Logo" width={16} height={16} className="inline-block" />
            </p>
          </div>

          <div className="flex justify-center">
            <button
              onClick={generateFortune}
              disabled={isGenerating || !contract}
              className="relative group px-8 py-6 bg-gradient-to-r from-[#2D31A6] to-[#7B7EF4] hover:from-[#7B7EF4] hover:to-[#2D31A6] text-white rounded-lg shadow-lg transition-all duration-300 hover:shadow-[#2D31A6]/20 hover:scale-105 disabled:opacity-50 disabled:hover:scale-100"
            >
              <span className="relative z-10 flex items-center gap-2">
                {isGenerating ? (
                  <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                ) : (
                  <Sparkles className="w-5 h-5" />
                )}
                {!contract ? "Connecting..." : isGenerating ? "Generating..." : "Generate Fortune"}
              </span>
            </button>
          </div>

          {fortuneText && (
            <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="h-px bg-gradient-to-r from-transparent via-[#2D31A6]/50 to-transparent" />
              <div className="space-y-2 text-center">
                <h2 className="text-sm font-medium text-[#7B7EF4]">Your Fortune</h2>
                <p className="text-lg text-white/90 italic">"{fortuneText}"</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
};

export default App;

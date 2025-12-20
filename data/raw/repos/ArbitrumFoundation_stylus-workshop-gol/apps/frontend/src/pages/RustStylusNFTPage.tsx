import Minter from '../components/Minter';
import { CONTRACT_ADDRESSES } from '../config/contracts';

// Use the contract address from centralized constants
const RUST_NFT_CONTRACT_ADDRESS = CONTRACT_ADDRESSES.RUST_NFT;

export default function RustStylusNFTPage() {
  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-white mb-2">Game of Life on Stylus</h1>
        <p className="text-gray-300">Mint your game of life NFT on Arbitrum Stylus</p>
      </div>
      
      <div className="bg-gray-900 rounded-lg p-6 shadow-lg">
        <Minter 
          key={RUST_NFT_CONTRACT_ADDRESS}
          contractAddress={RUST_NFT_CONTRACT_ADDRESS} 
          name="Rust + Stylus NFT"
        />
      </div>
      
      <div className="mt-8 p-6 bg-gray-900 rounded-lg">
        <h2 className="text-2xl font-semibold text-white mb-4">About Rust + Stylus NFT</h2>
        <p className="text-gray-300 mb-4">
          This is an NFT contract written in Rust and compiled to WebAssembly (Wasm) and deployed on Arbitrum Stylus.
        </p>
        <p className="text-gray-300">
          Connect your wallet to mint a new NFT or view your existing collection.
        </p>
      </div>
    </div>
  );
}

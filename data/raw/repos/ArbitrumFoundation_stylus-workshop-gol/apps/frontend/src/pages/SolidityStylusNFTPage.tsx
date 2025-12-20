import Minter from '../components/Minter';
import { CONTRACT_ADDRESSES } from '../config/contracts';
import SolidityStylusNFTAbi from '../abi/SolidityStylusNFT.json';

const SOLIDITY_STYLUS_NFT_CONTRACT_ADDRESS = CONTRACT_ADDRESSES.SOLIDITY_AND_STYLUS_NFT;

export default function SolidityStylusNFTPage() {
  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-white mb-2">Solidity + Stylus NFT</h1>
        <p className="text-gray-300">Mint your hybrid Solidity + Stylus NFT on Arbitrum Stylus</p>
      </div>
      
      <div className="bg-gray-900 rounded-lg p-6 shadow-lg">
        <Minter 
          key={SOLIDITY_STYLUS_NFT_CONTRACT_ADDRESS}
          contractAddress={SOLIDITY_STYLUS_NFT_CONTRACT_ADDRESS} 
          name="Solidity + Stylus NFT"
          abi={SolidityStylusNFTAbi}
        />
      </div>
      
      <div className="mt-8 p-6 bg-gray-900 rounded-lg">
        <h2 className="text-2xl font-semibold text-white mb-4">About Solidity + Stylus NFT</h2>
        <p className="text-gray-300 mb-4">
          This is a hybrid NFT contract that combines Solidity with Stylus, a WebAssembly (Wasm) runtime for Ethereum.
          It leverages the performance benefits of Stylus while maintaining compatibility with existing Solidity tooling.
        </p>
        <p className="text-gray-300">
          Connect your wallet to mint a new NFT or view your existing collection.
        </p>
      </div>
    </div>
  );
}

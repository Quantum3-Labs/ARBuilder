import Minter from '../components/Minter';
import { CONTRACT_ADDRESSES } from '../config/contracts';
import SolidityNFTAbi from '../abi/SolidityNFT.json';

const SOLIDITY_NFT_CONTRACT_ADDRESS = CONTRACT_ADDRESSES.SOLIDITY_NFT;

const SolidityNFTPage = () => {
  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-white mb-2">Solidity NFT</h1>
        <p className="text-gray-300">Mint your Solidity-based NFT on Arbitrum Stylus</p>
      </div>
      
      <div className="bg-gray-900 rounded-lg p-6 shadow-lg">
        <Minter 
          key={SOLIDITY_NFT_CONTRACT_ADDRESS}
          contractAddress={SOLIDITY_NFT_CONTRACT_ADDRESS} 
          name="Solidity NFT"
          abi={SolidityNFTAbi}
        />
      </div>
      
      <div className="mt-8 p-6 bg-gray-900 rounded-lg">
        <h2 className="text-2xl font-semibold text-white mb-4">About Solidity NFT</h2>
        <p className="text-gray-300">
          This is a standard ERC-721 NFT contract written in Solidity and deployed on the Arbitrum Stylus chain.
          Connect your wallet to mint a new NFT or view your existing collection.
        </p>
      </div>
    </div>
  );
};

export default SolidityNFTPage;

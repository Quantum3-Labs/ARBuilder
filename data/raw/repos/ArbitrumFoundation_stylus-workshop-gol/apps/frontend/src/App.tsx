import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import RustStylusNFTPage from './pages/RustStylusNFTPage';
import SolidityNFTPage from './pages/SolidityNFTPage';
import SolidityStylusNFTPage from './pages/SolidityStylusNFTPage';
import Layout from './components/Layout';
import { Web3Provider } from './contexts/Web3Context';

// Import contract constants
import { CONTRACT_ADDRESSES } from './config/contracts';

export const {
  RUST_NFT: RUST_NFT_CONTRACT_ADDRESS,
  SOLIDITY_NFT: SOLIDITY_NFT_CONTRACT_ADDRESS,
  SOLIDITY_AND_STYLUS_NFT: SOLIDITY_AND_STYLUS_NFT_CONTRACT_ADDRESS,
} = CONTRACT_ADDRESSES;

const App = (): JSX.Element => {
  return (
    <Web3Provider>
      <Router>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<RustStylusNFTPage />} />
            <Route path="rust-stylus" element={<RustStylusNFTPage />} />
            <Route path="solidity" element={<SolidityNFTPage />} />
            <Route path="solidity-stylus" element={<SolidityStylusNFTPage />} />
          </Route>
        </Routes>
      </Router>
    </Web3Provider>
  );
};

export default App;
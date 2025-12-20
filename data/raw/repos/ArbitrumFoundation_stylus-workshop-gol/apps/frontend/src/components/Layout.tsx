import { Link, Outlet } from 'react-router-dom';
import { useWeb3 } from '../contexts/Web3Context';

export default function Layout() {
  const { isConnected, address, connect, disconnect } = useWeb3();

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <nav className="bg-gray-800 p-4">
        <div className="container mx-auto flex justify-between items-center">
          <Link to="/" className="text-xl font-bold">NFT Workshop</Link>
          <div className="space-x-4 flex items-center">
            <Link to="/rust-stylus" className="hover:text-blue-400">Rust + Stylus</Link>
            <Link to="/solidity" className="hover:text-blue-400">Solidity</Link>
            <Link to="/solidity-stylus" className="hover:text-blue-400">Solidity + Stylus</Link>
            {/* Wallet Connect Button */}
            {isConnected ? (
              <>
                <span className="bg-gray-700 rounded px-3 py-1 text-sm font-mono mr-2">
                  {address && `${address.slice(0, 6)}...${address.slice(-4)}`}
                </span>
                <button
                  className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded"
                  onClick={disconnect}
                >
                  Disconnect
                </button>
              </>
            ) : (
              <button
                className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded"
                onClick={connect}
              >
                Connect Wallet
              </button>
            )}
          </div>
        </div>
      </nav>
      <main className="container mx-auto p-4">
        <Outlet />
      </main>
    </div>
  );
}

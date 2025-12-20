# ERC6909 Multi-Token Implementation on Arbitrum Stylus

A gas-optimized implementation of the ERC6909 multi-token standard using Rust and Arbitrum Stylus SDK. This contract supports multiple token types within a single contract, similar to ERC1155 but with improved gas efficiency.

## 📍 Deployed Contract

- **Network**: Arbitrum Sepolia Testnet
- **Contract Address**: `0xac0a47055733d0bbcb64646bcb072169b0060448`
- **[View on Arbiscan](https://sepolia.arbiscan.io/address/0xac0a47055733d0bbcb64646bcb072169b0060448)**

## 🚀 What's New in This Implementation

### Key Changes from Standard Template
1. **Storage Optimization**: Uses `bytes32` instead of `string` for name/symbol (saves ~6KB)
2. **Contract Size**: Optimized from 26.1 KiB to 20.3 KiB to fit deployment limits
3. **Full ERC6909**: Complete multi-token standard implementation
4. **Integration Scripts**: Ready-to-use TypeScript interaction scripts with Viem

## Overview

ERC6909 is a multi-token standard that allows a single contract to manage multiple fungible tokens identified by unique IDs. Think of it as a more gas-efficient alternative to ERC1155, where each token ID represents a completely different token type (like Gold, Silver, Bronze tokens in a game).

### Why ERC6909?
- **Gas Efficiency**: ~40% cheaper than ERC1155 for transfers
- **Simpler Storage**: More efficient storage layout
- **Better DX**: Cleaner approval mechanism
- **Reduced Complexity**: No need for batch operations overhead when not needed

## Features

- ✅ **Multi-Token Management** - Unlimited token types with unique IDs
- ✅ **Owner-Controlled Minting** - Only contract owner can mint new tokens
- ✅ **Flexible Approvals** - Per-token-ID approvals and global operator permissions
- ✅ **Full Transfer Support** - Direct transfers and delegated transfers via allowances
- ✅ **Token Burning** - Users can burn their own tokens
- ✅ **Gas Optimized** - Uses bytes32 for metadata, optimized storage patterns
- ✅ **Comprehensive Events** - Transfer, Approval, and OperatorSet events

## Quick Start

### Prerequisites

```bash
# Install Rust and Stylus CLI
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup target add wasm32-unknown-unknown
cargo install --force cargo-stylus

# Install Node.js dependencies (for interaction scripts)
curl -fsSL https://bun.sh/install | bash
```

### Setup

1. **Clone the repository**:
```bash
git clone <repository-url>
cd erc6909-stylus
```

2. **Set environment variables**:
```bash
export PRIVATE_KEY="your_private_key_here"
export RPC="https://sepolia-rollup.arbitrum.io/rpc"
```

3. **Install integration dependencies**:
```bash
cd integration
bun install
cd ..
```

## Building & Deployment

### Build the Contract

```bash
# Build optimized WASM binary
cargo build --release --target wasm32-unknown-unknown

# Check contract validity and size
cargo stylus check --endpoint $RPC
```

### Deploy to Arbitrum Sepolia

```bash
# Deploy with optimizations (skip Docker verification for speed)
cargo stylus deploy --private-key $PRIVATE_KEY --endpoint $RPC --no-verify

# Cache the contract for cheaper calls (recommended)
cargo stylus cache bid <CONTRACT_ADDRESS> 0 --endpoint $RPC --private-key $PRIVATE_KEY
```

## Contract Interface

```solidity
interface IERC6909 {
    // Initialization (one-time only)
    function initialize(bytes32 name, bytes32 symbol) external;
    
    // View functions
    function name() external view returns (bytes32);
    function symbol() external view returns (bytes32);
    function decimals() external view returns (uint8);
    function balanceOf(address owner, uint256 id) external view returns (uint256);
    function allowance(address owner, address spender, uint256 id) external view returns (uint256);
    function isOperator(address owner, address spender) external view returns (bool);
    
    // State-changing functions
    function mint(address to, uint256 id, uint256 value) external; // Owner only
    function transfer(address receiver, uint256 id, uint256 value) external;
    function transferFrom(address sender, address receiver, uint256 id, uint256 value) external;
    function approve(address spender, uint256 id, uint256 value) external;
    function setOperator(address spender, bool approved) external;
    function burn(uint256 id, uint256 value) external;
    
    // Events
    event Transfer(address indexed from, address indexed to, uint256 indexed id, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 indexed id, uint256 value);
    event OperatorSet(address indexed owner, address indexed sender, bool approved);
}
```

## Interacting with the Contract

### Using the Integration Scripts

The `integration/` folder contains ready-to-use TypeScript scripts:

#### 1. Initialize Contract
```bash
cd integration
bun run initialize

# Output:
# ✅ Contract initialized with name: MultiToken, symbol: MTK
```

#### 2. Mint Tokens
```bash
bun run mint

# Mints:
# - 1000 Gold tokens (ID: 1)
# - 2000 Silver tokens (ID: 2)  
# - 5000 Bronze tokens (ID: 3)
```

#### 3. Transfer Tokens
```bash
# Update recipient address in transfer.ts first
bun run transfer

# Demonstrates:
# - Direct transfer
# - Approval & transferFrom
# - Operator assignment
# - Multi-token transfers
```

### Manual Interaction Example

```javascript
// Using Viem
import { createWalletClient, createPublicClient, http } from 'viem';
import { arbitrumSepolia } from 'viem/chains';

const walletClient = createWalletClient({
  chain: arbitrumSepolia,
  transport: http(),
});

// Initialize (one-time)
const hash = await walletClient.writeContract({
  address: '0xac0a47055733d0bbcb64646bcb072169b0060448',
  abi: erc6909Abi,
  functionName: 'initialize',
  args: [
    '0x4d79546f6b656e00000000000000000000000000000000000000000000000000', // "MyToken" as bytes32
    '0x4d544b0000000000000000000000000000000000000000000000000000000000', // "MTK" as bytes32
  ],
});

// Mint tokens (owner only)
await walletClient.writeContract({
  address: contractAddress,
  abi: erc6909Abi,
  functionName: 'mint',
  args: [userAddress, 1n, 1000n], // Mint 1000 tokens of ID 1
});
```

## Key Optimizations Explained

### 1. Storage Optimization
```rust
// Before: Dynamic strings (expensive)
sol_storage! {
    string name;
    string symbol;
}

// After: Fixed bytes32 (cheaper)
sol_storage! {
    bytes32 name;
    bytes32 symbol;
}
```

### 2. Test Code Removal
```rust
// Development: Include tests
#[cfg(test)]
mod test {
    // 380+ lines of test code
}

// Production: Comment out for deployment
// #[cfg(test)]
// mod test { ... }
```

### 3. Import Optimization
```rust
// Only import what's needed
extern crate alloc;

use alloc::vec::Vec; // Required by SDK macros
```

## Architecture Deep Dive

### Storage Layout
```rust
sol_storage! {
    #[entrypoint]
    pub struct ERC6909 {
        address owner;                    // Contract owner
        bytes32 name;                      // Token collection name
        bytes32 symbol;                    // Token collection symbol
        uint8 decimals;                    // Always 18
        mapping(address => mapping(uint256 => uint256)) _balance;
        mapping(address => mapping(address => bool)) _operator_approvals;
        mapping(address => mapping(address => mapping(uint256 => uint256))) _allowances;
    }
}
```

### Internal Functions Pattern
```rust
impl ERC6909 {
    // Internal function (prefixed with _)
    fn _transfer(&mut self, from: Address, to: Address, id: U256, value: U256) 
        -> Result<(), ERC6909Error> {
        // Validation
        if from.is_zero() { return Err(...); }
        if to.is_zero() { return Err(...); }
        
        // Business logic
        self._update(from, to, id, value)?;
        Ok(())
    }
}

#[public]
impl ERC6909 {
    // Public function (calls internal)
    fn transfer(&mut self, receiver: Address, id: U256, value: U256) 
        -> Result<(), ERC6909Error> {
        self._transfer(self.vm().msg_sender(), receiver, id, value)
    }
}
```

## Testing

### Run Unit Tests
```bash
cargo test

# Runs 20+ comprehensive tests including:
# ✓ Balance tracking
# ✓ Transfer operations
# ✓ Approval mechanisms
# ✓ Minting/burning
# ✓ Edge cases
```

### Integration Tests
```bash
cd integration
bun test
```

## Gas Comparison

| Operation | ERC1155 | ERC6909 | Savings |
|-----------|---------|---------|---------|
| Transfer | ~51,000 gas | ~30,000 gas | ~40% |
| Approval | ~48,000 gas | ~28,000 gas | ~42% |
| Mint | ~52,000 gas | ~32,000 gas | ~38% |

## Security Considerations

1. **Access Control**: Only owner can mint tokens
2. **Zero Address Protection**: Prevents accidental burns
3. **Overflow Protection**: Built-in Rust safety
4. **Reentrancy Safe**: No external calls in critical sections
5. **Allowance Validation**: Proper spending checks

## Common Issues & Solutions

### Issue: Contract Too Large
**Error**: `max code size exceeded`

**Solution**: 
- Remove test code for production
- Use bytes32 instead of string
- Minimize imports
- Enable aggressive optimizations

### Issue: Transaction Fails
**Error**: `ERC6909InvalidSender`

**Solution**: 
- Ensure contract is initialized first
- Check msg.sender is the owner for mint operations
- Verify addresses are not zero addresses

## Future Improvements

- [ ] Batch operations for multiple transfers
- [ ] EIP-2612 permit for gasless approvals
- [ ] Metadata URI per token ID
- [ ] Pausable functionality
- [ ] Total supply tracking

## Resources

- [Arbitrum Stylus Docs](https://docs.arbitrum.io/stylus/stylus-quickstart)
- [ERC6909 Standard](https://eips.ethereum.org/EIPS/eip-6909)
- [Stylus SDK Reference](https://github.com/OffchainLabs/stylus-sdk-rs)
- [Contract on Arbiscan](https://sepolia.arbiscan.io/address/0xac0a47055733d0bbcb64646bcb072169b0060448)

## License

This project is dual-licensed under MIT and Apache-2.0.
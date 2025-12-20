import { 
  mintTokens, 
  getBalance, 
  getContractInfo, 
  ERC6909_CONTRACT_ADDRESS 
} from "./erc6909";
import { walletClient } from "./chain";

async function main() {
  try {
    console.log("=".repeat(50));
    console.log("ERC6909 Token Minting Script");
    console.log("=".repeat(50));
    
    if (ERC6909_CONTRACT_ADDRESS === "0x0000000000000000000000000000000000000000") {
      console.log("❌ Please update ERC6909_CONTRACT_ADDRESS in erc6909.ts with your deployed contract address");
      process.exit(1);
    }
    
    console.log(`\n📍 Contract Address: ${ERC6909_CONTRACT_ADDRESS}`);
    console.log(`👤 Minting with wallet: ${walletClient.account.address}`);
    
    // Get current contract info
    console.log("\n📊 Current contract info:");
    const contractInfo = await getContractInfo();
    console.log(`📌 Name: ${contractInfo.name}`);
    console.log(`🏷️  Symbol: ${contractInfo.symbol}`);
    console.log(`🔢 Decimals: ${contractInfo.decimals}`);
    
    // Define different token types with IDs
    const tokens = [
      { id: 1n, name: "Gold Token", amount: 1000n },
      { id: 2n, name: "Silver Token", amount: 2000n },
      { id: 3n, name: "Bronze Token", amount: 5000n },
    ];
    
    console.log(`\n🎯 Minting multiple token types to ${walletClient.account.address}:`);
    
    // Mint different token types
    for (const token of tokens) {
      console.log(`\n💰 Minting ${token.name} (ID: ${token.id})...`);
      
      // Check balance before minting
      const balanceBefore = await getBalance(walletClient.account.address, token.id);
      console.log(`   Balance before: ${balanceBefore.toString()}`);
      
      // Mint tokens
      await mintTokens(walletClient.account.address, token.id, token.amount);
      
      // Check balance after minting
      const balanceAfter = await getBalance(walletClient.account.address, token.id);
      console.log(`   Balance after: ${balanceAfter.toString()}`);
      console.log(`   ✅ Successfully minted ${(balanceAfter - balanceBefore).toString()} tokens`);
    }
    
    // Display final balances
    console.log("\n📊 Final token balances:");
    console.log("=".repeat(50));
    for (const token of tokens) {
      const balance = await getBalance(walletClient.account.address, token.id);
      console.log(`🪙 ${token.name} (ID: ${token.id}): ${balance.toString()}`);
    }
    console.log("=".repeat(50));
    
    console.log(`\n🔗 View on Arbiscan: https://sepolia.arbiscan.io/address/${ERC6909_CONTRACT_ADDRESS}`);
    console.log(`\n💡 Each token ID represents a different token type!`);
    console.log(`   • Token ID 1: Gold Token - Premium tier`);
    console.log(`   • Token ID 2: Silver Token - Standard tier`); 
    console.log(`   • Token ID 3: Bronze Token - Basic tier`);
    
  } catch (error: any) {
    console.error("\n❌ Error:", error.message);
    
    if (error.message?.includes("InvalidSender")) {
      console.log("🔒 Only the contract owner can mint tokens");
    }
    
    process.exit(1);
  }
}

main();
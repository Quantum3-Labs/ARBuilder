import { 
  transferTokens,
  transferFrom,
  approveSpender, 
  setOperator,
  getBalance, 
  getAllowance,
  isOperator,
  ERC6909_CONTRACT_ADDRESS 
} from "./erc6909";
import { walletClient } from "./chain";

// Example recipient address (you can change this)
const RECIPIENT_ADDRESS = "0xc81441FA54C36c0d84dda24b7ad57461C7D729db" as `0x${string}`;

async function main() {
  try {
    console.log("=".repeat(60));
    console.log("ERC6909 Token Transfer & Approval Demo");
    console.log("=".repeat(60));
    
    if (ERC6909_CONTRACT_ADDRESS === "0x0000000000000000000000000000000000000000") {
      console.log("❌ Please update ERC6909_CONTRACT_ADDRESS in erc6909.ts with your deployed contract address");
      process.exit(1);
    }
    
    console.log(`\n📍 Contract Address: ${ERC6909_CONTRACT_ADDRESS}`);
    console.log(`👤 Sender: ${walletClient.account.address}`);
    console.log(`🎯 Recipient: ${RECIPIENT_ADDRESS}`);
    
    const tokenId = 1n; // Gold Token
    const transferAmount = 100n;
    const approvalAmount = 50n;
    
    // Check initial balances
    console.log("\n Initial balances:");
    const senderBalance = await getBalance(walletClient.account.address, tokenId);
    const recipientBalance = await getBalance(RECIPIENT_ADDRESS, tokenId);
    console.log(` Sender balance (Token ID ${tokenId}): ${senderBalance.toString()}`);
    console.log(` Recipient balance (Token ID ${tokenId}): ${recipientBalance.toString()}`);
    
    if (senderBalance === 0n) {
      console.log("\n  No tokens to transfer! Run 'bun run mint.ts' first to mint some tokens.");
      process.exit(1);
    }
    
    // 1. Direct transfer
    console.log(`\n DEMO 1: Direct Transfer`);
    console.log(`Transferring ${transferAmount} tokens directly to recipient...`);
    
    await transferTokens(RECIPIENT_ADDRESS, tokenId, transferAmount);
    
    // Check balances after transfer
    const senderBalanceAfterTransfer = await getBalance(walletClient.account.address, tokenId);
    const recipientBalanceAfterTransfer = await getBalance(RECIPIENT_ADDRESS, tokenId);
    console.log(`✅ Transfer complete!`);
    console.log(` Sender new balance: ${senderBalanceAfterTransfer.toString()}`);
    console.log(` Recipient new balance: ${recipientBalanceAfterTransfer.toString()}`);
    
    // 2. Approval system demo
    console.log(`\n DEMO 2: Approval System`);
    console.log(`Approving recipient to spend ${approvalAmount} tokens...`);
    
    await approveSpender(RECIPIENT_ADDRESS, tokenId, approvalAmount);
    
    // Check allowance
    const allowance = await getAllowance(walletClient.account.address, RECIPIENT_ADDRESS, tokenId);
    console.log(`✅ Allowance set! Recipient can spend: ${allowance.toString()} tokens`);
    
    // 3. Operator system demo
    console.log(`\n DEMO 3: Operator System`);
    console.log(`Setting recipient as operator (can transfer all token IDs)...`);
    
    await setOperator(RECIPIENT_ADDRESS, true);
    
    // Check operator status
    const operatorStatus = await isOperator(walletClient.account.address, RECIPIENT_ADDRESS);
    console.log(`✅ Operator status: ${operatorStatus ? 'Approved' : 'Not approved'}`);
    
    // 4. Multiple token ID demo
    console.log(`\n DEMO 4: Multiple Token Types`);
    const silverTokenId = 2n;
    const bronzeTokenId = 3n;
    
    // Check balances for different token IDs
    const silverBalance = await getBalance(walletClient.account.address, silverTokenId);
    const bronzeBalance = await getBalance(walletClient.account.address, bronzeTokenId);
    
    console.log(` Current balances for different token types:`);
    console.log(` Gold Token (ID ${tokenId}): ${senderBalanceAfterTransfer.toString()}`);
    console.log(` Silver Token (ID ${silverTokenId}): ${silverBalance.toString()}`);
    console.log(` Bronze Token (ID ${bronzeTokenId}): ${bronzeBalance.toString()}`);
    
    if (silverBalance > 0) {
      console.log(`\n Transferring some Silver tokens...`);
      await transferTokens(RECIPIENT_ADDRESS, silverTokenId, 200n);
      
      const recipientSilverBalance = await getBalance(RECIPIENT_ADDRESS, silverTokenId);
      console.log(`✅ Recipient Silver token balance: ${recipientSilverBalance.toString()}`);
    }
    
    // Final summary
    console.log(`\n FINAL SUMMARY`);
    console.log("=".repeat(60));
    console.log(` All operations completed successfully!`);
    console.log(` Contract: ${ERC6909_CONTRACT_ADDRESS}`);
    console.log(` Your address: ${walletClient.account.address}`);
    console.log(` Recipient: ${RECIPIENT_ADDRESS}`);
    console.log(` View on Arbiscan: https://sepolia.arbiscan.io/address/${ERC6909_CONTRACT_ADDRESS}`);
    
  } catch (error: any) {
    console.error("\n❌ Error:", error.message);
    
    if (error.message?.includes("InsufficientBalance")) {
      console.log(" Insufficient token balance for the transfer");
    } else if (error.message?.includes("InvalidReceiver")) {
      console.log(" Invalid receiver address");
    }
    
    process.exit(1);
  }
}

main();
import { getContract, encodeAbiParameters, parseAbiParameters, hexToString, stringToHex, pad } from "viem";
import { walletClient } from "./chain";
import { erc6909Abi } from "./abis";

// Your deployed contract address (will be set after deployment)
export const ERC6909_CONTRACT_ADDRESS = "0xac0a47055733d0bbcb64646bcb072169b0060448"; // Deployed contract address

// Create contract instance
export const erc6909Contract = getContract({
  address: ERC6909_CONTRACT_ADDRESS as `0x${string}`,
  abi: erc6909Abi,
  client: walletClient,
});

// Helper function to convert string to bytes32
function stringToBytes32(str: string): `0x${string}` {
  const hex = stringToHex(str);
  return pad(hex, { size: 32 }) as `0x${string}`;
}

// Helper function to convert bytes32 to string
function bytes32ToString(bytes32: `0x${string}`): string {
  // Remove trailing zeros and convert to string
  const hex = bytes32.replace(/0+$/, '');
  if (hex === '0x') return '';
  return hexToString(hex, { size: 32 });
}

// Helper functions for interacting with the contract
export async function initializeContract(name: string, symbol: string) {
  try {
    console.log(`\n Initializing ERC6909 contract with name: ${name}, symbol: ${symbol}`);
    
    // Convert strings to bytes32
    const nameBytes32 = stringToBytes32(name);
    const symbolBytes32 = stringToBytes32(symbol);
    
    const hash = await erc6909Contract.write.initialize([nameBytes32, symbolBytes32]);
    console.log(` Transaction hash: ${hash}`);
    
    console.log(" Waiting for transaction confirmation...");
    const receipt = await walletClient.waitForTransactionReceipt({ hash });
    console.log(`✅ Transaction confirmed in block: ${receipt.blockNumber}`);
    
    return receipt;
  } catch (error: any) {
    if (error.message?.includes("InvalidSender")) {
      throw new Error("Contract already initialized");
    }
    throw error;
  }
}

export async function getContractInfo() {
  const [nameBytes32, symbolBytes32, decimals] = await Promise.all([
    erc6909Contract.read.name(),
    erc6909Contract.read.symbol(),
    erc6909Contract.read.decimals(),
  ]);
  
  // Convert bytes32 to strings
  const name = bytes32ToString(nameBytes32 as `0x${string}`);
  const symbol = bytes32ToString(symbolBytes32 as `0x${string}`);
  
  return {
    name,
    symbol,
    decimals,
  };
}

export async function getBalance(address: `0x${string}`, tokenId: bigint) {
  return erc6909Contract.read.balanceOf([address, tokenId]);
}

export async function getAllowance(owner: `0x${string}`, spender: `0x${string}`, tokenId: bigint) {
  return erc6909Contract.read.allowance([owner, spender, tokenId]);
}

export async function isOperator(owner: `0x${string}`, operator: `0x${string}`) {
  return erc6909Contract.read.isOperator([owner, operator]);
}

export async function mintTokens(to: `0x${string}`, tokenId: bigint, amount: bigint) {
  console.log(`\n Minting ${amount.toString()} tokens of ID ${tokenId.toString()} to ${to}...`);
  
  const hash = await erc6909Contract.write.mint([to, tokenId, amount]);
  console.log(` Transaction hash: ${hash}`);
  
  const receipt = await walletClient.waitForTransactionReceipt({ hash });
  console.log(`✅ Tokens minted! Block: ${receipt.blockNumber}`);
  
  return receipt;
}

export async function transferTokens(to: `0x${string}`, tokenId: bigint, amount: bigint) {
  console.log(`\n Transferring ${amount.toString()} tokens of ID ${tokenId.toString()} to ${to}...`);
  
  const hash = await erc6909Contract.write.transfer([to, tokenId, amount]);
  console.log(` Transaction hash: ${hash}`);
  
  const receipt = await walletClient.waitForTransactionReceipt({ hash });
  console.log(`✅ Transfer successful! Block: ${receipt.blockNumber}`);
  
  return receipt;
}

export async function transferFrom(
  from: `0x${string}`, 
  to: `0x${string}`, 
  tokenId: bigint, 
  amount: bigint
) {
  console.log(`\n Transferring ${amount.toString()} tokens of ID ${tokenId.toString()} from ${from} to ${to}...`);
  
  const hash = await erc6909Contract.write.transferFrom([from, to, tokenId, amount]);
  console.log(` Transaction hash: ${hash}`);
  
  const receipt = await walletClient.waitForTransactionReceipt({ hash });
  console.log(`✅ Transfer from successful! Block: ${receipt.blockNumber}`);
  
  return receipt;
}

export async function approveSpender(spender: `0x${string}`, tokenId: bigint, amount: bigint) {
  console.log(`\n Approving ${spender} to spend ${amount.toString()} tokens of ID ${tokenId.toString()}...`);
  
  const hash = await erc6909Contract.write.approve([spender, tokenId, amount]);
  console.log(` Transaction hash: ${hash}`);
  
  const receipt = await walletClient.waitForTransactionReceipt({ hash });
  console.log(`✅ Approval successful! Block: ${receipt.blockNumber}`);
  
  return receipt;
}

export async function setOperator(operator: `0x${string}`, approved: boolean) {
  console.log(`\n ${approved ? 'Setting' : 'Removing'} ${operator} as operator...`);
  
  const hash = await erc6909Contract.write.setOperator([operator, approved]);
  console.log(` Transaction hash: ${hash}`);
  
  const receipt = await walletClient.waitForTransactionReceipt({ hash });
  console.log(`✅ Operator status updated! Block: ${receipt.blockNumber}`);
  
  return receipt;
}

export async function burnTokens(tokenId: bigint, amount: bigint) {
  console.log(`\n Burning ${amount.toString()} tokens of ID ${tokenId.toString()}...`);
  
  const hash = await erc6909Contract.write.burn([tokenId, amount]);
  console.log(` Transaction hash: ${hash}`);
  
  const receipt = await walletClient.waitForTransactionReceipt({ hash });
  console.log(`✅ Tokens burned! Block: ${receipt.blockNumber}`);
  
  return receipt;
}
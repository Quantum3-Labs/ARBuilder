import {
  initializeContract,
  getContractInfo,
  ERC6909_CONTRACT_ADDRESS,
} from "./erc6909";
import { walletClient } from "./chain";

async function main() {
  try {
    console.log("=".repeat(60));
    console.log("ERC6909 Multi-Token Contract Initialization Script");
    console.log("=".repeat(60));

    if (
      ERC6909_CONTRACT_ADDRESS === "0x0000000000000000000000000000000000000000"
    ) {
      console.log(
        "❌ Please update ERC6909_CONTRACT_ADDRESS in erc6909.ts with your deployed contract address"
      );
      process.exit(1);
    }

    console.log(`\n Contract Address: ${ERC6909_CONTRACT_ADDRESS}`);
    console.log(` Initializing with wallet: ${walletClient.account.address}`);

    // Initialize the contract with multi-token name and symbol
    await initializeContract("MultiToken", "MTK");

    // Verify initialization by reading contract info
    console.log("\n Verifying initialization...");
    const contractInfo = await getContractInfo();

    console.log("\n ERC6909 Multi-Token contract successfully initialized!");
    console.log("=".repeat(60));
    console.log(` Contract Name: ${contractInfo.name}`);
    console.log(`  Contract Symbol: ${contractInfo.symbol}`);
    console.log(` Decimals: ${contractInfo.decimals}`);
    console.log(` Owner: ${walletClient.account.address}`);
    console.log("=".repeat(60));

    console.log(`\n About ERC6909:`);
    console.log(
      `   • Multi-token standard (like ERC1155 but more gas efficient)`
    );
    console.log(`   • Each token has a unique ID (uint256)`);
    console.log(`   • Independent balances and allowances per token ID`);
    console.log(`   • Global operator approvals across all token IDs`);
    console.log(`   • Owner can mint any token ID`);

    console.log(
      `\n🔗 View on Arbiscan: https://sepolia.arbiscan.io/address/${ERC6909_CONTRACT_ADDRESS}`
    );
    console.log(`\n Next steps:`);
    console.log(`   1. Run "bun run mint.ts" to mint some tokens`);
    console.log(`   2. Run "bun run transfer.ts" to transfer tokens`);
  } catch (error: any) {
    console.error("\n Error:", error.message);

    if (error.message === "Contract already initialized") {
      console.log(
        "\n Contract is already initialized. Reading current info..."
      );
      const contractInfo = await getContractInfo();
      console.log(` Contract Name: ${contractInfo.name}`);
      console.log(`  Contract Symbol: ${contractInfo.symbol}`);
      console.log(` Decimals: ${contractInfo.decimals}`);
    }

    process.exit(1);
  }
}

main();

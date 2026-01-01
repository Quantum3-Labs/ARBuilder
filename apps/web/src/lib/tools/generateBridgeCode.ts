/**
 * Generate Arbitrum bridging code (M2 tool)
 */

// Bridge type definitions
type BridgeType =
  | "eth_deposit"
  | "eth_deposit_to"
  | "eth_withdraw"
  | "erc20_deposit"
  | "erc20_withdraw"
  | "eth_l1_l3"
  | "erc20_l1_l3";

interface GenerateBridgeCodeArgs {
  bridgeType: BridgeType;
  amount?: string;
  tokenAddress?: string;
  destinationAddress?: string;
}

interface GenerateBridgeCodeResult {
  code: string;
  bridgeType: BridgeType;
  dependencies: Record<string, string>;
  envVars: string[];
  notes: string[];
}

// Code templates
const TEMPLATES: Record<BridgeType, string> = {
  eth_deposit: `import { providers, Wallet, utils } from 'ethers';
import { EthBridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function depositEth(amount: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l1Provider);

  const l2Network = await getArbitrumNetwork(l2Provider);
  const ethBridger = new EthBridger(l2Network);

  const depositTx = await ethBridger.deposit({
    amount: utils.parseEther(amount),
    parentSigner: wallet,
  });

  console.log('Deposit tx hash:', depositTx.hash);
  const receipt = await depositTx.wait();
  console.log('Deposit confirmed:', receipt.transactionHash);

  return receipt;
}

depositEth('{{amount}}');`,

  eth_deposit_to: `import { providers, Wallet, utils } from 'ethers';
import { EthBridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function depositEthTo(amount: string, destinationAddress: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l1Provider);

  const l2Network = await getArbitrumNetwork(l2Provider);
  const ethBridger = new EthBridger(l2Network);

  const depositTx = await ethBridger.depositTo({
    amount: utils.parseEther(amount),
    parentSigner: wallet,
    childProvider: l2Provider,
    destinationAddress,
  });

  console.log('Deposit tx hash:', depositTx.hash);
  const receipt = await depositTx.wait();
  console.log('Deposit confirmed:', receipt.transactionHash);

  return receipt;
}

depositEthTo('{{amount}}', '{{destinationAddress}}');`,

  eth_withdraw: `import { providers, Wallet, utils } from 'ethers';
import { EthBridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function withdrawEth(amount: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l2Provider);

  const l2Network = await getArbitrumNetwork(l2Provider);
  const ethBridger = new EthBridger(l2Network);

  const withdrawTx = await ethBridger.withdraw({
    amount: utils.parseEther(amount),
    childSigner: wallet,
    destinationAddress: wallet.address,
  });

  console.log('Withdrawal initiated:', withdrawTx.hash);
  const receipt = await withdrawTx.wait();
  console.log('L2 tx confirmed. Wait ~7 days for challenge period before claiming on L1.');

  return receipt;
}

withdrawEth('{{amount}}');`,

  erc20_deposit: `import { providers, Wallet, BigNumber } from 'ethers';
import { Erc20Bridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function depositErc20(tokenAddress: string, amount: BigNumber) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l1Provider);

  const l2Network = await getArbitrumNetwork(l2Provider);
  const erc20Bridger = new Erc20Bridger(l2Network);

  // Approve token for gateway
  const approveTx = await erc20Bridger.approveToken({
    erc20ParentAddress: tokenAddress,
    parentSigner: wallet,
  });
  await approveTx.wait();
  console.log('Token approved');

  // Deposit
  const depositTx = await erc20Bridger.deposit({
    amount,
    erc20ParentAddress: tokenAddress,
    parentSigner: wallet,
    childProvider: l2Provider,
  });

  console.log('Deposit tx hash:', depositTx.hash);
  const receipt = await depositTx.wait();
  console.log('Deposit confirmed:', receipt.transactionHash);

  return receipt;
}

depositErc20('{{tokenAddress}}', BigNumber.from('{{amount}}'));`,

  erc20_withdraw: `import { providers, Wallet, BigNumber } from 'ethers';
import { Erc20Bridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function withdrawErc20(tokenAddress: string, amount: BigNumber) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l2Provider);

  const l2Network = await getArbitrumNetwork(l2Provider);
  const erc20Bridger = new Erc20Bridger(l2Network);

  // Get L2 token address
  const l2TokenAddress = await erc20Bridger.getChildErc20Address(
    tokenAddress,
    l1Provider
  );

  const withdrawTx = await erc20Bridger.withdraw({
    amount,
    erc20ParentAddress: tokenAddress,
    childSigner: wallet,
    destinationAddress: wallet.address,
  });

  console.log('Withdrawal initiated:', withdrawTx.hash);
  const receipt = await withdrawTx.wait();
  console.log('L2 tx confirmed. Wait ~7 days before claiming on L1.');

  return receipt;
}

withdrawErc20('{{tokenAddress}}', BigNumber.from('{{amount}}'));`,

  eth_l1_l3: `import { providers, Wallet, utils } from 'ethers';
import { EthL1L3Bridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function bridgeEthL1ToL3(amount: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const l3Provider = new providers.JsonRpcProvider(process.env.L3_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l1Provider);

  const l3Network = await getArbitrumNetwork(l3Provider);
  const bridger = new EthL1L3Bridger(l3Network);

  const depositTx = await bridger.deposit({
    amount: utils.parseEther(amount),
    parentSigner: wallet,
    childProvider: l2Provider,
    childOfChildProvider: l3Provider,
  });

  console.log('L1->L3 deposit tx:', depositTx.hash);
  const receipt = await depositTx.wait();

  return receipt;
}

bridgeEthL1ToL3('{{amount}}');`,

  erc20_l1_l3: `import { providers, Wallet, BigNumber } from 'ethers';
import { Erc20L1L3Bridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function bridgeErc20L1ToL3(tokenAddress: string, amount: BigNumber) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const l3Provider = new providers.JsonRpcProvider(process.env.L3_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l1Provider);

  const l3Network = await getArbitrumNetwork(l3Provider);
  const bridger = new Erc20L1L3Bridger(l3Network);

  // Approve token
  const approveTx = await bridger.approveToken({
    erc20ParentAddress: tokenAddress,
    parentSigner: wallet,
  });
  await approveTx.wait();

  const depositTx = await bridger.deposit({
    amount,
    erc20ParentAddress: tokenAddress,
    parentSigner: wallet,
    childProvider: l2Provider,
    childOfChildProvider: l3Provider,
  });

  console.log('L1->L3 deposit tx:', depositTx.hash);
  const receipt = await depositTx.wait();

  return receipt;
}

bridgeErc20L1ToL3('{{tokenAddress}}', BigNumber.from('{{amount}}'));`,
};

function getNotes(bridgeType: BridgeType): string[] {
  const notes: string[] = [];

  if (bridgeType.includes("deposit") && !bridgeType.includes("l3")) {
    notes.push("L1 -> L2 deposits take ~10-15 minutes to confirm on L2");
    notes.push("Funds are automatically credited to your L2 address");
  }

  if (bridgeType.includes("withdraw")) {
    notes.push("Withdrawals require a ~7 day challenge period");
    notes.push("After the challenge period, call the claim function on L1");
  }

  if (bridgeType.includes("erc20")) {
    notes.push("Token must be approved before bridging");
    notes.push("First-time bridging may require gateway registration");
  }

  if (bridgeType.includes("l3")) {
    notes.push("L1 -> L3 bridging uses double retryable tickets (L1->L2->L3)");
    notes.push("May require gas token approval if L3 uses custom gas token");
  }

  return notes;
}

function getEnvVars(bridgeType: BridgeType): string[] {
  const vars = ["L1_RPC_URL", "L2_RPC_URL", "PRIVATE_KEY"];
  if (bridgeType.includes("l3")) {
    vars.push("L3_RPC_URL");
  }
  return vars;
}

export function generateBridgeCode(
  args: GenerateBridgeCodeArgs
): GenerateBridgeCodeResult {
  const { bridgeType, amount = "0.1", tokenAddress, destinationAddress } = args;

  let code = TEMPLATES[bridgeType];

  // Replace placeholders
  code = code.replace(/\{\{amount\}\}/g, amount);
  if (tokenAddress) {
    code = code.replace(/\{\{tokenAddress\}\}/g, tokenAddress);
  }
  if (destinationAddress) {
    code = code.replace(/\{\{destinationAddress\}\}/g, destinationAddress);
  }

  return {
    code,
    bridgeType,
    dependencies: {
      ethers: "^5.7.0",
      "@arbitrum/sdk": "^4.0.0",
    },
    envVars: getEnvVars(bridgeType),
    notes: getNotes(bridgeType),
  };
}

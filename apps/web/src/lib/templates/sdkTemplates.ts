/**
 * Curated working templates for Arbitrum SDK bridging and messaging.
 * These templates are verified to work with @arbitrum/sdk v4.0.0+
 *
 * Categories:
 * - Bridging: ETH and ERC20 deposits/withdrawals (L1<->L2, L1->L3)
 * - Messaging: Cross-chain message passing via retryables and ArbSys
 */

export interface SdkTemplate {
  name: string;
  description: string;
  category: "bridging" | "messaging";
  subcategory: string;
  sdkVersion: string;
  code: string;
  dependencies: Record<string, string>;
  envVars: string[];
  notes: string[];
}

// ============================================================================
// BRIDGING TEMPLATES
// ============================================================================

export const ETH_DEPOSIT_TEMPLATE: SdkTemplate = {
  name: "ETH Deposit (L1 → L2)",
  description: "Deposit ETH from L1 (Ethereum) to L2 (Arbitrum)",
  category: "bridging",
  subcategory: "eth",
  sdkVersion: "4.0.0",
  dependencies: {
    ethers: "^5.7.0",
    "@arbitrum/sdk": "^4.0.0",
  },
  envVars: ["L1_RPC_URL", "L2_RPC_URL", "PRIVATE_KEY"],
  notes: [
    "L1 → L2 deposits take ~10-15 minutes to confirm on L2",
    "Funds are automatically credited to your L2 address",
    "No approval needed for ETH",
  ],
  code: `import { providers, Wallet, utils } from 'ethers';
import { EthBridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function depositEth(amount: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l1Provider);

  const l2Network = await getArbitrumNetwork(l2Provider);
  const ethBridger = new EthBridger(l2Network);

  console.log('Depositing', amount, 'ETH to L2...');

  const depositTx = await ethBridger.deposit({
    amount: utils.parseEther(amount),
    parentSigner: wallet,
  });

  console.log('Deposit tx hash:', depositTx.hash);
  const receipt = await depositTx.wait();
  console.log('Deposit confirmed:', receipt.transactionHash);
  console.log('Funds will arrive on L2 in ~10-15 minutes');

  return receipt;
}

// Usage
depositEth('0.1');`,
};

export const ETH_WITHDRAW_TEMPLATE: SdkTemplate = {
  name: "ETH Withdraw (L2 → L1)",
  description: "Withdraw ETH from L2 (Arbitrum) back to L1 (Ethereum)",
  category: "bridging",
  subcategory: "eth",
  sdkVersion: "4.0.0",
  dependencies: {
    ethers: "^5.7.0",
    "@arbitrum/sdk": "^4.0.0",
  },
  envVars: ["L1_RPC_URL", "L2_RPC_URL", "PRIVATE_KEY"],
  notes: [
    "Withdrawals require a ~7 day challenge period",
    "After the challenge period, call the claim function on L1",
    "Keep track of the L2 tx hash to claim later",
  ],
  code: `import { providers, Wallet, utils } from 'ethers';
import { EthBridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function withdrawEth(amount: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l2Provider);

  const l2Network = await getArbitrumNetwork(l2Provider);
  const ethBridger = new EthBridger(l2Network);

  console.log('Initiating withdrawal of', amount, 'ETH...');

  const withdrawTx = await ethBridger.withdraw({
    amount: utils.parseEther(amount),
    childSigner: wallet,
    destinationAddress: wallet.address,
    from: wallet.address,
  });

  console.log('Withdrawal initiated:', withdrawTx.hash);
  const receipt = await withdrawTx.wait();
  console.log('L2 tx confirmed:', receipt.transactionHash);
  console.log('\\n⚠️  Wait ~7 days for challenge period before claiming on L1');
  console.log('Save this tx hash:', receipt.transactionHash);

  return receipt;
}

// Usage
withdrawEth('0.1');`,
};

export const ERC20_DEPOSIT_TEMPLATE: SdkTemplate = {
  name: "ERC20 Deposit (L1 → L2)",
  description: "Deposit ERC20 tokens from L1 to L2 with automatic gateway approval",
  category: "bridging",
  subcategory: "erc20",
  sdkVersion: "4.0.0",
  dependencies: {
    ethers: "^5.7.0",
    "@arbitrum/sdk": "^4.0.0",
  },
  envVars: ["L1_RPC_URL", "L2_RPC_URL", "PRIVATE_KEY"],
  notes: [
    "Token must be approved before bridging",
    "First-time bridging may require gateway registration",
    "L1 → L2 deposits take ~10-15 minutes",
  ],
  code: `import { providers, Wallet, BigNumber } from 'ethers';
import { Erc20Bridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function depositErc20(tokenAddress: string, amount: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l1Provider);

  const l2Network = await getArbitrumNetwork(l2Provider);
  const erc20Bridger = new Erc20Bridger(l2Network);

  // Step 1: Approve token for gateway
  console.log('Approving token for gateway...');
  const approveTx = await erc20Bridger.approveToken({
    erc20ParentAddress: tokenAddress,
    parentSigner: wallet,
  });
  await approveTx.wait();
  console.log('Token approved');

  // Step 2: Deposit tokens
  console.log('Depositing tokens...');
  const depositTx = await erc20Bridger.deposit({
    amount: BigNumber.from(amount),
    erc20ParentAddress: tokenAddress,
    parentSigner: wallet,
    childProvider: l2Provider,
  });

  console.log('Deposit tx hash:', depositTx.hash);
  const receipt = await depositTx.wait();
  console.log('Deposit confirmed:', receipt.transactionHash);
  console.log('Tokens will arrive on L2 in ~10-15 minutes');

  return receipt;
}

// Usage: depositErc20('0xTokenAddress', '1000000000000000000') // 1 token with 18 decimals
depositErc20('0x...', '1000000000000000000');`,
};

export const ERC20_WITHDRAW_TEMPLATE: SdkTemplate = {
  name: "ERC20 Withdraw (L2 → L1)",
  description: "Withdraw ERC20 tokens from L2 back to L1",
  category: "bridging",
  subcategory: "erc20",
  sdkVersion: "4.0.0",
  dependencies: {
    ethers: "^5.7.0",
    "@arbitrum/sdk": "^4.0.0",
  },
  envVars: ["L1_RPC_URL", "L2_RPC_URL", "PRIVATE_KEY"],
  notes: [
    "Withdrawals require a ~7 day challenge period",
    "Use the L1 token address (not L2) when calling withdraw",
    "Claim on L1 after challenge period ends",
  ],
  code: `import { providers, Wallet, BigNumber } from 'ethers';
import { Erc20Bridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function withdrawErc20(l1TokenAddress: string, amount: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l2Provider);

  const l2Network = await getArbitrumNetwork(l2Provider);
  const erc20Bridger = new Erc20Bridger(l2Network);

  console.log('Initiating token withdrawal...');

  const withdrawTx = await erc20Bridger.withdraw({
    amount: BigNumber.from(amount),
    erc20ParentAddress: l1TokenAddress,
    childSigner: wallet,
    destinationAddress: wallet.address,
  });

  console.log('Withdrawal initiated:', withdrawTx.hash);
  const receipt = await withdrawTx.wait();
  console.log('L2 tx confirmed:', receipt.transactionHash);
  console.log('\\n⚠️  Wait ~7 days for challenge period before claiming on L1');

  return receipt;
}

// Usage
withdrawErc20('0x...L1TokenAddress', '1000000000000000000');`,
};

export const ETH_L1_L3_TEMPLATE: SdkTemplate = {
  name: "ETH Bridge (L1 → L3)",
  description: "Bridge ETH directly from L1 to an Orbit L3 chain",
  category: "bridging",
  subcategory: "l3",
  sdkVersion: "4.0.0",
  dependencies: {
    ethers: "^5.7.0",
    "@arbitrum/sdk": "^4.0.0",
  },
  envVars: ["L1_RPC_URL", "L2_RPC_URL", "L3_RPC_URL", "PRIVATE_KEY"],
  notes: [
    "L1 → L3 bridging uses double retryable tickets (L1→L2→L3)",
    "May require gas token approval if L3 uses custom gas token",
    "Takes longer than L1→L2 as it goes through both hops",
  ],
  code: `import { providers, Wallet, utils } from 'ethers';
import { EthL1L3Bridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function bridgeEthL1ToL3(amount: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const l3Provider = new providers.JsonRpcProvider(process.env.L3_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l1Provider);

  const l3Network = await getArbitrumNetwork(l3Provider);
  const bridger = new EthL1L3Bridger(l3Network);

  console.log('Bridging', amount, 'ETH from L1 to L3...');

  const depositTx = await bridger.deposit({
    amount: utils.parseEther(amount),
    parentSigner: wallet,
    childProvider: l2Provider,
    childOfChildProvider: l3Provider,
  });

  console.log('L1 tx hash:', depositTx.hash);
  const receipt = await depositTx.wait();
  console.log('L1 tx confirmed:', receipt.transactionHash);
  console.log('Funds will arrive on L3 after L1→L2 and L2→L3 confirmations');

  return receipt;
}

// Usage
bridgeEthL1ToL3('0.1');`,
};

// ============================================================================
// MESSAGING TEMPLATES
// ============================================================================

export const L1_TO_L2_MESSAGE_TEMPLATE: SdkTemplate = {
  name: "L1 → L2 Message (Retryable Ticket)",
  description: "Send a cross-chain message from L1 to L2 using retryable tickets",
  category: "messaging",
  subcategory: "l1-to-l2",
  sdkVersion: "4.0.0",
  dependencies: {
    ethers: "^5.7.0",
    "@arbitrum/sdk": "^4.0.0",
  },
  envVars: ["L1_RPC_URL", "L2_RPC_URL", "PRIVATE_KEY"],
  notes: [
    "L1 → L2 messages use retryable tickets",
    "Gas estimation is automatic via NodeInterface",
    "Messages typically execute within 10-15 minutes",
    "If auto-redeem fails, tickets can be manually redeemed for 7 days",
  ],
  code: `import { providers, Wallet, utils, BigNumber, Contract } from 'ethers';
import {
  getArbitrumNetwork,
  ParentTransactionReceipt,
  ParentToChildMessageStatus,
} from '@arbitrum/sdk';

// Inbox ABI for createRetryableTicket
const INBOX_ABI = [
  'function createRetryableTicket(address to, uint256 l2CallValue, uint256 maxSubmissionCost, address excessFeeRefundAddress, address callValueRefundAddress, uint256 gasLimit, uint256 maxFeePerGas, bytes calldata data) external payable returns (uint256)',
  'function calculateRetryableSubmissionFee(uint256 dataLength, uint256 baseFee) view returns (uint256)',
];

// NodeInterface for gas estimation
const NODE_INTERFACE_ABI = [
  'function estimateRetryableTicket(address sender, uint256 deposit, address to, uint256 l2CallValue, address excessFeeRefundAddress, address callValueRefundAddress, bytes calldata data) external returns (uint256 gasLimit, uint256 gasPrice, uint256 submissionCost)',
];
const NODE_INTERFACE_ADDRESS = '0x00000000000000000000000000000000000000C8';

/**
 * Send a message from L1 to L2 using a retryable ticket.
 * The message will execute a function call on L2.
 */
async function sendL1ToL2Message(
  l2ContractAddress: string,
  calldata: string,
  l2CallValue: BigNumber = BigNumber.from(0)
) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const l1Wallet = new Wallet(process.env.PRIVATE_KEY!, l1Provider);

  const l2Network = await getArbitrumNetwork(l2Provider);

  // Estimate gas using NodeInterface
  const nodeInterface = new Contract(NODE_INTERFACE_ADDRESS, NODE_INTERFACE_ABI, l2Provider);
  const estimates = await nodeInterface.callStatic.estimateRetryableTicket(
    l1Wallet.address,
    utils.parseEther('1'),
    l2ContractAddress,
    l2CallValue,
    l1Wallet.address,
    l1Wallet.address,
    calldata
  );

  const gasLimit = estimates.gasLimit;
  const maxFeePerGas = await l2Provider.getGasPrice();

  // Calculate submission cost
  const inbox = new Contract(l2Network.ethBridge.inbox, INBOX_ABI, l1Wallet);
  const l1BaseFee = await l1Provider.getBlock('latest').then(b => b.baseFeePerGas || BigNumber.from(0));
  const maxSubmissionCost = await inbox.calculateRetryableSubmissionFee(
    calldata.length,
    l1BaseFee
  );

  // Total deposit
  const deposit = maxSubmissionCost.add(gasLimit.mul(maxFeePerGas)).add(l2CallValue);
  console.log('Total ETH required:', utils.formatEther(deposit));

  const tx = await inbox.createRetryableTicket(
    l2ContractAddress,
    l2CallValue,
    maxSubmissionCost,
    l1Wallet.address,
    l1Wallet.address,
    gasLimit,
    maxFeePerGas,
    calldata,
    { value: deposit }
  );

  console.log('L1 tx hash:', tx.hash);
  const receipt = await tx.wait();

  // Get message status
  const parentReceipt = new ParentTransactionReceipt(receipt);
  const messages = await parentReceipt.getParentToChildMessages(l2Provider);

  if (messages.length > 0) {
    const status = await messages[0].waitForStatus();
    console.log('Message status:', ParentToChildMessageStatus[status.status]);
  }

  return receipt;
}

// Example: Call setValue(42) on an L2 contract
// const iface = new utils.Interface(['function setValue(uint256 value)']);
// const calldata = iface.encodeFunctionData('setValue', [42]);
// sendL1ToL2Message('0x...L2Contract', calldata);`,
};

export const L2_TO_L1_MESSAGE_TEMPLATE: SdkTemplate = {
  name: "L2 → L1 Message (ArbSys)",
  description: "Send a cross-chain message from L2 to L1 using ArbSys precompile",
  category: "messaging",
  subcategory: "l2-to-l1",
  sdkVersion: "4.0.0",
  dependencies: {
    ethers: "^5.7.0",
    "@arbitrum/sdk": "^4.0.0",
  },
  envVars: ["L2_RPC_URL", "PRIVATE_KEY"],
  notes: [
    "L2 → L1 messages go through ArbSys precompile",
    "Messages require ~7 day challenge period before claiming",
    "Save the L2 tx hash to claim on L1 later",
  ],
  code: `import { providers, Wallet, utils, Contract } from 'ethers';

// ArbSys precompile address (same on all Arbitrum chains)
const ARB_SYS_ADDRESS = '0x0000000000000000000000000000000000000064';

const ARB_SYS_ABI = [
  'function sendTxToL1(address destination, bytes calldata data) external payable returns (uint256)',
  'event L2ToL1Tx(address caller, address indexed destination, uint256 indexed hash, uint256 indexed position, uint256 arbBlockNum, uint256 ethBlockNum, uint256 timestamp, uint256 callvalue, bytes data)',
];

/**
 * Send a message from L2 to L1 using ArbSys.
 * The message can be executed on L1 after the challenge period (~7 days).
 */
async function sendL2ToL1Message(
  l1DestinationAddress: string,
  calldata: string,
  value: string = '0'
) {
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const l2Wallet = new Wallet(process.env.PRIVATE_KEY!, l2Provider);

  const arbSys = new Contract(ARB_SYS_ADDRESS, ARB_SYS_ABI, l2Wallet);

  console.log('Sending L2 → L1 message...');

  const tx = await arbSys.sendTxToL1(
    l1DestinationAddress,
    calldata,
    { value: utils.parseEther(value) }
  );

  console.log('L2 tx hash:', tx.hash);
  const receipt = await tx.wait();
  console.log('L2 tx confirmed:', receipt.transactionHash);

  // Parse the L2ToL1Tx event
  const event = receipt.events?.find((e: any) => e.event === 'L2ToL1Tx');
  if (event) {
    console.log('Message position:', event.args.position.toString());
  }

  console.log('\\n⚠️  Message will be executable on L1 after ~7 day challenge period');
  console.log('Save this tx hash to claim later:', receipt.transactionHash);

  return receipt;
}

// Example: Call receiveMessage on L1 contract
// const iface = new utils.Interface(['function receiveMessage(bytes data)']);
// const calldata = iface.encodeFunctionData('receiveMessage', ['0x1234']);
// sendL2ToL1Message('0x...L1Contract', calldata);`,
};

export const L2_TO_L1_CLAIM_TEMPLATE: SdkTemplate = {
  name: "Claim L2 → L1 Message",
  description: "Execute/claim an L2 → L1 message on L1 after the challenge period",
  category: "messaging",
  subcategory: "l2-to-l1",
  sdkVersion: "4.0.0",
  dependencies: {
    ethers: "^5.7.0",
    "@arbitrum/sdk": "^4.0.0",
  },
  envVars: ["L1_RPC_URL", "L2_RPC_URL", "PRIVATE_KEY"],
  notes: [
    "Can only claim after challenge period ends (~7 days)",
    "Check status first to verify message is CONFIRMED",
    "Anyone can execute the message (not just original sender)",
  ],
  code: `import { providers, Wallet } from 'ethers';
import {
  ChildTransactionReceipt,
  ChildToParentMessageStatus,
} from '@arbitrum/sdk';

/**
 * Claim an L2 → L1 message on L1 after the challenge period.
 */
async function claimL2ToL1Message(l2TxHash: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const l1Wallet = new Wallet(process.env.PRIVATE_KEY!, l1Provider);

  // Get the L2 transaction receipt
  const l2Receipt = await l2Provider.getTransactionReceipt(l2TxHash);
  if (!l2Receipt) {
    throw new Error('L2 transaction not found');
  }

  // Get the L2 → L1 messages from the receipt
  const childReceipt = new ChildTransactionReceipt(l2Receipt);
  const messages = await childReceipt.getChildToParentMessages(l1Wallet);

  if (messages.length === 0) {
    throw new Error('No L2 → L1 messages found in transaction');
  }

  console.log(\`Found \${messages.length} message(s)\`);

  for (const message of messages) {
    const status = await message.status(l2Provider);
    console.log('Message status:', ChildToParentMessageStatus[status]);

    if (status === ChildToParentMessageStatus.CONFIRMED) {
      console.log('Executing message on L1...');
      const executeTx = await message.execute(l2Provider);
      const executeReceipt = await executeTx.wait();
      console.log('L1 execution tx:', executeReceipt.transactionHash);
    } else if (status === ChildToParentMessageStatus.EXECUTED) {
      console.log('Message already executed');
    } else if (status === ChildToParentMessageStatus.UNCONFIRMED) {
      console.log('Message not yet confirmed. Wait for challenge period (~7 days)');
    }
  }
}

// Usage: claimL2ToL1Message('0x...l2TxHash');`,
};

export const MESSAGE_STATUS_TEMPLATE: SdkTemplate = {
  name: "Check Message Status",
  description: "Check the status of cross-chain messages (L1→L2 and L2→L1)",
  category: "messaging",
  subcategory: "status",
  sdkVersion: "4.0.0",
  dependencies: {
    ethers: "^5.7.0",
    "@arbitrum/sdk": "^4.0.0",
  },
  envVars: ["L1_RPC_URL", "L2_RPC_URL"],
  notes: [
    "ParentToChildMessageStatus.REDEEMED = successful L1→L2",
    "ChildToParentMessageStatus.CONFIRMED = ready to claim on L1",
    "EXPIRED retryables cannot be redeemed (funds returned)",
  ],
  code: `import { providers } from 'ethers';
import {
  ParentTransactionReceipt,
  ParentToChildMessageStatus,
  ChildTransactionReceipt,
  ChildToParentMessageStatus,
} from '@arbitrum/sdk';

/**
 * Check the status of an L1 → L2 message (retryable ticket).
 */
async function checkL1ToL2Status(l1TxHash: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);

  const l1Receipt = await l1Provider.getTransactionReceipt(l1TxHash);
  if (!l1Receipt) {
    console.log('L1 transaction not found');
    return;
  }

  const parentReceipt = new ParentTransactionReceipt(l1Receipt);
  const messages = await parentReceipt.getParentToChildMessages(l2Provider);

  for (const message of messages) {
    const status = await message.waitForStatus();
    console.log('L1→L2 Status:', ParentToChildMessageStatus[status.status]);
  }
}

/**
 * Check the status of an L2 → L1 message.
 */
async function checkL2ToL1Status(l2TxHash: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);

  const l2Receipt = await l2Provider.getTransactionReceipt(l2TxHash);
  if (!l2Receipt) {
    console.log('L2 transaction not found');
    return;
  }

  const childReceipt = new ChildTransactionReceipt(l2Receipt);
  const messages = await childReceipt.getChildToParentMessages(l1Provider);

  for (const message of messages) {
    const status = await message.status(l2Provider);
    console.log('L2→L1 Status:', ChildToParentMessageStatus[status]);
  }
}

// Status enums:
// ParentToChildMessageStatus: NOT_YET_CREATED(1), CREATION_FAILED(2), FUNDS_DEPOSITED_ON_CHILD(3), REDEEMED(4), EXPIRED(5)
// ChildToParentMessageStatus: UNCONFIRMED(0), CONFIRMED(1), EXECUTED(2)

// Usage
checkL1ToL2Status('0x...l1TxHash');
checkL2ToL1Status('0x...l2TxHash');`,
};

// ============================================================================
// EXPORTS
// ============================================================================

export const SDK_TEMPLATES: Record<string, SdkTemplate> = {
  // Bridging
  eth_deposit: ETH_DEPOSIT_TEMPLATE,
  eth_withdraw: ETH_WITHDRAW_TEMPLATE,
  erc20_deposit: ERC20_DEPOSIT_TEMPLATE,
  erc20_withdraw: ERC20_WITHDRAW_TEMPLATE,
  eth_l1_l3: ETH_L1_L3_TEMPLATE,
  // Messaging
  l1_to_l2_message: L1_TO_L2_MESSAGE_TEMPLATE,
  l2_to_l1_message: L2_TO_L1_MESSAGE_TEMPLATE,
  l2_to_l1_claim: L2_TO_L1_CLAIM_TEMPLATE,
  message_status: MESSAGE_STATUS_TEMPLATE,
};

export function listSdkTemplates(): SdkTemplate[] {
  return [
    // Bridging templates
    ETH_DEPOSIT_TEMPLATE,
    ETH_WITHDRAW_TEMPLATE,
    ERC20_DEPOSIT_TEMPLATE,
    ERC20_WITHDRAW_TEMPLATE,
    ETH_L1_L3_TEMPLATE,
    // Messaging templates
    L1_TO_L2_MESSAGE_TEMPLATE,
    L2_TO_L1_MESSAGE_TEMPLATE,
    L2_TO_L1_CLAIM_TEMPLATE,
    MESSAGE_STATUS_TEMPLATE,
  ];
}

export function getSdkTemplate(name: string): SdkTemplate | undefined {
  return SDK_TEMPLATES[name];
}

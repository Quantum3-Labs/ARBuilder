/**
 * Generate Arbitrum cross-chain messaging code (M2 tool)
 *
 * Supports:
 * - L1 -> L2 messaging via retryable tickets
 * - L2 -> L1 messaging via ArbSys
 * - Message status tracking
 */

// Message type definitions
type MessageType = "l1_to_l2" | "l2_to_l1" | "l2_to_l1_claim" | "check_status";

interface GenerateMessagingCodeArgs {
  messageType: MessageType;
  includeExample?: boolean;
}

interface GenerateMessagingCodeResult {
  code: string;
  messageType: MessageType;
  dependencies: Record<string, string>;
  envVars: string[];
  notes: string[];
  relatedTypes: Record<string, Record<string, number>>;
}

// Code templates
const L1_TO_L2_MESSAGE_TEMPLATE = `import { providers, Wallet, utils, BigNumber, Contract } from 'ethers';
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

// NodeInterface ABI for gas estimation
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

  // Use NodeInterface to estimate gas (call this on L2)
  const nodeInterface = new Contract(NODE_INTERFACE_ADDRESS, NODE_INTERFACE_ABI, l2Provider);

  // Estimate gas for the retryable ticket
  const estimates = await nodeInterface.callStatic.estimateRetryableTicket(
    l1Wallet.address,
    utils.parseEther('1'), // deposit estimate
    l2ContractAddress,
    l2CallValue,
    l1Wallet.address,
    l1Wallet.address,
    calldata
  );

  const gasLimit = estimates.gasLimit;
  const maxFeePerGas = await l2Provider.getGasPrice();

  // Calculate submission cost based on calldata size
  const inbox = new Contract(l2Network.ethBridge.inbox, INBOX_ABI, l1Wallet);
  const l1BaseFee = await l1Provider.getBlock('latest').then(b => b.baseFeePerGas || BigNumber.from(0));
  const maxSubmissionCost = await inbox.calculateRetryableSubmissionFee(
    calldata.length,
    l1BaseFee
  );

  console.log('Gas params:', {
    gasLimit: gasLimit.toString(),
    maxFeePerGas: maxFeePerGas.toString(),
    maxSubmissionCost: maxSubmissionCost.toString(),
  });

  // Calculate total deposit (with some buffer)
  const deposit = maxSubmissionCost.add(gasLimit.mul(maxFeePerGas)).add(l2CallValue);
  console.log('Total ETH required:', utils.formatEther(deposit));

  const tx = await inbox.createRetryableTicket(
    l2ContractAddress,
    l2CallValue,
    maxSubmissionCost,
    l1Wallet.address,  // excessFeeRefundAddress
    l1Wallet.address,  // callValueRefundAddress
    gasLimit,
    maxFeePerGas,
    calldata,
    { value: deposit }
  );

  console.log('L1 tx hash:', tx.hash);
  const receipt = await tx.wait();
  console.log('L1 tx confirmed');

  // Parse the receipt to get retryable ticket info
  const parentReceipt = new ParentTransactionReceipt(receipt);
  const messages = await parentReceipt.getParentToChildMessages(l2Provider);

  if (messages.length > 0) {
    const message = messages[0];
    console.log('Retryable ticket created');

    // Wait for L2 execution
    const status = await message.waitForStatus();
    console.log('Message status:', ParentToChildMessageStatus[status.status]);
  }

  return {
    l1TxHash: receipt.transactionHash,
    messages,
  };
}

// Example: Send a message to call a function on L2
// const iface = new utils.Interface(['function setValue(uint256 value)']);
// const calldata = iface.encodeFunctionData('setValue', [42]);
// sendL1ToL2Message('0x...L2ContractAddress', calldata);`;

const L2_TO_L1_MESSAGE_TEMPLATE = `import { providers, Wallet, utils, Contract } from 'ethers';
import { getArbitrumNetwork, ChildToParentMessageWriter } from '@arbitrum/sdk';

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

  // Send the L2 -> L1 message via ArbSys
  const tx = await arbSys.sendTxToL1(
    l1DestinationAddress,
    calldata,
    { value: utils.parseEther(value) }
  );

  console.log('L2 tx hash:', tx.hash);
  const receipt = await tx.wait();
  console.log('L2 tx confirmed');

  // Parse the L2ToL1Tx event
  const event = receipt.events?.find((e: any) => e.event === 'L2ToL1Tx');
  if (event) {
    console.log('Message position:', event.args.position.toString());
    console.log('Message hash:', event.args.hash.toString());
  }

  console.log('\\nIMPORTANT: Message will be executable on L1 after ~7 day challenge period');
  console.log('Use the claim script to execute on L1 after the period ends');

  return {
    l2TxHash: receipt.transactionHash,
    position: event?.args?.position?.toString(),
  };
}

// Example: Send a message to call a function on L1
// const iface = new utils.Interface(['function receiveMessage(bytes data)']);
// const calldata = iface.encodeFunctionData('receiveMessage', ['0x1234']);
// sendL2ToL1Message('0x...L1ContractAddress', calldata);`;

const L2_TO_L1_CLAIM_TEMPLATE = `import { providers, Wallet } from 'ethers';
import {
  ChildTransactionReceipt,
  ChildToParentMessageStatus,
} from '@arbitrum/sdk';

/**
 * Claim an L2 -> L1 message on L1 after the challenge period.
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

  // Get the L2 -> L1 messages from the receipt
  const childReceipt = new ChildTransactionReceipt(l2Receipt);
  const messages = await childReceipt.getChildToParentMessages(l1Wallet);

  if (messages.length === 0) {
    throw new Error('No L2 -> L1 messages found in transaction');
  }

  console.log(\`Found \${messages.length} message(s)\`);

  for (const message of messages) {
    // Check status
    const status = await message.status(l2Provider);
    console.log('Message status:', ChildToParentMessageStatus[status]);

    if (status === ChildToParentMessageStatus.CONFIRMED) {
      // Message is ready to be executed
      console.log('Executing message on L1...');
      const executeTx = await message.execute(l2Provider);
      const executeReceipt = await executeTx.wait();
      console.log('L1 execution tx:', executeReceipt.transactionHash);
    } else if (status === ChildToParentMessageStatus.EXECUTED) {
      console.log('Message already executed');
    } else if (status === ChildToParentMessageStatus.UNCONFIRMED) {
      console.log('Message not yet confirmed. Wait for challenge period (~7 days)');

      // Get time until confirmation
      const waitResult = await message.waitUntilReadyToExecute(l2Provider);
      if (waitResult) {
        console.log('Time remaining:', waitResult.toString(), 'seconds');
      }
    }
  }
}

// Usage: claimL2ToL1Message('0x...l2TxHash');`;

const MESSAGE_STATUS_TEMPLATE = `import { providers } from 'ethers';
import {
  ParentTransactionReceipt,
  ParentToChildMessageStatus,
  ChildTransactionReceipt,
  ChildToParentMessageStatus,
} from '@arbitrum/sdk';

/**
 * Check the status of an L1 -> L2 message (retryable ticket).
 */
async function checkL1ToL2Status(l1TxHash: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);

  const l1Receipt = await l1Provider.getTransactionReceipt(l1TxHash);
  if (!l1Receipt) {
    return { error: 'L1 transaction not found' };
  }

  const parentReceipt = new ParentTransactionReceipt(l1Receipt);
  const messages = await parentReceipt.getParentToChildMessages(l2Provider);

  const results = [];
  for (const message of messages) {
    const status = await message.waitForStatus();
    results.push({
      status: ParentToChildMessageStatus[status.status],
      statusCode: status.status,
    });
  }

  return results;
}

/**
 * Check the status of an L2 -> L1 message.
 */
async function checkL2ToL1Status(l2TxHash: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);

  const l2Receipt = await l2Provider.getTransactionReceipt(l2TxHash);
  if (!l2Receipt) {
    return { error: 'L2 transaction not found' };
  }

  const childReceipt = new ChildTransactionReceipt(l2Receipt);
  const messages = await childReceipt.getChildToParentMessages(l1Provider);

  const results = [];
  for (const message of messages) {
    const status = await message.status(l2Provider);
    results.push({
      status: ChildToParentMessageStatus[status],
      statusCode: status,
    });
  }

  return results;
}

// Message status enums for reference:
// ParentToChildMessageStatus:
//   NOT_YET_CREATED = 1
//   CREATION_FAILED = 2
//   FUNDS_DEPOSITED_ON_CHILD = 3
//   REDEEMED = 4 (success)
//   EXPIRED = 5

// ChildToParentMessageStatus:
//   UNCONFIRMED = 0 (in challenge period)
//   CONFIRMED = 1 (ready to execute)
//   EXECUTED = 2 (already claimed)`;

const TEMPLATES: Record<MessageType, string> = {
  l1_to_l2: L1_TO_L2_MESSAGE_TEMPLATE,
  l2_to_l1: L2_TO_L1_MESSAGE_TEMPLATE,
  l2_to_l1_claim: L2_TO_L1_CLAIM_TEMPLATE,
  check_status: MESSAGE_STATUS_TEMPLATE,
};

function getNotes(messageType: MessageType): string[] {
  const notes: string[] = [];

  if (messageType === "l1_to_l2") {
    notes.push("L1 -> L2 messages use retryable tickets");
    notes.push("Gas estimation is automatic but can be overridden");
    notes.push("Messages typically execute within 10-15 minutes");
    notes.push("If auto-redeem fails, tickets can be manually redeemed for 7 days");
  } else if (messageType === "l2_to_l1") {
    notes.push("L2 -> L1 messages go through ArbSys precompile");
    notes.push("Messages require ~7 day challenge period before claiming");
    notes.push("The message includes proof of L2 state for L1 verification");
  } else if (messageType === "l2_to_l1_claim") {
    notes.push("Can only claim after challenge period ends (~7 days)");
    notes.push("Use checkL2ToL1Status to verify message is CONFIRMED");
    notes.push("Anyone can execute the message (not just original sender)");
  } else if (messageType === "check_status") {
    notes.push("ParentToChildMessageStatus.REDEEMED = successful L1->L2");
    notes.push("ChildToParentMessageStatus.CONFIRMED = ready to claim on L1");
    notes.push("EXPIRED retryables cannot be redeemed (funds returned)");
  }

  return notes;
}

function getRelatedTypes(): Record<string, Record<string, number>> {
  return {
    ParentToChildMessageStatus: {
      NOT_YET_CREATED: 1,
      CREATION_FAILED: 2,
      FUNDS_DEPOSITED_ON_CHILD: 3,
      REDEEMED: 4,
      EXPIRED: 5,
    },
    ChildToParentMessageStatus: {
      UNCONFIRMED: 0,
      CONFIRMED: 1,
      EXECUTED: 2,
    },
  };
}

export function generateMessagingCode(
  args: GenerateMessagingCodeArgs
): GenerateMessagingCodeResult {
  const { messageType } = args;

  const code = TEMPLATES[messageType];

  if (!code) {
    throw new Error(`Unknown message type: ${messageType}`);
  }

  return {
    code,
    messageType,
    dependencies: {
      ethers: "^5.7.0",
      "@arbitrum/sdk": "^4.0.0",
    },
    envVars: ["L1_RPC_URL", "L2_RPC_URL", "PRIVATE_KEY"],
    notes: getNotes(messageType),
    relatedTypes: getRelatedTypes(),
  };
}

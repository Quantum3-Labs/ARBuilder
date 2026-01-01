"""
Generate Arbitrum cross-chain messaging code.

Supports:
- L1 -> L2 messaging via retryable tickets
- L2 -> L1 messaging via ArbSys
- Message status tracking
"""

import json
from typing import Any

from .base import BaseTool

# Template for L1 -> L2 message via retryable ticket
L1_TO_L2_MESSAGE_TEMPLATE = '''import { providers, Wallet, utils, BigNumber } from 'ethers';
import {
  ParentToChildMessageCreator,
  ParentToChildMessageGasEstimator,
  getArbitrumNetwork,
} from '@arbitrum/sdk';

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

  // Estimate gas for the retryable ticket
  const gasEstimator = new ParentToChildMessageGasEstimator(l2Provider);

  const gasParams = await gasEstimator.estimateAll(
    {
      from: l1Wallet.address,
      to: l2ContractAddress,
      l2CallValue,
      excessFeeRefundAddress: l1Wallet.address,
      callValueRefundAddress: l1Wallet.address,
      data: calldata,
    },
    await l1Provider.getBaseFeePerGas(),
    l1Provider
  );

  console.log('Estimated gas params:', {
    gasLimit: gasParams.gasLimit.toString(),
    maxFeePerGas: gasParams.maxFeePerGas.toString(),
    maxSubmissionCost: gasParams.maxSubmissionCost.toString(),
  });

  // Create the retryable ticket
  const messageCreator = new ParentToChildMessageCreator(l1Wallet);

  const ticketRequest = await messageCreator.getTicketCreationRequest(
    {
      to: l2ContractAddress,
      from: l1Wallet.address,
      l2CallValue,
      excessFeeRefundAddress: l1Wallet.address,
      callValueRefundAddress: l1Wallet.address,
      data: calldata,
      ...gasParams,
    },
    l1Provider,
    l2Provider
  );

  // Calculate total value needed (L2 call value + gas costs)
  const totalValue = gasParams.deposit.add(l2CallValue);
  console.log('Total ETH required:', utils.formatEther(totalValue));

  // Send the transaction
  const tx = await l1Wallet.sendTransaction({
    ...ticketRequest.txRequest,
    value: totalValue,
  });

  console.log('L1 tx hash:', tx.hash);
  const receipt = await tx.wait();
  console.log('L1 tx confirmed');

  // Wait for L2 execution
  const l2Result = await receipt.waitForChildTransactionReceipt(l2Provider);

  if (l2Result.complete) {
    console.log('Message executed on L2!');
    console.log('L2 tx hash:', l2Result.childTxReceipt.transactionHash);
  } else {
    console.log('Message not yet executed, status:', l2Result.status);
  }

  return {
    l1TxHash: receipt.transactionHash,
    l2TxHash: l2Result.childTxReceipt?.transactionHash,
    complete: l2Result.complete,
  };
}

// Example: Send a message to call a function on L2
// const iface = new utils.Interface(['function setValue(uint256 value)']);
// const calldata = iface.encodeFunctionData('setValue', [42]);
// sendL1ToL2Message('0x...L2ContractAddress', calldata);
'''

# Template for L2 -> L1 message
L2_TO_L1_MESSAGE_TEMPLATE = '''import { providers, Wallet, utils, Contract } from 'ethers';
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
// sendL2ToL1Message('0x...L1ContractAddress', calldata);
'''

# Template for claiming L2 -> L1 message on L1
L2_TO_L1_CLAIM_TEMPLATE = '''import { providers, Wallet } from 'ethers';
import {
  ChildToParentMessage,
  ChildToParentMessageStatus,
  getArbitrumNetwork,
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
  const messages = await ChildToParentMessage.getChildToParentMessages(
    l1Wallet,
    l2Receipt,
    l2Provider
  );

  if (messages.length === 0) {
    throw new Error('No L2 -> L1 messages found in transaction');
  }

  console.log(`Found ${messages.length} message(s)`);

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

// Usage: claimL2ToL1Message('0x...l2TxHash');
'''

# Template for checking message status
MESSAGE_STATUS_TEMPLATE = '''import { providers } from 'ethers';
import {
  ParentToChildMessage,
  ParentToChildMessageStatus,
  ChildToParentMessage,
  ChildToParentMessageStatus,
  getArbitrumNetwork,
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

  const messages = await ParentToChildMessage.getParentToChildMessages(
    l1Receipt,
    l2Provider
  );

  const results = [];
  for (const message of messages) {
    const status = await message.status();
    results.push({
      retryableId: message.retryableCreationId,
      status: ParentToChildMessageStatus[status],
      statusCode: status,
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

  const messages = await ChildToParentMessage.getChildToParentMessages(
    l1Provider,
    l2Receipt,
    l2Provider
  );

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
//   EXECUTED = 2 (already claimed)
'''


class GenerateMessagingCodeTool(BaseTool):
    """Generate Arbitrum cross-chain messaging code."""

    name = "generate_messaging_code"
    description = """Generate TypeScript code for Arbitrum cross-chain messaging.

Supports:
- L1 -> L2 messaging via retryable tickets
- L2 -> L1 messaging via ArbSys precompile
- Message status checking
- Claiming L2 -> L1 messages after challenge period

The generated code uses ethers.js v5 and @arbitrum/sdk."""

    input_schema = {
        "type": "object",
        "properties": {
            "message_type": {
                "type": "string",
                "enum": ["l1_to_l2", "l2_to_l1", "l2_to_l1_claim", "check_status"],
                "description": "Type of messaging operation to generate code for",
            },
            "include_example": {
                "type": "boolean",
                "description": "Include example usage with sample contract call",
                "default": True,
            },
        },
        "required": ["message_type"],
    }

    def __init__(self, context_tool=None):
        """Initialize with optional context tool for RAG."""
        self.context_tool = context_tool

    def execute(self, **kwargs) -> dict[str, Any]:
        """Generate messaging code based on the specified type."""
        message_type = kwargs.get("message_type")
        include_example = kwargs.get("include_example", True)

        if not message_type:
            return {"error": "message_type is required"}

        templates = {
            "l1_to_l2": L1_TO_L2_MESSAGE_TEMPLATE,
            "l2_to_l1": L2_TO_L1_MESSAGE_TEMPLATE,
            "l2_to_l1_claim": L2_TO_L1_CLAIM_TEMPLATE,
            "check_status": MESSAGE_STATUS_TEMPLATE,
        }

        template = templates.get(message_type)
        if not template:
            return {"error": f"Unknown message_type: {message_type}"}

        result = {
            "code": template,
            "message_type": message_type,
            "dependencies": {
                "ethers": "^5.7.0",
                "@arbitrum/sdk": "^4.0.0",
            },
            "env_vars": [
                "L1_RPC_URL",
                "L2_RPC_URL",
                "PRIVATE_KEY",
            ],
            "notes": self._get_notes(message_type),
            "related_types": self._get_related_types(message_type),
        }

        return result

    def _get_notes(self, message_type: str) -> list[str]:
        """Get helpful notes for the message type."""
        notes = []

        if message_type == "l1_to_l2":
            notes.extend([
                "L1 -> L2 messages use retryable tickets",
                "Gas estimation is automatic but can be overridden",
                "Messages typically execute within 10-15 minutes",
                "If auto-redeem fails, tickets can be manually redeemed for 7 days",
            ])
        elif message_type == "l2_to_l1":
            notes.extend([
                "L2 -> L1 messages go through ArbSys precompile",
                "Messages require ~7 day challenge period before claiming",
                "The message includes proof of L2 state for L1 verification",
            ])
        elif message_type == "l2_to_l1_claim":
            notes.extend([
                "Can only claim after challenge period ends (~7 days)",
                "Use checkL2ToL1Status to verify message is CONFIRMED",
                "Anyone can execute the message (not just original sender)",
            ])
        elif message_type == "check_status":
            notes.extend([
                "ParentToChildMessageStatus.REDEEMED = successful L1->L2",
                "ChildToParentMessageStatus.CONFIRMED = ready to claim on L1",
                "EXPIRED retryables cannot be redeemed (funds returned)",
            ])

        return notes

    def _get_related_types(self, message_type: str) -> dict:
        """Get related SDK types for reference."""
        return {
            "ParentToChildMessageStatus": {
                "NOT_YET_CREATED": 1,
                "CREATION_FAILED": 2,
                "FUNDS_DEPOSITED_ON_CHILD": 3,
                "REDEEMED": 4,
                "EXPIRED": 5,
            },
            "ChildToParentMessageStatus": {
                "UNCONFIRMED": 0,
                "CONFIRMED": 1,
                "EXECUTED": 2,
            },
        }

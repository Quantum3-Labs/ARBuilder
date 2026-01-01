"""
Generate Arbitrum bridging code using the Arbitrum SDK.

Supports:
- ETH bridging (L1 <-> L2) via EthBridger
- ERC20 token bridging via Erc20Bridger
- L1 -> L3 bridging via EthL1L3Bridger and Erc20L1L3Bridger
"""

import json
import re
from typing import Any

from .base import BaseTool

# Template for ETH deposit (L1 -> L2)
ETH_DEPOSIT_TEMPLATE = '''import { providers, Wallet, utils } from 'ethers';
import { EthBridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function depositEth() {
  // Setup providers
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l1Provider);

  // Get network and bridger
  const l2Network = await getArbitrumNetwork(l2Provider);
  const ethBridger = new EthBridger(l2Network);

  // Deposit ETH
  const depositTx = await ethBridger.deposit({
    amount: utils.parseEther('{amount}'),
    parentSigner: wallet,
  });

  console.log('Deposit tx:', depositTx.hash);
  const receipt = await depositTx.wait();
  console.log('Deposit confirmed:', receipt.transactionHash);

  // Wait for L2 confirmation
  const l2Result = await receipt.waitForChildTransactionReceipt(l2Provider);
  if (l2Result.complete) {
    console.log('ETH received on L2!');
  }
}

depositEth().catch(console.error);
'''

# Template for ETH deposit to different address
ETH_DEPOSIT_TO_TEMPLATE = '''import { providers, Wallet, utils } from 'ethers';
import { EthBridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function depositEthTo(destinationAddress: string, amount: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l1Provider);

  const l2Network = await getArbitrumNetwork(l2Provider);
  const ethBridger = new EthBridger(l2Network);

  // Deposit to a different address using retryable ticket
  const depositTx = await ethBridger.depositTo({
    amount: utils.parseEther(amount),
    parentSigner: wallet,
    childProvider: l2Provider,
    destinationAddress,
  });

  console.log('Deposit tx:', depositTx.hash);
  const receipt = await depositTx.wait();

  const l2Result = await receipt.waitForChildTransactionReceipt(l2Provider);
  console.log('Deposit complete:', l2Result.complete);
}

// Usage: depositEthTo('0x...', '0.1');
'''

# Template for ETH withdrawal (L2 -> L1)
ETH_WITHDRAW_TEMPLATE = '''import { providers, Wallet, utils } from 'ethers';
import { EthBridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function withdrawEth(amount: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const l2Wallet = new Wallet(process.env.PRIVATE_KEY!, l2Provider);

  const l2Network = await getArbitrumNetwork(l2Provider);
  const ethBridger = new EthBridger(l2Network);

  // Initiate withdrawal from L2
  const withdrawTx = await ethBridger.withdraw({
    amount: utils.parseEther(amount),
    childSigner: l2Wallet,
    destinationAddress: l2Wallet.address,
    from: l2Wallet.address,
  });

  console.log('Withdrawal initiated:', withdrawTx.hash);
  const receipt = await withdrawTx.wait();
  console.log('L2 tx confirmed:', receipt.transactionHash);

  // Note: Withdrawal requires ~7 day challenge period before claiming on L1
  console.log('Withdrawal will be claimable after challenge period (~7 days)');
}

withdrawEth('{amount}').catch(console.error);
'''

# Template for ERC20 deposit
ERC20_DEPOSIT_TEMPLATE = '''import { providers, Wallet, BigNumber } from 'ethers';
import { Erc20Bridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function depositToken(tokenAddress: string, amount: BigNumber) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l1Provider);

  const l2Network = await getArbitrumNetwork(l2Provider);
  const erc20Bridger = new Erc20Bridger(l2Network);

  // Step 1: Approve token for gateway
  console.log('Approving token...');
  const approveTx = await erc20Bridger.approveToken({
    erc20ParentAddress: tokenAddress,
    parentSigner: wallet,
    amount,
  });
  await approveTx.wait();
  console.log('Token approved');

  // Step 2: Deposit token
  console.log('Depositing token...');
  const depositTx = await erc20Bridger.deposit({
    amount,
    erc20ParentAddress: tokenAddress,
    parentSigner: wallet,
    childProvider: l2Provider,
  });

  console.log('Deposit tx:', depositTx.hash);
  const receipt = await depositTx.wait();

  // Wait for L2 confirmation
  const l2Result = await receipt.waitForChildTransactionReceipt(l2Provider);
  if (l2Result.complete) {
    console.log('Token received on L2!');
  }
}

// Usage: depositToken('0x...tokenAddress', BigNumber.from('1000000000000000000'));
'''

# Template for ERC20 withdrawal
ERC20_WITHDRAW_TEMPLATE = '''import { providers, Wallet, BigNumber } from 'ethers';
import { Erc20Bridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function withdrawToken(l1TokenAddress: string, amount: BigNumber) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const l2Wallet = new Wallet(process.env.PRIVATE_KEY!, l2Provider);

  const l2Network = await getArbitrumNetwork(l2Provider);
  const erc20Bridger = new Erc20Bridger(l2Network);

  // Get L2 token address
  const l2TokenAddress = await erc20Bridger.getChildErc20Address(
    l1TokenAddress,
    l1Provider
  );
  console.log('L2 token address:', l2TokenAddress);

  // Initiate withdrawal
  const withdrawTx = await erc20Bridger.withdraw({
    amount,
    erc20ParentAddress: l1TokenAddress,
    childSigner: l2Wallet,
    destinationAddress: l2Wallet.address,
  });

  console.log('Withdrawal initiated:', withdrawTx.hash);
  const receipt = await withdrawTx.wait();
  console.log('L2 tx confirmed');

  // Note: Requires ~7 day challenge period
  console.log('Withdrawal will be claimable after challenge period (~7 days)');
}

// Usage: withdrawToken('0x...l1TokenAddress', BigNumber.from('1000000000000000000'));
'''

# Template for L1 -> L3 ETH bridging
ETH_L1_L3_TEMPLATE = '''import { providers, Wallet, utils } from 'ethers';
import { EthL1L3Bridger, getArbitrumNetwork, ParentToChildMessageStatus } from '@arbitrum/sdk';

async function depositEthToL3(amount: string) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const l3Provider = new providers.JsonRpcProvider(process.env.L3_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l1Provider);

  // Get L3 network config
  const l3Network = await getArbitrumNetwork(l3Provider);
  const bridger = new EthL1L3Bridger(l3Network);

  // Get deposit request (calculates gas for double retryable)
  const depositRequest = await bridger.getDepositRequest({
    amount: utils.parseEther(amount),
    l1Signer: wallet,
    l2Provider,
    l3Provider,
  });

  // Execute deposit
  const depositTx = await bridger.deposit({
    txRequest: depositRequest.txRequest,
    l1Signer: wallet,
  });

  console.log('L1 -> L3 deposit tx:', depositTx.hash);
  await depositTx.wait();

  // Monitor status
  const status = await bridger.getDepositStatus({
    txHash: depositTx.hash,
    l1Provider,
    l2Provider,
    l3Provider,
  });

  console.log('Deposit completed:', status.completed);
}

depositEthToL3('{amount}').catch(console.error);
'''

# Template for L1 -> L3 ERC20 bridging
ERC20_L1_L3_TEMPLATE = '''import { providers, Wallet, BigNumber } from 'ethers';
import { Erc20L1L3Bridger, getArbitrumNetwork } from '@arbitrum/sdk';

async function depositTokenToL3(l1TokenAddress: string, amount: BigNumber) {
  const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
  const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
  const l3Provider = new providers.JsonRpcProvider(process.env.L3_RPC_URL);
  const wallet = new Wallet(process.env.PRIVATE_KEY!, l1Provider);

  const l3Network = await getArbitrumNetwork(l3Provider);
  const bridger = new Erc20L1L3Bridger(l3Network);

  // Get deposit request
  const depositRequest = await bridger.getDepositRequest({
    l1Signer: wallet,
    erc20L1Address: l1TokenAddress,
    amount,
    l2Provider,
    l3Provider,
  });

  // Approve gas token if needed (for L3 gas fees)
  if (depositRequest.gasTokenAmount.gt(0)) {
    console.log('Approving gas token...');
    const gasApproveTx = await bridger.approveGasToken({
      l1Signer: wallet,
      l2Provider,
      amount: depositRequest.gasTokenAmount,
    });
    await gasApproveTx.wait();
  }

  // Approve the token
  console.log('Approving token...');
  const approveTx = await bridger.approveToken({
    erc20L1Address: l1TokenAddress,
    l1Signer: wallet,
    amount,
  });
  await approveTx.wait();

  // Execute deposit
  console.log('Depositing...');
  const depositTx = await bridger.deposit({
    txRequest: depositRequest.txRequest,
    l1Signer: wallet,
  });

  console.log('L1 -> L3 deposit tx:', depositTx.hash);

  // Monitor multi-stage status
  const status = await bridger.getDepositStatus({
    txHash: depositTx.hash,
    l1Provider,
    l2Provider,
    l3Provider,
  });

  console.log('Completed:', status.completed);
}

// Usage: depositTokenToL3('0x...', BigNumber.from('1000000000000000000'));
'''


class GenerateBridgeCodeTool(BaseTool):
    """Generate Arbitrum SDK bridging code."""

    name = "generate_bridge_code"
    description = """Generate TypeScript code for Arbitrum asset bridging using the Arbitrum SDK.

Supports:
- ETH bridging (L1 <-> L2) - deposit and withdraw
- ERC20 token bridging (L1 <-> L2) - deposit and withdraw with approvals
- L1 -> L3 bridging for Orbit chains (ETH and ERC20)

The generated code uses ethers.js v5 and @arbitrum/sdk."""

    input_schema = {
        "type": "object",
        "properties": {
            "bridge_type": {
                "type": "string",
                "enum": ["eth_deposit", "eth_deposit_to", "eth_withdraw",
                         "erc20_deposit", "erc20_withdraw",
                         "eth_l1_l3", "erc20_l1_l3"],
                "description": "Type of bridging operation to generate code for",
            },
            "amount": {
                "type": "string",
                "description": "Amount to bridge (in ETH for eth operations, or token units)",
                "default": "0.1",
            },
            "token_address": {
                "type": "string",
                "description": "L1 token address (required for erc20 operations)",
            },
            "destination_address": {
                "type": "string",
                "description": "Destination address (for deposit_to operations)",
            },
            "include_status_check": {
                "type": "boolean",
                "description": "Include code for checking bridge status",
                "default": True,
            },
        },
        "required": ["bridge_type"],
    }

    def __init__(self, context_tool=None):
        """Initialize with optional context tool for RAG."""
        self.context_tool = context_tool

    def execute(self, **kwargs) -> dict[str, Any]:
        """Generate bridging code based on the specified type."""
        bridge_type = kwargs.get("bridge_type")
        amount = kwargs.get("amount", "0.1")
        token_address = kwargs.get("token_address", "0x...")
        destination = kwargs.get("destination_address", "0x...")
        include_status = kwargs.get("include_status_check", True)

        # Validate inputs
        if not bridge_type:
            return {"error": "bridge_type is required"}

        if bridge_type.startswith("erc20") and not token_address:
            return {"error": "token_address is required for ERC20 operations"}

        # Select template
        templates = {
            "eth_deposit": ETH_DEPOSIT_TEMPLATE,
            "eth_deposit_to": ETH_DEPOSIT_TO_TEMPLATE,
            "eth_withdraw": ETH_WITHDRAW_TEMPLATE,
            "erc20_deposit": ERC20_DEPOSIT_TEMPLATE,
            "erc20_withdraw": ERC20_WITHDRAW_TEMPLATE,
            "eth_l1_l3": ETH_L1_L3_TEMPLATE,
            "erc20_l1_l3": ERC20_L1_L3_TEMPLATE,
        }

        template = templates.get(bridge_type)
        if not template:
            return {"error": f"Unknown bridge_type: {bridge_type}"}

        # Format template using replace to avoid curly brace issues
        code = template.replace("{amount}", amount)
        code = code.replace("{token_address}", token_address)
        code = code.replace("{destination}", destination)

        # Build response
        result = {
            "code": code,
            "bridge_type": bridge_type,
            "dependencies": {
                "ethers": "^5.7.0",
                "@arbitrum/sdk": "^4.0.0",
            },
            "env_vars": [
                "L1_RPC_URL",
                "L2_RPC_URL",
                "PRIVATE_KEY",
            ],
            "notes": self._get_notes(bridge_type),
        }

        if bridge_type in ["eth_l1_l3", "erc20_l1_l3"]:
            result["env_vars"].append("L3_RPC_URL")

        return result

    def _get_notes(self, bridge_type: str) -> list[str]:
        """Get helpful notes for the bridge type."""
        notes = []

        if "withdraw" in bridge_type:
            notes.append("Withdrawals require a ~7 day challenge period before claiming on L1")
            notes.append("Use ChildToParentMessage to track withdrawal status")

        if "deposit" in bridge_type:
            notes.append("Deposits typically confirm on L2 within 10-15 minutes")
            notes.append("Use waitForChildTransactionReceipt to wait for L2 confirmation")

        if "erc20" in bridge_type:
            notes.append("Token must be approved before bridging")
            notes.append("L2 token address is derived automatically by the gateway")

        if "l1_l3" in bridge_type:
            notes.append("L1->L3 bridging uses double retryable tickets (L1->L2->L3)")
            notes.append("Gas estimation accounts for both L2 and L3 execution")
            notes.append("Custom gas tokens may require additional approvals")

        return notes

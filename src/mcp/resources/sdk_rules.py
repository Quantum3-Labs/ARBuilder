"""
Arbitrum SDK Coding Rules Resource.

Provides coding guidelines for Arbitrum SDK bridging and cross-chain messaging.
"""

SDK_CODING_RULES = {
    "name": "Arbitrum SDK Rules",
    "version": "1.0.0",
    "description": "Guidelines for AI assistants generating Arbitrum SDK bridging code",

    "sdk_version": {
        "arbitrum_sdk": "^4.0.0",
        "ethers": "^5.7.0",
        "note": "Uses ethers v5, not v6",
    },

    "terminology": {
        "parent": "L1 (Ethereum) or L2 (when bridging to L3)",
        "child": "L2 (Arbitrum) or L3 (Orbit chain)",
        "retryable_ticket": "L1->L2 message mechanism with auto-redemption",
        "challenge_period": "~7 days for L2->L1 withdrawals",
    },

    "bridging_classes": {
        "EthBridger": {
            "purpose": "Bridge ETH between L1 and L2",
            "methods": ["deposit()", "depositTo()", "withdraw()"],
            "example": '''const ethBridger = new EthBridger(l2Network);
const depositTx = await ethBridger.deposit({
  amount: utils.parseEther('0.1'),
  parentSigner: l1Wallet,
});''',
        },
        "Erc20Bridger": {
            "purpose": "Bridge ERC20 tokens between L1 and L2",
            "methods": ["approveToken()", "deposit()", "withdraw()"],
            "note": "Always approve token before deposit",
            "example": '''const erc20Bridger = new Erc20Bridger(l2Network);
// Step 1: Approve
await erc20Bridger.approveToken({
  erc20ParentAddress: tokenAddress,
  parentSigner: l1Wallet,
});
// Step 2: Deposit
await erc20Bridger.deposit({
  amount,
  erc20ParentAddress: tokenAddress,
  parentSigner: l1Wallet,
  childProvider: l2Provider,
});''',
        },
        "EthL1L3Bridger": {
            "purpose": "Bridge ETH from L1 directly to L3 (Orbit chains)",
            "mechanism": "Double retryable (L1->L2->L3)",
            "example": '''const bridger = new EthL1L3Bridger(l3Network);
const depositRequest = await bridger.getDepositRequest({
  amount: utils.parseEther('0.1'),
  l1Signer: wallet,
  l2Provider,
  l3Provider,
});''',
        },
        "Erc20L1L3Bridger": {
            "purpose": "Bridge ERC20 from L1 to L3",
            "note": "May require gas token approval for L3 fees",
        },
    },

    "messaging": {
        "l1_to_l2": {
            "mechanism": "Retryable tickets via Inbox contract",
            "time": "~10-15 minutes",
            "gas_params": ["gasLimit", "maxFeePerGas", "maxSubmissionCost"],
            "key_contract": "Inbox (createRetryableTicket)",
            "estimation": "Use NodeInterface at 0x00000000000000000000000000000000000000C8",
        },
        "l2_to_l1": {
            "mechanism": "ArbSys precompile",
            "address": "0x0000000000000000000000000000000000000064",
            "method": "sendTxToL1(destination, data)",
            "time": "~7 days challenge period",
            "claim": "Execute on L1 after challenge period",
        },
    },

    "status_enums": {
        "ParentToChildMessageStatus": {
            "NOT_YET_CREATED": 1,
            "CREATION_FAILED": 2,
            "FUNDS_DEPOSITED_ON_CHILD": 3,
            "REDEEMED": 4,  # Success
            "EXPIRED": 5,
        },
        "ChildToParentMessageStatus": {
            "UNCONFIRMED": 0,  # In challenge period
            "CONFIRMED": 1,   # Ready to execute
            "EXECUTED": 2,    # Already claimed
        },
    },

    "patterns": {
        "provider_setup": '''const l1Provider = new providers.JsonRpcProvider(process.env.L1_RPC_URL);
const l2Provider = new providers.JsonRpcProvider(process.env.L2_RPC_URL);
const wallet = new Wallet(process.env.PRIVATE_KEY!, l1Provider);
const l2Network = await getArbitrumNetwork(l2Provider);''',

        "wait_for_l2": '''const receipt = await depositTx.wait();
const l2Result = await receipt.waitForChildTransactionReceipt(l2Provider);
if (l2Result.complete) {
  console.log('Deposit confirmed on L2');
}''',

        "check_withdrawal_status": '''const childReceipt = new ChildTransactionReceipt(l2Receipt);
const messages = await childReceipt.getChildToParentMessages(l1Wallet);
const status = await messages[0].status(l2Provider);
// ChildToParentMessageStatus.CONFIRMED = ready to claim''',
    },

    "env_vars": [
        "L1_RPC_URL",
        "L2_RPC_URL",
        "L3_RPC_URL (for Orbit chains)",
        "PRIVATE_KEY",
    ],

    "networks": {
        "ethereum_mainnet": "https://eth.llamarpc.com",
        "ethereum_sepolia": "https://rpc.sepolia.org",
        "arbitrum_one": "https://arb1.arbitrum.io/rpc",
        "arbitrum_sepolia": "https://sepolia-rollup.arbitrum.io/rpc",
        "arbitrum_nova": "https://nova.arbitrum.io/rpc",
    },

    "common_pitfalls": [
        "Forgetting to approve ERC20 before deposit",
        "Not waiting for L2 confirmation after deposit",
        "Trying to claim withdrawal before 7-day period",
        "Using ethers v6 syntax with SDK (use v5)",
        "Not handling retryable ticket expiration (7 days)",
        "Insufficient gas for L1->L2 message execution",
    ],

    "key_imports": '''import { providers, Wallet, utils, BigNumber } from 'ethers';
import {
  EthBridger,
  Erc20Bridger,
  getArbitrumNetwork,
  ParentTransactionReceipt,
  ChildTransactionReceipt,
  ParentToChildMessageStatus,
  ChildToParentMessageStatus,
} from '@arbitrum/sdk';''',
}

"""
Q&A tool for Arbitrum bridging and cross-chain messaging questions.

Uses RAG to retrieve relevant context from Arbitrum SDK documentation
and provides accurate answers about bridging patterns.
"""

import os
from typing import Any

from .base import BaseTool

# Pre-built knowledge base for common bridging questions
BRIDGING_KNOWLEDGE = {
    "eth_deposit": {
        "description": "Deposit ETH from L1 (Ethereum) to L2 (Arbitrum)",
        "class": "EthBridger",
        "method": "deposit() or depositTo()",
        "time": "~10-15 minutes for L2 confirmation",
        "gas": "Paid on L1, includes L2 execution costs",
    },
    "eth_withdraw": {
        "description": "Withdraw ETH from L2 (Arbitrum) to L1 (Ethereum)",
        "class": "EthBridger",
        "method": "withdraw()",
        "time": "~7 days challenge period before claiming on L1",
        "gas": "Paid on L2 for initiation, L1 for claiming",
    },
    "erc20_deposit": {
        "description": "Deposit ERC20 tokens from L1 to L2",
        "class": "Erc20Bridger",
        "method": "approveToken() then deposit()",
        "time": "~10-15 minutes for L2 confirmation",
        "notes": "Token must be approved for gateway first",
    },
    "erc20_withdraw": {
        "description": "Withdraw ERC20 tokens from L2 to L1",
        "class": "Erc20Bridger",
        "method": "withdraw()",
        "time": "~7 days challenge period",
        "notes": "L2 token address is derived from L1 address",
    },
    "retryable_tickets": {
        "description": "L1->L2 message delivery mechanism",
        "lifecycle": [
            "1. Created on L1 via Inbox contract",
            "2. Funds deposited on L2",
            "3. Auto-redeemed if gas params sufficient",
            "4. Can be manually redeemed if auto-redeem fails",
            "5. Expires after 7 days if not redeemed",
        ],
        "gas_params": ["gasLimit", "maxFeePerGas", "maxSubmissionCost"],
    },
    "l1_to_l2_messaging": {
        "description": "Send arbitrary messages from L1 to L2",
        "class": "InboxTools (for gas estimation) + Inbox contract",
        "mechanism": "Retryable tickets via createRetryableTicket",
        "time": "~10-15 minutes",
        "use_cases": ["Cross-chain contract calls", "Governance execution"],
    },
    "l2_to_l1_messaging": {
        "description": "Send messages from L2 to L1",
        "contract": "ArbSys (0x64)",
        "method": "sendTxToL1()",
        "time": "~7 days challenge period",
        "mechanism": "Merkle proof of L2 state",
    },
    "l1_l3_bridging": {
        "description": "Bridge assets directly from L1 to L3 (Orbit chains)",
        "classes": ["EthL1L3Bridger", "Erc20L1L3Bridger"],
        "mechanism": "Double retryable (L1->L2->L3)",
        "notes": "May require gas token approval for L3 fees",
    },
    "custom_gas_token": {
        "description": "L3 chains can use custom ERC20 as gas token",
        "method": "approveGasToken()",
        "notes": "Must approve gas token on L1 before bridging to L3",
    },
}


class AskBridgingTool(BaseTool):
    """Answer questions about Arbitrum bridging and cross-chain messaging."""

    name = "ask_bridging"
    description = """Answer questions about Arbitrum bridging and cross-chain messaging.

Topics covered:
- ETH and ERC20 bridging (L1 <-> L2)
- L1 -> L3 bridging for Orbit chains
- Retryable tickets and message lifecycle
- Cross-chain messaging patterns
- Challenge periods and withdrawal claiming
- Gas estimation and custom gas tokens

Uses knowledge base and optional RAG for accurate answers."""

    input_schema = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "Question about Arbitrum bridging or messaging",
            },
            "include_code_example": {
                "type": "boolean",
                "description": "Include a code example in the answer if relevant",
                "default": False,
            },
        },
        "required": ["question"],
    }

    def __init__(self, context_tool=None, llm_client=None):
        """Initialize with optional context tool and LLM client."""
        self.context_tool = context_tool
        self.llm_client = llm_client

    def execute(self, **kwargs) -> dict[str, Any]:
        """Answer a bridging question."""
        question = kwargs.get("question", "").strip()
        include_code = kwargs.get("include_code_example", False)

        if not question:
            return {"error": "Question is required and cannot be empty"}

        # Normalize question
        q_lower = question.lower()

        # Try to match against knowledge base
        answer_parts = []
        relevant_topics = []

        # Check for ETH-related questions
        if "eth" in q_lower and ("deposit" in q_lower or "bridge" in q_lower or "withdraw" in q_lower):
            if "withdraw" in q_lower or ("l1" in q_lower and "from l2" in q_lower):
                relevant_topics.append("eth_withdraw")
            else:
                relevant_topics.append("eth_deposit")

        # Check for token/ERC20 questions
        if "token" in q_lower or "erc20" in q_lower:
            if "withdraw" in q_lower:
                relevant_topics.append("erc20_withdraw")
            else:
                relevant_topics.append("erc20_deposit")

        # Check for retryable ticket questions
        if "retryable" in q_lower or "ticket" in q_lower:
            relevant_topics.append("retryable_tickets")

        # Check for messaging questions
        if "message" in q_lower or "messaging" in q_lower:
            if "l2 to l1" in q_lower or "l2->l1" in q_lower or "withdraw" in q_lower:
                relevant_topics.append("l2_to_l1_messaging")
            else:
                relevant_topics.append("l1_to_l2_messaging")

        # Check for L3/Orbit questions
        if "l3" in q_lower or "orbit" in q_lower:
            relevant_topics.append("l1_l3_bridging")

        # Check for gas token questions
        if "gas token" in q_lower or "custom gas" in q_lower:
            relevant_topics.append("custom_gas_token")

        # Check for timing questions
        if "how long" in q_lower or "time" in q_lower or "when" in q_lower:
            if "withdraw" in q_lower:
                relevant_topics.extend(["eth_withdraw", "l2_to_l1_messaging"])
            else:
                relevant_topics.append("eth_deposit")

        # Build answer from relevant topics
        if relevant_topics:
            for topic in set(relevant_topics):
                if topic in BRIDGING_KNOWLEDGE:
                    info = BRIDGING_KNOWLEDGE[topic]
                    answer_parts.append(f"## {topic.replace('_', ' ').title()}")
                    for key, value in info.items():
                        if isinstance(value, list):
                            answer_parts.append(f"**{key.replace('_', ' ').title()}:**")
                            for item in value:
                                answer_parts.append(f"  - {item}")
                        else:
                            answer_parts.append(f"**{key.replace('_', ' ').title()}:** {value}")
                    answer_parts.append("")

        # Try RAG context if available
        rag_context = ""
        if self.context_tool:
            try:
                ctx_result = self.context_tool.run(query=question, n_results=3)
                if ctx_result.get("contexts"):
                    rag_context = "\n\n".join(
                        c.get("content", "") for c in ctx_result["contexts"][:2]
                    )
            except Exception:
                pass  # RAG is optional

        # Build final answer
        if answer_parts:
            answer = "\n".join(answer_parts)
        else:
            # Generic answer for unmatched questions
            answer = self._get_generic_answer(question)

        result = {
            "answer": answer,
            "topics": list(set(relevant_topics)) if relevant_topics else ["general"],
            "references": self._get_references(relevant_topics),
        }

        if include_code:
            result["code_example"] = self._get_code_example(relevant_topics)

        if rag_context:
            result["additional_context"] = rag_context[:1000]

        return result

    def _get_generic_answer(self, question: str) -> str:
        """Get a generic answer for unmatched questions."""
        return """## Arbitrum Bridging Overview

The Arbitrum SDK provides several bridging classes:

**Asset Bridging (L1 <-> L2):**
- `EthBridger` - Bridge ETH between L1 and L2
- `Erc20Bridger` - Bridge ERC20 tokens

**L1 -> L3 Bridging (Orbit Chains):**
- `EthL1L3Bridger` - Bridge ETH from L1 directly to L3
- `Erc20L1L3Bridger` - Bridge tokens from L1 to L3

**Cross-Chain Messaging:**
- `InboxTools` + Inbox contract - Create L1->L2 retryable tickets
- `ArbSys` precompile - Send L2->L1 messages

**Key Timings:**
- L1 -> L2: ~10-15 minutes
- L2 -> L1: ~7 days challenge period

For specific questions, try asking about:
- "How do I deposit ETH to Arbitrum?"
- "How long does a withdrawal take?"
- "How do retryable tickets work?"
- "How do I bridge tokens to L3?"
"""

    def _get_references(self, topics: list) -> list[str]:
        """Get documentation references for topics."""
        refs = [
            "https://docs.arbitrum.io/build-decentralized-apps/token-bridging/token-bridge-erc20",
            "https://docs.arbitrum.io/build-decentralized-apps/cross-chain-messaging",
        ]

        if "l1_l3_bridging" in topics:
            refs.append("https://docs.arbitrum.io/launch-orbit-chain/how-tos/bridge-tokens")

        if "retryable_tickets" in topics:
            refs.append("https://docs.arbitrum.io/how-arbitrum-works/arbos/l1-l2-messaging")

        return refs

    def _get_code_example(self, topics: list) -> str:
        """Get a code example for the topics."""
        if "eth_deposit" in topics:
            return '''const ethBridger = new EthBridger(l2Network);
const depositTx = await ethBridger.deposit({
  amount: utils.parseEther('0.1'),
  parentSigner: l1Wallet,
});
await depositTx.wait();'''

        if "erc20_deposit" in topics:
            return '''const erc20Bridger = new Erc20Bridger(l2Network);
// Approve first
await (await erc20Bridger.approveToken({
  erc20ParentAddress: tokenAddress,
  parentSigner: l1Wallet,
})).wait();
// Then deposit
await erc20Bridger.deposit({
  amount,
  erc20ParentAddress: tokenAddress,
  parentSigner: l1Wallet,
  childProvider: l2Provider,
});'''

        if "l1_to_l2_messaging" in topics:
            return '''// Use InboxTools for gas estimation
const inboxTools = new InboxTools(l1Wallet, l2Network);
const gasParams = await inboxTools.estimateRetryableTicketGasLimit({...});

// Call createRetryableTicket on Inbox contract
const inbox = new Contract(l2Network.ethBridge.inbox, INBOX_ABI, l1Wallet);
const tx = await inbox.createRetryableTicket(...);'''

        return "// Use generate_bridge_code or generate_messaging_code for full examples"

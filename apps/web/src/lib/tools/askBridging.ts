/**
 * Ask Bridging Tool (M2 tool)
 *
 * Answers questions about Arbitrum bridging and cross-chain messaging
 * using RAG to retrieve relevant SDK documentation and code examples.
 */

import { answerBridgingQuestion } from "../openrouter";
import { getBridgingContext } from "./getBridgingContext";

export interface AskBridgingInput {
  question: string;
  includeCodeExample?: boolean;
  questionType?: "general" | "bridging" | "messaging" | "l3";
}

export interface AskBridgingOutput {
  answer: string;
  codeExamples: Array<{
    title: string;
    code: string;
    language: string;
  }>;
  references: string[];
  followUpQuestions: string[];
  tokensUsed: number;
}

// Pre-built knowledge base for fallback and enrichment
const BRIDGING_KNOWLEDGE: Record<string, Record<string, string | string[]>> = {
  eth_bridging: {
    description: "ETH bridging between L1 and L2",
    classes: ["EthBridger"],
    deposit_time: "~10-15 minutes",
    withdraw_time: "~7 days challenge period",
  },
  erc20_bridging: {
    description: "ERC20 token bridging",
    classes: ["Erc20Bridger"],
    steps: ["approveToken()", "deposit()", "wait for L2 confirmation"],
  },
  l1_to_l2_messaging: {
    description: "L1 -> L2 messaging via retryable tickets",
    contracts: ["Inbox", "NodeInterface"],
    time: "~10-15 minutes",
    key_classes: ["ParentTransactionReceipt", "ParentToChildMessageStatus"],
  },
  l2_to_l1_messaging: {
    description: "L2 -> L1 messaging via ArbSys",
    precompile: "ArbSys (0x64)",
    time: "~7 days challenge period",
    key_classes: ["ChildTransactionReceipt", "ChildToParentMessageStatus"],
  },
  l3_bridging: {
    description: "L1 -> L3 bridging for Orbit chains",
    classes: ["EthL1L3Bridger", "Erc20L1L3Bridger"],
    mechanism: "Double retryable tickets (L1->L2->L3)",
  },
};

/**
 * RAG-powered bridging Q&A tool.
 * Uses Vectorize for context retrieval and LLM for answer generation.
 */
export async function askBridging(
  vectorize: VectorizeIndex,
  ai: Ai,
  openrouterApiKey: string,
  input: AskBridgingInput
): Promise<AskBridgingOutput> {
  const { question, questionType = "general" } = input;

  // Build enhanced search query based on question type
  let searchQuery = question;
  if (questionType === "bridging") {
    searchQuery = `arbitrum sdk bridger deposit withdraw ${question}`;
  } else if (questionType === "messaging") {
    searchQuery = `cross-chain messaging retryable arbsys ${question}`;
  } else if (questionType === "l3") {
    searchQuery = `orbit l3 chain EthL1L3Bridger ${question}`;
  }

  // Get relevant context from Vectorize
  const contextResult = await getBridgingContext(vectorize, ai, {
    query: searchQuery,
    nResults: 5,
    rerank: true,
  });

  // Build context string for LLM
  let contextStr = contextResult.contexts
    .map((c, i) => `[${i + 1}] (${c.source})\n${c.content}`)
    .join("\n\n---\n\n");

  // Enrich with knowledge base if relevant topics detected
  const qLower = question.toLowerCase();
  const enrichments: string[] = [];

  if (qLower.includes("eth") && (qLower.includes("deposit") || qLower.includes("withdraw"))) {
    enrichments.push(formatKnowledge("eth_bridging"));
  }
  if (qLower.includes("token") || qLower.includes("erc20")) {
    enrichments.push(formatKnowledge("erc20_bridging"));
  }
  if (qLower.includes("message") || qLower.includes("retryable")) {
    if (qLower.includes("l2 to l1") || qLower.includes("withdraw")) {
      enrichments.push(formatKnowledge("l2_to_l1_messaging"));
    } else {
      enrichments.push(formatKnowledge("l1_to_l2_messaging"));
    }
  }
  if (qLower.includes("l3") || qLower.includes("orbit")) {
    enrichments.push(formatKnowledge("l3_bridging"));
  }

  if (enrichments.length > 0) {
    contextStr = `Quick Reference:\n${enrichments.join("\n")}\n\n---\n\n${contextStr}`;
  }

  // Get answer from LLM
  const response = await answerBridgingQuestion(openrouterApiKey, question, contextStr);

  // Extract code examples from response
  const codeExamples: Array<{ title: string; code: string; language: string }> = [];
  const codeBlockRegex = /```(typescript|javascript|ts|js)?\n([\s\S]*?)```/g;
  let match;
  let exampleIndex = 1;
  while ((match = codeBlockRegex.exec(response.content)) !== null) {
    codeExamples.push({
      title: `Example ${exampleIndex++}`,
      code: match[2].trim(),
      language: match[1] || "typescript",
    });
  }

  // Generate follow-up questions
  const followUpQuestions = generateFollowUpQuestions(question, questionType);

  return {
    answer: response.content
      .replace(/```(?:typescript|javascript|ts|js)?\n[\s\S]*?```/g, "[Code example above]")
      .trim(),
    codeExamples,
    references: contextResult.contexts.map((c) => c.source),
    followUpQuestions,
    tokensUsed: response.usage.totalTokens,
  };
}

function formatKnowledge(topic: string): string {
  const info = BRIDGING_KNOWLEDGE[topic];
  if (!info) return "";

  const lines: string[] = [`**${topic.replace(/_/g, " ").toUpperCase()}**`];
  for (const [key, value] of Object.entries(info)) {
    if (Array.isArray(value)) {
      lines.push(`- ${key}: ${value.join(", ")}`);
    } else {
      lines.push(`- ${key}: ${value}`);
    }
  }
  return lines.join("\n");
}

function generateFollowUpQuestions(question: string, questionType: string): string[] {
  const followUps: Record<string, string[]> = {
    general: [
      "How do I estimate gas for bridging?",
      "What happens if a retryable ticket fails?",
      "How do I track the status of my bridge transaction?",
    ],
    bridging: [
      "How long does it take to bridge tokens?",
      "Do I need to approve tokens before bridging?",
      "How do I withdraw tokens back to L1?",
    ],
    messaging: [
      "How do I send a cross-chain message?",
      "What's the difference between L1->L2 and L2->L1 messaging?",
      "How do I claim an L2->L1 message after the challenge period?",
    ],
    l3: [
      "How does L1->L3 bridging work?",
      "Do I need to handle custom gas tokens for L3?",
      "What are double retryable tickets?",
    ],
  };

  return followUps[questionType] || followUps.general;
}

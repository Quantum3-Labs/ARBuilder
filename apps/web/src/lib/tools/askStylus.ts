/**
 * Ask Stylus Tool
 *
 * Answers questions about Stylus development, debugging,
 * and best practices with context-aware responses.
 */

import { answerQuestion } from "../openrouter";
import { getStylusContext } from "./getStylusContext";

export interface AskStylusInput {
  question: string;
  codeContext?: string;
  questionType?: "general" | "debugging" | "optimization" | "security";
}

export interface AskStylusOutput {
  answer: string;
  codeExamples: Array<{
    title: string;
    code: string;
  }>;
  references: string[];
  followUpQuestions: string[];
  tokensUsed: number;
}

export async function askStylus(
  vectorize: VectorizeIndex,
  ai: Ai,
  openrouterApiKey: string,
  input: AskStylusInput
): Promise<AskStylusOutput> {
  const { question, codeContext, questionType = "general" } = input;

  // Build search query
  let searchQuery = question;
  if (questionType === "debugging") {
    searchQuery = `debugging troubleshooting ${question}`;
  } else if (questionType === "optimization") {
    searchQuery = `optimization performance gas ${question}`;
  } else if (questionType === "security") {
    searchQuery = `security vulnerability audit ${question}`;
  }

  // Get relevant context
  const contextResult = await getStylusContext(vectorize, ai, {
    query: searchQuery,
    nResults: 5,
    rerank: true,
  });

  // Build context string with optional code context
  let contextStr = contextResult.contexts
    .map((c, i) => `[${i + 1}] (${c.source})\n${c.content}`)
    .join("\n\n---\n\n");

  if (codeContext) {
    contextStr = `User's Code:\n\`\`\`rust\n${codeContext}\n\`\`\`\n\n---\n\n${contextStr}`;
  }

  // Get answer from LLM
  const response = await answerQuestion(openrouterApiKey, question, contextStr);

  // Extract code examples from response
  const codeExamples: Array<{ title: string; code: string }> = [];
  const codeBlockRegex = /```rust\n([\s\S]*?)```/g;
  let match;
  let exampleIndex = 1;
  while ((match = codeBlockRegex.exec(response.content)) !== null) {
    codeExamples.push({
      title: `Example ${exampleIndex++}`,
      code: match[1].trim(),
    });
  }

  // Generate follow-up questions based on the topic
  const followUpQuestions = generateFollowUpQuestions(question, questionType);

  return {
    answer: response.content
      .replace(/```rust\n[\s\S]*?```/g, "[Code example above]")
      .trim(),
    codeExamples,
    references: contextResult.contexts.map((c) => c.source),
    followUpQuestions,
    tokensUsed: response.usage.totalTokens,
  };
}

function generateFollowUpQuestions(
  question: string,
  questionType: string
): string[] {
  const commonFollowUps: Record<string, string[]> = {
    general: [
      "How can I test this implementation?",
      "What are the gas implications?",
      "How does this compare to Solidity?",
    ],
    debugging: [
      "How can I add logging for debugging?",
      "What tools can I use to trace transactions?",
      "How do I decode error messages?",
    ],
    optimization: [
      "What are the storage costs?",
      "How can I reduce contract size?",
      "What's the most gas-efficient approach?",
    ],
    security: [
      "What are common vulnerabilities to avoid?",
      "How do I handle reentrancy?",
      "Should I add access controls?",
    ],
  };

  return commonFollowUps[questionType] || commonFollowUps.general;
}

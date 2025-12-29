/**
 * OpenRouter API client for LLM calls.
 *
 * Uses DeepSeek for code generation and Gemini for Q&A.
 */

const OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions";

export interface Message {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface ChatCompletionOptions {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  stream?: boolean;
}

export interface ChatCompletionResponse {
  content: string;
  model: string;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

// Default models
export const MODELS = {
  CODE_GEN: "deepseek/deepseek-chat",
  QA: "google/gemini-3-flash-preview",
  FAST: "google/gemini-2.5-flash-lite",
} as const;

/**
 * Call OpenRouter API for chat completions.
 */
export async function chatCompletion(
  apiKey: string,
  messages: Message[],
  options: ChatCompletionOptions = {}
): Promise<ChatCompletionResponse> {
  const {
    model = MODELS.CODE_GEN,
    temperature = 0.2,
    maxTokens = 4096,
    stream = false,
  } = options;

  const response = await fetch(OPENROUTER_API_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://arbbuilder.whymelabs.com",
      "X-Title": "ARBuilder",
    },
    body: JSON.stringify({
      model,
      messages,
      temperature,
      max_tokens: maxTokens,
      stream,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`OpenRouter API error: ${response.status} - ${error}`);
  }

  const data = (await response.json()) as {
    choices: Array<{ message?: { content?: string } }>;
    model: string;
    usage?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
  };

  return {
    content: data.choices[0]?.message?.content ?? "",
    model: data.model,
    usage: {
      promptTokens: data.usage?.prompt_tokens ?? 0,
      completionTokens: data.usage?.completion_tokens ?? 0,
      totalTokens: data.usage?.total_tokens ?? 0,
    },
  };
}

/**
 * Generate Stylus code using DeepSeek.
 */
export async function generateCode(
  apiKey: string,
  prompt: string,
  context: string
): Promise<ChatCompletionResponse> {
  const messages: Message[] = [
    {
      role: "system",
      content: `You are an expert Stylus (Rust) smart contract developer for Arbitrum.
You write clean, secure, and gas-efficient code following best practices.
Use the provided context from the Stylus documentation and examples.

Important:
- Use stylus-sdk 0.8.4 with alloy-primitives 0.8.14
- Include #![cfg_attr(not(feature = "export-abi"), no_main)]
- Use sol_storage! macro for storage
- Use #[public] for external functions
- Handle errors with Result<T, Vec<u8>>`,
    },
    {
      role: "user",
      content: `Context from documentation:\n${context}\n\n---\n\nTask: ${prompt}`,
    },
  ];

  return chatCompletion(apiKey, messages, {
    model: MODELS.CODE_GEN,
    temperature: 0.2,
  });
}

/**
 * Answer questions about Stylus development.
 */
export async function answerQuestion(
  apiKey: string,
  question: string,
  context: string
): Promise<ChatCompletionResponse> {
  const messages: Message[] = [
    {
      role: "system",
      content: `You are a helpful Stylus development assistant.
Answer questions about Stylus smart contract development on Arbitrum.
Use the provided context to give accurate, up-to-date answers.
Include code examples when relevant.
Be concise but thorough.`,
    },
    {
      role: "user",
      content: `Context from documentation:\n${context}\n\n---\n\nQuestion: ${question}`,
    },
  ];

  return chatCompletion(apiKey, messages, {
    model: MODELS.QA,
    temperature: 0.3,
  });
}

/**
 * Generate tests for Stylus contract code.
 */
export async function generateTests(
  apiKey: string,
  contractCode: string,
  testFramework: "rust_native" | "foundry" = "rust_native"
): Promise<ChatCompletionResponse> {
  const messages: Message[] = [
    {
      role: "system",
      content: `You are a Stylus testing expert.
Generate comprehensive tests for the provided contract.
Framework: ${testFramework === "rust_native" ? "Rust native #[test] with stylus-test" : "Foundry Solidity tests"}

For Rust native tests:
- Use #[cfg(test)] module
- Import stylus_sdk::testing if needed
- Test all public functions
- Include edge cases and error conditions

For Foundry tests:
- Create Solidity interface matching the contract ABI
- Use forge-std Test contract
- Mock contract deployment`,
    },
    {
      role: "user",
      content: `Generate tests for this contract:\n\n\`\`\`rust\n${contractCode}\n\`\`\``,
    },
  ];

  return chatCompletion(apiKey, messages, {
    model: MODELS.CODE_GEN,
    temperature: 0.2,
  });
}

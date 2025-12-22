/**
 * Generate Tests Tool
 *
 * Generates test suites for Stylus contracts, supporting
 * both Rust native tests and Foundry integration tests.
 */

import { generateTests as generateTestsLLM } from "../openrouter";

export interface GenerateTestsInput {
  contractCode: string;
  testFramework?: "rust_native" | "foundry";
  testTypes?: Array<"unit" | "integration" | "fuzz">;
  coverageFocus?: string[];
}

export interface GenerateTestsOutput {
  tests: string;
  testSummary: {
    totalTests: number;
    unitTests: number;
    integrationTests: number;
    fuzzTests: number;
  };
  coverageEstimate: {
    functionsCovered: string[];
    functionsNotCovered: string[];
    edgeCases: string[];
  };
  setupInstructions: string;
  tokensUsed: number;
}

export async function generateTests(
  openrouterApiKey: string,
  input: GenerateTestsInput
): Promise<GenerateTestsOutput> {
  const {
    contractCode,
    testFramework = "rust_native",
    // testTypes and coverageFocus reserved for future advanced test generation
  } = input;

  // Generate tests using LLM
  const response = await generateTestsLLM(
    openrouterApiKey,
    contractCode,
    testFramework
  );

  // Extract test code
  const testMatch = response.content.match(/```(?:rust|solidity)\n([\s\S]*?)```/);
  const tests = testMatch ? testMatch[1].trim() : response.content;

  // Analyze generated tests
  const testCount = (tests.match(/#\[test\]/g) || []).length;
  const fuzzCount = (tests.match(/#\[test\].*fuzz/gi) || []).length;

  // Extract function names from contract code
  const functionNames = extractFunctionNames(contractCode);
  const testedFunctions = functionNames.filter((fn) =>
    tests.toLowerCase().includes(fn.toLowerCase())
  );
  const untestedFunctions = functionNames.filter(
    (fn) => !tests.toLowerCase().includes(fn.toLowerCase())
  );

  // Detect edge cases tested
  const edgeCases: string[] = [];
  if (tests.includes("zero") || tests.includes("0")) edgeCases.push("Zero values");
  if (tests.includes("overflow")) edgeCases.push("Overflow handling");
  if (tests.includes("underflow")) edgeCases.push("Underflow handling");
  if (tests.includes("error") || tests.includes("Err")) edgeCases.push("Error conditions");
  if (tests.includes("empty")) edgeCases.push("Empty inputs");

  // Generate setup instructions
  const setupInstructions =
    testFramework === "rust_native"
      ? generateRustTestInstructions()
      : generateFoundryTestInstructions();

  return {
    tests,
    testSummary: {
      totalTests: testCount,
      unitTests: testCount - fuzzCount,
      integrationTests: 0,
      fuzzTests: fuzzCount,
    },
    coverageEstimate: {
      functionsCovered: testedFunctions,
      functionsNotCovered: untestedFunctions,
      edgeCases,
    },
    setupInstructions,
    tokensUsed: response.usage.totalTokens,
  };
}

function extractFunctionNames(code: string): string[] {
  const functionRegex = /pub\s+fn\s+(\w+)/g;
  const names: string[] = [];
  let match;
  while ((match = functionRegex.exec(code)) !== null) {
    names.push(match[1]);
  }
  return names;
}

function generateRustTestInstructions(): string {
  return `# Running Rust Tests

1. Ensure your Cargo.toml has test dependencies:
\`\`\`toml
[dev-dependencies]
stylus-sdk = { version = "0.8.4", features = ["stylus-test"] }
\`\`\`

2. Run tests:
\`\`\`bash
cargo test
\`\`\`

3. Run with output:
\`\`\`bash
cargo test -- --nocapture
\`\`\`

4. Run specific test:
\`\`\`bash
cargo test test_function_name
\`\`\``;
}

function generateFoundryTestInstructions(): string {
  return `# Running Foundry Tests

1. Install Foundry:
\`\`\`bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
\`\`\`

2. Export ABI:
\`\`\`bash
cargo stylus export-abi > abi.json
\`\`\`

3. Create test file in \`test/\` directory

4. Run tests:
\`\`\`bash
forge test --fork-url <RPC_URL>
\`\`\``;
}

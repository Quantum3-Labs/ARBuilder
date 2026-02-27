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

  // Generate tests using LLM (chatCompletion retries 3x on empty)
  const response = await generateTestsLLM(
    openrouterApiKey,
    contractCode,
    testFramework
  );

  // Extract test code
  const testMatch = response.content.match(/```(?:rust|solidity)\n([\s\S]*?)```/);
  let tests = testMatch ? testMatch[1].trim() : response.content.trim();

  // Fallback: if LLM returned empty after all retries, generate skeleton
  if (!tests) {
    const contractName = extractContractName(contractCode);
    tests = testFramework === "rust_native"
      ? generateSkeletonRustTests(contractName, contractCode)
      : `// LLM did not generate tests. Please retry or write tests manually.`;
  }

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
  return `# Running Rust Tests (stylus-sdk 0.10.0)

1. Ensure your Cargo.toml has test dependencies:
\`\`\`toml
[dev-dependencies]
stylus-sdk = { version = "0.10.0", features = ["stylus-test"] }
\`\`\`

2. Run tests (use --target to run on host, not WASM):
\`\`\`bash
cargo test --target=x86_64-unknown-linux-gnu
\`\`\`
Or on macOS:
\`\`\`bash
cargo test --target=aarch64-apple-darwin
\`\`\`

3. Run with output:
\`\`\`bash
cargo test --target=x86_64-unknown-linux-gnu -- --nocapture
\`\`\`

4. Run specific test:
\`\`\`bash
cargo test --target=x86_64-unknown-linux-gnu test_function_name
\`\`\`

Note: The --target flag is needed because Stylus contracts compile to
wasm32-unknown-unknown by default (via rust-toolchain.toml), but tests
must run on the host platform. TestVM simulates the Stylus environment.`;
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
\`\`\`

5. Run with verbosity:
\`\`\`bash
forge test -vvv
\`\`\`

6. Run specific test:
\`\`\`bash
forge test --match-test test_function_name
\`\`\``;
}

function extractContractName(code: string): string {
  const match = code.match(/pub\s+struct\s+(\w+)/);
  return match ? match[1] : "MyContract";
}

function generateSkeletonRustTests(contractName: string, code: string): string {
  const fns = extractFunctionNames(code);
  const testFns = fns
    .filter((f) => f !== "new" && f !== "default")
    .map(
      (f) =>
        "    #[test]\n    fn test_" + f + "() {\n" +
        "        let vm = TestVM::default();\n" +
        "        let mut contract = " + contractName + "::from(&vm);\n" +
        "        // TODO: test " + f + "()\n    }"
    )
    .join("\n\n");

  const fallbackTest =
    "    #[test]\n    fn test_basic() {\n" +
    "        let vm = TestVM::default();\n" +
    "        let contract = " + contractName + "::from(&vm);\n" +
    "        // TODO: add test assertions\n    }";

  return "#[cfg(test)]\nmod tests {\n    use super::*;\n    use stylus_sdk::testing::*;\n\n" +
    (testFns || fallbackTest) + "\n}";
}

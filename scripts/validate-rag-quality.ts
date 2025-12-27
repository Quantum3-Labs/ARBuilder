/**
 * Quality gate validation for RAG knowledge base.
 *
 * Runs a series of test queries against the Vectorize index
 * to ensure current SDK patterns are properly indexed.
 *
 * Usage:
 * AUTH_SECRET=xxx npx tsx scripts/validate-rag-quality.ts
 */

import { readFileSync, existsSync } from "fs";
import { join } from "path";

// Configuration
const API_URL =
  process.env.API_URL || "https://arbbuilder.whymelabs.com";
const AUTH_SECRET = process.env.AUTH_SECRET!;
const STATE_DIR = "./.rag-state";
const SDK_VERSION_FILE = join(STATE_DIR, "sdk_version");

// Quality test definition
interface QualityTest {
  name: string;
  query: string;
  expectedPatterns: string[];
  mustNotInclude?: string[];
  minResults?: number;
}

// Test results
interface TestResult {
  name: string;
  passed: boolean;
  errors: string[];
  matchedPatterns: string[];
  foundDeprecated: string[];
}

// Define quality tests
const QUALITY_TESTS: QualityTest[] = [
  {
    name: "Current SDK version in Cargo.toml",
    query: "stylus-sdk dependency Cargo.toml version",
    expectedPatterns: ['stylus-sdk = "0.'],
    mustNotInclude: ['stylus-sdk = "0.5.', 'stylus-sdk = "0.4.'],
    minResults: 3,
  },
  {
    name: "Public attribute usage",
    query: "public function Stylus contract attribute",
    expectedPatterns: ["#[public]"],
    mustNotInclude: ["#[external]"],
    minResults: 2,
  },
  {
    name: "Entrypoint attribute",
    query: "entrypoint Stylus contract main",
    expectedPatterns: ["#[entrypoint]"],
    minResults: 2,
  },
  {
    name: "Storage macro usage",
    query: "sol_storage macro Stylus storage",
    expectedPatterns: ["sol_storage!"],
    minResults: 2,
  },
  {
    name: "Error handling patterns",
    query: "error handling Result Stylus contract",
    expectedPatterns: ["Result<"],
    minResults: 1,
  },
  {
    name: "Alloy types usage",
    query: "alloy primitives U256 Address Stylus",
    expectedPatterns: ["alloy"],
    minResults: 1,
  },
];

// Search context endpoint
interface ContextResult {
  contexts: Array<{
    content: string;
    metadata: Record<string, unknown>;
    score: number;
  }>;
}

async function searchContext(query: string): Promise<ContextResult> {
  const response = await fetch(`${API_URL}/api/v1/tools/context`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${AUTH_SECRET}`,
    },
    body: JSON.stringify({
      query,
      nResults: 10,
      contentType: "all",
      rerank: true,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Search failed: ${response.status} - ${error}`);
  }

  return response.json();
}

async function runTest(test: QualityTest): Promise<TestResult> {
  const result: TestResult = {
    name: test.name,
    passed: true,
    errors: [],
    matchedPatterns: [],
    foundDeprecated: [],
  };

  try {
    const searchResult = await searchContext(test.query);
    const contexts = searchResult.contexts || [];

    // Check minimum results
    if (test.minResults && contexts.length < test.minResults) {
      result.passed = false;
      result.errors.push(
        `Expected at least ${test.minResults} results, got ${contexts.length}`
      );
    }

    // Combine all content for pattern matching
    const allContent = contexts.map((c) => c.content).join("\n");

    // Check expected patterns
    for (const pattern of test.expectedPatterns) {
      if (allContent.includes(pattern)) {
        result.matchedPatterns.push(pattern);
      } else {
        result.passed = false;
        result.errors.push(`Expected pattern not found: ${pattern}`);
      }
    }

    // Check must-not-include patterns
    if (test.mustNotInclude) {
      for (const pattern of test.mustNotInclude) {
        if (allContent.includes(pattern)) {
          result.passed = false;
          result.foundDeprecated.push(pattern);
          result.errors.push(`Found deprecated pattern: ${pattern}`);
        }
      }
    }
  } catch (err) {
    result.passed = false;
    result.errors.push(`Test error: ${err}`);
  }

  return result;
}

async function validateQuality(): Promise<void> {
  console.log("=".repeat(60));
  console.log("RAG Knowledge Base Quality Validation");
  console.log("=".repeat(60));
  console.log(`Target: ${API_URL}`);
  console.log(`Running ${QUALITY_TESTS.length} quality tests\n`);

  // Load expected SDK version if available
  let expectedSdkVersion: string | null = null;
  if (existsSync(SDK_VERSION_FILE)) {
    expectedSdkVersion = readFileSync(SDK_VERSION_FILE, "utf-8").trim();
    console.log(`Expected SDK version: ${expectedSdkVersion}\n`);
  }

  // Run all tests
  const results: TestResult[] = [];
  let passed = 0;
  let failed = 0;

  for (const test of QUALITY_TESTS) {
    process.stdout.write(`Testing: ${test.name}... `);

    const result = await runTest(test);
    results.push(result);

    if (result.passed) {
      console.log("PASS");
      passed++;
    } else {
      console.log("FAIL");
      for (const error of result.errors) {
        console.log(`  - ${error}`);
      }
      failed++;
    }

    // Rate limit
    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  // Print summary
  console.log(`\n${"=".repeat(60)}`);
  console.log("Summary");
  console.log("=".repeat(60));
  console.log(`Passed: ${passed}/${QUALITY_TESTS.length}`);
  console.log(`Failed: ${failed}/${QUALITY_TESTS.length}`);

  if (failed > 0) {
    console.log("\nFailed tests:");
    for (const result of results) {
      if (!result.passed) {
        console.log(`  - ${result.name}`);
        for (const error of result.errors) {
          console.log(`      ${error}`);
        }
      }
    }
  }

  // Print deprecated patterns found
  const allDeprecated = results.flatMap((r) => r.foundDeprecated);
  if (allDeprecated.length > 0) {
    console.log("\nDeprecated patterns found in results:");
    for (const pattern of [...new Set(allDeprecated)]) {
      console.log(`  - ${pattern}`);
    }
  }

  // Exit with error code if any tests failed
  if (failed > 0) {
    console.log("\nQuality validation FAILED!");
    process.exit(1);
  } else {
    console.log("\nAll quality checks PASSED!");
  }
}

// Run validation
validateQuality().catch((err) => {
  console.error("Validation failed:", err);
  process.exit(1);
});

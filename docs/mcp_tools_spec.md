# ARBuilder MCP Tools Specification

## Overview

This document defines the capabilities, input/output specifications, and expected behaviors for the ARBuilder MCP tools. These tools provide AI-powered assistance for Arbitrum Stylus smart contract development.

## Tool 1: `get_stylus_context`

### Purpose
Retrieve relevant documentation and code examples from the RAG database to provide context for development tasks.

### Input Schema
```json
{
  "query": {
    "type": "string",
    "required": true,
    "description": "The search query (concept, function name, or code pattern)"
  },
  "n_results": {
    "type": "integer",
    "required": false,
    "default": 5,
    "min": 1,
    "max": 20,
    "description": "Number of results to return"
  },
  "content_type": {
    "type": "string",
    "required": false,
    "enum": ["all", "docs", "code"],
    "default": "all",
    "description": "Filter by content type"
  },
  "rerank": {
    "type": "boolean",
    "required": false,
    "default": true,
    "description": "Whether to rerank results for relevance"
  }
}
```

### Output Schema
```json
{
  "contexts": [
    {
      "content": "string - The actual content",
      "source": "string - File path or URL",
      "type": "string - 'docs' or 'code'",
      "relevance_score": "float - 0.0 to 1.0",
      "metadata": {
        "title": "string - Document/file title",
        "language": "string - Programming language if code"
      }
    }
  ],
  "total_results": "integer",
  "query": "string - Original query"
}
```

### Expected Behaviors
1. **Semantic Search**: Should find relevant content even when exact keywords don't match
2. **Code Understanding**: Should recognize code patterns and return similar implementations
3. **Documentation Matching**: Should match conceptual queries to relevant docs
4. **Filtering**: Should properly filter by content type when specified
5. **Ranking**: Reranked results should have higher relevance in top positions

### Capability Matrix

| Capability | Priority | Description |
|------------|----------|-------------|
| Basic keyword search | P0 | Find exact keyword matches |
| Semantic search | P0 | Find semantically similar content |
| Code snippet retrieval | P0 | Return complete, usable code snippets |
| Documentation retrieval | P0 | Return relevant documentation sections |
| Cross-reference | P1 | Link related docs and code examples |
| Filter by type | P1 | Support docs-only or code-only queries |
| Reranking | P1 | Improve result relevance via reranking |

---

## Tool 2: `generate_stylus_code`

### Purpose
Generate Stylus/Rust smart contract code based on user requirements and retrieved context.

### Input Schema
```json
{
  "prompt": {
    "type": "string",
    "required": true,
    "description": "Description of the code to generate"
  },
  "context_query": {
    "type": "string",
    "required": false,
    "description": "Optional query to retrieve additional context"
  },
  "contract_type": {
    "type": "string",
    "required": false,
    "enum": ["erc20", "erc721", "erc1155", "custom"],
    "description": "Type of contract to generate"
  },
  "include_tests": {
    "type": "boolean",
    "required": false,
    "default": false,
    "description": "Whether to include unit tests"
  },
  "temperature": {
    "type": "float",
    "required": false,
    "default": 0.2,
    "min": 0.0,
    "max": 1.0,
    "description": "Generation temperature (lower = more deterministic)"
  }
}
```

### Output Schema
```json
{
  "code": "string - Generated Rust/Stylus code",
  "explanation": "string - Explanation of the generated code",
  "dependencies": [
    {
      "name": "string - Crate name",
      "version": "string - Version constraint"
    }
  ],
  "warnings": ["string - Any warnings or caveats"],
  "context_used": [
    {
      "source": "string",
      "relevance": "float"
    }
  ]
}
```

### Expected Behaviors
1. **Valid Syntax**: Generated code must be syntactically valid Rust
2. **Stylus Patterns**: Should use correct Stylus SDK patterns (sol_storage!, #[entrypoint], etc.)
3. **Complete Code**: Should generate complete, compilable modules
4. **Best Practices**: Should follow Stylus/Rust best practices
5. **Context Integration**: Should incorporate retrieved context appropriately

### Capability Matrix

| Capability | Priority | Description |
|------------|----------|-------------|
| Basic contract generation | P0 | Generate simple Stylus contracts |
| ERC20 implementation | P0 | Generate standard token contracts |
| ERC721 implementation | P1 | Generate NFT contracts |
| Storage patterns | P0 | Use correct sol_storage! macro patterns |
| Error handling | P0 | Include proper error handling |
| Events/logging | P1 | Include event emissions |
| Access control | P1 | Implement ownership/access control |
| Gas optimization hints | P2 | Suggest gas optimizations |

---

## Tool 3: `ask_stylus`

### Purpose
Answer questions about Stylus development, explain concepts, debug issues, and provide guidance.

### Input Schema
```json
{
  "question": {
    "type": "string",
    "required": true,
    "description": "The question or topic to explain"
  },
  "code_context": {
    "type": "string",
    "required": false,
    "description": "Code snippet for context (e.g., for debugging)"
  },
  "question_type": {
    "type": "string",
    "required": false,
    "enum": ["concept", "debugging", "comparison", "howto", "general"],
    "default": "general",
    "description": "Type of question for optimized response"
  }
}
```

### Output Schema
```json
{
  "answer": "string - The answer/explanation",
  "code_examples": [
    {
      "description": "string",
      "code": "string"
    }
  ],
  "references": [
    {
      "title": "string",
      "source": "string",
      "relevance": "string - why this is relevant"
    }
  ],
  "follow_up_questions": ["string - Suggested follow-up questions"]
}
```

### Expected Behaviors
1. **Accurate Information**: Answers should be factually correct about Stylus
2. **Code Examples**: Should include relevant code examples when helpful
3. **Debugging Help**: Should identify issues in provided code
4. **Clear Explanations**: Should explain concepts clearly for different skill levels
5. **Source References**: Should cite relevant documentation

### Capability Matrix

| Capability | Priority | Description |
|------------|----------|-------------|
| Concept explanation | P0 | Explain Stylus concepts clearly |
| Code debugging | P0 | Identify and explain errors in code |
| Best practice guidance | P0 | Recommend best practices |
| Comparison (Stylus vs Solidity) | P1 | Compare with Solidity equivalents |
| Architecture advice | P1 | Suggest contract architecture |
| Gas analysis | P2 | Analyze gas implications |
| Security review | P2 | Basic security suggestions |

---

## Tool 4: `generate_tests`

### Purpose
Generate test cases for Stylus smart contracts.

### Input Schema
```json
{
  "contract_code": {
    "type": "string",
    "required": true,
    "description": "The contract code to generate tests for"
  },
  "test_framework": {
    "type": "string",
    "required": false,
    "enum": ["rust_native", "foundry", "hardhat"],
    "default": "rust_native",
    "description": "Test framework to use"
  },
  "test_types": {
    "type": "array",
    "required": false,
    "items": {"type": "string", "enum": ["unit", "integration", "fuzz"]},
    "default": ["unit"],
    "description": "Types of tests to generate"
  },
  "coverage_focus": {
    "type": "array",
    "required": false,
    "items": {"type": "string"},
    "description": "Specific functions to focus on"
  }
}
```

### Output Schema
```json
{
  "tests": "string - Generated test code",
  "test_summary": {
    "total_tests": "integer",
    "unit_tests": "integer",
    "integration_tests": "integer",
    "fuzz_tests": "integer"
  },
  "coverage_estimate": {
    "functions_covered": ["string"],
    "functions_not_covered": ["string"],
    "edge_cases": ["string - Edge cases tested"]
  },
  "setup_instructions": "string - How to run the tests"
}
```

### Expected Behaviors
1. **Valid Tests**: Generated tests should compile and run
2. **Comprehensive Coverage**: Should cover main functionality and edge cases
3. **Test Patterns**: Should use appropriate testing patterns
4. **Clear Assertions**: Should have clear, meaningful assertions
5. **Setup/Teardown**: Should include proper test setup when needed

### Capability Matrix

| Capability | Priority | Description |
|------------|----------|-------------|
| Unit test generation | P0 | Generate basic unit tests |
| Happy path tests | P0 | Test normal execution paths |
| Error case tests | P0 | Test error conditions |
| Edge case tests | P1 | Test boundary conditions |
| Fuzz test generation | P2 | Generate property-based tests |
| Integration tests | P2 | Generate multi-contract tests |
| Gas benchmarks | P2 | Generate gas measurement tests |

---

## Quality Requirements

### Response Time
- `get_stylus_context`: < 2 seconds (P0)
- `generate_stylus_code`: < 10 seconds (P0)
- `ask_stylus`: < 5 seconds (P0)
- `generate_tests`: < 10 seconds (P0)

### Accuracy Metrics
- **Retrieval Recall@5**: >= 0.80 (get_stylus_context)
- **Code Validity**: >= 95% syntactically valid (generate_stylus_code)
- **Answer Accuracy**: >= 90% factually correct (ask_stylus)
- **Test Validity**: >= 90% compilable tests (generate_tests)

### Error Handling
All tools must:
1. Return structured error responses for invalid inputs
2. Handle rate limits gracefully
3. Provide fallback behavior when context is unavailable
4. Log errors for debugging

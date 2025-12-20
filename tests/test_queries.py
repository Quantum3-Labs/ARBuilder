"""
Test queries for evaluating retrieval and reranking quality.

These queries are designed to test different aspects of the RAG system:
1. Basic factual queries
2. Code-related queries
3. Concept explanation queries
4. Multi-hop reasoning queries
"""

# Test queries with expected relevant content indicators
TEST_QUERIES = [
    # Basic Stylus queries
    {
        "query": "How do I create a new Stylus project?",
        "category": "stylus",
        "expected_keywords": ["cargo", "stylus", "new", "project", "init"],
        "difficulty": "basic",
    },
    {
        "query": "What is the Stylus SDK?",
        "category": "stylus",
        "expected_keywords": ["stylus-sdk", "rust", "arbitrum", "wasm"],
        "difficulty": "basic",
    },
    {
        "query": "How do I deploy a Stylus contract?",
        "category": "stylus",
        "expected_keywords": ["deploy", "cargo", "stylus", "check", "rpc"],
        "difficulty": "basic",
    },

    # Code-specific queries
    {
        "query": "Show me an example of an ERC20 token in Stylus",
        "category": "stylus",
        "expected_keywords": ["erc20", "token", "transfer", "balance", "sol_storage"],
        "difficulty": "intermediate",
    },
    {
        "query": "How do I use storage in Stylus contracts?",
        "category": "stylus",
        "expected_keywords": ["StorageVec", "StorageMap", "sol_storage", "storage"],
        "difficulty": "intermediate",
    },
    {
        "query": "What is the entrypoint macro in Stylus?",
        "category": "stylus",
        "expected_keywords": ["entrypoint", "macro", "#[entrypoint]", "contract"],
        "difficulty": "intermediate",
    },

    # Advanced concept queries
    {
        "query": "How does Stylus achieve gas efficiency compared to Solidity?",
        "category": "stylus",
        "expected_keywords": ["gas", "wasm", "efficient", "cheaper", "compute"],
        "difficulty": "advanced",
    },
    {
        "query": "Can Stylus contracts interact with Solidity contracts?",
        "category": "stylus",
        "expected_keywords": ["interop", "solidity", "call", "abi", "interface"],
        "difficulty": "advanced",
    },
    {
        "query": "What are the limitations of Stylus?",
        "category": "stylus",
        "expected_keywords": ["limitation", "wasm", "memory", "constraint"],
        "difficulty": "advanced",
    },

    # Arbitrum SDK queries
    {
        "query": "How do I bridge ETH from Ethereum to Arbitrum?",
        "category": "arbitrum_sdk",
        "expected_keywords": ["bridge", "eth", "deposit", "l1", "l2"],
        "difficulty": "basic",
    },
    {
        "query": "What is the EthBridger class?",
        "category": "arbitrum_sdk",
        "expected_keywords": ["EthBridger", "deposit", "withdraw", "bridge"],
        "difficulty": "intermediate",
    },
    {
        "query": "How do I send a message from L1 to L2?",
        "category": "arbitrum_sdk",
        "expected_keywords": ["message", "l1", "l2", "inbox", "retryable"],
        "difficulty": "intermediate",
    },

    # Orbit SDK queries
    {
        "query": "How do I deploy an Orbit chain?",
        "category": "orbit_sdk",
        "expected_keywords": ["orbit", "deploy", "chain", "rollup", "config"],
        "difficulty": "advanced",
    },
    {
        "query": "What is a custom gas token in Orbit?",
        "category": "orbit_sdk",
        "expected_keywords": ["gas", "token", "custom", "native", "orbit"],
        "difficulty": "advanced",
    },

    # OpenZeppelin Stylus queries
    {
        "query": "How do I use OpenZeppelin contracts with Stylus?",
        "category": "stylus",
        "expected_keywords": ["openzeppelin", "contracts", "erc", "ownable", "access"],
        "difficulty": "intermediate",
    },
]


def get_queries_by_difficulty(difficulty: str) -> list[dict]:
    """Get queries filtered by difficulty level."""
    return [q for q in TEST_QUERIES if q["difficulty"] == difficulty]


def get_queries_by_category(category: str) -> list[dict]:
    """Get queries filtered by category."""
    return [q for q in TEST_QUERIES if q["category"] == category]

"""
Query rewriting module for ARBuilder.
Enhances retrieval by expanding and reformulating queries.

SOTA Techniques Implemented:
1. HyDE (Hypothetical Document Embeddings) - Generate hypothetical answers
2. Multi-Query - Generate diverse query variants
3. Step-Back Questions - Generate higher-level concept queries
4. Query Decomposition - Break complex queries into sub-queries

References:
- https://arxiv.org/html/2411.13154v1 (DMQR-RAG)
- https://www.nomidl.com/generative-ai/revolutionizing-uery-rewrite-and-extension-rag-advanced-approach-with-hyde/
"""

import os
from typing import Optional

import httpx
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek/deepseek-chat")


class QueryRewriter:
    """
    Rewrites user queries to improve retrieval quality.

    Techniques:
    1. Query expansion - Add related terms and synonyms
    2. Intent classification - Understand what the user wants
    3. Multi-query generation - Generate multiple search perspectives
    4. Domain-specific enhancement - Add Arbitrum/dApp context
    """

    # Domain-specific term expansions
    DOMAIN_EXPANSIONS = {
        # Stylus/Rust terms
        "contract": ["smart contract", "stylus", "rust", "sol_storage"],
        "erc20": ["token", "erc-20", "fungible", "transfer", "balance", "approve"],
        "erc721": ["nft", "erc-721", "non-fungible", "mint", "ownerOf", "tokenURI"],
        "storage": ["sol_storage!", "StorageMap", "StorageVec", "state"],

        # Backend terms
        "backend": ["api", "server", "nestjs", "express", "route", "controller"],
        "api": ["endpoint", "route", "rest", "graphql", "controller"],
        "database": ["db", "postgres", "mongodb", "schema", "model", "entity"],
        "auth": ["authentication", "authorization", "jwt", "session", "oauth"],

        # Frontend terms
        "frontend": ["ui", "react", "next.js", "component", "page"],
        "wallet": ["wagmi", "viem", "rainbowkit", "connect", "web3"],
        "hook": ["useAccount", "useContractRead", "useContractWrite", "useState"],
        "component": ["react", "tsx", "jsx", "ui", "daisyui"],

        # Indexer terms
        "indexer": ["subgraph", "the graph", "event", "handler", "entity"],
        "subgraph": ["graphql", "schema", "mapping", "event handler"],
        "event": ["emit", "log", "handler", "subscription"],

        # Oracle terms
        "oracle": ["chainlink", "price feed", "data feed", "aggregator"],
        "price": ["oracle", "feed", "chainlink", "aggregator"],

        # Arbitrum terms
        "arbitrum": ["l2", "layer 2", "rollup", "stylus", "orbit"],
        "bridge": ["cross-chain", "l1", "l2", "deposit", "withdraw"],
        "deploy": ["deployment", "cargo stylus", "testnet", "mainnet"],
    }

    # Intent patterns for classification
    INTENT_PATTERNS = {
        "generate_code": ["create", "generate", "build", "make", "write", "implement"],
        "explain": ["what is", "how does", "explain", "why", "understand"],
        "debug": ["error", "fix", "debug", "issue", "problem", "not working"],
        "example": ["example", "sample", "show me", "demo", "template"],
        "compare": ["vs", "versus", "difference", "compare", "better"],
        "integrate": ["integrate", "connect", "combine", "with", "together"],
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        """
        Initialize the query rewriter.

        Args:
            api_key: OpenRouter API key.
            model: Model to use for rewriting.
            base_url: API base URL.
        """
        self.api_key = api_key or OPENROUTER_API_KEY
        self.model = model or DEFAULT_MODEL
        self.base_url = base_url

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")

        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/arbbuilder",
                "X-Title": "ARBuilder",
            },
            timeout=30.0,
        )

    def expand_query(self, query: str) -> str:
        """
        Expand query with domain-specific terms.

        Args:
            query: Original query.

        Returns:
            Expanded query string.
        """
        query_lower = query.lower()
        expansions = []

        for term, related in self.DOMAIN_EXPANSIONS.items():
            if term in query_lower:
                # Add a few related terms
                expansions.extend(related[:2])

        if expansions:
            # Deduplicate and filter terms already in query
            unique_expansions = [
                exp for exp in set(expansions)
                if exp.lower() not in query_lower
            ]
            if unique_expansions:
                return f"{query} ({' '.join(unique_expansions[:4])})"

        return query

    def classify_intent(self, query: str) -> str:
        """
        Classify the intent of a query.

        Args:
            query: User query.

        Returns:
            Intent classification.
        """
        query_lower = query.lower()

        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in query_lower:
                    return intent

        return "general"

    def generate_search_queries(self, query: str, num_queries: int = 3) -> list[str]:
        """
        Generate multiple search queries from different perspectives.

        Args:
            query: Original query.
            num_queries: Number of queries to generate.

        Returns:
            List of search queries.
        """
        queries = [query]  # Always include original

        # Add expanded version
        expanded = self.expand_query(query)
        if expanded != query:
            queries.append(expanded)

        # Determine intent and add intent-specific query
        intent = self.classify_intent(query)

        if intent == "generate_code":
            queries.append(f"code example {query}")
        elif intent == "explain":
            queries.append(f"documentation {query}")
        elif intent == "debug":
            queries.append(f"error solution {query}")
        elif intent == "example":
            queries.append(f"implementation {query}")
        elif intent == "integrate":
            queries.append(f"integration pattern {query}")

        return queries[:num_queries]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def rewrite_with_llm(
        self,
        query: str,
        context: Optional[str] = None,
    ) -> dict:
        """
        Use LLM to intelligently rewrite the query.

        Args:
            query: Original query.
            context: Optional context about user's task.

        Returns:
            Dict with rewritten query and metadata.
        """
        context_str = f"\nContext: {context}" if context else ""

        prompt = f"""You are a search query optimizer for a developer tool that helps build Arbitrum dApps.

Given a user query, rewrite it to improve retrieval of relevant code and documentation.

User Query: {query}{context_str}

Consider:
1. Add relevant technical terms (Stylus, wagmi, subgraph, etc.)
2. Clarify ambiguous terms
3. Expand abbreviations
4. Focus on the core technical need

Respond with a JSON object:
{{
    "rewritten_query": "optimized search query",
    "search_terms": ["term1", "term2", "term3"],
    "intent": "generate|explain|debug|example|integrate|general",
    "category": "stylus|backend|frontend|indexer|oracle|general"
}}

Only respond with the JSON, no other text."""

        response = self.client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 300,
            },
        )
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"].strip()

        try:
            import json
            import re

            # Try to extract JSON from response
            match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if match:
                result = json.loads(match.group())
            else:
                result = json.loads(content)

            return {
                "original_query": query,
                "rewritten_query": result.get("rewritten_query", query),
                "search_terms": result.get("search_terms", []),
                "intent": result.get("intent", "general"),
                "category": result.get("category", "general"),
            }

        except (json.JSONDecodeError, ValueError):
            # Fallback to simple expansion
            return {
                "original_query": query,
                "rewritten_query": self.expand_query(query),
                "search_terms": query.split()[:5],
                "intent": self.classify_intent(query),
                "category": "general",
            }

    def rewrite(
        self,
        query: str,
        use_llm: bool = False,
        context: Optional[str] = None,
    ) -> dict:
        """
        Main method to rewrite a query.

        Args:
            query: Original query.
            use_llm: Whether to use LLM for rewriting (slower but smarter).
            context: Optional context.

        Returns:
            Dict with rewriting results.
        """
        if use_llm:
            return self.rewrite_with_llm(query, context)

        # Fast path: rule-based rewriting
        expanded = self.expand_query(query)
        intent = self.classify_intent(query)
        search_queries = self.generate_search_queries(query)

        return {
            "original_query": query,
            "rewritten_query": expanded,
            "search_queries": search_queries,
            "intent": intent,
            "category": self._infer_category(query),
        }

    def _infer_category(self, query: str) -> str:
        """Infer the category from query terms."""
        query_lower = query.lower()

        category_keywords = {
            "stylus": ["stylus", "rust", "sol_storage", "cargo stylus", ".rs"],
            "backend": ["backend", "api", "nestjs", "express", "controller", "service"],
            "frontend": ["frontend", "react", "next", "component", "ui", "page"],
            "wallet": ["wallet", "wagmi", "viem", "rainbowkit", "connect"],
            "indexer": ["indexer", "subgraph", "graph", "event", "handler"],
            "oracle": ["oracle", "chainlink", "price", "feed"],
        }

        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return category

        return "general"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def generate_hyde(self, query: str) -> str:
        """
        Generate a Hypothetical Document Embedding (HyDE).

        Creates a hypothetical answer that would be relevant to the query,
        improving semantic similarity during retrieval.

        Args:
            query: User query.

        Returns:
            Hypothetical document/answer.
        """
        category = self._infer_category(query)
        intent = self.classify_intent(query)

        # Customize prompt based on category and intent
        if category == "stylus" and intent == "generate_code":
            context = "You are writing Rust code for Arbitrum Stylus smart contracts."
        elif category == "backend":
            context = "You are writing NestJS/Express backend code for a Web3 application."
        elif category == "frontend":
            context = "You are writing React/Next.js frontend code with wallet integration."
        elif category == "indexer":
            context = "You are creating subgraph schemas and mappings for The Graph."
        elif category == "oracle":
            context = "You are integrating Chainlink oracles into smart contracts."
        else:
            context = "You are a developer building on Arbitrum."

        prompt = f"""{context}

Write a detailed technical response that would answer this question:
"{query}"

Include:
- Relevant code snippets if applicable
- Key concepts and terminology
- Best practices
- Common patterns

Provide a comprehensive but focused answer (200-400 words)."""

        response = self.client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 600,
            },
        )
        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"].strip()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def generate_multi_queries(self, query: str, num_queries: int = 4) -> list[str]:
        """
        Generate multiple diverse queries for better retrieval coverage.

        Based on DMQR-RAG approach that shows 14% improvement over single query.

        Args:
            query: Original query.
            num_queries: Number of queries to generate.

        Returns:
            List of diverse queries.
        """
        prompt = f"""Given this developer question about Arbitrum dApp development:
"{query}"

Generate {num_queries} different search queries that would help find relevant information.
Each query should approach the topic from a different angle:
1. A more specific/technical version
2. A broader/conceptual version
3. An example-focused version
4. A related/alternative approach

Respond with ONLY a JSON array of strings, no other text:
["query1", "query2", "query3", "query4"]"""

        response = self.client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
                "max_tokens": 400,
            },
        )
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"].strip()

        try:
            import json
            import re

            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                queries = json.loads(match.group())
                return [query] + queries[:num_queries - 1]
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback to rule-based multi-query
        return self.generate_search_queries(query, num_queries)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def generate_step_back_question(self, query: str) -> str:
        """
        Generate a step-back question for higher-level context.

        Helps retrieve conceptual information that provides background
        for answering the specific question.

        Args:
            query: Original query.

        Returns:
            Higher-level concept question.
        """
        prompt = f"""Given this specific developer question:
"{query}"

Generate a "step-back" question that asks about the broader concept or principle behind it.
For example:
- Specific: "How do I implement transfer in a Stylus ERC20?"
- Step-back: "What are the key patterns for implementing ERC20 tokens in Stylus?"

Respond with ONLY the step-back question, nothing else."""

        response = self.client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 100,
            },
        )
        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"].strip()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def decompose_query(self, query: str) -> list[str]:
        """
        Decompose a complex query into sub-queries.

        Useful for multi-hop questions that need information
        from multiple sources.

        Args:
            query: Complex query.

        Returns:
            List of sub-queries.
        """
        prompt = f"""Analyze this developer question:
"{query}"

If it contains multiple sub-questions or requires multiple pieces of information, break it down.
If it's already a simple, focused question, return it as-is.

Respond with a JSON array of questions:
["question1", "question2", ...]"""

        response = self.client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 300,
            },
        )
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"].strip()

        try:
            import json
            import re

            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                return json.loads(match.group())
        except (json.JSONDecodeError, ValueError):
            pass

        return [query]

    def advanced_rewrite(
        self,
        query: str,
        use_hyde: bool = True,
        use_multi_query: bool = True,
        use_step_back: bool = False,
        use_decomposition: bool = False,
    ) -> dict:
        """
        Comprehensive query rewriting using multiple SOTA techniques.

        Args:
            query: Original query.
            use_hyde: Generate hypothetical document.
            use_multi_query: Generate multiple query variants.
            use_step_back: Generate step-back question.
            use_decomposition: Decompose complex queries.

        Returns:
            Dict with all rewriting results.
        """
        result = {
            "original_query": query,
            "expanded_query": self.expand_query(query),
            "intent": self.classify_intent(query),
            "category": self._infer_category(query),
        }

        if use_hyde:
            try:
                result["hyde_document"] = self.generate_hyde(query)
            except Exception as e:
                result["hyde_error"] = str(e)

        if use_multi_query:
            try:
                result["multi_queries"] = self.generate_multi_queries(query)
            except Exception as e:
                result["multi_queries"] = self.generate_search_queries(query)

        if use_step_back:
            try:
                result["step_back_question"] = self.generate_step_back_question(query)
            except Exception as e:
                result["step_back_error"] = str(e)

        if use_decomposition:
            try:
                result["sub_queries"] = self.decompose_query(query)
            except Exception as e:
                result["sub_queries"] = [query]

        return result

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

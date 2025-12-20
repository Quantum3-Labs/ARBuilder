"""
Reranking module for ARBuilder.
Uses LLM-based reranking for improved retrieval quality.
"""

import os
from typing import Optional

import httpx
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek/deepseek-chat")


class Reranker:
    """
    LLM-based reranker for improving retrieval quality.
    Uses a language model to score relevance of retrieved documents.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        """
        Initialize the reranker.

        Args:
            api_key: OpenRouter API key.
            model: Model to use for reranking.
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
            timeout=60.0,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Rerank documents based on relevance to query.

        Args:
            query: The search query.
            documents: List of document texts to rerank.
            top_k: Number of top results to return.

        Returns:
            List of dicts with 'index', 'document', and 'score'.
        """
        if not documents:
            return []

        # Build the reranking prompt
        docs_text = "\n\n".join([
            f"[Document {i+1}]\n{doc[:1500]}"  # Truncate long docs
            for i, doc in enumerate(documents)
        ])

        prompt = f"""You are a relevance scoring assistant. Given a query and a list of documents, score each document's relevance to the query on a scale of 0-10.

Query: {query}

Documents:
{docs_text}

For each document, provide a relevance score (0-10) where:
- 0-2: Not relevant
- 3-4: Slightly relevant
- 5-6: Moderately relevant
- 7-8: Highly relevant
- 9-10: Perfectly relevant

Respond with ONLY a JSON array of scores in order, like: [7, 3, 9, 5, ...]
No explanations, just the JSON array."""

        response = self.client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 200,
            },
        )
        response.raise_for_status()
        data = response.json()

        # Parse scores from response
        content = data["choices"][0]["message"]["content"].strip()

        try:
            # Try to extract JSON array from response
            import json
            import re

            # Find array in response
            match = re.search(r'\[[\d\s,\.]+\]', content)
            if match:
                scores = json.loads(match.group())
            else:
                # Fallback: try parsing whole content
                scores = json.loads(content)

            # Ensure we have enough scores
            while len(scores) < len(documents):
                scores.append(5)  # Default middle score

        except (json.JSONDecodeError, ValueError):
            # If parsing fails, use equal scores
            scores = [5] * len(documents)

        # Create scored results
        results = [
            {
                "index": i,
                "document": doc,
                "score": float(scores[i]) if i < len(scores) else 5.0,
            }
            for i, doc in enumerate(documents)
        ]

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:top_k]

    def rerank_with_metadata(
        self,
        query: str,
        results: dict,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Rerank ChromaDB query results.

        Args:
            query: The search query.
            results: ChromaDB query results dict.
            top_k: Number of top results to return.

        Returns:
            List of reranked results with metadata.
        """
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        ids = results["ids"][0]
        distances = results["distances"][0]

        # Rerank
        reranked = self.rerank(query, documents, top_k=top_k)

        # Attach original metadata
        final_results = []
        for item in reranked:
            idx = item["index"]
            final_results.append({
                "id": ids[idx],
                "document": item["document"],
                "metadata": metadatas[idx],
                "original_distance": distances[idx],
                "rerank_score": item["score"],
            })

        return final_results

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class BM25Reranker:
    """
    Simple BM25-based reranker for keyword matching.
    Lighter weight alternative to LLM reranking.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 reranker.

        Args:
            k1: Term frequency saturation parameter.
            b: Length normalization parameter.
        """
        self.k1 = k1
        self.b = b

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Rerank documents using BM25 scoring.

        Args:
            query: The search query.
            documents: List of documents to rerank.
            top_k: Number of top results to return.

        Returns:
            List of reranked results.
        """
        from rank_bm25 import BM25Okapi

        # Tokenize
        query_tokens = query.lower().split()
        doc_tokens = [doc.lower().split() for doc in documents]

        # Create BM25 index
        bm25 = BM25Okapi(doc_tokens)

        # Get scores
        scores = bm25.get_scores(query_tokens)

        # Create results
        results = [
            {
                "index": i,
                "document": doc,
                "score": float(scores[i]),
            }
            for i, doc in enumerate(documents)
        ]

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:top_k]


class HybridReranker:
    """
    Combines vector similarity, BM25, and optional LLM reranking.
    Uses Reciprocal Rank Fusion (RRF) for combining scores.
    """

    def __init__(
        self,
        use_llm: bool = False,
        llm_reranker: Optional[Reranker] = None,
        rrf_k: int = 60,
    ):
        """
        Initialize hybrid reranker.

        Args:
            use_llm: Whether to use LLM for final reranking.
            llm_reranker: LLM reranker instance.
            rrf_k: RRF constant (default 60).
        """
        self.bm25_reranker = BM25Reranker()
        self.use_llm = use_llm
        self.llm_reranker = llm_reranker
        self.rrf_k = rrf_k

    def rerank(
        self,
        query: str,
        documents: list[str],
        vector_distances: list[float],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Hybrid reranking using RRF.

        Args:
            query: The search query.
            documents: List of documents.
            vector_distances: Original vector search distances.
            top_k: Number of results to return.

        Returns:
            Reranked results.
        """
        n = len(documents)

        # Get BM25 rankings
        bm25_results = self.bm25_reranker.rerank(query, documents, top_k=n)
        bm25_ranks = {r["index"]: i + 1 for i, r in enumerate(bm25_results)}

        # Get vector rankings (lower distance = better rank)
        vector_sorted = sorted(range(n), key=lambda i: vector_distances[i])
        vector_ranks = {idx: rank + 1 for rank, idx in enumerate(vector_sorted)}

        # Compute RRF scores
        rrf_scores = {}
        for i in range(n):
            rrf_scores[i] = (
                1 / (self.rrf_k + vector_ranks[i]) +
                1 / (self.rrf_k + bm25_ranks[i])
            )

        # Sort by RRF score
        sorted_indices = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)

        results = [
            {
                "index": idx,
                "document": documents[idx],
                "vector_rank": vector_ranks[idx],
                "bm25_rank": bm25_ranks[idx],
                "rrf_score": rrf_scores[idx],
            }
            for idx in sorted_indices[:top_k]
        ]

        # Optional LLM reranking on top results
        if self.use_llm and self.llm_reranker:
            top_docs = [r["document"] for r in results]
            llm_results = self.llm_reranker.rerank(query, top_docs, top_k=top_k)

            # Merge LLM scores
            for i, llm_r in enumerate(llm_results):
                orig_idx = results[llm_r["index"]]["index"]
                results[i] = {
                    **results[llm_r["index"]],
                    "llm_score": llm_r["score"],
                    "final_rank": i + 1,
                }

            results = sorted(results, key=lambda x: x.get("llm_score", 0), reverse=True)

        return results

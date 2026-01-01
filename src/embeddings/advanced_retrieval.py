"""
Advanced Retrieval Pipeline for ARBuilder.
Combines SOTA techniques with configurable compute levels.

Compute Modes:
- "fast": Rule-based only, no API calls (~10ms)
- "balanced": Hybrid search + BM25 reranking (~100ms)
- "accurate": Full pipeline with HyDE + multi-query + LLM reranking (~2-5s)

References:
- Semantic Chunking: https://www.firecrawl.dev/blog/best-chunking-strategies-rag-2025
- HyDE: https://www.nomidl.com/generative-ai/revolutionizing-uery-rewrite-and-extension-rag-advanced-approach-with-hyde/
- DMQR-RAG: https://arxiv.org/html/2411.13154v1
- ColBERT: https://weaviate.io/blog/late-interaction-overview
"""

from typing import Optional
from dataclasses import dataclass

from .vectordb import VectorDB
from .reranker import HybridReranker, BM25Reranker, Reranker
from .query_rewriter import QueryRewriter


@dataclass
class RetrievalConfig:
    """Configuration for retrieval pipeline."""
    # Compute mode
    mode: str = "balanced"  # fast, balanced, accurate

    # Query rewriting
    use_query_expansion: bool = True
    use_hyde: bool = False
    use_multi_query: bool = False

    # Retrieval
    initial_k: int = 20  # Initial candidates to retrieve
    final_k: int = 5  # Final results after reranking

    # Reranking
    use_bm25: bool = True
    use_llm_rerank: bool = False

    # Filtering
    category_filter: Optional[str] = None

    @classmethod
    def fast(cls) -> "RetrievalConfig":
        """Fast mode - rule-based only, ~10ms."""
        return cls(
            mode="fast",
            use_query_expansion=True,
            use_hyde=False,
            use_multi_query=False,
            initial_k=10,
            final_k=5,
            use_bm25=False,
            use_llm_rerank=False,
        )

    @classmethod
    def balanced(cls) -> "RetrievalConfig":
        """Balanced mode - hybrid search + BM25, ~100ms."""
        return cls(
            mode="balanced",
            use_query_expansion=True,
            use_hyde=False,
            use_multi_query=False,
            initial_k=20,
            final_k=5,
            use_bm25=True,
            use_llm_rerank=False,
        )

    @classmethod
    def accurate(cls) -> "RetrievalConfig":
        """Accurate mode - full pipeline, ~2-5s."""
        return cls(
            mode="accurate",
            use_query_expansion=True,
            use_hyde=True,
            use_multi_query=True,
            initial_k=30,
            final_k=5,
            use_bm25=True,
            use_llm_rerank=True,
        )


class AdvancedRetriever:
    """
    Advanced retrieval pipeline combining multiple SOTA techniques.

    Pipeline stages:
    1. Query Rewriting (expansion, HyDE, multi-query)
    2. Initial Retrieval (vector search)
    3. Hybrid Fusion (combine results from multiple queries)
    4. Reranking (BM25 + optional LLM)
    5. Final Selection

    Usage:
        retriever = AdvancedRetriever()

        # Fast mode (no API calls)
        results = retriever.retrieve("How to implement ERC20 in Stylus?", mode="fast")

        # Balanced mode (recommended)
        results = retriever.retrieve("How to implement ERC20 in Stylus?", mode="balanced")

        # Accurate mode (for complex queries)
        results = retriever.retrieve("How to implement ERC20 in Stylus?", mode="accurate")
    """

    def __init__(
        self,
        vectordb: Optional[VectorDB] = None,
        query_rewriter: Optional[QueryRewriter] = None,
        collection_name: str = "arbbuilder",
    ):
        """
        Initialize the advanced retriever.

        Args:
            vectordb: Vector database instance.
            query_rewriter: Query rewriter instance.
            collection_name: ChromaDB collection name.
        """
        self.vectordb = vectordb or VectorDB(collection_name=collection_name)
        self.query_rewriter = query_rewriter
        self.bm25_reranker = BM25Reranker()
        self.llm_reranker = None  # Lazy initialization

    def _get_query_rewriter(self) -> QueryRewriter:
        """Lazy initialization of query rewriter."""
        if self.query_rewriter is None:
            self.query_rewriter = QueryRewriter()
        return self.query_rewriter

    def _get_llm_reranker(self) -> Reranker:
        """Lazy initialization of LLM reranker."""
        if self.llm_reranker is None:
            self.llm_reranker = Reranker()
        return self.llm_reranker

    def _expand_query(self, query: str, config: RetrievalConfig) -> dict:
        """
        Stage 1: Query expansion and rewriting.
        """
        result = {"original_query": query, "queries": [query]}

        if not config.use_query_expansion:
            return result

        rewriter = self._get_query_rewriter()

        # Rule-based expansion (always fast)
        expanded = rewriter.expand_query(query)
        result["expanded_query"] = expanded
        result["intent"] = rewriter.classify_intent(query)
        result["category"] = rewriter._infer_category(query)

        if expanded != query:
            result["queries"].append(expanded)

        # HyDE (requires LLM)
        if config.use_hyde:
            try:
                hyde_doc = rewriter.generate_hyde(query)
                result["hyde_document"] = hyde_doc
                result["queries"].append(hyde_doc[:500])  # Use truncated HyDE for search
            except Exception as e:
                result["hyde_error"] = str(e)

        # Multi-query (requires LLM or uses fallback)
        if config.use_multi_query:
            try:
                if config.mode == "accurate":
                    multi_queries = rewriter.generate_multi_queries(query, 4)
                else:
                    multi_queries = rewriter.generate_search_queries(query, 3)
                result["multi_queries"] = multi_queries
                result["queries"].extend(multi_queries[1:])  # Skip original
            except Exception:
                # Fallback to rule-based
                multi_queries = rewriter.generate_search_queries(query, 3)
                result["multi_queries"] = multi_queries

        # Deduplicate queries
        result["queries"] = list(dict.fromkeys(result["queries"]))

        return result

    def _initial_retrieval(
        self,
        queries: list[str],
        config: RetrievalConfig,
    ) -> list[dict]:
        """
        Stage 2: Initial retrieval from vector database.
        """
        all_results = {}

        # Build metadata filter if category specified
        where_filter = None
        if config.category_filter:
            where_filter = {"category": config.category_filter}

        # Retrieve for each query
        for query in queries:
            results = self.vectordb.query(
                query_text=query,
                n_results=config.initial_k,
                where=where_filter,
            )

            # Merge results (deduplicate by ID)
            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                if doc_id not in all_results:
                    all_results[doc_id] = {
                        "id": doc_id,
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i],
                        "query_matches": 1,
                    }
                else:
                    # Boost score for documents matching multiple queries
                    all_results[doc_id]["query_matches"] += 1
                    # Keep best (lowest) distance
                    all_results[doc_id]["distance"] = min(
                        all_results[doc_id]["distance"],
                        results["distances"][0][i]
                    )

        return list(all_results.values())

    def _rerank(
        self,
        query: str,
        candidates: list[dict],
        config: RetrievalConfig,
    ) -> list[dict]:
        """
        Stage 3: Reranking candidates.
        """
        if not candidates:
            return []

        documents = [c["document"] for c in candidates]

        # BM25 scoring
        if config.use_bm25:
            bm25_results = self.bm25_reranker.rerank(query, documents, top_k=len(documents))
            bm25_scores = {r["index"]: r["score"] for r in bm25_results}

            for i, candidate in enumerate(candidates):
                candidate["bm25_score"] = bm25_scores.get(i, 0)
        else:
            for candidate in candidates:
                candidate["bm25_score"] = 0

        # LLM reranking (expensive)
        if config.use_llm_rerank:
            try:
                llm_reranker = self._get_llm_reranker()
                llm_results = llm_reranker.rerank(query, documents, top_k=len(documents))
                llm_scores = {r["index"]: r["score"] for r in llm_results}

                for i, candidate in enumerate(candidates):
                    candidate["llm_score"] = llm_scores.get(i, 5)
            except Exception:
                for candidate in candidates:
                    candidate["llm_score"] = 5

        # Compute final score
        for candidate in candidates:
            # Normalize distance to 0-1 (lower is better, so invert)
            distance_score = 1 / (1 + candidate["distance"])

            # BM25 score (normalize roughly)
            bm25_normalized = min(candidate["bm25_score"] / 10, 1)

            # Query match boost
            match_boost = candidate.get("query_matches", 1) * 0.1

            # Combine scores
            if config.use_llm_rerank:
                llm_normalized = candidate.get("llm_score", 5) / 10
                candidate["final_score"] = (
                    0.3 * distance_score +
                    0.2 * bm25_normalized +
                    0.4 * llm_normalized +
                    0.1 * match_boost
                )
            else:
                candidate["final_score"] = (
                    0.5 * distance_score +
                    0.4 * bm25_normalized +
                    0.1 * match_boost
                )

        # Sort by final score
        candidates.sort(key=lambda x: x["final_score"], reverse=True)

        return candidates[:config.final_k]

    def retrieve(
        self,
        query: str,
        mode: str = "balanced",
        config: Optional[RetrievalConfig] = None,
    ) -> dict:
        """
        Main retrieval method.

        Args:
            query: User query.
            mode: Compute mode (fast, balanced, accurate).
            config: Optional custom configuration.

        Returns:
            Dict with results and metadata.
        """
        # Get configuration
        if config is None:
            if mode == "fast":
                config = RetrievalConfig.fast()
            elif mode == "accurate":
                config = RetrievalConfig.accurate()
            else:
                config = RetrievalConfig.balanced()

        # Stage 1: Query expansion
        query_info = self._expand_query(query, config)

        # Stage 2: Initial retrieval
        candidates = self._initial_retrieval(query_info["queries"], config)

        # Stage 3: Reranking
        results = self._rerank(query, candidates, config)

        return {
            "query": query,
            "mode": config.mode,
            "query_info": query_info,
            "total_candidates": len(candidates),
            "results": results,
        }

    def retrieve_for_generation(
        self,
        query: str,
        category: Optional[str] = None,
        n_results: int = 5,
    ) -> list[dict]:
        """
        Simplified retrieval for code generation tools.

        Uses balanced mode with optional category filtering.

        Args:
            query: User query.
            category: Optional category filter (stylus, backend, frontend, etc.)
            n_results: Number of results.

        Returns:
            List of relevant documents.
        """
        config = RetrievalConfig.balanced()
        config.final_k = n_results
        config.category_filter = category

        result = self.retrieve(query, config=config)
        return result["results"]


# Convenience functions
def quick_search(query: str, n_results: int = 5) -> list[dict]:
    """Quick search with minimal compute."""
    retriever = AdvancedRetriever()
    config = RetrievalConfig.fast()
    config.final_k = n_results
    result = retriever.retrieve(query, config=config)
    return result["results"]


def accurate_search(query: str, n_results: int = 5) -> list[dict]:
    """Accurate search with full pipeline."""
    retriever = AdvancedRetriever()
    config = RetrievalConfig.accurate()
    config.final_k = n_results
    result = retriever.retrieve(query, config=config)
    return result["results"]

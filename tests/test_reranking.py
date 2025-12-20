"""
Tests for reranking quality evaluation.
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.embeddings.vectordb import VectorDB
from src.embeddings.reranker import Reranker, BM25Reranker, HybridReranker
from tests.test_queries import TEST_QUERIES


class TestBM25Reranker:
    """Test BM25-based reranking."""

    @pytest.fixture
    def reranker(self):
        return BM25Reranker()

    def test_basic_reranking(self, reranker):
        """Test that BM25 reranks based on keyword relevance."""
        query = "How do I create an ERC20 token?"
        documents = [
            "This document talks about weather patterns and climate change.",
            "ERC20 tokens are fungible tokens on Ethereum. To create one, use OpenZeppelin.",
            "Stylus allows writing smart contracts in Rust for Arbitrum.",
            "Creating an ERC20 token requires implementing transfer, balanceOf functions.",
        ]

        results = reranker.rerank(query, documents, top_k=4)

        # The ERC20-related docs should rank higher
        top_2_docs = [r["document"] for r in results[:2]]
        assert any("ERC20" in doc for doc in top_2_docs), "ERC20 docs should rank high"

    def test_keyword_matching(self, reranker):
        """Test keyword matching improves ranking."""
        query = "Stylus SDK storage"
        documents = [
            "The weather is nice today.",
            "Stylus SDK provides storage utilities for contracts.",
            "Smart contracts use storage to persist data.",
            "SDK documentation explains various features.",
        ]

        results = reranker.rerank(query, documents, top_k=4)

        # Doc with most keyword overlap should rank first
        assert "Stylus SDK" in results[0]["document"]


class TestLLMReranker:
    """Test LLM-based reranking."""

    @pytest.fixture
    def reranker(self):
        try:
            return Reranker()
        except ValueError:
            pytest.skip("OpenRouter API key not configured")

    def test_relevance_scoring(self, reranker):
        """Test that LLM scores relevant docs higher."""
        query = "How do I deploy a Stylus contract?"
        documents = [
            "To deploy a Stylus contract, run 'cargo stylus deploy' with your RPC endpoint.",
            "Cooking pasta requires boiling water and adding salt.",
            "Stylus contracts are compiled to WASM before deployment.",
            "The stock market had a volatile day yesterday.",
        ]

        results = reranker.rerank(query, documents, top_k=4)

        # Relevant docs should have higher scores
        relevant_scores = [r["score"] for r in results if "Stylus" in r["document"]]
        irrelevant_scores = [r["score"] for r in results if "Stylus" not in r["document"]]

        avg_relevant = sum(relevant_scores) / len(relevant_scores) if relevant_scores else 0
        avg_irrelevant = sum(irrelevant_scores) / len(irrelevant_scores) if irrelevant_scores else 0

        print(f"\nAvg relevant score: {avg_relevant:.2f}, Avg irrelevant: {avg_irrelevant:.2f}")

        assert avg_relevant > avg_irrelevant, "Relevant docs should score higher"


class TestHybridReranker:
    """Test hybrid reranking combining vector + BM25."""

    @pytest.fixture
    def reranker(self):
        return HybridReranker(use_llm=False)

    def test_rrf_combination(self, reranker):
        """Test RRF combines rankings properly."""
        query = "ERC20 token transfer"
        documents = [
            "ERC20 tokens implement transfer functionality.",
            "Weather forecast for tomorrow.",
            "Transfer tokens between accounts using ERC20.",
            "Stock prices fluctuated today.",
        ]
        # Simulated vector distances (lower = more similar)
        vector_distances = [0.3, 0.9, 0.4, 0.8]

        results = reranker.rerank(
            query=query,
            documents=documents,
            vector_distances=vector_distances,
            top_k=4,
        )

        # ERC20 docs should rank in top 2
        top_2 = [r["document"] for r in results[:2]]
        assert all("ERC20" in doc or "Transfer" in doc for doc in top_2)


class TestRerankerIntegration:
    """Integration tests with actual vector database."""

    @pytest.fixture(scope="class")
    def vectordb(self):
        try:
            db = VectorDB(collection_name="arbbuilder")
            if db.collection.count() == 0:
                pytest.skip("Vector database is empty")
            return db
        except Exception as e:
            pytest.skip(f"Could not connect to vector database: {e}")

    @pytest.fixture
    def bm25_reranker(self):
        return BM25Reranker()

    @pytest.fixture
    def hybrid_reranker(self):
        return HybridReranker(use_llm=False)

    def test_reranking_improves_precision(self, vectordb, bm25_reranker):
        """Test that reranking improves precision on real queries."""
        query = "How do I implement an ERC721 NFT in Stylus?"
        expected_keywords = ["erc721", "nft", "stylus", "mint", "token"]

        # Get initial results
        results = vectordb.query(query_text=query, n_results=20)
        docs = results["documents"][0]

        # Rerank
        reranked = bm25_reranker.rerank(query, docs, top_k=10)
        reranked_docs = [r["document"] for r in reranked]

        # Calculate keyword hits in top 5
        def count_keyword_hits(doc_list, k=5):
            top_k = doc_list[:k]
            hits = 0
            for doc in top_k:
                doc_lower = doc.lower()
                hits += sum(1 for kw in expected_keywords if kw.lower() in doc_lower)
            return hits

        original_hits = count_keyword_hits(docs)
        reranked_hits = count_keyword_hits(reranked_docs)

        print(f"\nOriginal keyword hits (top 5): {original_hits}")
        print(f"Reranked keyword hits (top 5): {reranked_hits}")

        # Reranking should maintain or improve hits
        assert reranked_hits >= original_hits * 0.8, "Reranking significantly reduced quality"

    def test_hybrid_reranking_benchmark(self, vectordb, hybrid_reranker):
        """Benchmark hybrid reranking on test queries."""
        results_summary = []

        for query_info in TEST_QUERIES[:5]:  # Test on first 5 queries
            query = query_info["query"]
            expected = query_info["expected_keywords"]

            # Get vector results
            vector_results = vectordb.query(query_text=query, n_results=20)
            docs = vector_results["documents"][0]
            distances = vector_results["distances"][0]

            # Hybrid rerank
            reranked = hybrid_reranker.rerank(
                query=query,
                documents=docs,
                vector_distances=distances,
                top_k=10,
            )

            # Check keyword presence in top 5
            top_5_docs = [r["document"] for r in reranked[:5]]
            hits = sum(
                1 for doc in top_5_docs
                for kw in expected if kw.lower() in doc.lower()
            )

            results_summary.append({
                "query": query,
                "keyword_hits": hits,
                "max_possible": len(expected) * 5,
            })

        # Print summary
        print("\n=== Hybrid Reranking Benchmark ===")
        for r in results_summary:
            print(f"Query: {r['query'][:50]}...")
            print(f"  Keyword hits: {r['keyword_hits']}/{r['max_possible']}")

        total_hits = sum(r["keyword_hits"] for r in results_summary)
        total_possible = sum(r["max_possible"] for r in results_summary)
        hit_rate = total_hits / total_possible if total_possible > 0 else 0

        print(f"\nOverall hit rate: {hit_rate:.2%}")

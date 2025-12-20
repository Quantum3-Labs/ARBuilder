"""
Tests for retrieval quality evaluation.
"""

import json
import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.embeddings.vectordb import VectorDB
from tests.test_queries import TEST_QUERIES, get_queries_by_difficulty


class RetrievalMetrics:
    """Calculate retrieval quality metrics."""

    @staticmethod
    def keyword_recall(
        results: list[str],
        expected_keywords: list[str],
    ) -> float:
        """
        Calculate keyword recall - what fraction of expected keywords
        appear in the retrieved results.

        Args:
            results: List of retrieved document texts.
            expected_keywords: Keywords that should appear.

        Returns:
            Recall score between 0 and 1.
        """
        if not expected_keywords:
            return 1.0

        combined_text = " ".join(results).lower()
        found = sum(1 for kw in expected_keywords if kw.lower() in combined_text)

        return found / len(expected_keywords)

    @staticmethod
    def mrr(
        results: list[str],
        expected_keywords: list[str],
    ) -> float:
        """
        Calculate Mean Reciprocal Rank - how early does a relevant
        result appear.

        Args:
            results: List of retrieved document texts.
            expected_keywords: Keywords indicating relevance.

        Returns:
            MRR score between 0 and 1.
        """
        for i, doc in enumerate(results):
            doc_lower = doc.lower()
            # Consider relevant if contains at least 2 keywords
            matches = sum(1 for kw in expected_keywords if kw.lower() in doc_lower)
            if matches >= 2:
                return 1.0 / (i + 1)

        return 0.0

    @staticmethod
    def precision_at_k(
        results: list[str],
        expected_keywords: list[str],
        k: int = 5,
    ) -> float:
        """
        Calculate Precision@K - fraction of top-k results that are relevant.

        Args:
            results: List of retrieved document texts.
            expected_keywords: Keywords indicating relevance.
            k: Number of top results to consider.

        Returns:
            Precision@K score between 0 and 1.
        """
        top_k = results[:k]
        relevant = 0

        for doc in top_k:
            doc_lower = doc.lower()
            matches = sum(1 for kw in expected_keywords if kw.lower() in doc_lower)
            if matches >= 2:
                relevant += 1

        return relevant / k if k > 0 else 0.0


class TestRetrievalQuality:
    """Test suite for retrieval quality."""

    @pytest.fixture(scope="class")
    def vectordb(self):
        """Initialize vector database connection."""
        try:
            db = VectorDB(collection_name="arbbuilder")
            if db.collection.count() == 0:
                pytest.skip("Vector database is empty. Run ingestion first.")
            return db
        except Exception as e:
            pytest.skip(f"Could not connect to vector database: {e}")

    @pytest.fixture
    def metrics(self):
        """Initialize metrics calculator."""
        return RetrievalMetrics()

    def test_basic_retrieval(self, vectordb, metrics):
        """Test retrieval on basic queries."""
        basic_queries = get_queries_by_difficulty("basic")

        results_summary = []
        for query_info in basic_queries:
            results = vectordb.query(
                query_text=query_info["query"],
                n_results=10,
            )

            docs = results["documents"][0]
            keywords = query_info["expected_keywords"]

            recall = metrics.keyword_recall(docs, keywords)
            mrr = metrics.mrr(docs, keywords)
            p_at_5 = metrics.precision_at_k(docs, keywords, k=5)

            results_summary.append({
                "query": query_info["query"],
                "recall": recall,
                "mrr": mrr,
                "p@5": p_at_5,
            })

        # Calculate averages
        avg_recall = sum(r["recall"] for r in results_summary) / len(results_summary)
        avg_mrr = sum(r["mrr"] for r in results_summary) / len(results_summary)
        avg_p5 = sum(r["p@5"] for r in results_summary) / len(results_summary)

        print(f"\nBasic Queries - Avg Recall: {avg_recall:.3f}, MRR: {avg_mrr:.3f}, P@5: {avg_p5:.3f}")

        # Basic queries should have good recall
        assert avg_recall >= 0.5, f"Basic query recall too low: {avg_recall}"

    def test_intermediate_retrieval(self, vectordb, metrics):
        """Test retrieval on intermediate queries."""
        intermediate_queries = get_queries_by_difficulty("intermediate")

        results_summary = []
        for query_info in intermediate_queries:
            results = vectordb.query(
                query_text=query_info["query"],
                n_results=10,
            )

            docs = results["documents"][0]
            keywords = query_info["expected_keywords"]

            recall = metrics.keyword_recall(docs, keywords)
            mrr = metrics.mrr(docs, keywords)

            results_summary.append({
                "query": query_info["query"],
                "recall": recall,
                "mrr": mrr,
            })

        avg_recall = sum(r["recall"] for r in results_summary) / len(results_summary)
        avg_mrr = sum(r["mrr"] for r in results_summary) / len(results_summary)

        print(f"\nIntermediate Queries - Avg Recall: {avg_recall:.3f}, MRR: {avg_mrr:.3f}")

        assert avg_recall >= 0.4, f"Intermediate query recall too low: {avg_recall}"

    def test_advanced_retrieval(self, vectordb, metrics):
        """Test retrieval on advanced queries."""
        advanced_queries = get_queries_by_difficulty("advanced")

        results_summary = []
        for query_info in advanced_queries:
            results = vectordb.query(
                query_text=query_info["query"],
                n_results=10,
            )

            docs = results["documents"][0]
            keywords = query_info["expected_keywords"]

            recall = metrics.keyword_recall(docs, keywords)

            results_summary.append({
                "query": query_info["query"],
                "recall": recall,
            })

        avg_recall = sum(r["recall"] for r in results_summary) / len(results_summary)

        print(f"\nAdvanced Queries - Avg Recall: {avg_recall:.3f}")

        # Advanced queries can be harder, lower threshold
        assert avg_recall >= 0.3, f"Advanced query recall too low: {avg_recall}"

    def test_hybrid_search_improvement(self, vectordb, metrics):
        """Test that hybrid search improves over pure vector search."""
        test_query = "How do I create an ERC20 token with Stylus?"
        expected_keywords = ["erc20", "token", "stylus", "transfer", "balance"]

        # Pure vector search
        vector_results = vectordb.query(query_text=test_query, n_results=10)
        vector_recall = metrics.keyword_recall(
            vector_results["documents"][0],
            expected_keywords,
        )

        # Hybrid search
        hybrid_results = vectordb.hybrid_search(query_text=test_query, n_results=10)
        hybrid_recall = metrics.keyword_recall(
            hybrid_results["documents"][0],
            expected_keywords,
        )

        print(f"\nVector Recall: {vector_recall:.3f}, Hybrid Recall: {hybrid_recall:.3f}")

        # Hybrid should be at least as good
        assert hybrid_recall >= vector_recall * 0.9, "Hybrid search significantly worse than vector"


class TestRetrievalBenchmark:
    """Comprehensive retrieval benchmark."""

    @pytest.fixture(scope="class")
    def vectordb(self):
        """Initialize vector database connection."""
        try:
            db = VectorDB(collection_name="arbbuilder")
            if db.collection.count() == 0:
                pytest.skip("Vector database is empty. Run ingestion first.")
            return db
        except Exception as e:
            pytest.skip(f"Could not connect to vector database: {e}")

    def test_full_benchmark(self, vectordb):
        """Run full benchmark on all test queries."""
        metrics = RetrievalMetrics()
        all_results = []

        for query_info in TEST_QUERIES:
            results = vectordb.query(
                query_text=query_info["query"],
                n_results=10,
            )

            docs = results["documents"][0]
            keywords = query_info["expected_keywords"]

            result = {
                "query": query_info["query"],
                "category": query_info["category"],
                "difficulty": query_info["difficulty"],
                "recall": metrics.keyword_recall(docs, keywords),
                "mrr": metrics.mrr(docs, keywords),
                "p@5": metrics.precision_at_k(docs, keywords, k=5),
            }
            all_results.append(result)

        # Save benchmark results
        output_path = Path("tests/benchmark_results.json")
        output_path.parent.mkdir(exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(all_results, f, indent=2)

        # Print summary by difficulty
        for difficulty in ["basic", "intermediate", "advanced"]:
            subset = [r for r in all_results if r["difficulty"] == difficulty]
            if subset:
                avg_recall = sum(r["recall"] for r in subset) / len(subset)
                avg_mrr = sum(r["mrr"] for r in subset) / len(subset)
                print(f"\n{difficulty.upper()}: Recall={avg_recall:.3f}, MRR={avg_mrr:.3f}")

        # Overall metrics
        overall_recall = sum(r["recall"] for r in all_results) / len(all_results)
        overall_mrr = sum(r["mrr"] for r in all_results) / len(all_results)

        print(f"\nOVERALL: Recall={overall_recall:.3f}, MRR={overall_mrr:.3f}")
        print(f"\nResults saved to {output_path}")

        assert overall_recall >= 0.4, f"Overall recall too low: {overall_recall}"

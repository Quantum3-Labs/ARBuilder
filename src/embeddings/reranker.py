"""
Reranking module for ARBuilder.
Uses cross-encoder and MMR for improved retrieval quality and diversity.
"""

import os
from typing import Optional

import httpx
import numpy as np
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from .embedder import EmbeddingClient

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek/deepseek-chat")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
DEFAULT_CROSS_ENCODER = os.getenv("DEFAULT_CROSS_ENCODER", "nvidia/llama-3.2-nv-rerankqa-1b-v2")


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
        docs_text = "\n\n".join(
            [
                f"[Document {i + 1}]\n{doc[:1500]}"  # Truncate long docs
                for i, doc in enumerate(documents)
            ]
        )

        prompt = (
            "You are a relevance scoring assistant."
            " Given a query and a list of documents,"
            " score each document's relevance to the"
            " query on a scale of 0-10."
            f"\n\nQuery: {query}"
        )
        prompt += f"""

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
            match = re.search(r"\[[\d\s,\.]+\]", content)
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
            final_results.append(
                {
                    "id": ids[idx],
                    "document": item["document"],
                    "metadata": metadatas[idx],
                    "original_distance": distances[idx],
                    "rerank_score": item["score"],
                }
            )

        return final_results

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class CrossEncoderReranker:
    """
    Cross-encoder based reranker for high-accuracy relevance scoring.
    More accurate than bi-encoder approaches as it processes query-document pairs jointly.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_CROSS_ENCODER,
        api_key: Optional[str] = None,
        invoke_url: Optional[str] = None,
    ):
        """
        Initialize cross-encoder reranker.

        Args:
            model_name: Name of the cross-encoder model to use.
            api_key: NVIDIA API key. Defaults to NVIDIA_API_KEY from env.
            invoke_url: NVIDIA reranking endpoint override.
        """
        self.model_name = model_name
        self.api_key = api_key or NVIDIA_API_KEY

        model_slug = model_name.split("/")[-1].replace(".", "_")
        self.invoke_url = invoke_url or os.getenv(
            "NVIDIA_RERANK_URL",
            f"https://ai.api.nvidia.com/v1/retrieval/nvidia/{model_slug}/reranking",
        )

        self.available = bool(self.api_key)
        if not self.available:
            print("NVIDIA_API_KEY not found. CrossEncoder reranking unavailable.")
            self.client = None
            return

        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _request_rankings(self, query: str, documents: list[str]) -> list[dict]:
        payload = {
            "model": self.model_name,
            "query": {"text": query},
            "passages": [{"text": doc} for doc in documents],
        }

        response = self.client.post(self.invoke_url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("rankings", [])

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Rerank documents using cross-encoder model.

        Args:
            query: The search query.
            documents: List of documents to rerank.
            top_k: Number of top results to return.

        Returns:
            List of reranked results with relevance scores.
        """
        if not documents:
            return []

        if not self.available:
            # Fallback: return documents with neutral scores
            return [
                {"index": i, "document": doc, "score": 0.5}
                for i, doc in enumerate(documents[:top_k])
            ]

        try:
            rankings = self._request_rankings(query, documents)
        except Exception as e:
            import logging

            logging.warning(f"NVIDIA reranking failed: {e}")
            return [
                {"index": i, "document": doc, "score": 0.5}
                for i, doc in enumerate(documents[:top_k])
            ]

        results = []
        seen_indices = set()

        # NVIDIA response format:
        # {"rankings": [{"index": 2, "logit": 6.82}, ...]}
        for rank in rankings:
            idx = rank.get("index")
            if isinstance(idx, int) and 0 <= idx < len(documents):
                results.append(
                    {
                        "index": idx,
                        "document": documents[idx],
                        "score": float(rank.get("logit", 0.0)),
                    }
                )
                seen_indices.add(idx)

        # Ensure stable output even if API omits some passages.
        for i, doc in enumerate(documents):
            if i not in seen_indices:
                results.append({"index": i, "document": doc, "score": float("-inf")})

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:top_k]

    def close(self):
        """Close the HTTP client."""
        if self.client:
            self.client.close()


class MMRReranker:
    """
    Maximal Marginal Relevance (MMR) reranker for diversity.
    Balances relevance and diversity by penalizing documents similar to already selected ones.
    """

    def __init__(
        self, lambda_param: float = 0.5, embedding_client: Optional[EmbeddingClient] = None
    ):
        """
        Initialize MMR reranker.

        Args:
            lambda_param: Trade-off between relevance (1.0) and
                diversity (0.0). Default 0.5 for balance.
            embedding_client: EmbeddingClient instance for generating
                embeddings. If None, creates new instance.
        """
        self.lambda_param = lambda_param
        if embedding_client is not None:
            self.embedding_client = embedding_client
        else:
            try:
                self.embedding_client = EmbeddingClient()
            except (ValueError, Exception) as e:
                import logging

                logging.warning(f"EmbeddingClient unavailable (MMR will use fallback): {e}")
                self.embedding_client = None

    def rerank(
        self,
        query: str,
        documents: list[str],
        embeddings: Optional[np.ndarray] = None,
        query_embedding: Optional[np.ndarray] = None,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Rerank documents using MMR for diversity.

        Args:
            query: The search query.
            documents: List of documents to rerank.
            embeddings: Document embeddings (optional, will compute if not provided).
            query_embedding: Query embedding (optional, will compute if not provided).
            top_k: Number of top results to return.

        Returns:
            List of reranked results with MMR scores.
        """
        if not documents:
            return []

        # If embeddings not provided, compute them using EmbeddingClient
        if embeddings is None:
            try:
                # Generate embeddings for documents
                doc_embeddings = self.embedding_client.embed_batch(documents)
                embeddings = np.array(doc_embeddings)
            except Exception as e:
                # Fallback: return documents without reranking
                import logging

                logging.warning(f"Failed to generate embeddings for MMR: {e}")
                return [
                    {"index": i, "document": doc, "score": 1.0 / (i + 1)}
                    for i, doc in enumerate(documents[:top_k])
                ]

        # If query embedding not provided, compute it
        if query_embedding is None:
            try:
                query_emb = self.embedding_client.embed(query)
                query_embedding = np.array(query_emb)
            except Exception as e:
                # Fallback: use first doc as reference
                import logging

                logging.warning(f"Failed to generate query embedding for MMR: {e}")
                query_embedding = embeddings[0]

        # Compute cosine similarity between query and documents
        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        # Initial relevance scores
        relevance_scores = [cosine_similarity(query_embedding, doc_emb) for doc_emb in embeddings]

        # MMR selection
        selected_indices = []
        selected_embeddings = []
        remaining_indices = list(range(len(documents)))

        for _ in range(min(top_k, len(documents))):
            if not remaining_indices:
                break

            # Compute MMR scores for remaining documents
            mmr_scores = []
            for idx in remaining_indices:
                # Relevance component
                relevance = relevance_scores[idx]

                # Diversity component (similarity to already selected)
                if selected_embeddings:
                    max_sim = max(
                        cosine_similarity(embeddings[idx], sel_emb)
                        for sel_emb in selected_embeddings
                    )
                else:
                    max_sim = 0.0

                # MMR score: balance relevance and diversity
                mmr_score = self.lambda_param * relevance - (1 - self.lambda_param) * max_sim
                mmr_scores.append((idx, mmr_score))

            # Select document with highest MMR score
            best_idx, best_score = max(mmr_scores, key=lambda x: x[1])
            selected_indices.append(best_idx)
            selected_embeddings.append(embeddings[best_idx])
            remaining_indices.remove(best_idx)

        # Create results
        results = [
            {
                "index": idx,
                "document": documents[idx],
                "score": relevance_scores[idx],  # Original relevance score
                "mmr_rank": i + 1,
            }
            for i, idx in enumerate(selected_indices)
        ]

        return results


class HybridReranker:
    """
    Combines cross-encoder reranking with MMR for diversity.
    Default reranking strategy for ARBuilder (BM25 is handled in retrieval phase).
    """

    def __init__(
        self,
        use_cross_encoder: bool = True,
        use_mmr: bool = True,
        mmr_lambda: float = 0.5,
        use_llm: bool = False,
        llm_reranker: Optional[Reranker] = None,
        embedding_client: Optional[EmbeddingClient] = None,
    ):
        """
        Initialize hybrid reranker.

        Args:
            use_cross_encoder: Whether to use cross-encoder for relevance scoring (default True).
            use_mmr: Whether to apply MMR for diversity (default True).
            mmr_lambda: MMR trade-off parameter (1.0 = relevance, 0.0 = diversity, 0.5 = balanced).
            use_llm: Whether to use LLM for final reranking (optional, slower).
            llm_reranker: LLM reranker instance.
            embedding_client: EmbeddingClient instance for MMR
                embeddings. If None, creates new instance.
        """
        self.use_cross_encoder = use_cross_encoder
        self.use_mmr = use_mmr
        self.use_llm = use_llm
        self.llm_reranker = llm_reranker
        if embedding_client is not None:
            self.embedding_client = embedding_client
        else:
            try:
                self.embedding_client = EmbeddingClient()
            except (ValueError, Exception) as e:
                import logging

                logging.warning(f"EmbeddingClient unavailable (MMR will use fallback): {e}")
                self.embedding_client = None

        # Initialize cross-encoder
        if use_cross_encoder:
            model_name = DEFAULT_CROSS_ENCODER
            self.cross_encoder = CrossEncoderReranker(model_name)
        else:
            self.cross_encoder = None

        # Initialize MMR with shared embedding client
        if use_mmr:
            self.mmr_reranker = MMRReranker(
                lambda_param=mmr_lambda, embedding_client=self.embedding_client
            )
        else:
            self.mmr_reranker = None

    def rerank(
        self,
        query: str,
        documents: list[str],
        embeddings: Optional[np.ndarray] = None,
        query_embedding: Optional[np.ndarray] = None,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Hybrid reranking using cross-encoder and MMR.

        Args:
            query: The search query.
            documents: List of documents to rerank.
            embeddings: Document embeddings for MMR (optional, computed once if not provided).
            query_embedding: Query embedding for MMR (optional, computed once if not provided).
            top_k: Number of results to return.

        Returns:
            Reranked results with scores and diversity.
        """
        if not documents:
            return []

        results = documents

        # Stage 1: Cross-encoder reranking for relevance
        if self.use_cross_encoder and self.cross_encoder:
            # Get more candidates for MMR to work with
            ce_top_k = top_k * 2 if self.use_mmr else top_k
            ce_results = self.cross_encoder.rerank(query, documents, top_k=ce_top_k)

            # Reorder documents by cross-encoder scores
            results = ce_results
        else:
            # No cross-encoder: create results with indices
            results = [
                {"index": i, "document": doc, "score": 1.0 / (i + 1)}
                for i, doc in enumerate(documents)
            ]

        # Stage 2: Apply MMR for diversity
        if self.use_mmr and self.mmr_reranker and len(results) > 1:
            # Extract documents for MMR
            reranked_docs = [r["document"] for r in results]

            # Compute embeddings once if not provided (to avoid recalculation in MMR)
            if embeddings is None and self.embedding_client:
                try:
                    # Generate embeddings for all documents at once
                    doc_embeddings = self.embedding_client.embed_batch(documents)
                    embeddings = np.array(doc_embeddings)
                except Exception as e:
                    import logging

                    logging.warning(f"Failed to generate embeddings for MMR: {e}")
                    embeddings = None

            # Compute query embedding once if not provided
            if query_embedding is None and self.embedding_client and embeddings is not None:
                try:
                    query_emb = self.embedding_client.embed(query)
                    query_embedding = np.array(query_emb)
                except Exception as e:
                    import logging

                    logging.warning(f"Failed to generate query embedding for MMR: {e}")
                    query_embedding = None

            # Reorder embeddings based on cross-encoder results if provided
            if embeddings is not None:
                doc_to_embedding = {documents[i]: embeddings[i] for i in range(len(documents))}
                reordered_embeddings = np.array([doc_to_embedding[doc] for doc in reranked_docs])
            else:
                reordered_embeddings = None

            # Apply MMR with pre-computed embeddings
            mmr_results = self.mmr_reranker.rerank(
                query,
                reranked_docs,
                embeddings=reordered_embeddings,
                query_embedding=query_embedding,
                top_k=top_k,
            )

            # Merge cross-encoder scores with MMR rankings
            final_results = []
            for i, mmr_r in enumerate(mmr_results):
                ce_score = results[mmr_r["index"]]["score"]
                final_results.append(
                    {
                        "original_index": results[mmr_r["index"]].get("index", mmr_r["index"]),
                        "document": mmr_r["document"],
                        "cross_encoder_score": ce_score,
                        "mmr_rank": mmr_r.get("mmr_rank", i + 1),
                        "relevance_score": mmr_r["score"],
                    }
                )

            results = final_results
        else:
            # No MMR: just take top_k from cross-encoder results
            results = results[:top_k]

        # Stage 3: Optional LLM reranking (for highest quality)
        if self.use_llm and self.llm_reranker:
            top_docs = [r["document"] for r in results]
            llm_results = self.llm_reranker.rerank(query, top_docs, top_k=top_k)

            # Merge LLM scores
            final_results = []
            for i, llm_r in enumerate(llm_results):
                result_data = results[llm_r["index"]].copy()
                result_data["llm_score"] = llm_r["score"]
                result_data["final_rank"] = i + 1
                final_results.append(result_data)

            results = final_results

        return results

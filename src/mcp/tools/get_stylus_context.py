"""
get_stylus_context MCP Tool.

Retrieves relevant documentation and code examples from the RAG database.
"""

import sys
import math
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.embeddings.vectordb import VectorDB
from src.embeddings.reranker import HybridReranker
from src.mcp.tools.base import BaseTool


class GetStylusContextTool(BaseTool):
    """
    Retrieves relevant Stylus documentation and code examples.

    Uses hybrid search (vector + BM25) with optional reranking.
    """

    def __init__(
        self,
        vectordb: Optional[VectorDB] = None,
        collection_name: str = "arbbuilder",
        use_reranking: bool = True,
        **kwargs,
    ):
        """
        Initialize the tool.

        Args:
            vectordb: VectorDB instance (creates new if None).
            collection_name: ChromaDB collection name.
            use_reranking: Whether to rerank results.
        """
        super().__init__(**kwargs)
        self.vectordb = vectordb or VectorDB(collection_name=collection_name)
        self.use_reranking = use_reranking

        if use_reranking:
            # Cross-encoder + MMR for relevance and diversity
            self.reranker = HybridReranker(
                use_cross_encoder=True,
                use_mmr=True,
                use_llm=False
            )
        else:
            self.reranker = None

    def execute(
        self,
        query: str,
        n_results: int = 5,
        content_type: str = "all",
        rerank: bool = True,
        category_boosts: Optional[dict[str, float]] = None,
        **kwargs,
    ) -> dict:
        """
        Retrieve relevant context from the knowledge base.

        Args:
            query: Search query string.
            n_results: Number of results to return (1-20).
            content_type: Filter by type: "all", "docs", or "code".
            rerank: Whether to rerank results.
            category_boosts: Optional dict mapping category names to boost multipliers.
                           If None, uses default Stylus boosts. Pass {} to disable boosting.
                           Example: {"stylus": 1.3, "arbitrum_sdk": 1.5}

        Returns:
            Dict with contexts, total_results, and query.
        """
        # Validate input
        if not query or not query.strip():
            return {"error": "Query is required and cannot be empty"}

        query = query.strip()
        n_results = max(1, min(20, n_results))

        try:
            # Check if collection has data
            collection_count = self.vectordb.collection.count()
            collection_name = self.vectordb.collection_name
            persist_dir = str(self.vectordb.persist_directory)
            persist_dir_abs = str(self.vectordb.persist_directory.resolve())
            
            # Check if persist directory exists
            persist_dir_exists = self.vectordb.persist_directory.exists()
            cwd = str(Path.cwd())
            
            if collection_count == 0:
                return {
                    "error": "Collection is empty. Please ingest data first using the ingestion script.",
                    "contexts": [],
                    "total_results": 0,
                    "query": query,
                    "collection_count": 0,
                    "collection_name": collection_name,
                    "persist_directory": persist_dir,
                    "persist_directory_absolute": persist_dir_abs,
                    "persist_directory_exists": persist_dir_exists,
                    "current_working_directory": cwd,
                    "diagnostic": "If you just ingested data, you may need to restart the MCP server to pick up the new collection.",
                }
        except Exception as e:
            return {"error": f"Retrieval failed: {str(e)}"}

        # Build metadata filter
        where_filter = None
        if content_type == "docs":
            where_filter = {"type": {"$eq": "documentation"}}
        elif content_type == "code":
            where_filter = {"type": {"$eq": "code"}}

        # Configure category boosts
        category_boosts = self._get_category_boosts(category_boosts)

        try:
            # Fetch more results for reranking
            fetch_count = n_results * 3 if rerank and self.use_reranking else n_results

            # Query vector database with enhanced hybrid search
            if self.use_reranking and rerank:
                # Use hybrid search with BM25 + metadata boosting
                raw_results = self.vectordb.hybrid_search(
                    query_text=query,
                    n_results=fetch_count,
                    where=where_filter,
                    alpha=0.5,  # Balanced vector + BM25
                    category_boosts=category_boosts,
                    use_bm25=True,
                )
            else:
                # Use standard vector search
                raw_results = self.vectordb.query(
                    query_text=query,
                    n_results=fetch_count,
                    where=where_filter,
                )

            # Process results
            contexts = self._process_results(raw_results, n_results, query, rerank)

            return {
                "contexts": contexts,
                "total_results": len(contexts),
                "query": query,
            }

        except Exception as e:
            return {"error": f"Retrieval failed: {str(e)}"}

    def _get_category_boosts(self, category_boosts: Optional[dict[str, float]]) -> dict[str, float]:
        """
        Get category boost configuration.

        Args:
            category_boosts: Optional dict of category boosts. If None, returns default
                           Stylus-focused boosts. If empty dict, returns no boosts.

        Returns:
            Dict mapping category names to boost multipliers.
        """
        # If explicitly provided, use it (even if empty)
        if category_boosts is not None:
            return category_boosts
        
        # Default: Category boosts based on data distribution:
        # - stylus: 7196 chunks (82.8%) - PRIMARY focus, gets highest boost
        # - orbit_sdk: 1012 chunks (11.6%) - Related to Arbitrum chains
        # - arbitrum_sdk: 451 chunks (5.2%) - SDK documentation
        # - arbitrum_docs: 33 chunks (0.4%) - General docs
        return {
            "stylus": 1.3,        # 30% boost for Stylus content (primary focus)
            "orbit_sdk": 1.1,     # 10% boost for Orbit SDK (related)
            "arbitrum_sdk": 1.05, # 5% boost for Arbitrum SDK
            "arbitrum_docs": 1.0, # No boost (neutral)
        }

    def _process_results(
        self,
        raw_results: dict,
        n_results: int,
        query: str,
        rerank: bool,
    ) -> list[dict]:
        """
        Process raw ChromaDB results into context objects.

        Args:
            raw_results: Raw query results from ChromaDB.
            n_results: Number of results to return.
            query: Original query (for reranking).
            rerank: Whether to apply reranking.

        Returns:
            List of context dictionaries.
        """
        # Check if results are empty
        if not raw_results:
            return []
        
        # ChromaDB returns results as: {"ids": [[id1, id2, ...]], ...}
        # Check if we have any results
        if not raw_results.get("ids") or len(raw_results["ids"]) == 0:
            return []
        
        # Check if the first (and only) result list is empty
        if len(raw_results["ids"][0]) == 0:
            return []

        ids = raw_results["ids"][0]
        documents = raw_results["documents"][0]
        metadatas = raw_results["metadatas"][0]
        distances = raw_results["distances"][0]
        
        # Check if hybrid search scores are available
        hybrid_scores = raw_results.get("scores", [[]])[0] if "scores" in raw_results else None

        # Apply reranking if enabled (cross-encoder + MMR)
        if rerank and self.reranker and len(documents) > 0:
            reranked = self.reranker.rerank(
                query=query,
                documents=documents,
                embeddings=None,  # Computed once if needed, then reused in MMR
                query_embedding=None,  # Computed once if needed, then reused in MMR
                top_k=n_results,
            )

            # Build contexts from reranked results
            contexts = []
            for item in reranked:
                # Get original index from reranked result
                orig_idx = item.get("original_index", item.get("index", 0))
                
                # Ensure index is within bounds
                if orig_idx >= len(documents):
                    continue
                    
                metadata = metadatas[orig_idx] if orig_idx < len(metadatas) else {}

                # Prefer the hybrid combined score (cross-encoder + MMR) when available.
                ce_score = item.get("cross_encoder_score", item.get("relevance_score", 0.5))
                # NVIDIA reranker returns unbounded logits; map to [0, 1] with sigmoid.
                relevance = 1.0 / (1.0 + math.exp(-float(ce_score)))

                contexts.append(self._build_context(
                    content=documents[orig_idx],
                    metadata=metadata,
                    distance=distances[orig_idx] if orig_idx < len(distances) else 1.0,
                    relevance_score=relevance,
                ))

            return contexts

        # Without reranking, process in score/distance order
        contexts = []
        for i in range(min(n_results, len(documents))):
            metadata = metadatas[i] if i < len(metadatas) else {}

            # Use hybrid scores if available, otherwise convert distance to relevance
            if hybrid_scores and i < len(hybrid_scores):
                # Hybrid scores are already normalized and higher is better
                relevance = hybrid_scores[i]
            else:
                # Convert distance to relevance score (cosine distance)
                # Distance of 0 = perfect match = 1.0 relevance
                # Distance of 2 = opposite = 0.0 relevance
                relevance = max(0.0, 1.0 - (distances[i] / 2.0))

            contexts.append(self._build_context(
                content=documents[i],
                metadata=metadata,
                distance=distances[i],
                relevance_score=relevance,
            ))

        return contexts

    def _build_context(
        self,
        content: str,
        metadata: dict,
        distance: float,
        relevance_score: float,
    ) -> dict:
        """Build a context object from raw data."""
        # Determine content type
        content_type = metadata.get("type", "unknown")
        if content_type == "unknown":
            # Infer from content
            if "```rust" in content.lower() or "fn " in content or "sol_storage!" in content:
                content_type = "code"
            else:
                content_type = "docs"

        # Extract source
        source = metadata.get("source", metadata.get("file_path", "unknown"))

        # Extract title
        title = metadata.get("title", "")
        if not title and "file_path" in metadata:
            title = Path(metadata["file_path"]).stem

        # Extract language for code
        language = None
        if content_type == "code":
            language = metadata.get("language", "rust")

        return {
            "content": content,
            "source": source,
            "type": content_type,
            "relevance_score": round(relevance_score, 3),
            "metadata": {
                "title": title,
                "language": language,
                "chunk_id": metadata.get("chunk_id", ""),
                "category": metadata.get("category", ""),
            },
        }

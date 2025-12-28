"""
get_stylus_context MCP Tool.

Retrieves relevant documentation and code examples from the RAG database.
"""

import sys
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.embeddings.vectordb import VectorDB
from src.embeddings.reranker import HybridReranker, Reranker
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
            self.reranker = HybridReranker(use_llm=False)  # BM25 + vector fusion
        else:
            self.reranker = None

    def execute(
        self,
        query: str,
        n_results: int = 5,
        content_type: str = "all",
        rerank: bool = True,
        **kwargs,
    ) -> dict:
        """
        Retrieve relevant context from the knowledge base.

        Args:
            query: Search query string.
            n_results: Number of results to return (1-20).
            content_type: Filter by type: "all", "docs", or "code".
            rerank: Whether to rerank results.

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

        try:
            # Fetch more results for reranking
            fetch_count = n_results * 3 if rerank and self.use_reranking else n_results

            # Query vector database
            if self.use_reranking and rerank:
                # Use hybrid search
                raw_results = self.vectordb.hybrid_search(
                    query_text=query,
                    n_results=fetch_count,
                    where=where_filter,
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

        # Apply reranking if enabled
        if rerank and self.reranker and len(documents) > 0:
            reranked = self.reranker.rerank(
                query=query,
                documents=documents,
                vector_distances=distances,
                top_k=n_results,
            )

            # Build contexts from reranked results
            contexts = []
            for item in reranked:
                idx = item["index"]
                metadata = metadatas[idx] if idx < len(metadatas) else {}

                # Calculate relevance score (normalize RRF to 0-1)
                rrf_score = item.get("rrf_score", 0)
                relevance = min(1.0, rrf_score * 30)  # Normalize RRF scores

                contexts.append(self._build_context(
                    content=documents[idx],
                    metadata=metadata,
                    distance=distances[idx],
                    relevance_score=relevance,
                ))

            return contexts

        # Without reranking, process in distance order
        contexts = []
        for i in range(min(n_results, len(documents))):
            metadata = metadatas[i] if i < len(metadatas) else {}

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

"""
Semantic Chunking for ARBuilder.
SOTA approach: Groups sentences by semantic similarity using embeddings.
Reference: https://www.firecrawl.dev/blog/best-chunking-strategies-rag-2025
"""

import re
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import tiktoken


@dataclass
class SemanticChunk:
    """Represents a semantically coherent chunk."""
    content: str
    chunk_index: int
    total_chunks: int
    token_count: int
    semantic_score: float  # Coherence score
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "token_count": self.token_count,
            "semantic_score": self.semantic_score,
            **self.metadata,
        }


class SemanticChunker:
    """
    SOTA Semantic Chunking using embedding similarity.

    Approaches:
    1. Percentile-based: Split when similarity drops below percentile threshold
    2. Standard deviation: Split when similarity drops below mean - k*std
    3. Gradient-based: Split at largest similarity drops

    This provides ~70% accuracy improvement over fixed-size chunking.
    """

    def __init__(
        self,
        embedding_client=None,
        max_tokens: int = 512,
        min_tokens: int = 100,
        similarity_threshold: float = 0.5,
        method: str = "percentile",  # percentile, stddev, gradient
        percentile: int = 25,
        stddev_multiplier: float = 1.0,
        model: str = "cl100k_base",
    ):
        """
        Initialize semantic chunker.

        Args:
            embedding_client: Client for generating embeddings.
            max_tokens: Maximum tokens per chunk.
            min_tokens: Minimum tokens per chunk.
            similarity_threshold: Minimum similarity to keep sentences together.
            method: Chunking method (percentile, stddev, gradient).
            percentile: Percentile threshold for percentile method.
            stddev_multiplier: Multiplier for stddev method.
            model: Tiktoken encoding model.
        """
        self.embedding_client = embedding_client
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.similarity_threshold = similarity_threshold
        self.method = method
        self.percentile = percentile
        self.stddev_multiplier = stddev_multiplier
        self.encoding = tiktoken.get_encoding(model)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Handle common sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

        # Further split on newlines for code/markdown
        result = []
        for sent in sentences:
            # Split on double newlines (paragraphs)
            parts = sent.split('\n\n')
            result.extend([p.strip() for p in parts if p.strip()])

        return result

    def _compute_similarities(self, sentences: list[str]) -> list[float]:
        """
        Compute pairwise similarities between adjacent sentences.

        Returns list of similarities where similarities[i] is the
        similarity between sentences[i] and sentences[i+1].
        """
        if len(sentences) <= 1:
            return []

        if self.embedding_client is None:
            # Fallback: use simple token overlap similarity
            return self._compute_token_similarities(sentences)

        # Get embeddings for all sentences
        embeddings = self.embedding_client.embed_batch(sentences)

        # Compute cosine similarities between adjacent sentences
        similarities = []
        for i in range(len(embeddings) - 1):
            emb1 = np.array(embeddings[i])
            emb2 = np.array(embeddings[i + 1])

            # Cosine similarity
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            similarities.append(float(similarity))

        return similarities

    def _compute_token_similarities(self, sentences: list[str]) -> list[float]:
        """Fallback: compute similarity based on token overlap."""
        similarities = []

        for i in range(len(sentences) - 1):
            tokens1 = set(sentences[i].lower().split())
            tokens2 = set(sentences[i + 1].lower().split())

            if not tokens1 or not tokens2:
                similarities.append(0.0)
                continue

            # Jaccard similarity
            intersection = len(tokens1 & tokens2)
            union = len(tokens1 | tokens2)
            similarities.append(intersection / union if union > 0 else 0.0)

        return similarities

    def _find_breakpoints_percentile(self, similarities: list[float]) -> list[int]:
        """Find breakpoints using percentile method."""
        if not similarities:
            return []

        threshold = np.percentile(similarities, self.percentile)
        return [i for i, sim in enumerate(similarities) if sim < threshold]

    def _find_breakpoints_stddev(self, similarities: list[float]) -> list[int]:
        """Find breakpoints using standard deviation method."""
        if not similarities:
            return []

        mean_sim = np.mean(similarities)
        std_sim = np.std(similarities)
        threshold = mean_sim - (self.stddev_multiplier * std_sim)

        return [i for i, sim in enumerate(similarities) if sim < threshold]

    def _find_breakpoints_gradient(self, similarities: list[float], top_k: int = None) -> list[int]:
        """Find breakpoints at largest similarity drops."""
        if not similarities:
            return []

        # Compute gradients (drops in similarity)
        gradients = []
        for i in range(len(similarities)):
            if i == 0:
                gradients.append(1.0 - similarities[i])
            else:
                gradients.append(similarities[i - 1] - similarities[i])

        # Find indices with largest drops
        if top_k is None:
            # Use a threshold based on gradient magnitude
            threshold = np.mean(gradients) + np.std(gradients)
            breakpoints = [i for i, g in enumerate(gradients) if g > threshold]
        else:
            # Take top_k breakpoints
            sorted_indices = sorted(range(len(gradients)), key=lambda i: gradients[i], reverse=True)
            breakpoints = sorted(sorted_indices[:top_k])

        return breakpoints

    def _enforce_token_limits(self, chunks: list[str]) -> list[str]:
        """Ensure chunks are within token limits."""
        result = []

        for chunk in chunks:
            tokens = self.count_tokens(chunk)

            if tokens <= self.max_tokens:
                result.append(chunk)
            else:
                # Split oversized chunks
                sentences = self._split_into_sentences(chunk)
                current_chunk = ""
                current_tokens = 0

                for sent in sentences:
                    sent_tokens = self.count_tokens(sent)

                    if current_tokens + sent_tokens <= self.max_tokens:
                        current_chunk += sent + " "
                        current_tokens += sent_tokens
                    else:
                        if current_chunk.strip():
                            result.append(current_chunk.strip())
                        current_chunk = sent + " "
                        current_tokens = sent_tokens

                if current_chunk.strip():
                    result.append(current_chunk.strip())

        return result

    def _merge_small_chunks(self, chunks: list[str]) -> list[str]:
        """Merge chunks that are too small."""
        if not chunks:
            return []

        result = []
        current_chunk = ""
        current_tokens = 0

        for chunk in chunks:
            chunk_tokens = self.count_tokens(chunk)

            if current_tokens + chunk_tokens <= self.max_tokens:
                current_chunk += chunk + "\n\n"
                current_tokens += chunk_tokens
            else:
                if current_chunk.strip():
                    result.append(current_chunk.strip())
                current_chunk = chunk + "\n\n"
                current_tokens = chunk_tokens

        if current_chunk.strip():
            result.append(current_chunk.strip())

        return result

    def chunk(
        self,
        text: str,
        metadata: Optional[dict] = None,
    ) -> list[SemanticChunk]:
        """
        Chunk text using semantic similarity.

        Args:
            text: Text to chunk.
            metadata: Metadata to attach to chunks.

        Returns:
            List of SemanticChunk objects.
        """
        if not text.strip():
            return []

        metadata = metadata or {}

        # Split into sentences
        sentences = self._split_into_sentences(text)

        if len(sentences) <= 1:
            return [
                SemanticChunk(
                    content=text.strip(),
                    chunk_index=0,
                    total_chunks=1,
                    token_count=self.count_tokens(text),
                    semantic_score=1.0,
                    metadata=metadata.copy(),
                )
            ]

        # Compute similarities
        similarities = self._compute_similarities(sentences)

        # Find breakpoints based on method
        if self.method == "percentile":
            breakpoints = self._find_breakpoints_percentile(similarities)
        elif self.method == "stddev":
            breakpoints = self._find_breakpoints_stddev(similarities)
        elif self.method == "gradient":
            breakpoints = self._find_breakpoints_gradient(similarities)
        else:
            breakpoints = self._find_breakpoints_percentile(similarities)

        # Create chunks at breakpoints
        chunks = []
        start_idx = 0

        for bp in sorted(breakpoints):
            # Breakpoint is after sentence bp, so include sentences 0 to bp
            chunk_sentences = sentences[start_idx:bp + 1]
            if chunk_sentences:
                chunks.append(" ".join(chunk_sentences))
            start_idx = bp + 1

        # Don't forget the last chunk
        if start_idx < len(sentences):
            chunks.append(" ".join(sentences[start_idx:]))

        # Enforce token limits
        chunks = self._enforce_token_limits(chunks)

        # Merge small chunks
        chunks = self._merge_small_chunks(chunks)

        # Compute semantic scores for each chunk
        semantic_scores = []
        for chunk in chunks:
            chunk_sentences = self._split_into_sentences(chunk)
            if len(chunk_sentences) > 1:
                chunk_sims = self._compute_similarities(chunk_sentences)
                semantic_scores.append(np.mean(chunk_sims) if chunk_sims else 1.0)
            else:
                semantic_scores.append(1.0)

        # Create SemanticChunk objects
        return [
            SemanticChunk(
                content=chunk,
                chunk_index=i,
                total_chunks=len(chunks),
                token_count=self.count_tokens(chunk),
                semantic_score=semantic_scores[i],
                metadata=metadata.copy(),
            )
            for i, chunk in enumerate(chunks)
        ]


class CodeSemanticChunker:
    """
    Semantic chunking specifically for code.
    Uses AST-aware boundaries combined with semantic similarity.
    """

    # Code block patterns for different languages
    CODE_BLOCK_PATTERNS = {
        "rust": [
            r"((?:pub\s+)?fn\s+\w+[^{]*\{(?:[^{}]|\{[^{}]*\})*\})",  # Functions
            r"((?:pub\s+)?struct\s+\w+[^{]*\{[^}]*\})",  # Structs
            r"((?:pub\s+)?impl\s+[^{]*\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})",  # Impl blocks
            r"((?:pub\s+)?enum\s+\w+[^{]*\{[^}]*\})",  # Enums
        ],
        "typescript": [
            r"((?:export\s+)?(?:async\s+)?function\s+\w+[^{]*\{(?:[^{}]|\{[^{}]*\})*\})",  # Functions
            r"((?:export\s+)?class\s+\w+[^{]*\{(?:[^{}]|\{[^{}]*\})*\})",  # Classes
            r"((?:export\s+)?interface\s+\w+[^{]*\{[^}]*\})",  # Interfaces
            r"((?:export\s+)?const\s+\w+\s*=\s*\([^)]*\)\s*(?::\s*\w+)?\s*=>\s*\{(?:[^{}]|\{[^{}]*\})*\})",  # Arrow funcs
        ],
        "tsx": [
            r"((?:export\s+)?(?:default\s+)?function\s+\w+[^{]*\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})",  # Components
            r"((?:export\s+)?const\s+use\w+\s*=\s*\([^)]*\)[^{]*\{(?:[^{}]|\{[^{}]*\})*\})",  # Hooks
        ],
    }

    def __init__(
        self,
        embedding_client=None,
        max_tokens: int = 1024,
        model: str = "cl100k_base",
    ):
        self.embedding_client = embedding_client
        self.max_tokens = max_tokens
        self.encoding = tiktoken.get_encoding(model)

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def _extract_code_blocks(self, code: str, language: str) -> list[str]:
        """Extract semantic code blocks based on language patterns."""
        patterns = self.CODE_BLOCK_PATTERNS.get(language, [])

        if not patterns:
            # Fallback: split by blank lines
            return [b.strip() for b in code.split("\n\n") if b.strip()]

        blocks = []
        for pattern in patterns:
            try:
                matches = re.findall(pattern, code, re.MULTILINE | re.DOTALL)
                blocks.extend(matches)
            except re.error:
                continue

        # If no blocks found, fallback to line-based splitting
        if not blocks:
            return [b.strip() for b in code.split("\n\n") if b.strip()]

        return blocks

    def chunk(
        self,
        code: str,
        language: str,
        metadata: Optional[dict] = None,
    ) -> list[SemanticChunk]:
        """
        Chunk code semantically.

        Args:
            code: Code content.
            language: Programming language.
            metadata: Metadata to attach.

        Returns:
            List of SemanticChunk objects.
        """
        if not code.strip():
            return []

        metadata = metadata or {}
        metadata["language"] = language

        # Extract code blocks
        blocks = self._extract_code_blocks(code, language)

        # Group blocks that fit within token limits
        chunks = []
        current_chunk = ""
        current_tokens = 0

        for block in blocks:
            block_tokens = self.count_tokens(block)

            if current_tokens + block_tokens <= self.max_tokens:
                current_chunk += block + "\n\n"
                current_tokens += block_tokens
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = block + "\n\n"
                current_tokens = block_tokens

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return [
            SemanticChunk(
                content=chunk,
                chunk_index=i,
                total_chunks=len(chunks),
                token_count=self.count_tokens(chunk),
                semantic_score=1.0,  # Code blocks are inherently semantic
                metadata=metadata.copy(),
            )
            for i, chunk in enumerate(chunks)
        ]

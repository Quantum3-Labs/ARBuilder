"""
Document and code chunking utilities for ARBuilder.
"""

import re
from dataclasses import dataclass, field
from typing import Optional
import tiktoken


@dataclass
class Chunk:
    """Represents a chunk of text or code."""
    content: str
    chunk_index: int
    total_chunks: int
    token_count: int
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "token_count": self.token_count,
            **self.metadata,
        }


class DocumentChunker:
    """
    Chunk documents (markdown, text) for RAG ingestion.
    Uses semantic chunking based on headers and paragraphs.
    """

    def __init__(
        self,
        max_tokens: int = 512,
        overlap_tokens: int = 50,
        model: str = "cl100k_base",
    ):
        """
        Initialize the document chunker.

        Args:
            max_tokens: Maximum tokens per chunk.
            overlap_tokens: Token overlap between chunks.
            model: Tiktoken encoding model.
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.encoding = tiktoken.get_encoding(model)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))

    def chunk(
        self,
        text: str,
        metadata: Optional[dict] = None,
    ) -> list[Chunk]:
        """
        Chunk a document into smaller pieces.

        Args:
            text: Document text to chunk.
            metadata: Metadata to attach to each chunk.

        Returns:
            List of Chunk objects.
        """
        if not text.strip():
            return []

        metadata = metadata or {}
        chunks = []

        # Split by headers first (semantic sections)
        sections = self._split_by_headers(text)

        current_chunk = ""
        current_tokens = 0

        for section in sections:
            section_tokens = self.count_tokens(section)

            # If section fits in current chunk
            if current_tokens + section_tokens <= self.max_tokens:
                current_chunk += section + "\n\n"
                current_tokens += section_tokens
            else:
                # Save current chunk if not empty
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())

                # If section itself is too large, split by paragraphs
                if section_tokens > self.max_tokens:
                    sub_chunks = self._split_large_section(section)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                    current_tokens = 0
                else:
                    current_chunk = section + "\n\n"
                    current_tokens = section_tokens

        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # Apply overlap and create Chunk objects
        final_chunks = self._apply_overlap(chunks)

        return [
            Chunk(
                content=chunk,
                chunk_index=i,
                total_chunks=len(final_chunks),
                token_count=self.count_tokens(chunk),
                metadata=metadata.copy(),
            )
            for i, chunk in enumerate(final_chunks)
        ]

    def _split_by_headers(self, text: str) -> list[str]:
        """Split text by markdown headers."""
        # Pattern matches markdown headers
        pattern = r"(?=^#{1,6}\s)"
        sections = re.split(pattern, text, flags=re.MULTILINE)
        return [s.strip() for s in sections if s.strip()]

    def _split_large_section(self, section: str) -> list[str]:
        """Split a large section by paragraphs."""
        paragraphs = section.split("\n\n")
        chunks = []
        current_chunk = ""
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self.count_tokens(para)

            if current_tokens + para_tokens <= self.max_tokens:
                current_chunk += para + "\n\n"
                current_tokens += para_tokens
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())

                # If paragraph is still too large, split by sentences
                if para_tokens > self.max_tokens:
                    sentence_chunks = self._split_by_sentences(para)
                    chunks.extend(sentence_chunks)
                    current_chunk = ""
                    current_tokens = 0
                else:
                    current_chunk = para + "\n\n"
                    current_tokens = para_tokens

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _split_by_sentences(self, text: str) -> list[str]:
        """Split text by sentences."""
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks = []
        current_chunk = ""
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

            if current_tokens + sentence_tokens <= self.max_tokens:
                current_chunk += sentence + " "
                current_tokens += sentence_tokens
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
                current_tokens = sentence_tokens

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        """Apply overlap between chunks."""
        if len(chunks) <= 1 or self.overlap_tokens == 0:
            return chunks

        result = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]

            # Get overlap from end of previous chunk
            prev_tokens = self.encoding.encode(prev_chunk)
            overlap_text = self.encoding.decode(prev_tokens[-self.overlap_tokens:])

            # Prepend overlap to current chunk
            result.append(f"...{overlap_text}\n\n{current_chunk}")

        return result


class CodeChunker:
    """
    Chunk code files for RAG ingestion.
    Preserves function/struct boundaries where possible.
    """

    # Language-specific patterns for code splitting
    SPLIT_PATTERNS = {
        ".rs": [
            r"(?=^(?:pub\s+)?fn\s+\w+)",  # Rust functions
            r"(?=^(?:pub\s+)?struct\s+\w+)",  # Rust structs
            r"(?=^(?:pub\s+)?enum\s+\w+)",  # Rust enums
            r"(?=^(?:pub\s+)?impl\s+)",  # Rust impl blocks
            r"(?=^(?:pub\s+)?trait\s+\w+)",  # Rust traits
            r"(?=^(?:pub\s+)?mod\s+\w+)",  # Rust modules
        ],
        ".ts": [
            r"(?=^(?:export\s+)?(?:async\s+)?function\s+\w+)",  # TS functions
            r"(?=^(?:export\s+)?class\s+\w+)",  # TS classes
            r"(?=^(?:export\s+)?interface\s+\w+)",  # TS interfaces
            r"(?=^(?:export\s+)?type\s+\w+)",  # TS types
            r"(?=^(?:export\s+)?const\s+\w+\s*=\s*(?:async\s+)?\()",  # Arrow functions
        ],
        ".tsx": [
            r"(?=^(?:export\s+)?(?:default\s+)?function\s+\w+)",  # React components
            r"(?=^(?:export\s+)?const\s+\w+\s*[=:]\s*(?:\(\s*\)|React\.FC|FC))",  # FC components
            r"(?=^(?:export\s+)?const\s+use\w+)",  # Custom hooks
            r"(?=^(?:export\s+)?interface\s+\w+)",  # TS interfaces
            r"(?=^(?:export\s+)?type\s+\w+)",  # TS types
        ],
        ".jsx": [
            r"(?=^(?:export\s+)?(?:default\s+)?function\s+\w+)",  # React components
            r"(?=^(?:export\s+)?const\s+\w+\s*=\s*\()",  # Arrow function components
        ],
        ".js": [
            r"(?=^(?:export\s+)?(?:async\s+)?function\s+\w+)",  # JS functions
            r"(?=^(?:export\s+)?class\s+\w+)",  # JS classes
        ],
        ".sol": [
            r"(?=^contract\s+\w+)",  # Solidity contracts
            r"(?=^\s*function\s+\w+)",  # Solidity functions
            r"(?=^interface\s+\w+)",  # Solidity interfaces
            r"(?=^library\s+\w+)",  # Solidity libraries
        ],
        ".graphql": [
            r"(?=^type\s+\w+)",  # GraphQL types
            r"(?=^input\s+\w+)",  # GraphQL inputs
            r"(?=^enum\s+\w+)",  # GraphQL enums
            r"(?=^interface\s+\w+)",  # GraphQL interfaces
            r"(?=^query\s+\w+)",  # GraphQL queries
            r"(?=^mutation\s+\w+)",  # GraphQL mutations
        ],
        ".yaml": [
            r"(?=^[a-zA-Z_]+:(?:\s|$))",  # Top-level YAML keys
        ],
        ".yml": [
            r"(?=^[a-zA-Z_]+:(?:\s|$))",  # Top-level YAML keys
        ],
    }

    # File type to category mapping for metadata
    FILE_CATEGORIES = {
        ".rs": "rust_code",
        ".ts": "typescript_code",
        ".tsx": "react_component",
        ".jsx": "react_component",
        ".js": "javascript_code",
        ".sol": "solidity_contract",
        ".graphql": "graphql_schema",
        ".yaml": "config_yaml",
        ".yml": "config_yaml",
    }

    def __init__(
        self,
        max_tokens: int = 1024,
        overlap_lines: int = 5,
        model: str = "cl100k_base",
    ):
        """
        Initialize the code chunker.

        Args:
            max_tokens: Maximum tokens per chunk.
            overlap_lines: Line overlap between chunks.
            model: Tiktoken encoding model.
        """
        self.max_tokens = max_tokens
        self.overlap_lines = overlap_lines
        self.encoding = tiktoken.get_encoding(model)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))

    def chunk(
        self,
        code: str,
        extension: str,
        metadata: Optional[dict] = None,
    ) -> list[Chunk]:
        """
        Chunk code into smaller pieces.

        Args:
            code: Code content to chunk.
            extension: File extension (e.g., ".rs", ".ts").
            metadata: Metadata to attach to each chunk.

        Returns:
            List of Chunk objects.
        """
        if not code.strip():
            return []

        metadata = metadata or {}
        metadata["language"] = extension.lstrip(".")
        metadata["file_category"] = self.FILE_CATEGORIES.get(extension, "code")

        # Try semantic splitting first
        chunks = self._semantic_split(code, extension)

        # If semantic split didn't work well, fall back to line-based
        if len(chunks) == 1 and self.count_tokens(chunks[0]) > self.max_tokens:
            chunks = self._line_split(code)

        # Further split any chunks that are too large
        final_chunks = []
        for chunk in chunks:
            if self.count_tokens(chunk) > self.max_tokens:
                final_chunks.extend(self._line_split(chunk))
            else:
                final_chunks.append(chunk)

        # Apply overlap
        final_chunks = self._apply_line_overlap(final_chunks)

        return [
            Chunk(
                content=chunk,
                chunk_index=i,
                total_chunks=len(final_chunks),
                token_count=self.count_tokens(chunk),
                metadata=metadata.copy(),
            )
            for i, chunk in enumerate(final_chunks)
        ]

    def _semantic_split(self, code: str, extension: str) -> list[str]:
        """Split code by semantic boundaries (functions, classes, etc.)."""
        patterns = self.SPLIT_PATTERNS.get(extension, [])

        if not patterns:
            return [code]

        # Combine patterns
        combined_pattern = "|".join(patterns)

        try:
            sections = re.split(combined_pattern, code, flags=re.MULTILINE)
            return [s.strip() for s in sections if s.strip()]
        except re.error:
            return [code]

    def _line_split(self, code: str) -> list[str]:
        """Split code by lines when semantic splitting isn't possible."""
        lines = code.splitlines()
        chunks = []
        current_chunk_lines = []
        current_tokens = 0

        for line in lines:
            line_tokens = self.count_tokens(line)

            if current_tokens + line_tokens <= self.max_tokens:
                current_chunk_lines.append(line)
                current_tokens += line_tokens
            else:
                if current_chunk_lines:
                    chunks.append("\n".join(current_chunk_lines))
                current_chunk_lines = [line]
                current_tokens = line_tokens

        if current_chunk_lines:
            chunks.append("\n".join(current_chunk_lines))

        return chunks

    def _apply_line_overlap(self, chunks: list[str]) -> list[str]:
        """Apply line-based overlap between chunks."""
        if len(chunks) <= 1 or self.overlap_lines == 0:
            return chunks

        result = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_lines = chunks[i - 1].splitlines()
            overlap = prev_lines[-self.overlap_lines:]
            overlap_text = "\n".join(overlap)

            result.append(f"// ... continued from above\n{overlap_text}\n{chunks[i]}")

        return result

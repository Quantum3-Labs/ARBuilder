"""
Text cleaning utilities for ARBuilder preprocessing.
"""

import re
from typing import Optional


class TextCleaner:
    """Clean and normalize text content from scraped data."""

    # Patterns to remove
    NOISE_PATTERNS = [
        # GitHub UI elements
        r"Skip to content",
        r"Navigation Menu",
        r"Toggle navigation",
        r"Sign in",
        r"Sign up",
        r"Breadcrumbs",
        r"Footer",
        r"© \d{4} GitHub, Inc\.",
        r"You signed in with another tab or window\.",
        r"Reload to refresh your session\.",
        r"You signed out in another tab or window\.",
        # Common navigation elements
        r"Previous\s*Next",
        r"On this page",
        r"Table of contents",
        r"Edit this page",
        r"View on GitHub",
        # Cookie/privacy notices
        r"We use.*?cookies.*?(?:\.|$)",
        r"Accept all cookies",
        r"Privacy Policy",
        # Documentation navigation artifacts
        r"Search\.\.\.",
        r"Ctrl\s*K",
        r"⌘\s*K",
    ]

    # Markdown cleanup patterns
    MARKDOWN_CLEANUP = [
        # Multiple consecutive blank lines -> single blank line
        (r"\n{3,}", "\n\n"),
        # Multiple spaces -> single space
        (r"[ \t]+", " "),
        # Remove leading/trailing whitespace from lines
        (r"^[ \t]+|[ \t]+$", ""),
        # Clean up broken markdown links
        (r"\[\s*\]\(\s*\)", ""),
        # Remove empty markdown headers
        (r"^#+\s*$", ""),
    ]

    def __init__(self, remove_code_blocks: bool = False):
        """
        Initialize the text cleaner.

        Args:
            remove_code_blocks: If True, remove code blocks from text.
        """
        self.remove_code_blocks = remove_code_blocks
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        self.noise_regex = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in self.NOISE_PATTERNS
        ]
        self.cleanup_regex = [
            (re.compile(pattern, re.MULTILINE), replacement)
            for pattern, replacement in self.MARKDOWN_CLEANUP
        ]

    def clean(self, text: str) -> str:
        """
        Clean text content.

        Args:
            text: Raw text to clean.

        Returns:
            Cleaned text.
        """
        if not text:
            return ""

        # Remove noise patterns
        for pattern in self.noise_regex:
            text = pattern.sub("", text)

        # Remove code blocks if requested
        if self.remove_code_blocks:
            text = re.sub(r"```[\s\S]*?```", "", text)
            text = re.sub(r"`[^`]+`", "", text)

        # Apply cleanup patterns
        for pattern, replacement in self.cleanup_regex:
            text = pattern.sub(replacement, text)

        # Final cleanup
        text = text.strip()

        return text

    def clean_code(self, code: str, language: Optional[str] = None) -> str:
        """
        Clean code content while preserving structure.

        Args:
            code: Raw code to clean.
            language: Programming language (for language-specific cleaning).

        Returns:
            Cleaned code.
        """
        if not code:
            return ""

        lines = code.splitlines()
        cleaned_lines = []

        for line in lines:
            # Remove trailing whitespace but preserve indentation
            cleaned_line = line.rstrip()
            cleaned_lines.append(cleaned_line)

        # Remove excessive blank lines (more than 2 consecutive)
        result = []
        blank_count = 0
        for line in cleaned_lines:
            if not line.strip():
                blank_count += 1
                if blank_count <= 2:
                    result.append(line)
            else:
                blank_count = 0
                result.append(line)

        return "\n".join(result).strip()

    def extract_title(self, text: str) -> Optional[str]:
        """
        Extract title from markdown content.

        Args:
            text: Markdown text.

        Returns:
            Extracted title or None.
        """
        # Look for H1 header
        match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if match:
            return match.group(1).strip()

        # Look for first non-empty line
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line[:100]  # Limit length

        return None

    def remove_frontmatter(self, text: str) -> str:
        """
        Remove YAML frontmatter from markdown.

        Args:
            text: Markdown text with potential frontmatter.

        Returns:
            Text without frontmatter.
        """
        # Match YAML frontmatter (--- ... ---)
        pattern = r"^---\s*\n[\s\S]*?\n---\s*\n"
        return re.sub(pattern, "", text)

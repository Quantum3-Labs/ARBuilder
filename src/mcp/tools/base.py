"""
Base class for MCP tools.
"""

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "openai/gpt-oss-120b")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "qwen/qwen3.5-flash-02-23")


@dataclass
class ToolResult:
    """Standard result format for all tools."""
    success: bool
    data: dict = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        if self.error:
            return {"error": self.error}
        return self.data


class BaseTool(ABC):
    """
    Base class for all MCP tools.

    Provides common functionality like LLM calls and error handling.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        """
        Initialize the tool.

        Args:
            api_key: OpenRouter API key.
            model: Default model to use.
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
            timeout=120.0,
        )

    @abstractmethod
    def execute(self, **kwargs) -> dict:
        """
        Execute the tool with given parameters.

        Returns:
            Tool result as a dictionary.
        """
        pass

    def _call_llm(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        model: Optional[str] = None,
    ) -> str:
        """
        Make an LLM API call with production-grade resilience.

        Strategy:
        1. Try primary model up to 3 times with exponential backoff (1s, 2s, 4s)
        2. On finish_reason="length" (truncation), increase max_tokens by 1.5x
        3. On empty response or transient error, retry with backoff
        4. After primary model exhausted, try fallback model up to 2 times
        5. Returns "" only after ALL attempts fail

        Never throws — callers can use their own fallback logic.

        Args:
            messages: List of message dicts with role and content.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            model: Model to use (defaults to self.model).

        Returns:
            Generated text content, or "" on failure.
        """
        primary_model = model or self.model
        current_max_tokens = max_tokens
        primary_attempts = 3

        # Phase 1: Primary model — 3 attempts with escalation
        for attempt in range(primary_attempts):
            try:
                response = self.client.post(
                    "/chat/completions",
                    json={
                        "model": primary_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": current_max_tokens,
                    },
                )

                # Non-retryable client errors — skip to fallback
                if response.status_code in (400, 401, 403):
                    logger.error(
                        "[_call_llm] Non-retryable %d: %s",
                        response.status_code,
                        response.text[:200],
                    )
                    break

                # Retryable server errors — retry after backoff
                if response.status_code == 429 or response.status_code >= 500:
                    logger.warning(
                        "[_call_llm] HTTP %d (attempt %d/%d), retrying...",
                        response.status_code,
                        attempt + 1,
                        primary_attempts,
                    )
                    time.sleep(min(2**attempt, 4))
                    continue

                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                finish_reason = data["choices"][0].get("finish_reason", "unknown")

                # Truncation — escalate max_tokens and retry
                if finish_reason == "length":
                    old_tokens = current_max_tokens
                    current_max_tokens = min(int(current_max_tokens * 1.5), 32000)
                    logger.warning(
                        "[_call_llm] Truncated (attempt %d/%d). "
                        "Escalating max_tokens: %d → %d",
                        attempt + 1,
                        primary_attempts,
                        old_tokens,
                        current_max_tokens,
                    )
                    # On last attempt, use truncated content if non-empty
                    if attempt == primary_attempts - 1 and content and content.strip():
                        logger.warning("[_call_llm] Using truncated response on final primary attempt")
                        return content
                    # No backoff on truncation — retry immediately with higher max_tokens
                    continue

                if content and content.strip():
                    return content

                # Empty response — retry immediately (no backoff)
                logger.warning(
                    "[_call_llm] Empty response (attempt %d/%d). "
                    "Model: %s, finish_reason: %s",
                    attempt + 1,
                    primary_attempts,
                    data.get("model", "unknown"),
                    finish_reason,
                )

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                logger.warning(
                    "[_call_llm] Network error (attempt %d/%d): %s",
                    attempt + 1,
                    primary_attempts,
                    str(e),
                )
                time.sleep(min(2**attempt, 4))

            except Exception as e:
                logger.error("[_call_llm] Unexpected error: %s", str(e))
                break  # Don't retry unknown errors — skip to fallback

        # Phase 2: Fallback model — 2 attempts
        fallback_attempts = 2
        logger.warning(
            "[_call_llm] Primary model %s exhausted. Trying fallback: %s",
            primary_model,
            FALLBACK_MODEL,
        )

        for attempt in range(fallback_attempts):
            try:
                response = self.client.post(
                    "/chat/completions",
                    json={
                        "model": FALLBACK_MODEL,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": current_max_tokens,
                    },
                )

                if response.status_code in (400, 401, 403):
                    logger.error(
                        "[_call_llm] Fallback non-retryable %d: %s",
                        response.status_code,
                        response.text[:200],
                    )
                    break

                if response.status_code == 429 or response.status_code >= 500:
                    logger.warning(
                        "[_call_llm] Fallback HTTP %d (attempt %d/%d)",
                        response.status_code,
                        attempt + 1,
                        fallback_attempts,
                    )
                    time.sleep(min(2**attempt, 4))
                    continue

                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]

                if content and content.strip():
                    logger.warning(
                        "[_call_llm] Fallback succeeded: %s (%d tokens)",
                        data.get("model", "unknown"),
                        data.get("usage", {}).get("total_tokens", 0),
                    )
                    return content

                logger.warning(
                    "[_call_llm] Fallback empty (attempt %d/%d)",
                    attempt + 1,
                    fallback_attempts,
                )

            except Exception as e:
                logger.warning(
                    "[_call_llm] Fallback error (attempt %d/%d): %s",
                    attempt + 1,
                    fallback_attempts,
                    str(e),
                )
                time.sleep(min(2**attempt, 4))

        logger.error(
            "[_call_llm] All attempts failed. Primary: %s (%dx), Fallback: %s (%dx). "
            "max_tokens escalated to %d",
            primary_model,
            primary_attempts,
            FALLBACK_MODEL,
            fallback_attempts,
            current_max_tokens,
        )
        return ""

    def _validate_required(self, kwargs: dict, required: list[str]) -> Optional[str]:
        """
        Validate required parameters.

        Args:
            kwargs: Input parameters.
            required: List of required parameter names.

        Returns:
            Error message if validation fails, None otherwise.
        """
        missing = [r for r in required if not kwargs.get(r)]
        if missing:
            return f"Missing required parameters: {', '.join(missing)}"
        return None

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

"""
Base class for MCP tools.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek/deepseek-chat")


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
        Make an LLM API call.

        Args:
            messages: List of message dicts with role and content.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            model: Model to use (defaults to self.model).

        Returns:
            Generated text content.
        """
        response = self.client.post(
            "/chat/completions",
            json={
                "model": model or self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]

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

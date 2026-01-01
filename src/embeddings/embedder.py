"""
Embedding generation for ARBuilder using OpenRouter API.
"""

import logging
import os
import time
from typing import Optional

import httpx
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEFAULT_EMBEDDING_MODEL = os.getenv("DEFAULT_EMBEDDING", "google/gemini-embedding-001")

# Configure logging
logger = logging.getLogger(__name__)


class EmbeddingAPIError(Exception):
    """Custom exception for embedding API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self):
        parts = [super().__str__()]
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        if self.response_body:
            parts.append(f"Response: {self.response_body[:500]}")
        return " | ".join(parts)


class EmbeddingClient:
    """
    Client for generating embeddings via OpenRouter API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        """
        Initialize the embedding client.

        Args:
            api_key: OpenRouter API key. Defaults to env var.
            model: Embedding model to use. Defaults to env var.
            base_url: OpenRouter API base URL.
        """
        self.api_key = api_key or OPENROUTER_API_KEY
        self.model = model or DEFAULT_EMBEDDING_MODEL
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

    def _is_retryable_error(self, status_code: int) -> bool:
        """Check if an HTTP error is retryable."""
        # Retry on rate limits (429) and server errors (5xx)
        return status_code == 429 or status_code >= 500

    def _parse_embedding_response(self, data: dict, expected_count: int = 1) -> list[list[float]]:
        """
        Parse embedding response with validation.

        Args:
            data: Raw API response data.
            expected_count: Expected number of embeddings.

        Returns:
            List of embedding vectors.

        Raises:
            EmbeddingAPIError: If response format is invalid.
        """
        if "error" in data:
            error_msg = data.get("error", {})
            if isinstance(error_msg, dict):
                error_msg = error_msg.get("message", str(error_msg))
            raise EmbeddingAPIError(f"API returned error: {error_msg}")

        if "data" not in data:
            raise EmbeddingAPIError(
                f"Invalid response format: missing 'data' field",
                response_body=str(data)[:500]
            )

        embeddings_data = data["data"]
        if not isinstance(embeddings_data, list) or len(embeddings_data) == 0:
            raise EmbeddingAPIError(
                f"Invalid response format: 'data' is empty or not a list",
                response_body=str(data)[:500]
            )

        # Sort by index to maintain order
        sorted_data = sorted(embeddings_data, key=lambda x: x.get("index", 0))

        embeddings = []
        for i, item in enumerate(sorted_data):
            if "embedding" not in item:
                raise EmbeddingAPIError(
                    f"Invalid response format: missing 'embedding' in item {i}",
                    response_body=str(item)[:200]
                )
            embeddings.append(item["embedding"])

        return embeddings

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException, EmbeddingAPIError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def embed(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector as list of floats.

        Raises:
            EmbeddingAPIError: If embedding generation fails after retries.
        """
        try:
            response = self.client.post(
                "/embeddings",
                json={
                    "model": self.model,
                    "input": text,
                },
            )
        except httpx.TimeoutException as e:
            logger.warning(f"Timeout while generating embedding: {e}")
            raise

        # Handle HTTP errors with detailed logging
        if response.status_code != 200:
            response_text = response.text[:500] if response.text else "No response body"
            logger.error(
                f"Embedding API error: status={response.status_code}, "
                f"model={self.model}, response={response_text}"
            )

            if self._is_retryable_error(response.status_code):
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=response.request,
                    response=response
                )
            else:
                raise EmbeddingAPIError(
                    f"Non-retryable API error",
                    status_code=response.status_code,
                    response_body=response_text
                )

        try:
            data = response.json()
        except Exception as e:
            logger.error(f"Failed to parse embedding response as JSON: {e}")
            raise EmbeddingAPIError(f"Invalid JSON response: {e}", response_body=response.text[:500])

        embeddings = self._parse_embedding_response(data, expected_count=1)
        return embeddings[0]

    def _embed_batch_single(self, batch: list[str], batch_index: int) -> list[list[float]]:
        """
        Generate embeddings for a single batch with retry logic.

        Args:
            batch: List of texts to embed.
            batch_index: Index of this batch (for logging).

        Returns:
            List of embedding vectors.
        """
        max_retries = 5
        base_delay = 2

        for attempt in range(max_retries):
            try:
                response = self.client.post(
                    "/embeddings",
                    json={
                        "model": self.model,
                        "input": batch,
                    },
                )
            except httpx.TimeoutException as e:
                logger.warning(
                    f"Timeout on batch {batch_index}, attempt {attempt + 1}/{max_retries}: {e}"
                )
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.info(f"Retrying batch {batch_index} in {delay}s...")
                    time.sleep(delay)
                    continue
                raise EmbeddingAPIError(f"Timeout after {max_retries} attempts on batch {batch_index}")

            # Handle HTTP errors
            if response.status_code != 200:
                response_text = response.text[:500] if response.text else "No response body"
                logger.warning(
                    f"Batch {batch_index} API error (attempt {attempt + 1}/{max_retries}): "
                    f"status={response.status_code}, response={response_text}"
                )

                if self._is_retryable_error(response.status_code) and attempt < max_retries - 1:
                    # Exponential backoff with extra delay for rate limits
                    delay = base_delay * (2 ** attempt)
                    if response.status_code == 429:
                        delay = max(delay, 10)  # Minimum 10s for rate limits
                        logger.info(f"Rate limited. Waiting {delay}s before retry...")
                    else:
                        logger.info(f"Server error. Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    raise EmbeddingAPIError(
                        f"API error on batch {batch_index}",
                        status_code=response.status_code,
                        response_body=response_text
                    )

            # Parse response
            try:
                data = response.json()
            except Exception as e:
                logger.error(f"Failed to parse batch {batch_index} response as JSON: {e}")
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                raise EmbeddingAPIError(
                    f"Invalid JSON response on batch {batch_index}",
                    response_body=response.text[:500]
                )

            # Validate and extract embeddings
            try:
                embeddings = self._parse_embedding_response(data, expected_count=len(batch))
                return embeddings
            except EmbeddingAPIError as e:
                logger.warning(f"Batch {batch_index} parse error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                raise

        raise EmbeddingAPIError(f"Failed to process batch {batch_index} after {max_retries} attempts")

    def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 50,  # Reduced from 100 for better rate limit handling
    ) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of texts to embed.
            batch_size: Number of texts per API call (default: 50).

        Returns:
            List of embedding vectors.

        Raises:
            EmbeddingAPIError: If embedding generation fails after retries.
        """
        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        logger.info(f"Processing {len(texts)} texts in {total_batches} batches (batch_size={batch_size})")

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_index = i // batch_size + 1

            try:
                embeddings = self._embed_batch_single(batch, batch_index)
                all_embeddings.extend(embeddings)
                logger.debug(f"Batch {batch_index}/{total_batches} completed: {len(embeddings)} embeddings")
            except EmbeddingAPIError as e:
                logger.error(f"Failed to process batch {batch_index}/{total_batches}: {e}")
                raise

            # Rate limiting between batches
            if i + batch_size < len(texts):
                time.sleep(1.0)  # Increased from 0.5 for better rate limit handling

        logger.info(f"Successfully generated {len(all_embeddings)} embeddings")
        return all_embeddings

    def get_dimension(self) -> int:
        """Get the embedding dimension by running a test embedding."""
        test_embedding = self.embed("test")
        return len(test_embedding)

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

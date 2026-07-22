"""LLM client for communicating with Ollama or other providers."""

import os
import time
import logging
from typing import Optional
import requests

from agent.core.config import LLMConfig

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 1.0
RETRY_BACKOFF = 2.0


class LLMClient:
    """Client for LLM API calls with retry logic and error handling."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.session = requests.Session()
        self._verify_connection()

    def _verify_connection(self) -> None:
        """Verify that the LLM provider is reachable."""
        try:
            response = self.session.get(
                f"{self.config.base_url}/api/tags",
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            logger.info(f"Connected to {self.config.provider} at {self.config.base_url}")
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Failed to connect to {self.config.provider} at {self.config.base_url}: {e}"
            )
            raise ConnectionError(
                f"Cannot reach {self.config.provider} at {self.config.base_url}. "
                f"Ensure it is running and accessible."
            ) from e

    def generate(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
    ) -> str:
        """Generate a response from the LLM with automatic retries.

        Args:
            messages: Conversation messages in API format.
            tools: Optional tool definitions.

        Returns:
            The LLM response text.

        Raises:
            RuntimeError: If all retries are exhausted.
        """
        if not messages:
            raise ValueError("messages cannot be empty")

        payload = self._build_payload(messages, tools)
        delay = RETRY_DELAY

        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(f"LLM request attempt {attempt + 1}/{MAX_RETRIES}")
                response = self.session.post(
                    f"{self.config.base_url}/api/generate",
                    json=payload,
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                result = response.json()

                if "response" not in result:
                    raise ValueError("Invalid response format: missing 'response' field")

                return result["response"].strip()

            except requests.exceptions.Timeout:
                logger.warning(
                    f"LLM request timeout (attempt {attempt + 1}/{MAX_RETRIES}). "
                    f"Retrying in {delay}s..."
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(delay)
                    delay *= RETRY_BACKOFF
                else:
                    raise RuntimeError(
                        f"LLM request failed after {MAX_RETRIES} attempts due to timeout"
                    )

            except requests.exceptions.ConnectionError as e:
                logger.warning(
                    f"LLM connection error (attempt {attempt + 1}/{MAX_RETRIES}): {e}. "
                    f"Retrying in {delay}s..."
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(delay)
                    delay *= RETRY_BACKOFF
                else:
                    raise RuntimeError(
                        f"LLM connection failed after {MAX_RETRIES} attempts"
                    ) from e

            except requests.exceptions.HTTPError as e:
                if response.status_code >= 500:
                    logger.warning(
                        f"LLM server error {response.status_code} "
                        f"(attempt {attempt + 1}/{MAX_RETRIES}). Retrying in {delay}s..."
                    )
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(delay)
                        delay *= RETRY_BACKOFF
                    else:
                        raise RuntimeError(
                            f"LLM server returned {response.status_code} after {MAX_RETRIES} attempts"
                        ) from e
                else:
                    raise RuntimeError(
                        f"LLM request failed with status {response.status_code}: {response.text}"
                    ) from e

            except ValueError as e:
                raise RuntimeError(f"LLM response parsing failed: {e}") from e

        raise RuntimeError(f"LLM request failed after {MAX_RETRIES} attempts")

    def _build_payload(self, messages: list[dict], tools: Optional[list[dict]] = None) -> dict:
        """Build the API request payload."""
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        payload = {
            "model": self.config.model,
            "messages": formatted_messages,
            "temperature": self.config.temperature,
            "stream": False,
        }

        if tools:
            payload["tools"] = tools

        return payload

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

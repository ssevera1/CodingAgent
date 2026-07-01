"""LLM client for communicating with Ollama or other providers."""

import os
import time
import logging
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with LLM providers."""

    def __init__(self, config):
        self.config = config
        self.session = self._create_session()
        self._verify_connection()

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _verify_connection(self) -> None:
        """Verify that the LLM provider is reachable."""
        try:
            url = f"{self.config.llm.base_url}/api/tags"
            self.session.get(url, timeout=5)
            logger.debug(f"LLM provider reachable at {self.config.llm.base_url}")
        except requests.RequestException as e:
            logger.warning(
                f"Failed to connect to LLM provider at {self.config.llm.base_url}: {e}. "
                f"Will retry on first request."
            )

    def complete(
        self,
        messages: list[dict],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Send a completion request to the LLM.

        Args:
            messages: List of message dicts with role and content.
            max_tokens: Max tokens in response (uses config default if None).
            temperature: Sampling temperature (uses config default if None).

        Returns:
            The assistant's response text.

        Raises:
            RuntimeError: If the LLM provider is unreachable or returns an error.
            ValueError: If the response is malformed.
        """
        if not messages:
            raise ValueError("messages cannot be empty")

        if any(not isinstance(m, dict) or "role" not in m or "content" not in m for m in messages):
            raise ValueError("Each message must have 'role' and 'content' keys")

        max_tokens = max_tokens or self.config.llm.max_tokens
        temperature = temperature if temperature is not None else self.config.llm.temperature

        payload = {
            "model": self.config.llm.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        url = f"{self.config.llm.base_url}/api/chat"
        timeout = self.config.llm.timeout

        try:
            logger.debug(
                f"Sending request to {self.config.llm.model} "
                f"({len(messages)} messages, max_tokens={max_tokens})"
            )
            response = self.session.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
        except requests.Timeout:
            raise RuntimeError(
                f"LLM request timed out after {timeout}s. "
                f"Check {self.config.llm.base_url} and increase llm.timeout if needed."
            )
        except requests.ConnectionError as e:
            raise RuntimeError(
                f"Failed to connect to LLM provider at {self.config.llm.base_url}: {e}"
            )
        except requests.HTTPError as e:
            error_msg = response.text if response else str(e)
            logger.error(f"LLM provider returned error: {error_msg}")
            raise RuntimeError(f"LLM provider error: {error_msg}")

        try:
            data = response.json()
        except ValueError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

        if "message" not in data or "content" not in data["message"]:
            raise ValueError(
                f"Unexpected response schema from LLM. Expected 'message.content', got: {list(data.keys())}"
            )

        content = data["message"]["content"]
        if not isinstance(content, str):
            raise ValueError(f"Expected response content to be string, got {type(content).__name__}")

        if not content.strip():
            logger.warning("LLM returned empty response")

        logger.debug(f"Received response ({len(content)} chars)")
        return content

    def close(self) -> None:
        """Close the session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

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
    """Client for LLM API calls with retry logic and error handling."""

    def __init__(self, config):
        self.config = config
        self.session = self._create_session()

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

    def complete(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Request a completion from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            temperature: Override config temperature if provided.
            max_tokens: Override config max_tokens if provided.

        Returns:
            The assistant's response text.

        Raises:
            RuntimeError: If the LLM is unreachable or returns an error.
            ValueError: If messages is empty or malformed.
        """
        if not messages:
            raise ValueError("messages list cannot be empty")

        if not isinstance(messages, list):
            raise ValueError("messages must be a list")

        for msg in messages:
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                raise ValueError(
                    "Each message must be a dict with 'role' and 'content' keys"
                )

        temp = temperature if temperature is not None else self.config.llm.temperature
        tokens = max_tokens if max_tokens is not None else self.config.llm.max_tokens

        payload = {
            "model": self.config.llm.model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": tokens,
        }

        url = f"{self.config.llm.base_url}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}

        try:
            logger.debug(
                f"LLM request to {url} with model {self.config.llm.model}, "
                f"{len(messages)} messages"
            )
            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.config.llm.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            msg = f"Cannot connect to LLM at {self.config.llm.base_url}: {e}"
            logger.error(msg)
            raise RuntimeError(msg) from e
        except requests.exceptions.Timeout as e:
            msg = f"LLM request timed out after {self.config.llm.timeout}s: {e}"
            logger.error(msg)
            raise RuntimeError(msg) from e
        except requests.exceptions.HTTPError as e:
            msg = f"LLM returned HTTP {response.status_code}: {response.text[:200]}"
            logger.error(msg)
            raise RuntimeError(msg) from e
        except requests.exceptions.RequestException as e:
            msg = f"LLM request failed: {e}"
            logger.error(msg)
            raise RuntimeError(msg) from e

        try:
            data = response.json()
        except ValueError as e:
            msg = f"LLM returned invalid JSON: {response.text[:200]}"
            logger.error(msg)
            raise RuntimeError(msg) from e

        if "error" in data:
            msg = f"LLM error: {data['error']}"
            logger.error(msg)
            raise RuntimeError(msg)

        if "choices" not in data or not data["choices"]:
            msg = f"LLM returned empty choices: {data}"
            logger.error(msg)
            raise RuntimeError(msg)

        choice = data["choices"][0]
        if "message" not in choice or "content" not in choice["message"]:
            msg = f"LLM returned malformed choice: {choice}"
            logger.error(msg)
            raise RuntimeError(msg)

        content = choice["message"]["content"]
        if not content:
            logger.warning("LLM returned empty content")
            return ""

        logger.debug(f"LLM response: {len(content)} chars")
        return content

    def check_health(self) -> bool:
        """Check if the LLM service is reachable and responsive.

        Returns:
            True if the service is healthy, False otherwise.
        """
        url = f"{self.config.llm.base_url}/api/tags"
        try:
            response = self.session.get(url, timeout=5)
            is_healthy = response.status_code == 200
            if is_healthy:
                logger.debug(f"LLM health check passed")
            else:
                logger.warning(
                    f"LLM health check returned status {response.status_code}"
                )
            return is_healthy
        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            return False

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

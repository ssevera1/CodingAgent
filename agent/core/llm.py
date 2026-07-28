"""LLM client for communicating with Ollama."""

import json
import time
import logging
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from agent.core.config import LLMConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with Ollama LLM."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def chat(self, messages: list[dict]) -> str:
        """Send a chat request to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.

        Returns:
            The assistant's response text.

        Raises:
            RuntimeError: If the request fails or times out.
            ValueError: If the response is malformed.
        """
        if not messages:
            raise ValueError("messages cannot be empty")

        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        url = f"{self.config.base_url}/api/chat"
        logger.debug(f"Sending chat request to {url} with model {self.config.model}")

        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error(
                f"LLM request timed out after {self.config.timeout}s. "
                f"Check if Ollama is running at {self.config.base_url}"
            )
            raise RuntimeError(
                f"LLM request timed out. Ensure Ollama is running at {self.config.base_url}"
            )
        except requests.exceptions.ConnectionError as e:
            logger.error(
                f"Failed to connect to LLM at {self.config.base_url}. "
                f"Is Ollama running?"
            )
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.config.base_url}. "
                f"Ensure Ollama is running: ollama serve"
            ) from e
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                logger.error(
                    f"Model '{self.config.model}' not found. "
                    f"Pull it with: ollama pull {self.config.model}"
                )
                raise RuntimeError(
                    f"Model '{self.config.model}' not found. "
                    f"Pull it with: ollama pull {self.config.model}"
                ) from e
            logger.error(f"LLM request failed with status {response.status_code}")
            raise RuntimeError(
                f"LLM request failed: {response.status_code}"
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM request failed: {e}")
            raise RuntimeError(f"LLM request failed: {e}") from e

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {response.text}")
            raise ValueError(f"Invalid JSON in LLM response") from e

        if "message" not in data or "content" not in data.get("message", {}):
            logger.error(f"Unexpected response structure: {data}")
            raise ValueError("LLM response missing message.content field")

        content = data["message"]["content"]
        if not isinstance(content, str):
            logger.error(f"Expected string content, got {type(content).__name__}")
            raise ValueError(f"LLM response content is not a string")

        if not content.strip():
            logger.warning("LLM returned empty response")
            raise ValueError("LLM returned empty response")

        logger.debug(f"Received response: {len(content)} characters")
        return content

    def health_check(self) -> bool:
        """Check if Ollama is reachable and the model is available.

        Returns:
            True if healthy, False otherwise.
        """
        try:
            response = self.session.get(
                f"{self.config.base_url}/api/tags",
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()
            models = data.get("models", [])
            model_names = [m.get("name", "") for m in models]
            available = any(self.config.model in name for name in model_names)
            logger.debug(
                f"Health check: Ollama running, "
                f"model available={available}"
            )
            return available
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

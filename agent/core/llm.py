"""LLM client for communicating with Ollama or other providers."""

import os
import time
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from agent.core.config import LLMConfig


class LLMClient:
    """Client for LLM API calls with retry logic and timeout handling."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with exponential backoff retry strategy."""
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

    def chat(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """Call the LLM chat endpoint.

        Args:
            messages: List of message dicts with role and content.
            temperature: Override config temperature if provided.
            max_tokens: Override config max_tokens if provided.

        Returns:
            Response dict from LLM API.

        Raises:
            requests.RequestException: If request fails after retries.
            ValueError: If response is missing required fields.
        """
        if not messages:
            raise ValueError("messages cannot be empty")

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }

        try:
            response = self.session.post(
                f"{self.config.base_url}/v1/chat/completions",
                json=payload,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
        except requests.Timeout:
            raise requests.RequestException(
                f"LLM request timed out after {self.config.timeout}s"
            )
        except requests.ConnectionError:
            raise requests.RequestException(
                f"Failed to connect to LLM at {self.config.base_url}. "
                "Is Ollama running?"
            )

        data = response.json()

        if "error" in data:
            raise ValueError(f"LLM error: {data['error']}")

        if "choices" not in data or not data["choices"]:
            raise ValueError(
                f"Invalid LLM response: missing or empty choices. "
                f"Got: {data}"
            )

        choice = data["choices"][0]
        if "message" not in choice or "content" not in choice["message"]:
            raise ValueError(
                f"Invalid LLM response: missing message.content. "
                f"Got: {choice}"
            )

        return data

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

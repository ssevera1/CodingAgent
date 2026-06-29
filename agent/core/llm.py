"""LLM client for communicating with Ollama."""

import os
import time
import json
import logging
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with Ollama LLM."""

    def __init__(self, config):
        self.config = config
        self.base_url = config.llm.base_url
        self.model = config.llm.model
        self.temperature = config.llm.temperature
        self.max_tokens = config.llm.max_tokens
        self.timeout = config.llm.timeout
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

    def chat(self, messages: list[dict]) -> str:
        """Send messages to the LLM and get a response.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            The assistant's response text

        Raises:
            RuntimeError: If the LLM is unreachable or returns an error
        """
        if not messages:
            raise ValueError("messages cannot be empty")

        # Ensure system message exists
        if not messages or messages[0].get("role") != "system":
            raise ValueError("First message must be a system message")

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }

        try:
            logger.debug(f"Sending request to {url} with model {self.model}")
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to LLM at {self.base_url}: {e}")
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Is it running? Try: ollama serve"
            ) from e
        except requests.exceptions.Timeout as e:
            logger.error(f"LLM request timed out after {self.timeout}s")
            raise RuntimeError(
                f"LLM request timed out after {self.timeout}s"
            ) from e
        except requests.exceptions.HTTPError as e:
            logger.error(f"LLM returned HTTP {response.status_code}: {response.text}")
            if response.status_code == 404:
                raise RuntimeError(
                    f"Model '{self.model}' not found. Pull it first: "
                    f"ollama pull {self.model}"
                ) from e
            raise RuntimeError(
                f"LLM error (HTTP {response.status_code}): {response.text[:200]}"
            ) from e

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {response.text[:500]}")
            raise RuntimeError(
                f"Invalid response from LLM: {response.text[:100]}"
            ) from e

        message = data.get("message")
        if not message:
            logger.error(f"No message in LLM response: {data}")
            raise RuntimeError("LLM returned empty message")

        content = message.get("content")
        if not content:
            logger.error(f"Empty content in LLM response: {message}")
            raise RuntimeError("LLM returned empty content")

        logger.debug(f"Received response ({len(content)} chars)")
        return content

    def close(self):
        """Close the session."""
        self.session.close()

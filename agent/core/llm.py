"""LLM client for communicating with Ollama."""

import os
import time
import logging
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with local Ollama LLM."""

    def __init__(self, config):
        self.config = config
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy for network resilience."""
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

    def generate(self, messages: list[dict], temperature: Optional[float] = None) -> Optional[str]:
        """
        Generate a response from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Optional override for model temperature

        Returns:
            Generated text or None if request fails
        """
        if not messages:
            logger.error("generate() called with empty messages list")
            return None

        temp = temperature if temperature is not None else self.config.llm.temperature
        payload = {
            "model": self.config.llm.model,
            "messages": messages,
            "stream": False,
            "temperature": temp,
        }

        url = f"{self.config.llm.base_url}/api/chat"
        logger.debug(f"Sending request to {url} with model {self.config.llm.model}")

        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.config.llm.timeout,
            )
            response.raise_for_status()
        except requests.ConnectionError as e:
            logger.error(f"Connection error: {e}. Is Ollama running at {self.config.llm.base_url}?")
            return None
        except requests.Timeout:
            logger.error(f"Request timeout after {self.config.llm.timeout}s")
            return None
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

        try:
            data = response.json()
        except ValueError as e:
            logger.error(f"Invalid JSON in response: {e}")
            return None

        if "message" not in data or "content" not in data["message"]:
            logger.error(f"Unexpected response structure: {data}")
            return None

        text = data["message"]["content"]
        if not text:
            logger.warning("LLM returned empty response")
            return None

        logger.debug(f"Received {len(text)} chars from LLM")
        return text

    def is_available(self) -> bool:
        """Check if the LLM service is available."""
        try:
            response = self.session.get(
                f"{self.config.llm.base_url}/api/tags",
                timeout=5,
            )
            return response.status_code == 200
        except (requests.RequestException, Exception):
            return False

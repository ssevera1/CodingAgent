"""LLM client for communicating with Ollama."""

import os
import json
import time
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from agent.core.config import LLMConfig


class LLMClient:
    """Client for communicating with Ollama or other OpenAI-compatible LLM providers."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.timeout = config.timeout

        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        api_key = os.environ.get("OLLAMA_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def chat(self, messages: list[dict], temperature: Optional[float] = None) -> str:
        """
        Send a chat message and get a response.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            temperature: Optional override for model temperature.

        Returns:
            The assistant's response text.

        Raises:
            ConnectionError: If the LLM provider is unreachable.
            TimeoutError: If the request times out.
            ValueError: If the response format is invalid.
        """
        if not messages:
            raise ValueError("messages cannot be empty")

        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout as e:
            raise TimeoutError(
                f"LLM request timed out after {self.timeout}s at {url}"
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Could not connect to LLM at {url}. "
                f"Is Ollama running? (Configure with OLLAMA_API_KEY or base_url)"
            ) from e
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"LLM request failed: {e}") from e

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON from LLM: {response.text[:200]}"
            ) from e

        if "error" in data:
            raise ValueError(f"LLM error: {data['error']}")

        if "choices" not in data or not data["choices"]:
            raise ValueError(f"No choices in LLM response: {data}")

        choice = data["choices"][0]
        if "message" not in choice:
            raise ValueError(f"No message in LLM choice: {choice}")

        content = choice["message"].get("content")
        if not content:
            raise ValueError(
                f"Empty content in LLM response. Full response: {data}"
            )

        return content

"""LLM client for communicating with Ollama or other providers."""

import time
import requests
from typing import Optional
from agent.core.config import LLMConfig


class LLMClient:
    """Client for interacting with LLM providers with retry logic."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.timeout = config.timeout
        self._session = None

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def close(self):
        if self._session:
            self._session.close()
            self._session = None

    def complete(
        self,
        messages: list[dict],
        max_retries: int = 2,
    ) -> Optional[str]:
        """Send messages to LLM and get completion with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_retries: Number of retry attempts for transient failures

        Returns:
            Completion text or None if all retries exhausted
        """
        if not messages:
            raise ValueError("messages cannot be empty")

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

        for attempt in range(max_retries + 1):
            try:
                response = self.session.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()

                if "message" not in data:
                    raise ValueError(
                        f"Unexpected response format: {data}"
                    )

                content = data["message"].get("content", "")
                if not content:
                    raise ValueError("Empty content in LLM response")

                return content

            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                raise ConnectionError(
                    f"LLM connection failed after {max_retries + 1} attempts: {e}"
                )
            except requests.HTTPError as e:
                status_code = e.response.status_code
                if status_code == 404:
                    raise ValueError(
                        f"Model '{self.model}' not found. "
                        f"Ensure Ollama is running and model is pulled."
                    )
                if status_code >= 500 and attempt < max_retries:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                raise
            except ValueError:
                raise
            except Exception as e:
                raise RuntimeError(f"Unexpected error communicating with LLM: {e}")

        raise ConnectionError(
            f"LLM request failed after {max_retries + 1} attempts"
        )

    def __del__(self):
        self.close()

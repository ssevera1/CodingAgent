"""LLM client for interacting with Ollama."""

import os
import time
import requests
from typing import Optional
from agent.core.config import LLMConfig


class LLMClient:
    """Client for communicating with Ollama LLM service."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.session = requests.Session()

    def generate(
        self,
        messages: list[dict],
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> str:
        """Generate a response from the LLM with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            max_retries: Number of times to retry on transient failures.
            retry_delay: Initial delay in seconds between retries (exponential backoff).

        Returns:
            The assistant's response text.

        Raises:
            ConnectionError: If unable to connect after retries.
            ValueError: If LLM response is invalid or empty.
        """
        if not messages:
            raise ValueError("messages list cannot be empty")

        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        url = f"{self.base_url}/api/chat"
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    url,
                    json=payload,
                    timeout=self.config.timeout,
                )
                response.raise_for_status()

                data = response.json()
                if not data or "message" not in data:
                    raise ValueError(
                        f"Invalid LLM response structure: {data}"
                    )

                content = data["message"].get("content", "").strip()
                if not content:
                    raise ValueError("LLM returned empty response")

                return content

            except (requests.ConnectionError, requests.Timeout) as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = retry_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                raise ConnectionError(
                    f"Failed to connect to LLM at {url} after {max_retries} "
                    f"attempts: {last_error}"
                ) from last_error

            except requests.HTTPError as e:
                last_error = e
                if response.status_code >= 500 and attempt < max_retries - 1:
                    delay = retry_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                raise ConnectionError(
                    f"LLM service returned {response.status_code}: "
                    f"{response.text[:200]}"
                ) from last_error

            except (ValueError, requests.RequestException) as e:
                raise ValueError(f"LLM request failed: {e}") from e

        raise ConnectionError(
            f"Unexpected error after {max_retries} retries: {last_error}"
        )

    def health_check(self) -> bool:
        """Check if LLM service is reachable and responsive.

        Returns:
            True if service is healthy, False otherwise.
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            return response.status_code == 200
        except Exception:
            return False

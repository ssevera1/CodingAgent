"""LLM client with connection pooling and retry logic."""

import time
import requests
from typing import Optional
from agent.core.config import LLMConfig


class LLMClient:
    """Client for communicating with LLM providers (Ollama, etc.)."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.session = requests.Session()
        self._health_check_passed = False

    def health_check(self) -> bool:
        """Verify LLM service is reachable and healthy."""
        if self._health_check_passed:
            return True

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.session.get(
                    f"{self.config.base_url}/api/tags",
                    timeout=self.config.timeout,
                )
                if resp.status_code == 200:
                    self._health_check_passed = True
                    return True
            except (requests.ConnectionError, requests.Timeout):
                if attempt < max_retries - 1:
                    time.sleep(1 + attempt)
                continue

        return False

    def complete(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Request a completion from the LLM with exponential backoff."""
        if not self.health_check():
            raise RuntimeError(
                f"LLM service unavailable at {self.config.base_url}. "
                "Ensure Ollama is running: ollama serve"
            )

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "num_predict": max_tokens if max_tokens is not None else self.config.max_tokens,
            "stream": False,
        }

        max_retries = 3
        base_wait = 1

        for attempt in range(max_retries):
            try:
                resp = self.session.post(
                    f"{self.config.base_url}/api/chat",
                    json=payload,
                    timeout=self.config.timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                if not content:
                    raise ValueError("Empty response from LLM")
                return content
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt < max_retries - 1:
                    wait_time = base_wait * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                raise RuntimeError(
                    f"LLM request failed after {max_retries} attempts: {e}"
                )
            except requests.HTTPError as e:
                if e.response.status_code == 404:
                    raise RuntimeError(
                        f"Model '{self.config.model}' not found. "
                        "Pull it with: ollama pull <model>"
                    )
                raise RuntimeError(f"LLM HTTP error: {e}")
            except ValueError as e:
                raise RuntimeError(f"LLM response error: {e}")

        raise RuntimeError("Unexpected completion failure")

    def close(self):
        """Clean up resources."""
        if self.session:
            self.session.close()

    def __del__(self):
        self.close()

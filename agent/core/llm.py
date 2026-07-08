"""LLM client for communicating with Ollama or other providers."""

import time
import requests
from typing import Optional
from agent.core.config import LLMConfig


class LLMClient:
    """Client for LLM API calls with retry logic and timeout handling."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.timeout = config.timeout
        self.max_retries = 3
        self.retry_delay = 1.0

    def complete(self, messages: list[dict], system_prompt: Optional[str] = None) -> str:
        """Request a completion from the LLM with retry logic.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system message to prepend
            
        Returns:
            The assistant's response text
            
        Raises:
            RuntimeError: If all retries fail or response is malformed
        """
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": False,
        }
        if self.max_tokens:
            payload["num_predict"] = self.max_tokens

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                
                if "message" not in data or "content" not in data["message"]:
                    raise ValueError(f"Unexpected response schema: {data}")
                
                return data["message"]["content"]
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(
                        f"LLM request timeout after {self.max_retries} retries "
                        f"(timeout={self.timeout}s, model={self.model})"
                    )
                time.sleep(self.retry_delay)
            except requests.exceptions.ConnectionError:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(
                        f"Failed to connect to LLM at {self.base_url} "
                        f"after {self.max_retries} retries. "
                        f"Ensure Ollama is running: ollama serve"
                    )
                time.sleep(self.retry_delay)
            except requests.exceptions.HTTPError as e:
                if response.status_code == 404:
                    raise RuntimeError(
                        f"Model not found: {self.model}. "
                        f"Pull it with: ollama pull {self.model}"
                    )
                if attempt == self.max_retries - 1:
                    raise RuntimeError(
                        f"LLM HTTP error {response.status_code}: {response.text}"
                    )
                time.sleep(self.retry_delay)
            except (ValueError, requests.exceptions.RequestException) as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"LLM request failed: {str(e)}")
                time.sleep(self.retry_delay)

        raise RuntimeError("LLM request failed: exhausted retries")

    def health_check(self) -> bool:
        """Check if LLM service is reachable and responsive.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

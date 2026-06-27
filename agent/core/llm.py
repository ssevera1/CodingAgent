"""LLM client for communicating with Ollama or other providers."""

import os
import time
import logging
from typing import Optional
import requests

from agent.core.config import LLMConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with LLM providers with retry logic."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.session = requests.Session()
        self._verify_connection()

    def _verify_connection(self) -> bool:
        """Verify that the LLM provider is reachable."""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    f"{self.config.base_url}/api/tags",
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                logger.info(
                    f"Connected to {self.config.provider} at {self.config.base_url}"
                )
                return True
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Connection attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                else:
                    logger.error(
                        f"Failed to connect to {self.config.provider} after "
                        f"{max_retries} attempts. Is Ollama running at "
                        f"{self.config.base_url}?"
                    )
                    raise RuntimeError(
                        f"Cannot connect to LLM provider at {self.config.base_url}"
                    ) from e
        return False

    def complete(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Request completion from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            temperature: Override config temperature.
            max_tokens: Override config max_tokens.

        Returns:
            The assistant's response text.

        Raises:
            RuntimeError: If the request fails or returns invalid data.
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")

        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temp,
            "num_predict": max_tok,
            "stream": False,
        }

        max_retries = 2
        retry_delay = 1
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    f"{self.config.base_url}/api/chat",
                    json=payload,
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                data = response.json()

                if "message" not in data or "content" not in data["message"]:
                    raise RuntimeError(
                        f"Invalid response format from {self.config.provider}: "
                        f"missing message.content"
                    )

                content = data["message"]["content"]
                if not isinstance(content, str):
                    raise RuntimeError(
                        f"Invalid response format: content is "
                        f"{type(content).__name__}, expected str"
                    )

                if not content.strip():
                    logger.warning("LLM returned empty content")

                return content

            except requests.exceptions.Timeout:
                last_error = f"Request timeout after {self.config.timeout}s"
                if attempt < max_retries - 1:
                    logger.warning(f"{last_error}. Retrying...")
                    time.sleep(retry_delay)
                else:
                    logger.error(last_error)
                    raise RuntimeError(last_error) from None

            except requests.exceptions.RequestException as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    logger.warning(f"Request failed: {e}. Retrying...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    raise RuntimeError(
                        f"LLM request failed: {last_error}"
                    ) from e

            except ValueError as e:
                logger.error(f"Failed to parse response JSON: {e}")
                raise RuntimeError(
                    f"Invalid JSON response from {self.config.provider}"
                ) from e

        raise RuntimeError(f"LLM request failed: {last_error}")

    def list_models(self) -> list[str]:
        """List available models."""
        try:
            response = self.session.get(
                f"{self.config.base_url}/api/tags",
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def __del__(self):
        """Clean up session on deletion."""
        try:
            self.session.close()
        except Exception:
            pass

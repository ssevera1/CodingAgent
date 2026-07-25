"""LLM client for interacting with local Ollama instance."""

import os
import json
import time
import logging
from typing import Optional
import requests

from agent.core.config import LLMConfig

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 1.0
CONNECTION_TIMEOUT = 5.0


class LLMClient:
    """Client for communicating with Ollama LLM."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.provider = config.provider
        self.model = config.model
        self.base_url = config.base_url.rstrip("/")
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.timeout = config.timeout
        self._verify_connection()

    def _verify_connection(self) -> None:
        """Verify that the LLM backend is reachable before proceeding."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=CONNECTION_TIMEOUT,
            )
            response.raise_for_status()
            logger.info(f"LLM backend {self.base_url} is reachable")
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Cannot connect to LLM backend at {self.base_url}: {e}. "
                f"Ensure Ollama is running: `ollama serve`"
            )
            raise

    def complete(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Get a completion from the LLM with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.

        Returns:
            The assistant's response text.

        Raises:
            RuntimeError: If the request fails after all retries.
        """
        if not messages:
            raise ValueError("messages cannot be empty")

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return self._request(messages, temperature, max_tokens)
            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_DELAY * (2 ** attempt)
                    logger.warning(
                        f"LLM request timeout (attempt {attempt + 1}/{MAX_RETRIES}), "
                        f"retrying in {wait}s: {e}"
                    )
                    time.sleep(wait)
                else:
                    logger.error(f"LLM request failed after {MAX_RETRIES} attempts")
            except requests.exceptions.ConnectionError as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_DELAY * (2 ** attempt)
                    logger.warning(
                        f"LLM connection failed (attempt {attempt + 1}/{MAX_RETRIES}), "
                        f"retrying in {wait}s: {e}"
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        f"Cannot connect to LLM backend after {MAX_RETRIES} attempts. "
                        f"Is Ollama running at {self.base_url}?"
                    )
            except ValueError as e:
                logger.error(f"Invalid LLM request: {e}")
                raise
            except requests.exceptions.RequestException as e:
                logger.error(f"Unexpected LLM error: {e}")
                raise

        raise RuntimeError(
            f"LLM request failed after {MAX_RETRIES} retries: {last_error}"
        )

    def _request(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Execute a single LLM request.

        Args:
            messages: List of message dicts.
            temperature: Override temperature.
            max_tokens: Override max tokens.

        Returns:
            The assistant's response text.

        Raises:
            ValueError: If the response is malformed.
            requests.exceptions.RequestException: On network/HTTP errors.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "num_predict": max_tokens if max_tokens is not None else self.max_tokens,
            "stream": False,
        }

        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

        if "message" not in data or "content" not in data["message"]:
            logger.error(f"Unexpected LLM response structure: {data}")
            raise ValueError("LLM response missing 'message.content'")

        content = data["message"]["content"]
        if not isinstance(content, str):
            logger.error(f"LLM response content is not a string: {type(content)}")
            raise ValueError(f"LLM response content must be string, got {type(content)}")

        if not content.strip():
            logger.warning("LLM returned empty response")

        return content

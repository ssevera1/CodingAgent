"""LLM client with retry and timeout handling."""

import time
import logging
from typing import Optional
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    stop_reason: str
    usage: dict


class LLMClient:
    """Client for interacting with LLMs via Ollama."""

    def __init__(self, config):
        self.config = config
        self.model = config.llm.model
        self.base_url = config.llm.base_url
        self.temperature = config.llm.temperature
        self.max_tokens = config.llm.max_tokens
        self.timeout = config.llm.timeout
        self._client = None

    def _get_client(self):
        """Lazy-load Ollama client."""
        if self._client is None:
            try:
                import ollama
                self._client = ollama.Client(host=self.base_url)
            except Exception as e:
                logger.error(f"Failed to initialize Ollama client: {e}")
                raise RuntimeError(
                    f"Cannot connect to Ollama at {self.base_url}. "
                    "Ensure Ollama is running."
                ) from e
        return self._client

    def generate(
        self,
        messages: list[dict],
        max_retries: int = 2,
    ) -> LLMResponse:
        """Generate response from LLM with retry logic."""
        if not messages:
            raise ValueError("Messages list cannot be empty")

        last_error = None
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"LLM request (attempt {attempt + 1}/{max_retries}): "
                    f"model={self.model}, tokens={self.max_tokens}"
                )

                client = self._get_client()
                response = client.chat(
                    model=self.model,
                    messages=messages,
                    stream=False,
                    options={
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                    },
                )

                if not response or "message" not in response:
                    raise ValueError(f"Invalid response structure: {response}")

                message = response["message"]
                if "content" not in message:
                    raise ValueError(f"No content in message: {message}")

                logger.debug(
                    f"LLM response: stop_reason={response.get('done_reason', 'unknown')}, "
                    f"tokens={response.get('eval_count', 0)}"
                )

                return LLMResponse(
                    content=message["content"],
                    stop_reason=response.get("done_reason", "stop"),
                    usage={
                        "prompt_tokens": response.get("prompt_eval_count", 0),
                        "completion_tokens": response.get("eval_count", 0),
                    },
                )

            except (TimeoutError, ConnectionError) as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed (timeout/connection): {e}"
                )
                if attempt < max_retries - 1:
                    wait_secs = 2 ** attempt
                    logger.debug(f"Retrying in {wait_secs}s...")
                    time.sleep(wait_secs)
                continue

            except ValueError as e:
                last_error = e
                logger.error(f"Invalid LLM response: {e}")
                raise

            except Exception as e:
                last_error = e
                logger.error(f"Unexpected LLM error: {e}", exc_info=True)
                raise

        raise RuntimeError(
            f"LLM request failed after {max_retries} attempts. "
            f"Last error: {last_error}"
        ) from last_error

    def is_available(self) -> bool:
        """Check if LLM is available and responsive."""
        try:
            client = self._get_client()
            response = client.list()
            return response is not None
        except Exception as e:
            logger.warning(f"LLM availability check failed: {e}")
            return False

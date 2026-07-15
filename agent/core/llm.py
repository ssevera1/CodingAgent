"""LLM client for communicating with Ollama or other providers."""

import os
import time
import logging
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for LLM API calls with retry logic and error handling."""

    def __init__(self, config):
        self.config = config
        self.base_url = config.llm.base_url.rstrip("/")
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
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def chat(
        self,
        messages: list[dict],
        max_retries: int = 3,
    ) -> Optional[str]:
        """Send a chat request to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            max_retries: Number of retries on transient failures.

        Returns:
            The assistant's response content, or None if all retries failed.
        """
        if not messages:
            logger.warning("chat() called with empty messages")
            return None

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

        last_error = None
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"LLM request (attempt {attempt + 1}/{max_retries}): "
                    f"model={self.model}, messages={len(messages)}"
                )
                response = self.session.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                data = response.json()
                if "message" not in data:
                    logger.error(
                        f"Unexpected LLM response structure: {list(data.keys())}"
                    )
                    return None

                content = data["message"].get("content", "")
                if not content:
                    logger.warning("LLM returned empty response content")
                    return None

                logger.debug(f"LLM response received: {len(content)} chars")
                return content

            except requests.exceptions.Timeout as e:
                last_error = e
                logger.warning(
                    f"LLM request timeout (attempt {attempt + 1}/{max_retries}): "
                    f"{self.timeout}s"
                )
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

            except requests.exceptions.ConnectionError as e:
                last_error = e
                logger.warning(
                    f"LLM connection failed (attempt {attempt + 1}/{max_retries}): "
                    f"{self.base_url}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response else None
                logger.error(
                    f"LLM HTTP error {status_code}: {e.response.text if e.response else str(e)}"
                )
                if status_code and status_code < 500:
                    return None
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

            except ValueError as e:
                logger.error(f"LLM response JSON decode error: {e}")
                return None

            except Exception as e:
                logger.error(
                    f"Unexpected LLM error on attempt {attempt + 1}/{max_retries}: {e}"
                )
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        logger.error(
            f"LLM request failed after {max_retries} attempts: {last_error}"
        )
        return None

    def health_check(self) -> bool:
        """Check if the LLM service is reachable.

        Returns:
            True if reachable, False otherwise.
        """
        try:
            url = f"{self.base_url}/api/tags"
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            logger.debug("LLM health check passed")
            return True
        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            return False

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

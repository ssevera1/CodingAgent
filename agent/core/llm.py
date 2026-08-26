"""LLM interface for Ollama-based models."""

import json
import socket
import time
import urllib.request
import urllib.error
from typing import Generator, Literal, Optional, Union, overload

from agent.core.config import LLMConfig


class OllamaError(Exception):
    """Raised when Ollama API returns an error."""
    pass


class LLMClient:
    """Client for interacting with Ollama LLM API."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")

    def _validate_response(self, response: dict, required_fields: list[str]) -> None:
        """Validate that response contains expected fields.
        
        Args:
            response: The response dict to validate.
            required_fields: List of field names that must be present.
            
        Raises:
            OllamaError: If any required field is missing.
        """
        missing = [field for field in required_fields if field not in response]
        if missing:
            raise OllamaError(
                f"Malformed API response: missing required fields {missing}. "
                f"Got: {response}"
            )

    def _request(
        self,
        endpoint: str,
        data: dict,
        stream: bool = False,
        timeout: Optional[float] = None,
    ) -> dict:
        url = f"{self.base_url}{endpoint}"
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        effective_timeout = timeout if timeout is not None else self.config.timeout
        try:
            resp = urllib.request.urlopen(req, timeout=effective_timeout)
            if stream:
                return resp  # Return response object for streaming
            return json.loads(resp.read().decode("utf-8"))
        except socket.timeout:
            raise OllamaError(
                f"Timeout connecting to Ollama at {self.base_url} "
                f"(waited {self.config.timeout}s). Make sure Ollama is running."
            )
        except urllib.error.URLError as e:
            if isinstance(e.reason, (socket.timeout, socket.error, ConnectionRefusedError, OSError)):
                raise OllamaError(
                    f"Cannot connect to Ollama at {self.base_url}. "
                    f"Make sure Ollama is running: {e}"
                )
            raise OllamaError(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running: {e}"
            )
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise OllamaError(f"Ollama API error ({e.code}): {body}")

    def check_health(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode("utf-8"))
            models = [m["name"] for m in data.get("models", [])]
            # Check if our model (or a prefix of it) is available
            model_base = self.config.model.split(":")[0]
            return any(model_base in m for m in models)
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """List available models in Ollama."""
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    # A streaming call returns a generator, not the response dict. Overloads let
    # callers keep the precise type instead of narrowing the union by hand.
    @overload
    def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = ...,
        stream: Literal[False] = ...,
        timeout: Optional[float] = ...,
    ) -> dict: ...

    @overload
    def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = ...,
        *,
        stream: Literal[True],
        timeout: Optional[float] = ...,
    ) -> Generator[str, None, dict]: ...

    def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        stream: bool = False,
        timeout: Optional[float] = None,
    ) -> Union[dict, Generator[str, None, dict]]:
        """Send a chat completion request to Ollama.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool definitions for function calling.
            stream: Whether to stream the response.
            timeout: Optional per-request timeout override in seconds.

        Returns:
            Response dict with 'message' containing 'role', 'content',
            and optionally 'tool_calls'.
        """
        data = {
            "model": self.config.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                "num_ctx": self.config.context_window,
            },
        }
        if tools:
            data["tools"] = tools

        if stream:
            return self._stream_chat(data, timeout=timeout)

        result = self._request("/api/chat", data, timeout=timeout)
        self._validate_response(result, ["message"])
        return result

    def _stream_chat(
        self,
        data: dict,
        timeout: Optional[float] = None,
    ) -> Generator[str, None, dict]:
        """Stream chat response, yielding content chunks."""
        resp = self._request("/api/chat", data, stream=True, timeout=timeout)
        full_response = {"message": {"role": "assistant", "content": ""}}

        try:
            for line in resp:
                line = line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    if "message" in chunk:
                        content = chunk["message"].get("content", "")
                        full_response["message"]["content"] += content
                        yield content
                        # Check for tool calls
                        if "tool_calls" in chunk["message"]:
                            full_response["message"]["tool_calls"] = chunk["message"]["tool_calls"]
                    if chunk.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
        except socket.timeout:
            raise OllamaError(
                f"Timeout streaming from Ollama at {self.base_url} "
                f"(waited {self.config.timeout}s)."
            )

        return full_response

    def generate(self, prompt: str, timeout: Optional[float] = None) -> str:
        """Simple text generation without chat format.

        Args:
            prompt: The prompt to generate from.
            timeout: Optional per-request timeout override in seconds.

        Returns:
            Generated text response.
        """
        data = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }
        result = self._request("/api/generate", data, timeout=timeout)
        self._validate_response(result, ["response"])
        return result.get("response", "")

    def pull_model(
        self,
        model_name: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> bool:
        """Pull/download a model from Ollama registry.

        Args:
            model_name: Model name to pull. Uses config model if not specified.
            timeout: Optional per-request timeout override in seconds.

        Returns:
            True if pull succeeded, False otherwise.
        """
        model = model_name or self.config.model
        print(f"Pulling model '{model}'... This may take a while.")
        try:
            data = {"name": model, "stream": False}
            self._request("/api/pull", data, timeout=timeout)
            print(f"Model '{model}' pulled successfully.")
            return True
        except OllamaError as e:
            print(f"Failed to pull model: {e}")
            return False

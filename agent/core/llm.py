"""LLM interface for Ollama-based models."""

import json
import time
import urllib.request
import urllib.error
from typing import Generator, Optional

from agent.core.config import LLMConfig


class OllamaError(Exception):
    """Raised when Ollama API returns an error."""
    pass


class LLMClient:
    """Client for interacting with Ollama LLM API."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")

    def _request(self, endpoint: str, data: dict, stream: bool = False) -> dict:
        url = f"{self.base_url}{endpoint}"
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=self.config.timeout)
            if stream:
                return resp  # Return response object for streaming
            return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
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

    def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        stream: bool = False,
    ) -> dict:
        """Send a chat completion request to Ollama.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool definitions for function calling.
            stream: Whether to stream the response.

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
            return self._stream_chat(data)

        result = self._request("/api/chat", data)
        return result

    def _stream_chat(self, data: dict) -> Generator[str, None, dict]:
        """Stream chat response, yielding content chunks."""
        resp = self._request("/api/chat", data, stream=True)
        full_response = {"message": {"role": "assistant", "content": ""}}

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

        return full_response

    def generate(self, prompt: str) -> str:
        """Simple text generation without chat format."""
        data = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }
        result = self._request("/api/generate", data)
        return result.get("response", "")

    def pull_model(self, model_name: Optional[str] = None) -> bool:
        """Pull/download a model from Ollama registry."""
        model = model_name or self.config.model
        print(f"Pulling model '{model}'... This may take a while.")
        try:
            data = {"name": model, "stream": False}
            self._request("/api/pull", data)
            print(f"Model '{model}' pulled successfully.")
            return True
        except OllamaError as e:
            print(f"Failed to pull model: {e}")
            return False

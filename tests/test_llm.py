"""Tests for the Ollama LLM client response validation."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.core.config import LLMConfig
from agent.core.llm import LLMClient, OllamaError


def make_client() -> LLMClient:
    return LLMClient(LLMConfig())


def stream_lines(chunks) -> list[bytes]:
    return [json.dumps(chunk).encode("utf-8") for chunk in chunks]


def drain(generator):
    """Run a generator to completion, returning (yielded, return_value)."""
    yielded = []
    while True:
        try:
            yielded.append(next(generator))
        except StopIteration as stop:
            return yielded, stop.value


class TestValidateMessageStructure(unittest.TestCase):
    """Test _validate_message_structure."""

    def test_missing_message_raises(self):
        with self.assertRaises(OllamaError):
            make_client()._validate_message_structure({"done": True})

    def test_non_dict_message_raises(self):
        with self.assertRaises(OllamaError):
            make_client()._validate_message_structure({"message": "hello"})

    def test_non_string_content_raises(self):
        with self.assertRaises(OllamaError):
            make_client()._validate_message_structure(
                {"message": {"role": "assistant", "content": ["a", "b"]}}
            )

    def test_missing_content_without_tool_calls_raises(self):
        with self.assertRaises(OllamaError):
            make_client()._validate_message_structure(
                {"message": {"role": "assistant"}}
            )

    def test_missing_content_with_tool_calls_is_allowed(self):
        make_client()._validate_message_structure(
            {
                "message": {
                    "role": "assistant",
                    "tool_calls": [{"function": {"name": "read_file"}}],
                }
            }
        )

    def test_null_content_with_tool_calls_is_allowed(self):
        make_client()._validate_message_structure(
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{"function": {"name": "read_file"}}],
                }
            }
        )

    def test_valid_message_passes(self):
        make_client()._validate_message_structure(
            {"message": {"role": "assistant", "content": "hi"}}
        )

    def test_chat_accepts_tool_call_only_response(self):
        client = make_client()
        response = {
            "message": {
                "role": "assistant",
                "tool_calls": [{"function": {"name": "read_file", "arguments": {}}}],
            }
        }
        with patch.object(client, "_request", return_value=response):
            self.assertEqual(client.chat([{"role": "user", "content": "hi"}]), response)

    def test_chat_rejects_non_dict_message(self):
        client = make_client()
        with patch.object(client, "_request", return_value={"message": None}):
            with self.assertRaises(OllamaError):
                client.chat([{"role": "user", "content": "hi"}])


class TestStreamChat(unittest.TestCase):
    """Test _stream_chat chunk handling."""

    def test_tool_calls_without_content_are_kept(self):
        client = make_client()
        tool_calls = [{"function": {"name": "read_file", "arguments": {}}}]
        lines = stream_lines(
            [
                {"message": {"role": "assistant", "tool_calls": tool_calls}},
                {"message": {"role": "assistant", "content": ""}, "done": True},
            ]
        )
        with patch.object(client, "_request", return_value=lines):
            yielded, result = drain(client._stream_chat({}))

        self.assertEqual(result["message"].get("tool_calls"), tool_calls)
        self.assertEqual(yielded, [])

    def test_content_chunks_are_accumulated_and_yielded(self):
        client = make_client()
        lines = stream_lines(
            [
                {"message": {"role": "assistant", "content": "he"}},
                {"message": {"role": "assistant", "content": "llo"}},
                {"message": {"role": "assistant", "content": ""}, "done": True},
            ]
        )
        with patch.object(client, "_request", return_value=lines):
            yielded, result = drain(client._stream_chat({}))

        self.assertEqual(yielded, ["he", "llo"])
        self.assertEqual(result["message"]["content"], "hello")

    def test_null_content_does_not_crash(self):
        client = make_client()
        lines = stream_lines(
            [
                {"message": {"role": "assistant", "content": None}},
                {"message": {"role": "assistant", "content": "ok"}, "done": True},
            ]
        )
        with patch.object(client, "_request", return_value=lines):
            yielded, result = drain(client._stream_chat({}))

        self.assertEqual(yielded, ["ok"])
        self.assertEqual(result["message"]["content"], "ok")

    def test_non_string_content_raises(self):
        client = make_client()
        lines = stream_lines([{"message": {"role": "assistant", "content": [1, 2]}}])
        with patch.object(client, "_request", return_value=lines):
            with self.assertRaises(OllamaError):
                drain(client._stream_chat({}))

    def test_non_dict_message_is_skipped(self):
        client = make_client()
        lines = stream_lines(
            [
                {"message": "not a dict"},
                {"message": {"role": "assistant", "content": "ok"}, "done": True},
            ]
        )
        with patch.object(client, "_request", return_value=lines):
            yielded, result = drain(client._stream_chat({}))

        self.assertEqual(yielded, ["ok"])
        self.assertEqual(result["message"]["content"], "ok")


if __name__ == "__main__":
    unittest.main()

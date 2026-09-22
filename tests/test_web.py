"""Tests for the web search/fetch tools."""

import io
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.tools.web import WebFetchTool, WebSearchTool, _fetch_with_retry


def _fake_response(body: bytes, content_type: str = "text/html"):
    resp = io.BytesIO(body)
    resp.headers = type("Headers", (), {"get": lambda self, k, d=None: content_type})()
    return resp


class TestHtmlToText(unittest.TestCase):
    def setUp(self):
        self.tool = WebFetchTool()

    def test_br_tag_becomes_newline(self):
        self.assertEqual(self.tool._html_to_text("a<br>b"), "a\nb")

    def test_self_closing_br_tag_becomes_newline(self):
        self.assertEqual(self.tool._html_to_text("a<br/>b"), "a\nb")

    def test_br_with_space_becomes_newline(self):
        self.assertEqual(self.tool._html_to_text("a<br />b"), "a\nb")


class TestFetchWithRetry(unittest.TestCase):
    def test_returns_body_and_content_type_on_success(self):
        with patch("urllib.request.urlopen", return_value=_fake_response(b"hello", "text/plain")):
            body, content_type = _fetch_with_retry(req=None, timeout=1, max_retries=2)
        self.assertEqual(body, "hello")
        self.assertEqual(content_type, "text/plain")

    def test_retries_on_transient_url_error_then_succeeds(self):
        calls = {"n": 0}

        def fake_urlopen(req, timeout=None):
            calls["n"] += 1
            if calls["n"] < 2:
                raise urllib.error.URLError("connection refused")
            return _fake_response(b"ok")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("time.sleep"):
            body, _ = _fetch_with_retry(req=None, timeout=1, max_retries=2)

        self.assertEqual(body, "ok")
        self.assertEqual(calls["n"], 2)

    def test_gives_up_after_max_retries(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")), \
             patch("time.sleep"):
            with self.assertRaises(urllib.error.URLError):
                _fetch_with_retry(req=None, timeout=1, max_retries=2)

    def test_http_error_is_not_retried(self):
        calls = {"n": 0}

        def fake_urlopen(req, timeout=None):
            calls["n"] += 1
            raise urllib.error.HTTPError("http://x", 404, "Not Found", {}, None)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("time.sleep") as mock_sleep:
            with self.assertRaises(urllib.error.HTTPError):
                _fetch_with_retry(req=None, timeout=1, max_retries=2)

        self.assertEqual(calls["n"], 1)
        mock_sleep.assert_not_called()


class TestWebFetchTool(unittest.TestCase):
    def test_execute_issues_a_single_request(self):
        tool = WebFetchTool()
        with patch(
            "urllib.request.urlopen",
            return_value=_fake_response(b"<p>hi<br>there</p>", "text/html"),
        ) as mock_urlopen:
            result = tool.execute(url="https://example.com")

        self.assertEqual(mock_urlopen.call_count, 1)
        self.assertTrue(result.success)
        self.assertIn("hi\nthere", result.output)


class TestWebSearchTool(unittest.TestCase):
    def test_execute_returns_search_failed_on_persistent_error(self):
        tool = WebSearchTool()
        with patch(
            "urllib.request.urlopen", side_effect=urllib.error.URLError("down")
        ), patch("time.sleep"):
            result = tool.execute(query="test")

        self.assertFalse(result.success)
        self.assertIn("Search failed", result.error)


if __name__ == "__main__":
    unittest.main()

"""Web tools: search and fetch for online operations."""

import json
import urllib.request
import urllib.parse
import urllib.error
import re
import html
from typing import Optional

from agent.tools.base import BaseTool, ToolResult


class WebSearchTool(BaseTool):
    """Search the web using DuckDuckGo."""

    name = "web_search"
    description = (
        "Search the web for information. Returns search results with titles, "
        "URLs, and snippets. Useful for finding documentation, solutions, "
        "and up-to-date information."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default: 5)",
            },
        },
        "required": ["query"],
    }

    def __init__(self, config=None):
        self.timeout = config.request_timeout if config else 15
        self.user_agent = config.user_agent if config else "CodeAgent/1.0"

    def execute(self, query: str, max_results: int = 5, **kw) -> ToolResult:
        try:
            # Use DuckDuckGo HTML search (no API key needed)
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html",
                },
            )

            resp = urllib.request.urlopen(req, timeout=self.timeout)
            body = resp.read().decode("utf-8", errors="replace")

            # Parse results from HTML
            results = self._parse_ddg_html(body, max_results)

            if not results:
                return ToolResult(True, f"No results found for: {query}")

            lines = [f"Search results for: {query}\n"]
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. {r['title']}")
                lines.append(f"   URL: {r['url']}")
                lines.append(f"   {r['snippet']}")
                lines.append("")

            return ToolResult(True, "\n".join(lines))
        except urllib.error.URLError as e:
            return ToolResult(False, "", f"Search failed (network error): {e}")
        except Exception as e:
            return ToolResult(False, "", f"Search failed: {e}")

    def _parse_ddg_html(self, body: str, max_results: int) -> list[dict]:
        """Parse DuckDuckGo HTML results."""
        results = []

        # Find result blocks
        result_pattern = re.compile(
            r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
            r'class="result__snippet"[^>]*>(.*?)</(?:a|span|div)',
            re.DOTALL,
        )

        for match in result_pattern.finditer(body):
            if len(results) >= max_results:
                break

            raw_url = match.group(1)
            title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            snippet = re.sub(r"<[^>]+>", "", match.group(3)).strip()

            # DuckDuckGo redirects - extract actual URL
            if "uddg=" in raw_url:
                url_match = re.search(r"uddg=([^&]+)", raw_url)
                if url_match:
                    raw_url = urllib.parse.unquote(url_match.group(1))

            title = html.unescape(title)
            snippet = html.unescape(snippet)

            if title and raw_url:
                results.append({
                    "title": title,
                    "url": raw_url,
                    "snippet": snippet or "(no snippet)",
                })

        return results


class WebFetchTool(BaseTool):
    """Fetch and extract content from a URL."""

    name = "web_fetch"
    description = (
        "Fetch content from a URL and extract readable text. Useful for "
        "reading documentation, blog posts, and other web content."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch",
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum content length in characters (default: 10000)",
            },
        },
        "required": ["url"],
    }

    def __init__(self, config=None):
        self.timeout = config.request_timeout if config else 15
        self.user_agent = config.user_agent if config else "CodeAgent/1.0"

    def execute(self, url: str, max_length: int = 10000, **kw) -> ToolResult:
        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,text/plain",
                },
            )

            resp = urllib.request.urlopen(req, timeout=self.timeout)
            content_type = resp.headers.get("Content-Type", "")

            body = resp.read().decode("utf-8", errors="replace")

            if "text/html" in content_type:
                text = self._html_to_text(body)
            else:
                text = body

            if len(text) > max_length:
                text = text[:max_length] + "\n\n... [content truncated]"

            return ToolResult(True, f"Content from {url}:\n\n{text}")
        except urllib.error.HTTPError as e:
            return ToolResult(False, "", f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            return ToolResult(False, "", f"Failed to fetch {url}: {e}")
        except Exception as e:
            return ToolResult(False, "", f"Failed to fetch: {e}")

    def _html_to_text(self, html_content: str) -> str:
        """Basic HTML to text conversion."""
        # Remove script and style elements
        text = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        # Convert common tags
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"</(p|div|h[1-6]|li|tr)>", "\n", text)
        text = re.sub(r"<h([1-6])[^>]*>", lambda m: "\n" + "#" * int(m.group(1)) + " ", text)
        text = re.sub(r"<li[^>]*>", "  - ", text)
        # Remove remaining tags
        text = re.sub(r"<[^>]+>", "", text)
        # Decode entities
        text = html.unescape(text)
        # Clean up whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

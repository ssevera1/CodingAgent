"""Agent Scanner - Scan the internet for the most up-to-date coding agents."""

import json
import re
import urllib.request
import urllib.parse
import urllib.error
from dataclasses import dataclass
from typing import Optional

from agent.tools.base import BaseTool, ToolResult


@dataclass
class AgentInfo:
    """Information about a discovered coding agent."""
    name: str
    url: str
    description: str
    stars: str
    language: str
    last_updated: str
    category: str  # "cli", "ide", "web", "framework"
    license: str
    source: str  # Where this info came from

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "stars": self.stars,
            "language": self.language,
            "last_updated": self.last_updated,
            "category": self.category,
            "license": self.license,
            "source": self.source,
        }


# Well-known coding agents to always check
KNOWN_AGENTS = [
    {
        "name": "Aider",
        "repo": "paul-gauthier/aider",
        "category": "cli",
        "description": "AI pair programming in your terminal",
    },
    {
        "name": "OpenHands (OpenDevin)",
        "repo": "All-Hands-AI/OpenHands",
        "category": "web",
        "description": "Platform for software development agents",
    },
    {
        "name": "Cline",
        "repo": "cline/cline",
        "category": "ide",
        "description": "Autonomous coding agent for VS Code",
    },
    {
        "name": "Continue",
        "repo": "continuedev/continue",
        "category": "ide",
        "description": "Open-source AI code assistant for IDEs",
    },
    {
        "name": "SWE-agent",
        "repo": "SWE-agent/SWE-agent",
        "category": "cli",
        "description": "Agent for solving GitHub issues autonomously",
    },
    {
        "name": "Devon",
        "repo": "entropy-research/Devon",
        "category": "cli",
        "description": "Open-source AI software engineer",
    },
    {
        "name": "GPT-Engineer",
        "repo": "gpt-engineer-org/gpt-engineer",
        "category": "cli",
        "description": "AI that generates entire codebases from prompts",
    },
    {
        "name": "Sweep",
        "repo": "sweepai/sweep",
        "category": "web",
        "description": "AI junior developer that turns issues into PRs",
    },
    {
        "name": "Tabby",
        "repo": "TabbyML/tabby",
        "category": "ide",
        "description": "Self-hosted AI coding assistant",
    },
    {
        "name": "Mentat",
        "repo": "AbanteAI/mentat",
        "category": "cli",
        "description": "AI coding assistant in your terminal",
    },
    {
        "name": "Roo Code",
        "repo": "RooVetGit/Roo-Code",
        "category": "ide",
        "description": "AI-powered coding assistant for VS Code",
    },
    {
        "name": "Cursor",
        "repo": "getcursor/cursor",
        "category": "ide",
        "description": "AI-powered code editor",
    },
    {
        "name": "Bolt",
        "repo": "stackblitz/bolt.new",
        "category": "web",
        "description": "AI-powered full-stack web development agent",
    },
]


class AgentScannerTool(BaseTool):
    """Scan the internet for the latest coding agents."""

    name = "scan_agents"
    description = (
        "Scan the internet to find the most up-to-date coding agents. "
        "Queries GitHub API and web sources to discover and compare "
        "open-source coding agents, their features, and popularity."
    )
    parameters = {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": (
                    "Filter by category: 'cli' (terminal-based), 'ide' (editor plugins), "
                    "'web' (browser-based), 'framework' (agent frameworks), or 'all'"
                ),
            },
            "query": {
                "type": "string",
                "description": "Additional search query to find specific agents",
            },
            "sort_by": {
                "type": "string",
                "description": "Sort results by: 'stars', 'updated', 'name' (default: 'stars')",
            },
            "discover_new": {
                "type": "boolean",
                "description": "Also search for new/unknown agents beyond the known list",
            },
        },
        "required": [],
    }

    def __init__(self, config=None):
        self.timeout = config.request_timeout if config else 15
        self.user_agent = config.user_agent if config else "CodeAgent/1.0"

    def execute(
        self, category: str = "all", query: str = "",
        sort_by: str = "stars", discover_new: bool = True, **kw
    ) -> ToolResult:
        agents = []
        errors = []

        # 1. Check known agents via GitHub API
        for known in KNOWN_AGENTS:
            if category != "all" and known["category"] != category:
                continue
            info = self._fetch_github_repo(known["repo"])
            if info:
                info.category = known["category"]
                info.name = known["name"]
                agents.append(info)
            else:
                errors.append(f"Could not fetch {known['repo']}")

        # 2. Discover new agents from GitHub search
        if discover_new:
            discovered = self._search_github_agents(query or "coding agent AI", category)
            # Merge with known, avoiding duplicates
            known_urls = {a.url.lower() for a in agents}
            for d in discovered:
                if d.url.lower() not in known_urls:
                    agents.append(d)

        # 3. Sort results
        if sort_by == "stars":
            agents.sort(key=lambda a: self._parse_stars(a.stars), reverse=True)
        elif sort_by == "updated":
            agents.sort(key=lambda a: a.last_updated, reverse=True)
        elif sort_by == "name":
            agents.sort(key=lambda a: a.name.lower())

        # 4. Format output
        if not agents:
            return ToolResult(
                True,
                "No coding agents found. Check your internet connection and try again."
            )

        lines = [
            "=== Coding Agent Scanner Results ===",
            f"Found {len(agents)} coding agents",
            f"Category: {category} | Sorted by: {sort_by}",
            "=" * 50,
            "",
        ]

        for i, agent in enumerate(agents, 1):
            lines.append(f"  {i}. {agent.name}")
            lines.append(f"     URL:         {agent.url}")
            lines.append(f"     Stars:       {agent.stars}")
            lines.append(f"     Language:    {agent.language}")
            lines.append(f"     Category:    {agent.category}")
            lines.append(f"     Updated:     {agent.last_updated}")
            lines.append(f"     License:     {agent.license}")
            lines.append(f"     Description: {agent.description}")
            lines.append("")

        if errors:
            lines.append(f"\nWarnings: {len(errors)} repos could not be fetched")

        return ToolResult(True, "\n".join(lines))

    def _fetch_github_repo(self, repo: str) -> Optional[AgentInfo]:
        """Fetch repo info from GitHub API."""
        try:
            url = f"https://api.github.com/repos/{repo}"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            resp = urllib.request.urlopen(req, timeout=self.timeout)
            data = json.loads(resp.read().decode("utf-8"))

            return AgentInfo(
                name=data.get("name", repo.split("/")[-1]),
                url=data.get("html_url", f"https://github.com/{repo}"),
                description=data.get("description", "(no description)") or "(no description)",
                stars=str(data.get("stargazers_count", 0)),
                language=data.get("language", "Unknown") or "Unknown",
                last_updated=data.get("updated_at", "Unknown")[:10],
                category="unknown",
                license=(data.get("license") or {}).get("spdx_id", "Unknown"),
                source="github_api",
            )
        except Exception:
            return None

    def _search_github_agents(self, query: str, category: str) -> list[AgentInfo]:
        """Search GitHub for coding agents."""
        agents = []
        try:
            search_q = urllib.parse.quote(f"{query} coding agent language:python language:typescript")
            url = (
                f"https://api.github.com/search/repositories"
                f"?q={search_q}&sort=stars&order=desc&per_page=15"
            )
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            resp = urllib.request.urlopen(req, timeout=self.timeout)
            data = json.loads(resp.read().decode("utf-8"))

            for item in data.get("items", []):
                desc = item.get("description", "") or ""
                # Filter to likely coding agents
                keywords = ["agent", "coding", "code", "developer", "programming", "copilot", "assistant"]
                if not any(k in desc.lower() or k in item.get("name", "").lower() for k in keywords):
                    continue

                cat = category if category != "all" else self._guess_category(desc, item.get("topics", []))

                agents.append(AgentInfo(
                    name=item.get("name", "Unknown"),
                    url=item.get("html_url", ""),
                    description=desc[:200] if desc else "(no description)",
                    stars=str(item.get("stargazers_count", 0)),
                    language=item.get("language", "Unknown") or "Unknown",
                    last_updated=item.get("updated_at", "Unknown")[:10],
                    category=cat,
                    license=(item.get("license") or {}).get("spdx_id", "Unknown"),
                    source="github_search",
                ))
        except Exception:
            pass

        return agents

    def _guess_category(self, description: str, topics: list) -> str:
        """Guess the category of an agent based on its description."""
        text = (description + " " + " ".join(topics)).lower()
        if any(k in text for k in ["cli", "terminal", "command line"]):
            return "cli"
        if any(k in text for k in ["vscode", "ide", "editor", "extension", "plugin"]):
            return "ide"
        if any(k in text for k in ["web", "browser", "cloud"]):
            return "web"
        if any(k in text for k in ["framework", "sdk", "library"]):
            return "framework"
        return "unknown"

    def _parse_stars(self, stars_str: str) -> int:
        """Parse star count string to int."""
        try:
            return int(stars_str.replace(",", ""))
        except (ValueError, AttributeError):
            return 0

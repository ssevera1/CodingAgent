"""Search tools: Grep and Glob for code search."""

import os
import re
import fnmatch
from pathlib import Path
from typing import Optional

from agent.tools.base import BaseTool, ToolResult


# Directories and patterns to always skip
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".env",
    ".idea", ".vscode", "dist", "build", ".tox", ".mypy_cache",
    ".pytest_cache", "egg-info", ".eggs",
}

BINARY_EXTENSIONS = {
    ".pyc", ".pyo", ".exe", ".dll", ".so", ".dylib", ".bin",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico", ".svg",
    ".mp3", ".mp4", ".avi", ".mov", ".zip", ".tar", ".gz",
    ".rar", ".7z", ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".woff", ".woff2", ".ttf", ".eot", ".class", ".jar",
}


def _should_skip(path: Path) -> bool:
    """Check if a path should be skipped during search."""
    parts = path.parts
    return any(part in SKIP_DIRS for part in parts)


def _is_binary(path: Path) -> bool:
    """Check if a file is likely binary."""
    return path.suffix.lower() in BINARY_EXTENSIONS


class GrepTool(BaseTool):
    """Search file contents using regex patterns."""

    name = "grep"
    description = (
        "Search for a regex pattern in file contents. Returns matching lines "
        "with file paths and line numbers. Supports filtering by file glob pattern."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regex pattern to search for",
            },
            "path": {
                "type": "string",
                "description": "Directory or file to search in (default: working dir)",
            },
            "glob_filter": {
                "type": "string",
                "description": "Glob pattern to filter files (e.g., '*.py', '*.js')",
            },
            "case_insensitive": {
                "type": "boolean",
                "description": "Case insensitive search (default: false)",
            },
            "context_lines": {
                "type": "integer",
                "description": "Number of context lines before and after match",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 50)",
            },
        },
        "required": ["pattern"],
    }

    def __init__(self, working_dir: str):
        self.working_dir = working_dir

    def execute(
        self, pattern: str, path: str = "", glob_filter: str = "",
        case_insensitive: bool = False, context_lines: int = 0,
        max_results: int = 50, **kw
    ) -> ToolResult:
        try:
            flags = re.IGNORECASE if case_insensitive else 0
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return ToolResult(False, "", f"Invalid regex: {e}")

            search_path = Path(path) if path else Path(self.working_dir)
            if not search_path.is_absolute():
                search_path = Path(self.working_dir) / search_path
            search_path = search_path.resolve()

            if not search_path.exists():
                return ToolResult(False, "", f"Path not found: {search_path}")

            results = []
            files_searched = 0

            if search_path.is_file():
                files_to_search = [search_path]
            else:
                files_to_search = sorted(search_path.rglob("*"))

            for fpath in files_to_search:
                if not fpath.is_file():
                    continue
                if _should_skip(fpath.relative_to(search_path) if search_path.is_dir() else fpath):
                    continue
                if _is_binary(fpath):
                    continue
                if glob_filter and not fnmatch.fnmatch(fpath.name, glob_filter):
                    continue

                files_searched += 1
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                except (PermissionError, OSError):
                    continue

                for i, line in enumerate(lines):
                    if regex.search(line):
                        rel = fpath.relative_to(search_path) if search_path.is_dir() else fpath.name
                        # Add context lines
                        if context_lines > 0:
                            start = max(0, i - context_lines)
                            end = min(len(lines), i + context_lines + 1)
                            ctx = []
                            for j in range(start, end):
                                marker = ">" if j == i else " "
                                ctx.append(f"  {marker} {j+1:>5}: {lines[j].rstrip()}")
                            results.append(f"{rel}:{i+1}:\n" + "\n".join(ctx))
                        else:
                            results.append(f"{rel}:{i+1}: {line.rstrip()}")

                        if len(results) >= max_results:
                            break
                if len(results) >= max_results:
                    break

            if not results:
                return ToolResult(True, f"No matches found ({files_searched} files searched)")

            header = f"Found {len(results)} matches in {files_searched} files"
            if len(results) >= max_results:
                header += f" (limited to {max_results})"
            return ToolResult(True, header + "\n\n" + "\n".join(results))
        except Exception as e:
            return ToolResult(False, "", str(e))


class GlobTool(BaseTool):
    """Find files matching glob patterns."""

    name = "glob"
    description = (
        "Find files matching a glob pattern. Returns matching file paths "
        "sorted by modification time. Examples: '**/*.py', 'src/**/*.ts'"
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern to match files (e.g., '**/*.py')",
            },
            "path": {
                "type": "string",
                "description": "Base directory to search from (default: working dir)",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default: 100)",
            },
        },
        "required": ["pattern"],
    }

    def __init__(self, working_dir: str):
        self.working_dir = working_dir

    def execute(self, pattern: str, path: str = "", max_results: int = 100, **kw) -> ToolResult:
        try:
            search_path = Path(path) if path else Path(self.working_dir)
            if not search_path.is_absolute():
                search_path = Path(self.working_dir) / search_path
            search_path = search_path.resolve()

            if not search_path.exists():
                return ToolResult(False, "", f"Path not found: {search_path}")

            matches = []
            for fpath in search_path.glob(pattern):
                if _should_skip(fpath.relative_to(search_path)):
                    continue
                if fpath.is_file():
                    try:
                        mtime = fpath.stat().st_mtime
                        rel = fpath.relative_to(search_path)
                        matches.append((mtime, str(rel)))
                    except OSError:
                        continue

            # Sort by modification time (newest first)
            matches.sort(key=lambda x: x[0], reverse=True)
            matches = matches[:max_results]

            if not matches:
                return ToolResult(True, f"No files matching '{pattern}' in {search_path}")

            lines = [f"Found {len(matches)} files matching '{pattern}':\n"]
            for _, rel_path in matches:
                lines.append(f"  {rel_path}")

            return ToolResult(True, "\n".join(lines))
        except Exception as e:
            return ToolResult(False, "", str(e))

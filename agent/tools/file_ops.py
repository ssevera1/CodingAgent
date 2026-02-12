"""File operation tools: Read, Write, Edit."""

import os
import difflib
from pathlib import Path
from typing import Optional

from agent.tools.base import BaseTool, ToolResult


class ReadFileTool(BaseTool):
    """Read file contents with optional line range."""

    name = "read_file"
    description = (
        "Read the contents of a file. Returns the file content with line numbers. "
        "Use offset and limit for large files."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute or relative path to the file to read",
            },
            "offset": {
                "type": "integer",
                "description": "Line number to start reading from (1-based). Optional.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read. Optional.",
            },
        },
        "required": ["file_path"],
    }

    def __init__(self, working_dir: str):
        self.working_dir = working_dir

    def _resolve_path(self, file_path: str) -> Path:
        p = Path(file_path)
        if not p.is_absolute():
            p = Path(self.working_dir) / p
        return p.resolve()

    def execute(self, file_path: str, offset: int = 1, limit: int = 2000, **kw) -> ToolResult:
        try:
            path = self._resolve_path(file_path)
            if not path.exists():
                return ToolResult(False, "", f"File not found: {path}")
            if not path.is_file():
                return ToolResult(False, "", f"Not a file: {path}")

            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total = len(lines)
            start = max(0, offset - 1)
            end = min(total, start + limit)
            selected = lines[start:end]

            numbered = []
            for i, line in enumerate(selected, start=start + 1):
                # Truncate very long lines
                if len(line) > 2000:
                    line = line[:2000] + "... [truncated]\n"
                numbered.append(f"{i:>6}\t{line.rstrip()}")

            header = f"File: {path} ({total} lines total)"
            if start > 0 or end < total:
                header += f" [showing lines {start+1}-{end}]"

            return ToolResult(True, header + "\n" + "\n".join(numbered))
        except Exception as e:
            return ToolResult(False, "", str(e))


class WriteFileTool(BaseTool):
    """Write content to a file, creating it if necessary."""

    name = "write_file"
    description = (
        "Write content to a file. Creates the file and parent directories if they "
        "don't exist. Overwrites existing content."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to write",
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file",
            },
        },
        "required": ["file_path", "content"],
    }

    def __init__(self, working_dir: str):
        self.working_dir = working_dir

    def _resolve_path(self, file_path: str) -> Path:
        p = Path(file_path)
        if not p.is_absolute():
            p = Path(self.working_dir) / p
        return p.resolve()

    def execute(self, file_path: str, content: str, **kw) -> ToolResult:
        try:
            path = self._resolve_path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
            return ToolResult(True, f"Successfully wrote {lines} lines to {path}")
        except Exception as e:
            return ToolResult(False, "", str(e))


class EditFileTool(BaseTool):
    """Edit a file by replacing a specific string."""

    name = "edit_file"
    description = (
        "Edit a file by replacing an exact string match with new content. "
        "The old_string must be unique in the file. Use replace_all=true "
        "to replace all occurrences."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit",
            },
            "old_string": {
                "type": "string",
                "description": "The exact string to find and replace",
            },
            "new_string": {
                "type": "string",
                "description": "The replacement string",
            },
            "replace_all": {
                "type": "boolean",
                "description": "Replace all occurrences (default: false)",
            },
        },
        "required": ["file_path", "old_string", "new_string"],
    }

    def __init__(self, working_dir: str):
        self.working_dir = working_dir

    def _resolve_path(self, file_path: str) -> Path:
        p = Path(file_path)
        if not p.is_absolute():
            p = Path(self.working_dir) / p
        return p.resolve()

    def execute(
        self, file_path: str, old_string: str, new_string: str,
        replace_all: bool = False, **kw
    ) -> ToolResult:
        try:
            path = self._resolve_path(file_path)
            if not path.exists():
                return ToolResult(False, "", f"File not found: {path}")

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            count = content.count(old_string)
            if count == 0:
                return ToolResult(False, "", "old_string not found in file")
            if count > 1 and not replace_all:
                return ToolResult(
                    False, "",
                    f"old_string found {count} times. Use replace_all=true or "
                    "provide more context to make it unique."
                )

            if replace_all:
                new_content = content.replace(old_string, new_string)
            else:
                new_content = content.replace(old_string, new_string, 1)

            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(new_content)

            replacements = count if replace_all else 1
            return ToolResult(
                True,
                f"Replaced {replacements} occurrence(s) in {path}"
            )
        except Exception as e:
            return ToolResult(False, "", str(e))


class ListDirectoryTool(BaseTool):
    """List contents of a directory."""

    name = "list_directory"
    description = "List files and directories in the specified path."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to list (default: working directory)",
            },
            "recursive": {
                "type": "boolean",
                "description": "List recursively (default: false)",
            },
        },
        "required": [],
    }

    def __init__(self, working_dir: str):
        self.working_dir = working_dir

    def execute(self, path: str = "", recursive: bool = False, **kw) -> ToolResult:
        try:
            target = Path(path) if path else Path(self.working_dir)
            if not target.is_absolute():
                target = Path(self.working_dir) / target
            target = target.resolve()

            if not target.exists():
                return ToolResult(False, "", f"Path not found: {target}")
            if not target.is_dir():
                return ToolResult(False, "", f"Not a directory: {target}")

            entries = []
            if recursive:
                for item in sorted(target.rglob("*")):
                    rel = item.relative_to(target)
                    prefix = "d " if item.is_dir() else "f "
                    entries.append(f"  {prefix}{rel}")
            else:
                for item in sorted(target.iterdir()):
                    prefix = "d " if item.is_dir() else "f "
                    size = ""
                    if item.is_file():
                        s = item.stat().st_size
                        if s < 1024:
                            size = f" ({s}B)"
                        elif s < 1024 * 1024:
                            size = f" ({s/1024:.1f}KB)"
                        else:
                            size = f" ({s/1024/1024:.1f}MB)"
                    entries.append(f"  {prefix}{item.name}{size}")

            header = f"Directory: {target} ({len(entries)} entries)"
            return ToolResult(True, header + "\n" + "\n".join(entries))
        except Exception as e:
            return ToolResult(False, "", str(e))

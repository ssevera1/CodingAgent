"""Bash/shell command execution tool."""

import os
import subprocess
import shlex
import platform
from pathlib import Path
from typing import Optional

from agent.tools.base import BaseTool, ToolResult


# Commands that are always blocked for safety
BLOCKED_COMMANDS = {
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){:|:&};:",
    "chmod -R 777 /", "shutdown", "reboot", "halt", "poweroff",
}

# Commands that require confirmation
DANGEROUS_PATTERNS = [
    "rm -rf", "rm -r", "rmdir", "del /s", "format",
    "drop database", "drop table", "truncate",
    "git push --force", "git reset --hard",
    "git clean -f", "git checkout .",
]


class BashTool(BaseTool):
    """Execute shell commands."""

    name = "bash"
    description = (
        "Execute a shell command and return its output. Use for git operations, "
        "running tests, installing packages, building projects, and other "
        "terminal operations. Commands run in the working directory."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 120, max: 600)",
            },
        },
        "required": ["command"],
    }

    def __init__(self, working_dir: str, auto_approve: bool = False):
        self.working_dir = working_dir
        self.auto_approve = auto_approve

    def _is_blocked(self, command: str) -> Optional[str]:
        """Check if command is blocked."""
        cmd_lower = command.lower().strip()
        for blocked in BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                return f"Blocked dangerous command: {blocked}"
        return None

    def _is_dangerous(self, command: str) -> bool:
        """Check if command requires confirmation."""
        cmd_lower = command.lower()
        return any(p in cmd_lower for p in DANGEROUS_PATTERNS)

    def execute(self, command: str, timeout: int = 120, **kw) -> ToolResult:
        # Safety checks
        blocked = self._is_blocked(command)
        if blocked:
            return ToolResult(False, "", blocked)

        if self._is_dangerous(command) and not self.auto_approve:
            return ToolResult(
                False, "",
                f"Dangerous command requires confirmation: {command}\n"
                "Set auto_approve_bash=true in config or confirm interactively."
            )

        timeout = min(timeout, 600)

        try:
            is_windows = platform.system() == "Windows"
            if is_windows:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=self.working_dir,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                )
            else:
                result = subprocess.run(
                    ["/bin/bash", "-c", command],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=self.working_dir,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                )

            output = result.stdout
            if result.stderr:
                output += ("\n--- stderr ---\n" + result.stderr) if output else result.stderr

            # Truncate very large outputs
            if len(output) > 30000:
                output = output[:15000] + "\n\n... [output truncated] ...\n\n" + output[-15000:]

            if result.returncode != 0:
                return ToolResult(
                    False,
                    output or f"Command exited with code {result.returncode}",
                    f"Exit code: {result.returncode}",
                )

            return ToolResult(True, output or "(no output)")
        except subprocess.TimeoutExpired:
            return ToolResult(False, "", f"Command timed out after {timeout}s: {command}")
        except FileNotFoundError:
            return ToolResult(False, "", f"Command not found: {command.split()[0]}")
        except Exception as e:
            return ToolResult(False, "", str(e))

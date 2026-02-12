"""Git operation tools."""

import subprocess
import os
from pathlib import Path
from typing import Optional

from agent.tools.base import BaseTool, ToolResult


class GitTool(BaseTool):
    """Git operations: status, diff, log, add, commit, branch management."""

    name = "git"
    description = (
        "Execute git operations. Supports: status, diff, log, add, commit, "
        "branch, checkout, merge, stash, remote, pull, push, and more. "
        "Provides safety checks for destructive operations."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": (
                    "Git subcommand and arguments (e.g., 'status', 'diff --staged', "
                    "'log --oneline -10', 'add file.py', 'commit -m \"message\"')"
                ),
            },
        },
        "required": ["command"],
    }

    # Operations that are always blocked
    BLOCKED_OPS = {"push --force main", "push --force master", "push -f main", "push -f master"}

    # Operations that require extra care
    DANGEROUS_OPS = {
        "push --force", "push -f", "reset --hard", "clean -f",
        "checkout .", "restore .", "branch -D",
    }

    def __init__(self, working_dir: str):
        self.working_dir = working_dir

    def _find_git_root(self) -> Optional[str]:
        """Find the git repository root."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, cwd=self.working_dir,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except FileNotFoundError:
            pass
        return None

    def execute(self, command: str, **kw) -> ToolResult:
        # Safety checks
        cmd_lower = command.lower().strip()
        for blocked in self.BLOCKED_OPS:
            if blocked in cmd_lower:
                return ToolResult(False, "", f"Blocked: 'git {blocked}' is not allowed")

        for dangerous in self.DANGEROUS_OPS:
            if dangerous in cmd_lower:
                return ToolResult(
                    False, "",
                    f"Warning: 'git {dangerous}' is destructive. "
                    "Please confirm this is intentional."
                )

        # Block interactive commands
        if any(flag in command for flag in [" -i ", " --interactive"]):
            return ToolResult(False, "", "Interactive git commands are not supported")

        git_root = self._find_git_root()
        if not git_root and not cmd_lower.startswith("init") and not cmd_lower.startswith("clone"):
            return ToolResult(False, "", "Not inside a git repository")

        try:
            result = subprocess.run(
                f"git {command}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.working_dir,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            )

            output = result.stdout
            if result.stderr:
                # Git often writes to stderr for informational messages
                output += ("\n" + result.stderr) if output else result.stderr

            if result.returncode != 0:
                return ToolResult(False, output, f"git {command} failed (exit {result.returncode})")

            return ToolResult(True, output or "(no output)")
        except subprocess.TimeoutExpired:
            return ToolResult(False, "", f"git {command} timed out")
        except FileNotFoundError:
            return ToolResult(False, "", "git is not installed or not in PATH")
        except Exception as e:
            return ToolResult(False, "", str(e))

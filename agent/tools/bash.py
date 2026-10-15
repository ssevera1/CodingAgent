"""Bash/shell command execution tool."""

import os
import re
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

# Commands whose argv[0] reads file contents (checked against SENSITIVE_FILE_PATTERNS)
FILE_READ_COMMANDS = {
    "cat", "less", "more", "head", "tail", "vim", "vi", "nano", "strings",
    "grep", "sort", "od", "xxd", "base64",
}

# Path fragments that identify secret-bearing files, matched against the
# normalized/expanded path argument rather than the raw command text
SENSITIVE_FILE_PATTERNS = [
    re.compile(r"/etc/passwd$"),
    re.compile(r"/etc/shadow$"),
    re.compile(r"\.ssh(/|$)"),
    re.compile(r"\.aws(/|$)"),
    re.compile(r"\.netrc$"),
    re.compile(r"id_rsa$"),
    re.compile(r"id_ed25519$"),
    re.compile(r"/proc/(?:self|\d+)/environ$"),
]

# Commands that print environment variables; sensitive only when dumping
# everything (no specific name given) or when the requested name looks secret
ENV_DUMP_COMMANDS = {"env", "printenv", "set", "declare", "export"}

# argv[0] for commands that can print a variable's value directly
ENV_PRINT_COMMANDS = {"echo", "printf"}

SECRET_NAME_RE = re.compile(r"(API[_-]?KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)", re.IGNORECASE)
VAR_REF_RE = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")

# Shells whose -x flag traces commands with variables already expanded
TRACING_SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}


def _enables_xtrace(argv0: str, args: list) -> bool:
    """True if this command turns on xtrace (`set -x`, `set -o xtrace`,
    `bash -x ...`), which prints every later command with its variables
    expanded, so a secret referenced anywhere in the line reaches the
    output."""
    if argv0 != "set" and argv0 not in TRACING_SHELLS:
        return False
    for i, arg in enumerate(args):
        if arg.startswith("-") and not arg.startswith("--") and "x" in arg[1:]:
            return True
        if arg == "-o" and i + 1 < len(args) and args[i + 1] == "xtrace":
            return True
    return False


# env options that take a separate argument (`env -u NAME`, `env -C DIR`)
ENV_OPTS_WITH_ARG = {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"}


def _unwrap_env(tokens: list) -> Optional[list]:
    """Strip `env`'s own options and NAME=value assignments.

    Returns the wrapped command's tokens, or None when nothing is left,
    in which case `env` prints the whole environment.
    """
    i = 1
    while i < len(tokens):
        tok = tokens[i]
        if tok in ENV_OPTS_WITH_ARG:
            i += 2
        elif tok.startswith("-") or "=" in tok:
            i += 1
        else:
            return tokens[i:]
    return None


# Minimum timeout to prevent accidental no-timeout execution
MIN_TIMEOUT = 1
DEFAULT_TIMEOUT = 120
MAX_TIMEOUT = 600


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

    def _is_sensitive(self, command: str) -> Optional[str]:
        """Check if command reads a sensitive file or prints a secret-looking
        environment variable. Operates on parsed argv per shell segment so
        that commands merely mentioning a secret's name (e.g. grepping for
        it in source) are not flagged, only commands structured to read or
        print one.

        This is a best-effort guard against accidental or injected leakage,
        not a sandbox: only top-level segments are inspected, so command
        substitution, backticks, and interpreter wrappers such as
        ``bash -c`` or ``python -c`` are not examined.
        """
        secret_refs = [
            name for name in VAR_REF_RE.findall(command) if SECRET_NAME_RE.search(name)
        ]
        for segment in re.split(r"\|\||&&|[;|\n]", command):
            segment = segment.strip()
            if not segment:
                continue
            try:
                tokens = shlex.split(segment)
            except ValueError:
                # Unbalanced quotes (often from the split above cutting
                # inside a quoted "|"). Fall back to whitespace tokens so
                # the segment is still checked rather than skipped.
                tokens = segment.split()
            if not tokens:
                continue

            # `env [opts] [NAME=value ...] cmd` runs cmd, so check cmd
            # itself; with no cmd it prints every variable.
            while os.path.basename(tokens[0]) == "env":
                wrapped = _unwrap_env(tokens)
                if wrapped is None:
                    return f"Blocked: '{segment}' dumps environment variables"
                tokens = wrapped

            argv0 = os.path.basename(tokens[0])
            args = tokens[1:]

            if secret_refs and _enables_xtrace(argv0, args):
                return (
                    f"Blocked: '{segment}' turns on command tracing, which "
                    f"would print the value of '{secret_refs[0]}'"
                )

            if argv0 in FILE_READ_COMMANDS:
                for arg in args:
                    if arg.startswith("-"):
                        continue
                    expanded = os.path.normpath(
                        os.path.expanduser(os.path.expandvars(arg))
                    )
                    for pat in SENSITIVE_FILE_PATTERNS:
                        if pat.search(expanded):
                            return f"Blocked: '{segment}' reads sensitive file '{arg}'"

            if argv0 in ENV_DUMP_COMMANDS:
                named = [a for a in args if not a.startswith("-")]
                # NAME=value sets a variable (`export TOKEN=...`,
                # `env TOKEN=x ./run.sh`); only bare names read one.
                reads = [a for a in named if "=" not in a]
                # Only bare `set` prints variables; `set -e`, `set -x` and
                # `set -o ...` toggle shell options and print nothing.
                if argv0 == "set":
                    dumps = not args
                else:
                    dumps = not named
                if dumps or any(SECRET_NAME_RE.search(a) for a in reads):
                    return f"Blocked: '{segment}' dumps environment variables"

            if argv0 in ENV_PRINT_COMMANDS:
                for arg in args:
                    for var_name in VAR_REF_RE.findall(arg):
                        if SECRET_NAME_RE.search(var_name):
                            return (
                                f"Blocked: '{segment}' prints the value of "
                                f"'{var_name}'"
                            )
        return None

    def _sanitize_timeout(self, timeout: Optional[int]) -> int:
        """Validate and enforce timeout bounds."""
        if timeout is None:
            return DEFAULT_TIMEOUT
        if not isinstance(timeout, int):
            return DEFAULT_TIMEOUT
        return max(MIN_TIMEOUT, min(timeout, MAX_TIMEOUT))

    def execute(self, command: str, timeout: Optional[int] = None, **kw) -> ToolResult:
        # Safety checks
        blocked = self._is_blocked(command)
        if blocked:
            return ToolResult(False, "", blocked)

        sensitive = self._is_sensitive(command)
        if sensitive and not self.auto_approve:
            return ToolResult(
                False, "",
                f"{sensitive}\n"
                "Interactive confirmation does not lift this check; only "
                "auto_approve_bash=true in config skips it, and that disables "
                "confirmation for every bash command."
            )

        if self._is_dangerous(command) and not self.auto_approve:
            return ToolResult(
                False, "",
                f"Dangerous command requires confirmation: {command}\n"
                "Set auto_approve_bash=true in config or confirm interactively."
            )

        # Validate and enforce timeout
        timeout = self._sanitize_timeout(timeout)

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

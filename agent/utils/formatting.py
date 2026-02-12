"""Output formatting utilities for terminal display."""

import os
import sys
import platform


# ANSI color codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright foreground
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


def supports_color() -> bool:
    """Check if the terminal supports color output."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if platform.system() == "Windows":
        # Windows 10+ supports ANSI codes
        os.system("")  # Enable ANSI on Windows
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


_COLOR_ENABLED = supports_color()


def color(text: str, *codes: str) -> str:
    """Apply color codes to text."""
    if not _COLOR_ENABLED:
        return text
    prefix = "".join(codes)
    return f"{prefix}{text}{Colors.RESET}"


def bold(text: str) -> str:
    return color(text, Colors.BOLD)


def dim(text: str) -> str:
    return color(text, Colors.DIM)


def success(text: str) -> str:
    return color(text, Colors.BRIGHT_GREEN)


def error(text: str) -> str:
    return color(text, Colors.BRIGHT_RED)


def warning(text: str) -> str:
    return color(text, Colors.BRIGHT_YELLOW)


def info(text: str) -> str:
    return color(text, Colors.BRIGHT_CYAN)


def tool_name(text: str) -> str:
    return color(text, Colors.BRIGHT_MAGENTA, Colors.BOLD)


def header(text: str) -> str:
    return color(text, Colors.BRIGHT_BLUE, Colors.BOLD)


def code_block(text: str) -> str:
    return color(text, Colors.DIM)


def separator(char: str = "-", width: int = 60) -> str:
    return dim(char * width)


def banner() -> str:
    """Display the CodeAgent banner."""
    lines = [
        r"",
        r"   ____          _         _                    _   ",
        r"  / ___|___   __| | ___   / \   __ _  ___ _ __ | |_ ",
        r" | |   / _ \ / _` |/ _ \ / _ \ / _` |/ _ \ '_ \| __|",
        r" | |__| (_) | (_| |  __// ___ \ (_| |  __/ | | | |_ ",
        r"  \____\___/ \__,_|\___/_/   \_\__, |\___|_| |_|\__|",
        r"                               |___/                 ",
        r"",
    ]
    colored = [color(line, Colors.BRIGHT_CYAN) for line in lines]
    colored.append(
        dim("  Offline Coding Agent | Powered by Local LLMs via Ollama")
    )
    colored.append(dim(f"  v1.0.0 | Type /help for commands"))
    colored.append("")
    return "\n".join(colored)


def format_tool_call(name: str, args: dict) -> str:
    """Format a tool call for display."""
    args_str = ", ".join(f"{k}={repr(v)[:50]}" for k, v in args.items())
    return f"{tool_name(name)}({args_str})"


def format_tool_result(name: str, result) -> str:
    """Format a tool result for display."""
    if result.success:
        status = success("[OK]")
    else:
        status = error("[ERR]")
    output = result.output[:500] if len(result.output) > 500 else result.output
    return f"{status} {tool_name(name)}: {output}"


def spinner_frames() -> list[str]:
    """Get spinner animation frames (ASCII-safe for Windows compatibility)."""
    return ["|", "/", "-", "\\"]

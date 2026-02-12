"""CodeAgent - Main entry point and CLI interface."""

import os
import sys
import argparse
import time
import re
from pathlib import Path

from agent import __version__
from agent.core.config import Config, DEFAULT_CONFIG_FILE
from agent.core.engine import AgentEngine
from agent.core.llm import LLMClient, OllamaError
from agent.utils.formatting import (
    banner, bold, dim, error, success, warning, info,
    header, separator, Colors, color,
)


HELP_TEXT = """
Available commands:
  /help              Show this help message
  /quit, /exit       Exit CodeAgent
  /clear             Clear conversation history
  /status            Show agent status
  /model [name]      Show or change the active model
  /models            List available Ollama models
  /scan              Scan for the latest coding agents on the internet
  /config            Show current configuration
  /cd <path>         Change working directory
  /verbose           Toggle verbose mode
  /save [file]       Save conversation to file
  /load [file]       Load conversation from file
  /version           Show version information

Tips:
  - Ask me to read, write, or edit files
  - Ask me to search your codebase
  - Ask me to run commands or manage git
  - Ask me to explain or refactor code
  - Use /scan to discover the latest coding agents
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CodeAgent - Offline Coding Agent powered by local LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model", "-m",
        help="Ollama model to use (default: qwen2.5-coder:7b-instruct-q4_K_M)",
    )
    parser.add_argument(
        "--dir", "-d",
        help="Working directory (default: current directory)",
        default=os.getcwd(),
    )
    parser.add_argument(
        "--config", "-c",
        help="Path to config file",
        default=str(DEFAULT_CONFIG_FILE),
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="Disable web features (fully offline mode)",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve all tool executions (use with caution)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"CodeAgent v{__version__}",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Optional initial prompt (non-interactive mode)",
    )
    return parser.parse_args()


def check_ollama(config: Config) -> bool:
    """Check if Ollama is running and the model is available."""
    client = LLMClient(config.llm)

    print(dim("  Checking Ollama connection..."), end="", flush=True)
    if not client.check_health():
        print(error(" FAILED"))
        print(error("\n  Ollama is not running or the model is not available."))
        print(info("  Start Ollama with: ollama serve"))
        print(info(f"  Pull the model with: ollama pull {config.llm.model}"))
        return False

    print(success(" OK"))
    return True


def safe_print(text: str):
    """Print text safely, replacing characters the console can't encode."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Strip characters that can't be encoded (e.g. emoji on Windows cp1252)
        cleaned = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
            sys.stdout.encoding or "utf-8", errors="replace"
        )
        print(cleaned)


def handle_command(command: str, engine: AgentEngine, config: Config) -> bool:
    """Handle slash commands. Returns True if the REPL should continue."""
    parts = command.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd in ("/quit", "/exit", "/q"):
        print(dim("\n  Goodbye!\n"))
        return False

    elif cmd == "/help":
        print(HELP_TEXT)

    elif cmd == "/clear":
        engine.reset()
        print(success("  Conversation cleared."))

    elif cmd == "/status":
        models = engine.llm.list_models()
        print(header("  Agent Status"))
        print(f"  Model:      {config.llm.model}")
        print(f"  Provider:   {config.llm.provider} ({config.llm.base_url})")
        print(f"  Work Dir:   {config.agent.working_directory}")
        print(f"  Web:        {'Enabled' if config.web.enabled else 'Disabled'}")
        print(f"  Turns:      {engine._turn_count}")
        print(f"  Messages:   {len(engine.conversation.messages)}")
        print(f"  Models:     {', '.join(models) if models else 'Cannot list'}")

    elif cmd == "/model":
        if arg:
            config.llm.model = arg
            engine.llm = LLMClient(config.llm)
            print(success(f"  Model changed to: {arg}"))
        else:
            print(f"  Current model: {config.llm.model}")
            print(dim("  Usage: /model <model_name>"))

    elif cmd == "/models":
        models = engine.llm.list_models()
        if models:
            print(header("  Available Models:"))
            for m in models:
                marker = " *" if m == config.llm.model else ""
                print(f"    {m}{success(marker)}")
        else:
            print(warning("  Cannot list models. Is Ollama running?"))

    elif cmd == "/scan":
        print(info("  Scanning for coding agents..."))
        scanner_tool = engine.tools.get("scan_agents")
        if scanner_tool:
            category = arg if arg else "all"
            result = scanner_tool.execute(category=category, discover_new=True)
            safe_print(result.output)
        else:
            print(error("  Web features are disabled. Run without --no-web"))

    elif cmd == "/config":
        print(header("  Configuration"))
        print(f"  Config file: {DEFAULT_CONFIG_FILE}")
        print(f"  LLM:")
        print(f"    Model:       {config.llm.model}")
        print(f"    Base URL:    {config.llm.base_url}")
        print(f"    Temperature: {config.llm.temperature}")
        print(f"    Max Tokens:  {config.llm.max_tokens}")
        print(f"  Agent:")
        print(f"    Max Turns:   {config.agent.max_turns}")
        print(f"    Auto Reads:  {config.agent.auto_approve_reads}")
        print(f"    Auto Bash:   {config.agent.auto_approve_bash}")
        print(f"  Web:")
        print(f"    Enabled:     {config.web.enabled}")
        print(f"    Engine:      {config.web.search_engine}")

    elif cmd == "/cd":
        if not arg:
            print(f"  Current directory: {config.agent.working_directory}")
            print(dim("  Usage: /cd <path>"))
        else:
            new_dir = os.path.abspath(os.path.expanduser(arg))
            if os.path.isdir(new_dir):
                engine.update_working_directory(new_dir)
                print(success(f"  Changed to: {new_dir}"))
            else:
                print(error(f"  Not a directory: {new_dir}"))

    elif cmd == "/verbose":
        config.agent.verbose = not config.agent.verbose
        state = "ON" if config.agent.verbose else "OFF"
        print(f"  Verbose mode: {success(state) if config.agent.verbose else dim(state)}")

    elif cmd == "/save":
        path = Path(arg) if arg else Path("conversation.json")
        engine.conversation.save(path)
        print(success(f"  Saved conversation to {path}"))

    elif cmd == "/load":
        path = Path(arg) if arg else Path("conversation.json")
        if path.exists():
            engine.conversation.load(path)
            print(success(f"  Loaded conversation from {path}"))
        else:
            print(error(f"  File not found: {path}"))

    elif cmd == "/version":
        print(f"  CodeAgent v{__version__}")

    else:
        print(warning(f"  Unknown command: {cmd}"))
        print(dim("  Type /help for available commands"))

    return True


def run_interactive(engine: AgentEngine, config: Config):
    """Run the interactive REPL."""
    print(banner())
    print(f"  {dim('Model:')} {info(config.llm.model)}")
    print(f"  {dim('Dir:')}   {info(config.agent.working_directory)}")
    print(f"  {dim('Web:')}   {info('Enabled' if config.web.enabled else 'Disabled (offline)')}")
    print()

    while True:
        try:
            # Prompt
            cwd_short = os.path.basename(config.agent.working_directory) or "/"
            prompt = f"{color(cwd_short, Colors.BRIGHT_BLUE)} {color('>', Colors.BRIGHT_GREEN)} "
            user_input = input(prompt).strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                if not handle_command(user_input, engine, config):
                    break
                continue

            # Process with agent
            print()
            response = engine.process_message(user_input)
            safe_print(f"\n{response}\n")

        except KeyboardInterrupt:
            print(dim("\n  (Ctrl+C pressed. Type /quit to exit)"))
            continue
        except EOFError:
            print(dim("\n  Goodbye!\n"))
            break


def run_single(engine: AgentEngine, prompt: str):
    """Run a single prompt and exit."""
    response = engine.process_message(prompt)
    safe_print(response)


def main():
    """Main entry point."""
    args = parse_args()

    # Load or create config
    config_path = Path(args.config)
    config = Config.load(config_path)
    Config.ensure_dirs()

    # Apply CLI overrides
    if args.model:
        config.llm.model = args.model
    if args.dir:
        config.agent.working_directory = os.path.abspath(args.dir)
    if args.verbose:
        config.agent.verbose = True
    if args.no_web:
        config.web.enabled = False
    if args.auto_approve:
        config.agent.auto_approve_reads = True
        config.agent.auto_approve_searches = True
        config.agent.auto_approve_writes = True
        config.agent.auto_approve_bash = True

    # Save config for future sessions
    config.save(config_path)

    # Check Ollama connectivity
    if not check_ollama(config):
        sys.exit(1)

    # Create the engine
    engine = AgentEngine(config)

    # Run in single or interactive mode
    if args.prompt:
        run_single(engine, " ".join(args.prompt))
    else:
        run_interactive(engine, config)


if __name__ == "__main__":
    main()

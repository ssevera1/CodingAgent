"""Core agent engine - the main loop that processes user requests."""

import json
import re
import time
import sys
import threading
from typing import Optional

from agent.core.config import Config
from agent.core.llm import LLMClient, OllamaError
from agent.core.conversation import Conversation
from agent.tools.base import ToolRegistry, ToolResult
from agent.tools.file_ops import ReadFileTool, WriteFileTool, EditFileTool, ListDirectoryTool
from agent.tools.search import GrepTool, GlobTool
from agent.tools.bash import BashTool
from agent.tools.git import GitTool
from agent.tools.web import WebSearchTool, WebFetchTool
from agent.tools.agent_scanner import AgentScannerTool
from agent.prompts.system import get_system_prompt
from agent.utils.formatting import (
    format_tool_call, format_tool_result, tool_name, dim, error, success,
    warning, info, spinner_frames,
)


class AgentEngine:
    """Core agent engine that orchestrates LLM and tools."""

    def __init__(self, config: Config):
        self.config = config
        self.llm = LLMClient(config.llm)
        self.conversation = Conversation()
        self.tools = ToolRegistry()
        self.running = False
        self._turn_count = 0

        self._register_tools()
        self._setup_system_prompt()

    def _register_tools(self):
        """Register all available tools."""
        wd = self.config.agent.working_directory

        # File operations
        self.tools.register(ReadFileTool(wd))
        self.tools.register(WriteFileTool(wd))
        self.tools.register(EditFileTool(wd))
        self.tools.register(ListDirectoryTool(wd))

        # Search
        self.tools.register(GrepTool(wd))
        self.tools.register(GlobTool(wd))

        # Shell and git
        self.tools.register(BashTool(wd, self.config.agent.auto_approve_bash))
        self.tools.register(GitTool(wd))

        # Web operations
        if self.config.web.enabled:
            self.tools.register(WebSearchTool(self.config.web))
            self.tools.register(WebFetchTool(self.config.web))
            self.tools.register(AgentScannerTool(self.config.web))

    def _setup_system_prompt(self):
        """Set up the system prompt with tool descriptions."""
        tool_desc = self.tools.get_tool_descriptions()
        prompt = get_system_prompt(self.config.agent.working_directory, tool_desc)
        self.conversation.add_system(prompt)

    def process_message(self, user_input: str) -> str:
        """Process a user message and return the agent's response.

        This is the main agent loop:
        1. Send user message + history to LLM
        2. If LLM wants to use tools, execute them
        3. Send tool results back to LLM
        4. Repeat until LLM gives a final response
        """
        self.conversation.add_user(user_input)
        self._turn_count = 0

        while self._turn_count < self.config.agent.max_turns:
            self._turn_count += 1

            # Call the LLM
            try:
                response = self._call_llm()
            except OllamaError as e:
                error_msg = f"LLM Error: {e}"
                print(error(error_msg))
                return error_msg

            content = response.get("message", {}).get("content", "")
            tool_calls_from_api = response.get("message", {}).get("tool_calls", [])

            # Check for tool calls in the content (```tool blocks)
            tool_calls_from_content = self._extract_tool_calls(content)

            # Clean content (remove tool blocks for display)
            display_content = self._clean_content(content)

            if tool_calls_from_api:
                # Handle native Ollama tool calls
                self.conversation.add_assistant(content, tool_calls_from_api)

                if display_content.strip():
                    print(display_content)

                for tc in tool_calls_from_api:
                    func = tc.get("function", {})
                    name = func.get("name", "unknown")
                    args = func.get("arguments", {})
                    self._execute_and_record_tool(name, args, tc.get("id", name))

            elif tool_calls_from_content:
                # Handle tool calls from content
                self.conversation.add_assistant(content)

                if display_content.strip():
                    print(display_content)

                for tc in tool_calls_from_content:
                    name = tc["tool"]
                    args = tc.get("args", {})
                    self._execute_and_record_tool(name, args, name)

            else:
                # No tool calls - this is the final response
                self.conversation.add_assistant(content)
                return content

        return content + "\n\n" + warning("[Max turns reached]")

    def _call_llm(self) -> dict:
        """Call the LLM with current conversation and tools."""
        messages = self.conversation.get_messages()
        tools = self.tools.get_ollama_tools()

        # Show thinking indicator
        stop_spinner = self._start_spinner("Thinking")

        try:
            result = self.llm.chat(messages, tools=tools)
            return result
        finally:
            stop_spinner()

    def _execute_and_record_tool(self, name: str, args: dict, call_id: str):
        """Execute a tool and record results in conversation."""
        tool = self.tools.get(name)
        if not tool:
            err_msg = f"Unknown tool: {name}"
            print(error(f"  {err_msg}"))
            self.conversation.add_tool_result(call_id, name, err_msg)
            return

        # Display what's being executed
        print(f"  {format_tool_call(name, args)}")

        # Check for confirmation if needed
        if not self._should_auto_approve(name, args):
            if not self._confirm_action(name, args):
                msg = "Action cancelled by user"
                print(warning(f"  {msg}"))
                self.conversation.add_tool_result(call_id, name, msg)
                return

        # Execute with spinner
        stop_spinner = self._start_spinner(f"Running {name}")
        try:
            result = tool.execute(**args)
        except Exception as e:
            result = ToolResult(False, "", f"Tool execution error: {e}")
        finally:
            stop_spinner()

        # Display result
        print(f"  {format_tool_result(name, result)}")

        # Record in conversation
        self.conversation.add_tool_result(call_id, name, str(result))

    def _should_auto_approve(self, name: str, args: dict) -> bool:
        """Check if a tool call should be auto-approved."""
        cfg = self.config.agent
        if name in ("read_file", "list_directory") and cfg.auto_approve_reads:
            return True
        if name in ("grep", "glob") and cfg.auto_approve_searches:
            return True
        if name == "bash" and cfg.auto_approve_bash:
            return True
        if name in ("write_file", "edit_file") and cfg.auto_approve_writes:
            return True
        if name in ("web_search", "web_fetch", "scan_agents"):
            return True  # Web operations are read-only
        if name == "git":
            cmd = args.get("command", "").strip().split()[0] if args.get("command") else ""
            read_only = {"status", "diff", "log", "show", "branch", "remote", "tag", "stash"}
            if cmd in read_only:
                return True
        return False

    def _confirm_action(self, name: str, args: dict) -> bool:
        """Ask user for confirmation."""
        print(warning(f"\n  Confirm {name}? [y/N] "), end="", flush=True)
        try:
            answer = input().strip().lower()
            return answer in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False

    def _extract_tool_calls(self, content: str) -> list[dict]:
        """Extract tool calls from ```tool code blocks in LLM response.

        Handles multiple formats the LLM might use:
          - {"tool": "name", "args": {...}}
          - {"name": "name", "arguments": {...}}
          - {"function": "name", "parameters": {...}}
        """
        # Match ```tool blocks and also bare ```json blocks containing tool calls
        patterns = [
            r"```tool\s*\n(.*?)\n```",
            r"```json\s*\n(.*?)\n```",
            r"```\s*\n(\{[^`]*\"(?:tool|name|function)\"[^`]*\})\s*\n```",
        ]

        tool_calls = []
        seen = set()

        for pat in patterns:
            matches = re.findall(pat, content, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match.strip())
                except json.JSONDecodeError:
                    continue

                # Normalize various formats to {"tool": ..., "args": ...}
                tool_name = (
                    data.get("tool")
                    or data.get("name")
                    or data.get("function")
                )
                tool_args = (
                    data.get("args")
                    or data.get("arguments")
                    or data.get("parameters")
                    or {}
                )

                if tool_name and tool_name not in seen:
                    seen.add(tool_name)
                    tool_calls.append({"tool": tool_name, "args": tool_args})

        return tool_calls

    def _clean_content(self, content: str) -> str:
        """Remove tool call blocks from content for display."""
        cleaned = content
        # Remove ```tool blocks
        cleaned = re.sub(r"```tool\s*\n.*?\n```", "", cleaned, flags=re.DOTALL)
        # Remove ```json blocks that contain tool calls
        cleaned = re.sub(
            r"```json\s*\n\{[^`]*\"(?:tool|name|function)\"[^`]*\}\s*\n```",
            "", cleaned, flags=re.DOTALL,
        )
        # Remove bare ``` blocks with tool calls
        cleaned = re.sub(
            r"```\s*\n\{[^`]*\"(?:tool|name|function)\"[^`]*\}\s*\n```",
            "", cleaned, flags=re.DOTALL,
        )
        return cleaned.strip()

    def _start_spinner(self, message: str):
        """Start a terminal spinner. Returns a function to stop it."""
        frames = spinner_frames()
        stop_event = threading.Event()

        def spin():
            i = 0
            while not stop_event.is_set():
                frame = frames[i % len(frames)]
                try:
                    sys.stdout.write(f"\r  {dim(frame)} {dim(message)}...")
                    sys.stdout.flush()
                except (UnicodeEncodeError, OSError):
                    pass
                i += 1
                stop_event.wait(0.1)
            try:
                sys.stdout.write("\r" + " " * 60 + "\r")
                sys.stdout.flush()
            except (UnicodeEncodeError, OSError):
                pass

        thread = threading.Thread(target=spin, daemon=True)
        thread.start()

        def stop():
            stop_event.set()
            thread.join(timeout=1)

        return stop

    def update_working_directory(self, new_dir: str):
        """Update the working directory for all tools."""
        self.config.agent.working_directory = new_dir
        self._register_tools()
        self._setup_system_prompt()

    def reset(self):
        """Reset the conversation."""
        self.conversation.clear()
        self._setup_system_prompt()
        self._turn_count = 0

"""Conversation and context management."""

import json
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Message:
    """A single message in the conversation."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: Optional[list] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None  # tool name for tool messages
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d


class Conversation:
    """Manages conversation history with context window awareness."""

    def __init__(self, max_messages: int = 200, max_chars: int = 100000):
        self.messages: list[Message] = []
        self.max_messages = max_messages
        self.max_chars = max_chars

    def add_system(self, content: str):
        # Replace any existing system message
        self.messages = [m for m in self.messages if m.role != "system"]
        self.messages.insert(0, Message(role="system", content=content))

    def add_user(self, content: str):
        self.messages.append(Message(role="user", content=content))

    def add_assistant(self, content: str, tool_calls: Optional[list] = None):
        self.messages.append(
            Message(role="assistant", content=content, tool_calls=tool_calls)
        )

    def add_tool_result(self, tool_call_id: str, name: str, content: str):
        self.messages.append(
            Message(role="tool", content=content, tool_call_id=tool_call_id, name=name)
        )

    def get_messages(self) -> list[dict]:
        """Get messages formatted for the LLM API, with context management."""
        self._trim_context()
        return [m.to_dict() for m in self.messages]

    def _trim_context(self):
        """Trim conversation to fit within limits, keeping system message."""
        if len(self.messages) <= 2:
            return

        # Calculate total chars
        total_chars = sum(len(m.content) for m in self.messages)

        # Remove oldest non-system messages if over limits
        while (
            len(self.messages) > self.max_messages or total_chars > self.max_chars
        ) and len(self.messages) > 2:
            # Remove the oldest non-system message
            for i, m in enumerate(self.messages):
                if m.role != "system":
                    total_chars -= len(self.messages[i].content)
                    self.messages.pop(i)
                    break

    def clear(self):
        """Clear all messages except system."""
        system = [m for m in self.messages if m.role == "system"]
        self.messages = system

    def save(self, path: Path):
        """Save conversation to a JSON file."""
        data = [m.to_dict() | {"timestamp": m.timestamp} for m in self.messages]
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, path: Path):
        """Load conversation from a JSON file."""
        if not path.exists():
            return
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.messages = []
        for d in data:
            self.messages.append(
                Message(
                    role=d["role"],
                    content=d["content"],
                    tool_calls=d.get("tool_calls"),
                    tool_call_id=d.get("tool_call_id"),
                    name=d.get("name"),
                    timestamp=d.get("timestamp", 0),
                )
            )

    @property
    def turn_count(self) -> int:
        return sum(1 for m in self.messages if m.role == "assistant")

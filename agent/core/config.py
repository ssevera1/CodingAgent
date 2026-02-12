"""Configuration management for CodeAgent."""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


DEFAULT_CONFIG_DIR = Path.home() / ".codeagent"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_MEMORY_DIR = DEFAULT_CONFIG_DIR / "memory"


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = "ollama"
    model: str = "qwen2.5-coder:7b-instruct-q4_K_M"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.1
    max_tokens: int = 4096
    context_window: int = 32768
    timeout: int = 120


@dataclass
class AgentConfig:
    """Agent behavior configuration."""
    max_turns: int = 50
    auto_approve_reads: bool = True
    auto_approve_searches: bool = True
    auto_approve_writes: bool = False
    auto_approve_bash: bool = False
    safety_checks: bool = True
    working_directory: str = field(default_factory=lambda: os.getcwd())
    verbose: bool = False


@dataclass
class WebConfig:
    """Web/internet feature configuration."""
    enabled: bool = True
    search_engine: str = "duckduckgo"
    request_timeout: int = 15
    max_results: int = 10
    user_agent: str = "CodeAgent/1.0"


@dataclass
class Config:
    """Root configuration."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    web: WebConfig = field(default_factory=WebConfig)

    def save(self, path: Optional[Path] = None):
        path = path or DEFAULT_CONFIG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        path = path or DEFAULT_CONFIG_FILE
        if not path.exists():
            config = cls()
            config.save(path)
            return config
        with open(path) as f:
            data = json.load(f)
        return cls(
            llm=LLMConfig(**data.get("llm", {})),
            agent=AgentConfig(**data.get("agent", {})),
            web=WebConfig(**data.get("web", {})),
        )

    @classmethod
    def ensure_dirs(cls):
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_MEMORY_DIR.mkdir(parents=True, exist_ok=True)

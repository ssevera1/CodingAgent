# Changelog

All notable changes to CodeAgent are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `design/` directory with comprehensive architectural documentation
  - C4 model diagrams (Context, Container, Component, Code) using Mermaid.js
  - 8 Architecture Decision Records covering Ollama backend, zero dependencies,
    dual tool-call parsing, safety model, context windowing, DuckDuckGo search,
    tool registry, and cross-platform shell execution

## [1.0.0] - 2026-02-11

### Added
- **Core agent engine** with multi-turn LLM-tool loop (max 50 turns, configurable)
- **Ollama integration** via REST API — zero API keys, fully local inference
- **11 built-in tools:**
  - File operations: `read_file`, `write_file`, `edit_file`, `list_directory`
  - Code search: `grep` (regex), `glob` (pattern matching)
  - Shell execution: `bash` (cross-platform with safety checks)
  - Git operations: `git` (with safety rails for destructive commands)
  - Web: `web_search` (DuckDuckGo), `web_fetch` (URL content extraction)
  - Discovery: `scan_agents` (GitHub-based coding agent scanner)
- **Safety system** with three tiers: blocked commands, warned commands, and
  auto-approved read-only operations
- **Secret detection** for API keys, passwords, private keys, and sensitive files
- **Conversation management** with context windowing (200 messages / 100K chars)
  and JSON persistence (`/save`, `/load`)
- **Configuration system** with layered defaults: dataclass defaults → config file
  (`~/.codeagent/config.json`) → CLI overrides
- **Interactive REPL** with slash commands: `/help`, `/status`, `/model`, `/models`,
  `/scan`, `/config`, `/cd`, `/verbose`, `/save`, `/load`, `/version`
- **Single-prompt mode** for one-shot execution (`codeagent "prompt"`)
- **Cross-platform support** for Windows, Linux, and macOS
- **Zero external dependencies** — built entirely on Python 3.10+ standard library
- **Windows launchers:**
  - `CodeAgent.bat` — double-click launcher with auto Ollama startup
  - `CreateDesktopShortcut.bat` / `make_shortcut.ps1` — desktop shortcut creators
- **Installers:** `install.bat` (Windows), `install.sh` (Linux/macOS)
- **Documentation:** `README.md`, `docs/ARCHITECTURE.md`, `docs/CONFIGURATION.md`,
  `docs/QUICKSTART.md`, `docs/TOOLS.md`, `docs/AGENT_SCANNER.md`
- **Test suite:** 50 tests (17 integration, 33 unit) covering engine and all tools

[Unreleased]: https://github.com/ssevera1/CodingAgent/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/ssevera1/CodingAgent/releases/tag/v1.0.0

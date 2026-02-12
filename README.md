# CodeAgent

**A fully offline coding agent powered by local LLMs via Ollama.**

CodeAgent is a terminal-based coding assistant that replicates the functionality of commercial coding agents like Claude Code — but runs entirely on your local machine with no API keys, no subscriptions, and no data leaving your computer.

```
   ____          _         _                    _
  / ___|___   __| | ___   / \   __ _  ___ _ __ | |_
 | |   / _ \ / _` |/ _ \ / _ \ / _` |/ _ \ '_ \| __|
 | |__| (_) | (_| |  __// ___ \ (_| |  __/ | | | |_
  \____\___/ \__,_|\___/_/   \_\__, |\___|_| |_|\__|
                               |___/
```

---

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Windows](#windows)
  - [Linux](#linux)
  - [macOS](#macos)
  - [Manual Installation (All Platforms)](#manual-installation-all-platforms)
- [Downloading the LLM Model](#downloading-the-llm-model)
- [Running CodeAgent](#running-codeagent)
  - [Interactive Mode](#interactive-mode)
  - [One-Shot Mode](#one-shot-mode)
  - [Fully Offline Mode](#fully-offline-mode)
- [CLI Flags Reference](#cli-flags-reference)
- [Interactive Commands](#interactive-commands)
- [Tools Reference](#tools-reference)
  - [File Operations](#file-operations)
  - [Code Search](#code-search)
  - [Shell Execution](#shell-execution)
  - [Git Operations](#git-operations)
  - [Web Operations](#web-operations)
  - [Agent Scanner](#agent-scanner)
- [Example Sessions](#example-sessions)
- [Configuration](#configuration)
  - [Config File Location](#config-file-location)
  - [Full Configuration Reference](#full-configuration-reference)
  - [LLM Settings](#llm-settings)
  - [Agent Settings](#agent-settings)
  - [Web Settings](#web-settings)
- [Recommended Models](#recommended-models)
- [Architecture](#architecture)
  - [Project Structure](#project-structure)
  - [How the Agent Loop Works](#how-the-agent-loop-works)
  - [Data Flow Diagram](#data-flow-diagram)
- [Safety and Security](#safety-and-security)
- [Troubleshooting](#troubleshooting)
- [Running Tests](#running-tests)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Features

### Core Capabilities
- **File Operations** — Read, write, and edit files with line-level precision
- **Code Search** — Grep (regex content search) and Glob (file pattern matching)
- **Shell Execution** — Run any terminal command with built-in safety checks
- **Git Integration** — Full git operations with protection against destructive commands
- **Conversation Memory** — Maintains context across your entire coding session
- **Multi-turn Agent Loop** — Autonomously chains tool calls to complete complex tasks
- **Cross-Platform** — Works on Windows, Linux, and macOS

### Internet Features
- **Web Search** — Search the web via DuckDuckGo (no API key needed)
- **Web Fetch** — Read and extract content from any URL
- **Agent Scanner** — Discover and compare the latest open-source coding agents from GitHub in real-time

### Safety and Security
- Blocked dangerous commands (`rm -rf /`, fork bombs, etc.)
- Confirmation prompts for destructive operations (file writes, shell commands)
- Secret detection in files (API keys, tokens, passwords)
- Path traversal protection
- Git safety (blocks force-push to main/master, blocks interactive rebase)

### Zero Dependencies
- **No pip packages required** — uses only the Python standard library
- Ollama communication via `urllib` (stdlib)
- All tools implemented with stdlib modules
- Works in completely air-gapped environments

---

## Prerequisites

You need two things installed before using CodeAgent:

### 1. Python 3.10 or higher

Check if you have Python installed:
```bash
python --version
```

If not installed:
- **Windows**: Download from [python.org/downloads](https://www.python.org/downloads/). During installation, **check "Add Python to PATH"**.
- **Linux (Debian/Ubuntu)**: `sudo apt update && sudo apt install python3 python3-pip`
- **Linux (Fedora)**: `sudo dnf install python3 python3-pip`
- **Linux (Arch)**: `sudo pacman -S python python-pip`
- **macOS**: `brew install python3` or download from [python.org](https://www.python.org/downloads/)

### 2. Ollama

Ollama is the local LLM runtime that CodeAgent uses to run AI models on your machine.

Check if you have Ollama installed:
```bash
ollama --version
```

If not installed:
- **Windows**: Download the installer from [ollama.com/download](https://ollama.com/download)
- **Linux**: `curl -fsSL https://ollama.com/install.sh | sh`
- **macOS**: `brew install ollama` or download from [ollama.com/download](https://ollama.com/download)

After installing, make sure Ollama is running:
```bash
ollama serve
```
> On Windows and macOS, Ollama typically runs automatically as a background service after installation. On Linux, you may need to start it manually with `ollama serve` or enable the systemd service.

---

## Installation

### Windows

```batch
git clone https://github.com/ssevera1/CodingAgent.git
cd CodingAgent
install.bat
```

The installer will:
1. Verify Python and Ollama are installed
2. Install CodeAgent as a CLI command
3. Download the recommended coding LLM model if not already present

### Linux

```bash
git clone https://github.com/ssevera1/CodingAgent.git
cd CodingAgent
chmod +x install.sh
./install.sh
```

### macOS

```bash
git clone https://github.com/ssevera1/CodingAgent.git
cd CodingAgent
chmod +x install.sh
./install.sh
```

### Manual Installation (All Platforms)

If you prefer to install manually:

```bash
# 1. Clone the repository
git clone https://github.com/ssevera1/CodingAgent.git
cd CodingAgent

# 2. Install CodeAgent as a package
pip install -e .

# 3. Download the coding LLM model (4.7GB)
ollama pull qwen2.5-coder:7b-instruct-q4_K_M

# 4. Verify installation
codeagent --version
```

### Verifying Everything Works

```bash
# Check CodeAgent is installed
codeagent --version
# Output: CodeAgent v1.0.0

# Check Ollama is running
ollama list
# Should show qwen2.5-coder:7b-instruct-q4_K_M

# Quick test
codeagent "what is 2 + 2?"
```

---

## Downloading the LLM Model

CodeAgent runs on local LLMs via Ollama. You need at least one model downloaded.

### Recommended Model (Best Balance)

```bash
ollama pull qwen2.5-coder:7b-instruct-q4_K_M
```

This is **Qwen 2.5 Coder 7B** — one of the highest-rated open-source coding LLMs. It's 4.7GB and needs about 6GB of VRAM (GPU memory).

### Alternative Models

| Model | Download Command | Size | VRAM | Best For |
|-------|------------------|------|------|----------|
| Qwen 2.5 Coder 1.5B | `ollama pull qwen2.5-coder:1.5b` | 1 GB | 2 GB | Low-end hardware, fast responses |
| Qwen 2.5 Coder 7B | `ollama pull qwen2.5-coder:7b-instruct-q4_K_M` | 4.7 GB | 6 GB | **Best balance (recommended)** |
| DeepSeek Coder V2 16B | `ollama pull deepseek-coder-v2:16b` | 9 GB | 12 GB | Advanced coding tasks |
| CodeLlama 13B | `ollama pull codellama:13b` | 7 GB | 10 GB | Meta's coding model |
| Llama 3 8B | `ollama pull llama3:8b` | 4.7 GB | 6 GB | General purpose + coding |
| Qwen 2.5 Coder 32B | `ollama pull qwen2.5-coder:32b` | 18 GB | 24 GB | Maximum quality (needs RTX 4090+) |

### Checking Available Models

```bash
# List all downloaded models
ollama list

# Inside CodeAgent, use:
/models
```

### Switching Models

```bash
# At launch
codeagent --model codellama:13b

# Inside CodeAgent
/model deepseek-coder-v2:16b
```

### Hardware Requirements

| Model Size | Minimum RAM | Minimum VRAM | Example GPUs |
|------------|-------------|--------------|--------------|
| 1.5B | 4 GB | 2 GB | Any modern GPU, Intel iGPU |
| 7B | 8 GB | 6 GB | RTX 3060, RTX 4060, M1 |
| 13B | 16 GB | 10 GB | RTX 3080, RTX 4070, M1 Pro |
| 32B+ | 32 GB | 24 GB+ | RTX 4090, A100, M1 Ultra |

> **No GPU?** Ollama can run on CPU only. It will be slower but works. The 1.5B and 7B models are usable on CPU.

---

## Running CodeAgent

### Interactive Mode

This is the primary way to use CodeAgent. It starts a REPL (Read-Eval-Print Loop) where you type natural language requests:

```bash
codeagent
```

You'll see the CodeAgent banner and a prompt:
```
   ____          _         _                    _
  / ___|___   __| | ___   / \   __ _  ___ _ __ | |_
 ...
  v1.0.0 | Type /help for commands

  Model: qwen2.5-coder:7b-instruct-q4_K_M
  Dir:   /home/user/project
  Web:   Enabled

project >
```

Type anything naturally:
```
project > read main.py and explain what it does
project > find all functions that handle HTTP requests
project > add error handling to the database module
project > /scan
project > /quit
```

### One-Shot Mode

Run a single command and exit. Useful for scripting:

```bash
codeagent "explain what this project does"
codeagent "find all TODO comments in the codebase"
codeagent "show git status"
```

### Fully Offline Mode

Disable all internet features for complete air-gapped operation:

```bash
codeagent --no-web
```

This disables web search, web fetch, and agent scanning. All other features (file ops, code search, shell, git) work without internet.

### With a Specific Project Directory

```bash
codeagent --dir /path/to/your/project
codeagent --dir C:\Users\you\projects\myapp
```

---

## CLI Flags Reference

```
usage: codeagent [-h] [--model MODEL] [--dir DIR] [--config CONFIG]
                 [--verbose] [--no-web] [--auto-approve] [--version]
                 [prompt ...]
```

| Flag | Short | Description |
|------|-------|-------------|
| `--model MODEL` | `-m` | Ollama model to use (overrides config) |
| `--dir DIR` | `-d` | Working directory (default: current directory) |
| `--config CONFIG` | `-c` | Path to config file |
| `--verbose` | `-v` | Enable verbose/debug output |
| `--no-web` | | Disable all internet features |
| `--auto-approve` | | Auto-approve all tool executions (use with caution!) |
| `--version` | | Show version and exit |
| `prompt` | | Optional prompt for one-shot mode |

### Examples

```bash
# Interactive with specific model and directory
codeagent --model codellama:13b --dir ~/my-project

# One-shot, verbose, offline
codeagent --no-web --verbose "list all Python files"

# Auto-approve everything (for trusted automation)
codeagent --auto-approve "run the test suite and fix failures"
```

---

## Interactive Commands

These slash commands are available inside the CodeAgent REPL:

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/quit` or `/exit` | Exit CodeAgent |
| `/clear` | Clear conversation history and start fresh |
| `/status` | Show agent status (model, directory, message count) |
| `/model [name]` | Show current model or switch to a different one |
| `/models` | List all Ollama models available locally |
| `/scan [category]` | Scan the internet for the latest coding agents |
| `/config` | Show current configuration values |
| `/cd <path>` | Change working directory |
| `/verbose` | Toggle verbose/debug output on or off |
| `/save [file]` | Save conversation to a JSON file (default: `conversation.json`) |
| `/load [file]` | Load a previously saved conversation |
| `/version` | Show CodeAgent version |

---

## Tools Reference

CodeAgent has **11 built-in tools** that the LLM can use autonomously:

### File Operations

#### `read_file`
Read file contents with line numbers.
- **Parameters**: `file_path` (required), `offset` (optional, start line), `limit` (optional, max lines)
- **Auto-approved**: Yes
- **Example**: Reads `src/main.py` and returns numbered lines

#### `write_file`
Write content to a file. Creates parent directories if needed.
- **Parameters**: `file_path` (required), `content` (required)
- **Auto-approved**: No (asks for confirmation)
- **Behavior**: Overwrites existing files, creates directories automatically

#### `edit_file`
Edit a file by finding and replacing an exact string.
- **Parameters**: `file_path` (required), `old_string` (required), `new_string` (required), `replace_all` (optional)
- **Auto-approved**: No (asks for confirmation)
- **Safety**: Fails if `old_string` isn't found or matches multiple times (unless `replace_all=true`)

#### `list_directory`
List files and directories with sizes.
- **Parameters**: `path` (optional), `recursive` (optional)
- **Auto-approved**: Yes

### Code Search

#### `grep`
Search file contents using regex patterns (like ripgrep).
- **Parameters**: `pattern` (required), `path`, `glob_filter`, `case_insensitive`, `context_lines`, `max_results`
- **Auto-approved**: Yes
- **Automatically skips**: `.git/`, `node_modules/`, `__pycache__/`, binary files

#### `glob`
Find files by name pattern.
- **Parameters**: `pattern` (required, e.g., `**/*.py`), `path`, `max_results`
- **Auto-approved**: Yes
- **Returns**: Files sorted by modification time (newest first)

### Shell Execution

#### `bash`
Execute shell commands with safety checks.
- **Parameters**: `command` (required), `timeout` (optional, default 120s, max 600s)
- **Auto-approved**: No (asks for confirmation)
- **Blocked**: `rm -rf /`, fork bombs, `mkfs`, etc.
- **Warned**: `rm -rf`, `git push --force`, `git reset --hard`, etc.
- **Output**: Truncated at 30,000 characters

### Git Operations

#### `git`
Execute git commands with safety rails.
- **Parameters**: `command` (required, e.g., `status`, `diff --staged`, `log --oneline -10`)
- **Auto-approved**: Read-only commands only (`status`, `diff`, `log`, `show`, `branch`, `remote`, `tag`, `stash`)
- **Blocked**: Force-push to main/master, interactive mode (`-i`)
- **Warned**: `reset --hard`, `clean -f`, `checkout .`, `branch -D`

### Web Operations

#### `web_search`
Search the web using DuckDuckGo (no API key needed).
- **Parameters**: `query` (required), `max_results` (optional, default 5)
- **Auto-approved**: Yes (read-only)

#### `web_fetch`
Fetch and extract readable text from a URL.
- **Parameters**: `url` (required), `max_length` (optional, default 10000 chars)
- **Auto-approved**: Yes (read-only)
- **Features**: HTML-to-text conversion, removes scripts/styles

### Agent Scanner

#### `scan_agents`
Scan the internet for the latest open-source coding agents.
- **Parameters**: `category` (`all`, `cli`, `ide`, `web`, `framework`), `query`, `sort_by` (`stars`, `updated`, `name`), `discover_new` (boolean)
- **Auto-approved**: Yes (read-only)
- **Tracks**: 13+ well-known coding agents via GitHub API
- **Discovers**: New agents via GitHub search

**Quick usage from the REPL:**
```
/scan              # All agents, sorted by stars
/scan cli          # Terminal-based agents only
/scan ide          # Editor/IDE plugins only
/scan web          # Browser-based agents only
/scan framework    # Agent frameworks only
```

### Tool Approval Matrix

| Tool | Default Approval | Config Key |
|------|-----------------|------------|
| `read_file` | Auto | `auto_approve_reads` |
| `write_file` | Confirm | `auto_approve_writes` |
| `edit_file` | Confirm | `auto_approve_writes` |
| `list_directory` | Auto | `auto_approve_reads` |
| `grep` | Auto | `auto_approve_searches` |
| `glob` | Auto | `auto_approve_searches` |
| `bash` | Confirm | `auto_approve_bash` |
| `git` (read) | Auto | -- |
| `git` (write) | Confirm | -- |
| `web_search` | Auto | -- |
| `web_fetch` | Auto | -- |
| `scan_agents` | Auto | -- |

---

## Example Sessions

### Understanding a Codebase
```
project > what does this project do? give me a high-level overview

project > find the main entry point

project > list all the API endpoints

project > explain the authentication flow
```

### Writing Code
```
project > add input validation to the signup form in auth.py

project > create a new utility function that converts timestamps to ISO format

project > refactor the database module to use connection pooling

project > add type hints to all functions in utils.py
```

### Debugging
```
project > the tests are failing, help me figure out why

project > find where the variable `user_id` is being set to None

project > trace the data flow from the API endpoint to the database

project > why is this function returning an empty list?
```

### Git Workflows
```
project > show me what changed since yesterday

project > create a commit with all the files I modified

project > show the diff between main and this branch

project > what are the last 10 commits?
```

### Web Research and Agent Discovery
```
project > search for "python async context manager best practices"

project > /scan

project > what's the most popular terminal-based coding agent right now?

project > fetch the README from https://github.com/paul-gauthier/aider
```

---

## Configuration

### Config File Location

CodeAgent auto-creates its config on first run:

| OS | Path |
|----|------|
| Windows | `C:\Users\<you>\.codeagent\config.json` |
| Linux | `~/.codeagent/config.json` |
| macOS | `~/.codeagent/config.json` |

### Full Configuration Reference

```json
{
  "llm": {
    "provider": "ollama",
    "model": "qwen2.5-coder:7b-instruct-q4_K_M",
    "base_url": "http://localhost:11434",
    "temperature": 0.1,
    "max_tokens": 4096,
    "context_window": 32768,
    "timeout": 120
  },
  "agent": {
    "max_turns": 50,
    "auto_approve_reads": true,
    "auto_approve_searches": true,
    "auto_approve_writes": false,
    "auto_approve_bash": false,
    "safety_checks": true,
    "working_directory": ".",
    "verbose": false
  },
  "web": {
    "enabled": true,
    "search_engine": "duckduckgo",
    "request_timeout": 15,
    "max_results": 10,
    "user_agent": "CodeAgent/1.0"
  }
}
```

### LLM Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `llm.provider` | `"ollama"` | LLM backend (currently only Ollama) |
| `llm.model` | `"qwen2.5-coder:7b-instruct-q4_K_M"` | Model name (must be pulled in Ollama) |
| `llm.base_url` | `"http://localhost:11434"` | Ollama API URL. Change for remote Ollama instances |
| `llm.temperature` | `0.1` | Randomness (0.0=deterministic, 1.0=creative). **0.1 recommended for coding** |
| `llm.max_tokens` | `4096` | Max response length in tokens (~4 chars per token) |
| `llm.context_window` | `32768` | Conversation history size. Match to model's capability |
| `llm.timeout` | `120` | Seconds to wait for LLM response. Increase for large models or CPU mode |

### Agent Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `agent.max_turns` | `50` | Max tool-use cycles per request. Prevents infinite loops |
| `agent.auto_approve_reads` | `true` | Skip confirmation for file reads |
| `agent.auto_approve_searches` | `true` | Skip confirmation for grep/glob |
| `agent.auto_approve_writes` | `false` | Skip confirmation for file writes (**caution!**) |
| `agent.auto_approve_bash` | `false` | Skip confirmation for shell commands (**caution!**) |
| `agent.safety_checks` | `true` | Enable secret detection, path validation, command blocking |
| `agent.verbose` | `false` | Show debug information |

### Web Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `web.enabled` | `true` | Enable internet features. Set `false` for fully offline |
| `web.search_engine` | `"duckduckgo"` | Search provider |
| `web.request_timeout` | `15` | Seconds to wait for web requests |
| `web.max_results` | `10` | Max search results |

### Connecting to a Remote Ollama Instance

If Ollama runs on a different machine (e.g., a GPU server):

```json
{
  "llm": {
    "base_url": "http://192.168.1.100:11434"
  }
}
```

Or via CLI:
```bash
OLLAMA_HOST=http://192.168.1.100:11434 codeagent
```

---

## Recommended Models

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| `qwen2.5-coder:1.5b` | 1 GB | Very Fast | Basic | Quick tasks, limited hardware |
| `qwen2.5-coder:7b-instruct-q4_K_M` | 4.7 GB | Fast | Good | **Daily driver (recommended)** |
| `deepseek-coder-v2:16b` | 9 GB | Medium | Excellent | Complex coding, refactoring |
| `codellama:13b` | 7 GB | Medium | Good | Python/C++ focus |
| `llama3:8b` | 4.7 GB | Fast | Good | General purpose with coding |
| `qwen2.5-coder:32b` | 18 GB | Slow | Excellent | Maximum quality, needs top GPU |

To download any model:
```bash
ollama pull <model_name>
```

---

## Architecture

### Project Structure

```
CodingAgent/
├── agent/
│   ├── __init__.py            # Package init, version
│   ├── main.py                # CLI entry point, REPL, command handler
│   ├── core/
│   │   ├── engine.py          # Agent loop (LLM <-> Tools orchestration)
│   │   ├── llm.py             # Ollama REST API client
│   │   ├── conversation.py    # Message history & context management
│   │   └── config.py          # Configuration dataclasses & persistence
│   ├── tools/
│   │   ├── base.py            # BaseTool abstract class & ToolRegistry
│   │   ├── file_ops.py        # ReadFile, WriteFile, EditFile, ListDirectory
│   │   ├── search.py          # Grep (regex search), Glob (pattern match)
│   │   ├── bash.py            # Shell command execution + safety
│   │   ├── git.py             # Git operations + safety rails
│   │   ├── web.py             # WebSearch (DuckDuckGo), WebFetch (URL reader)
│   │   └── agent_scanner.py   # Coding agent discovery via GitHub API
│   ├── prompts/
│   │   └── system.py          # System prompt templates
│   └── utils/
│       ├── formatting.py      # ANSI colors, spinner, banner
│       └── safety.py          # Secret detection, path validation
├── docs/
│   ├── QUICKSTART.md          # 5-minute getting started guide
│   ├── TOOLS.md               # Detailed tool reference
│   ├── CONFIGURATION.md       # Config file deep dive
│   ├── AGENT_SCANNER.md       # Agent scanner documentation
│   └── ARCHITECTURE.md        # Internal architecture details
├── tests/
│   ├── test_tools.py          # 33 unit tests for all tools
│   └── test_engine.py         # 17 integration tests for the engine
├── install.bat                # Windows one-click installer
├── install.sh                 # Linux/macOS one-click installer
├── setup.py                   # Python package setup
├── pyproject.toml             # Modern Python build config
├── requirements.txt           # Dependencies (none required!)
├── config.yaml                # Reference configuration file
└── LICENSE                    # MIT License
```

### How the Agent Loop Works

```
User Input
    |
    v
+------------+     +-----------+     +----------------+
|  CLI/REPL  |---->|  Engine   |---->|  Ollama LLM    |
|            |<----|  (Loop)   |<----|  (Local)       |
+------------+     +-----+-----+     +----------------+
                         |
                         v
                 +---------------+
                 | Tool Registry |
                 +---------------+
                 | read_file     |
                 | write_file    |
                 | edit_file     |
                 | list_directory|
                 | grep          |
                 | glob          |
                 | bash          |
                 | git           |
                 | web_search    |
                 | web_fetch     |
                 | scan_agents   |
                 +---------------+
```

**Step-by-step:**

1. User types a message (e.g., "fix the bug in auth.py")
2. Engine sends the full conversation history + tool definitions to the local LLM
3. LLM responds with text and/or tool calls (e.g., "Let me read the file" + `read_file("auth.py")`)
4. Engine checks safety rules and approval settings
5. If approved, the tool executes and returns results
6. Tool results are added to the conversation and sent back to the LLM
7. LLM can call more tools or provide a final text response
8. Loop repeats (up to `max_turns`) until the LLM gives a final answer

### Data Flow Diagram

```
User: "fix the bug in auth.py"
  |
  +--[Turn 1]--> LLM: "I'll read auth.py first"
  |              + tool_call: read_file("auth.py")
  |              |
  |              +--> Tool executes, returns file contents
  |
  +--[Turn 2]--> LLM: "I see the issue on line 42"
  |              + tool_call: edit_file("auth.py", old="...", new="...")
  |              |
  |              +--> User confirms --> Tool executes edit
  |
  +--[Turn 3]--> LLM: "Fixed! The bug was a missing null check on line 42."
                 (no tool calls = final response)
```

---

## Safety and Security

CodeAgent includes multiple layers of safety:

### Blocked Commands
These shell commands are **always blocked** and will never execute:
- `rm -rf /` and `rm -rf /*`
- Fork bombs (`:(){:|:&};:`)
- `mkfs` (filesystem formatting)
- `dd if=` (raw disk writes)
- `chmod -R 777 /`
- `shutdown`, `reboot`, `halt`

### Dangerous Command Warnings
These commands trigger a confirmation prompt even with `--auto-approve`:
- `rm -rf`, `rm -r`, `rmdir`
- `git push --force`, `git reset --hard`
- `git clean -f`, `git checkout .`
- `drop database`, `drop table`, `truncate`

### Git Safety
- **Blocked**: `git push --force main`, `git push --force master`
- **Blocked**: `git add -i`, `git rebase -i` (interactive commands)
- **Auto-approved**: Read-only commands (`status`, `diff`, `log`, `show`, `branch`)
- **Confirmation required**: Write commands (`commit`, `push`, `merge`, `rebase`)

### Secret Detection
CodeAgent warns about:
- Files: `.env`, `credentials.json`, `*.pem`, `*.key`, `id_rsa`, `token.json`
- Content: API keys (`sk-...`, `ghp_...`), passwords, private keys, access tokens
- These files are flagged during git operations to prevent accidental commits

### Path Validation
- Warns when modifying system directories (`/etc`, `/usr`, `C:\Windows`)
- Validates paths before file operations
- Detects path traversal attempts

---

## Troubleshooting

### "Cannot connect to Ollama"

Ollama isn't running. Start it:
```bash
# Start the Ollama server
ollama serve

# Or on Linux with systemd:
sudo systemctl start ollama
```

### "Model not found"

The model isn't downloaded. Pull it:
```bash
ollama pull qwen2.5-coder:7b-instruct-q4_K_M
```

### Slow Responses

1. **Use a smaller model**: `codeagent --model qwen2.5-coder:1.5b`
2. **Check GPU acceleration**: Run `ollama ps` to see if the model is using GPU
3. **Reduce max_tokens**: Edit `~/.codeagent/config.json` and set `"max_tokens": 2048`
4. **Close other GPU apps**: Games, video editors, other ML workloads

### Out of Memory / CUDA Error

1. Use a quantized model (anything with `q4_K_M` in the name)
2. Use a smaller model (1.5B or 7B instead of 13B+)
3. Close other GPU-intensive applications
4. Run on CPU only (slower but uses system RAM instead of VRAM)

### "codeagent" Command Not Found

The package isn't installed or isn't in PATH:
```bash
# Reinstall
pip install -e .

# Or run directly
python -m agent.main
```

### Windows: Unicode/Encoding Errors

If you see encoding errors in the terminal, CodeAgent handles them automatically. If issues persist, try running in Windows Terminal (instead of the old cmd.exe) which has better Unicode support.

### Permission Denied on Linux/macOS

```bash
chmod +x install.sh
sudo pip install -e .
```

---

## Running Tests

CodeAgent includes a full test suite with **50 tests** covering tools, engine, config, conversation management, and safety:

```bash
# Run all tests
python -m pytest tests/ -v

# Run only tool tests
python -m pytest tests/test_tools.py -v

# Run only engine tests
python -m pytest tests/test_engine.py -v
```

Expected output:
```
50 passed in ~10s
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b my-feature`
3. Make your changes
4. Run the test suite: `python -m pytest tests/ -v`
5. Commit: `git commit -m "Add my feature"`
6. Push: `git push origin my-feature`
7. Open a Pull Request

### Adding a New Tool

1. Create a new file in `agent/tools/` (or add to an existing one)
2. Subclass `BaseTool` and implement `name`, `description`, `parameters`, and `execute()`
3. Register it in `agent/core/engine.py` in the `_register_tools()` method
4. Add tests in `tests/test_tools.py`
5. Document it in `docs/TOOLS.md`

### Adding a Known Agent to the Scanner

Edit `agent/tools/agent_scanner.py` and add to `KNOWN_AGENTS`:

```python
{
    "name": "New Agent Name",
    "repo": "owner/repo-name",
    "category": "cli",  # cli, ide, web, or framework
    "description": "What this agent does",
},
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [Ollama](https://ollama.com) - Local LLM runtime
- [Qwen2.5-Coder](https://github.com/QwenLM/Qwen2.5-Coder) - Coding LLM model
- Inspired by [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Aider](https://github.com/paul-gauthier/aider), and [Cline](https://github.com/cline/cline)

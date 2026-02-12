# CodeAgent

**An offline coding agent powered by local LLMs via Ollama.**

CodeAgent is a fully offline, terminal-based coding assistant that replicates the functionality of commercial coding agents like Claude Code — but runs entirely on your local machine with no API keys, no subscriptions, and no data leaving your computer.

```
   ____          _         _                    _
  / ___|___   __| | ___   / \   __ _  ___ _ __ | |_
 | |   / _ \ / _` |/ _ \ / _ \ / _` |/ _ \ '_ \| __|
 | |__| (_) | (_| |  __// ___ \ (_| |  __/ | | | |_
  \____\___/ \__,_|\___/_/   \_\__, |\___|_| |_|\__|
                               |___/
```

## Features

### Core Capabilities
- **File Operations** — Read, write, and edit files with line-level precision
- **Code Search** — Grep (regex content search) and Glob (file pattern matching)
- **Shell Execution** — Run any terminal command with safety checks
- **Git Integration** — Full git operations with protection against destructive commands
- **Conversation Memory** — Maintains context across your coding session
- **Multi-turn Agent Loop** — Autonomously chains tool calls to complete complex tasks

### Internet Features
- **Web Search** — Search the web via DuckDuckGo (no API key needed)
- **Web Fetch** — Read and extract content from any URL
- **Agent Scanner** — Discover and compare the latest open-source coding agents from GitHub

### Safety & Security
- Blocked dangerous commands (rm -rf /, fork bombs, etc.)
- Confirmation prompts for destructive operations
- Secret detection in files (API keys, tokens, passwords)
- Path traversal protection
- Git safety (blocks force-push to main/master)

### Fully Offline
- Runs 100% locally via Ollama — no internet required for core functionality
- Zero external Python dependencies (stdlib only)
- Use `--no-web` flag for complete air-gapped operation

## Quick Start

### Prerequisites
1. **Python 3.10+** — [python.org](https://python.org)
2. **Ollama** — [ollama.com](https://ollama.com)
3. **A coding LLM model** — Downloaded via Ollama

### Installation

#### Windows
```batch
git clone <repo-url> CodeAgent
cd CodeAgent
install.bat
```

#### Linux/macOS
```bash
git clone <repo-url> CodeAgent
cd CodeAgent
chmod +x install.sh
./install.sh
```

#### Manual Installation
```bash
# Install Ollama and pull the coding model
ollama pull qwen2.5-coder:7b-instruct-q4_K_M

# Install CodeAgent
pip install -e .

# Run
codeagent
```

### First Run
```bash
# Interactive mode
codeagent

# With a specific project directory
codeagent --dir /path/to/project

# One-shot prompt
codeagent "explain what this project does"

# Fully offline (no web features)
codeagent --no-web

# Use a different model
codeagent --model llama3:8b
```

## Usage

### Interactive Commands
| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/quit` | Exit CodeAgent |
| `/clear` | Clear conversation history |
| `/status` | Show agent status |
| `/model [name]` | Show or change active model |
| `/models` | List available Ollama models |
| `/scan [category]` | Scan internet for coding agents |
| `/config` | Show current configuration |
| `/cd <path>` | Change working directory |
| `/save [file]` | Save conversation |
| `/load [file]` | Load conversation |

### Example Interactions

**Reading and understanding code:**
```
> explain the main.py file

> what does the function handle_request do?

> find all TODO comments in this project
```

**Writing and editing code:**
```
> add input validation to the login function in auth.py

> create a new test file for the utils module

> refactor the database connection to use connection pooling
```

**Git operations:**
```
> show me the git status

> create a commit with all changed files

> show the diff for the last 3 commits
```

**Web and agent scanning:**
```
> search for "python async best practices"

> /scan cli

> what are the top coding agents right now?
```

## Architecture

```
CodeAgent/
├── agent/
│   ├── main.py              # CLI entry point and REPL
│   ├── core/
│   │   ├── engine.py        # Agent loop (LLM ↔ Tools)
│   │   ├── llm.py           # Ollama API client
│   │   ├── conversation.py  # Context/memory management
│   │   └── config.py        # Configuration system
│   ├── tools/
│   │   ├── base.py          # Tool base class & registry
│   │   ├── file_ops.py      # Read, Write, Edit, ListDir
│   │   ├── search.py        # Grep, Glob
│   │   ├── bash.py          # Shell execution
│   │   ├── git.py           # Git operations
│   │   ├── web.py           # Web search & fetch
│   │   └── agent_scanner.py # Coding agent discovery
│   ├── prompts/
│   │   └── system.py        # System prompts
│   └── utils/
│       ├── formatting.py    # Terminal colors & display
│       └── safety.py        # Security checks
├── docs/                    # Documentation
├── tests/                   # Test suite
├── install.bat              # Windows installer
├── install.sh               # Linux/macOS installer
├── setup.py                 # Package setup
├── pyproject.toml           # Build config
└── config.yaml              # Reference configuration
```

### How It Works

```
User Input
    │
    ▼
┌──────────┐     ┌─────────┐     ┌──────────────┐
│  CLI/REPL │────▶│  Engine  │────▶│  Ollama LLM  │
│           │◀────│  (Loop)  │◀────│  (Local)     │
└──────────┘     └────┬─────┘     └──────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  Tool Registry │
              ├───────────────┤
              │ read_file     │
              │ write_file    │
              │ edit_file     │
              │ grep          │
              │ glob          │
              │ bash          │
              │ git           │
              │ web_search    │
              │ web_fetch     │
              │ scan_agents   │
              └───────────────┘
```

1. User enters a message
2. Engine sends conversation history + tool definitions to the local LLM
3. LLM responds with text and/or tool calls
4. Engine executes requested tools with safety checks
5. Tool results are fed back to the LLM
6. Loop repeats until LLM gives a final text response

## Configuration

Configuration is stored at `~/.codeagent/config.json`. Edit it directly or use the reference `config.yaml`.

### Key Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `llm.model` | `qwen2.5-coder:7b-instruct-q4_K_M` | Ollama model name |
| `llm.temperature` | `0.1` | Lower = more deterministic |
| `llm.max_tokens` | `4096` | Max response length |
| `llm.context_window` | `32768` | Context window size |
| `agent.max_turns` | `50` | Max tool-use turns per request |
| `agent.auto_approve_reads` | `true` | Auto-approve file reads |
| `agent.auto_approve_bash` | `false` | Auto-approve shell commands |
| `web.enabled` | `true` | Enable web features |

### Recommended Models

| Model | Size | Best For |
|-------|------|----------|
| `qwen2.5-coder:7b-instruct-q4_K_M` | 4.7GB | **Best balance** of quality and speed |
| `qwen2.5-coder:1.5b` | 1GB | Fast responses on limited hardware |
| `deepseek-coder-v2:16b` | 9GB | Advanced coding tasks |
| `codellama:13b` | 7GB | Good general coding |
| `llama3:8b` | 4.7GB | General purpose with coding |

Pull any model with: `ollama pull <model_name>`

## Agent Scanner

The built-in agent scanner queries GitHub's API to discover and compare coding agents in real-time.

```bash
# Scan all categories
/scan

# Filter by category
/scan cli        # Terminal-based agents
/scan ide        # Editor plugins
/scan web        # Browser-based agents
/scan framework  # Agent frameworks
```

It tracks 13+ known agents and also discovers new ones via GitHub search, showing stars, language, license, and last update date.

## Offline Mode

CodeAgent's core functionality works completely offline:
```bash
codeagent --no-web
```

This disables web search, web fetch, and agent scanning — but all file operations, code search, shell execution, and git integration work without any internet connection.

## Troubleshooting

### "Cannot connect to Ollama"
```bash
# Start the Ollama server
ollama serve

# Check it's running
ollama list
```

### "Model not found"
```bash
# Pull the default coding model
ollama pull qwen2.5-coder:7b-instruct-q4_K_M
```

### Slow responses
- Use a smaller model: `codeagent --model qwen2.5-coder:1.5b`
- Ensure GPU acceleration is working in Ollama
- Reduce `max_tokens` in config

### Out of memory
- Use a quantized model (q4_K_M variants)
- Close other GPU-intensive applications
- Use CPU-only mode (slower but uses less VRAM)

## License

MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgments

- [Ollama](https://ollama.com) — Local LLM runtime
- [Qwen2.5-Coder](https://github.com/QwenLM/Qwen2.5-Coder) — Coding LLM
- Inspired by [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Aider](https://github.com/paul-gauthier/aider), and [Cline](https://github.com/cline/cline)

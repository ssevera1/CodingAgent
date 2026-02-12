# Quick Start Guide

Get CodeAgent running in under 5 minutes.

## Step 1: Install Prerequisites

### Python 3.10+
- Download from [python.org](https://python.org)
- Make sure `python` and `pip` are in your PATH

### Ollama
- Download from [ollama.com](https://ollama.com)
- Windows: Run the installer
- Linux: `curl -fsSL https://ollama.com/install.sh | sh`
- macOS: `brew install ollama` or download the app

## Step 2: Download a Coding Model

Open a terminal and run:
```bash
ollama pull qwen2.5-coder:7b-instruct-q4_K_M
```

This downloads the Qwen 2.5 Coder model (4.7GB). It's one of the best open-source coding LLMs, optimized for code generation, understanding, and editing.

**Alternative models** (if you have hardware constraints):
```bash
# Smaller, faster (1GB)
ollama pull qwen2.5-coder:1.5b

# Larger, more capable (9GB, needs 16GB+ VRAM)
ollama pull deepseek-coder-v2:16b
```

## Step 3: Install CodeAgent

```bash
cd CodeAgent
pip install -e .
```

Or on Windows, just run:
```batch
install.bat
```

## Step 4: Start Coding

```bash
# Start interactive session
codeagent

# Or point it at your project
codeagent --dir C:\Users\you\projects\myapp
```

You'll see the CodeAgent banner and a prompt. Start typing naturally:

```
CodeAgent > read the main.py file and explain what it does

CodeAgent > find all functions that handle HTTP requests

CodeAgent > add error handling to the database connection code

CodeAgent > run the tests and fix any failures
```

## Step 5: Try Key Features

### File Operations
```
> read src/app.py
> edit src/app.py to add input validation
> create a new file called utils/helpers.py
```

### Code Search
```
> find all Python files in this project
> search for "TODO" comments across the codebase
> find where the User class is defined
```

### Git
```
> show git status
> create a commit with message "Add input validation"
> show the last 5 commits
```

### Agent Scanner (requires internet)
```
> /scan
> /scan cli
```

## Command Reference

| Command | Action |
|---------|--------|
| `/help` | Show all commands |
| `/quit` | Exit |
| `/clear` | Reset conversation |
| `/status` | Show agent info |
| `/scan` | Find coding agents online |
| `/model <name>` | Switch LLM model |
| `/models` | List available models |
| `/cd <path>` | Change directory |

## What's Next?

- Read [TOOLS.md](TOOLS.md) for detailed tool documentation
- Read [CONFIGURATION.md](CONFIGURATION.md) to customize behavior
- Read [AGENT_SCANNER.md](AGENT_SCANNER.md) for the agent discovery feature
- Check the main [README.md](../README.md) for architecture details

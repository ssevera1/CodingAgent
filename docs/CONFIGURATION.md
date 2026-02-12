# Configuration Guide

CodeAgent stores its configuration at `~/.codeagent/config.json`. The config is automatically created on first run.

## Config File Location

| OS | Path |
|----|------|
| Windows | `C:\Users\<you>\.codeagent\config.json` |
| Linux | `~/.codeagent/config.json` |
| macOS | `~/.codeagent/config.json` |

## Full Configuration Reference

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

## LLM Settings

### `llm.model`
The Ollama model to use. Must be already pulled with `ollama pull`.

**Recommended models for coding:**
| Model | VRAM | Quality | Speed |
|-------|------|---------|-------|
| `qwen2.5-coder:7b-instruct-q4_K_M` | 6GB | Good | Fast |
| `qwen2.5-coder:1.5b` | 2GB | Basic | Very Fast |
| `deepseek-coder-v2:16b` | 12GB | Excellent | Medium |
| `codellama:13b` | 10GB | Good | Medium |
| `llama3:8b` | 6GB | Good | Fast |

### `llm.temperature`
Controls response randomness. Range: 0.0 to 1.0.
- `0.0` — Completely deterministic (always same answer)
- `0.1` — **Recommended** for coding (consistent, predictable)
- `0.7` — More creative but less reliable
- `1.0` — Maximum randomness

### `llm.max_tokens`
Maximum length of each LLM response in tokens. One token is roughly 4 characters.
- `2048` — Short responses
- `4096` — **Default**, good balance
- `8192` — Long detailed responses

### `llm.context_window`
How much conversation history the model can see. Depends on the model's capability.
- `4096` — Minimum, short context
- `32768` — **Default for Qwen 2.5 Coder**
- `131072` — Some models support 128K

### `llm.base_url`
Ollama API endpoint. Change this to connect to a remote Ollama instance.
- Local: `http://localhost:11434` (default)
- Remote: `http://192.168.1.100:11434`

### `llm.timeout`
Seconds to wait for LLM response. Increase for larger models or CPU-only inference.

## Agent Settings

### `agent.max_turns`
Maximum number of tool-use cycles per user message. Prevents infinite loops.
- `10` — Quick tasks only
- `50` — **Default**, handles complex tasks
- `100` — Very complex multi-step tasks

### `agent.auto_approve_reads`
Auto-approve file reading and directory listing without asking.
- `true` — **Default**, reads are safe
- `false` — Ask before every file read

### `agent.auto_approve_searches`
Auto-approve grep and glob searches.
- `true` — **Default**, searches are safe
- `false` — Ask before every search

### `agent.auto_approve_writes`
Auto-approve file writes and edits.
- `false` — **Default**, always ask before modifying files
- `true` — Modify files without asking (use with caution)

### `agent.auto_approve_bash`
Auto-approve shell command execution.
- `false` — **Default**, always ask before running commands
- `true` — Run commands without asking (use with caution)

### `agent.safety_checks`
Enable safety validation (path checks, secret detection, command blocking).
- `true` — **Default**, recommended
- `false` — Disable all safety checks (not recommended)

### `agent.verbose`
Show detailed debug information during execution.

## Web Settings

### `web.enabled`
Enable or disable all internet features.
- `true` — **Default**, enables web search, fetch, and agent scanning
- `false` — Fully offline mode, no network requests

Can also be set via CLI: `codeagent --no-web`

### `web.request_timeout`
Seconds to wait for web requests. Increase on slow connections.

### `web.max_results`
Maximum number of search results to return.

## CLI Overrides

All settings can be overridden from the command line:

```bash
# Use a different model
codeagent --model codellama:13b

# Set working directory
codeagent --dir /path/to/project

# Disable web features
codeagent --no-web

# Auto-approve everything (dangerous!)
codeagent --auto-approve

# Verbose output
codeagent --verbose
```

## Environment Variables

CodeAgent respects these environment variables:

| Variable | Description |
|----------|-------------|
| `NO_COLOR` | Disable color output |
| `FORCE_COLOR` | Force color output |
| `OLLAMA_HOST` | Override Ollama base URL |

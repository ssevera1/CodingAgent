# Architecture

This document describes the internal architecture of CodeAgent.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CodeAgent CLI                            │
│  ┌───────────┐  ┌────────────┐  ┌──────────────────────────┐   │
│  │  Argument  │  │    REPL    │  │    Command Handler       │   │
│  │  Parser    │  │  (input)   │  │  (/help, /scan, etc.)    │   │
│  └─────┬─────┘  └──────┬─────┘  └────────────┬─────────────┘   │
│        └───────────┬────┘                     │                 │
│                    ▼                          │                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Agent Engine                          │   │
│  │  ┌────────────────┐  ┌───────────────┐  ┌───────────┐   │   │
│  │  │  Conversation   │  │  Tool         │  │  Safety   │   │   │
│  │  │  Manager        │  │  Registry     │  │  Checks   │   │   │
│  │  └────────┬───────┘  └───────┬───────┘  └─────┬─────┘   │   │
│  │           │                  │                │          │   │
│  │           ▼                  ▼                ▼          │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │              Agent Loop                         │    │   │
│  │  │  1. Send messages + tools to LLM                │    │   │
│  │  │  2. Parse response for tool calls               │    │   │
│  │  │  3. Execute tools with safety checks            │    │   │
│  │  │  4. Feed results back to LLM                    │    │   │
│  │  │  5. Repeat until final text response             │    │   │
│  │  └─────────────────────┬───────────────────────────┘    │   │
│  └────────────────────────┼────────────────────────────────┘   │
│                           │                                     │
└───────────────────────────┼─────────────────────────────────────┘
                            │
              ┌─────────────┴──────────────┐
              │                            │
     ┌────────▼────────┐         ┌─────────▼──────────┐
     │   Ollama LLM    │         │   Tool Executors    │
     │   (Local API)   │         │                     │
     │                 │         │  File: R/W/Edit/Ls  │
     │  qwen2.5-coder  │         │  Search: Grep/Glob  │
     │  or any model   │         │  Shell: Bash        │
     │                 │         │  VCS: Git           │
     └─────────────────┘         │  Web: Search/Fetch  │
                                 │  Scanner: Agents    │
                                 └─────────────────────┘
```

## Component Details

### 1. CLI Layer (`agent/main.py`)

The entry point handles:
- **Argument parsing**: Model selection, working directory, flags
- **REPL loop**: Read-eval-print loop with readline support
- **Command dispatch**: Slash commands (/help, /scan, /model, etc.)
- **Configuration loading**: From file and CLI overrides

### 2. Agent Engine (`agent/core/engine.py`)

The core orchestrator that:
- Initializes and registers all tools
- Manages the system prompt
- Implements the **agent loop** (the critical path):
  1. Formats conversation for the LLM
  2. Calls the LLM with tool definitions
  3. Parses the response (text + tool calls)
  4. Executes approved tool calls
  5. Records results in conversation
  6. Loops back to step 1 if tools were called
  7. Returns final text when no more tools are needed

### 3. LLM Client (`agent/core/llm.py`)

Communicates with Ollama's REST API:
- **Chat endpoint** (`/api/chat`): Main conversation with tool support
- **Generate endpoint** (`/api/generate`): Simple text generation
- **Tags endpoint** (`/api/tags`): Model listing and health checks
- **Pull endpoint** (`/api/pull`): Model downloading
- Uses only `urllib` (no external dependencies)
- Supports streaming responses

### 4. Conversation Manager (`agent/core/conversation.py`)

Manages message history:
- **Context windowing**: Trims old messages to fit model limits
- **Message types**: system, user, assistant, tool
- **Persistence**: Save/load conversations to JSON
- **Turn counting**: Tracks agent turns for loop limits

### 5. Tool System (`agent/tools/`)

#### Base (`base.py`)
- `BaseTool`: Abstract class all tools implement
- `ToolResult`: Standardized success/error return type
- `ToolRegistry`: Registers tools and generates LLM tool schemas

#### File Operations (`file_ops.py`)
- `ReadFileTool`: Read with line numbers, offset/limit
- `WriteFileTool`: Create/overwrite files
- `EditFileTool`: Find-and-replace editing
- `ListDirectoryTool`: Directory listing

#### Search (`search.py`)
- `GrepTool`: Regex content search with context lines
- `GlobTool`: File pattern matching
- Both skip `.git`, `node_modules`, binary files automatically

#### Bash (`bash.py`)
- Shell command execution with timeout
- Blocked commands list (rm -rf /, fork bombs)
- Dangerous command detection (warns before executing)
- Cross-platform (Windows cmd / Unix bash)

#### Git (`git.py`)
- Git command execution with safety rails
- Blocks force-push to main/master
- Blocks interactive mode
- Auto-approves read-only commands

#### Web (`web.py`)
- `WebSearchTool`: DuckDuckGo HTML scraping (no API key)
- `WebFetchTool`: URL fetching with HTML-to-text conversion

#### Agent Scanner (`agent_scanner.py`)
- Queries GitHub API for known coding agents
- Searches GitHub for new agents
- Categorizes agents (cli, ide, web, framework)
- Sorts by stars, update date, or name

### 6. Safety System (`agent/utils/safety.py`)

- **File safety**: Detects sensitive files (.env, credentials, keys)
- **Content safety**: Regex detection of API keys, tokens, passwords
- **Path safety**: Validates paths, warns about system directories
- **Command safety**: Blocks dangerous shell commands

### 7. Formatting (`agent/utils/formatting.py`)

- ANSI color support with Windows compatibility
- Banner, spinners, tool call display
- Graceful fallback when colors aren't supported

## Data Flow

### User Message Processing

```
User types: "fix the bug in auth.py"
    │
    ▼
Engine.process_message("fix the bug in auth.py")
    │
    ├── conversation.add_user(input)
    │
    ├── [Turn 1] LLM call
    │   ├── LLM returns: "Let me read auth.py first" + tool_call(read_file, auth.py)
    │   ├── Execute read_file("auth.py") → ToolResult(content)
    │   └── conversation.add_tool_result(result)
    │
    ├── [Turn 2] LLM call (with file contents in context)
    │   ├── LLM returns: "I see the bug on line 42" + tool_call(edit_file, ...)
    │   ├── Confirm with user (write operation)
    │   ├── Execute edit_file(...) → ToolResult(success)
    │   └── conversation.add_tool_result(result)
    │
    └── [Turn 3] LLM call
        └── LLM returns: "Fixed the bug. The issue was..." (no tool calls)
            │
            ▼
        Final response displayed to user
```

## Design Decisions

### Zero Dependencies
All functionality uses Python's standard library. This means:
- No `pip install` failures
- No version conflicts
- Works in air-gapped environments
- Minimal attack surface

### Ollama as LLM Backend
- Free and open-source
- Runs any GGUF model
- GPU acceleration out of the box
- Simple REST API
- No API keys needed

### Tool Call Parsing
We support two methods of tool calling:
1. **Native Ollama tool calls**: The LLM returns structured `tool_calls` in the API response
2. **Content-based tool calls**: The LLM embeds `\`\`\`tool` blocks in its text response

This dual approach ensures compatibility across different Ollama models, as not all models support native function calling.

### Safety-First Defaults
- File writes require confirmation
- Shell commands require confirmation
- Destructive git operations are blocked
- Sensitive files are flagged
- All safety can be configured but defaults are restrictive

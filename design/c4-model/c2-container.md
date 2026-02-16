# C2 - Container Diagram

Zooms into CodeAgent to show the major runtime units and their interactions.

```mermaid
C4Container
    title Container Diagram — CodeAgent Internals

    Person(dev, "Developer", "Terminal user")

    System_Boundary(codeagent, "CodeAgent Process (Python 3.10+)") {
        Container(cli, "CLI / REPL", "Python, main.py", "Parses arguments, handles slash commands, manages the interactive read-eval-print loop")
        Container(engine, "Agent Engine", "Python, core/engine.py", "Orchestrates the multi-turn LLM-tool loop: send context, parse tool calls, execute, repeat")
        Container(llm_client, "LLM Client", "Python, core/llm.py", "HTTP client for Ollama REST API using only urllib (zero deps)")
        Container(conversation, "Conversation Manager", "Python, core/conversation.py", "Stores message history, applies context windowing, serializes to JSON")
        Container(config, "Configuration Manager", "Python, core/config.py", "Loads/saves config from ~/.codeagent/config.json, merges CLI overrides")
        Container(tools, "Tool System", "Python, tools/*.py", "11 built-in tools: file I/O, search, shell, git, web, agent scanner")
        Container(safety, "Safety Layer", "Python, utils/safety.py", "Validates commands, detects secrets, blocks dangerous operations")
        Container(formatting, "Formatting Layer", "Python, utils/formatting.py", "ANSI colors, spinners, tool call/result rendering")
        Container(prompts, "Prompt Templates", "Python, prompts/system.py", "System prompt with tool definitions, usage guidelines, safety rules")
    }

    System_Ext(ollama, "Ollama Server", "Local LLM inference")
    System_Ext(fs, "Local Filesystem", "Project files and repos")
    System_Ext(web, "External Web", "DuckDuckGo, GitHub, URLs")

    Rel(dev, cli, "Enters prompts and commands", "stdin/stdout")
    Rel(cli, engine, "Delegates user messages", "Function call")
    Rel(cli, config, "Reads/writes settings", "Function call")
    Rel(engine, llm_client, "Sends messages + tool schemas", "Function call")
    Rel(engine, conversation, "Adds/retrieves messages", "Function call")
    Rel(engine, tools, "Executes tool calls", "Function call via ToolRegistry")
    Rel(engine, safety, "Validates before execution", "Function call")
    Rel(engine, prompts, "Loads system prompt", "Function call")
    Rel(engine, formatting, "Renders output", "Function call")
    Rel(llm_client, ollama, "POST /api/chat, /api/tags", "HTTP REST, JSON")
    Rel(tools, fs, "File I/O, subprocess, git", "Python stdlib")
    Rel(tools, web, "Search queries, URL fetches", "HTTPS")
```

## Container Responsibilities

| Container | Responsibility | Key Files |
|-----------|---------------|-----------|
| **CLI / REPL** | User-facing interface, argument parsing, command dispatch | `agent/main.py` |
| **Agent Engine** | Core loop: LLM call &rarr; parse &rarr; execute &rarr; loop | `agent/core/engine.py` |
| **LLM Client** | Zero-dependency HTTP wrapper for Ollama REST API | `agent/core/llm.py` |
| **Conversation Manager** | Message history with context windowing (200 msg / 100K char limits) | `agent/core/conversation.py` |
| **Configuration Manager** | Layered config: defaults &rarr; file &rarr; CLI overrides | `agent/core/config.py` |
| **Tool System** | 11 tools with registry, JSON schema generation, standardized results | `agent/tools/*.py` |
| **Safety Layer** | Command blocking, secret detection, path validation | `agent/utils/safety.py` |
| **Formatting Layer** | Cross-platform ANSI output with color detection and fallbacks | `agent/utils/formatting.py` |
| **Prompt Templates** | System prompt construction with dynamic tool definitions | `agent/prompts/system.py` |

## Latency Profile

```mermaid
gantt
    title Typical Single-Turn Latency Breakdown
    dateFormat X
    axisFormat %s s

    section User Input
    Parse + dispatch           :0, 50

    section LLM Inference
    Ollama /api/chat (7B model) :50, 15000

    section Tool Execution
    Read file                  :15050, 100
    Safety validation          :15050, 20
    Grep search                :15070, 500

    section Response
    Format + render            :15570, 30
```

> **Dominant latency**: LLM inference (1-60s depending on model size, GPU, and
> prompt length). All other operations are sub-second on local hardware.

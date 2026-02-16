# C3 - Component Diagram

Zooms into the Agent Engine and Tool System to show individual components and
their interactions.

## Agent Engine Components

```mermaid
C4Component
    title Component Diagram — Agent Engine

    Container_Boundary(engine_boundary, "Agent Engine") {
        Component(process_msg, "process_message()", "Entry point: accepts user input, runs agent loop, returns final response")
        Component(call_llm, "_call_llm()", "Formats conversation and tool schemas, calls LLM client, returns raw response")
        Component(extract_tc, "_extract_tool_calls()", "Parses tool calls from native API format or ```tool JSON blocks in content")
        Component(approve, "_should_auto_approve() / _confirm_action()", "Approval gate: auto-approves safe ops, prompts user for writes/shell/git")
        Component(execute, "_execute_and_record_tool()", "Runs tool via ToolRegistry, records result in conversation")
        Component(clean, "_clean_content()", "Strips tool JSON blocks from display content")
        Component(spinner, "_start_spinner()", "Background thread: animated terminal spinner during LLM calls")
    }

    Container_Ext(llm, "LLM Client")
    Container_Ext(conv, "Conversation Manager")
    Container_Ext(registry, "ToolRegistry")
    Container_Ext(safety_mod, "Safety Layer")

    Rel(process_msg, call_llm, "Sends formatted messages")
    Rel(call_llm, llm, "HTTP chat completion")
    Rel(process_msg, extract_tc, "Parses LLM response")
    Rel(process_msg, approve, "Checks approval for each tool call")
    Rel(approve, safety_mod, "Validates command safety")
    Rel(process_msg, execute, "Executes approved tools")
    Rel(execute, registry, "Dispatches to registered tool")
    Rel(execute, conv, "Records tool result as message")
    Rel(process_msg, clean, "Cleans response for display")
    Rel(process_msg, spinner, "Shows progress indicator")
```

## Tool System Components

```mermaid
C4Component
    title Component Diagram — Tool System

    Container_Boundary(tools_boundary, "Tool System") {
        Component(base, "BaseTool (ABC)", "Abstract base: name, description, parameters, execute(), to_ollama_tool()")
        Component(registry, "ToolRegistry", "Registers tools, generates JSON Schema array, dispatches by name")
        Component(result, "ToolResult", "Standardized return: success bool, output str, error str")

        Component(read_file, "ReadFile", "Read file with line numbers, offset/limit support")
        Component(write_file, "WriteFile", "Create/overwrite files, auto-creates directories")
        Component(edit_file, "EditFile", "Find-and-replace with uniqueness check and replace_all")
        Component(list_dir, "ListDirectory", "List files/dirs with sizes, optional recursion")
        Component(grep, "Grep", "Regex content search with glob filter and context lines")
        Component(glob, "GlobTool", "File pattern matching sorted by modification time")
        Component(bash_tool, "Bash", "Cross-platform shell execution with safety checks")
        Component(git, "Git", "Git operations with safety rails and auto-approval for reads")
        Component(web_search, "WebSearch", "DuckDuckGo HTML scraping, no API key")
        Component(web_fetch, "WebFetch", "URL fetch with HTML-to-text extraction")
        Component(scanner, "AgentScanner", "GitHub API agent discovery with category filtering")
    }

    Rel(registry, base, "Manages instances of")
    Rel(read_file, base, "extends")
    Rel(write_file, base, "extends")
    Rel(edit_file, base, "extends")
    Rel(list_dir, base, "extends")
    Rel(grep, base, "extends")
    Rel(glob, base, "extends")
    Rel(bash_tool, base, "extends")
    Rel(git, base, "extends")
    Rel(web_search, base, "extends")
    Rel(web_fetch, base, "extends")
    Rel(scanner, base, "extends")
```

## Data Flow: Multi-Turn Agent Loop

```mermaid
sequenceDiagram
    participant U as Developer
    participant CLI as CLI / REPL
    participant E as Engine
    participant C as Conversation
    participant L as LLM Client
    participant O as Ollama
    participant T as ToolRegistry
    participant S as Safety Layer

    U->>CLI: "Find all TODO comments and list them"
    CLI->>E: process_message(input)
    E->>C: add_user(input)

    rect rgb(240, 248, 255)
        Note over E,O: Turn 1 — LLM decides to use grep tool
        E->>C: get_messages()
        C-->>E: [system, user]
        E->>L: chat(messages, tools)
        L->>O: POST /api/chat
        O-->>L: {content, tool_calls: [{grep, {pattern: "TODO"}}]}
        L-->>E: response
        E->>E: _extract_tool_calls()
        E->>E: _should_auto_approve("grep") → true
        E->>T: execute("grep", {pattern: "TODO"})
        T-->>E: ToolResult(success, "file1.py:10: # TODO ...")
        E->>C: add_tool_result(result)
    end

    rect rgb(245, 255, 245)
        Note over E,O: Turn 2 — LLM composes final answer
        E->>C: get_messages()
        C-->>E: [system, user, assistant+tool_call, tool_result]
        E->>L: chat(messages, tools)
        L->>O: POST /api/chat
        O-->>L: {content: "I found 5 TODOs...", tool_calls: []}
        L-->>E: response (no tool calls → loop ends)
    end

    E-->>CLI: "I found 5 TODOs..."
    CLI-->>U: Rendered output

```

## Approval Flow Detail

```mermaid
flowchart TD
    A[Tool call received] --> B{Is tool in auto-approve list?}
    B -->|read_file, list_directory,<br/>grep, glob, web_search,<br/>web_fetch, scan_agents| C[Execute immediately]
    B -->|No| D{Is it a read-only git op?}
    D -->|status, diff, log,<br/>show, branch, remote| C
    D -->|No| E{auto_approve_writes<br/>or auto_approve_bash<br/>enabled in config?}
    E -->|Yes| C
    E -->|No| F[Prompt user for confirmation]
    F -->|Approved| G[Safety validation]
    F -->|Denied| H[Skip, record cancellation]
    G -->|Safe| C
    G -->|Blocked command| I[Reject with warning]
    G -->|Dangerous command| J[Show warning, re-confirm]
    C --> K[Execute tool]
    K --> L[Record ToolResult in conversation]
```

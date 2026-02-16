# C1 - System Context Diagram

Shows CodeAgent as a black box and its relationships with users and external systems.

```mermaid
C4Context
    title System Context Diagram — CodeAgent

    Person(dev, "Developer", "Uses CodeAgent to perform coding tasks via a terminal interface")

    System(codeagent, "CodeAgent", "Offline, terminal-based coding agent that executes multi-turn tool-assisted workflows powered by local LLMs")

    System_Ext(ollama, "Ollama", "Local LLM inference server exposing a REST API on localhost:11434")
    System_Ext(filesystem, "Local Filesystem", "Project files, configs, git repositories the developer works on")
    System_Ext(ddg, "DuckDuckGo", "Public web search engine (HTML scraping, no API key)")
    System_Ext(github, "GitHub API", "Public REST API for repository metadata and agent discovery")
    System_Ext(websites, "Public Web", "Arbitrary URLs fetched for documentation and reference")

    Rel(dev, codeagent, "Sends prompts, approves tool actions", "Terminal / REPL")
    Rel(codeagent, ollama, "Sends chat completions with tool schemas", "HTTP REST, JSON")
    Rel(codeagent, filesystem, "Reads, writes, edits, searches files; runs shell commands", "Python stdlib I/O")
    Rel(codeagent, ddg, "Sends search queries", "HTTPS GET, HTML scraping")
    Rel(codeagent, github, "Fetches repository metadata for agent scanning", "HTTPS REST, JSON")
    Rel(codeagent, websites, "Fetches page content for reference", "HTTPS GET, HTML-to-text")
```

## Data Flow Summary

| Flow | Protocol | Latency | Auth Required |
|------|----------|---------|---------------|
| Developer &rarr; CodeAgent | stdin (terminal) | Instant | None |
| CodeAgent &rarr; Ollama | HTTP REST (localhost) | 1-60s per turn (model-dependent) | None |
| CodeAgent &rarr; Filesystem | Python `pathlib` / `subprocess` | <100ms typical | OS-level permissions |
| CodeAgent &rarr; DuckDuckGo | HTTPS GET | 1-3s | None (HTML scraping) |
| CodeAgent &rarr; GitHub API | HTTPS GET | 1-3s | None (public endpoints, rate-limited) |
| CodeAgent &rarr; Public Web | HTTPS GET | 1-5s | None |

## Key Constraints

- **Fully offline capable**: Ollama and filesystem are the only required
  dependencies. Web features can be disabled with `--no-web`.
- **No API keys anywhere**: All external integrations use public, unauthenticated
  endpoints or local services.
- **Single-user system**: One developer interacts with one CodeAgent instance at
  a time. No multi-tenancy or shared state.

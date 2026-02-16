# CodeAgent Design Documentation

This directory contains architectural documentation for CodeAgent, organized into
two complementary sections:

## C4 Model Diagrams (`c4-model/`)

Visualizations of the system architecture at four levels of abstraction, rendered
with Mermaid.js for in-repo editability and GitHub-native rendering.

| Level | File | What It Shows |
|-------|------|---------------|
| **C1 - Context** | [c1-context.md](c4-model/c1-context.md) | CodeAgent in its environment: users, Ollama, external services |
| **C2 - Container** | [c2-container.md](c4-model/c2-container.md) | Major runtime units: CLI, Engine, LLM Client, Tool System |
| **C3 - Component** | [c3-component.md](c4-model/c3-component.md) | Internal components within each container, data flows, latency |
| **C4 - Code** | [c4-code.md](c4-model/c4-code.md) | Class-level design of the Tool System and Engine core |

## Architecture Decision Records (`adr/`)

A chronological log of significant design decisions, their context, the
alternatives considered, and the trade-offs accepted.

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](adr/ADR-001-local-only-ollama-backend.md) | Local-Only Ollama Backend | Accepted |
| [ADR-002](adr/ADR-002-zero-external-dependencies.md) | Zero External Dependencies | Accepted |
| [ADR-003](adr/ADR-003-dual-tool-call-parsing.md) | Dual Tool-Call Parsing Strategy | Accepted |
| [ADR-004](adr/ADR-004-safety-first-approval-model.md) | Safety-First Tool Approval Model | Accepted |
| [ADR-005](adr/ADR-005-context-windowing-strategy.md) | Context Windowing Over Summarization | Accepted |
| [ADR-006](adr/ADR-006-duckduckgo-web-search.md) | DuckDuckGo for Web Search | Accepted |
| [ADR-007](adr/ADR-007-modular-tool-registry.md) | Modular Tool Registry Pattern | Accepted |
| [ADR-008](adr/ADR-008-cross-platform-shell-execution.md) | Cross-Platform Shell Execution | Accepted |

## How to Read These Diagrams

The Mermaid diagrams render natively on GitHub, GitLab, and most modern Markdown
viewers. To edit interactively, paste diagram source into
[mermaid.live](https://mermaid.live/) or use the Mermaid extension in VS Code.

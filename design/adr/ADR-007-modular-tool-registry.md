# ADR-007: Modular Tool Registry Pattern

**Status:** Accepted
**Date:** 2025-01-18
**Deciders:** Core team

## Context

CodeAgent ships with 11 built-in tools, and the architecture should support
adding new tools without modifying the engine. The tool system needs to:

1. Register tools at startup
2. Generate JSON Schema definitions for the LLM (Ollama tool format)
3. Dispatch tool calls by name
4. Return standardized results
5. Be testable in isolation

## Decision

**Implement a `BaseTool` abstract base class, a `ToolResult` dataclass, and a
`ToolRegistry` that manages tool instances.**

```
BaseTool (ABC)
├── name: str (abstract property)
├── description: str (abstract property)
├── parameters: dict (abstract property, JSON Schema)
├── execute(**kwargs) -> ToolResult (abstract method)
└── to_ollama_tool() -> dict (generates Ollama-format definition)

ToolRegistry
├── register(tool: BaseTool)
├── get(name: str) -> BaseTool
├── execute(name, **kwargs) -> ToolResult
├── get_tool_definitions() -> list[dict]  (all tools as Ollama schemas)
└── update_working_directory(path: str)
```

Each tool is a self-contained class in its own module (or grouped by domain),
and the engine registers all tools at startup.

## Alternatives Considered

### Function-based tools (decorated functions)
- **Pros:** Less boilerplate, familiar pattern from LangChain/OpenAI function calling
- **Cons:** Harder to share state (working directory), no standard way to generate
  schemas, harder to test individual tools
- **Rejected because:** Class-based approach provides cleaner encapsulation for
  stateful tools (working directory, config access)

### Plugin system with entry points
- **Pros:** Third-party tools installable via pip, dynamic discovery
- **Cons:** Requires setuptools entry points, adds install complexity, harder to
  reason about security
- **Rejected because:** Premature for v1.0; the class-based registry makes future
  plugin support straightforward to add

### Hardcoded tool dispatch (if/elif chain)
- **Pros:** Simplest possible implementation, no abstraction overhead
- **Cons:** Adding a tool requires modifying the engine, no schema generation,
  poor separation of concerns
- **Rejected because:** Doesn't scale; 11 tools already means a 200+ line
  dispatch function

### LangChain Tool abstraction
- **Pros:** Battle-tested, community ecosystem
- **Cons:** Massive dependency (`langchain-core` alone pulls in 10+ packages),
  frequent breaking changes, overkill for our needs
- **Rejected because:** Violates ADR-002 (zero dependencies) and adds unnecessary
  abstraction layers

## Consequences

### Positive
- **Easy to add tools**: Implement `BaseTool`, register in engine — done. No
  engine changes needed.
- **Self-documenting**: Each tool carries its own name, description, and JSON
  Schema; the LLM sees exactly what it needs
- **Testable**: Each tool can be instantiated and tested independently
- **Consistent results**: `ToolResult` ensures all tools return the same
  structure (success, output, error)
- **Schema generation**: `to_ollama_tool()` eliminates manual schema maintenance

### Trade-offs Accepted
- **Boilerplate**: Each tool requires a class with 4 abstract members, even for
  trivial tools — more code than a decorated function
- **No dynamic loading**: Tools are registered at startup in `engine.py`; there's
  no way to add tools at runtime or from external packages (intentional for v1.0
  security)
- **Working directory coupling**: Tools inherit `working_directory` from the
  registry, which means they can't operate in different directories simultaneously

# ADR-003: Dual Tool-Call Parsing Strategy

**Status:** Accepted
**Date:** 2025-01-20
**Deciders:** Core team

## Context

Different Ollama models handle tool calling inconsistently:

- **Models with native tool support** (Qwen 2.5, Llama 3.1+) return structured
  `tool_calls` in the API response object.
- **Models without native support** (older CodeLlama, Mistral variants) sometimes
  embed tool calls as JSON blocks within the text content, using markdown code
  fences.
- **Some models mix both**: returning a native tool call *and* repeating it in
  the content body.

A rigid parser that only handles one format would limit model compatibility.

## Decision

**Implement dual parsing: first check for native API tool calls, then fall back
to regex extraction of JSON blocks from content.** Support three JSON schemas:

```json
{"tool": "name", "args": {...}}
{"name": "name", "arguments": {...}}
{"function": "name", "parameters": {...}}
```

Deduplicate tool calls using a `seen` set (keyed on tool name + serialized args)
to prevent double execution when a model returns both native and content-based
calls.

## Alternatives Considered

### Native API only
- **Pros:** Clean, structured, no regex parsing
- **Cons:** Excludes many popular models that don't support native tool calling
- **Rejected because:** Would severely limit the "any Ollama model" promise

### Content parsing only (ignore native API)
- **Pros:** Single code path, works with all models
- **Cons:** Ignores structured data when available, regex parsing is fragile,
  harder to validate
- **Rejected because:** When native tool calls are available, they're more
  reliable than regex extraction

### Require a specific model
- **Pros:** Simplifies parsing, can optimize for one model's behavior
- **Cons:** Vendor lock-in to a specific model, defeats the purpose of local
  flexibility
- **Rejected because:** Contradicts the goal of working with any Ollama model

## Consequences

### Positive
- **Broad model compatibility**: Works with Qwen, Llama, CodeLlama, Mistral,
  DeepSeek, Phi, and more
- **Graceful degradation**: If native calling fails, content parsing often
  recovers the tool call
- **No duplicate execution**: Deduplication prevents tools from running twice when
  models emit both formats

### Trade-offs Accepted
- **Parser complexity**: `_extract_tool_calls()` is one of the most complex
  methods in the engine, with multiple regex patterns and JSON parsing paths
- **Silent failures possible**: If a model emits malformed JSON in a code fence,
  the tool call is silently skipped rather than raising an error
- **Testing burden**: Must test all three JSON formats x two parsing paths (native
  + content) = six combinations plus edge cases

# ADR-005: Context Windowing Over Summarization

**Status:** Accepted
**Date:** 2025-01-22
**Deciders:** Core team

## Context

Local LLMs have limited context windows (typically 4K-32K tokens, with some
models supporting 128K). A multi-turn agent conversation with tool results can
easily exceed these limits — a single `grep` result might be 5K characters, and a
10-turn conversation with file reads can reach 50K+ characters.

When context is exceeded, the model either truncates silently (losing information)
or returns an error. The system needs a strategy to keep conversations within
bounds.

## Decision

**Use a sliding-window approach: keep the system message pinned and drop the
oldest non-system messages when either limit is exceeded.**

Limits:
- **Max messages**: 200
- **Max total characters**: 100,000

The windowing algorithm:
1. Always preserve the system message (index 0)
2. When limits are exceeded, remove the oldest non-system message
3. Repeat until within bounds

## Alternatives Considered

### Summarization (compress old messages with LLM)
- **Pros:** Retains semantic meaning of old context, more information density
- **Cons:** Requires an extra LLM call per compression (1-10s latency), summary
  quality varies with model size, risk of losing critical details
- **Rejected because:** Adds significant latency and complexity; local 7B models
  produce mediocre summaries that lose tool result details

### Token counting with tiktoken
- **Pros:** Accurate token-level windowing matched to model's actual context limit
- **Cons:** Requires `tiktoken` dependency (violates ADR-002), different models
  use different tokenizers, Ollama doesn't expose tokenizer info
- **Rejected because:** Character-based approximation (1 token ≈ 4 chars) is
  sufficient; exact counting adds dependency for marginal benefit

### RAG over conversation history
- **Pros:** Semantic retrieval of relevant past context, scales to unlimited
  history
- **Cons:** Requires an embedding model, vector store, and retrieval pipeline;
  massive complexity increase
- **Rejected because:** Overkill for a terminal coding agent; can be explored if
  CodeAgent evolves into a longer-session tool

### Hard error on context overflow
- **Pros:** Simplest implementation, no data loss
- **Cons:** Breaks the user experience; user must manually clear context mid-task
- **Rejected because:** Terrible UX; users shouldn't need to manage token budgets

## Consequences

### Positive
- **Zero additional latency**: No LLM calls for compression
- **Predictable behavior**: Oldest messages drop first; user can reason about
  what's still in context
- **Zero dependencies**: Simple Python list operations
- **Graceful degradation**: Agent keeps working as conversations grow long; old
  context fades naturally

### Trade-offs Accepted
- **Information loss**: Old tool results and conversation turns are permanently
  dropped; the agent may "forget" earlier parts of a long session
- **No semantic awareness**: The algorithm doesn't know which old messages are
  more important — a critical file read from turn 2 is dropped before a trivial
  greeting from turn 3 if turn 2 is older
- **Character-based approximation**: The 100K character limit is a rough proxy
  for token limits; some models may still overflow if their tokenizer is less
  efficient than the ~4 chars/token assumption

# ADR-001: Local-Only Ollama Backend

**Status:** Accepted
**Date:** 2025-01-15
**Deciders:** Core team

## Context

CodeAgent needs an LLM backend to power its coding assistant capabilities. The
market offers several options: cloud APIs (OpenAI, Anthropic, Google), local
inference servers (Ollama, llama.cpp, vLLM, LocalAI), and hybrid approaches.

The target audience is developers who want a fully offline coding assistant with
no recurring costs, no data leaving their machine, and no vendor lock-in.

## Decision

**Chosen Ollama as the sole LLM backend**, communicating via its REST API on
`localhost:11434`.

## Alternatives Considered

### Cloud APIs (OpenAI, Anthropic)
- **Pros:** Best model quality, no local hardware requirements, streaming support
- **Cons:** Requires API keys, recurring costs, sends code to third parties,
  internet dependency
- **Rejected because:** Violates the core "offline, no API keys" principle

### llama.cpp directly
- **Pros:** Maximum control, lowest overhead, no server dependency
- **Cons:** Requires compiling C++ per platform, manual model management, no
  standard tool-calling API
- **Rejected because:** Dramatically increases setup complexity for end users

### vLLM / Text Generation Inference
- **Pros:** Production-grade throughput, batching, PagedAttention
- **Cons:** Heavy dependencies (PyTorch), GPU-only, complex setup, overkill for
  single-user use
- **Rejected because:** Too heavyweight for a developer tool; Ollama wraps
  llama.cpp with a simpler interface

### Multi-provider abstraction (LiteLLM, LangChain)
- **Pros:** Supports many backends, easy switching
- **Cons:** Adds large dependency trees, abstractions leak, version conflicts
- **Rejected because:** Violates zero-dependency goal; can be added later if needed

## Consequences

### Positive
- **Zero API keys**: Setup is `ollama pull model && codeagent` — no accounts, no
  billing, no tokens
- **Full privacy**: All data stays on the machine; safe for proprietary codebases
- **Model flexibility**: Any GGUF model works — swap between Qwen, CodeLlama,
  DeepSeek, Mistral by changing one config value
- **Simple integration**: Ollama's REST API is clean and well-documented; our
  client is ~150 lines of stdlib Python

### Trade-offs Accepted
- **Model quality ceiling**: Local 7B-34B models are less capable than
  GPT-4/Claude for complex multi-step reasoning
- **Hardware dependency**: Requires a machine with sufficient RAM/VRAM (minimum
  6GB for the default 7B model)
- **Single provider**: No fallback if Ollama has bugs or drops features; mitigated
  by Ollama being open-source and actively maintained
- **No streaming yet**: Current implementation reads full responses; streaming
  would improve perceived latency significantly

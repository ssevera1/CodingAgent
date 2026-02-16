# ADR-002: Zero External Dependencies

**Status:** Accepted
**Date:** 2025-01-15
**Deciders:** Core team

## Context

Python projects typically rely on third-party packages for HTTP clients
(`requests`, `httpx`), configuration (`pydantic`, `dynaconf`), CLI parsing
(`click`, `typer`), and formatting (`rich`, `colorama`). Each dependency adds
install complexity, version conflicts, supply chain risk, and maintenance burden.

CodeAgent targets developers who may have constrained environments: air-gapped
networks, corporate machines with restricted pip access, or minimal Docker images.

## Decision

**Use only Python standard library modules.** The entire codebase — HTTP client,
JSON handling, file I/O, subprocess management, terminal formatting, path
manipulation — is built on `urllib`, `json`, `pathlib`, `subprocess`, `dataclasses`,
`re`, `threading`, and other stdlib modules.

## Alternatives Considered

### requests + rich + click
- **Pros:** Best-in-class DX for HTTP, terminal output, and CLI parsing
- **Cons:** 3 packages + transitive dependencies (~15 packages total), version
  pinning needed, breaks in air-gapped environments
- **Rejected because:** Convenience doesn't justify the install fragility for an
  offline-first tool

### httpx + pydantic
- **Pros:** Modern async HTTP, type-safe config with validation
- **Cons:** Heavy dependency tree (httpx pulls in httpcore, anyio, sniffio;
  pydantic pulls in typing-extensions)
- **Rejected because:** Overkill for synchronous localhost HTTP calls and simple
  dataclass config

### Vendoring key libraries
- **Pros:** Zero pip install, but get library features
- **Cons:** Maintenance burden to keep vendored code updated, license compliance
  complexity, bloats repository
- **Rejected because:** The stdlib alternatives work well enough; vendoring adds
  complexity without proportional benefit

## Consequences

### Positive
- **`pip install -e .` always works**: No dependency resolution, no conflicts, no
  network needed during install
- **Tiny attack surface**: No third-party code in the supply chain
- **Portable**: Works on any Python 3.10+ installation, including minimal Docker
  images and corporate-locked machines
- **Fast installs**: Install is essentially just copying files

### Trade-offs Accepted
- **More code to maintain**: The HTTP client (`llm.py`) manually handles
  connection pooling, timeouts, and error parsing that `requests` provides for free
- **Rougher terminal output**: ANSI escape codes work but lack the polish of
  `rich` (no automatic terminal width detection, no markdown rendering)
- **No input validation**: Config uses plain dataclasses instead of pydantic;
  invalid config values fail at runtime rather than at load time
- **No async**: `urllib` is synchronous; switching to async later would require
  significant refactoring or adding `aiohttp`

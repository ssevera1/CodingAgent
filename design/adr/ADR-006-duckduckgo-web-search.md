# ADR-006: DuckDuckGo for Web Search

**Status:** Accepted
**Date:** 2025-01-25
**Deciders:** Core team

## Context

CodeAgent needs web search to look up documentation, error messages, and API
references. This is an optional but valuable capability for a coding agent. The
search integration must align with the project's principles: no API keys, no
accounts, and minimal external coupling.

## Decision

**Use DuckDuckGo's HTML endpoint (`https://html.duckduckgo.com/html/`) with
HTML scraping to extract search results.** No API key required, no account needed.

The implementation:
1. POST a search query to DuckDuckGo's HTML endpoint
2. Parse the returned HTML to extract result titles, URLs, and snippets
3. Return structured results to the LLM as tool output

Web features are disabled entirely with the `--no-web` flag.

## Alternatives Considered

### Google Custom Search API
- **Pros:** Best result quality, well-documented API, structured JSON responses
- **Cons:** Requires API key, 100 queries/day free tier, then $5/1000 queries
- **Rejected because:** API key requirement violates the zero-auth principle

### Bing Web Search API
- **Pros:** Good quality, Microsoft-backed
- **Cons:** Requires Azure account and API key, complex pricing tiers
- **Rejected because:** Same API key issue as Google

### SearXNG (self-hosted meta-search)
- **Pros:** Privacy-respecting, no API key, aggregates multiple engines
- **Cons:** Requires running another server, complex setup, not installed by
  default anywhere
- **Rejected because:** Adding another server dependency contradicts the
  "just run Ollama and go" setup experience

### Brave Search API
- **Pros:** Privacy-focused, free tier of 2000 queries/month
- **Cons:** Still requires API key registration
- **Rejected because:** API key requirement

### No web search at all
- **Pros:** Simplest, fully offline
- **Cons:** Limits the agent's ability to look up documentation and error solutions
- **Rejected because:** Web search is too valuable for a coding agent; made it
  optional instead with `--no-web`

## Consequences

### Positive
- **Zero setup**: Works immediately without any accounts or configuration
- **Privacy-respecting**: DuckDuckGo doesn't track searches
- **Graceful degradation**: If DuckDuckGo is unreachable, the tool returns an
  error and the agent continues without web results
- **Fully optional**: `--no-web` disables all web features for air-gapped use

### Trade-offs Accepted
- **Fragile scraping**: HTML parsing depends on DuckDuckGo's page structure;
  layout changes could silently break result extraction
- **Lower result quality**: DuckDuckGo's results are generally less relevant than
  Google's for technical queries
- **Rate limiting risk**: Heavy usage could trigger DuckDuckGo's anti-bot
  protections with no fallback
- **No structured API**: HTML scraping is inherently less reliable than a proper
  JSON API; edge cases in HTML may produce incomplete results

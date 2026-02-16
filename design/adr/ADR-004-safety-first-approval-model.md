# ADR-004: Safety-First Tool Approval Model

**Status:** Accepted
**Date:** 2025-01-20
**Deciders:** Core team

## Context

CodeAgent's tools can read files, write files, execute arbitrary shell commands,
and run git operations. An LLM hallucination or misinterpreted prompt could lead
to:

- Accidental deletion of files (`rm -rf`)
- Committing secrets to version control
- Running destructive database commands
- Modifying system files outside the project

The agent needs a permission model that balances safety with usability — requiring
confirmation for every tool call would make the agent unusable, but auto-approving
everything would be dangerous.

## Decision

**Implement a three-tier approval model:**

| Tier | Tools | Default | Rationale |
|------|-------|---------|-----------|
| **Auto-approve** | `read_file`, `list_directory`, `grep`, `glob`, `web_search`, `web_fetch`, `scan_agents` | Always on | Read-only operations cannot cause harm |
| **Conditional** | `git` (read-only subcommands: `status`, `diff`, `log`, `show`, `branch`, `remote`, `tag`) | Auto-approve | These git commands only read state |
| **Require confirmation** | `write_file`, `edit_file`, `bash`, `git` (write operations) | Prompt user | These can modify state irreversibly |

Additionally, a **safety validation layer** applies to all commands:
- **Blocked**: Always rejected (`rm -rf /`, fork bombs, `mkfs`)
- **Warned**: Shown with extra warning, requires explicit confirmation
  (`git push --force`, `drop database`)

All tiers are configurable via `auto_approve_reads`, `auto_approve_writes`,
`auto_approve_bash` in the agent config.

## Alternatives Considered

### Approve everything (trust the LLM)
- **Pros:** Fastest workflow, zero friction
- **Cons:** One hallucination away from `rm -rf .` or committing `.env`
- **Rejected because:** Unacceptable risk; local LLMs hallucinate more than
  cloud models

### Approve nothing (confirm every tool call)
- **Pros:** Maximum safety
- **Cons:** A 5-tool task requires 5 confirmations; destroys the "agent" experience
- **Rejected because:** Users would disable it immediately, defeating the purpose

### Sandbox execution (Docker / chroot)
- **Pros:** True isolation, even destructive commands are safe
- **Cons:** Requires Docker installed, adds startup latency, complicates file
  access, doesn't work well on Windows
- **Rejected because:** Adds a heavy dependency; contradicts "zero dependencies"
  goal. Can be explored as a future enhancement.

### LLM-based safety classifier
- **Pros:** Contextual understanding of intent
- **Cons:** Adds latency (another LLM call), unreliable (LLMs can be tricked),
  circular dependency (using LLM to validate LLM output)
- **Rejected because:** Too slow and not reliable enough for a safety-critical
  gate

## Consequences

### Positive
- **Safe defaults**: A new user can't accidentally cause damage without
  explicitly confirming
- **Low friction for reads**: The most common agent loop (read → search → read →
  respond) requires zero confirmations
- **Configurable**: Power users can enable `auto_approve_writes` for trusted
  workflows
- **Defense in depth**: Even with auto-approve enabled, the safety layer still
  blocks catastrophic commands

### Trade-offs Accepted
- **Interrupted flow**: Multi-step write operations require multiple
  confirmations, breaking the "autonomous agent" feel
- **False sense of security**: A sophisticated prompt injection attack could craft
  a command that passes safety checks but is still harmful
- **Maintenance burden**: The blocked/warned command lists must be kept up to date
  as new dangerous patterns emerge

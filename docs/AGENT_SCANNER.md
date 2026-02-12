# Agent Scanner

The Agent Scanner is a built-in feature that lets you discover and compare the latest open-source coding agents from across the internet — all from within CodeAgent.

## Overview

The scanner does two things:
1. **Checks known agents** — Queries GitHub API for real-time stats on 13+ well-known coding agents
2. **Discovers new agents** — Searches GitHub for new/emerging coding agents matching your criteria

## Usage

### From the CLI
```
/scan              # Scan all categories
/scan cli          # Terminal-based agents only
/scan ide          # Editor/IDE plugins only
/scan web          # Browser-based agents only
/scan framework    # Agent frameworks only
```

### From Conversation
```
> What are the best coding agents right now?
> Find me terminal-based coding agents sorted by stars
> Scan for the latest AI coding tools
```

### Programmatic (via tool)
The agent can call `scan_agents` with these parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `category` | string | `"all"` | `cli`, `ide`, `web`, `framework`, `all` |
| `query` | string | `""` | Additional search terms |
| `sort_by` | string | `"stars"` | `stars`, `updated`, `name` |
| `discover_new` | boolean | `true` | Search beyond known agents |

## Tracked Agents

The scanner tracks these well-known coding agents:

### CLI / Terminal Agents
| Agent | Repository | Description |
|-------|------------|-------------|
| Aider | paul-gauthier/aider | AI pair programming in the terminal |
| SWE-agent | SWE-agent/SWE-agent | Autonomous GitHub issue solver |
| Devon | entropy-research/Devon | Open-source AI software engineer |
| GPT-Engineer | gpt-engineer-org/gpt-engineer | Generates codebases from prompts |
| Mentat | AbanteAI/mentat | Terminal AI coding assistant |

### IDE / Editor Agents
| Agent | Repository | Description |
|-------|------------|-------------|
| Cline | cline/cline | Autonomous agent for VS Code |
| Continue | continuedev/continue | Open-source code assistant |
| Roo Code | RooVetGit/Roo-Code | AI coding for VS Code |
| Cursor | getcursor/cursor | AI-powered code editor |
| Tabby | TabbyML/tabby | Self-hosted coding assistant |

### Web / Cloud Agents
| Agent | Repository | Description |
|-------|------------|-------------|
| OpenHands | All-Hands-AI/OpenHands | Platform for coding agents |
| Sweep | sweepai/sweep | AI that turns issues into PRs |
| Bolt | stackblitz/bolt.new | Full-stack web development agent |

## Output Format

Each scan result includes:

```
  1. Aider
     URL:         https://github.com/paul-gauthier/aider
     Stars:       25432
     Language:    Python
     Category:    cli
     Updated:     2026-02-10
     License:     Apache-2.0
     Description: AI pair programming in your terminal
```

## How It Works

1. **GitHub API** — Makes unauthenticated API calls to `api.github.com`
   - Rate limit: 60 requests/hour without a token
   - Fetches: stars, language, license, last update, description

2. **GitHub Search** — When `discover_new=true`, searches for repositories matching coding agent keywords

3. **Category Inference** — New discoveries are auto-categorized based on description keywords (cli, terminal, vscode, ide, web, browser, framework, sdk)

## Limitations

- **Rate limiting**: GitHub allows 60 API calls/hour without authentication. A full scan uses ~15 calls.
- **No authentication**: Does not use GitHub tokens. For higher rate limits, you could modify the scanner to include a `GITHUB_TOKEN` header.
- **Network required**: This feature requires internet access. It's disabled in `--no-web` mode.
- **Discovery accuracy**: Auto-discovered agents may include non-agent repositories that match keywords.

## Extending the Scanner

To add a new known agent, edit `agent/tools/agent_scanner.py` and add an entry to `KNOWN_AGENTS`:

```python
{
    "name": "New Agent",
    "repo": "owner/repo-name",
    "category": "cli",  # cli, ide, web, or framework
    "description": "What it does",
},
```

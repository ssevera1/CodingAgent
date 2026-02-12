# Tools Reference

CodeAgent comes with 11 built-in tools organized into five categories.

---

## File Operations

### `read_file`
Read the contents of a file with line numbers.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | string | Yes | Path to the file |
| `offset` | integer | No | Start line (1-based, default: 1) |
| `limit` | integer | No | Max lines to read (default: 2000) |

**Examples:**
- Read entire file: `read_file("src/main.py")`
- Read lines 50-100: `read_file("src/main.py", offset=50, limit=50)`

**Auto-approved:** Yes (configurable)

---

### `write_file`
Write content to a file. Creates parent directories if needed.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | string | Yes | Path to the file |
| `content` | string | Yes | Content to write |

**Behavior:**
- Overwrites existing files
- Creates parent directories automatically
- Uses UTF-8 encoding with Unix line endings

**Auto-approved:** No (configurable)

---

### `edit_file`
Edit a file by finding and replacing an exact string.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | string | Yes | Path to the file |
| `old_string` | string | Yes | Exact text to find |
| `new_string` | string | Yes | Replacement text |
| `replace_all` | boolean | No | Replace all occurrences (default: false) |

**Behavior:**
- Fails if `old_string` is not found
- Fails if `old_string` matches multiple times (unless `replace_all=true`)
- Preserves file encoding

**Auto-approved:** No (configurable)

---

### `list_directory`
List files and directories in a path.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | No | Directory to list (default: working dir) |
| `recursive` | boolean | No | List recursively (default: false) |

**Auto-approved:** Yes

---

## Code Search

### `grep`
Search file contents using regex patterns (like ripgrep).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pattern` | string | Yes | Regex pattern |
| `path` | string | No | Search directory (default: working dir) |
| `glob_filter` | string | No | File filter (e.g., `*.py`) |
| `case_insensitive` | boolean | No | Case insensitive (default: false) |
| `context_lines` | integer | No | Context lines around matches |
| `max_results` | integer | No | Max results (default: 50) |

**Skips automatically:** `.git`, `node_modules`, `__pycache__`, binary files

**Examples:**
- Find function definitions: `grep("def handle_", glob_filter="*.py")`
- Find imports: `grep("import requests", case_insensitive=true)`
- With context: `grep("class User", context_lines=5)`

**Auto-approved:** Yes

---

### `glob`
Find files matching glob patterns.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pattern` | string | Yes | Glob pattern (e.g., `**/*.py`) |
| `path` | string | No | Base directory (default: working dir) |
| `max_results` | integer | No | Max results (default: 100) |

**Examples:**
- All Python files: `glob("**/*.py")`
- Test files: `glob("**/test_*.py")`
- Config files: `glob("*.{json,yaml,toml}")`

**Auto-approved:** Yes

---

## Shell Execution

### `bash`
Execute shell commands.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `command` | string | Yes | Command to execute |
| `timeout` | integer | No | Timeout in seconds (default: 120, max: 600) |

**Safety features:**
- Blocks dangerous commands (rm -rf /, fork bombs, etc.)
- Warns about destructive commands (rm -rf, git push --force)
- Truncates output over 30,000 characters
- Runs in the working directory

**Auto-approved:** No (configurable)

---

## Git Operations

### `git`
Execute git commands with safety checks.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `command` | string | Yes | Git subcommand and args |

**Safety features:**
- Blocks force-push to main/master
- Warns about destructive operations (reset --hard, clean -f)
- Blocks interactive commands (-i flag)
- Disables terminal prompts (GIT_TERMINAL_PROMPT=0)

**Read-only commands (auto-approved):** status, diff, log, show, branch, remote, tag, stash

**Examples:**
- `git("status")`
- `git("diff --staged")`
- `git("log --oneline -10")`
- `git("add src/main.py")`
- `git("commit -m 'Fix bug'")`

---

## Web Operations

### `web_search`
Search the web using DuckDuckGo (no API key needed).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `max_results` | integer | No | Max results (default: 5) |

**Auto-approved:** Yes (read-only)

---

### `web_fetch`
Fetch and extract readable text from a URL.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | Yes | URL to fetch |
| `max_length` | integer | No | Max content chars (default: 10000) |

**Features:**
- Converts HTML to readable text
- Removes scripts, styles, and navigation
- Handles redirects
- Truncates long content

**Auto-approved:** Yes (read-only)

---

### `scan_agents`
Scan the internet for the latest open-source coding agents.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | string | No | Filter: `cli`, `ide`, `web`, `framework`, `all` |
| `query` | string | No | Additional search query |
| `sort_by` | string | No | Sort: `stars`, `updated`, `name` |
| `discover_new` | boolean | No | Search for unknown agents (default: true) |

**Auto-approved:** Yes (read-only)

See [AGENT_SCANNER.md](AGENT_SCANNER.md) for detailed documentation.

---

## Tool Approval Matrix

| Tool | Default | Configurable |
|------|---------|-------------|
| `read_file` | Auto-approve | `auto_approve_reads` |
| `write_file` | Confirm | `auto_approve_writes` |
| `edit_file` | Confirm | `auto_approve_writes` |
| `list_directory` | Auto-approve | `auto_approve_reads` |
| `grep` | Auto-approve | `auto_approve_searches` |
| `glob` | Auto-approve | `auto_approve_searches` |
| `bash` | Confirm | `auto_approve_bash` |
| `git` (read) | Auto-approve | — |
| `git` (write) | Confirm | — |
| `web_search` | Auto-approve | — |
| `web_fetch` | Auto-approve | — |
| `scan_agents` | Auto-approve | — |

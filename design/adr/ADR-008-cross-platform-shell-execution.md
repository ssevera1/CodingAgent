# ADR-008: Cross-Platform Shell Execution

**Status:** Accepted
**Date:** 2025-01-28
**Deciders:** Core team

## Context

CodeAgent's `bash` tool executes shell commands requested by the LLM. The agent
must run on Windows, Linux, and macOS, each with different default shells:

- **Linux/macOS**: `/bin/bash` or `/bin/sh`
- **Windows**: `cmd.exe` (default) or PowerShell

Shell syntax differs significantly between platforms: path separators, environment
variable expansion, command chaining, piping, and available utilities.

## Decision

**Use platform-conditional execution:**

```python
if is_windows:
    subprocess.run(command, shell=True, ...)  # Delegates to cmd.exe
else:
    subprocess.run(["/bin/bash", "-c", command], ...)  # Explicit bash
```

Key design choices:
- On Unix, explicitly invoke `/bin/bash` rather than relying on `shell=True`
  (which may use `/bin/sh` and miss bash features)
- On Windows, use `shell=True` which delegates to `cmd.exe`
- Apply the same safety validation layer across all platforms
- Set a configurable timeout (default 120s, max 600s) to prevent runaway commands
- Truncate output at 30K characters to prevent memory exhaustion

## Alternatives Considered

### Bash-only (require WSL on Windows)
- **Pros:** Single shell syntax, consistent behavior across platforms
- **Cons:** WSL not installed by default, adds setup step, confuses file paths
  (WSL vs Windows paths)
- **Rejected because:** Many Windows developers don't use WSL; requiring it
  contradicts the easy-setup goal

### PowerShell everywhere
- **Pros:** Cross-platform (PowerShell Core runs on Linux/macOS), modern scripting
- **Cons:** Not installed by default on most Linux distributions, different syntax
  from what LLMs typically generate, slower startup
- **Rejected because:** LLMs predominantly generate bash-style commands;
  PowerShell would require prompt engineering to avoid syntax errors

### Abstract command layer (no raw shell access)
- **Pros:** Maximum safety, platform-independent, predictable behavior
- **Cons:** Severely limits what the agent can do; can't run build tools, test
  suites, or language-specific commands
- **Rejected because:** Shell access is essential for a coding agent; the safety
  layer provides sufficient protection

### Docker-based execution
- **Pros:** Consistent Linux environment everywhere, isolated from host
- **Cons:** Requires Docker installation, startup latency, file mount complexity,
  networking issues for localhost services
- **Rejected because:** Too heavy for interactive use; can be offered as an
  optional execution mode later

## Consequences

### Positive
- **Works everywhere**: Windows, Linux, and macOS without additional setup
- **LLM-friendly**: Models can generate standard bash commands (most common in
  training data) and they work on Unix; Windows `cmd.exe` handles simpler commands
- **Safety preserved**: The same blocked/warned command lists apply regardless of
  platform
- **Bounded execution**: Timeouts and output truncation prevent resource exhaustion

### Trade-offs Accepted
- **Windows command compatibility**: Complex bash commands (pipes, process
  substitution, bash-specific syntax) may fail on Windows `cmd.exe`. The LLM must
  be aware it's on Windows (communicated via system prompt).
- **Security surface**: `shell=True` on Windows is generally discouraged due to
  command injection risks; mitigated by the safety validation layer running before
  execution
- **No persistent shell state**: Each command runs in a fresh subprocess; `cd`,
  environment variable exports, and shell functions don't persist between calls
- **Platform detection at runtime**: Uses `sys.platform` check; edge cases like
  Cygwin, MSYS2, or Git Bash may behave unexpectedly

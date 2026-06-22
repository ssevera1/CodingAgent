#!/usr/bin/env python3
"""
Proposes and commits one focused, realistic improvement to this codebase.
Opens a PR for human review before merging.
"""

import base64
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

import anthropic

# ── Context builder ──────────────────────────────────────────────────────────

MAX_CONTEXT_CHARS = 20_000
PRIORITY_DIRS = {"src", "tests", "test", "lib", "core", "scripts"}
PRIORITY_EXTS = {".py", ".ts", ".js", ".tsx", ".jsx", ".go", ".rs"}
READABLE_EXTS = PRIORITY_EXTS | {".yaml", ".yml", ".toml", ".sh", ".md", ".json"}
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".pytest_cache", ".mypy_cache", "coverage",
}
SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Pipfile.lock", ".gitignore",
}


def sh(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def tracked_files() -> list[str]:
    out = sh(["git", "ls-files"])
    return [f for f in out.splitlines() if f]


def build_context() -> str:
    files = tracked_files()
    tree = "\n".join(files)
    recent_log = sh(["git", "log", "--oneline", "-15"])

    parts = [
        f"## Repository file tree\n{tree}",
        f"## Recent commits\n{recent_log}",
    ]
    chars = len(tree) + len(recent_log)

    def rank(path: str) -> int:
        p = Path(path)
        if p.name in SKIP_FILES:
            return 99
        if any(part in SKIP_DIRS for part in p.parts):
            return 99
        if p.suffix not in READABLE_EXTS:
            return 99
        if p.parts[0] in PRIORITY_DIRS:
            return 0 if p.suffix in PRIORITY_EXTS else 1
        if p.suffix in PRIORITY_EXTS:
            return 2
        return 3

    for f in sorted(files, key=rank):
        if chars >= MAX_CONTEXT_CHARS:
            break
        p = Path(f)
        if rank(f) == 99:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            if len(content) > 5_000:
                content = content[:5_000] + "\n... (truncated)"
            entry = f"\n## {f}\n```\n{content}\n```"
            parts.append(entry)
            chars += len(entry)
        except OSError:
            pass

    return "\n".join(parts)


# ── Prompt ────────────────────────────────────────────────────────────────────

PROMPT = """\
You are a senior engineer doing a focused improvement pass on a codebase you know well.

{context}

Your task: implement ONE specific, realistic improvement that a thoughtful engineer \
would make after actually running and using this code.

Good candidates:
- An unhandled edge case or error path (None/NaN/empty input, connection failure, \
schema mismatch, race condition)
- A missing test that covers observable, non-trivial behaviour
- A hardcoded value that belongs in config or an env var
- A missing log line at a decision point that would help debug production issues
- A function that can silently return wrong output or swallow an exception
- A retry or timeout that is missing on a network/IO call

Constraints:
- ONE file only: create or modify a single file
- The file must be complete and runnable — no placeholders, no TODO stubs
- No verbose explanatory comments; write as a competent engineer would
- Do NOT touch README.md, *.yml/*.yaml workflow files, or lock files
- Commit message: conventional commits format, imperative mood, ≤72 chars \
(e.g. "fix: handle empty feature store on first run")

Respond with ONLY valid JSON — no markdown fences, no prose outside the object:
{{"file_path":"relative/path/to/file","file_content":"complete file content here",\
"commit_message":"type(scope): description","pr_title":"Short PR title (≤60 chars)",\
"pr_body":"## What\\nOne sentence.\\n\\n## Why\\nOne sentence."}}
"""


# ── Main ──────────────────────────────────────────────────────────────────────

def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def main() -> None:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    print("Building context…")
    context = build_context()
    print(f"Context size: {len(context):,} chars")

    print("Requesting improvement…")
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": PROMPT.format(context=context)}],
    )
    raw = msg.content[0].text.strip()

    # Strip markdown fences if the model wrapped the JSON anyway
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        imp = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"JSON parse error: {exc}\nRaw response:\n{raw[:800]}")
        sys.exit(0)  # Soft exit — skip this run rather than failing the workflow

    file_path = Path(imp["file_path"])
    commit_msg: str = imp["commit_message"]
    pr_title: str = imp["pr_title"]
    pr_body: str = imp["pr_body"]

    print(f"Improvement: {commit_msg}")
    print(f"File:        {file_path}")

    # Safety guard — don't touch workflow or lock files
    blocked = {".yml", ".yaml", ".lock"}
    if file_path.suffix in blocked or file_path.name in SKIP_FILES:
        print(f"Skipping protected file type: {file_path}")
        sys.exit(0)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(imp["file_content"], encoding="utf-8")

    # Git setup
    run(["git", "config", "user.name",  os.environ.get("GIT_AUTHOR_NAME",  "Scott Severance")])
    run(["git", "config", "user.email", os.environ.get("GIT_AUTHOR_EMAIL", "scott@scottseverance.net")])

    branch = f"improve/{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    run(["git", "checkout", "-b", branch])
    run(["git", "add", str(file_path)])
    run(["git", "commit", "-m", commit_msg])
    run(["git", "push", "origin", branch])

    subprocess.run(
        ["gh", "pr", "create",
         "--title", pr_title,
         "--body", pr_body,
         "--base", "main",
         "--head", branch],
        check=True,
        env=os.environ,
    )

    print(f"PR opened: {pr_title}")


if __name__ == "__main__":
    main()

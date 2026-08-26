#!/usr/bin/env python3
"""
Proposes and commits one focused, realistic improvement to this codebase.
Opens a PR for human review before merging.
"""

import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

import anthropic

# ── Context builder ──────────────────────────────────────────────────────────

MAX_CONTEXT_CHARS = 20_000
# Survey previews are truncated, so they can only be used to CHOOSE a file —
# never to rewrite one. The rewrite pass always reads the file in full.
PREVIEW_CHARS = 5_000
# Largest file we will ask for a full rewrite of, bounded by MAX_OUTPUT_TOKENS.
MAX_TARGET_CHARS = 32_000
MAX_OUTPUT_TOKENS = 16_384
# A rewrite that returns less than this fraction of the original is treated as
# accidental deletion, not an improvement.
SHRINK_FLOOR = 0.6
# Skip the run entirely once this many bot PRs are already awaiting review.
MAX_OPEN_PRS = int(os.environ.get("MAX_OPEN_PRS", "5"))
# How many already-closed proposals to recall, so a drained queue does not reset
# the bot's memory of what it has tried.
RECENT_PR_MEMORY = int(os.environ.get("RECENT_PR_MEMORY", "20"))
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


def bot_pr_titles(state: str, limit: int) -> list[str]:
    """Titles of this bot's PRs in the given state, newest first."""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        return []
    out = sh(["gh", "pr", "list", "-R", repo, "--state", state,
              "--limit", str(limit), "--json", "title,headRefName"])
    if not out:
        return []
    try:
        prs = json.loads(out)
    except json.JSONDecodeError:
        return []
    return [p["title"] for p in prs
            if str(p.get("headRefName", "")).startswith("improve/")]


def open_bot_prs() -> list[str]:
    """Currently-open proposals, so the bot neither repeats nor piles up."""
    return bot_pr_titles("open", 100)


def past_bot_prs() -> list[str]:
    """Recently closed/merged proposals.

    Without this the bot forgets every theme it has already tried as soon as the
    review queue is drained, and starts re-proposing them from a clean slate.
    """
    return bot_pr_titles("closed", RECENT_PR_MEMORY)[:RECENT_PR_MEMORY]


def default_branch() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo:
        name = sh(["gh", "api", f"repos/{repo}", "--jq", ".default_branch"])
        if name:
            return name
    ref = sh(["git", "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"])
    if ref:
        return ref.rsplit("/", 1)[-1]
    return "main"


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
            if len(content) > PREVIEW_CHARS:
                content = content[:PREVIEW_CHARS] + "\n... (truncated preview)"
            entry = f"\n## {f}\n```\n{content}\n```"
            parts.append(entry)
            chars += len(entry)
        except OSError:
            pass

    return "\n".join(parts)


# ── Prompt ────────────────────────────────────────────────────────────────────

SELECT_PROMPT = """\
You are a senior engineer choosing where to make ONE focused improvement to a \
codebase you know well.

{context}
{open_prs}
The file previews above may be TRUNCATED — treat them as a map, not as ground \
truth. Do not assume something is missing just because you cannot see it; you \
will be shown the complete file before you write anything.

Pick exactly ONE file to improve. Good candidates:
- An unhandled edge case or error path (None/NaN/empty input, connection failure, \
schema mismatch, race condition)
- A missing test that covers observable, non-trivial behaviour
- A hardcoded value that belongs in config or an env var
- A missing log line at a decision point that would help debug production issues
- A function that can silently return wrong output or swallow an exception
- A retry or timeout that is missing on a network/IO call

Constraints:
- Do NOT pick anything already listed as an open pull request above; choose a \
genuinely different area of the codebase
- Do NOT pick README.md, *.yml/*.yaml workflow files, or lock files

Do not think out loud, explain your reasoning, or walk through your analysis of \
the codebase — a caller is parsing your response programmatically and any text \
outside the object below will break it. Respond with ONLY the JSON object, \
starting with `{{` and ending with `}}` — no markdown fences, no preamble, no \
commentary before or after it:
{{"file_path":"relative/path/to/file","plan":"one sentence naming the concrete change"}}
"""

WRITE_PROMPT = """\
You are a senior engineer making ONE focused improvement to this file.

## Intended change
{plan}

## Complete current contents of {path}
This is the ENTIRE file — nothing is truncated. Preserve every existing behaviour, \
export, and code path that is not part of the intended change.
```
{current}
```

Constraints:
- Apply only the intended change; do not refactor or reorganise anything else
- Return the complete file, runnable as-is — no placeholders, no TODO stubs, \
no "... rest of file unchanged" markers
- If the change is already implemented in the file above, say so by returning the \
file unmodified rather than inventing a different change
- No verbose explanatory comments; write as a competent engineer would
- Commit message: conventional commits format, imperative mood, ≤72 chars \
(e.g. "fix: handle empty feature store on first run")

Do not think out loud, explain your reasoning, or walk through your analysis — a \
caller is parsing your response programmatically and any text outside the object \
below will break it. Respond with ONLY the JSON object, starting with `{{` and \
ending with `}}` — no markdown fences, no preamble, no commentary before or after it:
{{"file_content":"complete file content here",\
"commit_message":"type(scope): description","pr_title":"Short PR title (≤60 chars)",\
"pr_body":"## What\\nOne sentence.\\n\\n## Why\\nOne sentence."}}
"""


# ── Main ──────────────────────────────────────────────────────────────────────

def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def ask_json(client, prompt: str, max_tokens: int) -> dict | None:
    """One model call returning parsed JSON, or None if the run should be skipped."""
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )

    # A response cut off at the token limit yields a half-written file; never act on it.
    if msg.stop_reason == "max_tokens":
        print(f"Response hit the {max_tokens} token limit; skipping run.")
        return None

    raw = msg.content[0].text.strip()
    # Strip markdown fences if the model wrapped the JSON anyway
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Despite the instruction, the model sometimes reasons in prose before (or
    # instead of) emitting bare JSON. Rather than discard a usable answer,
    # look for the first balanced {...} object anywhere in the response.
    start = raw.find("{")
    if start != -1:
        depth = 0
        for i, ch in enumerate(raw[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(raw[start:i + 1])
                    except json.JSONDecodeError:
                        break

    print(f"JSON parse error; no valid JSON object found.\nRaw response:\n{raw[:2000]}")
    return None


def safe_target(raw_path: str, repo_root: Path) -> Path | None:
    """Resolve a model-supplied path inside repo_root, or None if it is off limits."""
    candidate = (repo_root / raw_path).resolve()

    # Reject path traversal outside the repo.
    if not str(candidate).startswith(str(repo_root) + os.sep):
        print(f"Rejecting path outside repo root: {candidate}")
        return None

    # Reject writes into dotfile directories (.git, .github, .githooks, etc.).
    if any(p.startswith(".") for p in candidate.relative_to(repo_root).parts):
        print(f"Rejecting dotfile/dot-directory path: {candidate}")
        return None

    # Reject protected file types and names.
    blocked_suffixes = {".yml", ".yaml", ".lock"}
    blocked_names = {n.lower() for n in SKIP_FILES} | {"readme.md"}
    if (candidate.suffix.lower() in blocked_suffixes
            or candidate.name.lower() in blocked_names):
        print(f"Skipping protected file: {candidate}")
        return None

    return candidate


def main() -> None:
    # Check the review queue before spending an API call on a run we'd discard.
    pr_titles = open_bot_prs()
    if len(pr_titles) >= MAX_OPEN_PRS:
        print(f"{len(pr_titles)} improvement PRs already open "
              f"(limit {MAX_OPEN_PRS}); skipping run.")
        sys.exit(0)

    sections = []
    if pr_titles:
        sections.append("\n## Already proposed and awaiting review — do NOT repeat these\n"
                        + "\n".join(f"- {t}" for t in pr_titles))
    past_titles = past_bot_prs()
    if past_titles:
        sections.append("\n## Previously proposed and already closed — do NOT repeat these\n"
                        + "\n".join(f"- {t}" for t in past_titles))
    open_prs = ("\n".join(sections) + "\n") if sections else ""
    print(f"{len(pr_titles)} open and {len(past_titles)} past PR(s) fed back into context")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Resolve the repo root and constrain all writes to within it.
    root_out = sh(["git", "rev-parse", "--show-toplevel"])
    if not root_out:
        print("Cannot determine repo root; aborting.")
        sys.exit(0)
    repo_root = Path(root_out).resolve()

    print("Building context…")
    context = build_context()
    print(f"Context size: {len(context):,} chars")

    # Pass 1 — choose a target from truncated previews. Cheap, and wrong answers
    # are caught by safe_target before the expensive call.
    print("Selecting a target file…")
    choice = ask_json(client, SELECT_PROMPT.format(context=context, open_prs=open_prs), 1024)
    if not choice or "file_path" not in choice:
        sys.exit(0)

    file_path = safe_target(str(choice["file_path"]), repo_root)
    if file_path is None:
        sys.exit(0)

    original = ""
    if file_path.is_file():
        original = file_path.read_text(encoding="utf-8", errors="ignore")
        if len(original) > MAX_TARGET_CHARS:
            print(f"{file_path} is {len(original):,} chars (limit {MAX_TARGET_CHARS:,}); "
                  "too large to rewrite in one response. Skipping run.")
            sys.exit(0)

    rel = file_path.relative_to(repo_root).as_posix()
    plan = str(choice.get("plan", "")).strip()
    print(f"Target: {rel} ({len(original):,} chars)")
    print(f"Plan:   {plan}")

    # Pass 2 — rewrite with the complete file in context, never a preview.
    print("Requesting improvement…")
    imp = ask_json(
        client,
        WRITE_PROMPT.format(plan=plan, path=rel,
                            current=original or "(new file — does not exist yet)"),
        MAX_OUTPUT_TOKENS,
    )
    if not imp:
        sys.exit(0)

    missing = [k for k in ("file_content", "commit_message", "pr_title", "pr_body")
               if k not in imp]
    if missing:
        print(f"Response missing keys {missing}; skipping run.")
        sys.exit(0)

    new_content: str = imp["file_content"]
    commit_msg: str = imp["commit_message"]
    pr_title: str = imp["pr_title"]
    pr_body: str = imp["pr_body"]

    if new_content == original:
        print("Rewrite is identical to the current file; nothing to propose.")
        sys.exit(0)

    # Last line of defence: a rewrite that loses most of the file is deletion,
    # not improvement, however plausible the accompanying commit message reads.
    if original and len(new_content) < len(original) * SHRINK_FLOOR:
        lost = 100 * (1 - len(new_content) / len(original))
        print(f"Rewrite drops {lost:.0f}% of {rel} "
              f"({len(original):,} -> {len(new_content):,} chars); "
              "treating as data loss and skipping.")
        sys.exit(0)

    print(f"Improvement: {commit_msg}")
    print(f"File:        {file_path}")

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(new_content, encoding="utf-8")

    # Git setup
    run(["git", "config", "user.name",  os.environ.get("GIT_AUTHOR_NAME",  "Scott Severance")])
    run(["git", "config", "user.email", os.environ.get("GIT_AUTHOR_EMAIL", "scott@scottseverance.net")])

    base = default_branch()
    print(f"Base branch: {base}")

    branch = f"improve/{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    run(["git", "checkout", "-b", branch])
    run(["git", "add", "--", str(file_path)])
    # Disable hooks so a planted pre-commit hook cannot execute.
    run(["git", "-c", "core.hooksPath=/dev/null", "commit", "-m", commit_msg])
    run(["git", "push", "origin", branch])

    subprocess.run(
        ["gh", "pr", "create",
         "--title", pr_title,
         "--body", pr_body,
         "--base", base,
         "--head", branch],
        check=True,
        env=os.environ,
    )

    print(f"PR opened: {pr_title}")


if __name__ == "__main__":
    main()

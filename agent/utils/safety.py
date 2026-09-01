"""Safety checks and validation utilities."""

import os
import re
from pathlib import Path
from typing import Optional


# File patterns that should never be committed or exposed
SENSITIVE_PATTERNS = [
    r"\.env$",
    r"\.env\.\w+$",
    r"credentials\.json$",
    r"secrets\.ya?ml$",
    r"\.pem$",
    r"\.key$",
    r"id_rsa",
    r"id_ed25519",
    r"\.p12$",
    r"\.pfx$",
    r"token\.json$",
    r"service[_-]?account.*\.json$",
]

# Content patterns that suggest secrets
SECRET_CONTENT_PATTERNS = [
    r"(?:api[_-]?key|apikey)\s*[=:]\s*['\"][A-Za-z0-9+/=_-]{20,}",
    r"(?:secret|password|passwd|pwd)\s*[=:]\s*['\"][^\s'\"]{8,}",
    r"(?:access[_-]?token|auth[_-]?token)\s*[=:]\s*['\"][A-Za-z0-9+/=_-]{20,}",
    r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----",
    r"sk-[A-Za-z0-9]{20,}",  # OpenAI-style API keys
    r"ghp_[A-Za-z0-9]{36}",  # GitHub personal access tokens
    r"ghs_[A-Za-z0-9]{36}",  # GitHub server tokens
]


def is_sensitive_file(filepath: str) -> bool:
    """Check if a file path matches sensitive patterns."""
    name = Path(filepath).name.lower()
    return any(re.search(p, name, re.IGNORECASE) for p in SENSITIVE_PATTERNS)


def contains_secrets(content: str) -> list[str]:
    """Check if content contains potential secrets. Returns list of findings."""
    findings = []
    for pattern in SECRET_CONTENT_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            # Don't include the actual secret in the finding
            findings.append(f"Potential secret detected (pattern: {pattern[:30]}...)")
    return findings


def validate_path(filepath: str, working_dir: str) -> Optional[str]:
    """Validate a file path for safety.

    Returns error message if unsafe, None if safe.
    """
    try:
        resolved = Path(filepath).resolve()
        work_resolved = Path(working_dir).resolve()

        # Check for path traversal
        try:
            resolved.relative_to(work_resolved)
        except ValueError:
            # Allow absolute paths but warn about system directories
            system_dirs = ["/etc", "/usr", "/bin", "/sbin", "/var",
                          "C:\\Windows", "C:\\Program Files"]
            for sys_dir in system_dirs:
                if str(resolved).startswith(sys_dir):
                    return f"Warning: modifying system path {resolved}"

        return None
    except Exception as e:
        return f"Invalid path: {e}"


def sanitize_command(command: str) -> tuple[bool, str]:
    """Check if a shell command is safe to run.

    Returns (is_safe, reason) tuple.
    """
    dangerous_patterns = [
        (r"rm\s+-rf\s+/(?:\s|$)", "Deleting root filesystem"),
        (r":\(\)\{.*\|.*&\}", "Fork bomb detected"),
        (r"mkfs\.", "Filesystem formatting"),
        (r"dd\s+if=.*of=/dev/", "Writing to raw device"),
        (r"chmod\s+-R\s+777\s+/", "Changing permissions on root"),
        (r">\s*/dev/sd[a-z]", "Writing to raw disk"),
        (r"curl.*\|\s*(?:bash|sh)", "Piping URL to shell"),
        (r"wget.*\|\s*(?:bash|sh)", "Piping download to shell"),
    ]

    for pattern, reason in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return False, reason

    return True, ""


def check_file_size(filepath: str, max_mb: int = 50) -> Optional[str]:
    """Check if file size is within limits."""
    try:
        size = os.path.getsize(filepath)
        max_bytes = max_mb * 1024 * 1024
        if size > max_bytes:
            return f"File is too large ({size / 1024 / 1024:.1f}MB, max {max_mb}MB)"
        return None
    except OSError:
        return None  # File doesn't exist yet, that's fine

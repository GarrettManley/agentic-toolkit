"""Lightweight secret detector for staged content / evidence files.

Patterns based on common credential formats. NOT a full gitleaks replacement,
but covers the highest-frequency leaks.
"""
from __future__ import annotations

import re
from typing import NamedTuple


class SecretMatch(NamedTuple):
    pattern_name: str
    line_number: int
    snippet: str  # First 30 chars, truncated


# Patterns: (name, regex, redaction_advice)
PATTERNS: list[tuple[str, re.Pattern, str]] = [
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "rotate immediately and redact"),
    ("aws-secret-key", re.compile(r"(?i)aws_?secret_?access_?key['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?"), "rotate and redact"),
    ("github-pat-classic", re.compile(r"\bghp_[A-Za-z0-9]{36,}\b"), "revoke at https://github.com/settings/tokens and redact"),
    ("github-pat-fine", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{82,}\b"), "revoke and redact"),
    ("gitlab-pat", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"), "revoke and redact"),
    ("slack-bot-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "rotate and redact"),
    ("private-key-pem", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"), "rotate keypair and redact"),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "redact (JWTs may include sensitive claims)"),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "rotate and redact"),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"), "rotate and redact"),
    ("google-api-key", re.compile(r"\bAIza[A-Za-z0-9_-]{35}\b"), "rotate and redact"),
    ("stripe-secret", re.compile(r"\bsk_(live|test)_[A-Za-z0-9]{24,}\b"), "rotate and redact"),
    ("generic-bearer", re.compile(r"(?i)\bauthorization:\s*bearer\s+[A-Za-z0-9._-]{20,}\b"), "redact and rotate referenced token"),
    ("password-assignment", re.compile(r"(?i)\bpassword\s*[:=]\s*['\"][^'\"]{8,}['\"]"), "redact"),
]


def scan_text(content: str) -> list[SecretMatch]:
    """Scan text for known secret patterns. Returns list of matches."""
    matches: list[SecretMatch] = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for name, pattern, _advice in PATTERNS:
            for m in pattern.finditer(line):
                snippet = line[max(0, m.start() - 5):m.end() + 5]
                matches.append(SecretMatch(name, line_no, snippet[:60]))
    return matches


def has_secrets(content: str) -> bool:
    return bool(scan_text(content))

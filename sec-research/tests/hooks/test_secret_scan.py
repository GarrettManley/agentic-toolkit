"""Test PT-6 / G-2: gitleaks-style secret detection."""
from __future__ import annotations

import pytest


def test_aws_access_key_detected():
    from lib.secret_scan import has_secrets, scan_text
    content = "config:\n  aws_key: AKIAIOSFODNN7EXAMPLE\n"
    assert has_secrets(content)
    matches = scan_text(content)
    assert any(m.pattern_name == "aws-access-key" for m in matches)


def test_github_pat_detected():
    from lib.secret_scan import has_secrets
    content = "GITHUB_TOKEN=ghp_AbCdEf1234567890aBcDeFgHiJkLmNoPqRsTuVwX12"
    assert has_secrets(content)


def test_jwt_detected():
    from lib.secret_scan import has_secrets
    content = "auth: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    assert has_secrets(content)


def test_private_key_detected():
    from lib.secret_scan import has_secrets
    content = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
    assert has_secrets(content)


def test_clean_content_passes():
    from lib.secret_scan import has_secrets
    content = "This is a normal log line with no secrets, just AKIA-not-a-real-prefix and ghp-not-token-format."
    assert not has_secrets(content)


def test_anthropic_key_detected():
    from lib.secret_scan import has_secrets
    content = "API_KEY=sk-ant-AbCdEf1234567890ABCDef"
    assert has_secrets(content)

import pytest
import os
import re

# Refactored Logic (Quote-safe parsing)
def extract_verification_cmd(content):
    # Regex that matches double-quoted strings while respecting backslash escaping
    # (?:[^"\\]|\\.)* matches either a character that isn't a quote/backslash OR an escaped character
    match = re.search(r'verification_cmd:\s*"((?:[^"\\]|\\.)*)"', content, re.DOTALL)
    if match:
        return match.group(1)
    return None

def test_extract_cmd_with_escaped_quotes():
    """GREEN TEST: Should handle escaped quotes inside the command."""
    content = '---\nverification_cmd: "echo \\"Hello World\\""\n---'
    result = extract_verification_cmd(content)
    assert result == 'echo \\"Hello World\\"'

def test_extract_cmd_multiline():
    """STAY GREEN: Ensure multiline still works."""
    content = '---\nverification_cmd: "Get-Process |\n  Where-Object { $_.CPU -gt 10 }"\n---'
    result = extract_verification_cmd(content)
    assert result == "Get-Process |\n  Where-Object { $_.CPU -gt 10 }"

import pytest
import os
import re
import json

# Refactored Logic (Robust brace-nesting parser)
def extract_json(text):
    start = text.find("{")
    if start == -1:
        return text.strip()
    
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                # Found the true end of the first object
                return text[start:i+1]
    
    # Fallback to current behavior if depth never returns to zero
    return text[start:].strip()

def test_extract_multiple_objects():
    """GREEN TEST: Should isolate the FIRST JSON object and ignore subsequent ones."""
    text = 'Task 1: {"name": "first", "meta": {"id": 1}}. Task 2: {"name": "second"}'
    result = extract_json(text)
    # Verify we got valid JSON
    data = json.loads(result)
    assert data["name"] == "first"
    assert data["meta"]["id"] == 1
    assert "second" not in result

def test_extract_json_with_trailing_garbage():
    """STAY GREEN: Ensure it still handles simple cases."""
    text = '{"name": "test"} and some other text.'
    assert extract_json(text) == '{"name": "test"}'

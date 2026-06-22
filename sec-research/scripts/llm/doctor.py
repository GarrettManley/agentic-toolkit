# scripts/llm/doctor.py
"""Provider reachability check. claude: key resolvable (no network). llama:
GET /health on the local endpoint (loopback, gated). Mirrors sandbox/doctor.py
fail-closed shape: returns (ok, notes)."""
from __future__ import annotations

import sys
import urllib.error
import urllib.request

from llm.client import DEFAULT_PROVIDER


def llm_doctor(provider: str | None = None) -> tuple[bool, list[str]]:
    name = (provider or DEFAULT_PROVIDER).lower()
    notes: list[str] = []
    if name == "claude":
        from llm.providers.claude import _resolve_key
        try:
            _resolve_key()
            notes.append("claude: API key resolved")
            return True, notes
        except Exception as e:
            notes.append(f"claude: {e}")
            return False, notes
    if name == "llama":
        from llm.providers.llama import ENDPOINT
        from lib.policy import check_http
        from llm._hosts import LLAMA_BOOTSTRAP_HOSTS
        health = ENDPOINT.rsplit("/v1/", 1)[0] + "/health"
        try:
            check_http(health, bootstrap_hosts=LLAMA_BOOTSTRAP_HOSTS)
            with urllib.request.urlopen(health, timeout=5):
                notes.append(f"llama: {health} reachable")
            return True, notes
        except (urllib.error.URLError, OSError) as e:
            notes.append(f"llama: {health} unreachable ({e})")
            return False, notes
    notes.append(f"unknown provider {name!r}")
    return False, notes


def main() -> int:
    ok, notes = llm_doctor()
    for n in notes:
        print(n)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
    sys.exit(main())

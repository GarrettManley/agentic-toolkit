"""Resend HTTP API adapter (https://resend.com/docs/api-reference/emails/send-email)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

API_URL = "https://api.resend.com/emails"
USER_AGENT = "mail-probe/0.1"  # Cloudflare-fronted API rejects the default urllib UA


class SendError(RuntimeError):
    pass


def send(api_key: str, *, sender: str, to: str, subject: str, text: str, timeout: float = 30.0) -> str:
    """Send one plain-text message; return Resend's message id."""
    body = json.dumps({"from": sender, "to": [to], "subject": subject, "text": text}).encode()
    req = urllib.request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)["id"]
    except urllib.error.HTTPError as e:
        raise SendError(f"Resend HTTP {e.code}: {e.read().decode(errors='replace')[:300]}") from e
    except urllib.error.URLError as e:
        raise SendError(f"Resend unreachable: {e.reason}") from e

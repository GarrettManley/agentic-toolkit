"""DNS-over-HTTPS (JSON API) adapter — queries Cloudflare and Google directly so the
probe sees both public resolver views regardless of the local resolver/cache."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

from mail_probe.checks import DnsAnswer

RESOLVERS: dict[str, str] = {
    "cloudflare": "https://cloudflare-dns.com/dns-query",
    "google": "https://dns.google/resolve",
}
_TYPE_CODES = {"NS": 2, "MX": 15, "TXT": 16}
_TXT_CHUNK = re.compile(r'"((?:[^"\\]|\\.)*)"')
USER_AGENT = "mail-probe/0.1"


def _normalise(rtype: str, data: str) -> str:
    if rtype == "TXT":
        # DoH returns TXT as quoted chunk(s): '"v=spf1 " "include:..."' -> joined payload.
        chunks = _TXT_CHUNK.findall(data)
        return "".join(chunks) if chunks else data
    return data.lower().rstrip(".")


def parse_doh(resolver: str, name: str, rtype: str, payload: dict) -> DnsAnswer:
    """Turn a DoH JSON response into a ``DnsAnswer``, keeping only records of ``rtype``
    (drops CNAME hops and RRSIGs that may share the Answer section)."""
    code = _TYPE_CODES[rtype]
    data = tuple(
        _normalise(rtype, rec["data"]) for rec in payload.get("Answer", []) if rec.get("type") == code
    )
    return DnsAnswer(resolver=resolver, name=name, rtype=rtype, status=int(payload.get("Status", -1)), data=data)


def query(resolver: str, name: str, rtype: str, *, timeout: float = 10.0) -> DnsAnswer:
    url = f"{RESOLVERS[resolver]}?{urllib.parse.urlencode({'name': name, 'type': rtype})}"
    req = urllib.request.Request(url, headers={"Accept": "application/dns-json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return parse_doh(resolver, name, rtype, json.load(resp))


def queries_for(domain: str) -> list[tuple[str, str]]:
    return [(domain, "NS"), (domain, "MX"), (domain, "TXT"), (f"_dmarc.{domain}", "TXT")]

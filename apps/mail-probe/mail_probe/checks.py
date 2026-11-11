"""Pure decision logic: DNS assertions and outcome/exit-code mapping.

No IO here — adapters in ``dns_doh``, ``resend_client`` and ``gmail_imap`` feed
plain values in, and ``probe`` composes the results.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum

CF_NAMESERVERS = frozenset({"collins.ns.cloudflare.com", "miguel.ns.cloudflare.com"})
CF_MX_SUFFIX = ".mx.cloudflare.net"
CF_SPF_INCLUDE = "include:_spf.mx.cloudflare.net"


@dataclass(frozen=True)
class DnsAnswer:
    """One resolver's answer to one (name, type) query.

    ``status`` is the DoH/RCODE status (0 = NOERROR, 2 = SERVFAIL, 3 = NXDOMAIN).
    ``data`` holds record payloads already normalised by the adapter: TXT strings
    unquoted and joined, names lower-cased without the trailing dot.
    """

    resolver: str
    name: str
    rtype: str
    status: int
    data: tuple[str, ...]


@dataclass(frozen=True)
class Finding:
    resolver: str
    check: str
    message: str

    def __str__(self) -> str:
        return f"[{self.resolver}] {self.check}: {self.message}"


def _mx_host(record: str) -> str:
    # "10 route1.mx.cloudflare.net" -> "route1.mx.cloudflare.net"
    return record.split()[-1]


def evaluate_dns(answers: Iterable[DnsAnswer], *, domain: str) -> list[Finding]:
    """Assert the domain is wired for Cloudflare Email Routing.

    Checks, per resolver: every query resolved NOERROR; NS is exactly the CF pair;
    MX is non-empty and entirely ``*.mx.cloudflare.net``; the apex TXT carries an SPF
    record including CF; ``_dmarc.<domain>`` carries a DMARC record.
    """
    findings: list[Finding] = []
    for a in answers:
        if a.status != 0:
            findings.append(Finding(a.resolver, f"{a.rtype} {a.name}", f"DNS status {a.status} (expected 0/NOERROR)"))
            continue
        match a.rtype:
            case "NS":
                if set(a.data) != CF_NAMESERVERS:
                    findings.append(Finding(a.resolver, "NS", f"got {sorted(a.data)}, expected {sorted(CF_NAMESERVERS)}"))
            case "MX":
                hosts = [_mx_host(r) for r in a.data]
                if not hosts:
                    findings.append(Finding(a.resolver, "MX", "no MX records"))
                elif foreign := [h for h in hosts if not h.endswith(CF_MX_SUFFIX)]:
                    findings.append(Finding(a.resolver, "MX", f"non-Cloudflare MX hosts {foreign}"))
            case "TXT" if a.name == domain:
                spf = [t for t in a.data if t.lower().startswith("v=spf1")]
                if len(spf) != 1:
                    findings.append(Finding(a.resolver, "SPF", f"expected exactly one SPF record, got {len(spf)}"))
                elif CF_SPF_INCLUDE not in spf[0].split():
                    findings.append(Finding(a.resolver, "SPF", f"missing {CF_SPF_INCLUDE}: {spf[0]!r}"))
            case "TXT" if a.name == f"_dmarc.{domain}":
                if not any(t.startswith("v=DMARC1") for t in a.data):
                    findings.append(Finding(a.resolver, "DMARC", "no v=DMARC1 record"))
    return findings


class Delivery(StrEnum):
    """What happened to the probe message after it was handed to the sender."""

    DELIVERED = "delivered"
    SPAM = "spam"
    TIMEOUT = "timeout"
    SEND_FAILED = "send_failed"
    PROBE_ERROR = "probe_error"  # our own tooling failed (IMAP login, missing secret…)


class Outcome(StrEnum):
    OK = "ok"
    DNS_FAIL = "dns_fail"
    SEND_FAIL = "send_fail"
    TIMEOUT = "timeout"
    SPAM = "spam"
    ERROR = "error"


EXIT_CODES: dict[Outcome, int] = {
    Outcome.OK: 0,
    Outcome.ERROR: 1,
    Outcome.DNS_FAIL: 2,
    Outcome.SEND_FAIL: 3,
    Outcome.TIMEOUT: 4,
    Outcome.SPAM: 5,
}

_DELIVERY_OUTCOME = {
    Delivery.SEND_FAILED: Outcome.SEND_FAIL,
    Delivery.TIMEOUT: Outcome.TIMEOUT,
    Delivery.SPAM: Outcome.SPAM,
    Delivery.PROBE_ERROR: Outcome.ERROR,
}


def decide_outcome(findings: list[Finding], delivery: Delivery) -> Outcome:
    """A delivery failure outranks DNS drift; DNS drift with mail still flowing is a warning-grade failure."""
    if delivery in _DELIVERY_OUTCOME:
        return _DELIVERY_OUTCOME[delivery]
    return Outcome.DNS_FAIL if findings else Outcome.OK


@dataclass
class ProbeResult:
    outcome: Outcome
    started_at: str
    finished_at: str
    recipient: str
    delivery: Delivery
    latency_s: float | None = None
    findings: list[Finding] = field(default_factory=list)
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.outcome is Outcome.OK

    @property
    def summary(self) -> str:
        if self.ok:
            return f"{self.recipient} delivered in {self.latency_s:.0f}s; DNS clean"
        parts = [f"{self.outcome.value}: {self.recipient} delivery={self.delivery.value}"]
        if self.detail:
            parts.append(self.detail)
        if self.findings:
            parts.append(f"{len(self.findings)} DNS finding(s)")
        return "; ".join(parts)

    def to_record(self) -> dict:
        return {
            "name": "mail-probe",
            "ok": self.ok,
            "outcome": self.outcome.value,
            "summary": self.summary,
            "checked_at": self.finished_at,
            "started_at": self.started_at,
            "recipient": self.recipient,
            "delivery": self.delivery.value,
            "latency_s": self.latency_s,
            "findings": [str(f) for f in self.findings],
            "detail": self.detail,
        }

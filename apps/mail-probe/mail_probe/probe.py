"""Compose the weekly probe: DNS assertions -> send via Resend -> confirm in Gmail -> record + alert.

Usage:  secrets uv run python -m mail_probe.probe [--to jobs@garrettmanley.dev] [--timeout 900] [--no-alert] [--keep]
Exit codes: see ``checks.EXIT_CODES`` (0 ok, 1 probe error, 2 DNS drift, 3 send fail, 4 timeout, 5 spam).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from mail_probe import dns_doh
from mail_probe.checks import (
    EXIT_CODES,
    Delivery,
    DnsAnswer,
    Finding,
    Outcome,
    ProbeResult,
    decide_outcome,
    evaluate_dns,
)
from mail_probe.gmail_imap import ALL_MAIL, SPAM

# Injected by `op run` from .env.tpl (1Password refs); never stored on disk.
SECRET_ENV = ("RESEND_API_KEY", "GMAIL_USER", "GMAIL_APP_PASSWORD")
DEFAULT_TO = "jobs@garrettmanley.dev"
DEFAULT_SENDER = "mail-probe <probe@probe.garrettmanley.com>"
APP_ROOT = Path(__file__).resolve().parent.parent
HEALTHCHECK_PATH = Path.home() / ".claude" / "stewardship" / "healthchecks" / "mail-probe.json"
RUNS_LOG = APP_ROOT / "data" / "runs.jsonl"


class Mailbox(Protocol):
    def search(self, folder: str, gmail_query: str) -> list[bytes]: ...
    def trash(self, folder: str, uids: list[bytes]) -> None: ...


@dataclass
class Deps:
    """IO seams, injected so ``run`` is testable without network."""

    dns_query: Callable[[str, str, str], DnsAnswer]
    send_mail: Callable[[str, str, str], str]  # (to, subject, text) -> message id
    open_mailbox: Callable[[], AbstractContextManager[Mailbox]]
    resolvers: tuple[str, ...] = tuple(dns_doh.RESOLVERS)
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    now: Callable[[], str] = lambda: datetime.now(UTC).isoformat(timespec="seconds")


def _check_dns(domain: str, deps: Deps) -> list[Finding]:
    answers: list[DnsAnswer] = []
    query_errors: list[Finding] = []
    for resolver in deps.resolvers:
        for name, rtype in dns_doh.queries_for(domain):
            try:
                answers.append(deps.dns_query(resolver, name, rtype))
            except Exception as e:  # network boundary: record, keep probing
                query_errors.append(Finding(resolver, f"{rtype} {name}", f"query error: {e}"))
    return query_errors + evaluate_dns(answers, domain=domain)


def _await_delivery(
    mailbox: Mailbox, gmail_query: str, *, t0: float, timeout_s: float, interval_s: float, trash: bool, deps: Deps
) -> tuple[Delivery, float | None]:
    while True:
        if uids := mailbox.search(ALL_MAIL, gmail_query):
            latency = deps.clock() - t0
            if trash:
                mailbox.trash(ALL_MAIL, uids)
            return Delivery.DELIVERED, latency
        if mailbox.search(SPAM, gmail_query):
            return Delivery.SPAM, deps.clock() - t0
        if deps.clock() - t0 >= timeout_s:
            return Delivery.TIMEOUT, None
        deps.sleep(interval_s)


def run(
    recipient: str,
    deps: Deps,
    *,
    timeout_s: float = 900,
    interval_s: float = 30,
    trash: bool = True,
    token: str | None = None,
) -> ProbeResult:
    started = deps.now()
    domain = recipient.rpartition("@")[2]
    findings = _check_dns(domain, deps)

    token = token or uuid.uuid4().hex  # hex: no dashes for Gmail's search parser to treat as negation
    subject = f"[mail-probe] {token}"
    gmail_query = f"to:{recipient} subject:{token}"
    detail = ""
    latency: float | None = None

    t0 = deps.clock()
    try:
        deps.send_mail(recipient, subject, f"Automated weekly delivery probe for {recipient}. Token {token}.")
    except Exception as e:
        delivery, detail = Delivery.SEND_FAILED, str(e)
    else:
        try:
            with deps.open_mailbox() as mailbox:
                delivery, latency = _await_delivery(
                    mailbox, gmail_query, t0=t0, timeout_s=timeout_s, interval_s=interval_s, trash=trash, deps=deps
                )
        except Exception as e:
            delivery, detail = Delivery.PROBE_ERROR, f"mailbox check failed: {e}"
        if delivery is Delivery.TIMEOUT:
            detail = f"not in Gmail after {timeout_s:.0f}s (query: {gmail_query})"
        elif delivery is Delivery.SPAM:
            detail = "probe arrived but was filed as spam"

    return ProbeResult(
        outcome=decide_outcome(findings, delivery),
        started_at=started,
        finished_at=deps.now(),
        recipient=recipient,
        delivery=delivery,
        latency_s=latency,
        findings=findings,
        detail=detail,
    )


def _load_secrets() -> dict[str, str | None]:
    secrets = {name: os.environ.get(name) or None for name in SECRET_ENV}
    if secrets["GMAIL_APP_PASSWORD"]:
        # Google displays app passwords in 4-char groups; tolerate the pasted form.
        secrets["GMAIL_APP_PASSWORD"] = secrets["GMAIL_APP_PASSWORD"].replace(" ", "")
    return secrets


def _write_records(record: dict) -> None:
    HEALTHCHECK_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = HEALTHCHECK_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, HEALTHCHECK_PATH)
    RUNS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with RUNS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--to", default=DEFAULT_TO, help="forwarding address under test")
    p.add_argument("--sender", default=DEFAULT_SENDER, help="From: on a Resend-verified domain")
    p.add_argument("--timeout", type=float, default=900, help="seconds to wait for arrival")
    p.add_argument("--interval", type=float, default=30, help="seconds between Gmail polls")
    p.add_argument("--keep", action="store_true", help="don't trash the probe message")
    p.add_argument("--no-alert", action="store_true", help="skip the failure alert email")
    args = p.parse_args(argv)

    secrets = _load_secrets()
    missing = [k for k, v in secrets.items() if not v]
    if missing:
        now = datetime.now(UTC).isoformat(timespec="seconds")
        result = ProbeResult(
            outcome=Outcome.ERROR, started_at=now, finished_at=now, recipient=args.to,
            delivery=Delivery.PROBE_ERROR,
            detail=f"missing env var(s) {missing}; run via scripts/run_weekly.ps1 or `secrets uv run python -m mail_probe.probe`",
        )
    else:
        from mail_probe import resend_client
        from mail_probe.gmail_imap import GmailMailbox

        deps = Deps(
            dns_query=lambda r, n, t: dns_doh.query(r, n, t),
            send_mail=lambda to, subj, text: resend_client.send(
                secrets["RESEND_API_KEY"], sender=args.sender, to=to, subject=subj, text=text
            ),
            open_mailbox=lambda: GmailMailbox(secrets["GMAIL_USER"], secrets["GMAIL_APP_PASSWORD"]),
        )
        result = run(args.to, deps, timeout_s=args.timeout, interval_s=args.interval, trash=not args.keep)

    record = result.to_record()
    _write_records(record)
    print(f"[mail-probe] {'OK' if result.ok else 'FAIL'} - {result.summary}")  # ASCII: cp1252 console
    for f in result.findings:
        print(f"  {f}")

    if not result.ok and not args.no_alert and secrets["GMAIL_USER"] and secrets["GMAIL_APP_PASSWORD"]:
        from mail_probe.alert import send_alert

        try:
            send_alert(
                secrets["GMAIL_USER"], secrets["GMAIL_APP_PASSWORD"],
                subject=f"[mail-probe] FAIL ({result.outcome.value}): {args.to}",
                body=json.dumps(record, indent=2),
            )
        except Exception as e:  # toast from the wrapper still fires on the exit code
            print(f"[mail-probe] alert email failed: {e}", file=sys.stderr)

    return EXIT_CODES[result.outcome]


if __name__ == "__main__":
    sys.exit(main())

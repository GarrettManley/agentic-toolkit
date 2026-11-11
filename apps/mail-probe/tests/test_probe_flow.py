"""Sociable test of ``probe.run`` with the three IO adapters doubled (no network)."""

from contextlib import nullcontext

from mail_probe.checks import Delivery, DnsAnswer, Outcome
from mail_probe.gmail_imap import ALL_MAIL, SPAM
from mail_probe.probe import Deps, run

TO = "jobs@garrettmanley.dev"
D = "garrettmanley.dev"
GOOD = {
    (D, "NS"): ("collins.ns.cloudflare.com", "miguel.ns.cloudflare.com"),
    (D, "MX"): ("3 route2.mx.cloudflare.net",),
    (D, "TXT"): ("v=spf1 include:_spf.mx.cloudflare.net ~all",),
    (f"_dmarc.{D}", "TXT"): ("v=DMARC1; p=quarantine",),
}


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.t += s


class FakeMailbox:
    """Probe message appears in ``folder`` once ``arrive_at`` seconds of fake time have passed."""

    def __init__(self, clock: FakeClock, folder: str | None, arrive_at: float = 0) -> None:
        self.clock, self.folder, self.arrive_at = clock, folder, arrive_at
        self.trashed: list[bytes] = []

    def search(self, folder: str, gmail_query: str) -> list[bytes]:
        return [b"42"] if folder == self.folder and self.clock() >= self.arrive_at else []

    def trash(self, folder: str, uids: list[bytes]) -> None:
        self.trashed.extend(uids)


def make_deps(clock: FakeClock, mailbox: FakeMailbox, *, send_error: Exception | None = None, sent: list | None = None):
    def send(to, subject, text):
        if send_error:
            raise send_error
        if sent is not None:
            sent.append((to, subject))
        return "id-1"

    return Deps(
        dns_query=lambda r, n, t: DnsAnswer(r, n, t, 0, GOOD[(n, t)]),
        send_mail=send,
        open_mailbox=lambda: nullcontext(mailbox),
        resolvers=("cloudflare", "google"),
        sleep=clock.sleep,
        clock=clock,
        now=lambda: "2026-11-10T00:00:00+00:00",
    )


def test_delivered_probe_is_ok_with_latency_and_trashed():
    clock = FakeClock()
    box = FakeMailbox(clock, ALL_MAIL, arrive_at=60)
    sent: list = []
    result = run(TO, make_deps(clock, box, sent=sent), timeout_s=900, interval_s=30, token="abc")
    assert (result.outcome, result.latency_s, box.trashed, sent) == (
        Outcome.OK, 60, [b"42"], [(TO, "[mail-probe] abc")]
    )


def test_probe_never_arriving_times_out():
    clock = FakeClock()
    result = run(TO, make_deps(clock, FakeMailbox(clock, None)), timeout_s=120, interval_s=30)
    assert (result.outcome, result.delivery) == (Outcome.TIMEOUT, Delivery.TIMEOUT)


def test_probe_in_spam_is_spam_and_not_trashed():
    clock = FakeClock()
    box = FakeMailbox(clock, SPAM)
    result = run(TO, make_deps(clock, box), timeout_s=120, interval_s=30)
    assert (result.outcome, box.trashed) == (Outcome.SPAM, [])


def test_send_failure_skips_mailbox_and_reports_detail():
    clock = FakeClock()

    def never_open():
        raise AssertionError("mailbox must not be opened after a send failure")

    deps = make_deps(clock, FakeMailbox(clock, ALL_MAIL), send_error=RuntimeError("Resend HTTP 403"))
    deps.open_mailbox = never_open
    result = run(TO, deps)
    assert (result.outcome, result.detail) == (Outcome.SEND_FAIL, "Resend HTTP 403")


def test_dns_query_error_is_a_finding_not_a_crash():
    clock = FakeClock()
    deps = make_deps(clock, FakeMailbox(clock, ALL_MAIL))
    good_query = deps.dns_query

    def flaky(r, n, t):
        if r == "google" and t == "NS":
            raise TimeoutError("timed out")
        return good_query(r, n, t)

    deps.dns_query = flaky
    result = run(TO, deps)
    assert result.outcome is Outcome.DNS_FAIL and "query error" in result.findings[0].message

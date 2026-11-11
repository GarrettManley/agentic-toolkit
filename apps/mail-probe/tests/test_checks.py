"""Unit tests for the pure DNS assertions and outcome mapping."""

from mail_probe.checks import (
    EXIT_CODES,
    Delivery,
    DnsAnswer,
    Finding,
    Outcome,
    decide_outcome,
    evaluate_dns,
)

D = "garrettmanley.dev"


def healthy(resolver: str = "cloudflare") -> list[DnsAnswer]:
    return [
        DnsAnswer(resolver, D, "NS", 0, ("collins.ns.cloudflare.com", "miguel.ns.cloudflare.com")),
        DnsAnswer(resolver, D, "MX", 0, ("3 route2.mx.cloudflare.net", "28 route3.mx.cloudflare.net")),
        DnsAnswer(resolver, D, "TXT", 0, ("v=spf1 include:_spf.mx.cloudflare.net ~all", "google-site-verification=x")),
        DnsAnswer(resolver, f"_dmarc.{D}", "TXT", 0, ("v=DMARC1; p=quarantine",)),
    ]


def replace(answers: list[DnsAnswer], rtype: str, name: str, **changes) -> list[DnsAnswer]:
    from dataclasses import replace as dc_replace

    return [dc_replace(a, **changes) if (a.rtype, a.name) == (rtype, name) else a for a in answers]


def checks_of(findings: list[Finding]) -> list[str]:
    return [f.check for f in findings]


def test_healthy_zone_has_no_findings():
    assert evaluate_dns(healthy("cloudflare") + healthy("google"), domain=D) == []


def test_servfail_is_reported_with_status():
    findings = evaluate_dns(replace(healthy(), "MX", D, status=2, data=()), domain=D)
    assert checks_of(findings) == [f"MX {D}"] and "status 2" in findings[0].message


def test_non_cloudflare_nameservers_flagged():
    findings = evaluate_dns(replace(healthy(), "NS", D, data=("ns-cloud-e1.googledomains.com",)), domain=D)
    assert checks_of(findings) == ["NS"]


def test_foreign_mx_host_flagged():
    findings = evaluate_dns(replace(healthy(), "MX", D, data=("10 mxa.mailgun.org", "3 route2.mx.cloudflare.net")), domain=D)
    assert checks_of(findings) == ["MX"] and "mxa.mailgun.org" in findings[0].message


def test_empty_mx_flagged():
    assert checks_of(evaluate_dns(replace(healthy(), "MX", D, data=()), domain=D)) == ["MX"]


def test_spf_without_cloudflare_include_flagged():
    findings = evaluate_dns(replace(healthy(), "TXT", D, data=("v=spf1 include:mailgun.org ~all",)), domain=D)
    assert checks_of(findings) == ["SPF"]


def test_duplicate_spf_records_flagged():
    spf = "v=spf1 include:_spf.mx.cloudflare.net ~all"
    assert checks_of(evaluate_dns(replace(healthy(), "TXT", D, data=(spf, spf)), domain=D)) == ["SPF"]


def test_missing_dmarc_flagged():
    assert checks_of(evaluate_dns(replace(healthy(), "TXT", f"_dmarc.{D}", data=()), domain=D)) == ["DMARC"]


def test_delivered_with_clean_dns_is_ok():
    assert decide_outcome([], Delivery.DELIVERED) is Outcome.OK


def test_delivered_with_dns_drift_is_dns_fail():
    assert decide_outcome([Finding("google", "SPF", "x")], Delivery.DELIVERED) is Outcome.DNS_FAIL


def test_delivery_failure_outranks_dns_drift():
    assert decide_outcome([Finding("google", "SPF", "x")], Delivery.TIMEOUT) is Outcome.TIMEOUT


def test_each_delivery_failure_maps_to_its_outcome():
    assert [decide_outcome([], d) for d in (Delivery.SEND_FAILED, Delivery.SPAM, Delivery.PROBE_ERROR)] == [
        Outcome.SEND_FAIL,
        Outcome.SPAM,
        Outcome.ERROR,
    ]


def test_exit_codes_are_distinct_and_only_ok_is_zero():
    codes = list(EXIT_CODES.values())
    assert len(set(codes)) == len(Outcome) and [o for o, c in EXIT_CODES.items() if c == 0] == [Outcome.OK]

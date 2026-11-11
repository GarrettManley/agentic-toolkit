"""Serialisation boundary: DoH JSON -> DnsAnswer."""

from mail_probe.dns_doh import parse_doh


def test_txt_chunks_are_unquoted_and_joined():
    payload = {"Status": 0, "Answer": [{"type": 16, "data": '"v=spf1 include:_spf.mx." "cloudflare.net ~all"'}]}
    assert parse_doh("google", "d", "TXT", payload).data == ("v=spf1 include:_spf.mx.cloudflare.net ~all",)


def test_names_are_lowercased_without_trailing_dot_and_other_types_dropped():
    payload = {
        "Status": 0,
        "Answer": [
            {"type": 5, "data": "alias.example."},  # CNAME hop
            {"type": 15, "data": "3 Route2.MX.Cloudflare.net."},
        ],
    }
    assert parse_doh("cloudflare", "d", "MX", payload).data == ("3 route2.mx.cloudflare.net",)


def test_servfail_has_status_and_no_data():
    answer = parse_doh("google", "d", "MX", {"Status": 2})
    assert (answer.status, answer.data) == (2, ())

# mail-probe

Weekly end-to-end check that `jobs@garrettmanley.dev` (the address on the resume) still
forwards to Gmail through Cloudflare Email Routing. The address was silently dead for months
while the zone returned SERVFAIL, until the 2026-11-10 migration
(`docs/migrations/2026-11-10-squarespace-to-cloudflare.md`) fixed it.

## What a run does

1. **DNS:** queries Cloudflare and Google DoH for NS, MX, SPF and `_dmarc` and asserts the
   Cloudflare Email Routing wiring (`mail_probe/checks.py`).
2. **Send:** sends a message to `jobs@` through Resend from `probe@probe.garrettmanley.com`, with
   subject `[mail-probe] <token>`.
3. **Confirm:** polls Gmail over IMAP for up to 15 min. If the message arrives it's moved to Trash.
   If it lands in Spam, the run fails with a distinct outcome.
4. **Record:** writes `~/.claude/stewardship/healthchecks/mail-probe.json`, which the morning
   briefing reads, and appends to `data/runs.jsonl`.
5. **Alert on failure:** sends an email straight to Gmail over SMTP 587 (not through `.dev`), and the
   wrapper shows a Windows toast.

Exit codes: 0 ok, 1 probe error, 2 DNS drift (mail still delivered), 3 send failed,
4 timeout, 5 spam.

### Why it's built this way

- A test sent from your own Gmail proves nothing. Gmail drops a message that forwards back to the
  account that sent it, so the sender has to be external (Resend).
- Outbound port 25 is blocked by the ISP, so the probe can't talk to the MX directly. It has to
  send through an HTTP API.
- Scheduled cloud routines don't get Gmail access, so the probe runs locally from Task Scheduler.

## Setup

```powershell
cd apps/mail-probe
uv sync
# Secrets: 1Password vault "Automation" items referenced in .env.tpl; the weekly task
# authenticates with the service-account token (~/scripts/lib/Secrets.psm1).
secrets uv run python -m mail_probe.probe       # interactive run (Windows Hello)
pwsh -NoProfile -File scripts/run_weekly.ps1   # one live run as the scheduled task would
pwsh -NoProfile -File scripts/register_weekly.ps1   # Task 'mail-probe-weekly', Mondays 07:00 local
```

Resend: domain `probe.garrettmanley.com` is verified. Its DKIM TXT and two Forge CNAMEs (`rsend.probe`, `send.probe`) live in the
Cloudflare `garrettmanley.com` zone. The root domain's DMARC is `p=quarantine` with no `sp=`,
so the subdomain inherits it, and mail only passes because the Resend DKIM aligns.

## Development

`uv run pytest`. The unit tests cover the DNS assertions and outcome mapping, there is one
serialization test for the DoH parser, and one flow test with the network adapters doubled.
No test touches the network; the live run above is the integration check.

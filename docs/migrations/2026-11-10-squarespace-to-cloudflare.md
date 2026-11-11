---
status: active
author: Garrett Manley
created: 2026-11-10
diataxis: how-to
---

# Squarespace → Cloudflare domain migration

**Started:** 2026-11-10
**Plan:** `C:\Users\Garre\.claude\plans\i-m-looking-to-migrate-velvety-sun.md`
**Shape:** Safe two-phase per domain — DNS first, bake 24–72h, then registrar transfer.
**Hard constraint:** Zero mail interruption. All affected mailboxes are on Google Workspace.

**Tooling note:** `dig` isn't installed on this Windows box. Use PowerShell native:

```powershell
Resolve-DnsName -Server 1.1.1.1 -Type ANY  <domain>
Resolve-DnsName -Server 1.1.1.1 -Type MX   <domain>
Resolve-DnsName -Server 1.1.1.1 -Type TXT  <domain>
Resolve-DnsName -Server 1.1.1.1 -Type TXT  _dmarc.<domain>
Resolve-DnsName -Server 1.1.1.1 -Type TXT  google._domainkey.<domain>
Resolve-DnsName -Server 1.1.1.1 -Type NS   <domain>
```

Cross-check against `-Server 8.8.8.8`. The plan's `dig` snippets stay valid for WSL.

## Buckets

- **A** — TLD supported by Cloudflare Registrar → full two-phase migration.
- **B** — TLD NOT supported by Cloudflare Registrar → DNS-to-Cloudflare only; registration
  stays at Squarespace or moves to Porkbun (decide after Phase 5).
- **C** — Email forwarding only (no hosted mailbox) → migrate + recreate forwarding at
  Cloudflare Email Routing.

Cloudflare Registrar supported TLDs:
https://developers.cloudflare.com/registrar/account-and-billing/manage-and-transfer/supported-tlds/

## Domain roster

Four domains, all registered at Squarespace, all with DNS delegated to Google Cloud DNS
(`ns-cloud-*.googledomains.com`). Squarespace manages *registration*; Google Cloud DNS hosts
*the zones*. This is unusual — the migration moves both to Cloudflare.

| # | Domain              | TLD      | Bucket | Current mail        | Expiration     | Notes |
|---|---------------------|----------|--------|---------------------|----------------|-------|
| 1 | g.recipes           | .recipes | A      | None (empty zone)   | 2027-04-13     | No records at all; parked. CF Registrar supports .recipes (Identity Digital). |
| 2 | garrettmanley.app   | .app     | A      | None (empty zone)   | 2027-04-13     | No records at all; parked. .app is HSTS-preloaded → HTTPS mandatory when used. |
| 3 | garrettmanley.com   | .com     | A + C  | Mailgun MX + SPF    | 2027-01-21     | Apex A → Squarespace site hosts; www → `ext-sq.squarespace.com`; Squarespace URL-forward → github.com/GarrettManley. Squarespace Email Forwarding UI lists 4 rules (email@, urgent@, kayla@, garrett@) but MX=Mailgun — Mailgun Routes is likely the real forwarder, UI rules likely dormant. CONFIRM with a test email. On migration: either preserve Mailgun Routes (keep MX=Mailgun in CF zone) OR migrate to Cloudflare Email Routing. |
| 4 | garrettmanley.dev   | .dev     | A + C  | Mailgun SPF + MX    | 2027-04-13     | **BROKEN:** SERVFAIL from 1.1.1.1 and 8.8.8.8. Zone content exists at `ns-cloud-e1-4.googledomains.com` (SPF `v=spf1 include:mailgun.org ~all`, 2 MX, no A) but the .dev TLD delegation or DNSSEC DS is broken — resolvers reject. Pre-existing. Migration via Cloudflare NS swap + clearing any stale DS at Squarespace will reset it cleanly. **Forwarding rules dormant:** `guildmaster@`→`garrettmanley+guildmaster@gmail.com`, `jobs@`→`garrettmanley+jobs@gmail.com`. These have NOT been receiving mail while the zone has been SERVFAIL (sender MTAs can't resolve the MX). |

**Bucket logic per the plan:**
- A = full two-phase (DNS → bake → registrar transfer). All four domains qualify.
- B = TLD not supported by CF Registrar. **None.**
- C = email-forwarding reconstruction needed at CF Email Routing. **`.com` (4 rules) and `.dev` (2 rules).**

Cloudflare Registrar supports all four TLDs (.com/.app/.dev as headline examples on the product
page; .recipes listed in the TLD policies table, Identity Digital registry).

## Forwarding rules to recreate at Cloudflare Email Routing

Six total, consolidating onto CF Email Routing (replaces both the Squarespace UI rules and any
live Mailgun Routes — stack goes from three providers to one).

**garrettmanley.com**:
| From                       | To                                 |
|----------------------------|------------------------------------|
| email@garrettmanley.com    | garrettmanley@gmail.com            |
| urgent@garrettmanley.com   | garrettmanley@gmail.com            |
| kayla@garrettmanley.com    | kayla.hughes.manley@gmail.com      |
| garrett@garrettmanley.com  | email@garrettmanley.com (chained)  |

Note: `garrett@` → `email@` is a chain that then forwards out. CF Email Routing supports
chaining via a catch-all/custom-address → address pattern; may need to flatten to
`garrett@ → garrettmanley@gmail.com` directly instead.

**garrettmanley.dev** (currently dormant due to SERVFAIL — will reactivate on migration):
| From                        | To                                           |
|-----------------------------|----------------------------------------------|
| guildmaster@garrettmanley.dev | garrettmanley+guildmaster@gmail.com        |
| jobs@garrettmanley.dev      | garrettmanley+jobs@gmail.com                 |

**garrettmanley.app**: no forwarding rules. Park with an empty zone (just CAA + optional
Email Routing "reject all" to prevent spoofing).

**g.recipes**: no forwarding rules. Park with an empty zone.

## Phase 2 playbook (CF account + zones + records + Email Routing)

Execution order (lowest risk → highest, to build confidence with the CF flow):
1. **g.recipes** — parked, empty zone. Dry-run the CF add-zone flow here.
2. **garrettmanley.app** — parked, empty zone. Same flow.
3. **garrettmanley.dev** — broken forwarders; migration RESTORES mail that's been dead.
4. **garrettmanley.com** — live site + 4 forwarders + URL redirect. Last, after CF flow is proven.

### Step-by-step (per domain)

Done at **Cloudflare dashboard** (dash.cloudflare.com), the **Squarespace domain manager**,
and the **Google Cloud DNS console** (console.cloud.google.com → Network services → Cloud DNS).

#### Prep (one-time)

1. Create Cloudflare account; enable 2FA (hardware key or TOTP).
2. Account → Members → set backup recovery email.

#### Per-domain loop

1. **Cloudflare** → Add Site → enter `<domain>` → Free plan. CF scans current NS (Google
   Cloud DNS) and imports records.
2. **Diff** the imported record set against the per-domain snapshot below. Add/fix any
   missing record manually.
3. **Enable Email Routing** (only for `.com` and `.dev`): Email → Email Routing → follow the
   guided setup. CF auto-adds the required MX + SPF records to the zone. Destination
   addresses must be verified by clicking a link Gmail delivers to each `@gmail.com` target
   (do this once per unique destination, not per rule).
4. Add the forwarding rules per the tables above (email@, urgent@, kayla@, garrett@ on .com;
   guildmaster@, jobs@ on .dev).
5. For `garrettmanley.com`: configure the URL redirect to github via Cloudflare → Rules →
   Bulk Redirects (free): source `https://garrettmanley.com/*` → destination
   `https://github.com/GarrettManley/$1`, type 301, preserve path+query. Apex A record can
   point at any address (even `192.0.2.1`, a documentation IP) as long as it is
   **orange-cloud proxied** so CF intercepts.
6. **Lower TTLs** on MX, TXT, A, CNAME to **300s**. The zone is hosted on
   `ns-cloud-*.googledomains.com` — this is the shared Google infra that both Google Domains
   (now Squarespace) and Google Cloud DNS use. Check first: **Squarespace → Domains →
   `<domain>` → Advanced Settings → DNS Settings** is the most likely editor. If not
   present, check Google Cloud Console → Network services → Cloud DNS. Edit TTLs there.
   Wait at least the previous TTL (14400s = 4h based on the .dev snapshot) before proceeding
   to NS swap in Phase 3, so resolvers worldwide actually pick up the short TTL.
7. **Verify the CF zone answers correctly** by querying the two CF nameservers directly
   (CF shows them in the zone overview):
   ```powershell
   Resolve-DnsName -Server <cf-ns-1> -Type MX <domain>
   Resolve-DnsName -Server <cf-ns-1> -Type TXT <domain>
   Resolve-DnsName -Server <cf-ns-1> -Type A <domain>
   ```
   Everything should look exactly like what you intend to publish AFTER cutover.

### Per-zone record plan

#### g.recipes (empty / parked)
- **CF NS assigned (2026-11-10):** `conrad.ns.cloudflare.com`, `marge.ns.cloudflare.com`
- Imported record: 1 CNAME `_domainconnect` → `_domainconnect.d...` (Squarespace Domain
  Connect handshake record; harmless, keep)
- Optional: CAA `0 issue ";"` (block all cert issuance while parked)
- Optional: Email Routing "Reject all" catch-all (anti-spoof)
- NS at Squarespace still: `ns-cloud-e1-4.googledomains.com` (don't swap yet)

#### garrettmanley.app (parked — api subdomain deleted)
- **CF NS assigned (2026-11-10):** `conrad.ns.cloudflare.com`, `marge.ns.cloudflare.com`
- Imported records (post-cleanup):
  - **CNAME** `_domainconnect` → `_domainconnect.domains.squarespace.com` (Squarespace
    handshake record; harmless, kept)
  - ~~**A** `api.garrettmanley.app` → `40.78.135.89`~~ **DELETED 2026-11-10** (dead per
    Garrett)
- Note: `.app` is on the HSTS preload list — HTTPS mandatory if ever used
- Optional: CAA `0 issue ";"`, Email Routing reject-all
- NS at Squarespace still: `ns-cloud-b1-4.googledomains.com` (don't swap yet)

#### garrettmanley.dev (added; mail-only, broken→fixed)
- **CF NS assigned (2026-11-10):** `collins.ns.cloudflare.com`, `miguel.ns.cloudflare.com`
- Imported records: **0** (CF's scanner also gets SERVFAIL — expected)
- Need to add: Cloudflare Email Routing (auto-installs MX + SPF + optional DKIM)
- Email Routing rules to add:
  - `guildmaster@garrettmanley.dev` → `garrettmanley+guildmaster@gmail.com`
  - `jobs@garrettmanley.dev` → `garrettmanley+jobs@gmail.com`
- **Critical: at Squarespace registrar, delete/clear any DS record for this domain** before
  changing NS. CF's own page recommends: "Make sure DNSSEC is off. Find and turn off the DNS
  security (DNSSEC) setting if it is on. You can re-enable it later through Cloudflare."
- NS at Squarespace still: `ns-cloud-e1-4.googledomains.com` (don't swap yet)

#### garrettmanley.com (added; live site + mail + Bluesky verification)
- **CF NS assigned (2026-11-10):** `collins.ns.cloudflare.com`, `miguel.ns.cloudflare.com`
- Imported records (9 total):
  - **A** `garrettmanley.com` → `198.185.159.145` (Proxied) — Squarespace web host
  - **A** `garrettmanley.com` → `198.185.159.144` (Proxied) — Squarespace web host
  - **CNAME** `_domainconnect` → `_domainconnect.domains.squarespace.com` (Proxied) — handshake
  - **CNAME** `www` → `ext-sq.squarespace.com` (Proxied) — Squarespace www
  - **MX** `garrettmanley.com` → `mxb.mailgun.org` prio 10 (DNS only) — Mailgun inbound
  - **MX** `garrettmanley.com` → `mxa.mailgun.org` prio 10 (DNS only) — Mailgun inbound
  - **TXT** `_atproto` → `"did=did:plc:ptuxef..."` (DNS only) — **BLUESKY / AT PROTOCOL
    handle verification — MUST PRESERVE**
  - **TXT** `garrettmanley.com` → `"v=spf1 include:ma..."` (DNS only) — Mailgun SPF
  - **TXT** `mx._domainkey` → `"k=rsa; p=MIGfMA..."` (DNS only) — **Mailgun DKIM key; this
    is for OUTBOUND mail Mailgun sends. Confirm with Garrett whether any app sends via
    Mailgun before deleting.**
- Email Routing rules to add (after confirming Mailgun outbound status):
  - `email@garrettmanley.com` → `garrettmanley@gmail.com`
  - `urgent@garrettmanley.com` → `garrettmanley@gmail.com`
  - `kayla@garrettmanley.com` → `kayla.hughes.manley@gmail.com`
  - `garrett@garrettmanley.com` → `garrettmanley@gmail.com` (flatten the chain)
- Site redirect note: the apex A records point at Squarespace, which serves an HTTP 301 to
  github.com/GarrettManley. The redirect works via HTTP Host header, not DNS — so it
  continues working after NS swap AS LONG AS registration stays at Squarespace. Once we
  transfer registration (Phase 4), we need to replace this with a Cloudflare Bulk Redirect
  OR a static GitHub Pages redirect, OR let the apex go dark.
- NS at Squarespace still: `ns-cloud-c1-4.googledomains.com` (don't swap yet)

#### garrettmanley.dev (mail-only; broken→fixed)
- NS: Cloudflare-assigned
- MX / SPF / DKIM: Cloudflare Email Routing auto-adds (do NOT keep the Mailgun MX)
- Email Routing rules:
  - `guildmaster@garrettmanley.dev` → `garrettmanley+guildmaster@gmail.com`
  - `jobs@garrettmanley.dev` → `garrettmanley+jobs@gmail.com`
- **Critical: at Squarespace registrar, delete/clear any DS record for this domain** before
  changing NS — if a stale DS persists, DNSSEC chain stays broken even after CF takes over.
  Then let CF handle DNSSEC: CF → the zone → DNS → DNSSEC → enable → copy DS record →
  paste into Squarespace. (Only do DNSSEC after NS cutover is confirmed working.)

#### garrettmanley.com (live site + forwarders + redirect)
- NS: Cloudflare-assigned
- Apex A: `192.0.2.1` (or any IP), **orange-cloud proxied** so CF edge handles the
  redirect
- www: CNAME to `garrettmanley.com`, orange-cloud (so redirect also catches www/)
- MX / SPF: Cloudflare Email Routing auto-adds
- Bulk Redirect: `https://garrettmanley.com/*` → `https://github.com/GarrettManley/$1`, 301
- Email Routing rules:
  - `email@garrettmanley.com` → `garrettmanley@gmail.com`
  - `urgent@garrettmanley.com` → `garrettmanley@gmail.com`
  - `kayla@garrettmanley.com` → `kayla.hughes.manley@gmail.com`
  - `garrett@garrettmanley.com` → `garrettmanley@gmail.com` (flatten the chain — CF Email
    Routing doesn't do multi-hop; the old `garrett@ → email@` → gmail chain collapses to a
    direct send)
- Optional DMARC TXT at `_dmarc.garrettmanley.com`:
  `v=DMARC1; p=none; rua=mailto:garrettmanley+dmarc@gmail.com; fo=1` — observe first, tighten
  to `quarantine` after a week of clean reports.

## Per-domain DNS snapshots (Phase 1 source-of-truth)

> One section per domain. Paste `dig` output verbatim — this is the rollback artifact.

### Template — copy for each domain

```
Domain: <domain>
Captured: <ISO-8601 UTC timestamp>
Resolvers queried: 1.1.1.1, 8.8.8.8 (cross-check)

--- dig @1.1.1.1 <domain> ANY +noall +answer ---
<paste>

--- dig @1.1.1.1 <domain> MX +short ---
<paste>

--- dig @1.1.1.1 <domain> TXT +short ---
<paste>

--- dig @1.1.1.1 _dmarc.<domain> TXT +short ---
<paste>

--- dig @1.1.1.1 google._domainkey.<domain> TXT +short ---
<paste>
(If empty, check Google Admin → Apps → Google Workspace → Gmail → Authenticate email for
the actual DKIM selector, and re-query against <selector>._domainkey.<domain>.)

--- dig @1.1.1.1 <domain> NS +short ---
<paste>

Google Workspace specifics (from admin.google.com):
- Subscription owner: <Google direct | Squarespace-resold>
- DKIM selector: <google | custom>
- SPF record text: <paste>
- DMARC policy: <none | quarantine | reject>

Squarespace extras:
- Email forwarding rules: <list or "none">
- Apex record type: <A | ALIAS/ANAME | CNAME>
- Non-mail CNAMEs (www, subdomains, verification tokens): <list>
```

## Cutover log

> Append a timestamped entry per real action taken. Keep it terse — this is an audit trail.

| Timestamp (local MT) | Domain              | Action                                                    | Outcome |
|----------------------|---------------------|-----------------------------------------------------------|---------|
| 2026-11-10 ~09:30    | g.recipes           | Added as CF zone (Free), imported 1 CNAME                 | OK      |
| 2026-11-10 ~09:32    | garrettmanley.app   | Added as CF zone (Free), imported A+CNAME                 | OK      |
| 2026-11-10 ~09:33    | garrettmanley.app   | Deleted api A record (dead Azure IP)                      | OK      |
| 2026-11-10 ~09:34    | garrettmanley.dev   | Added as CF zone (Free), 0 records imported (SERVFAIL)    | OK      |
| 2026-11-10 ~09:35    | garrettmanley.com   | Added as CF zone (Free), imported 9 records (incl Mailgun, Bluesky) | OK |
| 2026-11-10 ~09:40    | garrettmanley.com   | Enabled Email Routing (not yet active — zone pending)     | Pending |
| 2026-11-10 ~09:42    | account             | Added 4 destinations: garrettmanley@gmail.com (verified), kayla.hughes.manley@gmail.com (pending), garrettmanley+guildmaster@gmail.com (pending), garrettmanley+jobs@gmail.com (pending) | Pending verifications |
| 2026-11-10 ~09:45    | garrettmanley.com   | Created 3 routing rules: email@, urgent@, garrett@ → garrettmanley@gmail.com (all Active) | OK |
| 2026-11-10 ~10:28    | account             | Verifications complete for +guildmaster and +jobs (Garrett); kayla still Pending | OK |
| 2026-11-10 ~10:29    | garrettmanley.dev   | Created 2 routing rules: guildmaster@, jobs@ → garrettmanley+alias@gmail.com (Active) | OK |
| 2026-11-10 ~10:45    | ALL                 | Discovered Squarespace-side DNS has records CF scan missed: Procell/Azure/Firebase/Fastly/Squarespace subdomains | Noted |
| 2026-11-10 ~10:55    | g.recipes, .app     | Confirmed: all Procell/Duracell/Google-verify records to be dropped (per Garrett) | OK |
| 2026-11-10 ~11:00    | garrettmanley.com   | Decisions: drop christmas / gmf-app-link / karaoke / Google-verify (dead); keep apex A + www CNAME (Squarespace edge handles GitHub redirect until Phase 4); keep _atproto Bluesky TXT | OK |
| 2026-11-10 ~11:00    | garrettmanley.dev   | Decisions: preserve Firebase wildcard + _acme-challenge TXT (live hosting); preserve Bluesky _atproto; git.garrettmanley.dev to be re-done as CF Bulk Redirect | OK |
| 2026-11-10 ~11:05    | garrettmanley.dev   | Added to CF zone: A `*` → 199.36.158.100 DNS-only; TXT `_acme-challenge` → bX9jRUBClBdaXSA96RfhXahJydv5kdnFWQrXpxmcDQM; TXT `_atproto` → did=did:plc:ptuxef3bhj6v3y6ihxexu2kl | OK |
| 2026-11-10 ~11:20    | g.recipes           | Squarespace NS → conrad+marge.ns.cloudflare.com; DNSSEC disabled by Squarespace | Submitted, SERVFAIL transient |
| 2026-11-10 ~11:21    | garrettmanley.app   | Squarespace NS → conrad+marge.ns.cloudflare.com; DNSSEC disabled by Squarespace | Submitted, SERVFAIL transient |
| 2026-11-10 ~12:40    | g.recipes           | NS propagated 1.1.1.1 + 8.8.8.8; SOA = conrad.ns.cloudflare.com | **Zone Active** at CF |
| 2026-11-10 ~12:40    | garrettmanley.app   | NS propagated 1.1.1.1 + 8.8.8.8; SOA = conrad.ns.cloudflare.com | **Zone Active** at CF |
| 2026-11-10 ~13:51    | garrettmanley.dev   | Squarespace NS → collins+miguel.ns.cloudflare.com; OAuth step-up required; no DNSSEC prompt (already in broken state → pre-existing SERVFAIL) | Submitted |
| 2026-11-10 ~13:54    | garrettmanley.com   | Squarespace NS → collins+miguel.ns.cloudflare.com; DNSSEC disabled by Squarespace; OAuth step-up skipped (session persisted); Mailgun MX+SPF+DKIM preserved in CF zone → zero-gap mail | Submitted |
| 2026-11-10 ~14:38    | garrettmanley.dev   | NS propagated instantly; CF zone **Active**; CF Email Routing enabled (MX x3, SPF, DKIM added) → guildmaster@ + jobs@ live | **Live** |
| 2026-11-10 ~14:38    | garrettmanley.com   | NS propagated instantly; CF zone **Active**; Mailgun MX x2 + SPF + DKIM deleted; CF Email Routing enabled (MX x3, SPF, DKIM added); brief (~2 min) mail window where sending MTAs queued on 4xx | **Live** |
| 2026-11-10 ~15:12    | garrettmanley.com   | Deleted `kayla.hughes.manley@gmail.com` destination (unused); added `_dmarc` TXT = `v=DMARC1; p=quarantine` | **Done** |
| 2026-11-10 ~15:12    | garrettmanley.dev   | Added `_dmarc` TXT = `v=DMARC1; p=quarantine`; added `git` A → 192.0.2.1 (Proxied, TEST-NET placeholder); CF Single Redirect Rule: `https://git.garrettmanley.dev/claude-marketplace` → `https://github.com/GarrettManley/claude-marketplace` (301). Verified end-to-end. | **Done** |
| 2026-11-10 ~19:00    | garrettmanley.com   | Added Resend sending subdomain for the jobs@ probe: TXT `resend._domainkey.probe` (DKIM), CNAME `rsend.probe` → `rsend.forge.rmta.net`, CNAME `send.probe` → `send.forge.rmta.net` (all DNS only). Resend domain `probe.garrettmanley.com` verified. | **Done** |
| 2026-11-10 ~20:03    | garrettmanley.dev   | `jobs@` verified end-to-end (Resend → CF Email Routing → Gmail, DKIM/DMARC/ARC pass, ~17-36 s). Weekly probe `Workspace/apps/mail-probe` registered as Task `mail-probe-weekly` (Mon 07:00 MT). Gmail filter `from:probe@probe.garrettmanley.com` = never spam + skip inbox (new-domain probe was spam-filtered despite auth pass). | **Done** |

## Current status (as of 2026-11-10 ~15:12 MT)

**Phase 3 (DNS cutover): COMPLETE for all 4 zones.** All active at CF, mail flowing via CF Email Routing on both .com and .dev. Zero known regressions.

Active Email Routing rules (5 total — kayla@ dropped as unused):
- `.com`: email@, urgent@, garrett@ → `garrettmanley@gmail.com`
- `.dev`: guildmaster@ → `garrettmanley+guildmaster@gmail.com`; jobs@ → `garrettmanley+jobs@gmail.com`

Other services preserved:
- Firebase wildcard hosting `*.garrettmanley.dev` → 199.36.158.100 (DNS-only)
- Bluesky handle verification `_atproto` TXT on both .com and .dev
- Squarespace site on `garrettmanley.com` (apex A + www CNAME, Proxied — proxied through CF)
- `_acme-challenge` TXT on .dev (wildcard cert)
- CF Single Redirect: `https://git.garrettmanley.dev/claude-marketplace` → `https://github.com/GarrettManley/claude-marketplace` (301, verified)

DMARC: `p=quarantine` on both .com and .dev (can tighten to `p=reject` after observation window).

## Pending validation (manual, 24–72h)

Before Phase 4 kicks off, validate the following in-use paths:

- [ ] **Mail round-trip (.com)**: send FROM an external account (not garrettmanley@gmail.com; Gmail suppresses self-loop) TO each of `email@`, `urgent@`, `garrett@garrettmanley.com`. Check Gmail "Show original" for `SPF=PASS`, `DKIM=PASS`, `DMARC=PASS`.
- [ ] **Mail round-trip (.dev)**: send FROM external TO `guildmaster@` and `jobs@garrettmanley.dev`. Check auth headers.
- [ ] **Firebase hosting**: visit a known `*.garrettmanley.dev` subdomain to confirm it still serves correctly (the wildcard A → 199.36.158.100 was preserved, but verify the cert chain isn't broken — `_acme-challenge` TXT was also preserved).
- [ ] **Squarespace site**: visit `https://garrettmanley.com` — should still render the Squarespace page (apex A x2 are Proxied through CF to Squarespace edge).
- [ ] **Bluesky handle**: in the Bluesky app, verify the `@garrettmanley.com` / `@garrettmanley.dev` handles still resolve (`_atproto` TXT was preserved on both).
- [ ] **GitHub redirect**: browser-visit `https://git.garrettmanley.dev/claude-marketplace` → should end on `github.com/GarrettManley/claude-marketplace`. (Verified via curl at 15:12.)
- [ ] **Old Squarespace apex redirect** (if any): did the old Squarespace apex URL-forward `garrettmanley.com` → `github.com/GarrettManley` need re-creating under CF? Currently NOT set up — only Squarespace site serves on the apex. If Garrett wants that back, add a Single Redirect Rule for `https://garrettmanley.com/*` → `https://github.com/GarrettManley$1` or similar.

If any of the above fails, catch it here before Phase 4 — Squarespace still holds the registration, so DNS can be rolled back by swapping NS back to `ns-cloud-c*.googledomains.com` (zones at Google Cloud DNS were untouched during migration).

## Phase 4 — Registrar transfer (Squarespace → CF)

**On hold.** Kick off once validation above is clean.

Pre-flight at Squarespace for each domain:
1. **Unlock the domain** (Squarespace → `<domain>` → Overview → disable "Transfer Lock")
2. **Turn OFF auto-renew** (prevents Squarespace charging you while transfer is in flight)
3. **Verify WHOIS email** is current (`garrettmanley@gmail.com` — it is). Squarespace privacy may rewrite the registrant email; temporarily disable privacy if the auth-code email never arrives.
4. **Request EPP / Authorization Code** — Squarespace either emails it or shows inline.

At Cloudflare for each domain:
5. CF Dashboard → Registrar → Transfer Domains → paste domain + auth code → pay one-year renewal (at-cost; no markup).
6. Approve the ICANN change-of-registrar email at the WHOIS registrant address (`garrettmanley@gmail.com`).
7. Transfer completes in ~5 days (ICANN waiting period). Expiration extends by one year.
8. DNS impact: **none** — NS already points at CF.

Post-transfer cleanup:
9. Re-enable Registrar Lock at CF (CF enables by default).
10. Confirm WHOIS redaction is on (CF free by default).
11. (Optional) Re-enable DNSSEC at CF side + add DS record to the TLD (CF Registrar does this automatically since it now controls both ends; Squarespace required us to disable DNSSEC for the NS swap).

Ordering recommendation: do parked zones (g.recipes, .app) first — zero consequence if anything hiccups. Then .dev. Save .com for last (live mail + Bluesky + Squarespace site).

Expected savings:
- `.recipes` — roughly $72/yr → ~$30-35/yr at CF (Identity Digital TLD, no markup)
- `.app`, `.dev`, `.com` — a few $/yr each vs. Squarespace retail.

## Known artifacts to clean up later (low priority)

- `_domainconnect.garrettmanley.com` CNAME → `_domainconnect.domains.squarespace.com` (Proxied). This supports Squarespace's auto-config UI; harmless to leave until we fully leave Squarespace. Delete during/after Phase 4 cleanup.
- `_domainconnect.garrettmanley.app` CNAME (same — harmless on parked zone).
- DNSSEC re-enable (optional): CF offers free DNSSEC post-Phase 4.

## Full per-zone CF record state (Phase 2 target)

### g.recipes CF zone — ready for NS swap
Current: `_domainconnect` CNAME (Squarespace, harmless)
Nothing to add or delete. NS swap will drop all Squarespace-side records (procell.api A, Google verification CNAME, asuid TXT) which is desired.

### garrettmanley.app CF zone — ready for NS swap
Current: `_domainconnect` CNAME (api A was deleted)
Nothing to add or delete. NS swap will drop Squarespace-side Procell records (api A, test.api CNAME, Google verification CNAME, 2 asuid TXT) which is desired.

### garrettmanley.dev CF zone — ready for NS swap (pending git redirect)
Current: `*` A → 199.36.158.100 (DNS-only Firebase), `_acme-challenge` TXT, `_atproto` TXT
Add before NS swap: CF redirect for `git.garrettmanley.dev` — resolved 15:12 as a Single Redirect Rule `https://git.garrettmanley.dev/claude-marketplace` → `https://github.com/GarrettManley/claude-marketplace` (301; see log row above)
After NS swap (zone Active): enable CF Email Routing (adds MX + SPF + DKIM auto)
Also: at Squarespace registrar → DNSSEC → clear any DS record

### garrettmanley.com CF zone — ready for NS swap after CF Email Routing MX is enabled
Current (from scan): 2 apex A (Squarespace), 2 CNAME (www + _domainconnect), 2 Mailgun MX, Mailgun SPF TXT, Mailgun DKIM TXT (mx._domainkey), Bluesky _atproto TXT
Keep: apex A x2, www CNAME, _domainconnect CNAME, _atproto TXT
Do nothing before NS swap to preserve mail flow via Mailgun MX
After NS swap (zone Active):
  1. Enable CF Email Routing (adds route1/2/3.mx.cloudflare.net MX at prio 36/88/41 + SPF + DKIM `cf2024-1._domainkey`)
  2. Delete Mailgun MX x2 (mxa, mxb.mailgun.org prio 10)
  3. Delete Mailgun SPF TXT (`v=spf1 include:mailgun.org ~all`) — or merge into CF's SPF if we want both (we don't; Mailgun inbound-only)
  4. Delete Mailgun DKIM TXT (`mx._domainkey`)
Note: GitHub redirect via Squarespace apex IP keeps working through NS swap AND Phase 4 registrar transfer (as long as domain stays with Squarespace OR we set up CF Bulk Redirect before transfer).

## Ready for Phase 3 (NS swap)

5 of 6 rules are Active. Mail currently still flows via Mailgun (nothing changed in production).
Email Routing MX records are NOT yet in the CF zones (CF blocks that step until the zone is
Active, which happens only after NS swap).

Phase 3 plan:
1. **Find the DNS editor** — zones are hosted on `ns-cloud-*.googledomains.com` (legacy Google
   Domains → Squarespace infra). Check Squarespace → Domains → `<domain>` → Advanced →
   DNS. If not editable there, check console.cloud.google.com → Network services → Cloud DNS
   under any Google Cloud project Garrett owns.
2. **Lower TTLs** on all records to 300s. Wait ≥4h for the old 14400s TTL to expire
   globally.
3. **NS swap in order**: g.recipes → garrettmanley.app → garrettmanley.dev → garrettmanley.com
4. For `.dev`: **also clear any DS record** at Squarespace registrar settings before/during
   NS swap. This fixes the SERVFAIL side-effect.
5. Wait for each zone to go **Active** in Cloudflare (minutes to hours).
6. For `.com` and `.dev`: click **Add missing records** on Email Routing → Settings → DNS
   records. This adds CF's MX, SPF, DKIM records.
7. For `.com`: delete the Mailgun records (2 MX, 1 SPF, 1 DKIM). Preserve Bluesky
   _atproto TXT, Squarespace apex A and www CNAME (redirect still served by Squarespace),
   Squarespace _domainconnect CNAME.
8. Verify mail: send test to each forwarded address; confirm arrival at Gmail.

## Rollback notes

If mail flow regresses after an NS swap:
1. At Squarespace, revert the domain's nameservers to the previously recorded values (in the
   per-domain Phase 1 snapshot above — Squarespace was `ns-cloud-*.googledomains.com` or
   Squarespace's own NS; capture the actual values before swapping).
2. Previous TTLs were lowered to 300s in Phase 2, so global propagation back should happen
   within 5–10 minutes at most resolvers.
3. Confirm with `dig @1.1.1.1 <domain> NS +short` and a round-trip test email.
4. Do NOT proceed with any registrar transfer until root cause is understood and the DNS
   mirror has been corrected.

## 2026-11-10 — garrettmanley.dev lab moved from Firebase to Cloudflare Workers

- Worker `garrettmanley-lab` (Static Assets, `site/wrangler.jsonc`) attached as the apex custom domain.
  Deploys run from `publish.ps1`: Hugo build → `scrub-check` privacy gate → `wrangler deploy` with the
  token from the Hello-gated 1Password `Deploy` vault (`site/.env.tpl`).
- Deleted: `*` A 199.36.158.100 (Firebase wildcard) and `_acme-challenge` TXT (Firebase cert). `www` and
  other subdomains now NXDOMAIN; `git.` (proxied, redirect to GitHub) untouched; mail records untouched.
- Verified (DoH): apex, `/hire/`, `/docs/` 200; unknown path 404; `git.…/claude-marketplace` 301 → GitHub.
- Firebase hosting site `garrettmanley-lab` still live at its web.app URL until Phase 3 (redirect + key revoke).

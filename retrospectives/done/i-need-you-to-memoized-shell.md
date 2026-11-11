# Retrospective: jobs@garrettmanley.dev restore check + weekly end-to-end probe

**Plan:** `~/.claude/plans/i-need-you-to-memoized-shell.md`
**Commit:** `1f9db50` (`feat(mail-probe): weekly end-to-end probe for the jobs@ forwarding address`)
**Date:** 2026-11-10

## Outcome

The resume address `jobs@garrettmanley.dev` is confirmed working after the Cloudflare migration.
`apps/mail-probe` runs every Monday at 07:00 as Task `mail-probe-weekly`. Each run:
- checks the DNS records on Cloudflare's and Google's public resolvers;
- sends a test message through Resend from the verified subdomain `probe.garrettmanley.com`;
- confirms over Gmail IMAP that it arrived, with landing in spam treated as a separate failure;
- writes a result JSON that the stewardship morning briefing shows in a new Health Checks section
  (claude-marketplace #65, stewardship 1.5.0);
- on failure, sends an alert email and shows a Windows notification.

The work grew past the plan. It produced a machine-wide **1Password secrets layer**: an `Automation` vault,
`.env.tpl` references, `~/scripts/lib/Secrets.psm1`, a read-only service account picked automatically
under agents, and a shell guard that blocks commands which would expose a secret. A full secrets audit
followed. The unencrypted SSH key was rotated into 1Password, aether's Google OAuth secret moved to the
vault, and GitHub git auth moved to HTTPS via the `gh` token.

## What worked

- **Read-only diagnosis before any change.** DNS on two resolvers plus a Gmail search for real inbound
  mail (a recruiter email reached the inbox) proved the address worked in minutes, before any code existed.
- **Asking at real decision points** (test depth, sender, alerting, secret store, git auth) kept
  scope aligned. Each answer changed the design materially.
- **Pure core with adapters as seams** (`checks.py` holds the logic, `probe.run` takes injected `Deps`).
  The DNS, send and IMAP layers all changed mid-flight (keyring → env vars, Mailgun → Resend) without
  touching tests. 21 unit/flow tests, no network.
- **Printing only the shape of a secret.** Every check (length, prefix, equality with the source)
  ran inside `op run`, so no secret value ever entered the transcript.
- **Live failure-path runs.** Running with a bad key, alerts on, and a real scheduled-task trigger caught
  things unit tests couldn't: Gmail spam-filing a new domain, the wrapper's environment, Task Scheduler context.
- **A background agent for the separate-repo PR** (the briefing section) ran in parallel with the
  Resend/DNS setup and cost nothing on the critical path.

## Friction / bugs

- **The plan assumed a Mailgun account**
  - *What happened:* the plan's sender was "the existing Mailgun account". The user had none.
  - *Root cause:* I read Mailgun MX/SPF/DKIM records in DNS as the user's account. They were Google Domains'
    and then Squarespace's hidden forwarding backend.
  - *How caught:* the user rejected the plan.
  - *Fix:* switched to Resend on a dedicated subdomain.
  - *Rule:* DNS records name a provider, not an account owner. Ask before planning around a third-party account.

- **Positional parameter swallowed the command**
  - *What happened:* `Invoke-WithSecrets -- pwsh ...` failed: `pwsh` was bound to `-EnvFile`.
  - *Root cause:* PowerShell consumes `--` and binds remaining words positionally unless
    `PositionalBinding = $false` is set.
  - *How caught:* the first real use. No test exercised argument pass-through.
  - *Fix:* `PositionalBinding = $false`, plus a Pester test that mocks `op` and asserts the exact argv.
  - *Rule:* any wrapper that forwards a command needs a pass-through test with a mocked executable.

- **`& op @(...)` passes a single array argument**
  - *What happened:* the new test failed with `System.Object[]`.
  - *Root cause:* splatting an array *expression* passes one argument to a function or mock. Native
    executables flatten it, which hid the bug in real use.
  - *Fix:* splat a variable (`$opArgs = ...; & op @opArgs`).

- **uv-managed Python couldn't verify TLS**
  - *What happened:* DoH queries failed with `CERTIFICATE_VERIFY_FAILED`.
  - *Root cause:* uv's bundled CPython doesn't read the Windows certificate store.
  - *Fix:* `truststore.inject_into_ssl()` in the package `__init__`.

- **Gmail spam-filed the probe even though authentication passed**
  - *What happened:* the first live run returned `spam`, with DKIM/DMARC/ARC all passing.
  - *Root cause:* a domain created an hour earlier plus a short hex-subject message trips content and
    reputation heuristics.
  - *How caught:* the probe's distinct spam outcome, then IMAP header inspection (the Gmail
    connector hides Spam).
  - *Fix:* a Gmail filter on the probe sender set to never spam and skip the inbox. The probe now tests
    the forward path, not per-sender spam reputation.

- **Desktop-app auth prompted on every agent tool call**
  - *What happened:* the user was asked to approve 1Password for every command, first for `op` and then
    for the SSH agent, even with per-application approval remembered and 1Password restarted.
  - *Root cause:* each agent tool call is a new process tree, and 1Password scopes approval to that tree.
  - *Fix:* `op` uses the read-only service account automatically when `CLAUDECODE=1`. GitHub git auth
    moved to HTTPS via the `gh` keyring token.
  - *Rule:* anything an agent calls repeatedly must authenticate with a non-interactive credential.
    Interactive approval is for humans only.

- **Audit false positives**
  - *What happened:* the audit reported 50 "secret-shaped" transcript matches. An exact-format rescan
    found none real (for example `sk-` matched inside "risk-").
  - *Rule:* rescan audit hits with exact token formats before proposing redaction.

- **Concurrent session stashed my files**
  - *What happened:* an aether session stashed my uncommitted `.env.tpl` and `registry.ts` hint along
    with its own WIP before a push.
  - *Fix:* left the stash intact and left a note in Roleplaying's `remember.md` plus a cross-session message.
  - *Rule:* commit cross-repo changes promptly, or tell the owning session, when other sessions are live
    in that repo.

## Concrete improvements

- **Secrets playbook in `~/AGENTS.md`**: loaded by every session under `~`. Done (`c992eb9`, `71aafbb`).
- **Secret-exposure shell guard** (`~/.claude/hooks/check_secret_exposure.py`, 23 tests): done, active
  after a Claude Code restart.
- **Agent-default service-account auth** in `Secrets.psm1` (`88a776a`): done.
- **`.remember/` pruned from `pre_commit_audit.ps1`**: done (in `1f9db50`). Auto-written memory notes
  had been tripping the TBD check.
- **Restore aether `stash@{0}`**: follow-up for the aether session. Until then `npm start` lacks the
  Google OAuth values.

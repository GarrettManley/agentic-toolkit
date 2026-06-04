---
title: "Auth Troubleshooting"
weight: 60
---

Problems connecting to a **locally-running** engine with the `aether-cli`, and what to do
about each.

> **Local play today.** The transport is being rebuilt (spec 043, #138): the old SSH +
> Google-sign-in flow is retired. Remote sign-in and its error cases are being rebuilt
> (#138/#139) — see [Remote sign-in (coming)](#remote-sign-in-coming). Everything else
> here is for local play.

## "Connection refused" / the CLI can't reach the gateway

**What's happening.** The engine isn't running, or the CLI is pointed at the wrong port.

**What to do.**

1. Make sure the gateway is running in another terminal (`npm start`). It prints the
   port it's listening on when ready.
2. The default is `443`; if `443` was taken it falls back to `8443`. Point the CLI at it:
   `--server https://localhost:8443`.
3. If the engine failed to bind the port, free it with `npx ts-node src/maintenance.ts`
   and start again.

## TLS / "self-signed certificate" error

**What's happening.** The gateway uses a self-signed development certificate, which your
client won't trust by default.

**What to do.** On `localhost`, add `--insecure` to accept it, or `--ca <gateway-cert.pem>`
to *verify* it. The CLI refuses `--insecure` against any non-loopback host (that would
remove MITM protection).

## "Unauthenticated" / access denied on localhost

**What's happening.** The loopback bypass isn't active, so the gateway is demanding a
token you don't have locally.

**What to do.** Start the gateway with `npm start` (it sets `AETHER_EXPOSE_LOOPBACK=1`),
and connect from `localhost` / `127.0.0.1`. If you launched the engine another way, set
that environment variable before starting it.

## "Character not found" / "Awaiting character creation"

**What's happening.** There's no `universe/characters/<name>.json` matching the name you
passed.

**What to do.** Check spelling and case (names are case-sensitive). Ask the GM to create
the character file, or connect and run `/session0` to create the character.

## The stream closes immediately, or the DM never responds

**What's happening.** The engine hit an error after you connected.

**What to do.** Check the **engine terminal**. Common causes:

- The model backend isn't running — Ollama not started or its models not pulled (see
  [Your First Campaign](/aether/tutorial-first-campaign/), Step 3).
- The Rust core isn't built — run `cargo build --release` under `core/`.
- A network error reaching Gemini (if you're on the Gemini provider).

## "Rate limited"

**What's happening.** The brute-force filter is rate-limiting repeated connection
attempts (default: 20 per 60 seconds).

**What to do.** Wait 60 seconds and retry. If you were retrying in a loop because of a
config problem, fix the config first—each attempt counts.

## Remote sign-in (coming)

Connecting from **another machine** uses a Google OIDC sign-in. That flow—and its error
cases (the "app isn't verified" warning, link-token expiry, CSRF on return from Google,
character-ownership 403s, token-exchange failures)—is being rebuilt as part of transport
v2 (#138) and the remote sign-in handoff (#139). This section will be restored when
remote play ships.

## Related docs

- [Player onboarding](/aether/player-onboarding/)—the happy path
- [Player Manual](/aether/player-manual/)
- [Playing via the CLI](/aether/aether-cli/)


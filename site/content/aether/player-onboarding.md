---
title: "Player Onboarding"
weight: 10
---

Welcome. This tutorial walks you through connecting to a locally-running Aether
Engine with the `aether-cli` and seeing your first game prompt. By the end you'll
have the engine running, connected as your character, and typed your first action.

> **Local play today.** Aether's transport is being rebuilt (spec 043). The
> old "SSH into a public server + Google sign-in" flow has been retired. What works
> now is **local play** — the engine and the CLI on the same machine, over the
> loopback bypass. **Remote multiplayer** (sign-in from another machine) is coming;
> see [Remote multiplayer](#remote-multiplayer-coming) at the end.

## What you need

- The **Aether repo** checked out, with `npm install` run once. The engine and the
  CLI both live here (`packages/aether-cli`).
- The engine's **model backend** available — Ollama by default (`npm start`); see
  [Your First Campaign](/aether/tutorial-first-campaign/) for the one-time setup.
- The **character name** you want to play. Example: `gurga`, `korrin`, `valen`.
  Case matters—use the exact string from the character's JSON file.

No SSH client and no Google sign-in are needed for local play.

## Step 1—Start the engine

In a terminal at the repo root, start the gateway:

```bash
npm start
```

This boots the HTTPS Connect-RPC gateway on `localhost` with the **loopback bypass**
enabled (`AETHER_EXPOSE_LOOPBACK=1`) and the Ollama provider. Leave it running; it
prints a line when it's listening (default port `443`, or `8443` if `443` is taken).

## Step 2—Connect with the CLI

In a **second** terminal, also at the repo root:

```bash
npm run play -w @garrettmanley/aether-cli -- <your-character> --insecure
```

(equivalently: `npx ts-node packages/aether-cli/src/cli.ts play <your-character> --insecure`)

- On `localhost` the **loopback bypass authenticates you automatically**—there is no
  Google sign-in and no token to paste.
- `--insecure` accepts the gateway's **self-signed dev certificate** (localhost only;
  the CLI refuses `--insecure` against any non-loopback host). To *verify* the cert
  instead, point `--ca <gateway-cert.pem>` at the gateway's certificate.
- If the gateway is on a non-default port, add `--server https://localhost:8443`.

## Step 3—Play

On success you'll see something like:

```text
Connected as gurga · session 1f9c… · server <version>
Slash commands: /help  /gm  /accept  …
Type to act; lines beginning with "/" are slash commands. Ctrl-D to quit.
```

Type naturally—the engine interprets your actions and streams back the scene. Lines
beginning with `/` are **slash commands** (the available set is listed on connect).
Press **Ctrl-D** to quit.

## What happened behind the scenes

- The CLI is **presentation-only**: it transmits your typed input and renders the
  events the engine streams back. All game logic lives in the engine.
- On `localhost`, the loopback bypass grants access without a token. Character
  **ownership and claiming** (binding a character to an identity) applies to remote
  sign-in, which is part of the flow being rebuilt—see below.
- If you disconnect and reconnect, the CLI **resumes where you left off**: it records
  the last event it saw per character (`~/.config/aether/state.json`) and replays
  anything you missed from the engine's per-session buffer.

## Remote multiplayer (coming)

Playing from **another machine**—with Google sign-in and an installed
`@garrettmanley/aether-cli`—is being rebuilt as part of transport v2 and the
remote sign-in handoff. Until it ships, play is **local** (same machine as the
engine). When remote lands, this section will document the sign-in and connection
flow (and how a character is claimed by a Google account).

## Troubleshooting

See [auth-troubleshooting.md](/aether/auth-troubleshooting/) for connection and sign-in
errors.

## Related docs

- [Player Manual](/aether/player-manual/)—once you're in, how to play.
- [Your First Campaign](/aether/tutorial-first-campaign/)—a walkthrough of the early game,
  including the one-time engine setup.
- [Playing via the CLI](/aether/aether-cli/)—the CLI client in more depth.


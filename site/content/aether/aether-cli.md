---
title: "Playing via the CLI"
weight: 50
---

## 1. Orientation

This guide is for the **player** — the person at a keyboard, connecting to a running
Aether engine and playing a session. It is not for the **engine operator** who runs
`npm start`, or the **GM** running the game (see [`gm-manual.md`](/aether/gm-manual/)). The CLI
is presentation-only: it transmits your typed commands and renders the events the engine
streams back. Reference: spec 043 (#138).

> **Local play today.** The CLI connects to a **locally-running** engine over the loopback
> bypass — no sign-in. Connecting from another machine (install + Google sign-in) is being
> rebuilt (#138, #139); the `login` command below is a placeholder until it ships.

## 2. Concepts

| Term | Definition |
|---|---|
| **`aether-cli`** | The Connect-RPC client. Thin presentation layer; no engine logic lives here. It lives in the workspace at `packages/aether-cli` (not yet published to a registry). |
| **Loopback bypass** | On `localhost`, the gateway authenticates you automatically (no token), when started with `AETHER_EXPOSE_LOOPBACK=1` — which `npm start` sets. |
| **Session resume** | If the CLI disconnects mid-play, reconnecting replays the events you missed, in order, up to the server's ring-buffer capacity (default 1000). The CLI records the last event it saw per character at `~/.config/aether/state.json`. |
| **Slash command** | Out-of-character commands prefixed with `/`. The server publishes the catalog on connect; the CLI prints it, and `/help` lists it in-session. |
| **Bearer token / identity-key** *(remote, coming)* | For remote play, a token issued after Google sign-in authenticates you and binds a character to your identity. Not used on the loopback path. |

This version prints events as plain text and reads stdin lines as commands. Rich
rendering — an Ink-based UI, slash autocomplete, animated spinners — lands in slice 3.

## 3. Workflow (local)

1. **Start the engine** (operator). In one terminal at the repo root:

   ```bash
   npm start
   ```

   This boots the HTTPS Connect-RPC gateway on `localhost` with the loopback bypass.

2. **Connect to play a character.** In a second terminal:

   ```bash
   npm run play -w @garrettmanley/aether-cli -- <character> --insecure
   # equivalently:
   npx ts-node packages/aether-cli/src/cli.ts play <character> --insecure
   ```

   On `localhost` there is no sign-in. `--insecure` accepts the gateway's self-signed dev
   cert (localhost only; use `--ca <gateway-cert.pem>` to verify it instead). Add
   `--server https://localhost:8443` if the gateway isn't on `443`.

3. **Play.** Your typed lines are sent as `PlayerInput`; the engine cycles through intent
   classification, mechanical resolution, and prose generation; the resulting events
   stream back. Slash commands work too — `/session0`, `/roll`, `/gm`, etc.

4. **Reconnect after a drop.** Re-run the same command. The CLI replays missed events
   from your last seen sequence (`~/.config/aether/state.json`).

> **Remote login** (`aether login`) is a placeholder that prints how to play locally —
> the OIDC sign-in it will drive is pending #139.

## 4. Examples

### 4.1 Connecting

```text
$ npm run play -w @garrettmanley/aether-cli -- Sylvanwen --insecure
WARNING: --insecure disables TLS verification (loopback dev only).
Connected as Sylvanwen · session 1f9c… · server <version>
Slash commands: /session0  /roll  /gm  /accept  …
Type to act; lines beginning with "/" are slash commands. Ctrl-D to quit.
```

### 4.2 Playing through a session

**Input.** At the prompt you type:

```text
I cast Wild Shape and become a brown bear, then charge the goblin.
```

**Output.**

```text
[SYSTEM] Reading your intent...
[SYSTEM] Composing the scene...
[NARRATIVE] You feel your shape shift, fur sprouting along your arms,
your hands becoming clawed paws. The goblin looks up just as you barrel
toward it on all fours.
[STATUS_BAR] Sylvanwen (Brown Bear, HP 34/34) — Goblin's turn next.
```

`[SYSTEM]` lines are progress markers, `[NARRATIVE]` is the engine's prose, and
`[STATUS_BAR]` is the status line (plain text in this version; richer rendering in slice 3).

### 4.3 Reconnecting after a drop

Re-run `play`; the CLI resumes from where it left off:

```text
[RESUME_GAP] ...        # only if more events elapsed than the buffer holds
[NARRATIVE] The goblin lunges at the bear with its scimitar...
[STATUS_BAR] Sylvanwen (Brown Bear, HP 28/34) — your turn.
```

Events that fell out of the ring buffer are recoverable only from the campaign's ledger.

## 5. Pitfalls

- **SSH no longer works.** As of spec 043 the SSH gateway is removed; `ssh <character>@host`
  returns connection-refused. Use `aether play <character>`.
- **`--insecure` is localhost-only.** It disables TLS verification; the CLI refuses it for
  any non-loopback host. For a real cert, pass `--ca <gateway-cert.pem>`.
- **Don't run two CLIs for the same character at once.** `MessageBus` scopes (`LOCAL`,
  `BLIND`) target a single session at a time; two clients fragment your event stream. To
  spectate from elsewhere, ask the GM for god-view delegation.
- **The audit log is a feature.** Every connection, command, and disconnect is logged to
  `logs/overseer.jsonl` server-side — your evidence that an action attributed to you was
  actually you.

## 6. Reference: command summary

| Command | Effect |
|---|---|
| `aether play <character> [--server <url>] [--ca <cert.pem>] [--insecure] [--token <bearer>]` | Connect and play. On `localhost` the loopback bypass authenticates you; resumes from the per-character cursor. |
| `aether login` | Remote OIDC sign-in — **pending #139** (currently prints local-play guidance). |

Until the package is published, run the CLI from the workspace:
`npm run play -w @garrettmanley/aether-cli -- …` or
`npx ts-node packages/aether-cli/src/cli.ts …`. In-game slash commands are a server-side
surface — type `/help` in-session to see what your role can invoke.

## 7. References

- Spec 043: transport v2 — design.
- Runbook: transport v2 operations — engine operator's MOP.
- [Player manual](/aether/player-manual/) — in-game commands and gameplay (transport-agnostic).
- [Player onboarding](/aether/player-onboarding/) — first-time orientation.
- [GM manual](/aether/gm-manual/) — for the person running the game.
- ADR-0010 — why the transport changed.
- #138 — tracking issue.


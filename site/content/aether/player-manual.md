---
title: "Player Manual"
weight: 40
---

This manual covers everything you need to play a campaign with the `aether-cli`:
connecting, creating your character, taking actions, interpreting dice results, and
troubleshooting common problems.

> **Local play today.** The transport is being rebuilt (spec 043): the old SSH +
> Google-sign-in flow is retired. What works now is **local** play via the `aether-cli`
> over the loopback bypass. **Remote multiplayer** is coming — see
> [Player onboarding](/aether/player-onboarding/#remote-multiplayer-coming).

---

## Connecting

Start the engine in one terminal, then connect with the CLI from a second:

```bash
npm start                                                            # terminal 1: loopback gateway
npm run play -w @garrettmanley/aether-cli -- <character> --insecure  # terminal 2
```

On `localhost` the loopback bypass authenticates you automatically—there is no Google
sign-in. `--insecure` accepts the gateway's self-signed dev certificate (localhost only;
use `--ca <gateway-cert.pem>` to verify it instead). If the gateway isn't on the default
port, add `--server https://localhost:8443`.

First-time players should read [player-onboarding.md](/aether/player-onboarding/) first.
Connection problems are listed in [auth-troubleshooting.md](/aether/auth-troubleshooting/).
**Remote players** (another machine, Google sign-in) are coming with #138/#139.

---

## Character creation

Type `/session0` at any time to start the character creation flow. The
engine walks you through name, race, class, and background. You only
need to complete Session 0 once per character.

Your status bar appears on completion:

```text
╔══════════════════════════════════════╗
║             KIRA                     ║
║  HP: 10/10 | AC: 12                  ║
╚══════════════════════════════════════╝
```

---

## Taking actions

Type a natural-language description of what your character does. The
Dungeon Master classifies your intent, checks whether a die roll is
needed, and narrates the outcome.

**Examples:**

```text
I draw my sword and attack the skeleton.
I try to pick the lock on the chest.
I whisper to the innkeeper asking about recent visitors.
I look up at the ceiling to check for signs of a trap door.
```

Avoid bare numbers—typing `1` or `3` does not select a menu option.
Describe what your character does instead.

---

## Skill checks and dice

When your action requires a die roll, the Dungeon Master proposes the
appropriate check:

```text
That sounds like a Stealth check—want to roll it?
```

**Responding to a proposed roll:**

| Response | Effect |
| --- | --- |
| `yes` or `y` | Accept the proposed skill check |
| `no` or `n` | Decline—the DM narrates a hold-back |
| `roll stealth` | Accept but override to a specific skill |

If you decline, the DM narrates that your character holds back or
redirects. No mechanical outcome is recorded.

---

## Rolling dice directly

Use `/roll` to roll a die immediately without a narrative context:

```bash
/roll        # roll a d20
/roll 8      # roll a d8
```

The result displays immediately. The DM narrates a brief outcome.

---

## Commands

| Command | Effect |
| --- | --- |
| `/session0` | Start character creation |
| `/roll [sides]` | Roll a die (default: d20) |

The CLI lists the full set available to your role on connect, and `/help`
prints it in-session.

---

## Visibility scopes

Not all messages reach every player. The Dungeon Master routes output
through visibility scopes:

| Scope | You see it if… |
| --- | --- |
| `GLOBAL` | You are an approved session |
| `LOCAL` | The message was addressed to you |
| `BLIND` | You are the target, a GM, or a God-View observer. Other players see a generic notice. |
| `GM` | You have GM privileges (`/gm` on a localhost session) |

---

## Troubleshooting

**"Awaiting character creation"—I already made a character.**
Your character file may not exist at `universe/characters/<name>.json`.
Ask your GM to verify the file or start a new Session 0.

**The DM's response takes a long time.**
You will see "The Dungeon Master is thinking..." while the LLM
generates. This is normal. If it stalls for more than 30 seconds,
the engine may have hit a network error. Check the server terminal
for errors.

**"It is X's turn—wait for your turn to act."**
You are in an active combat encounter. Wait until the Dungeon Master
announces your character's name before submitting an action.

**My action was rejected with "describe what your character does."**
You typed a bare number. Describe your action in words instead.

---

## Related documentation

- [First-time onboarding](/aether/player-onboarding/)
- [Auth troubleshooting](/aether/auth-troubleshooting/)
- [Tutorial: Your First Campaign](/aether/tutorial-first-campaign/)
- [Playing via the CLI](/aether/aether-cli/)
- [GM Manual](/aether/gm-manual/)
- Glossary


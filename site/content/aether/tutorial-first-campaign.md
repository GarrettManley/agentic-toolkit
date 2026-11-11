---
title: "Tutorial: Your First Campaign"
weight: 30
---

This tutorial walks you from a fresh clone to your first turn in about 15 minutes. By
the end you will have a running engine, a new character, and your first narrative
exchange with the Dungeon Master.

> **Local play today.** The transport is being rebuilt (spec 043): the old SSH +
> Google-sign-in flow is retired. This tutorial covers **local** play via the
> `aether-cli` over the loopback bypass. **Remote multiplayer** is coming — see
> [Player onboarding](/aether/player-onboarding/#remote-multiplayer-coming).

**Prerequisites:**

- Git
- Node.js 20 or later
- Rust toolchain—install from [rustup.rs](https://rustup.rs)
- Either a Gemini API key **or** a local `llama-server` instance (see Step 3;
  setup: docs/runbooks/llamacpp-phase1-setup.md)

---

## Step 1: Clone and install

```bash
git clone <your-aether-remote> aether
cd aether
npm install
```

`npm install` also wires the workspace packages, including `@garrettmanley/aether-cli`.

---

## Step 2: Build the Rust core

The TypeScript layer executes a compiled Rust binary. Build it once
now, and again any time you change files under `core/src/`.

```bash
cd core && cargo build --release && cd ..
```

The binary lands at `core/target/release/core.exe` (Windows) or
`core/target/release/core` (Linux/macOS).

---

## Step 3: Configure an LLM provider

### Option A—Gemini API (cloud)

Set your API key in the shell before starting the engine:

```bash
export GEMINI_API_KEY=your-key-here
```

### Option B—llama-server (local, no API key)

Follow docs/runbooks/llamacpp-phase1-setup.md to
install and start `llama-server`—it's the single source for install steps, the model to
load, and the port to use, so this tutorial doesn't restate specifics that can drift out
of sync with it. By default one local `llama-server` instance serves both the classifier
and prose roles (ADR-0013).

---

## Step 4: Start the engine

```bash
# Gemini provider
npm run start:gemini

# llama-server provider (default)
npm start
```

`npm start` boots the HTTPS Connect-RPC gateway on `localhost` with the loopback bypass
enabled. You will see the campaign initialize and the gateway report it is listening:

```text
Campaign [aether_frontier] initialized. Loading Universe Lore...
[Aether] HTTPS gateway listening on port 443
```

Leave this terminal running.

---

## Step 5: Connect with the CLI

Open a **second** terminal. `kira` doesn't have a character file yet, so connect with
`--create` to open the Session-0 wizard over the wire:

```bash
npm run play -w @garrettmanley/aether-cli -- kira --insecure --create
```

The first positional argument (`kira`) is the character name. On `localhost` the
loopback bypass authenticates you automatically—no browser, no Google sign-in. The
`--insecure` flag accepts the gateway's self-signed dev certificate (localhost only;
use `--ca <gateway-cert.pem>` to verify it instead).

> Connecting from **another machine** (with Google sign-in) is being rebuilt as part of
> transport v2; until it ships, play is local.

---

## Step 6: Create your character

The wizard opens immediately and greets you by name:

```text
Greetings, kira. What is your class? (e.g., Warrior, Mage, Rogue)
```

Answer each prompt—class, ability scores, then inventory. Character creation takes
about two minutes. See [character-creation.md](/aether/character-creation/) for the
narrative-identity fields (personality, backstory, bonds) that make your character
come alive in prose; the wizard covers the mechanical fields.

When it completes, your status bar appears:

```text
╔══════════════════════════════════════╗
║             KIRA                     ║
║  HP: 10/10 | AC: 12                  ║
╚══════════════════════════════════════╝
```

Reconnect without `--create` for every session after this one:

```bash
npm run play -w @garrettmanley/aether-cli -- kira --insecure
```

---

## Step 7: Take your first action

Type a natural-language description of what your character does:

```text
I look around the tavern and try to get a feel for the room.
```

> **Tip.** If the engine instead says it is another combatant's turn in a
> session you only just started, an encounter from an earlier run survived in
> the campaign state. Type `/end-combat` to clear it and act normally.

The Dungeon Master thinks for a moment and then narrates a response.
The engine may propose a skill check—for example:

```text
You scan the room with practiced eyes. That sounds like a Perception
check—want to roll it?
```

Type `yes` (or just `y`) to confirm. The Rust core rolls the dice,
the result appears in your terminal, and the Dungeon Master narrates
the outcome.

---

## What you learned

- The engine separates your input (your text) from mechanical resolution
  (the Rust core) and prose generation (the LLM).
- `--create` opens the Session-0 wizard for a new character. You only need it once
  per character.
- Natural-language actions flow through intent classification, optional
  dice proposals, and narrative generation.

## Next steps

- [Player Manual](/aether/player-manual/)—full command reference, dice
  syntax, visibility scopes, and troubleshooting.
- [Playing via the CLI](/aether/aether-cli/)—the CLI client in more depth.
- Architectural Overview—how the
  three layers interact.
- Glossary—definitions for all
  engine-specific terms.


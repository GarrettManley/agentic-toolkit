---
title: "Tutorial: Your First Campaign"
weight: 30
---

This tutorial walks you from a fresh clone to your first turn in about 15 minutes. By
the end you will have a running engine, a new character, and your first narrative
exchange with the Dungeon Master.

> **Local play today.** The transport is being rebuilt (spec 043, #138): the old SSH +
> Google-sign-in flow is retired. This tutorial covers **local** play via the
> `aether-cli` over the loopback bypass. **Remote multiplayer** is coming — see
> [Player onboarding](/aether/player-onboarding/#remote-multiplayer-coming).

**Prerequisites:**

- Git
- Node.js 20 or later
- Rust toolchain—install from [rustup.rs](https://rustup.rs)
- Either a Gemini API key **or** a local [Ollama](https://ollama.com)
  instance (see Step 3)

---

## Step 1: Clone and install

```bash
git clone git@github.com:GarrettManley/aether-engine.git
cd aether-engine
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

### Option B—Ollama (local, no API key)

1. Install Ollama from [ollama.com](https://ollama.com).
2. Pull the required models:

   ```bash
   ollama pull mistral:7b-instruct
   ollama pull gemma3:4b
   ```

3. Start the engine with the Ollama provider in Step 4.

---

## Step 4: Start the engine

```bash
# Gemini provider
npm run start:gemini

# Ollama provider (default)
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

Open a **second** terminal and connect as your character:

```bash
npm run play -w @garrettmanley/aether-cli -- Kira --insecure
```

The first positional argument (`Kira`) is the character name. On `localhost` the
loopback bypass authenticates you automatically—no browser, no Google sign-in. The
`--insecure` flag accepts the gateway's self-signed dev certificate (localhost only;
use `--ca <gateway-cert.pem>` to verify it instead).

The engine responds with a campaign recap. If this is a new character
you will see:

```text
[SYSTEM]: Awaiting character creation for Kira...
```

> Connecting from **another machine** (with Google sign-in) is being rebuilt as part of
> transport v2 (#138, #139); until it ships, play is local.

---

## Step 6: Create your character

Type `/session0` and press Enter to start character creation.

```text
/session0
```

The engine guides you through name, race, class, and background.
Answer each prompt. Character creation takes about two minutes.

When it completes, your status bar appears:

```text
╔══════════════════════════════════════╗
║             KIRA                     ║
║  HP: 10/10 | AC: 12                  ║
╚══════════════════════════════════════╝
```

---

## Step 7: Take your first action

Type a natural-language description of what your character does:

```text
I look around the tavern and try to get a feel for the room.
```

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
- `/session0` creates a new character. You only need it once per character.
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


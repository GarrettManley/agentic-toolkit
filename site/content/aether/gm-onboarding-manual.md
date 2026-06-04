---
title: "GM Onboarding"
weight: 70
---


This guide is for the **GM operator**—a human or agent (typically
Claude over a Monitor stream) who writes Pass-2 prose for the
Aether Engine while it runs in manual GM mode (spec 041, issue #108).
For the **engine operator** who runs the server itself, see
manual-gm-operations.md.

## 1. What manual GM mode is

A player connects to the engine with the CLI and types something like
"I climb the rope" or "I attack the bandit." The engine
classifies their intent (Pass 1), resolves any mechanics through
the Rust core (Sage), then builds a Pass-2 prompt that asks for
narrative prose. In normal mode an LLM (Ollama, Gemini) answers
that prompt. In **manual mode**, you do.

The engine writes the Pass-2 prompt to a file under
`logs/manual-gm/pending/`, then polls
`logs/manual-gm/responses/` for a matching response file. You
watch the pending directory, read the prompt, compose prose, and
drop a response file. The engine consumes it, runs Pass-3
extraction (still automatic), and continues the cycle. From the
player's perspective there is no visible difference; from yours,
you are the narrator for every turn.

## 2. The prompt JSON schema

A pending prompt file is named
`<sessionId>-<cycleNum>.prompt.json` and contains:

| Field | Type | Purpose |
|---|---|---|
| `sessionId` | UUID | The player's session. Use this in the response filename. |
| `cycleNum` | integer | Monotonic counter per session. Use this in the response filename. |
| `characterName` | string | The player's character (for example `gurga`). Stay in their POV. |
| `prompt` | string | The fully assembled Pass-2 prompt: player input, intent, mechanical resolution, and instructions. |
| `narrativeContext` | string | Lore digest + recent world facts + active scene. Read this for continuity. |
| `systemInstruction` | string | The dynamic Pass-2 instructions (anti-resolution rules, voice, length cap). **Treat this as authoritative.** |

`systemInstruction` changes per cycle. When the next actor is an
NPC, it tells you to set up the NPC's response without resolving
it. When the next actor is the player, it tells you to leave
agency open. Read it every cycle. Do not rely on memory.

## 3. The response JSON schema

Write your response to
`logs/manual-gm/responses/<sessionId>-<cycleNum>.response.json`.
The filename must exactly match the prompt's session id and cycle
number, or the engine will not pair them.

Required fields:

| Field | Type | Purpose |
|---|---|---|
| `prose` | string | Your Pass-2 narrative. Under 200 words. No mechanical claims. |
| `operator_id` | string | Your identity for the audit log. Format: `<who>:<utc-date>`. Example: `claude:2026-05-07`. |

Optional:

| Field | Type | Purpose |
|---|---|---|
| `metadata` | object | Free-form notes preserved verbatim in the audit log. Useful for tagging tricky cycles. |

Example minimal response:

```json
{
  "prose": "The rope creaks under your weight as you haul yourself up the cliff face. Loose pebbles skitter past your boots and ping against the rocks below. At the top, the wind shifts — and somewhere ahead, a horn answers the one you heard in the valley.",
  "operator_id": "claude:2026-05-07"
}
```

## 4. Watching for prompts

You need a stream that fires the moment a new file appears in
`logs/manual-gm/pending/`. On any modern shell:

```bash
inotifywait -m -e create logs/manual-gm/pending/
```

On Windows PowerShell:

```powershell
$w = New-Object System.IO.FileSystemWatcher "logs/manual-gm/pending/", "*.json"
Register-ObjectEvent $w Created -Action { Get-Content $Event.SourceEventArgs.FullPath | Write-Host }
```

Whichever you use, also tail the audit log so you see your
responses being recorded:

```bash
tail -f logs/manual-gm-audit.jsonl
```

When working through Claude Code's Monitor tool, run the watcher
as a background command and the Monitor stream surfaces each new
prompt as it arrives.

## 5. Composing a response

Read in this order:

1. **`systemInstruction`** — the contract for this turn.
2. **`narrativeContext`** — the world state. Do not contradict it.
3. **`prompt`** — the player's input and the mechanical outcome
   you must reflect.

Then write prose that:

- **Stays in the character's POV.** Second person ("you climb the
  rope"), present tense.
- **Respects the mechanical outcome.** If the prompt says the
  attack hit for 7 damage, the prose must show a hit. Never
  invent damage, ranges, conditions, or saving throws.
- **Honors the anti-resolution rule.** Do not narrate the next
  actor's response unless `systemInstruction` says you should.
  When the next actor is an NPC, set up their action; do not
  resolve it. When the next actor is the player, leave agency
  open. (See issue #105 for the rationale.)
- **Stays under 200 words.** Hard cap. Long prose breaks pacing
  and inflates the prompt cache for the next cycle.
- **Names entities consistently.** No parenthetical aliases
  (#103). If the prompt says `Kira`, write `Kira`, not
  `Kira (the rogue)`.

If a prompt asks for something the rules forbid (a bare number,
a mechanical fact you do not have), refuse implicitly: write
prose that brackets the moment without resolving it. The engine's
Pass-3 extraction will pick up any stage directions you do
include.

## 6. Common pitfalls

- **Narrating to resolution.** The most common bug. The player
  swings, the prose carries through to "the orc collapses." The
  engine has not rolled the orc's HP. Stop at the swing.
- **Parenthetical aliases.** "Gurga (the half-orc barbarian)"
  pollutes downstream summarization. Use the name once,
  pronouns after.
- **Exceeding 200 words.** Your prose is part of the prompt
  cache for the next cycle. Long responses cost tokens
  forever.
- **Inventing mechanics.** "You take 4 damage." No. Mechanics
  belong to the Sage. If the prompt does not state damage, do
  not state damage.
- **Filename mismatch.** A response named with the wrong cycle
  number is silently ignored. Copy the prompt filename's stem
  exactly, just swap `prompt` for `response`.

## 7. What the engine still does automatically

You write Pass-2 prose only. The engine handles:

- **Pass 1—intent classification.** The player's input is
  classified into a typed intent (skill check, attack, spell)
  before you ever see a prompt.
- **Mechanical resolution.** Dice rolls, damage, condition
  changes, encounter management—all the Rust Sage's job.
- **Pass 3—stage-direction extraction.** After your prose is
  consumed, the engine re-reads it for `EFFECT_APPLIED`,
  `INITIATE_COMBAT`, `END_COMBAT`, `STAGE_DIRECTIONS`, and
  similar tags. Embed these tags in the prose where they fit
  the fiction; do not invent the schema yourself unless you
  know it.
- **State sync.** Spell gain, level gain, item gain queue
  through `/accept` to mutate character JSON. You narrate the
  fiction; the engine writes the truth.

## 8. Mechanical levers you can suggest

You cannot directly run engine commands from the manual
provider, but you can recommend the engine operator (or a GM
session) execute these from a GM CLI session:

| Command | Effect |
|---|---|
| `/gm startencounter <names...>` | Roll initiative, enter combat. |
| `/gm endencounter` | Exit combat. |
| `/gm delegate <character> <identity-key>` | Grant operator status. |
| `/gm revoke <character> <identity-key>` | Revoke operator status. |
| `npx ts-node inject.ts <campaign> "<text>"` | Inject narrative directly to the ledger. |
| `npx ts-node inject.ts <campaign> --dc-override <skill> <dc>` | Override the DC for the next skill check. |

See [gm-manual.md](/aether/gm-manual/) for the full GM command
surface.

## 9. Audit and accountability

Every response you write is appended to
`logs/manual-gm-audit.jsonl` with a hash of the prompt, the
prose verbatim, your `operator_id`, and the UTC timestamp. This
is a permanent, append-only trail.

Set `OPERATOR_ID` to a value that identifies you (or your
session). Defaults to `claude:<UTC-date>`. For named human
operators, use `<name>:<utc-date>` (for example
`garrett:2026-05-07`).

The audit log is retained for 90 days minimum as SOC2 evidence.
Treat your prose as on the record.

## 10. Workflow example

A player connected as `gurga` types `I climb the rope`. The
engine classifies (skill check, athletics), the Sage rolls
(success), and writes:

`logs/manual-gm/pending/8c4a7e3f-1d22-4f0b-9a1b-7e3c5d6f8a90-17.prompt.json`

```json
{
  "sessionId": "8c4a7e3f-1d22-4f0b-9a1b-7e3c5d6f8a90",
  "cycleNum": 17,
  "characterName": "gurga",
  "prompt": "Player input: I climb the rope.\nIntent: skill_check (athletics, DC 12).\nResult: success (rolled 18).\nNext actor: gurga.\nWrite Pass-2 prose under 200 words.",
  "narrativeContext": "LORE DIGEST: ... WORLD STATE: rope hanging from a cliff above the river. ACTIVE SCENE: gurga at the rope's base.",
  "systemInstruction": "Next actor is the player. End with agency open. Do not narrate gurga's next action. No mechanical claims."
}
```

You read the prompt. You compose:

```json
{
  "prose": "You set your feet against the rock and pull. The rope is wet from the river spray, but it holds. Hand over hand you climb until you can hook an elbow over the lip of the cliff. The wind up here carries the smell of woodsmoke from somewhere east, and the horn — that horn from the valley — sounds again, closer now.",
  "operator_id": "claude:2026-05-07"
}
```

You save this to
`logs/manual-gm/responses/8c4a7e3f-1d22-4f0b-9a1b-7e3c5d6f8a90-17.response.json`.

Within 250 ms the engine consumes the response, deletes both
files, runs Pass-3 (no stage directions in this prose, so no
state changes), and broadcasts the prose to the player's
session. The player sees their prose; the audit log records
your contribution. The cycle is done.

## Related docs

- [Claude as the manual GM — prompt-shape reference](/aether/claude-as-gm/) —
  the four Pass-2 prompt shapes (open action, roll-proposal,
  post-roll, speech-to-NPC) with markers and example responses
- Runbook: Manual GM operations
- [GM and operator manual](/aether/gm-manual/)
- [Player manual](/aether/player-manual/)
- [Player onboarding](/aether/player-onboarding/)
- [Character creation](/aether/character-creation/) — required narrative-identity fields for PC JSON files (#121).


---
title: "Claude as GM"
weight: 90
---


This guide catalogs the four prompt shapes a manual-mode operator
encounters in spec 041 (#108), each with the marker that signals
the shape, the system-instruction excerpt that gates operator
behavior, and an example response drawn from the 2026-05-08 Shape
A live validation. Use this when you (Claude or a human) are
sitting in the Pass-2 seat and want to identify what kind of cycle
you're answering before you compose.

For the broader manual-mode workflow (file watcher, response JSON
schema, audit log, common pitfalls), see
[gm-onboarding-manual.md](/aether/gm-onboarding-manual/). For engine-
operator setup (start, monitor, stop, recover), see
manual-gm-operations.md.

## At a glance

The Pass-2 prompt body and `systemInstruction` together identify
which shape you're in:

| Shape | Marker in prompt body | System-instruction signal | Operator produces |
|---|---|---|---|
| Open action | No preamble; raw player input | Standard 1–2 paragraph anti-resolution rule | Immersive prose ending on a sensory hook or open question |
| Roll-proposal preamble | `Skill to propose: <skill>` | "1–2 sentences" + skill prompt | One short beat that ends in the skill question; do **not** roll |
| Post-roll resolution | `Mechanical Result: { … }` JSON | Standard 1–2 paragraph form | Narration of the already-rolled outcome (success or failure) |
| Speech-to-NPC | Player addresses an NPC ("I want to ask V…") | Exception clause: "you may offer one or two example replies inline" | Prose that voices the NPC; example replies optional |

Of the 17 cycles in Shape A, the distribution was 13 open-action,
2 roll-proposal preamble, 2 post-roll resolution, and 1
speech-to-NPC. Roll-proposal and post-roll always come in pairs:
the engine first asks you to set up the roll, then (after the
player accepts and the Sage resolves) asks you to narrate the
outcome.

## 1. Open action

**When it fires.** The default. Whenever the player's input does
not need a skill check, doesn't follow up a pending roll, and
isn't directed at a registered NPC, the engine produces an
open-action prompt.

**Marker.** None. The prompt body is the player's raw input
("Let's explore the unknown", "I bring the bracelet to the
seam"), with no `Skill to propose:` or `Mechanical Result:`
preamble.

**System-instruction excerpt** (from `src/dm.ts` —
`playerNextInstruction`):

> Your response must engage directly with the player's current
> input. Do not continue or repeat imagery from the previous turn
> unless the player explicitly referenced it. … Keep your
> response to 1–2 paragraphs, under 200 words. Do not invent
> mechanical rules. … End your narrative with the scene open
> and inviting: a sensory hook (something the player notices,
> hears, or feels) or a light question like "What do you do?".

**What you produce.** 1–2 paragraphs, under 200 words, ending on
a sensory hook or light question. No mechanical claims.

**Example.** Shape A cycle 1 — input "Let's explore the unknown":

> The Aether-Link's silver thread thrums against your wrist —
> not warning, not yet, but *attention*. The Loom is watching
> you watch the obelisk. You step closer. Up close, the stone
> isn't stone at all; the surface flickers between rendered
> textures — granite, basalt, something like burnished copper —
> as if the world hadn't decided yet what this thing was supposed
> to be. Voidy paces a tight half-circle around the base,
> tendrils trailing low. The creature isn't growling. It's
> *looking*.
>
> Behind the obelisk the half-formed clay slopes downward into
> something the mists don't quite cover — a corridor, maybe, or
> the bed of a river that was never finished, running deeper
> into the Null-Zone away from the Basin. The Void-Glass shard
> at your wrist catches a refraction the obelisk shouldn't be
> casting: a single thin line of light, pointing along that
> corridor. The bracelet hums in time with it. The Loom is
> showing you something. What do you follow?

## 2. Roll-proposal preamble

**When it fires.** The classifier inferred a skill check but the
engine is in `rollMode: 'proposed'` (the default). Before
rolling, the engine asks you to set up the roll narratively so
the player can see what's at stake and accept with `/accept`.

**Marker.** The prompt body opens with two lines:

```text
User Action: <player input>
Skill to propose: <skill-slug>
```

**System-instruction excerpt.** A shorter, focused form:

> Compose 1–2 sentences that bring the moment into focus and
> end on the skill prompt. Do not roll. Do not state outcomes.
> The player will accept the roll on their next turn.

**What you produce.** One or two sentences. No paragraphs. End
with a question that proposes the skill explicitly, e.g. "That
feels like an Insight check — roll it?". Do **not** describe
the result; the dice haven't been thrown.

**Example.** Shape A cycle 6 — input "I want to make some kind
of insight check; Skill to propose: insight":

> You ease your breathing and let the threshold's pull soften,
> watching not the slab but the texture of the moment — Voidy's
> hush, the bracelet's pull, the weight of being seen by
> something that cares whether you see back. That feels like an
> Insight check — roll it?

## 3. Post-roll resolution

**When it fires.** Always paired with the previous cycle's
roll-proposal preamble. The player has typed `/accept`, the Sage
has rolled, and now the engine wants Pass-2 prose that narrates
the result.

**Marker.** The prompt body opens with the original input plus
a JSON resolution payload:

```text
User Action: <player input>
Mechanical Result: {"character": "...", "skill": "...", "roll": N, "dc": M, "success": true|false, ...}
```

**System-instruction excerpt.** Back to the standard form (the
same anti-resolution rule as open action), because this *is* the
resolution.

**What you produce.** 1–2 paragraphs, under 200 words. Reflect
the success or failure clearly. Do not invent damage, ranges, or
new conditions; the Sage's payload is authoritative for any
mechanical fact you reference.

**Example.** Shape A cycle 7 — same input, post-roll:

> The reading lands. The slab isn't a door for everyone. It's a
> door for *one*, and it's mourning. Voidy's hush isn't reverence
> for the place — it's reverence for the shape of someone who
> passed through here and didn't come back. Whoever they were,
> they wore something the Loom is still tied to. Probably not
> the only such thing in the world. Possibly not the only one at
> this wrist.
>
> Your bracelet hasn't been pulling you toward the slab. It's
> been pulling you *through* it — toward something on the far
> side that was never built, or was unbuilt, the way the slab
> itself is half-rendered toward you and finished toward the
> corridor. You realize you haven't sensed the Aether Tear since
> the corridor began.

## 4. Speech-to-NPC

**When it fires.** The player's input addresses a registered NPC
directly ("I want to ask V what he makes of this", "I tell the
cartographer we'll help"). The classifier emits a SPEECH intent;
the engine still asks you to write Pass-2 prose, but the
system-instruction unlocks an exception clause that allows
example NPC replies inline.

**Marker.** The prompt body is the player's raw input (no
`Skill to propose:` or `Mechanical Result:` preamble). What
distinguishes the shape is the player addressing a present NPC.
The engine's `systemInstruction` for this cycle still appends:

> Only in explicit dialogue scenes — when an NPC is waiting for
> the player to answer — you may offer one or two example replies
> inline. Even then, never present them as a numbered menu and
> never append a "respond freely" footer.

**What you produce.** Prose that voices the NPC's response and,
optionally, includes one or two example replies the player might
give back — woven into the fiction, not as a numbered menu.

**Example.** Shape A cycle 10 — input "I want to ask V what he
makes of this":

> You crouch close to Voidy, low enough for the static-growl to
> be a hush rather than a hum. "What do you make of this?"
>
> Voidy doesn't look at you. It looks at the seam, and at the
> print twenty paces down. Its tendrils contract, then settle.
> The voice that comes out is not its hunting voice — quieter,
> more shaped, like fragments of someone else's syllables
> surfacing through static. *"…known.… walked.… mapped…"* Each
> word arrives wrapped in the digital crackle that fills its
> silences. *"…did not return through.… left through, did not
> come… back through. The slab waits the same as the place
> waits."*
>
> Voidy's ember-eyes flick to the bracelet on your wrist, then
> to the figure-print, then back. *"Same shape. Different one."*

This response did not include explicit example replies because
Voidy's fragmented dialogue was itself the prompt; the player
read it and answered with their own beat in the next cycle.
Including an example reply (one or two short alternatives the
player might say back) is allowed when the NPC's question is
direct and the player might benefit from a hint.

## Operator identity

Set `OPERATOR_ID` to a value that identifies you for the audit
log. The convention used in Shape A was `claude:<UTC-date>` (LL-5
in spec 041). Format: `<who>:<utc-date>`. Examples:

- `claude:2026-05-08` — Claude-authored cycle on 2026-05-08
- `garrett:2026-05-08` — Human-authored cycle by Garrett

Every response you write lands in `logs/manual-gm-audit.jsonl`
with this identifier, your prose verbatim, and a UTC timestamp.
The audit log is retained 90 days minimum as SOC2 evidence;
treat your prose as on the record.

Two field-naming conventions to keep straight (#126):

- **Response file** (what you write) — snake_case: `prose`,
  `operator_id`, optional `metadata`. This is the operator-facing
  protocol surface.
- **Audit log entry** (what the engine records) — camelCase:
  `operatorId`, `latencyMs`, `cycleNum`, `sessionId`, `outcome`.
  This matches the broader TypeScript-JSON convention used in
  MessageBus metadata and OVERSEER telemetry.

## Atomic writes

The engine deletes the response file once it consumes it, so a
half-written file can be read mid-write and produce a malformed
response. Use a tmp-then-rename pattern to make the write atomic:

```bash
# Write to a sibling tmp file first, then rename in one step.
echo '<json>' > "$RESPONSE.tmp" && mv "$RESPONSE.tmp" "$RESPONSE"
```

```python
# In Python (used for Shape A):
import os, tempfile, json
fd, tmp = tempfile.mkstemp(dir=responses_dir, suffix='.tmp')
with os.fdopen(fd, 'w') as f:
    json.dump(response, f)
os.replace(tmp, target)  # atomic on POSIX and Windows
```

The engine ingests every response within ~250 ms of file landing
in Shape A, so a torn write would be visible immediately as a
`MANUAL_GM_RESPONSE_INVALID` audit-log entry rather than silently
corrupting state.

## Related docs

- [GM onboarding manual](/aether/gm-onboarding-manual/) — full
  manual-mode workflow, response JSON schema, file watching,
  pitfalls
- Runbook: Manual GM operations —
  engine-operator setup
- Spec 041 — design and
  decision record
- Manual-GM threat model —
  auth boundary and audit-log expectations


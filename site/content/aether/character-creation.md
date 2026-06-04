---
title: "Character Creation"
weight: 20
---


The Aether Engine drives Pass-2 prose from the contents of your
character JSON file. **Mechanical fields** (HP, AC, abilities,
proficiencies) drive Sage and combat. **Narrative-identity fields**
(personality, backstory, bonds, ideals, flaws, goals, appearance,
pronouns) drive how the LLM writes your character into scenes.

If the narrative-identity fields are empty, the engine still runs —
but the LLM has no anchor for your PC, so prose will drift onto
whichever NPC happens to have a richer hook. The 2026-05-08 Shape C
session caught this in the wild: Gurga had every mechanical field
populated and zero narrative ones, while the void-stalker NPC had
`personality` and `goals`, so Pass-2 prose treated Voidy as the
protagonist and Gurga as a generic level-1 warlock — even producing
"...your duty to Gurga", referring to the protagonist in the third
person.

This guide walks through the required fields, what makes each
field useful, and how to author the trickiest one (the patron entity).

## 1. Quick start

1. Copy `universe/characters/_pc-template.json` to
   `universe/characters/<your-name>.json` (lowercase, no leading
   underscore — the validator skips files starting with `_`).
2. Replace every placeholder. Mechanical fields can stay at the
   template defaults if you're rolling a fresh level-1 warlock; the
   narrative fields must each be filled.
3. Run `npm run characters:check`. The script walks
   `universe/characters/*.json` and warns if any required narrative
   field is empty. Default mode is advisory (exit 0); pass
   `--strict` to make missing fields a hard error.
4. The engine also runs the same check at boot and prints a single
   warning line per affected character to stderr. Engine still
   starts — this is non-blocking.

For the live `gurga.json` as a worked example, see the file in the
repo. It was the first PC authored with all narrative fields
filled, and the immediate prose-quality lift on the next cycle is
why this guide exists.

## 2. Required narrative-identity fields

The validator (`scripts/check-character-fields.mjs`) flags any of
these as empty/missing on a PC:

| Field | Type | What the LLM does with it |
|---|---|---|
| `pronouns` | string | Used in every Pass-2 reference to the PC. Without it the LLM falls back to gendered guesses or third-person noun chains. |
| `appearance` | string | Two-to-four sentences. The thing a stranger sees in the first ten seconds. The LLM weaves these details into scene description. |
| `personality` | string | One-to-three sentences. Habitual behavior, default posture toward the world. **Not** a backstory — the thing the character does without thinking. |
| `backstory` | string | Three-to-six sentences ending at the moment the campaign begins. Anchors why this character is here, with this class, with these bonds. |
| `bonds` | string[] | One-to-four short statements. People, places, or objects the PC cares about enough to risk something for. |
| `ideals` | string[] | One-to-three short statements. Principles the PC tries to live by. |
| `flaws` | string[] | One-to-three short statements. Habitual failure modes that have consequences. |
| `goals` | string[] | One-to-four short statements. What the PC wants — short term and long term. |

A useful heuristic: if you can imagine a session where the LLM never
references a field, the field is too abstract to be useful. Phrase
flaws as tendencies that cost something. Phrase bonds as
specific people, places, or objects, not abstractions.

## 3. Optional narrative fields

These fields are not required, but the engine uses them when present.
Leave them out entirely (delete the key) if not applicable — empty
objects/arrays are fine too.

| Field | Type | Use it when |
|---|---|---|
| `patron` | object | Warlock, Cleric, characters with otherworldly entanglements, or any PC whose arc has a major NPC influence. |
| `traits` | string[] | Atomic mannerisms the LLM can salt into prose — "taps the bracelet when nervous", "always quotes the cartographer's field manual". Two-to-five entries is plenty. |

### 3.1 The patron entity (the trickiest field)

A `patron` is an object with five sub-fields. Each does specific
work in the prompt:

| Sub-field | Purpose |
|---|---|
| `name` | How the PC names this entity. May be a true name, an epithet, or "the Loom" / "my master" / "the voice". |
| `nature` | Two-to-four sentences. What kind of being is it? How does it communicate? What is its relationship to the rendered world? |
| `wants` | One-to-two sentences. What is the patron pursuing through this character? The long-term arc. |
| `gives` | One-to-two sentences. The mechanical and narrative gift. Why the character serves. |
| `demands` | One-to-two sentences. The cost. What the patron asks that the character must keep paying. |

The four behavior sub-fields work together. `wants` defines the
arc. `gives` and `demands` form the ongoing trade. `nature`
controls the texture of every appearance the patron makes in prose.

Example, from `gurga.json`:

```json
"patron": {
  "name": "The Loom",
  "nature": "An entity that exists between threads of reality, watching where the world's data frays. It speaks in resonances and partial visions, never commands.",
  "wants": "The Aether Tear in the East un-knotted.",
  "gives": "Eldritch power threaded through the Aether-Link bracelet's silver line. When Gurga succeeds, the thread hums; when they fail, it pulses red.",
  "demands": "Witness. The Loom asks Gurga to see what others overlook — glitches, half-rendered places, entities that live in the gaps."
}
```

Notice none of these sub-fields are abstract. "Wants the Tear
un-knotted" is a destination Sage and the LLM can both reason
about. "Gives" is a specific physical anchor (the bracelet) plus a
specific feedback signal (the silver line's color). "Demands" is a
verb the LLM can dramatize when it picks scenes.

## 4. What makes a "good" personality / bond / flaw

Three FAQ-style heuristics for the fields that newcomers struggle
with most.

### 4.1 Personality — a behavior, not a label

Bad: "Stoic. Brave. Honorable."
Good: "Speaks last. Will not break eye contact. Refuses to repeat
an order — once is enough or it isn't worth saying."

The bad version gives the LLM three adjectives to swap in. The good
version gives the LLM specific behaviors the LLM can dramatize.
Adjectives compress; behaviors expand.

### 4.2 Bond — a specific anchor, not a relationship category

Bad: "My master."
Good: "The Aether-Link bracelet — Gurga's only physical anchor to
the Loom, and to the cartographer who never came back."

The bad version is a placeholder. The good version is a specific
object with a specific history that gives the LLM something
concrete to reference when stakes need to rise. Specific bonds
survive across scenes; abstract bonds dissolve into prose hand-
waving.

### 4.3 Flaw — a tendency with a price

Bad: "Stubborn."
Good: "Cannot leave a knot un-pulled. The Aether Tear is not a
destination, it is a compulsion."

The bad version is a label. The good version describes a pattern
the GM can trigger and a cost the player pays for. Flaws should
function like Pendragon's Vices — not personality decoration, but
forces that pull the character into bad situations.

## 5. Validation workflow

```bash
# Default mode — walks universe/characters/, warns to stderr, exits 0.
npm run characters:check

# Strict mode — exits 1 if any required field is missing. Useful for
# CI gating once the team is comfortable; not on by default.
node scripts/check-character-fields.mjs --strict

# Validate one specific file.
node scripts/check-character-fields.mjs universe/characters/gurga.json
```

The validator skips:

- Files whose basename starts with `_` (e.g. `_pc-template.json`).
- Known test/scenario fixtures (currently `druid_harness.json`).
- Files that lack a `class_features` field — these are presumed
  NPCs (e.g. `void-stalker.json`).

The boot-time warning in `src/server.ts` uses the same set of
rules; it is non-blocking and prints one line per affected
character.

## 6. See also

- [GM onboarding manual](/aether/gm-onboarding-manual/) — for the GM
  operator who composes Pass-2 prose in manual mode.
- `docs/engineering/plans/2026-05-08-108-shape-c-findings.md`
  — the live-play session that exposed the gap and motivated #121.
- `universe/characters/gurga.json`
  — the worked example referenced throughout this guide.


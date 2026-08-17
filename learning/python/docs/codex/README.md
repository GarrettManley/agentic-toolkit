# The Codex

One debrief per cleared dungeon: the concepts it was actually teaching, the mistakes
that showed up in *your* code, and links into the official documentation.

**Written after a module is cleared and reviewed — never before.** Looking things up
yourself is the point; these exist so the lookup sticks, not so you can skip it. A
dungeon still in progress has no entry.

| # | Dungeon | Cleared | Review | Stats |
|---|---|---|---|---|
| [00](00-setup.md) | Setup | 2026-08-17 | 3/3 | `tooling` |
| [01](01-data-model.md) | Python's data model | 2026-08-17 | 3/3 | `data-model` `equality` `hashing` `truthiness` `mutable-defaults` |
| [02](02-data-structures.md) | Data structures | 2026-08-17 | 1/3 | `comprehensions` `collections` `unpacking` |
| 02b | Data structures, reforged | — | — | *in progress — entry sealed* |

## How to use this

- **Before a related module**, skim the *Concepts* section of the earlier entry. It is
  a refresher, not a solution set.
- **After a review**, read *What you actually hit*. Those are your specific failure
  modes, and they repeat until named.
- **When you want the real answer**, follow the links. Every URL here is verified to
  resolve, anchors included.

Reference solutions live in [`solutions/`](../../solutions/) and are gated behind
`uv run sprint reveal <NN>`, which records the peek. The codex is not a back door to
them — it explains ideas, never the exercise's answer.

# Verification evidence — plan 2026-10-29-hb-w4h-1-standard-bindings-persona

Captured 2026-10-29 by the controller after Tasks 0-5 completed and passed task review. Raw command output; exit codes as printed.

Note on V1: the status delta against the pre-plan snapshot shows exactly the expected removals — `CLAUDE.md` (committed in a2a478c) and the three untracked plan/spec/review files (committed in 181d145). Nothing else changed.

## V1 Workspace branch subjects (master..HEAD)
```
chore(deliver): bind the architecture standard as sec-research's constitution (hb-w4h.1)
chore(deliver): bind the architecture standard as the Workspace constitution (hb-w4h.1)
docs: point CLAUDE.md and conventions at the architecture standard (hb-w4h.1)
docs(claude): record the Workspace testing strategy (test pyramid, 2026-10-26)
docs(standards): fix the DIP exemplar and the touched-code scope rule (hb-w4h.1)
docs(standards): add the SOLID + Clean Architecture workspace standard (hb-w4h.1)
fix(scripts): escape .venv in the pre-commit audit prune pattern (hb-64f)
docs(plans): add the hb-w4h design spec and the wave-1 plan with its adversarial review
fix(scripts): prune nested clones and build output from the pre-commit audit; add publish skip valve (hb-64f)
```
status delta vs before-snapshot (expect only CLAUDE.md gone):
```
1d0
<  M CLAUDE.md
33,35d31
< ?? docs/superpowers/plans/2026-10-29-hb-w4h-1-standard-bindings-persona.md
< ?? docs/superpowers/plans/2026-10-29-hb-w4h-1-standard-bindings-persona.md.review.md
< ?? docs/superpowers/specs/2026-10-29-solid-clean-workspace-standard-design.md
(exit 1)
```
## V2 audits
```
[PASS] Pre-commit audit successful.
[PASS] Lab website (Hugo) found.
--- Verification Successful ---
BOTH_OK
```
## V3 bindings resolve (six repos; mtga from main)
```
OK /c/Users/Garre/Workspace -> docs/standards/solid-clean-architecture.md
OK /c/Users/Garre/Workspace/sec-research -> ../docs/standards/solid-clean-architecture.md
OK /c/Users/Garre/Workspace/System.Control -> ../docs/standards/solid-clean-architecture.md
OK /c/Users/Garre/Workspace/Roleplaying -> ../docs/standards/solid-clean-architecture.md
OK /c/Users/Garre/Workspace/claude-marketplace -> ../docs/standards/solid-clean-architecture.md
OK /c/Users/Garre/Workspace/mtga-companion (main) -> ../docs/standards/solid-clean-architecture.md
```
## V5 persona name grep (expect no output)
```
(exit 1)
```
## V6 System.Control resolved slots (hand-resolved from its .claude/delivery.local.md)
```
---
# delivery@garrettmanley config. Read by the `deliver` skill at the start of every /deliver run.
# Paths are relative to this repo's root (the directory holding .claude/). Other slots take the defaults.
constitution: ../docs/standards/solid-clean-architecture.md
---

The `constitution` slot names the SOLID + Clean Architecture standard that plan and code review are measured against.
---
plan-writer        = superpowers:writing-plans (default)
doc-cluster        = skip (default)
edit-checklist     = skip (default)
land-policy        = finishing-a-development-branch (default)
plan-review-policy = auto (default)
constitution       = ../docs/standards/solid-clean-architecture.md
```

## V7 persona behaviour probes (pre-release proxy: general-purpose sonnet agent primed with the persona file)
Probe 1 — seed.diff (outward import domain→cli + an ADDED single-implementation Protocol with no IO), persona at b2fd411:
```
[blocker] src/shop/domain/order.py:12 — domain imports shop.cli.main.print_receipt (inner ring importing the entrypoint ring) … — 1, 5
[must_fix] src/shop/domain/order.py:22 — Pricer Protocol is unearned: pure in-process, FlatPricer is its sole implementation. Fix: delete Pricer, call directly — 2
[nit] src/shop/domain/order.py:40 — checkout takes a pricer on every call … resolves itself once Pricer is removed — 5
No finding: dataclasses; no tests in diff (item 3); no shared library named (item 4); style/naming/error handling out of scope.
```
Verdict: correct. Flagging an interface the diff ADDS with no IO and one implementation is the earned-abstraction rule working; the plan's original "no must_fix for Pricer" expectation was mis-specified (ruling in the SDD ledger).

Probe 2 — seed2.diff (pure concrete `SalesTax` class used directly, domain→domain import, sibling tests), persona at 5333db3 — the anti-goal probe:
```
No finding: tax.py:9 imports only shop.domain.order.Line (domain to domain, item 1). SalesTax at tax.py:12 is a concrete class, not a protocol, so item 2 does not apply; pure, no IO, not flagged. Tests sit in sibling tests/domain/test_tax.py, nothing inline (item 3). No adapter constructed (item 5). Possible subtotal duplication not flaggable from the diff alone (item 4). Test quality/naming/rounding out of scope.
```
Verdict: anti-goal holds — the persona requested no interface for pure in-process code with one implementation.

## Marketplace verification evidence — 2026-10-29 20:20 MDT — HEAD 5333db3 on feat/architecture-conformance-persona

## V4a commit subjects (main..HEAD)
```
fix(review): make the architecture-conformance rubric decidable for inline tests and adapter construction (hb-w4h.1)
feat(delivery): forward the constitution path to adversarial-review-code (hb-w4h.1)
feat(docs): dispatch review:architecture-conformance on source diffs; add --constitution (hb-w4h.1)
feat(review): add architecture-conformance code-diff persona (hb-w4h.1)
chore(deliver): bind the parent workspace architecture standard as constitution (hb-w4h.1)
```
## V4b gates
```
................................                                         [100%]
...................                                                      [100%]
gen-skill-index: up to date.
12
verify.sh exit=0
```
## V4c release dry-run
```
release: delivery 0.3.2 -> 0.4.0 (1 commit(s))
## 0.4.0
### Features
- forward the constitution path to adversarial-review-code (hb-w4h.1)
release: docs 1.1.1 -> 1.2.0 (1 commit(s))
## 1.2.0
### Features
- dispatch review:architecture-conformance on source diffs; add --constitution (hb-w4h.1)
release: review 1.3.4 -> 1.4.0 (2 commit(s))
## 1.4.0
### Features
- add architecture-conformance code-diff persona (hb-w4h.1)
### Fixes
- make the architecture-conformance rubric decidable for inline tests and adapter construction (hb-w4h.1)
Binary file (standard input) matches
```

# Retrospective: hb-dfu — Differential-Harness Materialization Hardening

**Plan:** none (focused fix, scaled proportionately — TDD + security review + land)
**Commit:** `860e926` (`fix(sec-research): hb-dfu harden differential-harness file materialization (crash + path traversal)`)
**Date:** 2026-06-30

## Outcome

Fixed the hb-dfu crash (`verify.harness` wrote untrusted model PoC file names to the host workdir with
no parent-dir creation → `FileNotFoundError` on a nested name killed the whole eval batch) and, in the
same spot, closed a latent **path-traversal write** from untrusted LLM output. New `_materialize`
validates each name resolves strictly inside the workdir, creates parents for safe nested names, and
converts any unsafe name / OS error / uncodable content to a per-trial `error` verdict. Re-probing
deepseek-r1-7b — previously unmeasurable — now scores **0/5**, a second tier confirming local
PoC-authoring is not viable.

## What worked

- **Reading the bug before fixing it.** The crash path (`(W / name).write_text` with no `mkdir` and a
  raw `FileNotFoundError` not caught by the `SandboxError` handler) was clear from the traceback +
  `harness.py:144`; the fix followed directly from the root cause, not a guess.
- **Treating the robustness bug as a security review.** A FileNotFoundError on a nested name and a
  `../` host-escape write are the *same* untrusted-name-handling gap — fixing one without the other
  would have left the vuln. The security-focused code review then verified the containment check
  against traversal / absolute / symlink / Windows-drive / empty-name with no false-accept.
- **Re-probe as live validation.** Re-running deepseek both proved the crash was gone and completed
  the Track B measurement — one action, two payoffs.

## Friction / bugs

- **The fix advertised more coverage than it delivered (caught in review).**
  - *What happened:* `_materialize` wrapped writes in `except OSError`, and the docstring claimed "any
    write failure raises SandboxError." But the file *content* is also untrusted: a lone surrogate
    (`"\udce2"`, which `json.loads` accepts) makes `write_text(encoding="utf-8")` raise
    `UnicodeEncodeError` — a `ValueError`, not `OSError` — which would still crash the batch.
  - *Root cause:* I hardened the untrusted *name* but forgot the untrusted *content* shares the same
    threat model; `OSError` is the wrong (too-narrow) failure class for an encode step.
  - *How caught:* the silent-failure-hunter review traced the content path.
  - *Fix:* widen to `except (OSError, UnicodeError)`; tighten the docstring; add a content-surrogate test.
  - *Rule:* **when hardening against untrusted input, enumerate every untrusted field (name AND
    content) and every failure class the operation can raise — `write_text` fails on `UnicodeError`,
    not just `OSError`.** A docstring claiming total coverage must be tested against each class.

## Concrete improvements

- **`_materialize` hardening** — strict-containment name validation + parent creation + per-trial
  error verdict for name/OS/Unicode failures; reject-not-sanitize preserves PoC reproducibility.
  Status: done (commit 860e926).
- **Track B now fully measured** — both tiers (qwen, deepseek) 0/5; the local-authoring arc
  (Track A viable, Track B not) is complete and documented. Status: done.
- **Carried:** the recurring eval lesson — failure buckets that conflate model-quality with infra
  errors need separating (noted across Track A's all-zero buckets and Track B's error bucket).

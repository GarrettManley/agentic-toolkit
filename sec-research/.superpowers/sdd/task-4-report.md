# Task 4 Report — `scripts/verify/harness.py` :: `_drive_phased`

## Status
COMPLETE — all tests green, committed on master.

## RUNTIME_DIR import resolution
`from lib.paths import RUNTIME_DIR` — hooks/ is on sys.path via
`tests/conftest.py:19`. `scripts/llm/generate.py` uses the identical import
(`from lib.paths import RUNTIME_DIR`, line 17). No local derivation needed.

## Files created
- `scripts/verify/harness.py` — `_drive_phased` + module constants
  (`RUNTIME_VERDICTS_DIR`, `INSTALL_TIMEOUT_S=180`, `TRIGGER_TIMEOUT_S=120`).
- `tests/scripts/test_verify_harness_drive.py` — 7 new tests (written first,
  red, then green after implementation).

## Test summary
Baseline: 262 passed / 2 skipped.
After implementation: 269 passed / 2 skipped (+7 new tests).

### Tests added
| Test | What it asserts |
|------|----------------|
| `test_install_runs_before_trigger_and_uses_bridge` | First call → bridge, second call → none |
| `test_trigger_network_none_explicit` | `argv[idx+1] == "none"` on 2nd call (C2) |
| `test_shared_workdir` | Both calls mount the same host path via `-v .../:/work` |
| `test_files_materialized_before_install` | `trigger.js` exists with correct content in `W` after call |
| `test_install_failure_raises_sandbox_error_and_trigger_not_called` | exit=1 → SandboxError, runner called exactly once |
| `test_install_timeout_raises_sandbox_error_and_trigger_not_called` | TimeoutExpired → SandboxError, runner called exactly once |
| `test_evidence_capture_shape_on_success` | install_ev.phase=="install", trigger_ev.phase=="trigger", fields populated from SandboxResult |

## Key design decisions
- `_drive_phased` does NOT compute a verdict — that is `derive_verdict` in Task 5.
- `_drive_phased` does NOT catch `SandboxError` or `ScopeViolation` — both propagate
  to the Task 5 caller for per-item isolation.
- Workdir: `verdict_root / slug / "work" / hypothesis_id` — matches spec §5.6.
- `verdict_root` parameter defaults to `RUNTIME_VERDICTS_DIR` but is injectable
  so tests can pass `tmp_path` without touching real runtime/.
- `runner` is forwarded directly into both `sandbox_run` calls — the same
  capturing-runner pattern from `test_sandbox_runner.py`.

## Concerns
None. The implementation is a straight transcription of the spec §5.6 pseudocode
with the correct phase strings (`"install"` / `"execute"`) and the named timeout
constants. No edge cases remain unhandled for this task's scope.

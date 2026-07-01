export const meta = {
  name: 'marketplace-w5-coverage',
  description: 'W5: author import-based unit tests across all plugins + ci to reach >=90% Python line coverage',
  phases: [{ title: 'Author tests', detail: 'one agent per plugin/area' }],
}

const REPO = 'C:\\Users\\Garre\\source\\repos\\claude-marketplace'

const COMMON = `You are writing pytest unit tests for the public claude-marketplace repo at ${REPO}.
GOAL: raise Python LINE coverage of the target file(s) to >=90% each.
RULES:
- Write IMPORT-BASED tests: import the module and call its functions/main() directly with pytest
  fixtures (tmp_path, monkeypatch, capsys). Import-based tests get coverage credit; subprocess calls do NOT.
  Only use subprocess when a module is a pure CLI with no importable logic.
- Mirror the plugin's EXISTING test conventions: first read that plugin's tests/conftest.py (it sets up
  sys.path so the scripts/ modules import by bare name) and ONE existing test_*.py for style. If the plugin
  has NO tests/ dir yet, CREATE tests/conftest.py mirroring plugins/evidence/tests/conftest.py's sys.path
  pattern (insert the dir(s) holding the modules under test onto sys.path).
- Mock external commands: gh, git (where the code shells out), network. Follow the fake-binary-on-PATH seam
  (e.g. monkeypatch a tmp 'gh'/'git' script onto PATH, or monkeypatch subprocess.check_output). Tests must be
  hermetic and pass offline.
- Use 'pragma: no cover' ONLY for: 'if __name__ == "__main__":' lines, the opposite-OS branch of a
  sys.platform guard, and genuinely unreachable defensive branches. Do NOT pragma real logic just to hit 90%.
- Each test must be deterministic and pass. After writing, RUN: python -m pytest <your test files> -q
  (from ${REPO}) and confirm ALL pass. Iterate until green.
- DO NOT run git. DO NOT commit. DO NOT edit files outside your plugin's tests/ dir (you MAY create that dir
  + its conftest.py). DO NOT edit the modules under test (tests only). Stay inside ${REPO}.`

const RET = {
  type: 'object', additionalProperties: false,
  properties: {
    test_files: { type: 'array', items: { type: 'string' }, description: 'repo-relative paths of test files created' },
    tests_passing: { type: 'number' },
    tests_failing: { type: 'number' },
    modules_covered: { type: 'array', items: { type: 'string' } },
    coverage_notes: { type: 'string', description: 'per-module: approx coverage reached + any lines left uncovered with reason (pragma/unreachable)' },
    notes: { type: 'string' },
  },
  required: ['test_files', 'tests_passing', 'tests_failing', 'modules_covered', 'coverage_notes'],
}

const GROUPS = [
  { key: 'ci-scanners', model: 'sonnet', dir: 'ci/tests', spec:
    `Target the 5 zero-coverage CI scanner scripts (all have main(argv) entry points + helper functions). Tests go in ci/tests/ (read ci/tests/test_aether_hooks.py for the existing style; ci scripts import via importlib because of hyphenated names — use importlib.util.spec_from_file_location to load 'ci/lint-no-bare-python.py' etc., OR add their dir to sys.path and import the underscore form if available):\n` +
    `- ci/lint-no-bare-python.py (0%): test scan_file/should_scan/main on tmp dirs with clean files, files containing bare 'python', 'python2', and the exempt cases (python3, hyphenated 'lint-no-bare-python'). Assert exit codes 0/1 and the report.\n` +
    `- ci/lint-frontmatter.py (0%): build tmp SKILL.md/agent .md files with valid + invalid frontmatter; assert pass/fail.\n` +
    `- ci/gen-skill-index.py (0%): point it at a tmp tree of skills/agents; assert --write produces the table and --check detects drift.\n` +
    `- ci/check-vendored-sync.py (0%): create tmp vendored copies that match + mismatch; assert clean vs drift exit.\n` +
    `- ci/verify_hook_runtime_controls.py (0%): exercise its checks on a tmp plugin layout.\n` +
    `These are hyphenated filenames — load each via importlib.util.spec_from_file_location("modname", "<abs path>").` },

  { key: 'ci-release-versions', model: undefined, dir: 'ci/tests', spec:
    `(W5.1 — LOAD-BEARING) Target ci/release.py (50%) and ci/check-versions.py (66%). release.py is Conventional-Commits semver. The squash launch makes its git-path correctness critical. Read ci/release.py fully first.\n` +
    `Write ci/tests/test_release.py covering _last_tag, _commits_for, parse_commit, plan, main via a TEMP GIT REPO fixture (git init a tmp dir, set user, make commits + tags with subprocess). Cases REQUIRED:\n` +
    ` (a) a '<plugin>-v1.0.0' tag at HEAD with no newer commits => plan() yields "nothing to do" (no bump).\n` +
    ` (b) one 'feat(scope): x' commit after the tag => minor bump proposed.\n` +
    ` (c) 'fix(scope):' => patch bump; a scopeless 'chore:' => parse_commit returns None / no bump (the squash-subject case).\n` +
    ` (d) breaking-change marker => major bump.\n` +
    `Also cover the missing lines 108-219 region. For check-versions.py cover lines 54,61,83,96-122 (the --fix path + drift detection) with tmp plugin.json/marketplace.json fixtures.` },

  { key: 'discipline-big', model: undefined, dir: 'plugins/discipline/tests', spec:
    `Target the two largest discipline modules (read plugins/discipline/tests/conftest.py + test_gateguard.py for style):\n` +
    `- plugins/discipline/scripts/shell_substitution.py (58%, 357 stmts; missing incl 361-518 — the bulk). This parses shell command substitution / detects dangerous patterns. Write thorough unit tests over its public functions for the many uncovered branches (parsing edge cases, each dangerous-pattern detector, the substitution walker). Aim >=90%.\n` +
    `- plugins/discipline/scripts/discipline_config.py (42%, 210 stmts; missing 104-281 region). Loads/merges .local.md config. Test each config-key parser, defaults, merge precedence, malformed input, with tmp .local.md files. Aim >=90%.` },

  { key: 'discipline-scripts', model: 'sonnet', dir: 'plugins/discipline/tests', spec:
    `Target (read conftest.py + an existing test for the gh/git fake-binary seam):\n` +
    `- plugins/discipline/hooks/plan_issue_check.py (55%; missing 148-233 region — the validation logic). Test the plan-file issue/value/retrospective validators with tmp plan files (valid + each failure mode). Note the issue-state regex (Closes/Updates/Follows up #N or hb-/bd- ids).\n` +
    `- plugins/discipline/scripts/snapshot.py (83%), session_resume_context.py (91%), pre_compact_snapshot.py (85%): cover the missing branches.\n` +
    `- plugins/discipline/scripts/gateguard.py (89%, 372 stmts): push to >=92% by covering the missing detector branches (lines 311-368 region).` },

  { key: 'discipline-hooks-vendored', model: 'sonnet', dir: 'plugins/discipline/tests', spec:
    `Target the UNTESTED discipline hooks + vendored utils (currently 0% / not measured). Read conftest.py first:\n` +
    `- plugins/discipline/hooks/frontmatter_lint.py, pitfalls_pointer.py, spec_companion_check.py, todo_issue_hook.py: each is a PreToolUse/SessionStart hook reading JSON from stdin. Test their importable logic functions directly; for the stdin/main path, feed JSON via monkeypatch(sys.stdin) or call the core function. Mock gh/git.\n` +
    `- plugins/discipline/scripts/_inject_issues.py (NEW, untested): test detect_repo() (env / .local.md / git remote parse — mock subprocess), build_context(), and main() (mock 'gh issue list'). Assert the hookSpecificOutput JSON shape.\n` +
    `- plugins/discipline/scripts/run_with_flags.py and hook_flags.py (vendored, untested): import the discipline copies and test their flag-parsing / dispatch logic. Aim >=90% each.` },

  { key: 'evidence', model: 'sonnet', dir: 'plugins/evidence/tests', spec:
    `Read plugins/evidence/tests/conftest.py + test_secret_scan.py. Target:\n` +
    `- plugins/evidence/scripts/scope_binding.py (untested, 0%): test check_url / check_path with a tmp .claude/evidence-scope.yaml (hosts, deny_hosts, path_prefixes, wildcard) AND the permissive no-manifest default (returns True). Needs PyYAML (now installed).\n` +
    `- plugins/evidence/scripts/evidence_hmac.py (92%; missing 132-133,150-151,191-192,205-206): cover the remaining issue/verify/redeem error/expiry/tamper branches.\n` +
    `- plugins/evidence/hooks/secret_scan.py (97%; missing 84-85): cover the last branch.` },

  { key: 'learning', model: 'sonnet', dir: 'plugins/learning/tests', spec:
    `Read plugins/learning/tests/conftest.py + test_storage.py. Target:\n` +
    `- storage.py (80%; missing 49,63-65,77-80,89,93-96), observe.py (88%), instinct_schema.py (87%), instinct_cli.py (83%; missing 195-214), analyze.py (95%): cover the missing branches with import-based tests + tmp data dirs (set LEARNING_DATA_ROOT to tmp_path).\n` +
    `- plugins/learning/scripts/hook_flags.py + run_with_flags.py (vendored, untested): import the learning copies and test them (>=90%).` },

  { key: 'stewardship', model: 'sonnet', dir: 'plugins/stewardship/tests', spec:
    `Read plugins/stewardship/tests/conftest.py + an existing test. Target:\n` +
    `- drift_check.py (58%; missing 122-229 — the command-running + reporting logic): test the frontmatter parser + verification-command runner with tmp .md context files (mock subprocess for the commands). Aim >=90%.\n` +
    `- stop_format_typecheck.py (75%; missing 123-183), auto_memory_housekeep.py (untested, 0%: test the archival-candidate + dedup passes with tmp memory dirs), post_edit_accumulator.py (95%), language_detect.py (96%).\n` +
    `- plugins/stewardship/scripts/hook_flags.py + run_with_flags.py (vendored, untested): import + test (>=90%).` },

  { key: 'aether', model: 'sonnet', dir: 'plugins/aether/tests', spec:
    `CREATE plugins/aether/tests/ (conftest.py mirroring evidence's sys.path setup, pointing at plugins/aether/scripts AND plugins/aether/hooks). The 5 hooks are UNTESTED (0%). ci/tests/test_aether_hooks.py tests some via SUBPROCESS (no coverage credit) — add IMPORT-based tests:\n` +
    `- hooks/cd_core_guard.py, classifier_eval_reminder.py, gameplay_harness_reminder.py, ledger_truncation_hook.py, rust_rebuild_reminder.py: import each, call its core logic (most no-op outside an Aether repo — build a synthetic aether checkout via tmp_path with core/Cargo.toml like ci/tests/test_aether_hooks.py does; reuse that approach). Mock stdin JSON where they read PreToolUse input.\n` +
    `- scripts/aether_repo.py (61%; missing 36-39,44-51,62-63,78,81-82): cover the repo-root-walk + no-op-outside-aether branches.\n` +
    `Aim >=90% per file.` },

  { key: 'git', model: 'sonnet', dir: 'plugins/git/tests', spec:
    `(W5.3) CREATE plugins/git/tests/ (conftest.py adding plugins/git/skills/commit-message/scripts to sys.path). Target plugins/git/skills/commit-message/scripts/validate.py (untested). It validates Conventional-Commit messages and has an OPTIONAL 'import yaml' branch (PyYAML now installed → exercise the yaml path AND simulate its absence). Test: valid commits, each violation (bad type, missing scope rules, subject length, etc.), and BOTH the yaml-present and yaml-absent (monkeypatch sys.modules['yaml']=None / ImportError) config-loading paths. Aim >=90%.` },

  { key: 'orchestration', model: 'sonnet', dir: 'plugins/orchestration/tests', spec:
    `CREATE plugins/orchestration/tests/ (conftest.py adding plugins/orchestration/hooks to sys.path). Target plugins/orchestration/hooks/inject_orchestration_context.py (untested, 0%): it's a SessionStart hook that injects context/agent-orchestration.md. Import it, test that it emits the correct hookSpecificOutput JSON (reading the bundled context file), and any guard branches. Mock stdin/env as needed. Aim >=90%.` },

  { key: 'init-behavioral', model: 'sonnet', dir: 'plugins (multiple)/tests', spec:
    `(W5.2 init correctness — behavioral, not for the Python coverage %). Write SUBPROCESS behavioral tests verifying the new init scripts are idempotent. For each of evidence/orchestration/discipline/git init.sh (bash), create plugins/<p>/tests/test_init.py that: runs init.sh with HOME pointed at a tmp dir, asserts the expected file is created + the status line, runs it AGAIN and asserts "already configured" (idempotent), and asserts exit 0. Skip stewardship (touches the real scheduler) — just assert its --help/dry path is safe. Use subprocess + a tmp HOME via env. These verify correctness; they need not add Python line coverage.` },
]

phase('Author tests')
const results = (await parallel(GROUPS.map(g => () =>
  agent(`${COMMON}\n\n=== YOUR ASSIGNMENT (${g.key}) ===\n${g.spec}`,
    { label: `w5:${g.key}`, phase: 'Author tests', schema: RET, model: g.model })
))).filter(Boolean)

const totalPass = results.reduce((s, r) => s + (r.tests_passing || 0), 0)
const totalFail = results.reduce((s, r) => s + (r.tests_failing || 0), 0)
const allFiles = results.flatMap(r => r.test_files || [])
log(`W5 done: ${allFiles.length} test files, ${totalPass} passing, ${totalFail} failing`)
return { groups: results, total_tests_passing: totalPass, total_tests_failing: totalFail, test_files: allFiles }

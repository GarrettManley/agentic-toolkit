# The Architecture of Hybrid Context Synthesis | Agentic Protocol

## 1. File Modification Standards
- **Surgical Edits (Preferred):** Use the `replace` tool for modifications to files over **100 lines** or for precision changes to well-known blocks.
- **Full Overwrites:** Use `write_file` for new file creation or small configuration files (under 100 lines) where the risk of hallucination is low.
- **Safety Protocol:** When `replace` fails due to match errors, perform a `read_file` with limited context (e.g. `start_line` / `end_line`) to verify exact whitespace and line endings before retrying.

## 2. Token Budgeting
- **Search Scope:** Always use `include_pattern` to narrow `grep_search` results.
- **Reading Limits:** Avoid reading more than 200 lines at once. Use `start_line` and `end_line` for targeted research.

## 3. Finality & Verification
- **Pre-commit Audit:** Before declaring a task complete, run `_scripts/pre_commit_audit.ps1` to catch trivial syntax and placeholder errors.
- **Mandatory Verification:** All implementation tasks must conclude with a verification step (e.g. running a test, build, or `verify_workspace.ps1`). A task is only complete when its behavioral correctness is verified.
- **Continuous Optimization:** Findings from the `.gemini/experiments.yaml` registry should be reviewed weekly to update these core protocols.

## 4. Corporate Repository Isolation
- **Strict Isolation:** NEVER touch, scan, or read the `/malachite/` or `/Duracell/` repositories or any associated corporate folders unless explicitly directed for a specific task in that context.
- **Privacy First:** Ensure all published work (e.g., the lab website) is purged of internal project names or repository identifiers.

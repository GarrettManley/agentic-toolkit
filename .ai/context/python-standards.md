---
topic: Python Engineering Standards
last_verified: 2026-03-25
source_tier: 1 (Canonical)
proof_type: Internal (Empirical)
verification_cmd: "ruff --version; pytest --version"
evidence: "Verified modern toolset availability"
model_used: Gemini Pro
---

# Global Python Standards

Standard practices for all Python projects in this workspace, modernizing the legacy `mohs/agents.md` guidelines.

## 1. Code Style & Linting
- **Formatter**: Use `ruff format` (replaces Black/Isort).
- **Linter**: Use `ruff check` (replaces Flake8/Pylint).
- **Line Length**: 88 characters (standard for modern tools).
- **Typing**: Use Type Hints for all public API signatures.

## 2. Testing (The Verification Layer)
- **Engine**: Always use `pytest`.
- **Convention**: Arrange-Act-Assert pattern.
- **Agent Rule**: Any code change **must** include a corresponding unit test pass recorded in the ADR or Truth File metadata.

## 3. Tooling
- Prefer `pyproject.toml` for all dependency management.
- Use `uv` or `pip` for package management (Agents are permitted to install if required for verification).

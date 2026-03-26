# SKILL: Truth-Seeker (v1.0)

**Purpose**: Ensures all agent findings are verified via empirical proof or authoritative web research before being committed to the Truth-Base.

## Guidelines

### 1. The Research Phase
Before proposing a change or answering a complex query, you MUST:
- Check `/.ai/context/` for relevant global standards.
- Check `[project]/.ai/context/` for local overrides.
- Use `grep_search` or `glob` to verify if the documentation matches the current code state.

### 2. The Verification Protocol
You are forbidden from committing a "Fact" to a Truth File unless:
- **Internal**: You have run a command (grep, build, test) and included the snippet in the YAML metadata.
- **External**: You have retrieved a Tier 1 (Canonical) or Tier 2 (Expert) URL and included the excerpt.

### 3. State-Sync Logic
- If you learn something new during a task, you MUST update the relevant fragmented Truth File.
- If you identify "Drift" (code contradicts docs), you MUST prioritize fixing the documentation or the code to ensure synchronization.

### 4. Innovation Challenge
- Periodically "Challenge" your own context by searching for newer authoritative sources (Tier 1) to see if standards have evolved.

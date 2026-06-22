---
title: "Core Script: archive / README.md"
date: 2026-06-22
draft: false
---

# Core Script: archive / README.md

```text
# Archived scripts

Retired 2026-06-12 when Ollama was uninstalled from this machine (Aether
retired it from production in aether-engine#173; the local GGUFs were
extracted to `C:\models` and llama-server is the only local runtime).

- `fast_orchestrator.py` — local orchestration loop via `ollama.chat`
  (`qwen-orchestrator`). ADR-002-era; nothing scheduled or imported it.
- `refine_content.py` — local audit pass via `MFDoom/deepseek-r1-tool-calling:8b`.
- `evolve_personas.py` — persona evolution via the same model.

All three depend on the `ollama` Python client and the Ollama daemon, neither
of which is installed anymore. If a local-model tier is revived it will be on
llama-server (OpenAI `/v1/chat/completions`, one-model-per-process) — scoped
under harness-backlog hb-28u.8, not by resurrecting these as-is.

```

---
*Published from .ai active toolkit.*

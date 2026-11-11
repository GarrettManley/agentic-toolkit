# Archived scripts

Retired 2026-06-12 when Ollama was uninstalled from this machine (Aether
retired it from production first; the local GGUFs were extracted to a local
models directory and llama-server is the only local runtime).

- `fast_orchestrator.py` — local orchestration loop via `ollama.chat`
  (`qwen-orchestrator`). ADR-002-era; nothing scheduled or imported it.
- `refine_content.py` — local audit pass via `MFDoom/deepseek-r1-tool-calling:8b`.
- `evolve_personas.py` — persona evolution via the same model.

All three depend on the `ollama` Python client and the Ollama daemon, neither
of which is installed anymore. If a local-model tier is revived it will be on
llama-server (OpenAI `/v1/chat/completions`, one-model-per-process) — scoped
in the harness backlog, not by resurrecting these as-is.

# scripts/llm/generate.py
"""Stage 4b orchestrator: recon items -> validated, scope-bounded hypotheses.

Per recon item: select playbooks (skip if none), build prompt, call the LLM,
stamp server fields, validate against the full hypothesis schema, hard-drop any
target not in the SAME program's scope, de-dupe within the run, persist to
runtime/hypotheses/<slug>/. ScopeViolation propagates uncaught; LLMUnavailable
isolates to the single asset."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from lib import ledger
from lib.paths import RUNTIME_DIR
from lib.scope_match import is_in_scope

from llm.client import LLMClient, LLMUnavailable, select_client
from llm.playbook import PLAYBOOKS_DIR, load_playbooks, select_playbooks
from llm.prompt import build_prompt
from llm.schema import load_schema, validate_hypothesis, wrapper_schema

RUNTIME_HYPOTHESES_DIR = RUNTIME_DIR / "hypotheses"


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _advisory_fixed_version(item: dict, cve: str | None) -> str | None:
    """Return the fixed version from the recon item's advisory matching ``cve``.

    Recon (scripts/recon/advisories.py) extracts ``fixed`` from OSV events into
    each known_advisories entry. Used to server-stamp evidence_seed.fixed_version
    so the differential oracle's fixed-version target is deterministic, not
    LLM-authored."""
    if not cve:
        return None
    for adv in item.get("known_advisories", []) or []:
        if adv.get("cve") == cve and adv.get("fixed"):
            return adv["fixed"]
    return None


def generate_hypotheses(scopes: dict, recon: list, *, client: LLMClient | None = None,
                        provider: str | None = None, playbooks_root: Path | None = None,
                        hyp_root: Path | None = None, now: datetime | None = None) -> list[dict]:
    playbooks = load_playbooks(playbooks_root or PLAYBOOKS_DIR)
    if not playbooks:
        return []  # cold-start guard: never prompt with no playbook

    client = client or select_client(provider)
    now = now or datetime.now(timezone.utc)
    hyp_root = hyp_root or RUNTIME_HYPOTHESES_DIR
    full_schema = load_schema()
    model_schema = wrapper_schema(full_schema)

    accepted: list[dict] = []
    seen: set[tuple] = set()
    seq = 0

    for item in recon:
        eligible = select_playbooks(item, playbooks)
        if not eligible:
            continue
        slug = item.get("slug", "")
        system, messages = build_prompt(item, eligible)
        try:
            resp = client.complete_json(system=system, messages=messages, schema=model_schema)
        except LLMUnavailable:
            ledger.append_event("hypothesis-llm-unavailable", slug=slug,
                                asset=item.get("asset", {}).get("identifier"))
            continue

        try:
            raw = json.loads(resp.text).get("hypotheses", [])
        except json.JSONDecodeError:
            ledger.append_event("hypothesis-parse-error", slug=slug)
            continue

        for h in raw:
            seq += 1
            h["hypothesis_id"] = f"HYP-{now.strftime('%Y-%m-%d')}-{seq:03d}"
            h["generated_at"] = _iso(now)
            h["generator"] = {"provider": resp.provider, "model": resp.model}
            h["recon_ref"] = {"slug": slug,
                              "asset_identifier": item.get("asset", {}).get("identifier", ""),
                              "recon_ts": item.get("recon_ts", "")}
            ok, errors = validate_hypothesis(h)
            if not ok:
                ledger.append_event("hypothesis-invalid", slug=slug, errors=errors[:3])
                continue
            seed = h.setdefault("evidence_seed", {})
            if not (seed.get("fixed_version") or "").strip():
                fixed = _advisory_fixed_version(item, seed.get("candidate_cve_id"))
                if fixed:
                    seed["fixed_version"] = fixed
            tgt = h["target"]
            in_scope, prog = is_in_scope(tgt["asset_type"], tgt["identifier"])
            if not in_scope or prog != slug:
                ledger.append_event("hypothesis-out-of-scope", slug=slug,
                                    target=tgt["identifier"], resolved=prog)
                continue
            key = (tgt["identifier"], h["vuln_class"], h["source_playbook"]["technique"])
            if key in seen:
                continue
            seen.add(key)
            accepted.append(h)

    _persist(accepted, hyp_root)
    return accepted


def _persist(hypotheses: list[dict], hyp_root: Path) -> None:
    by_slug: dict[str, list[dict]] = {}
    for h in hypotheses:
        by_slug.setdefault(h["program_slug"], []).append(h)
    for slug, items in by_slug.items():
        prog_dir = hyp_root / slug
        prog_dir.mkdir(parents=True, exist_ok=True)
        (prog_dir / "hypotheses.json").write_text(
            json.dumps(items, indent=2), encoding="utf-8")

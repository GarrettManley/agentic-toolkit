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


# Models frequently emit evidence_seed using the *finding* vocabulary
# (schema/evidence.schema.json field names) that the class playbook references, rather
# than the *hypothesis* evidence_seed keys the pipeline reads. LLM output is a system
# boundary, so normalize the known aliases onto the canonical keys once, here.
_SEED_KEY_ALIASES = {
    "cve_id_proposed_or_assigned": "candidate_cve_id",
    "cve_id": "candidate_cve_id",
    "attack_vector": "attack_vector_hypothesis",
}


def _normalize_seed_keys(seed: dict) -> None:
    """Map finding-vocabulary aliases onto canonical hypothesis evidence_seed keys
    (only when the canonical key isn't already populated)."""
    for alias, canonical in _SEED_KEY_ALIASES.items():
        if alias in seed and not seed.get(canonical):
            seed[canonical] = seed.pop(alias)


def _stamp_or_drop(obj: dict, key: str, value) -> None:
    """Server-stamp a recon-ground-truth field, or DROP any model-supplied value when recon
    cannot supply one — so an untrusted model value never rides through (cf. _resolve_fixed_version)."""
    if value:
        obj[key] = value
    else:
        obj.pop(key, None)


def _normalize_authored(h: dict, item: dict) -> None:
    """Align a model-authored hypothesis with the seed-completeness gate at the system
    boundary. Seed-key aliases are backfill-only. For ``dependency-cve``, the seed's package
    identity and the install version are RECON GROUND TRUTH: package_ecosystem/package_name
    feed ``npm install`` (verify/llm_strategy.py) and the install version pins the differential
    target, so each is stamped from recon or DROPPED — never a model value riding through (a
    dropped field then fails the support gate rather than installing an unverified package).
    candidate_cve_id stays model-authored (the hypothesis's claim, cross-checked by
    _resolve_fixed_version). NOTE: target.identifier (the scope/dedup key) is intentionally left
    model-authored and scope-checked downstream; pinning it to the recon asset to close the
    latent seed-vs-target divergence is a tracked follow-up (would otherwise moot the scope gate)."""
    seed = h.setdefault("evidence_seed", {})
    _normalize_seed_keys(seed)
    if h.get("vuln_class") != "dependency-cve":
        return
    asset = item.get("asset", {}) or {}
    _stamp_or_drop(seed, "package_ecosystem", asset.get("ecosystem"))
    _stamp_or_drop(seed, "package_name", asset.get("identifier"))
    _stamp_or_drop(h.setdefault("target", {}), "version_or_revision", item.get("resolved_version"))


def _resolve_fixed_version(item: dict, seed: dict) -> None:
    """Enforce server-controlled trust boundary for evidence_seed.fixed_version.

    Always takes fixed_version from the trusted recon advisory, overwriting any
    LLM-supplied value.  If no advisory match exists, drops any LLM-supplied
    fixed_version so it can never be used as a trust boundary for the
    differential fixed-version install."""
    fixed = _advisory_fixed_version(item, seed.get("candidate_cve_id"))
    if fixed:
        seed["fixed_version"] = fixed       # trusted recon advisory value (overwrite)
    else:
        seed.pop("fixed_version", None)     # no trusted source -> never trust an LLM-supplied pin


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
            _normalize_authored(h, item)
            if h.get("vuln_class") == "dependency-cve":
                tgt = h.get("target") or {}
                asset_id = (item.get("asset") or {}).get("identifier")
                # The recon-stamped seed (package_name/version) describes THIS recon asset, so the
                # finding's target must be it too. A model targeting a sibling package — even one in
                # scope — would file the finding under a target the PoC never tests. Drop with a trace.
                if asset_id and tgt.get("identifier") != asset_id:
                    ledger.append_event("hypothesis-target-divergence", slug=slug,
                                        target=tgt.get("identifier"), recon_asset=asset_id)
                    continue
                # Recon could not supply an install version; a dependency-cve PoC is impossible.
                # Drop with a trace rather than persist an accepted-but-un-PoC-able hypothesis.
                if not tgt.get("version_or_revision"):
                    ledger.append_event("hypothesis-version-unresolved", slug=slug,
                                        target=tgt.get("identifier"))
                    continue
            ok, errors = validate_hypothesis(h)
            if not ok:
                ledger.append_event("hypothesis-invalid", slug=slug, errors=errors[:3])
                continue
            seed = h.setdefault("evidence_seed", {})
            _resolve_fixed_version(item, seed)
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

"""hb-0vq authoring-reliability harness.

Two scored tracks against a fixed CVE reference (minimatch / CVE-2022-3517),
isolating local-model grammar-constrained authoring quality from the rest of
the pipeline:

- Track A scores hypothesis-seed completeness: the fraction of trials in which
  the model emits a model_item_schema-valid dependency-cve hypothesis whose
  evidence_seed is complete enough to drive Stage 4c (npm package + name + CVE
  + affected version). Validation is at the *model-output* altitude
  (model_item_schema), because server-stamped fields are added afterward and
  must not be invented by the model.
- Track B scores PoC authoring: the fraction of trials in which the model
  authors a PoC that the real differential oracle scores ``verified``.

Both tracks are LLM-provider-agnostic (env SECRESEARCH_LLM_PROVIDER /
SECRESEARCH_LLAMA_MODEL). The scorers themselves are offline-testable via a
fake client (Track A) and an injected runner (Track B).
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import jsonschema

# Bootstrap scripts/ (and hooks/) onto sys.path so the module runs both under
# pytest (conftest adds them) and as a standalone CLI. Mirrors scripts/sandbox/doctor.py.
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
for _p in (str(_SCRIPTS_DIR), str(_SCRIPTS_DIR.parent / "hooks")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from llm.client import LLMClient, LLMUnavailable  # noqa: E402
from llm.generate import _normalize_seed_keys  # noqa: E402
from llm.playbook import PLAYBOOKS_DIR, load_playbooks, select_playbooks  # noqa: E402
from llm.prompt import build_prompt  # noqa: E402
from llm.schema import load_schema, model_item_schema, wrapper_schema  # noqa: E402

# A dependency-cve hypothesis is PoC-ready iff the LLMPocStrategy support gate
# (minus the server-stamped fixed_version) is satisfiable from the model's own
# output: npm ecosystem, a package name, a candidate CVE, and a target version.
_SEED_FIELDS = ("package_name", "candidate_cve_id")


def seed_complete(hyp: dict) -> bool:
    if hyp.get("vuln_class") != "dependency-cve":
        return False
    seed = hyp.get("evidence_seed") or {}
    target_ver = (hyp.get("target") or {}).get("version_or_revision") or ""
    return bool(
        (seed.get("package_ecosystem") or "").strip() == "npm"
        and all((seed.get(f) or "").strip() for f in _SEED_FIELDS)
        and target_ver.strip()
    )


@dataclass
class TrackAResult:
    model: str
    trials: int
    complete: int
    parse_errors: int
    invalid: int
    empty_seed: int

    @property
    def rate(self) -> float:
        return self.complete / self.trials if self.trials else 0.0


def score_track_a(recon_item: dict, *, client: LLMClient, trials: int,
                  playbooks_root=None) -> TrackAResult:
    """Run ``trials`` hypothesis-generation calls and score seed completeness.

    Reproduces the inner authoring loop of llm.generate.generate_hypotheses
    (build prompt -> complete_json -> parse -> normalize seed -> validate item ->
    seed_complete) WITHOUT the scope/dedup/persist plumbing, so the score
    reflects model authoring quality alone.
    """
    playbooks = load_playbooks(playbooks_root or PLAYBOOKS_DIR)
    eligible = select_playbooks(recon_item, playbooks)
    system, messages = build_prompt(recon_item, eligible)
    model_schema = wrapper_schema(load_schema())
    item_validator = jsonschema.Draft202012Validator(model_item_schema(load_schema()))

    complete = parse_errors = invalid = empty_seed = 0
    for _ in range(trials):
        try:
            resp = client.complete_json(system=system, messages=messages, schema=model_schema)
            hyps = json.loads(resp.text).get("hypotheses", [])
        except (LLMUnavailable, json.JSONDecodeError):
            parse_errors += 1
            continue
        trial_ok = False
        for h in hyps:
            _normalize_seed_keys(h.setdefault("evidence_seed", {}))
            if not (h.get("evidence_seed") or {}):
                empty_seed += 1
            if list(item_validator.iter_errors(h)):
                invalid += 1
                continue
            if seed_complete(h):
                trial_ok = True
        if trial_ok:
            complete += 1
    return TrackAResult(getattr(client, "model", "?"), trials, complete,
                        parse_errors, invalid, empty_seed)


@dataclass
class TrackBResult:
    model: str
    trials: int
    verified: int
    refuted: int
    error: int
    skipped: int

    @property
    def rate(self) -> float:
        return self.verified / self.trials if self.trials else 0.0


def score_track_b(hypothesis: dict, *, client: LLMClient, trials: int,
                  runner=subprocess.run) -> TrackBResult:
    """Run ``trials`` LLM PoC-authoring attempts for a fixed, already-valid
    hypothesis through the real differential oracle (verify_hypotheses) and score
    the fraction the oracle confirms ``verified``.

    The hypothesis is held constant so the score isolates PoC-authoring quality
    from seed quality (which Track A measures). ``runner`` is injectable so the
    scorer is offline-testable without Docker.
    """
    # Lazy import: verify.harness pulls in the sandbox stack, unneeded for Track A.
    from verify.harness import verify_hypotheses
    from verify.llm_strategy import LLMPocStrategy

    counts = {"verified": 0, "refuted": 0, "error": 0, "skipped": 0}
    for i in range(trials):
        hyp = dict(hypothesis)
        hyp["hypothesis_id"] = f"{hypothesis['hypothesis_id']}-{i}"
        results = verify_hypotheses([hyp], strategy=LLMPocStrategy(client=client), runner=runner)
        verdict = results[0]["verdict"]
        counts[verdict] = counts.get(verdict, 0) + 1
    return TrackBResult(getattr(client, "model", "?"), trials, counts["verified"],
                        counts["refuted"], counts["error"], counts["skipped"])


def main(argv: list[str] | None = None) -> int:
    import argparse
    from pathlib import Path

    from llm.client import select_client

    ap = argparse.ArgumentParser(description="hb-0vq local-authoring reliability eval")
    ap.add_argument("--track", choices=["a", "b", "both"], default="both")
    ap.add_argument("--trials", type=int, default=10)
    ap.add_argument("--report", type=Path, help="write the JSON report to this path")
    args = ap.parse_args(argv)

    fix = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "llm"
    client = select_client()  # honors SECRESEARCH_LLM_PROVIDER / SECRESEARCH_LLAMA_MODEL
    out: dict = {"model": getattr(client, "model", "?"), "provider": client.provider,
                 "trials": args.trials}
    if args.track in ("a", "both"):
        recon = json.loads((fix / "recon_item_minimatch.json").read_text(encoding="utf-8"))
        a = score_track_a(recon, client=client, trials=args.trials)
        out["track_a"] = a.__dict__ | {"rate": a.rate}
    if args.track in ("b", "both"):
        hyp = json.loads((fix / "hypothesis_minimatch.json").read_text(encoding="utf-8"))
        b = score_track_b(hyp, client=client, trials=args.trials)
        out["track_b"] = b.__dict__ | {"rate": b.rate}

    print(json.dumps(out, indent=2))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

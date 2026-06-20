"""Exp 006 case generator - Grammar-Constrained Dependency Scheduling.

Deterministic (SEED=42), pure stdlib. Emits three artifacts next to this file:
  cases.json      - the blind task set (no answers), one entry per DAG case
  gold.json       - the earliest-finish-time solution for each case (the graded truth)
  cases_meta.json - run metadata (seed, band split, deadline balance)

A reader reproduces the benchmark by: `python gen_cases.py` then `python verify_gold.py`
then `python eval.py`. The gold is a forward earliest-finish-time pass; verify_gold.py
re-derives it independently so you never have to trust this file.
"""
import json
import os
import random

SEED = 42
HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = "ABCDEF"

# (band name, n_cases, node_count N, edge probability p) - hard-stratified difficulty gradient
BANDS = [
    ("easy_N4", 20, 4, 0.35),
    ("med_N5", 20, 5, 0.45),
    ("hard_N6", 20, 6, 0.55),
]


def build_dag(rng, n, p, hard):
    """Forward-only edges over a random linear order => guaranteed acyclic.
    In-degree capped at 2 to keep the arithmetic hand-traceable."""
    labels = list(LABELS[:n])
    while True:
        order = labels[:]
        rng.shuffle(order)
        indeg = {l: 0 for l in labels}
        edges = []
        for i in range(n):
            for j in range(i + 1, n):
                u, v = order[i], order[j]
                if indeg[v] < 2 and rng.random() < p:
                    edges.append([u, v])
                    indeg[v] += 1
        if not edges:
            continue  # must have >=1 dependency
        if hard and len(edges) < 3:
            continue  # HARD band must actually be hard
        return labels, edges


def solve(labels, edges, dur):
    """Earliest-finish-time forward pass. EFT[n] = dur[n] + max(EFT[preds], default 0)."""
    preds = {l: [] for l in labels}
    succ = {l: [] for l in labels}
    for u, v in edges:
        preds[v].append(u)
        succ[u].append(v)
    indeg = {l: len(preds[l]) for l in labels}
    avail = sorted(l for l in labels if indeg[l] == 0)
    topo = []
    while avail:
        node = avail.pop(0)
        topo.append(node)
        for w in succ[node]:
            indeg[w] -= 1
            if indeg[w] == 0:
                avail.append(w)
        avail.sort()  # alphabetical tie-break -> one canonical reference order
    eft = {}
    for node in topo:
        eft[node] = dur[node] + max((eft[p] for p in preds[node]), default=0)
    return eft, max(eft.values()), topo


def main():
    cases, gold, cpls = [], {}, {}
    idx = 0
    for band, count, n, p in BANDS:
        for _ in range(count):
            rng = random.Random(SEED * 1000 + idx)
            labels, edges = build_dag(rng, n, p, band == "hard_N6")
            dur = {l: rng.randint(2, 8) for l in labels}
            eft, cpl, topo = solve(labels, edges, dur)
            cid = f"c{idx:02d}"
            cases.append({"case_id": cid, "band": band, "n_nodes": n,
                          "nodes": labels, "durations": dur, "edges": edges,
                          "deadline": None})
            gold[cid] = {"finish_times": eft, "critical_path_length": cpl,
                         "deadline_met": None}
            cpls[cid] = cpl
            idx += 1

    # Boundary determinism (graft): force >=2 cases/band to deadline == cpl exactly,
    # so the discriminating "meets-exactly" comparison is always exercised.
    boundary = set()
    for bi, (band, count, n, p) in enumerate(BANDS):
        rngb = random.Random(SEED * 7 + bi)
        boundary.update(rngb.sample(range(bi * 20, bi * 20 + count), 2))

    def assign(rng):
        for i, c in enumerate(cases):
            cpl = cpls[c["case_id"]]
            if i in boundary:
                c["deadline"] = cpl                       # met exactly (true)
            elif rng.random() < 0.5:
                c["deadline"] = max(1, cpl - rng.randint(1, 3))   # infeasible (false)
            else:
                c["deadline"] = cpl + rng.randint(0, 3)           # feasible (true)
            gold[c["case_id"]]["deadline_met"] = cpl <= c["deadline"]

    # Balance deadline_met to 40-60% true; the 50/50 coin makes this converge fast.
    rngd = random.Random(SEED * 13)
    frac = 0.0
    for _ in range(500):
        assign(rngd)
        met = sum(1 for c in cases if gold[c["case_id"]]["deadline_met"])
        frac = met / len(cases)
        if 0.40 <= frac <= 0.60:
            break

    met = sum(1 for c in cases if gold[c["case_id"]]["deadline_met"])
    meta = {"seed": SEED, "n_cases": len(cases),
            "bands": {b[0]: b[1] for b in BANDS},
            "node_counts": {b[0]: b[2] for b in BANDS},
            "edge_probs": {b[0]: b[3] for b in BANDS},
            "deadline_met_count": met, "deadline_unmet_count": len(cases) - met,
            "boundary_cases": sorted(f"c{i:02d}" for i in boundary),
            "llama_server_build": "9596", "generated_by": "gen_cases.py"}

    for name, obj in [("cases.json", cases), ("gold.json", gold), ("cases_meta.json", meta)]:
        with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
    print(f"wrote {len(cases)} cases; deadline_met {met}/{len(cases)} ({frac:.0%}); "
          f"boundary {sorted(boundary)}")


if __name__ == "__main__":
    main()

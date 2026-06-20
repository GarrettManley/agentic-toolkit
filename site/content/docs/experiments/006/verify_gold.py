"""Independently re-derive Exp 006 gold from cases.json and assert it matches gold.json.
Confirms the published answers without trusting gen_cases.py. Pure stdlib."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def solve(labels, edges, dur):
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
        avail.sort()
    eft = {}
    for node in topo:
        eft[node] = dur[node] + max((eft[p] for p in preds[node]), default=0)
    return eft, max(eft.values())


def main():
    cases = json.load(open(os.path.join(HERE, "cases.json"), encoding="utf-8"))
    gold = json.load(open(os.path.join(HERE, "gold.json"), encoding="utf-8"))
    bad = 0
    for c in cases:
        eft, cpl = solve(c["nodes"], c["edges"], c["durations"])
        g = gold[c["case_id"]]
        if eft != g["finish_times"]:
            print(f"{c['case_id']}: finish_times mismatch {eft} != {g['finish_times']}"); bad += 1
        if cpl != g["critical_path_length"]:
            print(f"{c['case_id']}: cpl mismatch {cpl} != {g['critical_path_length']}"); bad += 1
        if (cpl <= c["deadline"]) != g["deadline_met"]:
            print(f"{c['case_id']}: deadline_met mismatch"); bad += 1
    print(f"OK: {len(cases)} cases, gold independently verified" if bad == 0
          else f"FAIL: {bad} mismatches")
    return bad


if __name__ == "__main__":
    raise SystemExit(1 if main() else 0)

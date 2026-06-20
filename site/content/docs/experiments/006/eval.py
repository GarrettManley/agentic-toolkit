"""Exp 006 harness - Grammar-Constrained Dependency Scheduling across local GGUF models.

Runs each model one-process-at-a-time through llama-server (8 GB VRAM ceiling), sends the
60 seeded scheduling cases under a json_schema grammar constraint, grades with a deterministic
4/4 oracle against earliest-finish-time gold, and writes:
  data.json          - lean multi-model artifact the Hugo shortcode reads
  results_full.json   - per-band / per-component breakdown + run metadata
  <scratch>/raw/<slug>/<case>.json - full per-trial audit trail (NOT published)

Pure stdlib. Reproduce: `python gen_cases.py && python verify_gold.py && python eval.py`.
temperature=0 greedy -> bit-reproducible on the same GPU.
"""
import argparse
import json
import math
import os
import socket
import statistics
import subprocess
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LLAMA = r"C:\llama\llama-server.exe"
RAW_DIR = r"C:\Users\Garre\Workspace\.exp006-scratch\raw"  # outside the published bundle
PORT = 8099
BASE = f"http://127.0.0.1:{PORT}"

MODELS = [
    {"slug": "deepseek-r1-7b",   "gguf": r"C:\models\deepseek-r1-7b-Q4_K_M.gguf"},
    {"slug": "qwen2.5-coder-7b", "gguf": r"C:\models\qwen2.5-coder-7b-Q4_K_M.gguf"},
    {"slug": "llama3.1-8b",      "gguf": r"C:\models\llama3.1-8b-Q4_K_M.gguf"},
    {"slug": "gemma-4-E4B",      "gguf": r"C:\models\gemma-4-E4B-it-Q4_K_M.gguf"},
    {"slug": "phi4-mini",        "gguf": r"C:\models\phi4-mini-Q4_K_M.gguf"},
]

SCHEMA = {"name": "scheduling_answer", "strict": True, "schema": {
    "type": "object", "additionalProperties": False,
    "required": ["reasoning", "topo_order", "finish_times", "critical_path_length", "deadline_met"],
    "properties": {
        "reasoning": {"type": "string"},
        "topo_order": {"type": "array", "items": {"type": "string"}},
        "finish_times": {"type": "object", "additionalProperties": {"type": "integer"}},
        "critical_path_length": {"type": "integer"},
        "deadline_met": {"type": "boolean"},
    }}}

SYSTEM = (
    "You are a precise project-scheduling solver. You answer ONLY with a single JSON object "
    "matching the provided schema. Always fill the \"reasoning\" field FIRST and use it to derive "
    "the answer step by step; the numeric fields you commit to must match the arithmetic you wrote "
    "there. A task can start only after ALL of its dependencies have finished; tasks with no "
    "dependencies start at time 0. Use integer time units only.\n\n"
    "--- WORKED EXAMPLE (do NOT reuse these numbers) ---\n"
    "Tasks: X=3, Y=2, Z=4. Dependencies: X->Z, Y->Z. Deadline: 8.\n"
    "reasoning: \"X has no deps -> finishes at 3. Y has no deps -> finishes at 2. Z depends on X "
    "and Y -> starts at max(3,2)=3, finishes 3+4=7. Max finish = 7. 7 <= 8 so deadline met.\"\n"
    "topo_order: [\"X\",\"Y\",\"Z\"]\nfinish_times: {\"X\":3,\"Y\":2,\"Z\":7}\n"
    "critical_path_length: 7\ndeadline_met: true\n--- END EXAMPLE ---")


def user_prompt(case):
    tasks = "\n".join(f"{l}: {case['durations'][l]}" for l in case["nodes"])
    deps = "\n".join(f"{u} -> {v}" for u, v in case["edges"])
    labels = ", ".join(case["nodes"])
    return (f"Tasks and durations:\n{tasks}\n"
            f"Dependencies (\"U -> V\" means V cannot start until U has finished):\n{deps}\n"
            f"Project deadline: {case['deadline']} time units.\n\n"
            "Compute the earliest finish time for every task, the critical path length "
            "(max finish time), a valid execution order, and whether the deadline is met. "
            "Respond with JSON only.\n\n"
            f"NOTE: include exactly these task labels in finish_times and topo_order: {labels}.")


# ---------- deterministic oracle ----------
def grade(resp, gold_entry, edges, labels):
    comps = {"deadline_met": False, "critical_path_length": False,
             "finish_times": False, "topo_order": False}
    if not isinstance(resp, dict):
        return False, comps
    comps["deadline_met"] = isinstance(resp.get("deadline_met"), bool) and \
        resp["deadline_met"] == gold_entry["deadline_met"]
    try:
        comps["critical_path_length"] = int(resp["critical_path_length"]) == gold_entry["critical_path_length"]
    except (KeyError, TypeError, ValueError):
        comps["critical_path_length"] = False
    ft = resp.get("finish_times")
    if isinstance(ft, dict) and set(ft.keys()) == set(labels):
        try:
            comps["finish_times"] = all(int(ft[l]) == gold_entry["finish_times"][l] for l in labels)
        except (TypeError, ValueError):
            comps["finish_times"] = False
    to = resp.get("topo_order")
    if isinstance(to, list) and set(to) == set(labels):
        pos = {l: i for i, l in enumerate(to)}
        comps["topo_order"] = all(pos[u] < pos[v] for u, v in edges)
    return all(comps.values()), comps


def wilson(s, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = s / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z / d) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)


# ---------- server lifecycle ----------
def kill_all():
    subprocess.run(["taskkill", "/F", "/IM", "llama-server.exe"], capture_output=True, text=True)


def port_busy():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.5)
    try:
        return s.connect_ex(("127.0.0.1", PORT)) == 0
    finally:
        s.close()


def http(url, payload=None, timeout=5):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"},
                                 method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def start(gguf):
    args = [LLAMA, "--model", gguf, "--ctx-size", "8192", "--n-gpu-layers", "99",
            "--flash-attn", "on", "--cache-type-k", "q8_0", "--cache-type-v", "q8_0",
            "--seed", "42", "--port", str(PORT), "--host", "127.0.0.1"]
    log = open(os.path.join(RAW_DIR, "server.log"), "w", encoding="utf-8", errors="replace")
    return subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT), log


def wait_health(proc, timeout_s=120):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if proc.poll() is not None:
            return None
        try:
            if http(f"{BASE}/health", timeout=2).get("status") == "ok":
                return time.time() - t0
        except Exception:
            pass
        time.sleep(2)
    return None


def run_model(slug, gguf, cases, gold, max_tokens):
    kill_all()
    while port_busy():
        time.sleep(1)
    raw_model = os.path.join(RAW_DIR, slug)
    os.makedirs(raw_model, exist_ok=True)
    proc, log = start(gguf)
    load_s = wait_health(proc, 120)
    if load_s is None:
        log.close()
        try:
            with open(os.path.join(RAW_DIR, "server.log"), encoding="utf-8", errors="replace") as f:
                tail = "".join(f.readlines()[-8:])
        except Exception:
            tail = ""
        kill_all()
        return {"slug": slug, "load_failed": True, "note": tail[:300]}

    # warm-up (discard timing - removes cold-start skew)
    try:
        http(f"{BASE}/v1/chat/completions", {"messages": [{"role": "user", "content": "hi"}],
             "max_tokens": 1, "temperature": 0}, timeout=60)
    except Exception:
        pass

    per_comp = {k: 0 for k in ("deadline_met", "critical_path_length", "finish_times", "topo_order")}
    band_pass = {}
    band_tot = {}
    successes = 0
    tokens_total = 0
    tps_samples = []
    reason_chars = []
    schema_fail = 0
    t_start = time.time()
    for i, case in enumerate(cases):
        cid = case["case_id"]
        band = case["band"]
        band_tot[band] = band_tot.get(band, 0) + 1
        body = {"messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": user_prompt(case)}],
                "response_format": {"type": "json_schema", "json_schema": SCHEMA},
                "temperature": 0, "seed": 42, "max_tokens": max_tokens}
        parsed = None
        content = ""
        try:
            r = http(f"{BASE}/v1/chat/completions", body, timeout=180)
            content = r["choices"][0]["message"]["content"]
            tokens_total += r.get("usage", {}).get("completion_tokens", 0)
            tps = r.get("timings", {}).get("predicted_per_second")
            if tps:
                tps_samples.append(tps)
            try:
                parsed = json.loads(content)
            except Exception:
                schema_fail += 1
        except Exception as e:
            content = f"<request error: {e}>"
            schema_fail += 1
        passed, comps = grade(parsed, gold[cid], case["edges"], case["nodes"])
        if parsed is not None and isinstance(parsed.get("reasoning"), str):
            reason_chars.append(len(parsed["reasoning"]))
        for k, v in comps.items():
            per_comp[k] += 1 if v else 0
        if passed:
            successes += 1
            band_pass[band] = band_pass.get(band, 0) + 1
        with open(os.path.join(raw_model, f"{cid}.json"), "w", encoding="utf-8") as f:
            json.dump({"case_id": cid, "passed": passed, "components": comps,
                       "response": content}, f, indent=1)
        if (i + 1) % 15 == 0:
            print(f"    [{slug}] {i+1}/60  running pass={successes}", flush=True)
    elapsed = time.time() - t_start

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
    log.close()
    kill_all()

    n = len(cases)
    lo, hi = wilson(successes, n)
    return {
        "slug": slug, "load_failed": False, "load_s": round(load_s, 1),
        "trials": n, "successes": successes,
        "pass_k": round(successes / n, 4), "wilson_ci_low": lo, "wilson_ci_high": hi,
        "tokens_total": tokens_total,
        "tokens_per_success": round(tokens_total / max(successes, 1), 1),
        "tps": round(statistics.mean(tps_samples), 1) if tps_samples else 0,
        "reasoning_mean_chars": round(statistics.mean(reason_chars), 1) if reason_chars else 0,
        "schema_fail_count": schema_fail,
        "component_rates": {k: round(per_comp[k] / n, 4) for k in per_comp},
        "band_pass_rates": {b: round(band_pass.get(b, 0) / band_tot[b], 4) for b in band_tot},
        "elapsed_s": round(elapsed, 1),
    }


def write_outputs(model_rows, meta, max_tokens):
    lean = []
    for r in model_rows:
        if r.get("load_failed"):
            lean.append({"model": r["slug"], "quant": "Q4_K_M", "trials": 60, "successes": None,
                         "tokens_total": 0, "mean_steps": 1.0, "tps": 0, "pass_k": None,
                         "wilson_ci_low": None, "wilson_ci_high": None,
                         "note": "model failed to load on llama-server build 9596: " + r.get("note", "")[:160]})
            continue
        lean.append({"model": r["slug"], "quant": "Q4_K_M", "trials": r["trials"],
                     "successes": r["successes"], "tokens_total": r["tokens_total"],
                     "mean_steps": 1.0, "tps": r["tps"], "pass_k": r["pass_k"],
                     "wilson_ci_low": r["wilson_ci_low"], "wilson_ci_high": r["wilson_ci_high"],
                     "tokens_per_success": r["tokens_per_success"],
                     "reasoning_mean_chars": r["reasoning_mean_chars"],
                     "component_rates": r["component_rates"], "band_pass_rates": r["band_pass_rates"]})
    data = {"id": "006", "schema": "multi-model", "name": "Grammar-Constrained Dependency Scheduling",
            "task": ("Given a small DAG of tasks with integer durations and a deadline, emit "
                     "grammar-constrained JSON (reasoning-first, then topo_order + per-task "
                     "finish_times + critical_path_length + deadline_met); graded by a deterministic "
                     "4/4 oracle against precomputed earliest-finish-time gold."),
            "harness": "llama-server", "seed": 42, "n_cases": 60, "temperature": 0,
            "max_tokens": max_tokens, "llama_server_build": "9596", "models": lean}
    with open(os.path.join(HERE, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    full = {"meta": meta, "max_tokens": max_tokens, "models": model_rows}
    with open(os.path.join(HERE, "results_full.json"), "w", encoding="utf-8") as f:
        json.dump(full, f, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="all")
    ap.add_argument("--max-tokens", type=int, default=1536)
    ap.add_argument("--limit", type=int, default=0, help="run only first N cases (smoke test)")
    args = ap.parse_args()
    os.makedirs(RAW_DIR, exist_ok=True)
    cases = json.load(open(os.path.join(HERE, "cases.json"), encoding="utf-8"))
    if args.limit:
        cases = cases[:args.limit]
    gold = json.load(open(os.path.join(HERE, "gold.json"), encoding="utf-8"))
    meta = json.load(open(os.path.join(HERE, "cases_meta.json"), encoding="utf-8"))
    selected = MODELS if args.models == "all" else [m for m in MODELS if m["slug"] in args.models.split(",")]

    rows = []
    for m in selected:
        print(f"=== {m['slug']} ===", flush=True)
        t0 = time.time()
        row = run_model(m["slug"], m["gguf"], cases, gold, args.max_tokens)
        if row.get("load_failed"):
            print(f"    LOAD FAILED: {row.get('note','')[:120]}", flush=True)
        else:
            print(f"    done: pass_k={row['pass_k']:.2f} [{row['wilson_ci_low']:.2f},{row['wilson_ci_high']:.2f}] "
                  f"tps={row['tps']} tok/succ={row['tokens_per_success']} "
                  f"bands={row['band_pass_rates']} ({row['elapsed_s']:.0f}s)", flush=True)
        rows.append(row)
        write_outputs(rows, meta, args.max_tokens)  # incremental save after each model
        print(f"    [{time.time()-t0:.0f}s elapsed for this model; data.json updated]", flush=True)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()

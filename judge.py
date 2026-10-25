import argparse
import json
import os
import re
import subprocess
from collections import Counter
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor
from numeric import distinct

MATHLIB_DIR = os.environ.get("MATHLIB_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "mathlib4"))

FENCE = re.compile(r"```lean4?\s*(.*?)```", re.DOTALL)
BY = re.compile(r":=\s*by\b")
VETO = re.compile(r"\b(?:sorry(?:Ax)?|admit|native_decide|ofReduceBool)\b|\b(?:axiom|constant)\s+\w+\s*:")
PASSES = re.compile(r"^\s*Passes\s*:\s*(.+?)\s*$", re.M)
NUM = re.compile(r"^-?\d+(\.\d+)?$")


def split_proof(code):
    i = code.find("theorem ")
    m = BY.search(code, max(i, 0))
    return (code[:m.start()], code[m.end():]) if m else (code, "")


def stmt_key(code):
    head, _ = split_proof(code)
    head = "\n".join(l for l in head.splitlines() if not l.strip().startswith(("import ", "open ")))
    return " ".join(head.split())


def prepare(text, template, menu, top_c=2):
    blocks = FENCE.findall(text)
    if not blocks:
        return None
    proof = blocks[-1].strip()
    if "<candidate>" in proof:
        return None                                           
    pre, _, suf = stmt_key(template).partition("<candidate>")
    key = stmt_key(proof)
    if not (key.startswith(pre) and key.endswith(suf) and len(key) >= len(pre) + len(suf)):
        return None                                          
    _, body = split_proof(proof)
    if VETO.search(body):
        return None
    ms = PASSES.findall(text)
    raw = list(dict.fromkeys(v.strip() for v in re.findall(r"`([^`]+)`", ms[-1] if ms else "") if v.strip()))
    plain = all(NUM.match(v) for v in menu)
    values = [v for v in raw if v in menu or (plain and NUM.match(v))][:top_c]
    return (values, body) if values else None


def compiled(template, v):
    head, _ = split_proof(template.replace("<candidate>", f"({v})"))
    return head


def lean_ok(code, timeout=120):
    try:
        r = subprocess.run(["lake", "env", "lean", "--stdin"], input=code, text=True, capture_output=True,
                           timeout=timeout, cwd=MATHLIB_DIR)
    except subprocess.TimeoutExpired:
        return False
    return r.returncode == 0 and "declaration uses 'sorry'" not in r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/Experiment.json")
    ap.add_argument("--rolls", default="rolls.jsonl")
    ap.add_argument("--out", default="results.jsonl")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=120, help="seconds per Lean call")
    ap.add_argument("--top_c", type=int, default=2, help="how many declared values are compiled (the paper uses 2)")
    args = ap.parse_args()

    cards = json.load(open(args.data, encoding="utf-8"))
    rolls = [json.loads(l) for l in open(args.rolls, encoding="utf-8")]
    jobs = []
    samples = [[{"declared": [], "passed": []} for _ in r["rolls"]] for r in rolls]
    for k, (c, r) in enumerate(zip(cards, rolls)):
        for i, (text, fin) in enumerate(zip(r["rolls"], r["finish"])):
            p = prepare(text, c["template"], c["menu"], args.top_c) if fin != "length" else None
            for v in p[0] if p else []:
                samples[k][i]["declared"].append(v)
                jobs.append((k, i, v, compiled(c["template"], v) + ":= by" + p[1]))
    print(f"{len(rolls)} Question, {sum(len(r['rolls']) for r in rolls)} samples, {len(jobs)} Lean calls", flush=True)

    with ThreadPoolExecutor(args.workers) as ex:
        ok = list(ex.map(lambda j: lean_ok(j[3], args.timeout), jobs))
    passed = [[] for _ in rolls]
    for (k, i, v, _), good in zip(jobs, ok):
        if good:
            samples[k][i]["passed"].append(v)
            if v not in passed[k]:
                passed[k].append(v)

    stats = Counter()
    with open(args.out, "w", encoding="utf-8") as f:
        for c, vals, smp in zip(cards, passed, samples):
            pairs = [(a, b) for a, b in combinations(vals, 2) if distinct(c["menu"], a, b)]
            unfaithful = bool(pairs)
            f.write(json.dumps({"problem": c["problem"], "source": c["source"], "answer": c["answer"], "passed": vals,
                                "samples": smp, "pairs": pairs, "solved": bool(vals), "unfaithful": unfaithful}, ensure_ascii=False) + "\n")
            for g in (c["source"], "Overall"):
                stats[g, "cards"] += 1
                stats[g, "solved"] += bool(vals)
                stats[g, "unfaithful"] += unfaithful
    for g in ("AIME2024", "AIME2025", "AMC23", "Overall"):
        n = stats[g, "cards"]
        if not n:
            continue
        calls = len(jobs) if g == "Overall" else sum(1 for j in jobs if cards[j[0]]["source"] == g)
        print(f"{g:9s} Question {n:3d}  Lean accept {stats[g, 'solved']:3d} ({stats[g, 'solved'] / n:.1%})  "
              f"unfaithful {stats[g, 'unfaithful']:3d} ({stats[g, 'unfaithful'] / n:.1%})  Lean calls {calls}")


if __name__ == "__main__":
    main()

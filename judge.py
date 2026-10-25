"""Reproduction step 2: compile the declared values in rolls.jsonl -> results.jsonl and the paper's table."""
import argparse
import json
from collections import Counter
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor
from gobble_prover.judge import compiled, lean_ok, prepare
from gobble_prover.numeric import distinct


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
            p = prepare(text, c["template"], c.get("menu", []), args.top_c) if fin != "length" else None
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
            pairs = [(a, b) for a, b in combinations(vals, 2) if distinct(c.get("menu", []), a, b)]
            unfaithful = bool(pairs)
            f.write(json.dumps({"problem": c.get("problem"), "source": c.get("source", ""), "answer": c.get("answer"), "passed": vals,
                                "samples": smp, "pairs": pairs, "solved": bool(vals), "unfaithful": unfaithful}, ensure_ascii=False) + "\n")
            for g in (c.get("source", ""), "Overall"):
                stats[g, "cards"] += 1
                stats[g, "solved"] += bool(vals)
                stats[g, "unfaithful"] += unfaithful
    for g in ("AIME2024", "AIME2025", "AMC23", "Overall"):
        n = stats[g, "cards"]
        if not n:
            continue
        calls = len(jobs) if g == "Overall" else sum(1 for j in jobs if cards[j[0]].get("source", "") == g)
        print(f"{g:9s} Question {n:3d}  Lean accept {stats[g, 'solved']:3d} ({stats[g, 'solved'] / n:.1%})  "
              f"unfaithful {stats[g, 'unfaithful']:3d} ({stats[g, 'unfaithful'] / n:.1%})  Lean calls {calls}")


if __name__ == "__main__":
    main()

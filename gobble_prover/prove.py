"""Run Gobble-Prover on your own problems: sample proofs with vLLM, then compile the declared values with Lean."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations

from .judge import compiled, lean_ok, prepare
from .numeric import distinct
from .prompt import render

MODEL = "Pengzhen23/Gobble-Prover-1.7B"


def sample(problems, model=MODEL, n=1, max_tokens=30000, tp=1):
    """n prover outputs per problem with vLLM. Returns, per problem, a list of (text, finish_reason)."""
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    tok = AutoTokenizer.from_pretrained(model)
    prompts = [tok.apply_chat_template([{"role": "user", "content": render(p["template"], p.get("menu", []))}],
                                       add_generation_prompt=True, tokenize=False) for p in problems]
    llm = LLM(model=model, tensor_parallel_size=tp, max_model_len=max_tokens + 2048)
    sp = SamplingParams(n=n, temperature=1.0, top_p=1.0, top_k=-1, max_tokens=max_tokens)
    return [[(x.text, x.finish_reason) for x in o.outputs] for o in llm.generate(prompts, sp)]


def judge(problem, rolls, lean=True, top_c=2, timeout=120, workers=8):
    """Parse the prover outputs of one problem and compile every (value, proof) they declare (unless lean=False)."""
    template, menu = problem["template"], problem.get("menu", [])
    jobs, truncated = [], 0
    for text, fin in rolls:
        if fin == "length":
            truncated += 1
            continue
        p = prepare(text, template, menu, top_c)
        for v in p[0] if p else []:
            job = (v, compiled(template, v) + ":= by" + p[1])
            if job not in jobs:
                jobs.append(job)
    ok = [None] * len(jobs)
    if lean and jobs:
        with ThreadPoolExecutor(workers) as ex:
            ok = list(ex.map(lambda j: lean_ok(j[1], timeout), jobs))
    proofs, declared = {}, {}
    for (v, code), good in zip(jobs, ok):
        declared.setdefault(v, code)
        if good:
            proofs.setdefault(v, code)
    passed = list(proofs)
    pairs = [[a, b] for a, b in combinations(passed, 2) if distinct(menu, a, b)]
    return {"name": problem.get("name"), "passed": passed, "unfaithful": bool(pairs), "distinct_pairs": pairs,
            "proofs": proofs, "declared": declared, "samples": len(rolls), "truncated": truncated}


def prove(problems, model=MODEL, n=1, max_tokens=30000, tp=1, lean=True, top_c=2, timeout=120, workers=8):
    """problems: list of {"template": Lean 4 statement containing `<candidate>`, "menu": [candidate answers] (optional),
    "name": str (optional)}. Returns one dict per problem (see judge)."""
    rolls = sample(problems, model, n, max_tokens, tp)
    return [judge(p, r, lean, top_c, timeout, workers) for p, r in zip(problems, rolls)]


def dump(results, path):
    """JSON list, one field per line."""
    with open(path, "w", encoding="utf-8") as f:
        f.write("[\n" + ",\n".join(
            "{\n" + ",\n".join(f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}" for k, v in r.items()) + "\n}"
            for r in results) + "\n]\n")


def main():
    ap = argparse.ArgumentParser(description="Gobble-Prover: prove Lean 4 statements that come with candidate answers.")
    ap.add_argument("--input", required=True, help="JSON list of problems: {template, menu (optional), name (optional)}")
    ap.add_argument("--out", default="results.json")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--n", type=int, default=1, help="prover samples per problem")
    ap.add_argument("--max_tokens", type=int, default=30000)
    ap.add_argument("--tp", type=int, default=1, help="tensor parallel size")
    ap.add_argument("--no_lean", action="store_true", help="skip the Lean check; results then only list the declared values and their Lean files")
    ap.add_argument("--top_c", type=int, default=2, help="declared values compiled per sample (the paper uses 2)")
    ap.add_argument("--timeout", type=int, default=120, help="seconds per Lean call")
    ap.add_argument("--workers", type=int, default=8, help="parallel Lean calls")
    args = ap.parse_args()
    problems = json.load(open(args.input, encoding="utf-8"))
    results = prove(problems, args.model, args.n, args.max_tokens, args.tp, not args.no_lean, args.top_c, args.timeout, args.workers)
    dump(results, args.out)
    for i, r in enumerate(results):
        name = r["name"] or f"#{i}"
        if args.no_lean:
            print(f"{name}: declared {list(r['declared'])}")
        else:
            print(f"{name}: passed {r['passed']}" + ("  UNFAITHFUL statement (two distinct values proved)" if r["unfaithful"] else ""))
    print("wrote", args.out)


if __name__ == "__main__":
    main()

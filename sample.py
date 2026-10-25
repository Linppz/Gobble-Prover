"""Reproduction step 1: sample proofs for data/Experiment.json -> rolls.jsonl."""
import argparse
import json
from gobble_prover.prove import MODEL, sample

ap = argparse.ArgumentParser()
ap.add_argument("--model", default=MODEL)
ap.add_argument("--data", default="data/Experiment.json")
ap.add_argument("--out", default="rolls.jsonl")
ap.add_argument("--n", type=int, default=1, help="samples per formal statement (1, 4, 8, ...)")
ap.add_argument("--max_tokens", type=int, default=30000)
ap.add_argument("--tp", type=int, default=1, help="tensor parallel size")
args = ap.parse_args()
cards = json.load(open(args.data, encoding="utf-8"))
with open(args.out, "w", encoding="utf-8") as f:
    for rolls in sample(cards, args.model, args.n, args.max_tokens, args.tp):
        f.write(json.dumps({"rolls": [t for t, _ in rolls], "finish": [fin for _, fin in rolls]}, ensure_ascii=False) + "\n")
print("wrote", args.out, len(cards), "questions x", args.n, "samples")

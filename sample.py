import argparse
import json
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams
from prompt import render

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="Linppz/Gobble-Prover-1.7B")
ap.add_argument("--data", default="data/Experiment.json")
ap.add_argument("--out", default="rolls.jsonl")
ap.add_argument("--n", type=int, default=1, help="samples per formal statement (1, 4, 8, ...)")
ap.add_argument("--max_tokens", type=int, default=30000)
ap.add_argument("--tp", type=int, default=1, help="tensor parallel size")
args = ap.parse_args()
cards = json.load(open(args.data, encoding="utf-8"))
tok = AutoTokenizer.from_pretrained(args.model)
prompts = [tok.apply_chat_template([{"role": "user", "content": render(c["template"], c["menu"])}],
                                   add_generation_prompt=True, tokenize=False) for c in cards]
llm = LLM(model=args.model, tensor_parallel_size=args.tp, max_model_len=args.max_tokens + 2048)
sp = SamplingParams(n=args.n, temperature=1.0, top_p=1.0, top_k=-1, max_tokens=args.max_tokens)
with open(args.out, "w", encoding="utf-8") as f:
    for o in llm.generate(prompts, sp):
        f.write(json.dumps({"rolls": [x.text for x in o.outputs],
                            "finish": [x.finish_reason for x in o.outputs]}, ensure_ascii=False) + "\n")
print("wrote", args.out, len(cards), "questions x", args.n, "samples")

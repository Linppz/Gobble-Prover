# Reproduction: Gobble-Prover-1.7B on AIME 2024 / AIME 2025 / AMC23

## Paper

Efficient Proof Generation for Lean Statements with Multiple Candidate Answers.
Pengzhen Lin, Ke Zhang, Maziar Raissi, Zhouxing Shi. University of California, Riverside, 2026.

```bibtex
@article{lin2026efficient,
  title={Efficient Proof Generation for Lean Statements with Multiple Candidate Answers},
  author={Lin, Pengzhen and Zhang, Ke and Raissi, Maziar and Shi, Zhouxing},
  journal={arXiv preprint},
  year={2026}
}
```

## Model

https://huggingface.co/Linppz/Gobble-Prover-1.7B

This is our released model, Gobble-Prover-1.7B. You can download it
directly and run it on your own server to reproduce our work. hope you enjoy it!



## Files

| File | Purpose |
|---|---|
| `data/Experiment.json` | To make experimental reproduction faster, we have provided you with 100 questions, including AIME 2024 (30), AIME 2025 (30), and AMC23 (40). They all come from Kimina-Autoformalizer-7B with the correct answer. There is one question from AMC23 whose formal statement produced by the formalizer always failed type-checking, so we removed it. |
| `prompt.py` | The py file we use to concat the prompt. |
| `sample.py` | Samples proofs with vLLM. |
| `judge.py` | Decides which declared values are sent to Lean, compiles them, and reports the metrics. |
| `numeric.py` | Numeric distinctness of two passing values (menu candidates by construction, write-ins via SymPy and math_verify). |


## Requirements

* Python 3.10+, `pip install vllm transformers sympy math-verify` (tested with Python 3.11.15, vllm 0.10.2, transformers 4.55.2, torch 2.8.0+cu128)
* A GPU for sampling (the 1.7B model fits on a single 24 GB card).
* Lean 4.26.0 with Mathlib for judging, checked out into this folder (run from the folder that contains `judge.py`):
  ```bash
  curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh
  git clone --branch v4.26.0 --depth 1 https://github.com/leanprover-community/mathlib4.git
  cd mathlib4 && lake exe cache get && lake build && cd ..
  ```
  `lean-toolchain` of that checkout is `leanprover/lean4:v4.26.0`; elan installs it automatically.
  If Mathlib lives elsewhere, point `MATHLIB_DIR` to it.

## Run

Both steps run with no arguments:

```bash
python sample.py     # downloads the model from Hugging Face, one proof per formal statement -> rolls.jsonl
python judge.py      # compiles with ./mathlib4 -> results.jsonl and the summary table
```

Defaults: `--model Linppz/Gobble-Prover-1.7B`, `--n 1` (use `--n 4` or `--n 8` for
roll 4/8 times for each formal statement), `--out rolls.jsonl`; `judge.py` reads `rolls.jsonl`, writes `results.jsonl`, uses 8 workers and a
120 s timeout per Lean call (`--workers`, `--timeout`). `--top_c` sets how many declared values are compiled
(default 2, as in the paper)

Sampling settings: temperature 1.0, no top-p or top-k truncation, at most 30000 generated tokens, one user
message rendered by `prompt.py` through the model's chat template.

## Expected results

These 99 statements are the Kimina-Autoformalizer correct-answer subset of the paper's benchmark and each Formal statement's menu always own a ground-truth answer.
Table 1 in the paper averages over three formalizers, and each formal statement there has two versions, one formalized with the 
correct answer and one with an incorrect answer.

The numbers below were produced with this code (`python sample.py --n 5`, then `python judge.py`), i.e. pass@5 on
the 99 formal statements. 

Sampling took about 16 minutes on one RTX 6000 Ada (48 GB); Lean call took about 25 minutes with 8 workers. 

| Benchmark | Statements | Lean accept | Unfaithful |
|---|---|---|---|
| AIME 2024 | 30 | 26.7% | 13.3% |
| AIME 2025 | 30 | 16.7% | 6.7% |
| AMC23 | 39 | 30.8% | 5.1% |
| Overall | 99 | 25.3% | 8.1% |


## Output

`results.jsonl` has one line per formal statement: `passed` (compiled values), `samples` (per sample, the declared values and the ones that compiled), `pairs` (the pairs judged distinct), `solved`, `unfaithful`.
The script prints, per benchmark and overall, the question count (`Question`), Lean-accepted questions
(`Lean accept`, the `solved` field), unfaithful questions and Lean calls:

```
AIME2024  Question  30  Lean accept ...  unfaithful ...  Lean calls ...
AIME2025  Question  30  ...
AMC23     Question  39  ...
Overall   Question  99  ...
```

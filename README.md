# Gobble-Prover

**Gobble-Prover-1.7B** is a Lean 4 prover for *answer-construction* problems: theorem statements whose answer is
not known in advance and is given as a list of candidate answers, or as nothing at all. In one call it picks a
candidate it can prove, writes in its own answer when no candidate is right, and generates the proof. Every value it
reports comes with a complete Lean 4 file that compiled under Mathlib.

Model: https://huggingface.co/Pengzhen23/Gobble-Prover-1.7B (fine-tuned from
[AI-MO/Kimina-Prover-Distill-1.7B](https://huggingface.co/AI-MO/Kimina-Prover-Distill-1.7B) with supervised
fine-tuning followed by GRPO; 1.7B parameters, runs on a single 24 GB GPU).

Paper: *Efficient Proof Generation for Lean Statements with Multiple Candidate Answers*.
Pengzhen Lin, Ke Zhang, Maziar Raissi, Zhouxing Shi. University of California, Riverside, 2026.

## Why use it

* **One call for all candidates.** The usual pipeline proves each candidate answer separately. Gobble-Prover reads
  the whole candidate list, selects the value it can prove and proves it, reaching the same proof success rate as
  per-candidate proving at about one sixth of the token cost on MATH-500, AMC 2023 and AIME 2024/2025/2026.
* **Writes in missing answers.** When no candidate is right, or when no candidates are given, the prover proposes
  its own value and proves it.
* **Flags unfaithful statements.** The prover declares up to two values its proof covers. If two mathematically
  distinct values both compile under the same statement, the formal statement does not pin down the problem. The
  paper finds at least 6.1% of autoformalized competition statements this way, with no extra judge model.

## Install

```bash
git clone https://github.com/Linppz/Gobble-Prover.git
cd Gobble-Prover
pip install -e .          # vllm, transformers, sympy, math-verify
```

Tested with Python 3.11.15, vllm 0.10.2, transformers 4.55.2, torch 2.8.0+cu128. The model is downloaded from
Hugging Face on first use.

To check proofs you also need Lean 4.26.0 with Mathlib. Check it out into the repository folder (or anywhere, and
point `MATHLIB_DIR` to it):

```bash
curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh
git clone --branch v4.26.0 --depth 1 https://github.com/leanprover-community/mathlib4.git
cd mathlib4 && lake exe cache get && lake build && cd ..
```

`lean-toolchain` of that checkout is `leanprover/lean4:v4.26.0`; elan installs it automatically.

## Run your own problems

Write the problems as a JSON list. Each problem has

* `template`: a Lean 4 statement with the answer replaced by `<candidate>`, ending in `:= by sorry`;
* `menu` (optional): the candidate answers as strings, in the form they should appear in Lean; `[]` or omitted
  means the prover can only write in its own value;
* `name` (optional): any label, copied to the output.

`data/example.json` has three such problems (answer among the candidates; answer missing from the candidates; no
candidates):

```json
{
  "name": "product",
  "template": "import Mathlib\n\ntheorem product (a b : ℝ) (h₁ : a + b = 10) (h₂ : a - b = 4) :\n    a * b = <candidate> := by sorry",
  "menu": ["20", "24"]
}
```

Then run

```bash
gobble-prover --input data/example.json --n 4        # or: python prove.py --input data/example.json --n 4
```

`--n` is the number of prover samples per problem (more samples, more chances). `--no_lean` skips the Lean check for
machines without Mathlib. Other options: `--model`, `--max_tokens` (30000), `--tp` (tensor parallel size),
`--top_c` (declared values compiled per sample, 2 as in the paper), `--timeout` (120 s per Lean call),
`--workers` (8 parallel Lean calls), `--out` (`results.json`).

The output has one entry per problem:

| Field | Meaning |
|---|---|
| `passed` | values whose proof compiled |
| `proofs` | value → complete Lean file (statement with the value filled in, plus the proof) |
| `unfaithful` | true when two distinct values both passed, i.e. the statement does not determine the answer |
| `distinct_pairs` | the pairs of passing values judged distinct |
| `declared` | every value the prover declared, with its Lean file, whether or not it compiled (all you get with `--no_lean`) |
| `samples`, `truncated` | samples drawn, and how many hit the token limit |

Python:

```python
from gobble_prover import prove
results = prove([{"template": "...<candidate>...", "menu": ["4", "7"]}], n=4)
results[0]["passed"], results[0]["proofs"]
```

`gobble_prover.sample` and `gobble_prover.judge` are the two halves (vLLM sampling, parsing + Lean), usable
separately.

## How a sample is judged

The prover ends its answer with a line `Passes: \`v1\`, \`v2\`` and a `lean4` block. The first `top_c` declared
values are each substituted (in parentheses) into the template, the proof from the block is appended unchanged, and
the file is compiled with `lake env lean`. A sample is discarded when it has no Lean block, leaves `<candidate>` in
place, changes the statement outside the slot, or uses a vetoed tactic. A declared value is kept when it is one of
the candidates, or when it and all candidates are plain numbers (write-ins); this is the rule used for the paper's
numbers. Two passing values are "distinct" when they are different candidates, or, for write-ins, when SymPy and
math-verify both say they differ.

Sampling settings: temperature 1.0, no top-p or top-k truncation, at most 30000 generated tokens, one user message
rendered by `gobble_prover/prompt.py` through the model's chat template.

## Reproduce the paper's numbers

`data/Experiment.json` holds 99 formal statements: AIME 2024 (30), AIME 2025 (30) and AMC23 (39), all produced by
Kimina-Autoformalizer-7B with the correct answer among the candidates (one AMC23 statement that never type-checked
was removed). These are the Kimina-Autoformalizer correct-answer subset of the paper's benchmark; Table 1 in the
paper averages over three formalizers, and each formal statement there has two versions, one formalized with the
correct answer and one with an incorrect answer.

```bash
python sample.py --n 5   # samples -> rolls.jsonl
python judge.py          # compiles with ./mathlib4 -> results.jsonl and the summary table
```

`sample.py` takes `--model`, `--data`, `--out`, `--n`, `--max_tokens`, `--tp`; `judge.py` takes `--data`,
`--rolls`, `--out`, `--workers`, `--timeout`, `--top_c`. `results.jsonl` has one line per statement: `passed`,
`samples` (per sample, the declared values and the ones that compiled), `pairs`, `solved`, `unfaithful`.

Expected results (pass@5 on the 99 statements). Sampling took about 16 minutes on one RTX 6000 Ada (48 GB);
judging about 25 minutes with 8 workers.

| Benchmark | Statements | Lean accept | Unfaithful |
|---|---|---|---|
| AIME 2024 | 30 | 26.7% | 13.3% |
| AIME 2025 | 30 | 16.7% | 6.7% |
| AMC23 | 39 | 30.8% | 5.1% |
| Overall | 99 | 25.3% | 8.1% |

## License

Apache License 2.0 (same as the model and its base model). See `LICENSE`.

## Citation

```bibtex
@article{lin2026efficient,
  title={Efficient Proof Generation for Lean Statements with Multiple Candidate Answers},
  author={Lin, Pengzhen and Zhang, Ke and Raissi, Maziar and Shi, Zhouxing},
  journal={arXiv preprint},
  year={2026}
}
```

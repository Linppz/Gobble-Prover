"""Turn a prover output into Lean files and compile them."""
import os
import re
import subprocess

MATHLIB_DIR = os.environ.get("MATHLIB_DIR", "mathlib4")   # a Mathlib checkout; a relative path is resolved from the working directory

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
    """Declared values (at most top_c) and the proof body of one prover output, or None if the output is unusable:
    no Lean block, placeholder left in, statement changed outside the slot, or a vetoed tactic in the proof.
    A write-in value is kept only when it and every candidate are plain numbers (the paper's rule)."""
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
    """The statement with `<candidate>` replaced by (v), up to and excluding `:= by`."""
    head, _ = split_proof(template.replace("<candidate>", f"({v})"))
    return head


def lean_ok(code, timeout=120):
    try:
        r = subprocess.run(["lake", "env", "lean", "--stdin"], input=code, text=True, capture_output=True,
                           timeout=timeout, cwd=MATHLIB_DIR)
    except subprocess.TimeoutExpired:
        return False
    return r.returncode == 0 and "declaration uses 'sorry'" not in r.stdout

def render(template, menu):
    block = template.strip()
    opts = "\n".join(f"{chr(65 + i)}. {o}" for i, o in enumerate(menu))
    wi = f"{chr(65 + len(menu))}. write-in — propose your own answer."
    return (
        "Below is a Lean 4 theorem whose answer has been replaced by the "
        "placeholder `<candidate>`:\n\n"
        f"```lean4\n{block}\n```\n\n"
        f"The candidate answers are:\n{opts}\n{wi}\n\n"
        f"Pick one candidate (A–{chr(64 + len(menu))}) or write in your own "
        "value, substitute it in place of `<candidate>`, keep the rest of the "
        "statement exactly as written, and complete the proof in Lean 4.\n\n"
        "At the end of your reasoning, before the final Lean 4 code block, "
        "output one line of the form:\nPasses: `value1`, `value2`\n"
        "declaring up to two values under which you believe your proof "
        "compiles. Your proof will be graded as follows: only the first two "
        "declared values are substituted into `<candidate>`, your proof is "
        "attached unchanged, and each resulting theorem is compiled. You earn "
        "one point if at least one compiles, and one additional point if both "
        "compile and are mathematically distinct. If you declare nothing, "
        "nothing is compiled. Never modify the statement itself.\n\n"
        "Before producing the Lean 4 code, provide a detailed proof plan "
        "outlining the main proof steps and strategies.")

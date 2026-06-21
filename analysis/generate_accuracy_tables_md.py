#!/usr/bin/env python3
"""
Generate docs combining §6.2 (6×3 per model) and §6.3 (marginal pooled) with bootstrap CI.

Output: docs/main_experiment_accuracy_tables.md

Usage (from schema_effect/):
    .venv/bin/python analysis/generate_accuracy_tables_md.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from analysis.bootstrap_accuracy_ci import bootstrap_accuracy_ci, load_correct_flags

RESULTS = _ROOT / "results"
OUT_MD = _ROOT / "docs" / "main_experiment_accuracy_tables.md"
CONDITION_RE = re.compile(r"__L(\d+)S(\d+)\.csv$", re.IGNORECASE)

# Stable display order; append any other complete models alphabetically
PREFERRED_ORDER = [
    "gemini-2.5-flash",
    "qwen2.5-coder-32b-local",
    "qwen2.5-coder-14b-local",
    "qwen2.5-coder-7b-local",
    "qwen2.5-coder-3b-local",
    "qwen2.5-coder-1.5b-local",
    "qwen2.5-coder-0.5b-local",
    "phi-4-local",
    "olmo-2-13b-local",
]

DISPLAY: Dict[str, str] = {
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "qwen2.5-coder-32b-local": "Qwen2.5-Coder 32B",
    "qwen2.5-coder-14b-local": "Qwen2.5-Coder 14B",
    "qwen2.5-coder-7b-local": "Qwen2.5-Coder 7B",
    "qwen2.5-coder-3b-local": "Qwen2.5-Coder 3B",
    "qwen2.5-coder-1.5b-local": "Qwen2.5-Coder 1.5B",
    "qwen2.5-coder-0.5b-local": "Qwen2.5-Coder 0.5B",
    "phi-4-local": "Phi-4",
    "olmo-2-13b-local": "OLMo-2 13B",
}


def _fmt_pct(res) -> str:
    return f"{res.accuracy * 100:.1f}% ± {res.margin * 100:.1f}%"


def discover_complete_models() -> List[str]:
    found: Dict[str, set] = {}
    for path in RESULTS.glob("*__L*S*.csv"):
        m = CONDITION_RE.search(path.name)
        if not m:
            continue
        model = path.name.split("__", 1)[0]
        found.setdefault(model, set()).add((int(m.group(1)), int(m.group(2))))
    complete = [x for x in PREFERRED_ORDER if x in found and len(found[x]) == 18]
    for name in sorted(found):
        if len(found[name]) == 18 and name not in complete:
            complete.append(name)
    return complete


def cell_ci(
    model: str,
    L: int,
    S: int,
    *,
    n_bootstrap: int,
    seed: int,
):
    path = RESULTS / f"{model.replace('/', '-')}__L{L}S{S}.csv"
    flags = load_correct_flags(path)
    return bootstrap_accuracy_ci(flags, n_bootstrap=n_bootstrap, seed=seed + L * 10 + S)


def pool_ci(parts: Sequence[List[bool]], *, n_bootstrap: int, seed: int):
    merged: List[bool] = []
    for p in parts:
        merged.extend(p)
    return bootstrap_accuracy_ci(merged, n_bootstrap=n_bootstrap, seed=seed)


def main() -> int:
    n_bootstrap = 10_000
    seed = 42
    models = discover_complete_models()
    if not models:
        print("No complete models.", file=sys.stderr)
        return 1

    lines: List[str] = []
    lines.append("# Main experiment: execution accuracy tables\n")
    lines.append(
        "Combined view of `experiment_design.md` **§6.2** (joint structural × semantic) "
        "and **§6.3** (marginal pooled accuracies). "
        "Cell format matches §6.2: point estimate ± half-width of 95% bootstrap CI "
        f"({n_bootstrap:,} replicates). "
        "Marginal rows pool question-level outcomes across the indicated conditions "
        "(§6.3); CI is bootstrap on the **pooled** multiset of flags (dependent across conditions).\n"
    )
    lines.append(f"**Models included** ({len(models)}): " + ", ".join(DISPLAY.get(m, m) for m in models) + "\n")
    lines.append("---\n")

    # §6.2 combined: Model | Structural | S1 | S2 | S3
    lines.append("## Joint accuracy by model, structural level, and semantic level (§6.2)\n")
    lines.append(
        "| **Model** | **Structural** | **S1** | **S2** | **S3** |\n"
        "|-------------|----------------|--------|--------|--------|\n"
    )
    for model in models:
        disp = DISPLAY.get(model, model)
        for L in range(1, 7):
            row_model = disp if L == 1 else ""
            cells = []
            for S in range(1, 4):
                res = cell_ci(model, L, S, n_bootstrap=n_bootstrap, seed=seed)
                cells.append(_fmt_pct(res))
            lines.append(f"| {row_model} | **L{L}** | {cells[0]} | {cells[1]} | {cells[2]} |\n")
        lines.append("|  |  |  |  |  |\n")  # spacer between models

    lines.append("\n*Each L×S cell: n = 397 questions (one condition).*\n")

    # §6.3 — two blocks in same file
    lines.append("\n---\n")
    lines.append("## Marginal accuracy by structural level (§6.3 left)\n")
    lines.append(
        "*Pool all `results/{model}__L{i}S*.csv` rows at fixed structural level i (S1–S3). "
        f"n = 397 × 3 = 1,191 per row.*\n\n"
        "| **Model** | **L1** | **L2** | **L3** | **L4** | **L5** | **L6** |\n"
        "|-------------|--------|--------|--------|--------|--------|--------|\n"
    )
    for model in models:
        disp = DISPLAY.get(model, model)
        cols = []
        for L in range(1, 7):
            parts = [
                load_correct_flags(RESULTS / f"{model.replace('/', '-')}__L{L}S{S}.csv")
                for S in range(1, 4)
            ]
            res = pool_ci(parts, n_bootstrap=n_bootstrap, seed=seed + 1000 + hash(model) % 10000 + L)
            cols.append(_fmt_pct(res))
        lines.append(f"| {disp} | {cols[0]} | {cols[1]} | {cols[2]} | {cols[3]} | {cols[4]} | {cols[5]} |\n")

    lines.append("\n---\n")
    lines.append("## Marginal accuracy by semantic level (§6.3 right)\n")
    lines.append(
        "*Pool all `results/{model}__L*S{j}.csv` rows at fixed semantic level j (L1–L6). "
        f"n = 397 × 6 = 2,382 per row.*\n\n"
        "| **Model** | **S1** | **S2** | **S3** |\n"
        "|-------------|--------|--------|--------|\n"
    )
    for model in models:
        disp = DISPLAY.get(model, model)
        cols = []
        for S in range(1, 4):
            parts = [
                load_correct_flags(RESULTS / f"{model.replace('/', '-')}__L{L}S{S}.csv")
                for L in range(1, 7)
            ]
            res = pool_ci(parts, n_bootstrap=n_bootstrap, seed=seed + 2000 + hash(model) % 10000 + S)
            cols.append(_fmt_pct(res))
        lines.append(f"| {disp} | {cols[0]} | {cols[1]} | {cols[2]} |\n")

    lines.append("\n---\n")
    lines.append("## Regeneration\n\n")
    lines.append("```bash\ncd schema_effect\n.venv/bin/python analysis/generate_accuracy_tables_md.py\n```\n")

    OUT_MD.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_MD} ({len(models)} models)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

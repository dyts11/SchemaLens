#!/usr/bin/env python3
"""
full vs fewshot vs din vs reflexion vs dense — accuracy by semantic level
(qwen2.5-coder-14b-local).

Pools structural levels per semantic level for each of the five result
directories:
  results/full       — zero-shot baseline, pooled over L1-L6
  results/fewshot     — 3-shot static prompting, pooled over L1-L6 (held-out subset)
  results/din         — DIN-SQL decomposed prompting, pooled over L1-L6 (same subset)
  results/reflexion   — 1 self-correction retry, pooled over L1-L6
  results/dense       — dense-retrieval few-shot, pooled over L3-L6 only
                         (no L2 files; L1S3 is a partial run — excluded to
                         keep the pooled denominator uncontaminated; see
                         docs/qwen14b_fewshot_vs_full_accuracy.md)

Usage (from schema_effect/):
    .venv/bin/python analysis/plot_methods_ablation_by_S.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

FIG_DIR = _ROOT / "docs" / "figures"
MODEL = "qwen2.5-coder-14b-local"

# name_tmpl, structural levels pooled into each S value (dense: L3-L6 only)
CONDITIONS: Dict[str, Tuple[Path, str, List[int]]] = {
    "full":      (_ROOT / "results" / "full",     f"{MODEL}__L{{L}}S{{S}}.csv", list(range(1, 7))),
    "fewshot":   (_ROOT / "results" / "fewshot",  f"{MODEL}__L{{L}}S{{S}}__fs3.csv", list(range(1, 7))),
    "din":       (_ROOT / "results" / "din",      f"{MODEL}__L{{L}}S{{S}}__din.csv", list(range(1, 7))),
    "reflexion": (_ROOT / "results" / "reflexion", f"{MODEL}__L{{L}}S{{S}}__reflexion1.csv", list(range(1, 7))),
    "dense":     (_ROOT / "results" / "dense",    f"{MODEL}__L{{L}}S{{S}}__dense_fs3.csv", [3, 4, 5, 6]),
}

SERIES_COLORS = {
    "full":      "#767676",  # neutral_mid — baseline
    "fewshot":   "#0F4D92",  # blue_main
    "din":       "#42949E",  # teal
    "reflexion": "#9A4D8E",  # violet
    "dense":     "#B64342",  # red_strong — top performer
}
SERIES_LABELS = {
    "full": "zero-shot",
    "fewshot": "fewshot",
    "din": "din",
    "reflexion": "reflexion",
    "dense": "dense",
}
SEM_LABELS = ["S1", "S2", "S3"]


def _apply_pub_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
        }
    )


def save_pub(fig: plt.Figure, stem: Path) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{stem}.svg", bbox_inches="tight")
    fig.savefig(f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(f"{stem}.png", dpi=600, bbox_inches="tight")
    plt.close(fig)


def _accuracy_by_S(results_dir: Path, name_tmpl: str, pooled_Ls: List[int]) -> np.ndarray:
    """Accuracy % per semantic level, pooled over the given structural levels."""
    acc = np.full(3, np.nan)
    for si, S in enumerate(range(1, 4)):
        correct = 0
        total = 0
        for L in pooled_Ls:
            path = results_dir / name_tmpl.format(L=L, S=S)
            if not path.exists():
                raise FileNotFoundError(path)
            with path.open(encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    total += 1
                    if str(row.get("correct", "")).strip().lower() == "true":
                        correct += 1
        acc[si] = 100.0 * correct / total if total else np.nan
    return acc


def load_all() -> Dict[str, np.ndarray]:
    return {
        name: _accuracy_by_S(results_dir, name_tmpl, pooled_Ls)
        for name, (results_dir, name_tmpl, pooled_Ls) in CONDITIONS.items()
    }


def plot(data: Dict[str, np.ndarray], out_stem: Path) -> None:
    _apply_pub_style()
    fig, ax = plt.subplots(figsize=(3.9, 2.95))
    x = np.arange(len(SEM_LABELS))

    for name in ("full", "fewshot", "din", "reflexion", "dense"):
        y = data[name]
        color = SERIES_COLORS[name]
        ax.plot(
            x,
            y,
            color=color,
            linewidth=1.9,
            marker="o",
            markersize=5.2,
            markerfacecolor=color,
            markeredgecolor="#272727",
            markeredgewidth=0.45,
            label=SERIES_LABELS[name],
            zorder=3,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(SEM_LABELS, fontsize=7)
    ax.set_xlabel("Semantic level", fontsize=7.5, labelpad=4)
    ax.set_ylabel("Execution accuracy (%)", fontsize=7.5)
    y_max = 45.0
    ax.set_ylim(0, y_max)
    ax.set_yticks(np.linspace(0, y_max, 4))
    ax.set_title(
        "Prompting / self-correction methods by semantic level\n(qwen2.5-coder-14b-local)",
        fontsize=8,
        fontweight="bold",
        pad=6,
    )
    ax.legend(fontsize=6, loc="upper left")

    half = 0.5
    ax.set_xlim(-half, len(SEM_LABELS) - 1 + half)

    fig.text(
        0.5,
        0.01,
        "full/fewshot/din/reflexion pooled over L1–L6; dense pooled over L3–L6 only (see caption note in figure script).",
        ha="center",
        fontsize=5.5,
        color="#606060",
    )

    fig.tight_layout(rect=[0, 0.05, 1, 1])
    save_pub(fig, out_stem)


def main() -> int:
    data = load_all()
    out_stem = FIG_DIR / "qwen14b_methods_ablation_by_S"
    plot(data, out_stem)
    print(f"Wrote {out_stem}.{{svg,pdf,png}}")

    print("\nAccuracy by semantic level (%):\n")
    print("| S | full | fewshot | din | reflexion | dense |")
    print("|---|---|---|---|---|---|")
    for si, S in enumerate(SEM_LABELS):
        cells = []
        for n in ("full", "fewshot", "din", "reflexion", "dense"):
            v = data[n][si]
            cells.append("-" if np.isnan(v) else f"{v:.1f}")
        print(f"| {S} | " + " | ".join(cells) + " |")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

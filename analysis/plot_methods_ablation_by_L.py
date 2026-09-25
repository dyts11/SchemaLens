#!/usr/bin/env python3
"""
full vs fewshot vs din vs reflexion vs dense — accuracy by structural level
(qwen2.5-coder-14b-local).

Pools S1-S3 per structural level for each of the five result directories:
  results/full       — zero-shot baseline (n=397/cell)
  results/fewshot     — 3-shot static prompting (n=370/cell; held-out subset)
  results/din         — DIN-SQL decomposed prompting (n=370/cell; same subset)
  results/reflexion   — 1 self-correction retry (n=397/cell)
  results/dense       — dense-retrieval few-shot (n=397/cell, L3-L6 only —
                         no L2 files and L1S3 is a partial run, so dense is
                         plotted for L3-L6 only; see
                         docs/qwen14b_fewshot_vs_full_accuracy.md)

Usage (from schema_effect/):
    .venv/bin/python analysis/plot_methods_ablation_by_L.py
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

# name_tmpl, valid structural levels (dense excludes L2 [no files] and L1 [partial L1S3])
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
STRUCT_LABELS = ["L1", "L2", "L3", "L4", "L5", "L6"]


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


def _accuracy_by_L(results_dir: Path, name_tmpl: str, valid_Ls: List[int]) -> np.ndarray:
    """Accuracy % per structural level (NaN where not valid), pooled over S1-S3."""
    acc = np.full(6, np.nan)
    for li, L in enumerate(range(1, 7)):
        if L not in valid_Ls:
            continue
        correct = 0
        total = 0
        for S in range(1, 4):
            path = results_dir / name_tmpl.format(L=L, S=S)
            if not path.exists():
                raise FileNotFoundError(path)
            with path.open(encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    total += 1
                    if str(row.get("correct", "")).strip().lower() == "true":
                        correct += 1
        acc[li] = 100.0 * correct / total if total else np.nan
    return acc


def load_all() -> Dict[str, np.ndarray]:
    return {
        name: _accuracy_by_L(results_dir, name_tmpl, valid_Ls)
        for name, (results_dir, name_tmpl, valid_Ls) in CONDITIONS.items()
    }


def plot(data: Dict[str, np.ndarray], out_stem: Path) -> None:
    _apply_pub_style()
    fig, ax = plt.subplots(figsize=(3.9, 2.95))
    x = np.arange(len(STRUCT_LABELS))

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
    ax.set_xticklabels(STRUCT_LABELS, fontsize=7)
    ax.set_xlabel("Structural level", fontsize=7.5, labelpad=4)
    ax.set_ylabel("Execution accuracy (%)", fontsize=7.5)
    y_max = 40.0
    ax.set_ylim(0, y_max)
    ax.set_yticks(np.linspace(0, y_max, 5))
    ax.set_title(
        "Prompting / self-correction methods by structural level\n(qwen2.5-coder-14b-local)",
        fontsize=8,
        fontweight="bold",
        pad=6,
    )
    ax.legend(fontsize=6, loc="upper left")

    half = 0.5
    ax.set_xlim(-half, len(STRUCT_LABELS) - 1 + half)

    fig.text(
        0.5,
        0.01,
        "Pooled over S1–S3 per structural level. dense: L3–L6 only (no L2 data; L1S3 partial run excluded).",
        ha="center",
        fontsize=5.5,
        color="#606060",
    )

    fig.tight_layout(rect=[0, 0.05, 1, 1])
    save_pub(fig, out_stem)


def main() -> int:
    data = load_all()
    out_stem = FIG_DIR / "qwen14b_methods_ablation_by_L"
    plot(data, out_stem)
    print(f"Wrote {out_stem}.{{svg,pdf,png}}")

    print("\nAccuracy by structural level (%):\n")
    print("| L | full | fewshot | din | reflexion | dense |")
    print("|---|---|---|---|---|---|")
    for li, L in enumerate(STRUCT_LABELS):
        cells = []
        for n in ("full", "fewshot", "din", "reflexion", "dense"):
            v = data[n][li]
            cells.append("-" if np.isnan(v) else f"{v:.1f}")
        print(f"| {L} | " + " | ".join(cells) + " |")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

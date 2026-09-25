#!/usr/bin/env python3
"""
zero-shot vs fewshot vs reflexion vs dense — accuracy by structural level
(top) and semantic level (bottom), combined into one model_size.png-style
two-panel figure (qwen2.5-coder-14b-local). din-sql dropped.

Usage (from schema_effect/):
    .venv/bin/python analysis/plot_methods_ablation_combined.py
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

CONDITIONS: Dict[str, Tuple[Path, str, List[int]]] = {
    "full":      (_ROOT / "results" / "full",      f"{MODEL}__L{{L}}S{{S}}.csv", list(range(1, 7))),
    "fewshot":   (_ROOT / "results" / "fewshot",   f"{MODEL}__L{{L}}S{{S}}__fs3.csv", list(range(1, 7))),
    "reflexion": (_ROOT / "results" / "reflexion", f"{MODEL}__L{{L}}S{{S}}__reflexion1.csv", list(range(1, 7))),
    "dense":     (_ROOT / "results" / "dense",     f"{MODEL}__L{{L}}S{{S}}__dense_fs3.csv", [3, 4, 5, 6]),
}

SERIES_ORDER = ("full", "fewshot", "reflexion", "dense")
SERIES_COLORS = {
    "full": "#1F77B4",
    "fewshot": "#FF7F0E",
    "reflexion": "#17BECF",
    "dense": "#8C564B",
}
SERIES_LABELS = {
    "full": "zero-shot",
    "fewshot": "fewshot",
    "reflexion": "reflexion",
    "dense": "dense",
}
STRUCT_LABELS = ["L1", "L2", "L3", "L4", "L5", "L6"]
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


def _load_rows(path: Path) -> List[dict]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def accuracy_by_L(results_dir: Path, name_tmpl: str, valid_Ls: List[int]) -> np.ndarray:
    acc = np.full(6, np.nan)
    for li, L in enumerate(range(1, 7)):
        if L not in valid_Ls:
            continue
        correct = total = 0
        for S in range(1, 4):
            for row in _load_rows(results_dir / name_tmpl.format(L=L, S=S)):
                total += 1
                if str(row.get("correct", "")).strip().lower() == "true":
                    correct += 1
        acc[li] = 100.0 * correct / total if total else np.nan
    return acc


def accuracy_by_S(results_dir: Path, name_tmpl: str, pooled_Ls: List[int]) -> np.ndarray:
    acc = np.full(3, np.nan)
    for si, S in enumerate(range(1, 4)):
        correct = total = 0
        for L in pooled_Ls:
            for row in _load_rows(results_dir / name_tmpl.format(L=L, S=S)):
                total += 1
                if str(row.get("correct", "")).strip().lower() == "true":
                    correct += 1
        acc[si] = 100.0 * correct / total if total else np.nan
    return acc


def load_all() -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
    by_L = {name: accuracy_by_L(rd, tmpl, ls) for name, (rd, tmpl, ls) in CONDITIONS.items()}
    by_S = {name: accuracy_by_S(rd, tmpl, ls) for name, (rd, tmpl, ls) in CONDITIONS.items()}
    return by_L, by_S


def _draw_panel(ax: plt.Axes, data: Dict[str, np.ndarray], x_labels: List[str], y_max: float, *, show_ylabel: bool) -> None:
    x = np.arange(len(x_labels))
    for name in SERIES_ORDER:
        y = data[name]
        color = SERIES_COLORS[name]
        ax.plot(
            x,
            y,
            color=color,
            linewidth=2.3,
            marker="o",
            markersize=6.5,
            markerfacecolor=color,
            markeredgecolor="#272727",
            markeredgewidth=0.5,
            label=SERIES_LABELS[name],
            zorder=3,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=13)
    if show_ylabel:
        ax.set_ylabel("Execution accuracy (%)", fontsize=14)
    ax.set_ylim(0, y_max)
    ax.set_yticks(np.arange(0, y_max + 1, 15))
    ax.tick_params(axis="y", labelleft=True, labelsize=12)
    ax.yaxis.grid(True, linestyle="-", linewidth=0.35, color="#D8D8D8", zorder=0)
    ax.set_axisbelow(True)
    half = 0.5
    ax.set_xlim(-half, len(x_labels) - 1 + half)


def plot(by_L: Dict[str, np.ndarray], by_S: Dict[str, np.ndarray], out_stem: Path) -> None:
    _apply_pub_style()
    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(7.6, 3.4))
    y_max = 45.0

    _draw_panel(ax_left, by_L, STRUCT_LABELS, y_max=y_max, show_ylabel=True)
    ax_left.set_xlabel("Structural level", fontsize=14, labelpad=4)

    _draw_panel(ax_right, by_S, SEM_LABELS, y_max=y_max, show_ylabel=False)
    ax_right.set_xlabel("Semantic level", fontsize=14, labelpad=4)

    handles, labels = ax_left.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=4,
        fontsize=13,
        bbox_to_anchor=(0.5, -0.03),
        columnspacing=1.1,
        handletextpad=0.4,
    )

    fig.subplots_adjust(left=0.09, right=0.99, bottom=0.26, top=0.98, wspace=0.08)
    save_pub(fig, out_stem)


def main() -> int:
    by_L, by_S = load_all()
    out_stem = FIG_DIR / "qwen14b_methods_ablation_combined"
    plot(by_L, by_S, out_stem)
    print(f"Wrote {out_stem}.{{svg,pdf,png}}")

    print("\nAccuracy by structural level (%):\n")
    print("| L | " + " | ".join(SERIES_LABELS[n] for n in SERIES_ORDER) + " |")
    print("|---|" + "---|" * len(SERIES_ORDER))
    for li, L in enumerate(STRUCT_LABELS):
        cells = ["-" if np.isnan(by_L[n][li]) else f"{by_L[n][li]:.1f}" for n in SERIES_ORDER]
        print(f"| {L} | " + " | ".join(cells) + " |")

    print("\nAccuracy by semantic level (%):\n")
    print("| S | " + " | ".join(SERIES_LABELS[n] for n in SERIES_ORDER) + " |")
    print("|---|" + "---|" * len(SERIES_ORDER))
    for si, S in enumerate(SEM_LABELS):
        cells = ["-" if np.isnan(by_S[n][si]) else f"{by_S[n][si]:.1f}" for n in SERIES_ORDER]
        print(f"| {S} | " + " | ".join(cells) + " |")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

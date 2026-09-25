#!/usr/bin/env python3
"""
full vs cot vs ev vs cot_ev — accuracy by structural level (qwen2.5-coder-14b-local).

Pools S1-S3 per structural level for each of the four result directories:
  results/full     — zero-shot baseline
  results/cot       — chain-of-thought instruction block
  results/ev        — BIRD evidence hints injected
  results/cot_ev    — both combined

Usage (from schema_effect/):
    .venv/bin/python analysis/plot_cot_ev_ablation_by_L.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from typing import Dict, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

FIG_DIR = _ROOT / "docs" / "figures"
MODEL = "qwen2.5-coder-14b-local"

CONDITIONS: Dict[str, Tuple[Path, str]] = {
    "full":    (_ROOT / "results" / "full",    f"{MODEL}__L{{L}}S{{S}}.csv"),
    "cot":     (_ROOT / "results" / "cot",      f"{MODEL}__L{{L}}S{{S}}__cot.csv"),
    "ev":      (_ROOT / "results" / "ev",       f"{MODEL}__L{{L}}S{{S}}__ev.csv"),
    "cot_ev":  (_ROOT / "results" / "cot_ev",   f"{MODEL}__L{{L}}S{{S}}__cot__ev.csv"),
}

# Two method families: cool = no evidence hints, warm = evidence hints.
SERIES_COLORS = {
    "full":    "#484878",  # baseline_dark (NMI pastel) — cool, zero-shot
    "cot":     "#7884B4",  # baseline_mid  (NMI pastel) — cool, +CoT only
    "ev":      "#D24B40",  # warm accent — +evidence hints
    "cot_ev":  "#E28E2C",  # warm accent (secondary) — +evidence +CoT
}
SERIES_LABELS = {
    "full": "zero-shot",
    "cot": "cot",
    "ev": "ev",
    "cot_ev": "cot_ev",
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


def _accuracy_by_L(results_dir: Path, name_tmpl: str) -> np.ndarray:
    """Accuracy % per structural level, pooled over S1-S3."""
    acc = np.full(6, np.nan)
    for li, L in enumerate(range(1, 7)):
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
        name: _accuracy_by_L(results_dir, name_tmpl)
        for name, (results_dir, name_tmpl) in CONDITIONS.items()
    }


def plot(data: Dict[str, np.ndarray], out_stem: Path) -> None:
    _apply_pub_style()
    fig, ax = plt.subplots(figsize=(3.9, 2.95))
    x = np.arange(len(STRUCT_LABELS))

    for name in ("full", "cot", "ev", "cot_ev"):
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
    y_max = 45.0
    ax.set_ylim(0, y_max)
    ax.set_yticks(np.linspace(0, y_max, 4))
    ax.set_title(
        "Evidence hints vs chain-of-thought by structural level\n(qwen2.5-coder-14b-local)",
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
        "Pooled over S1–S3 per structural level; n=397 questions/cell.",
        ha="center",
        fontsize=5.5,
        color="#606060",
    )

    fig.tight_layout(rect=[0, 0.04, 1, 1])
    save_pub(fig, out_stem)


def main() -> int:
    data = load_all()
    out_stem = FIG_DIR / "qwen14b_cot_ev_ablation_by_L"
    plot(data, out_stem)
    print(f"Wrote {out_stem}.{{svg,pdf,png}}")

    print("\nAccuracy by structural level (%):\n")
    print("| L | full | cot | ev | cot_ev |")
    print("|---|---|---|---|---|")
    for li, L in enumerate(STRUCT_LABELS):
        row = " | ".join(f"{data[n][li]:.1f}" for n in ("full", "cot", "ev", "cot_ev"))
        print(f"| {L} | {row} |")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
